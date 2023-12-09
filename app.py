from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request, redirect, url_for, json
import jwt
import hashlib
import uuid
from datetime import (
    datetime, # representing and manipulating date and time
    # representing the difference between two dates or times
    # ( Getting the time difference )
    timedelta 
)

import os
from os.path import join, dirname
from dotenv import load_dotenv
import random
import string

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

conn = MongoClient(MONGODB_URI) # Create connection to MongoDB Cluster
db = conn[DB_NAME]

app = Flask(__name__)

# VARS
SECRET_KEY = 'SPARTA' # NEEDED for JWT process encrypting
TOKEN_KEY = 'mytoken'

# RENDER PAGES

# LOGIN ADMIN
@app.route('/admin/login')
def admin_login():
    msg = request.args.get('msg')
    return render_template('admin/login_admin.html', msg = msg)

@app.route('/admin/user')
def menu_user():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms = ['HS256']
        )
        username = payload.get('id') 
        user_info = db.admin.find_one(
            {'username': username},
            {'_id': False}
        )
        datas = db.user.find({}, {'_id':False})
        user_data = enumerate(datas, start=1)
        return render_template('admin/menu_user.html', user_info = user_info, user_data = user_data)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin_login'))
    
@app.route('/admin/artwork')
def menu_artwork():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms = ['HS256']
        )
        username = payload.get('id') 
        user_info = db.admin.find_one(
            {'username': username},
            {'_id': False}
        )
        # Create random ID Artwork 
        artworks = db.artwork.find({})
        """ length = 3
        random_id = ''.join(random.choice(string.ascii_lowercase) for _ in range(length)) """
        return render_template('admin/menu_artwork.html', user_info = user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin_login'))
    

@app.route('/admin')
def admin():
    token_receive = request.cookies.get(TOKEN_KEY)
    # decrypting the important variables' value (TOKEN)
    try:
        payload = jwt.decode( # translating the token
            token_receive,
            SECRET_KEY,
            algorithms = ['HS256']
        )
        # get the user info and set them as payload
        user_info = db.admin.find_one({'username': payload.get('id')})
        return render_template('admin/dashboard_admin.html', user_info = user_info)
    # handle if the token has expired
    except jwt.ExpiredSignatureError:
        msg = "Your token has expired"
        # redirecting client to login endpoint with 'msg' data
        return redirect(url_for('admin_login', msg = msg))
    except jwt.exceptions.DecodeError:
        msg = 'There was a problem logging you in'
        return redirect(url_for('admin_login', msg = msg))
    

# PROCESSES

@app.route('/admin/loggingin', methods=["POST"])
def login_process():
    
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    hashed_pw = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    
    result = db.admin.find_one({
        "username": username_receive,
        "password": hashed_pw
    })
    
    if result:
        payload = {
            "id" : username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256").decode('utf-8')
        return jsonify({"result": "success", "token":token})
    else:
        return jsonify({
            "result": "fail",
            "msg": "We could not found admin data with that that username/ password combination"
        })


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)