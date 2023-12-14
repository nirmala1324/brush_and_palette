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
from werkzeug.utils import secure_filename
import random
import string

import os
from datetime import datetime, timedelta
from os.path import dirname, join

import jwt
from dotenv import load_dotenv

app = Flask(__name__)

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")
SECRET_KEY = os.environ.get("SECRET_KEY")
TOKEN_KEY_ADMIN = os.environ.get("TOKEN_KEY_ADMIN")
TOKEN_KEY_FANS = os.environ.get("TOKEN_KEY_FANS")

conn = MongoClient(MONGODB_URI)
db = conn[DB_NAME]

@app.route("/", methods=["GET"])
def home():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
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

# ROUTE ARTWORK
@app.route("/artwork", methods=["GET"])
def get_artwork():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
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
@app.route("/artwork/detail", methods=["GET"])
def artwork_detail():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})

        id = request.args.get("id")
        artwork = db.artwork.find_one({"_id": ObjectId(id)})

        if artwork:
            artwork["_id"] = str(artwork["_id"])
            return render_template(
                "fans/artwork_detail.html", artwork=artwork, user_info=user_info
            )
        else:
            return "Tidak ada artwork dengan url tersebut"

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = "Terjadi kesalahan, Silakan login kembali untuk melanjutkan."
        return redirect(url_for("login", msg=msg))


# ROUTE ARTWORK REVIEW
@app.route("/artwork/review", methods=["GET", "POST"])
def artwork_review():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})

        if request.method == "GET":
            artwork_id = request.args.get("id")
            artwork = db.artwork.find_one({"_id": ObjectId(artwork_id)})
            if artwork:
                comments = db.comments.find({"artwork_id": artwork_id}).sort(
                    "timestamp", -1
                )
                return render_template(
                    "fans/review.html",
                    artwork=artwork,
                    comments=comments,
                    user_info=user_info,
                )
            else:
                return "Tidak ada artwork dengan ID tersebut"

        elif request.method == "POST":
            current_time = datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
            artwork_id = request.form.get("artwork_id")
            comment_text = request.form.get("comment_text")
            db.comments.insert_one(
                {
                    "artwork_id": artwork_id,
                    "comment": comment_text,
                    "user_id": user_info["_id"],
                    "username": user_info["username"],
                    "timestamp": formatted_time,
                }
            )
            return redirect(url_for("artwork_review", id=artwork_id))

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = "Terjadi kesalahan, Silakan login kembali untuk melanjutkan."
        return redirect(url_for("login", msg=msg))

# ROUTE BUY ARTWORK
@app.route('/artwork/checkout')
def artwork_checkout():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})
        
        artwork_id = request.args.get("id")
        artwork = db.artwork.find_one({"_id": ObjectId(artwork_id)})
        
        if artwork:
            return render_template('fans/buy_artwork.html', artwork=artwork, user_info=user_info)        
            
        else:
            return "Tidak ada artwork dengan ID tersebut"
        
        
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = "Terjadi kesalahan, Silakan login kembali untuk melanjutkan."
        return redirect(url_for("login", msg=msg))
    
@app.route('/api/save_order', methods=['POST'])
def save_order():
    data_order = request.form.to_dict()
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_order['timestamp'] = formatted_time
    
    if 'unit' in data_order:
        data_order['unit'] = int(data_order['unit'])
        
    db.purchases.insert_one(data_order)
    
    unit = data_order.get('unit', 0)
    artwork_id = data_order.get('artwork_id')
    artwork_data = db.artwork.find_one({'_id': ObjectId(artwork_id)})
    
    if artwork_data:
        stock = artwork_data.get('stock', 0) - unit
        print('quantity - artwork_data = ', artwork_data)
        
        # Perbarui nilai 'quantity' di koleksi 'artwork'
        db.artwork.update_one({}, {"$set": {'stock': stock}})
    return jsonify({'message': 'Terima kasih! pembelian berhasil.'}), 200

# ROUTE CHECKOUT DETAIL
@app.route("/artwork/checkout/detail", methods=["GET", "POST"])
def checkout_detail():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user_login.find_one({"username": payload.get("id")})
        
        artwork_id = request.args.get("id")
        artwork = db.artwork.find_one({"_id": ObjectId(artwork_id)})
        
        if artwork:
            purchases = db.purchases.find({
                "username": user_info['username'],
                "artwork_id": artwork_id
            }).sort([("_id", -1)]).limit(1)
            
            return render_template('fans/checkout_detail.html', purchases=purchases, user_info=user_info, artwork=artwork)
            
        else:
            return "Tidak ada data pembelian dengan parameter tersebut"

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
    token_receive = request.cookies.get(TOKEN_KEY_ADMIN)
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
    token_receive = request.cookies.get(TOKEN_KEY_ADMIN)
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
        artists = db.artist.find({})
        msg = request.args.get('msg') 
        """ length = 3
        random_id = ''.join(random.choice(string.ascii_lowercase) for _ in range(length)) """
        return render_template('admin/menu_artwork.html', user_info = user_info, datas = artworks, artists = artists, msg = msg)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin_login'))
    
@app.route('/admin/artist')
def menu_artist():
    token_receive = request.cookies.get(TOKEN_KEY_ADMIN)
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
        artist = db.artist.find({})
        msg = request.args.get('msg') 
        return render_template('admin/menu_artist.html', user_info = user_info, datas = artist, msg = msg)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for('admin_login'))
    

@app.route('/admin')
def admin():
    token_receive = request.cookies.get(TOKEN_KEY_ADMIN)
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
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        return jsonify({"result": "success", "token":token})
    else:
        return jsonify({
            "result": "fail",
            "msg": "We could not found admin data with that that username/ password combination"
        })

def generate_random_id(length=4):
    random_id = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
    return random_id

# TAMBAH ARTWORK
@app.route('/tambah_artwork', methods=["POST"])
def tambah_artwork():
    token_receive = request.cookies.get(TOKEN_KEY_ADMIN)
    try: 
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        # Retrieve data given from client
        artistID_receive = request.form.get('artistID_give')
        artist = ObjectId(artistID_receive)
        artworkTitle_receive = request.form.get('artworkTitle_give')
        artworkDesc_receive = request.form.get('artworkDesc_give')
        artworkPrice_receive = int(request.form.get('artworkPrice_give'))
        artworkStock_receive = int(request.form.get('artworkStock_give'))
        # Randomize ID for Artwork
        artworkId = "AW_" + generate_random_id()
        artistName_db = db.artist.find_one({'_id': artist}, {'fullname': 1, '_id': 0})
        artistName = artistName_db['fullname']
        # Insert data inside new_doc
        new_doc = {
            'artwork_id': artworkId,
            'artist': artistName,
            'title': artworkTitle_receive,
            'artist_id': artist,
            'desc': artworkDesc_receive,
            'price': artworkPrice_receive,
            'stock': artworkStock_receive,
        }
        # Get the photo data
        if 'artworkPhoto_give' in request.files:
            file = request.files.get('artworkPhoto_give')
            filename = secure_filename(file.filename)
            # extract extension file
            extension = filename.split('.')[-1] # get value split first from the back(?)
            file_path = f'admin/artwork/{artworkId}.{extension}'
            file.save('./static/' + file_path)
            new_doc['photo'] = filename
            new_doc['photo_real'] = file_path
        db.artwork.insert_one(new_doc)
        return jsonify({
            'result': 'success',
            'msg': 'An artwork (' + artworkTitle_receive + ') successfully added!'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = 'You need to log in'
        return redirect(url_for('admin_login', msg = msg))
    
# EDIT ARTWORK
@app.route('/admin/artwork/edit', methods = ['POST'])
def edit_artwork():
    artID_receive = request.form['artworkID']
    artTitle_receive = request.form['editArtTitle']
    artDesc_receive = request.form['editArtDesc']
    artPrice_receive = int(request.form['editArtPrice'])
    artStock_receive = int(request.form['editArtStock'])
    artPrevPhoto_receive = request.form['artworkPhoto']
    artNewPhoto_receive = request.files['editArtPhoto']
    prev_file_path = './static/' + artPrevPhoto_receive
    # creating document
    new_doc = {
        'title': artTitle_receive,
        'desc': artDesc_receive,
        'price': artPrice_receive,
        'stock': artStock_receive
    }
    if artNewPhoto_receive:
        if os.path.exists(prev_file_path):
            os.remove('./static/' + artPrevPhoto_receive)
        file = artNewPhoto_receive
        filename = secure_filename(file.filename)
        # extract extension file
        extension = filename.split('.')[-1] # get value split first from the back(?)
        file_path = f'admin/artwork/{artID_receive}.{extension}'
        file.save('./static/' + file_path)
        new_doc['photo'] = filename
        new_doc['photo_real'] = file_path
    db.artwork.update_one(
        {'artwork_id' : artID_receive},
        {'$set': new_doc} # let user know how to do update
    )
    msg = 'Artwork '+ artID_receive +' successfully updated'
    return redirect(url_for('menu_artwork', msg = msg))

@app.route('/admin/artwork/delete', methods = ['POST'])
def delete_artwork():
    photo = request.form['photo']
    artworkID = request.form['idDelete']
    os.remove('./static/' + photo)
    db.artwork.delete_one({'artwork_id':artworkID})
    msg = 'Artwork '+ artworkID +' successfully deleted'
    return redirect(url_for('menu_artwork', msg = msg))

# TAMBAH ARTWORK
@app.route('/tambah_artist', methods=["POST"])
def tambah_artist():
    token_receive = request.cookies.get(TOKEN_KEY_ADMIN)
    try: 
        payload = jwt.decode(
            token_receive,
            SECRET_KEY,
            algorithms=['HS256']
        )
        # Retrieve data given from client
        artistFullname_receive = request.form.get('artistFullname_give')
        artistDesc_receive = request.form.get('artistDesc_give')
        artistEmail_receive = request.form.get('artistEmail_give')
        artistAcc_receive = request.form.get('artistAcc_give')
        artistBank_receive = request.form.get('artistBank_give')
        bankAccount = artistAcc_receive + '(' + artistBank_receive + ')'
        # Randomize ID for Artwork
        artistId = "A_" + generate_random_id()
        # Insert data inside new_doc
        new_doc = {
            'artist_id': artistId,
            'fullname': artistFullname_receive,
            'desc': artistDesc_receive,
            'email': artistEmail_receive,
            'bank': bankAccount,
        }
        # Get the photo data
        if 'artistPhoto_give' in request.files:
            file = request.files.get('artistPhoto_give')
            filename = secure_filename(file.filename)
            # extract extension file
            extension = filename.split('.')[-1] # get value split first from the back(?)
            file_path = f'admin/artist/{artistId}.{extension}'
            file.save('./static/' + file_path)
            new_doc['photo'] = filename
            new_doc['photo_real'] = file_path
        db.artist.insert_one(new_doc)
        return jsonify({
            'result': 'success',
            'msg': 'An artist (' + artistFullname_receive + ') successfully added!'
        })
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        msg = 'You need to log in'
        return redirect(url_for('admin_login', msg = msg))

# EDIT ARTIST
@app.route('/admin/artist/edit', methods = ['POST'])
def edit_artist():
    artistID_receive = request.form['artistID']
    artistFullname_receive = request.form['editArtistFullname']
    artistDesc_receive = request.form['editArtistDesc']
    artistEmail_receive = request.form['editArtistEmail']
    artistAcc_receive = request.form['editArtistAcc']
    artistBank_receive = request.form['editArtistBank']
    artistBank = artistAcc_receive + ' ('+ artistBank_receive +')'
    artistPrevPhoto_receive = request.form['artistPhoto']
    artistNewPhoto_receive = request.files['editArtistPhoto']
    prev_file_path = './static/' + artistPrevPhoto_receive
    # creating document
    new_doc = {
        'fullname': artistFullname_receive,
        'desc': artistDesc_receive,
        'email': artistEmail_receive,
        'bank': artistBank
    }
    if artistBank_receive:
        artistBank = artistAcc_receive + ' ('+ artistBank_receive +')'
        new_doc['bank'] = artistBank

    if artistNewPhoto_receive:
        if os.path.exists(prev_file_path):
            os.remove(prev_file_path)
        file = artistNewPhoto_receive
        filename = secure_filename(file.filename)
        # extract extension file
        extension = filename.split('.')[-1] # get value split first from the back(?)
        file_path = f'admin/artwork/{artistID_receive}.{extension}'
        file.save('./static/' + file_path)
        new_doc['photo'] = filename
        new_doc['photo_real'] = file_path
    db.artist.update_one(
        {'artist_id' : artistID_receive},
        {'$set': new_doc} # let user know how to do update
    )
    msg = 'Artwork '+ artistID_receive +' successfully updated'
    return redirect(url_for('menu_artwork', msg = msg))

@app.route('/admin/artist/delete', methods = ['POST'])
def delete_artist():
    artistID = request.form['idDelete']
    photo = request.form['photo']
    os.remove('./static/' + photo)
    db.artist.delete_one({'artist_id':artistID})
    msg = 'Artist'+ artistID +' successfully deleted'
    return redirect(url_for('menu_artist', msg = msg))

# --------------------------------------------------------------------------------

# ARTIST FANS

@app.route('/artist')
def artists():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)

    artists_data = list(db.artist.find({}, {'_id': 1, 'fullname': 1, 'photo': 1}))  

    return render_template('fans/artist.html', artists_data=artists_data)

@app.route('/artist/<artist_id>')
def artist_detail(artist_id):
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        artists_data = list(db.artist.find({}, {'_id': 1, 'fullname': 1}))  
        artist_data = db.artist.find_one({'_id': ObjectId(artist_id)}, {'_id': 1, 'fullname': 1, 'desc': 1, 'photo': 1})
        artworks = list(db.artwork.find({'artist_id': ObjectId(artist_id)}, {'photo': 1, 'title': 1, 'price': 1}))
        if artist_data:
            return render_template('fans/artist_detail.html', artist_data=artist_data, artworks=artworks, artists_data=artists_data)
        else:
            return "Artist data not found"

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))

    
    

##profile

@app.route('/fans/profile')
def fans_profile():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        user_info = db.user_login.find_one({"username": username})
        user_purchases = db.purchases.find({"username": username})  

        return render_template('fans/profile.html', user_login=user_info, user_info=user_info, purchases=user_purchases)

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("nama_fungsi_lain"))



@app.route("/update_profile", methods=["POST"])
def save_img():
    token_receive = request.cookies.get(TOKEN_KEY_FANS)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        name_receive = request.form["name_give"]
        phone_receive = request.form["phone_give"]
        alamat_receive = request.form["alamat_give"]

    
        if "file_give" in request.files:
            file = request.files["file_give"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                extension = filename.split(".")[-1]
                file_path = f"{username}.{extension}"
                file.save(os.path.join("./static/fans/profile", file_path))

                profile_pic_path = file_path
            else:
                profile_pic_path = db.user_login.find_one({"username": username}, {"profile_pic_real": 1})["profile_pic_real"]

            
            db.user_login.update_one(
                {"username": username},
                {
                    "$set": {
                        "name": name_receive,
                        "alamat": alamat_receive,  
                        "phone": phone_receive,
                        "profile_pic_real": profile_pic_path
                    }
                }
            )

            return jsonify({"result": "success", "msg": "Profile updated!"})
        else:
            return jsonify({"result": "failed", "msg": "No file provided!"}), 400

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("fans/profile"))



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
