#!/usr/bin/python
# -*- coding: utf-8 -*-

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement

from flask import Flask
from flask import jsonify
from flask import request
from flask import Response
from flask import make_response
from flask import current_app
from flask import render_template

from datetime import timedelta
from functools import update_wrapper

import os.path
import json
import logging

app = Flask(__name__)
app.config.from_object(__name__)

chatbot = ChatBot('Smart Bot', trainer='chatterbot.trainers.ChatterBotCorpusTrainer')
#chatbot = ChatBot('Smart Bot', trainer='chatterbot.trainers.UbuntuCorpusTrainer')

def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))


def get_file(filename):  # pragma: no cover
    try:
        src = os.path.join(root_dir(), filename)
        return open(src).read()
    except IOError as exc:
        return str(exc)

def crossdomain(origin=None, methods=None, headers=None, max_age=21600, attach_to_all=True, automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator


@app.route('/', methods=['GET'])
@crossdomain(origin='*')
def home():
    content = get_file('html/index.html')
    return Response(content, mimetype="text/html")
    #return render_template('html/index.html')

"""
method: GET
parameter:  sentence
"""
@app.route('/chat', methods=['GET'])
@crossdomain(origin='*')
def chat():
    # call chat api
    resp = chatbot.get_response(request.args.get('sentence', ''))
    return resp.text

if __name__ == '__main__':
    # preprocessing, training
    chatbot.train('chatterbot.corpus.english')
    #chatbot.train()
    app.run('0.0.0.0', 8080)

