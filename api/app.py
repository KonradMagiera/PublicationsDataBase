from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, make_response
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


app = Flask(__name__)

# CONFIG
load_dotenv(verbose=True)
#UPLOAD_TIME = int(os.getenv("UPLOAD_TIME"))
#DOWNLOAD_TIME = int(os.getenv("DOWNLOAD_TIME"))
JWT_SECRET = os.getenv("JWT_SECRET")
LOGIN_EXPIRE = int(os.getenv('LOGIN_EXPIRE'))

app.config['SESSION_ID'] = ''
app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///db.sqlite3"
db = SQLAlchemy(app)

# DATABASE MODEL
class Publication(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(256), unique=True, nullable=False)
	author = db.Column(db.String(128), unique=False, nullable=False)
	publisher = db.Column(db.String(128), unique=False, nullable=False)
	user = db.Column(db.String(32), unique=False, nullable=False)
	filename = db.Column(db.String(128), unique=False, nullable=True)
	pub_date = db.Column(db.DateTime, default=datetime.now, unique=False, nullable=True)


	def __init__(self, title, author, publisher, user, filename=None, pub_date=None, id=None):
		self.id = id
		self.title = title
		self.author = author
		self.publisher = publisher
		self.user = user
		self.filename = filename
		self.pub_date = pub_date

	def get_all(self):
		data = {
			"id": self.id,
			"title": self.title,
			"author": self.author,
			"publisher": self.publisher,
			"user": self.user,
			"filename": self.filename,
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

db.create_all()

# FILL DATABASE
try:
	user = User(user="admin", password="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918")
	db.session.add(user)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	user = User(user="magierak", password="430afa184d6e53861cecbac329560e11800b0bbbe48be6aa3a3e206b78ace691")
	db.session.add(user)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title", author="Author", publisher="Publisher", user="admin", filename="Filename")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title1", author="Author1", publisher="Publisher1", user="admin", filename="Filename1")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title2", author="Author2", publisher="Publisher2", user="magierak", filename="Filename2")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title3", author="Author", publisher="Publisher1", user="magierak", filename="Filename3")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

try:
	pub = Publication(title="Title4", author="Author2", publisher="Publisher2", user="admin", filename="Filename4")
	db.session.add(pub)
	db.session.commit()
except IntegrityError:
	db.session.rollback()

#######

@app.route('/login', methods=['POST'])
def login():
	token_decode = request.headers.get('Authorization')
	try:	
		token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm='HS256')
	except jwt.ExpiredSignatureError:
		msg = {"message": "token expired"}
		return jsonify(msg), 401

	if(('username' not in token_decode) and ('password' not in token_decode)):
		msg = {'message': 'Missing valid credentials'}
		return jsonify(msg), 401

	user = token_decode['username']
	password = token_decode['password']
	password = str.encode(password)
	password = SHA256.new(password)
	password = password.hexdigest()
	user_db = User.query.filter_by(user=user).first()
	if(user_db == None):
		msg = {"message": "incorrect username or password"}
		return jsonify(msg), 401
	elif(user_db.password == password):
		app.config['SESSION_ID'] = str(uuid4())
		resp = make_response('logged in', 200)
		token = {"session_id": app.config['SESSION_ID'], "exp": datetime.now() + timedelta(seconds=LOGIN_EXPIRE)}
		token = jwt.encode(token, JWT_SECRET, algorithm='HS256')
		resp.headers['Authorization'] = token
		return resp
	else:
		msg = {"message": "incorrect username or password"}
		return jsonify(msg), 401

@app.route('/logout', methods=['POST'])
def logout():
	data = request.get_json()
	if("username" in data):
		app.config['SESSION_ID'] = ''
		return "logged out", 200
	elif("username" not in data):
		return "logged out with troubles", 200
	else:
		return "unexpected error", 500

@app.route('/', methods=['GET'])
@app.route('/publications', methods=['GET'])
def publications():
	data = request.get_json()
	#JWT
	if('username' not in data):
		data = {"message": "username was not provided"}
		return jsonify(data), 401
	user = data['username']
	publ = Publication.query.filter_by(user=user).all()
	tmp_pub = list()
	for p in publ:
		tmp_pub.append(p.get_all())
	data = { "publication": tmp_pub }
	return jsonify(data), 200

@app.route('/', methods=['POST'])
@app.route('/publications', methods=['POST'])
def publications_add():
	#JWT
	data = request.get_json() #username, jwt, author, publisher, title
	if(("username" not in data) or ("title" not in data) or ("author" not in data) or ("publisher" not in data)):
		msg = {"message": "missing json parameters"}
		return jsonify(msg)
	
	pub = Publication.query.filter_by(title=data['title']).first()
	if(pub != None):
		msg = {"message": "publication exists"}
		return jsonify(msg), 401
	
	error = False
	id = None
	try:
		pub = None
		if(("date" in data) and data['date'] != ''):
			format_str = '%Y-%m-%d'
			datetime_obj = datetime.strptime(data['date'], format_str)
			pub = Publication(title=data['title'], author=data['author'], publisher=data['publisher'], user=data['username'], pub_date=datetime_obj)
			db.session.add(pub)
			db.session.commit()
		else:
			pub = Publication(title=data['title'], author=data['author'], publisher=data['publisher'], user=data['username'])
			db.session.add(pub)
			db.session.commit()
		id = pub.get_all()
		id = id['id']
	except IntegrityError:
		error = True
		db.session.rollback()

	msg = {}
	if(error):
		msg = {"message": "add failed"}
		return jsonify(msg), 401
	else:
		msg = {"message": "publication added", "id": id}
		return jsonify(msg), 201

@app.route('/publications/<pid>', methods=['GET'])
def publicationspid(pid):
	data = request.get_json()
	#JWT
	if("username" not in data):
		data = {"error": "username not provided"}
		return jsonify(data), 401
	publ = Publication.query.filter_by(id=pid, user=data['username']).first()
	tmp_pub = list()
	tmp_pub.append(publ.get_all())
	data = { "publication": tmp_pub }
	return jsonify(data), 200

@app.route('/publications/<pid>', methods=['PUT'])
def publications_id_update(pid):
	data = request.get_json()
	if(('id' not in data) or ('username' not in data) or ("title" not in data) or ("author" not in data) or ("publisher" not in data)):
		msg = {"message": "id not provided"}
		return jsonify(msg), 401
	pub = Publication.query.filter_by(id=data['id'], user=data['username']).first()
	if(pub == None):
		msg = {"message": "publication doesnt exists"}
		return jsonify(msg), 401
	date = None
	if(data['date'] != ''):
		format_str = '%Y-%m-%d'
		date = datetime.strptime(data['date'], format_str)
	pub.update(title=data['title'], author=data['author'], publisher=data['publisher'], pub_date=date)
	msg = {"message": "Before commit"}
	try:
		db.session.commit()
		msg = {"message": "succesfully updated"}
		return jsonify(msg), 200
	except IntegrityError:
		db.session.rollback()
		msg = {"message": "title already exists"}
		return jsonify(msg), 401

@app.route('/publications/<pid>', methods=['DELETE'])
def publications_id_delete(pid):
	data = request.get_json()
	#JWT
	if('username' not in data):
		msg = {"message": "Misisng id or username"}
		return jsonify(msg), 401
	pubquery = Publication.query.filter_by(id=pid, user=data['username'])
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

@app.route('/publications/<pid>/files', methods=['GET'])
def publicationspid_files(pid):
	data = request.get_json()
	if("username" not in data):
		msg = {"message": "user not specified"}
		return jsonify(msg), 401
	files = File.query.filter_by(pub_id=pid).all()
	tmp_files = list()
	for f in files:
		tmp_files.append(f.get_all())
	data = { "publication": tmp_files }
	return jsonify(data), 200

@app.route('/publications/<pid>/files', methods=['POST'])
def files_add(pid):
	files = request.files.get('file')
	extension = files.filename.split(".")[-1]
	msg = {"message": "before save"}
	if files and extension == 'pdf':
		filepath = os.path.join(app.config['UPLOAD_FOLDER'], pid)
		if not os.path.exists(filepath):
			os.mkdir(filepath)
		filepath = os.path.join(filepath, files.filename)

		pub = Publication.query.filter_by(id=pid).first()
		if(pub == None):
			msg = {"message": "publication not found"}
			return jsonify(msg), 404

		filequery = File.query.filter_by(pub_id=int(pid), filename=files.filename).first()
		if(filequery != None):
			msg = {"message": "file with specific name has been already added to publication"}
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

@app.route('/publications/<pid>/files/<fid>', methods=['GET'])
def filesfid(pid, fid):
	files = File.query.filter_by(id=fid, pub_id=pid).first()
	if(files == None):
		msg = {"message": "Could not find file for given ids"}
		return jsonify(msg), 401
	
	filename = files.get_all()
	filename = filename['filename']
	filepath = app.config['UPLOAD_FOLDER']
	filepath = os.path.join(filepath, pid)
	filepath = os.path.join(filepath, filename)
	send = send_file(filepath, attachment_filename=filename, as_attachment=True)
	return send, 200

@app.route('/publications/<pid>/files/<fid>', methods=['DELETE'])
def file_delete(pid, fid):
	filequery = File.query.filter_by(id=fid, pub_id=pid)
	if(filequery.count() != 1):
		msg = {"messaage": "file not found"}
		return jsonify(msg), 401
	try:
		filepath = os.path.join(app.config['UPLOAD_FOLDER'], pid)
		files = File.query.filter_by(id=fid, pub_id=pid).first()
		files = files.get_all()
		filepath = os.path.join(filepath, files['filename'])
		print(filepath, flush=True)
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
		file_ids.append(tmp['id'])
		filenames.append(tmp['filename'])
	for fid, filename in zip(file_ids, filenames):
		filequery = File.query.filter_by(id=int(fid), pub_id=int(pid))
		if(filequery.count() != 1):
			msg = {"message": "file not found"}
			return jsonify(msg), 401
		filepath = os.path.join(app.config['UPLOAD_FOLDER'], str(pid))
		filepath = os.path.join(filepath, filename)
		try:
			filequery.delete()
			db.session.commit()
			msg = {"message": "Successfully deleted"}
			os.remove(filepath)
			return jsonify(msg), 200
		except:
			db.session.rollback()
			msg = {"message": "Failed to delete"}
			return jsonify(msg), 401