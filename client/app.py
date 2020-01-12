from flask import Flask, render_template, request, redirect, url_for, make_response, send_file, jsonify, Response, session
import secrets
import requests
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

app = Flask(__name__)

# CONFIG
load_dotenv(verbose=True)
JWT_SECRET = os.getenv("JWT_SECRET")
REQUEST_CREDENTIALS_EXPIRE = int(os.getenv("REQUEST_CREDENTIALS_EXPIRE"))
PUBLICATIONS_ACCESS = int(os.getenv("PUBLICATIONS_ACCESS"))

app.config["SECRET_KEY"] = secrets.token_urlsafe(16)
oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id='c2PmfJVzeXvzCYNfd0XFSyW4PD8SXP2c',
    client_secret='WHw-238VITTx5h9ssgq-Z6pddZzTdECEfH2hYU1-kmlfmW74cD3aZlTmq5jO3UkX',
    api_base_url='https://uni-web-p4.eu.auth0.com',
    access_token_url='https://uni-web-p4.eu.auth0.com/oauth/token',
    authorize_url='https://uni-web-p4.eu.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

#######

@app.route('/callback')
def callback_handling():
	auth0.authorize_access_token()
	resp = auth0.get('userinfo')
	userinfo = resp.json()
	session["USERNAME"] = userinfo['name']
	#session["SESSION_ID"] = "tmp"
	return redirect(url_for('login'))

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		if(('USERNAME' not in session) or ('SESSION_ID' not in session)):
			return redirect('/')
		return f(*args, **kwargs)
	return decorated

def requires_user(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		if('USERNAME' not in session):
			return redirect('/')
		return f(*args, **kwargs)
	return decorated

@app.route('/', methods=['GET'])
def index():
	response = ''
	if(("USERNAME" not in session) or ("SESSION_ID" not in session)):
		response = redirect(url_for('login_auth'))
		session.clear()
	else:
		response = redirect(url_for('profile', username=session["USERNAME"]))
	return response

@app.route('/loginauth', methods=['GET'])
def render_auth():
	return render_template("auth0.html")

@app.route('/loginauth', methods=['POST'])
def login_auth():
	return auth0.authorize_redirect(redirect_uri='http://localhost:5001/callback')

@app.route('/login', methods=['GET'])
@requires_user
def render_login():
	if("SESSION_ID" in session):
		return redirect(url_for('profile', username=session["USERNAME"]))
	error = ''
	if('error' in request.args):
		error = request.args['error']
	return render_template("login.html", error=error, user=session["USERNAME"])

@app.route('/login', methods=['POST'])
@requires_user
def login():
	if( request.form['btn-signin'] == "Logout"):
		session.clear()
		params = {'returnTo': url_for('login_auth', _external=True), 'client_id': 'c2PmfJVzeXvzCYNfd0XFSyW4PD8SXP2c'}
		return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))
	password = request.form.get('password')
	token = {"username": session["USERNAME"], "password": password, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
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

		#session["USERNAME"] = user
		session["SESSION_ID"] = token_decode['session_id']
		return redirect(url_for('render_profile'))
	message = response.json()
	message = message['message']
	return redirect(url_for('login', error=message))

@app.route('/profile', methods=['GET'])
@requires_auth
def render_profile():
	if(('SESSION_ID' in session) and ("USERNAME" in session)):
		user = session["USERNAME"]
		return render_template("profile.html", username=user)
	else:
		session.clear()
		return redirect(url_for('login', error="Session expired"))

@app.route('/profile', methods=['POST'])
@requires_auth
def profile():
	if request.form['btn'] == 'Logout':
		token = create_jwt(REQUEST_CREDENTIALS_EXPIRE)
		if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
			session.clear()
			return token
		
		headers= {"Authorization": token}
		response = requests.post("http://api:5000/logout", headers=headers)
		if(response.status_code == 200):
			session.clear()
			params = {'returnTo': url_for('login_auth', _external=True), 'client_id': 'c2PmfJVzeXvzCYNfd0XFSyW4PD8SXP2c'}
			return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))
			#return redirect(url_for('login'))
		else:
			session.clear()
			params = {'returnTo': url_for('login_auth', _external=True), 'client_id': 'c2PmfJVzeXvzCYNfd0XFSyW4PD8SXP2c'}
			return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))
			#return redirect(url_for('login', error="error occured"))
	else:
		return redirect(url_for('render_publications'))

@app.route('/publications', methods=['GET'])
@requires_auth
def render_publications():
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
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
@requires_auth
def publications_back():
	if(request.form['btn'] =='Back'):
		return redirect(url_for('render_profile'))
	else:
		#Add
		return redirect(url_for('render_publications_add'))

@app.route('/publications/add', methods=['GET'])
@requires_auth
def render_publications_add():
	return render_template('add_publication.html')

@app.route('/publications/add', methods=['POST'])
@requires_auth
def publications_add():
	if(request.form['btn'] == 'Save'):
		title = request.form['title']
		author = request.form['author']
		publisher = request.form['publisher']
		date = request.form['date']
		file = request.files.get('file')
		files = {"file": (file.filename, file, 'application/pdf')}

		token = create_jwt(PUBLICATIONS_ACCESS)
		if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
			session.clear()
			return token
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
@requires_auth
def render_publications_id(id):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get('http://api:5000/publications/' + id, headers=headers)
	data = response.json()
	if((response.status_code != 200) or ("publication" not in data)):
		return redirect(url_for("render_publications"))
	data = data['publication']
	data = data[0]
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get('http://api:5000/publications/'+ id + "/files", headers=headers)
	files = response.json()
	files = files['publication']
	if(len(files) == 0):
		files = None
	return render_template('publication.html', publication=data, files=files)

@app.route('/publications/<id>', methods=['POST'])
@requires_auth
def publications_id_post(id):
	if(request.form['btn'] == 'Back'):
		return redirect(url_for('render_publications'))
	elif(request.form['btn'] == 'Add file'):
		file = request.files.get('file')
		files = {'file': (file.filename, file, 'application/pdf')}
		if(file.filename != ''):
				token = create_jwt(PUBLICATIONS_ACCESS)
				if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
					session.clear()
					return token
				headers= {"Authorization": token}
				requests.post('http://api:5000/publications/' + str(id) + "/files", files=files, headers=headers)
		return redirect(url_for('render_publications_id', id=id))

@app.route('/publications/<id>/edit', methods=['GET'])
@requires_auth
def render_publication_id_edit(id):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
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
@requires_auth
def send_publications_id_edit(id):
	if(request.form['btn'] == 'Save'):
		title = request.form['title']
		author = request.form['author']
		publisher = request.form['publisher']
		date = request.form['date']
		token = create_jwt(PUBLICATIONS_ACCESS)
		if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
			session.clear()
			return token
		headers= {"Authorization": token}
		requests.put('http://api:5000/publications/' + id, json={"id": id, "title": title, "author": author, "publisher": publisher, "date":date}, headers=headers)
	return redirect(url_for('render_publications_id', id=id))

@app.route('/publications/<id>/delete', methods=['GET'])
@requires_auth
def publications_id_delete(id):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	requests.delete('http://api:5000/publications/' + id, headers=headers)
	return redirect(url_for('render_publications'))

@app.route('/publications/<pid>/files/<fid>', methods=['GET'])
@requires_auth
def file_download(pid, fid):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get('http://api:5000/publications/' + pid + "/files/" + fid, headers=headers)
	if(response.status_code != 200):
		return redirect(url_for('render_publications_id', id=pid))
	resp = Response(response=response.content, content_type='application/pdf')
	return resp
	
@app.route('/publications/<pid>/files/<fid>/delete', methods=['GET'])
@requires_auth
def file_delete(pid, fid):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	requests.delete('http://api:5000/publications/' + pid + "/files/" + fid, headers=headers)
	return redirect(url_for('render_publications_id', id=pid))

def create_jwt(expire_time):
	if("SESSION_ID" in session):
		session_id = session["SESSION_ID"]
		token = {"username": session["USERNAME"], "session_id": session_id, "exp": datetime.now() + timedelta(seconds=expire_time)}
		token = jwt.encode(token, JWT_SECRET, algorithm='HS256')
		return token
	else:
		return redirect(url_for('login', error="Session expired"))
