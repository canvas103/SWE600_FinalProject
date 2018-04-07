#!/usr/bin/python
# -*- coding: utf-8 -*-

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement
import logging


from flask import Flask
from flask import jsonify
from flask import request
from flask import Response

import json

app = Flask(__name__)

chatbot = ChatBot('Smart Bot', trainer='chatterbot.trainers.ChatterBotCorpusTrainer')


@app.route('/')
def home():
    return "Hello SmartBot!"

"""
method: POST
parameter:  sentence
"""
@app.route('/chat', methods=['POST'])
def chat():
    # call chat api
    resp = chatbot.get_response(request.form['sentence'])
    msg = {'resp' : resp.text}
    return Response(json.dumps(msg), status=200, mimetype='application/json')

if __name__ == '__main__':
    # preprocessing, training
    chatbot.train('chatterbot.corpus.english')
    app.run('0.0.0.0', 8080)

