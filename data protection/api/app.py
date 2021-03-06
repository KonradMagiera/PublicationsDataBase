from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, make_response, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from Crypto.Hash import SHA256
import os
from os.path import isfile, join
from uuid import uuid4
import jwt
import json
from dotenv import load_dotenv
import time
from flask_cors import CORS, cross_origin
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


app = Flask(__name__)

if __name__ == "__main__":
	app.run(threaded=True)
# CONFIG
load_dotenv(verbose=True)
JWT_SECRET = os.getenv("JWT_SECRET")
REQUEST_CREDENTIALS_EXPIRE = int(os.getenv("REQUEST_CREDENTIALS_EXPIRE"))
sessions = []
users_notification = {}
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
db = SQLAlchemy(app)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per minute", "10000 per day"]
)

# DATABASE MODEL
class Publication(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(256), unique=True, nullable=False)
	author = db.Column(db.String(128), unique=False, nullable=False)
	publisher = db.Column(db.String(128), unique=False, nullable=False)
	user = db.Column(db.String(32), unique=False, nullable=False)
	pub_date = db.Column(db.DateTime, default=datetime.now, unique=False, nullable=True)


	def __init__(self, title, author, publisher, user, pub_date=None, id=None):
		self.id = id
		self.title = title
		self.author = author
		self.publisher = publisher
		self.user = user
		self.pub_date = pub_date

	def get_all(self):
		data = {
			"id": self.id,
			"title": self.title,
			"author": self.author,
			"publisher": self.publisher,
			"user": self.user,
			"pub_date": self.pub_date
		}
		return data
	
	def update(self, title=None, author=None, publisher=None, pub_date=None, filename=None):
		if(title):
			self.title = title
		if(author):
			self.author = author
		if(publisher):
			self.publisher = publisher
		if(pub_date):
			self.pub_date = pub_date
		if(filename):
			self.filename = filename

class File(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	pub_id = db.Column(db.Integer, unique=False, nullable=False)
	filename = db.Column(db.String(128), unique=False, nullable=False)

	def __init__(self, pub_id, filename, id=None):
		self.id = id
		self.pub_id = pub_id
		self.filename = filename

	def get_all(self):
		data = {
			"id": self.id,
			"pub_id": self.pub_id,
			"filename": self.filename
		}
		return data

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	user = db.Column(db.String(32), unique=True, nullable=False)
	password = db.Column(db.String(256), unique=False, nullable=False) # SHA256

	def update(self, password=None):
		if(password):
			self.password = password

db.create_all()

# FILL DATABASE

# USERS
try:
	user = User(user="admin", password="b52a4d33ca7c889a9b28b943689cd6f736cbd7aecd914fa05d289cd3bf41c870")
	db.session.add(user)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	user = User(user="magierak", password="255fb40109088f421f619be50a7aa601db89df34a662e9695d123bba8f70c401")
	db.session.add(user)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

# PUBLICATIONS
try:
	pub = Publication(title="Title", author="Author", publisher="Publisher", user="admin")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title1", author="Author1", publisher="Publisher1", user="admin")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="MG", author="Grażyna", publisher="Publisher2", user="magierak")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="MG2", author="Janusz", publisher="Publisher1", user="magierak")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title2", author="Author2", publisher="Publisher2", user="admin")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

#######

@app.route("/event/<username>")
@cross_origin()
def event(username):
	def event_stream():
		if(username in users_notification):
			msg = users_notification[username]
			yield 'data: %s\n\n' % msg
		else:
			yield 'data: \n\n'
		time.sleep(3)
		if(username in users_notification):
			users_notification[username] = ""
	return Response(event_stream(), mimetype="text/event-stream")


@app.route("/login", methods=["POST"])
def login():
	token_decode = request.headers.get("Authorization")
	try:	
		token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm="HS256")
	except jwt.ExpiredSignatureError:
		msg = {"message": "token expired"}
		return jsonify(msg), 401

	if(("username" not in token_decode) and ("password" not in token_decode)):
		msg = {"message": "Missing valid credentials"}
		return jsonify(msg), 401

	user = token_decode["username"]
	password = token_decode["password"]
	password = hashString(password, 100)
	user_db = User.query.filter_by(user=user).first()
	if(user_db == None):
		msg = {"message": "incorrect username or password"}
		return jsonify(msg), 401
	elif(user_db.password == password):
		session = str(uuid4())
		sessions.append({"user": user, "session_id": session})
		if(user not in users_notification):
			users_notification[user] = ""

		resp = make_response("logged in", 200)
		token = {"session_id": session, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
		token = jwt.encode(token, JWT_SECRET, algorithm="HS256")
		resp.headers["Authorization"] = token
		return resp
	else:
		msg = {"message": "incorrect username or password"}
		return jsonify(msg), 401

@app.route("/logout", methods=["POST"])
def logout():
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status
	for u in sessions:
		if((u["user"] == token_decode["username"]) and (u["session_id"] == token_decode["session_id"])):
			sessions.remove(u)
			break
	user_logged_in = False
	for u in sessions:
		if(u["user"] == token_decode["username"]):
			user_logged_in = True
			break
	if(not user_logged_in):
		del users_notification[token_decode["username"]]
	msg = {"message": "logged out"}
	return jsonify(msg), 200


@app.route("/register", methods=["POST"])
def register():
	token_decode = request.headers.get("Authorization")
	try:	
		token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm="HS256")
	except jwt.ExpiredSignatureError:
		msg = {"message": "token expired"}
		return jsonify(msg), 401
	username = token_decode["username"]
	password = token_decode["password"]
	if(not verify_password(password)):
		msg = {"message": "Password is too weak"}
		return jsonify(msg), 401
	user_db = User.query.filter_by(user=username).first()
	if(user_db != None):
		msg = {"message": "User already exists"}
		return jsonify(msg), 401
	try:
		password = hashString(password, 120)
		new_user = User(user=username, password=password)
		db.session.add(new_user)
		db.session.commit()
		msg = {"message": "User created"}
		return jsonify(msg), 201
	except IntegrityError:
		db.session.rollback()
		msg = {"message": "Unexpected error"}
		return jsonify(msg), 401

@app.route("/change_password", methods=["PUT"])
def change_password():
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status
	user_db = User.query.filter_by(user=token_decode["username"]).first()
	if(user_db == None):
		msg = {"message": "incorrect username or password"}
		return jsonify(msg), 401
	else:
		password = hashString(token_decode["old_password"], 120)
		if(user_db.password != password):
			msg = {"message": "incorrect username or password"}
			return jsonify(msg), 401
		if(not verify_password(token_decode["new_password"])):
			msg = {"message": "Password is too weak"}
			return jsonify(msg), 401
		new_password = hashString(token_decode["new_password"], 120)
		user_db.update(password=new_password)
		try:
			db.session.commit()
			msg = {"message": "password changed"}
			return jsonify(msg), 200
		except IntegrityError:
			db.session.rollback()
			msg = {"message": "database error"}
			return jsonify(msg), 401

@app.route("/", methods=["GET"])
@app.route("/publications", methods=["GET"])
def publications():
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	user = token_decode["username"]
	publ = Publication.query.filter_by(user=user).all()
	tmp_pub = list()
	for p in publ:
		tmp_pub.append(p.get_all())
	data = { "publication": tmp_pub }
	return jsonify(data), 200

@app.route("/", methods=["POST"])
@app.route("/publications", methods=["POST"])
def publications_add():
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	data = request.get_json()
	if(("title" not in data) or ("author" not in data) or ("publisher" not in data)):
		msg = {"message": "publication's information not provided"}
		return jsonify(msg), 401
	
	pub = Publication.query.filter_by(title=data["title"]).first()
	if(pub != None):
		msg = {"message": "publication exists"}
		return jsonify(msg), 401
	
	id = None
	try:
		pub = None
		if(("date" in data) and data["date"] != ""):
			format_str = "%Y-%m-%d"
			datetime_obj = datetime.strptime(data["date"], format_str)
			pub = Publication(title=data["title"], author=data["author"], publisher=data["publisher"], user=token_decode["username"], pub_date=datetime_obj)
			db.session.add(pub)
			db.session.commit()
		else:
			pub = Publication(title=data["title"], author=data["author"], publisher=data["publisher"], user=token_decode["username"])
			db.session.add(pub)
			db.session.commit()
		id = pub.get_all()
		id = id["id"]
	except IntegrityError:
		db.session.rollback()

	if(id == None):
		msg = {"message": "add failed"}
		return jsonify(msg), 401
	else:
		msg = {"message": "publication added", "id": id}
		users_notification[token_decode["username"]] = "Publication '%s' added!" % data["title"]
		return jsonify(msg), 201

@app.route("/publications/<pid>", methods=["GET"])
def publicationspid(pid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	publ = Publication.query.filter_by(id=pid, user=token_decode["username"]).first()
	tmp_pub = list()
	tmp_pub.append(publ.get_all())
	data = { "publication": tmp_pub }
	return jsonify(data), 200

@app.route("/publications/<pid>", methods=["PUT"])
def publications_id_update(pid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	data = request.get_json()
	if(("id" not in data) or ("title" not in data) or ("author" not in data) or ("publisher" not in data)):
		msg = {"message": "publication's info not provided"}
		return jsonify(msg), 401
	pub = Publication.query.filter_by(id=data["id"], user=token_decode["username"]).first()
	if(pub == None):
		msg = {"message": "publication doesnt exists"}
		return jsonify(msg), 401
	date = None
	if(data["date"] != ""):
		format_str = "%Y-%m-%d"
		date = datetime.strptime(data["date"], format_str)
	pub.update(title=data["title"], author=data["author"], publisher=data["publisher"], pub_date=date)
	msg = {"message": "Before commit"}
	try:
		db.session.commit()
		msg = {"message": "succesfully updated"}
		return jsonify(msg), 200
	except IntegrityError:
		db.session.rollback()
		msg = {"message": "title already exists"}
		return jsonify(msg), 401

@app.route("/publications/<pid>", methods=["DELETE"])
def publications_id_delete(pid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	pubquery = Publication.query.filter_by(id=pid, user=token_decode["username"])
	if(pubquery.count() != 1):
		msg = {"message": f"publication with id {pid} doesnt exist"}
		return jsonify(msg), 401
	delete_all_pub_files(pid)	
	try:
		pubquery.delete()
		db.session.commit()
		msg = {"message": "Successfully deleted"}
		return jsonify(msg), 200
	except IntegrityError:
		db.session.rollback()
		msg = {"message": "Failed to delete"}
		return jsonify(msg), 401

@app.route("/publications/<pid>/files", methods=["GET"])
def publicationspid_files(pid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	files = File.query.filter_by(pub_id=pid).all()
	tmp_files = list()
	for f in files:
		tmp_files.append(f.get_all())
	data = { "publication": tmp_files }
	return jsonify(data), 200

@app.route("/publications/<pid>/files", methods=["POST"])
def files_add(pid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status


	files = request.files.get("file")
	extension = files.filename.split(".")[-1]
	msg = {"message": "before save"}
	if files and extension == "pdf":
		filepath = os.path.join(app.config["UPLOAD_FOLDER"])
		if not os.path.exists(filepath):
			os.mkdir(filepath)
		filepath = os.path.join(app.config["UPLOAD_FOLDER"], pid)
		if not os.path.exists(filepath):
			os.mkdir(filepath)
		filepath = os.path.join(filepath, files.filename)

		pub = Publication.query.filter_by(id=pid).first()
		if(pub == None):
			msg = {"message": "publication not found"}
			return jsonify(msg), 404

		filequery = File.query.filter_by(pub_id=int(pid), filename=files.filename).first()
		if(filequery != None):
			msg = {"message": "file with specific name has already been added to publication"}
			return jsonify(msg), 401
		try:
			filequery = File(filename=files.filename, pub_id=int(pid))
			db.session.add(filequery)
			db.session.commit()
			files.save(filepath)
			msg = {"message": "file added"}
			return jsonify(msg), 201
		except IntegrityError:
			db.session.rollback()
			msg = {"message": "error while saving file"}
			return jsonify(msg), 409
	else:
		msg = {"message": "file is not a pdf"}
		return jsonify(msg), 415

@app.route("/publications/<pid>/files/<fid>", methods=["GET"])
def filesfid(pid, fid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status

	files = File.query.filter_by(id=fid, pub_id=pid).first()
	if(files == None):
		msg = {"message": "Could not find file for given ids"}
		return jsonify(msg), 401
	
	filename = files.get_all()
	filename = filename["filename"]
	filepath = app.config["UPLOAD_FOLDER"]
	filepath = os.path.join(filepath, pid)
	filepath = os.path.join(filepath, filename)
	send = send_file(filepath, attachment_filename=filename, as_attachment=True)
	return send, 200

@app.route("/publications/<pid>/files/<fid>", methods=["DELETE"])
def file_delete(pid, fid):
	token_decode = request.headers.get("Authorization")
	token_decode, status = validate_token(token_decode)
	if(status != 200):
		return token_decode, status
	
	filequery = File.query.filter_by(id=fid, pub_id=pid)
	if(filequery.count() != 1):
		msg = {"messaage": "file not found"}
		return jsonify(msg), 401
	try:
		filepath = os.path.join(app.config["UPLOAD_FOLDER"], pid)
		files = File.query.filter_by(id=fid, pub_id=pid).first()
		files = files.get_all()
		filepath = os.path.join(filepath, files["filename"])
		filequery.delete()
		db.session.commit()
		msg = {"message": "Successfully deleted"}
		os.remove(filepath)
		return jsonify(msg), 200
	except IntegrityError:
		db.session.rollback()
		msg = {"message": "Failed to delete"}
		return jsonify(msg), 401

def delete_all_pub_files(pid):
	files = File.query.filter_by(pub_id=pid).all()
	file_ids = list()
	filenames = list()
	for f in files:
		tmp = f.get_all()
		file_ids.append(tmp["id"])
		filenames.append(tmp["filename"])
	for fid, filename in zip(file_ids, filenames):
		filequery = File.query.filter_by(id=int(fid), pub_id=int(pid))
		if(filequery.count() != 1):
			msg = {"message": "file not found"}
			return jsonify(msg), 401
		filepath = os.path.join(app.config["UPLOAD_FOLDER"], str(pid))
		filepath = os.path.join(filepath, filename)
		try:
			filequery.delete()
			db.session.commit()
			msg = {"message": "Successfully deleted"}
			os.remove(filepath)
		except:
			db.session.rollback()
			msg = {"message": "Failed to delete"}
			return jsonify(msg), 401

def validate_token(token):
	token_decode = token
	try:	
		token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm="HS256")
	except jwt.ExpiredSignatureError:
		msg = {"message": "token expired"}
		return jsonify(msg), 401

	if(("username" not in token_decode) or ("session_id" not in token_decode)):
		msg = {"message": "not authorized connection"}
		return jsonify(msg), 401

	for u in sessions:
		if((u["user"] == token_decode["username"]) and (u["session_id"] == token_decode["session_id"])):
			return token_decode, 200
	msg = {"message": "validation error"}
	return jsonify(msg), 401

def hashString(password, num):
	new_password = password
	for i in range(0, num):
		new_password = str.encode(new_password)
		new_password = SHA256.new(new_password)
		new_password = new_password.hexdigest()
	return new_password

def verify_password(password):
	pattern = re.compile("""(?=^.{8,20}$)(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&amp;*()_+}{&quot;:;"?&gt;.&lt;,])(?!.*\s).*$""")
	print(password, flush=True)
	if(pattern.match(password) == None):
		return False
	return True
	