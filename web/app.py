from flask import Flask, jsonify, request
from flask_restful import Api, Resource

import bcrypt
from pymongo import MongoClient
import spacy

app = Flask(__name__)
api = Api(app)

# Making connection with MongoClient
client = MongoClient("mongodb://db:27017")
# Getting a db
db = client['SimilarityDB']
# Getting a collection
users = db["Users"]


def UserExist(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


class Register(Resource):
    def post(self):
        postData = request.get_json()

        username = postData["username"]
        password = postData["password"]

        # Assume request contains username and pw
        if UserExist(username):
            retJson = {
                "status": 301,
                "msg": "Username exist"
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 6
        })

        retJson = {
            "status": 200,
            "msg": "You successfully sign up to the api"
        }

        return jsonify(retJson)


def verifyPw(username, password):
    if not UserExist(username):
        return False

    hashed_pw = users.find({
        "Username": username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def countTokens(username):
    tokens = users.find({
        "Username": username
    })[0]["Tokens"]
    return tokens


class Detect(Resource):
    def post(self):
        postData = request.get_json()

        username = postData["username"]
        password = postData["password"]
        text1 = postData["text1"]
        text2 = postData["text2"]

        if not UserExist(username):
            retJson = {
                "status": 301,
                "msg": "Username exist"
            }
            return jsonify(retJson)

        correct_pw = verifyPw(username, password)
        if not correct_pw:
            retJson = {
                "status": 302,
                "msg": "Invalid Password"
            }
            return jsonify(retJson)

        # verify enough tokens
        num_tokens = countTokens(username)

        if not num_tokens > 0:
            retJson = {
                "status": 303,
                "msg": "Not enough tokens"
            }
            return jsonify(retJson)

        # Calculate the edit distance
        nlp = spacy.load('en_core_web_sm')

        text1 = nlp(text1)
        text2 = nlp(text2)
        # the closer ratio is to 1, the more similar text1 and text2 are
        ratio = text1.similarity(text2)

        retJson = {
            "status": 200,
            "similarity": ratio,
            "msg": "Successfully calculated successfully"
        }

        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": num_tokens-1
            }
        })

        return jsonify(retJson)


class Refill(Resource):
    def post(self):
        postData = request.get_json()

        username = postData["username"]
        password = postData["admin_pw"]
        refill_amount = postData["refill"]

        if not UserExist(username):
            retJson = {
                "status": 301,
                "msg": "Invalid username"
            }
            return jsonify(retJson)

        # For test use, but never do this
        # Create a collection of admins that has password
        correct_pw = "mabuuuu"
        if not password == correct_pw:
            retJson = {
                "status": 304,
                "msg": "Invalid Admin Password"
            }
            return jsonify(retJson)

        num_tokens = countTokens(username)
        new_num_tokens = num_tokens+refill_amount

        users.update({
            "Username": username
        }, {
            "$set": {
                "Tokens": refill_amount+num_tokens
            }
        })
        retJson = {
            "status": 200,
            "msg": "Refilled sucessfully",
            "balance": "Now the user has " + str(new_num_tokens)+" tokens."
        }

        return jsonify(retJson)


api.add_resource(Register, "/register")
api.add_resource(Detect, "/detect")
api.add_resource(Refill, "/refill")


@app.route("/")
def hello():
    return "Hello, World!"


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
