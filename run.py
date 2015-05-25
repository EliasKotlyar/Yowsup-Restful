from yowsuprestful.stack import QueueStack

from flask import Flask
from flask_restful import Resource, Api
from flask import request
import sys

app = Flask(__name__)
api = Api(app)
stack = QueueStack()


class getMessage(Resource):
    def get(self):
        message = stack.getMessage()
        if not message:
            message = {}
        return message


class postMessage(Resource):
    def get(self):
        msg = request.args.get('msg', '')
        number = request.args.get('number', '')
        stack.sendMessage(number, msg)
        message = {
            "sended": "1"
        }
        return message


class postImageByPath(Resource):
    def get(self):
        path = request.args.get('path', '')
        number = request.args.get('number', '')
        stack.sendImage(number, path)
        message = {
            "sended": "1"
        }
        return message


class postImageBase64(Resource):
    def get(self):
        raise Exception("To Implement")


class postImageUrl(Resource):
    def get(self):
        raise Exception("To Implement")


api.add_resource(getMessage, '/')
api.add_resource(postMessage, '/postMessage')
api.add_resource(postImageByPath, '/postImageByPath')
api.add_resource(postImageBase64, '/postImageBase64')
api.add_resource(postImageUrl, '/postImageUrl')

if __name__ == '__main__':
    args = sys.argv
    user = args[1]
    password = args[2]

    # stack.sendMessage()
    stack.start(user, password)

    app.run(debug=True)
