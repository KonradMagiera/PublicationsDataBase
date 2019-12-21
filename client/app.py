from flask import Flask, render_template, request, redirect, url_for, make_response, send_file, jsonify, Response
import requests
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv


app = Flask(__name__)

# CONFIG
load_dotenv(verbose=True)
JWT_SECRET = os.getenv("JWT_SECRET")
app.config['CURRENT_USER'] = ''
REQUEST_CREDENTIALS_EXPIRE = int(os.getenv("REQUEST_CREDENTIALS_EXPIRE"))
PUBLICATIONS_ACCESS = int(os.getenv("PUBLICATIONS_ACCESS"))


#######

@app.route('/', methods=['GET'])
def index():
	
	user_tmp = app.config['CURRENT_USER']
	response = ''
	if(user_tmp == ''):
		response = make_response(redirect(url_for('login')))
		response.set_cookie('session_id', '', max_age=0)
	else:
		session_id = request.cookies.get('session_id')
		response = redirect(url_for('profile', username=app.config['CURRENT_USER']) if session_id else url_for('render_login'))
	return response

@app.route('/login', methods=['GET'])
def render_login():
	error = ''
	if('error' in request.args):
		error = request.args['error']
	return render_template("login.html", error=error)

@app.route('/login', methods=['POST'])
def login():
	user = request.form.get('username')
	password = request.form.get('password')
	token = {"username": user, "password": password, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
	token = jwt.encode(token, JWT_SECRET, algorithm='HS256')
	headers= {"Authorization": token}
	response = requests.post("http://api:5000/login", headers=headers)	
	if(response.status_code == 200):
		token_decode = response.headers.get('Authorization')
		try:	
			token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm='HS256')
		except jwt.ExpiredSignatureError:
			msg = "token expired"
			return redirect(url_for('render_login', error= msg)), 401

		app.config['CURRENT_USER'] = user
		resp = make_response(redirect(url_for('render_profile')))
		session_id = token_decode['session_id']
		resp.set_cookie('session_id', session_id, httponly=True)
		return resp
	message = response.json()
	message = message['message']
	return redirect(url_for('login', error=message))

@app.route('/profile', methods=['GET'])
def render_profile():
	if(('session_id' in request.cookies) and (app.config['CURRENT_USER'] != '')):
		user = app.config['CURRENT_USER']
		return render_template("profile.html", username=user)
	else:
		app.config['CURRENT_USER'] = ''
		return redirect(url_for('login', error="Session expired"))

@app.route('/profile', methods=['POST'])
def profile():
	if request.form['btn'] == 'Logout':
		headers= {"Authorization": create_jwt(REQUEST_CREDENTIALS_EXPIRE)}
		response = requests.post("http://api:5000/logout", headers=headers)
		if(response.status_code == 200):
			resp = make_response(redirect(url_for('login')))
			resp.set_cookie('session_id', '', max_age=0)
			app.config['CURRENT_USER'] = ''
			return resp
		else:
			resp = make_response(redirect(url_for('login', error="error occured")))
			resp.set_cookie('session_id', '', max_age=0)
			app.config['CURRENT_USER'] = ''
			return resp
	else:
		return redirect(url_for('render_publications'))

@app.route('/publications', methods=['GET'])
def render_publications():
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.get("http://api:5000/publications", headers=headers)
	pubs = list()
	data = response.json()
	if(("publication" not in data) or (response.status_code != 200)):
		pubs = None
	else:	
		data = data['publication']
		for pub in data:
			pubs.append({'id': pub['id'], 'title': pub['title']})
	return render_template('publications.html', publications=pubs)

@app.route('/publications', methods=['POST'])
def publications_back():
	if(request.form['btn'] =='Back'):
		return redirect(url_for('render_profile'))
	else:
		#Add
		return redirect(url_for('render_publications_add'))

@app.route('/publications/add', methods=['GET'])
def render_publications_add():
	return render_template('add_publication.html')

@app.route('/publications/add', methods=['POST'])
def publications_add():
	if(request.form['btn'] == 'Save'):
		title = request.form['title']
		author = request.form['author']
		publisher = request.form['publisher']
		date = request.form['date']
		file = request.files.get('file')
		files = {"file": (file.filename, file, 'application/pdf')}

		token = create_jwt(PUBLICATIONS_ACCESS)
		headers= {"Authorization": token}
		response = requests.post('http://api:5000/publications', json={"title": title, "author": author, "publisher": publisher, "date": date}, headers=headers)
		if(file.filename != ''):
			data = response.json()
			if('id' in data):
				id = data['id']
				headers = {"Authorization": token}
				response = requests.post("http://api:5000/publications/" + str(id) + "/files", files=files, headers=headers)

	return redirect(url_for('render_publications'))

@app.route('/publications/<id>', methods=['GET'])
def render_publications_id(id):
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.get('http://api:5000/publications/' + id, headers=headers)
	data = response.json()
	if((response.status_code != 200) or ("publication" not in data)):
		return redirect(url_for("render_publications"))
	data = data['publication']
	data = data[0]
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.get('http://api:5000/publications/'+ id + "/files", headers=headers)
	files = response.json()
	files = files['publication']
	if(len(files) == 0):
		files = None
	return render_template('publication.html', publication=data, files=files)

@app.route('/publications/<id>', methods=['POST'])
def publications_id_post(id):
	if(request.form['btn'] == 'Back'):
		return redirect(url_for('render_publications'))
	elif(request.form['btn'] == 'Add file'):
		file = request.files.get('file')
		files = {'file': (file.filename, file, 'application/pdf')}
		if(file.filename != ''):
				headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
				response = requests.post('http://api:5000/publications/' + str(id) + "/files", files=files, headers=headers)
		return redirect(url_for('render_publications_id', id=id))

@app.route('/publications/<id>/edit', methods=['GET'])
def render_publication_id_edit(id):
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.get('http://api:5000/publications/' + id, headers=headers)
	data = response.json()
	if((response.status_code != 200) or ("publication" not in data)):
		return redirect(url_for("render_publications_id", id=id))
	data = data['publication']
	data = data[0]
	date = data['pub_date']
	date = date[5:-13]
	day = date[0:2]
	month = {
		'Jan' : 1,
        'Feb' : 2,
        'Mar' : 3,
        'Apr' : 4,
        'May' : 5,
        'Jun' : 6,
        'Jul' : 7,
        'Aug' : 8,
        'Sep' : 9, 
        'Oct' : 10,
        'Nov' : 11,
        'Dec' : 12}
	tmp_mon = date[3:6]
	month = month[tmp_mon]
	year = date[7:11]
	data['pub_date'] = str(year) + '-' + str(month) + '-' + day
	return render_template('edit_publication.html', publication=data)

@app.route('/publications/<id>/edit', methods=['POST'])
def send_publications_id_edit(id):
	if(request.form['btn'] == 'Save'):
		title = request.form['title']
		author = request.form['author']
		publisher = request.form['publisher']
		date = request.form['date']
		headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
		response = requests.put('http://api:5000/publications/' + id, json={"id": id, "title": title, "author": author, "publisher": publisher, "date":date}, headers=headers)
	return redirect(url_for('render_publications_id', id=id))

@app.route('/publications/<id>/delete', methods=['GET'])
def publications_id_delete(id):
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.delete('http://api:5000/publications/' + id, headers=headers)
	return redirect(url_for('render_publications'))

@app.route('/publications/<pid>/files/<fid>', methods=['GET'])
def file_download(pid, fid):
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.get('http://api:5000/publications/' + pid + "/files/" + fid, headers=headers)
	if(response.status_code != 200):
		return redirect(url_for('render_publications_id', id=pid))
	resp = Response(response=response.content, content_type='application/pdf')
	return resp
	
@app.route('/publications/<pid>/files/<fid>/delete', methods=['GET'])
def file_delete(pid, fid):
	headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
	response = requests.delete('http://api:5000/publications/' + pid + "/files/" + fid, headers=headers)
	return redirect(url_for('render_publications_id', id=pid))

def create_jwt(expire_time):
	session_id = request.cookies.get('session_id')
	token = {"username": app.config['CURRENT_USER'], "session_id": session_id, "exp": datetime.now() + timedelta(seconds=expire_time)}
	token = jwt.encode(token, JWT_SECRET, algorithm='HS256')
	return token
