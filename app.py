from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request, redirect, url_for, json
import jwt
import hashlib
import uuid
from bson.objectid import ObjectId
from datetime import (
    datetime, # representing and manipulating date and time
    # representing the difference between two dates or times
    # ( Getting the time difference )
    timedelta 
)

import os
from datetime import datetime, timedelta
from os.path import dirname, join

import jwt
from dotenv import load_dotenv
import random
import string

app = Flask(__name__)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY = os.environ.get("TOKEN_KEY")

conn = MongoClient(MONGODB_URI)
db = conn[DB_NAME]

@app.route("/", methods=["GET"])
def home():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})

        result = db.artwork.find({})
        return render_template("fans/index.html", user_info=user_info, result=result)

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = "Terjadi kesalahan atau token telah kedaluwarsa. Silakan login kembali untuk melanjutkan."
        return redirect(url_for("login", msg=msg))


# ROUTE HALAMAN LOGIN
@app.route("/login", methods=["GET"])
def login():
    msg = request.args.get("msg")
    return render_template("fans/login.html", msg=msg)


# CEK DUPLICATE ID PENDAFTARAN
@app.route("/sign_up/check_dup", methods=["POST"])
def check_dup():
    username_receive = request.form.get("username_give")
    exists = bool(db.user_login.find_one({"username": username_receive}))
    return jsonify({"result": "success", "exists": exists})


# ROUTE UNTUK MENYIMPAN DATA PENDAFTARAN USER
@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    name_receive = request.form["name_give"]
    alamat_receive = request.form["address_give"]
    phone_receive = int(request.form["phone_give"])

    password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()

    doc = {
        "username": username_receive,
        "password": password_hash,
        "name": name_receive,
        "alamat": alamat_receive,
        "phone": phone_receive,
        "profile_name": name_receive,
        "profile_pic": "",
        "profile_pic_real": "profile_pics/profile_placeholder.png",
        "profile_info": "",
    }
    db.user_login.insert_one(doc)
    return jsonify({"result": "success"})


# ROUTE CEK DATA LOGIN
@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    
    result = db.user_login.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256").decode('utf-8')
        
        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "Mohon pastikan bahwa ID pengguna dan sandi yang Anda masukkan sesuai dengan yang terdaftar.",
            }
        )

# ROUTE ARTWORK
@app.route("/artwork", methods=["GET"])
def get_artwork():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})

        artwork = db.artwork.find({})
        return render_template(
            "fans/artwork.html", user_info=user_info, artwork=artwork
        )

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = "Terjadi kesalahan, Silakan login kembali untuk melanjutkan."
        return redirect(url_for("login", msg=msg))


# ROUTE ARTWORK DETAIL
@app.route('/artwork/detail', methods=["GET"])
def artwork_detail():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})

        id = request.args.get("id")
        artwork = db.artwork.find_one({"_id": ObjectId(id)})
        
        if artwork:
                artwork["_id"] = str(artwork["_id"])
                return render_template('fans/artwork_detail.html', artwork=artwork, user_info=user_info)
        else:
            return "Tidak ada artwork dengan url tersebut"
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = "Terjadi kesalahan, Silakan login kembali untuk melanjutkan."
        return redirect(url_for("login", msg=msg))

# ------------------------------------ ADMIN ---------------------------------------------------

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
    

@app.route('/artist')
def artists():
    return render_template('fans/artist.html')

@app.route('/artist/<artist_id>')
def artist_detail(artist_id):
    artist_data = db.artist_collection.find_one({'_id': artist_id})
    return render_template('artist_detail.html', artist_id=artist_id, artist_data=artist_data)
    
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
