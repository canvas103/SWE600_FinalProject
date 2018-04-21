import logging
import os
import sys
from .conversation import Statement, Response
from . import utils


class Trainer(object):
    """
    Base class for all other trainer classes.
    """

    def __init__(self, storage, **kwargs):
        self.chatbot = kwargs.get('chatbot')
        self.storage = storage
        self.logger = logging.getLogger(__name__)
        self.show_training_progress = kwargs.get('show_training_progress', True)

    def get_preprocessed_statement(self, input_statement):
        """
        Preprocess the input statement.
        """

        # The chatbot is optional to prevent backwards-incompatible changes
        if not self.chatbot:
            return input_statement

        for preprocessor in self.chatbot.preprocessors:
            input_statement = preprocessor(self, input_statement)

        return input_statement

    def train(self, *args, **kwargs):
        """
        This method must be overridden by a child class.
        """
        raise self.TrainerInitializationException()

    def get_or_create(self, statement_text):
        """
        Return a statement if it exists.
        Create and return the statement if it does not exist.
        """
        temp_statement = self.get_preprocessed_statement(
            Statement(text=statement_text)
        )

        statement = self.storage.find(temp_statement.text)

        if not statement:
            statement = Statement(temp_statement.text)

        return statement

    class TrainerInitializationException(Exception):
        """
        Exception raised when a base class has not overridden
        the required methods on the Trainer base class.
        """

        def __init__(self, value=None):
            default = (
                'A training class must be specified before calling train(). ' +
                'See http://chatterbot.readthedocs.io/en/stable/training.html'
            )
            self.value = value or default

        def __str__(self):
            return repr(self.value)

    def _generate_export_data(self):
        result = []
        for statement in self.storage.filter():
            for response in statement.in_response_to:
                result.append([response.text, statement.text])

        return result

    def export_for_training(self, file_path='./export.json'):
        """
        Create a file from the database that can be used to
        train other chat bots.
        """
        import json
        export = {'conversations': self._generate_export_data()}
        with open(file_path, 'w+') as jsonfile:
            json.dump(export, jsonfile, ensure_ascii=False)


class ListTrainer(Trainer):
    """
    Allows a chat bot to be trained using a list of strings
    where the list represents a conversation.
    """

    def train(self, conversation):
        """
        Train the chat bot based on the provided list of
        statements that represents a single conversation.
        """
        previous_statement_text = None

        for conversation_count, text in enumerate(conversation):
            if self.show_training_progress:
                utils.print_progress_bar(
                    'List Trainer',
                    conversation_count + 1, len(conversation)
                )

            statement = self.get_or_create(text)

            if previous_statement_text:
                statement.add_response(
                    Response(previous_statement_text)
                )

            previous_statement_text = statement.text
            self.storage.update(statement)


class ChatterBotCorpusTrainer(Trainer):
    """
    Allows the chat bot to be trained using data from the
    ChatterBot dialog corpus.
    """

    def __init__(self, storage, **kwargs):
        super(ChatterBotCorpusTrainer, self).__init__(storage, **kwargs)
        from .corpus import Corpus

        self.corpus = Corpus()

    def train(self, *corpus_paths):

        # Allow a list of corpora to be passed instead of arguments
        if len(corpus_paths) == 1:
            if isinstance(corpus_paths[0], list):
                corpus_paths = corpus_paths[0]

        # Train the chat bot with each statement and response pair
        for corpus_path in corpus_paths:

            corpora = self.corpus.load_corpus(corpus_path)

            corpus_files = self.corpus.list_corpus_files(corpus_path)
            for corpus_count, corpus in enumerate(corpora):
                for conversation_count, conversation in enumerate(corpus):

                    if self.show_training_progress:
                        utils.print_progress_bar(
                            str(os.path.basename(corpus_files[corpus_count])) + ' Training',
                            conversation_count + 1,
                            len(corpus)
                        )

                    previous_statement_text = None

                    for text in conversation:
                        statement = self.get_or_create(text)
                        statement.add_tags(corpus.categories)

                        if previous_statement_text:
                            statement.add_response(
                                Response(previous_statement_text)
                            )

                        previous_statement_text = statement.text
                        self.storage.update(statement)


class UbuntuCorpusTrainer(Trainer):
    """
    Allow chatbots to be trained with the data from
    the Ubuntu Dialog Corpus.
    """

    def __init__(self, storage, **kwargs):
        super(UbuntuCorpusTrainer, self).__init__(storage, **kwargs)

        self.data_download_url = kwargs.get(
            'ubuntu_corpus_data_download_url',
            'http://cs.mcgill.ca/~jpineau/datasets/ubuntu-corpus-1.0/ubuntu_dialogs.tgz'
        )

        self.data_directory = kwargs.get(
            'ubuntu_corpus_data_directory',
            './data/'
        )

        self.extracted_data_directory = os.path.join(
            self.data_directory, 'ubuntu_dialogs'
        )

        # Create the data directory if it does not already exist
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)

    def is_downloaded(self, file_path):
        """
        Check if the data file is already downloaded.
        """
        if os.path.exists(file_path):
            self.logger.info('File is already downloaded')
            return True

        return False

    def is_extracted(self, file_path):
        """
        Check if the data file is already extracted.
        """

        if os.path.isdir(file_path):
            self.logger.info('File is already extracted')
            return True
        return False

    def download(self, url, show_status=True):
        """
        Download a file from the given url.
        Show a progress indicator for the download status.
        Based on: http://stackoverflow.com/a/15645088/1547223
        """
        import requests

        file_name = url.split('/')[-1]
        file_path = os.path.join(self.data_directory, file_name)

        # Do not download the data if it already exists
        if self.is_downloaded(file_path):
            return file_path

        with open(file_path, 'wb') as open_file:
            print('Downloading %s' % url)
            response = requests.get(url, stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None:
                # No content length header
                open_file.write(response.content)
            else:
                download = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    download += len(data)
                    open_file.write(data)
                    if show_status:
                        done = int(50 * download / total_length)
                        sys.stdout.write('\r[%s%s]' % ('=' * done, ' ' * (50 - done)))
                        sys.stdout.flush()

            # Add a new line after the download bar
            sys.stdout.write('\n')

        print('Download location: %s' % file_path)
        return file_path

    def extract(self, file_path):
        """
        Extract a tar file at the specified file path.
        """
        import tarfile

        print('Extracting {}'.format(file_path))

        if not os.path.exists(self.extracted_data_directory):
            os.makedirs(self.extracted_data_directory)

        def track_progress(members):
            sys.stdout.write('.')
            for member in members:
                # This will be the current file being extracted
                yield member

        with tarfile.open(file_path) as tar:
            tar.extractall(path=self.extracted_data_directory, members=track_progress(tar))

        self.logger.info('File extracted to {}'.format(self.extracted_data_directory))

        return True

    def train(self):
        import glob
        import csv

        # Download and extract the Ubuntu dialog corpus if needed
        corpus_download_path = self.download(self.data_download_url)

        # Extract if the directory doesn not already exists
        if not self.is_extracted(self.extracted_data_directory):
            self.extract(corpus_download_path)

        extracted_corpus_path = os.path.join(
            self.extracted_data_directory,
            '**', '**', '*.tsv'
        )

        file_kwargs = {}

        if sys.version_info[0] > 2:
            # Specify the encoding in Python versions 3 and up
            file_kwargs['encoding'] = 'utf-8'
            # WARNING: This might fail to read a unicode corpus file in Python 2.x

        for file in glob.iglob(extracted_corpus_path):
            self.logger.info('Training from: {}'.format(file))

            with open(file, 'r', **file_kwargs) as tsv:
                reader = csv.reader(tsv, delimiter='\t')

                previous_statement_text = None

                for row in reader:
                    if len(row) > 0:
                        text = row[3]
                        statement = self.get_or_create(text)
                        print(text, len(row))

                        statement.add_extra_data('datetime', row[0])
                        statement.add_extra_data('speaker', row[1])

                        if row[2].strip():
                            statement.add_extra_data('addressing_speaker', row[2])

                        if previous_statement_text:
                            statement.add_response(
                                Response(previous_statement_text)
                            )

                        previous_statement_text = statement.text
                        self.storage.update(statement)
