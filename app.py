import hashlib
import os
from datetime import datetime, timedelta
from os.path import dirname, join

import jwt
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from pymongo import MongoClient

app = Flask(__name__)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")

SECRET_KEY = os.environ.get("SECRET_KEY")

conn = MongoClient(MONGODB_URI)
db = conn[DB_NAME]

TOKEN_KEY = os.environ.get("TOKEN_KEY")


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
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
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



if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
