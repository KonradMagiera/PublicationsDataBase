from flask import Flask, render_template, request, redirect, url_for, make_response, send_file, jsonify, Response, session
import secrets
import requests
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import wraps
import re
from flask_talisman import Talisman
from Crypto.Hash import SHA256

app = Flask(__name__)

# CONFIG
load_dotenv(verbose=True)
JWT_SECRET = os.getenv("JWT_SECRET")
REQUEST_CREDENTIALS_EXPIRE = int(os.getenv("REQUEST_CREDENTIALS_EXPIRE"))
PUBLICATIONS_ACCESS = int(os.getenv("PUBLICATIONS_ACCESS"))
API_URL = os.getenv("API_URL")
app.config["SECRET_KEY"] = secrets.token_urlsafe(16)


Talisman(app)
#######

def requires_auth(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		if(("USERNAME" not in session) or ("SESSION_ID" not in session)):
			return redirect("/")
		return f(*args, **kwargs)
	return decorated

@app.route("/", methods=["GET"])
def index():
	response = ""
	if(("USERNAME" not in session) or ("SESSION_ID" not in session)):
		response = redirect(url_for("render_main"))
		session.clear()
	else:
		response = redirect(url_for("profile", username=session["USERNAME"]))
	return response


@app.route("/main", methods=["GET"])
def render_main():
	return render_template("main.html")

@app.route("/main", methods=["POST"])
def main():
	if request.form["btn"] == "Sign in":
		return redirect(url_for("render_login"))
	return redirect(url_for("render_register"))

@app.route("/login", methods=["GET"])
def render_login():
	if(("SESSION_ID" in session) and ("USERNAME" in session)):
		return redirect(url_for("profile", username=session["USERNAME"]))
	error = ""
	if("error" in request.args):
		error = request.args["error"]
	return render_template("login.html", error=error)

@app.route("/login", methods=["POST"])
def login():
	if request.form["btn"] == "Register page":
		return redirect(url_for("render_register"))
	user = request.form.get("username")
	password = request.form.get("password")

	password = hashString(password, 20)
	token = {"username": user, "password": password, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
	token = jwt.encode(token, JWT_SECRET, algorithm="HS256")
	headers= {"Authorization": token}
	response = requests.post(API_URL + "/login", headers=headers)
	if(response.status_code == 200):
		token_decode = response.headers.get("Authorization")
		try:	
			token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm="HS256")
		except jwt.ExpiredSignatureError:
			msg = "token expired"
			return redirect(url_for("render_login", error= msg)), 401
		session["USERNAME"] = user
		session["SESSION_ID"] = token_decode["session_id"]
		return redirect(url_for("render_profile"))
	message = response.json()
	message = message["message"]
	return redirect(url_for("login", error=message))

@app.route("/register", methods=["GET"])
def render_register():
	if(("SESSION_ID" in session) and ("USERNAME" in session)):
		return render_template("profile.html", username=session["USERNAME"])
	error = ""
	username = ""
	if("error" in request.args):
		error = request.args["error"]
	if("username" in request.args):
		username = request.args["username"]
	return render_template("register.html", error=error, username=username)

@app.route("/register", methods=["POST"])
def register():
	if request.form["btn"] == "Login page":
		return redirect(url_for("render_login"))
	
	user = request.form.get("username")
	password = request.form.get("password")

	if(not verify_password(password)):
		return redirect(url_for("render_register", error="Password is too weak", username=user))
	repeat_password = request.form.get("repeat_password")
	if(password != repeat_password):
		return redirect(url_for("render_register", error="Passwords doesn't match", username=user))

	token = {"username": user, "password": password, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
	token = jwt.encode(token, JWT_SECRET, algorithm="HS256")
	headers= {"Authorization": token}
	response = requests.post(API_URL + "/register", headers=headers)
	if(response.status_code != 201):
		data = response.json()
		data = data["message"]
		return redirect(url_for("render_register", error=data, username=user))
	return redirect(url_for("render_login"))

@app.route("/profile", methods=["GET"])
@requires_auth
def render_profile():
	if(("SESSION_ID" in session) and ("USERNAME" in session)):
		return render_template("profile.html", username=session["USERNAME"])
	else:
		session.clear()
		return redirect(url_for("login", error="Session expired"))

@app.route("/profile", methods=["POST"])
@requires_auth
def profile():
	if request.form["btn"] == "Logout":
		token = create_jwt(REQUEST_CREDENTIALS_EXPIRE)
		if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
			session.clear()
			return token
		
		headers= {"Authorization": token}
		response = requests.post(API_URL + "/logout", headers=headers)
		if(response.status_code == 200):
			session.clear()
			return redirect(url_for("login"))
		else:
			session.clear()
			return redirect(url_for("login", error="error occured"))
	elif request.form["btn"] == "Change password":
		return redirect(url_for("render_change"))
	else:
		return redirect(url_for("render_publications"))

@app.route("/change_password", methods=["GET"])
@requires_auth
def render_change():
	error = ''
	if("error" in request.args):
		error = request.args["error"]
	return render_template("changepwd.html", error=error)

@app.route("/change_password", methods=["POST"])
@requires_auth
def changepwd():
	if request.form["btn"] == "Cancel":
		return redirect(url_for("render_profile"))
	old_password = request.form.get("old_password")
	new_password = request.form.get("password")
	if(not verify_password(new_password)):
		return redirect(url_for("render_change", error="Password is too weak"))
	repeat_password = request.form.get("repeat_password")
	if(new_password != repeat_password):
		return redirect(url_for("render_change", error="Passwords doesn't match"))

	token = {"username": session["USERNAME"], "session_id": session["SESSION_ID"], "old_password": old_password, "new_password": new_password, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
	token = jwt.encode(token, JWT_SECRET, algorithm="HS256")
	headers= {"Authorization": token}
	response = requests.put(API_URL + "/change_password", headers=headers)
	if(response.status_code == 200):
		return redirect(url_for("render_profile"))
	data = response.json()
	return redirect(url_for("render_change", error=data["message"]))

@app.route("/publications", methods=["GET"])
@requires_auth
def render_publications():
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get(API_URL + "/publications", headers=headers)
	pubs = list()
	data = response.json()
	if(("publication" not in data) or (response.status_code != 200)):
		pubs = None
	else:	
		data = data["publication"]
		for pub in data:
			pubs.append({"id": pub["id"], "title": pub["title"]})
	return render_template("publications.html", publications=pubs, username=session["USERNAME"])

@app.route("/publications", methods=["POST"])
@requires_auth
def publications_back():
	if(request.form["btn"] =="Back"):
		return redirect(url_for("render_profile"))
	else:
		#Add
		return redirect(url_for("render_publications_add"))

@app.route("/publications/add", methods=["GET"])
@requires_auth
def render_publications_add():
	return render_template("add_publication.html", username=session["USERNAME"])

@app.route("/publications/add", methods=["POST"])
@requires_auth
def publications_add():
	if(request.form["btn"] == "Save"):
		title = request.form["title"]
		author = request.form["author"]
		publisher = request.form["publisher"]
		date = request.form["date"]
		file = request.files.get("file")
		files = {"file": (file.filename, file, "application/pdf")}

		token = create_jwt(PUBLICATIONS_ACCESS)
		if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
			session.clear()
			return token
		headers= {"Authorization": token}
		response = requests.post(API_URL + "/publications", json={"title": title, "author": author, "publisher": publisher, "date": date}, headers=headers)
		if(file.filename != ""):
			data = response.json()
			if("id" in data):
				id = data["id"]
				headers = {"Authorization": token}
				response = requests.post(API_URL + "/publications/" + str(id) + "/files", files=files, headers=headers)

	return redirect(url_for("render_publications"))

@app.route("/publications/<id>", methods=["GET"])
@requires_auth
def render_publications_id(id):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get(API_URL + "/publications/" + id, headers=headers)
	data = response.json()
	if((response.status_code != 200) or ("publication" not in data)):
		return redirect(url_for("render_publications"))
	data = data["publication"]
	data = data[0]
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get(API_URL + "/publications/"+ id + "/files", headers=headers)
	files = response.json()
	files = files["publication"]
	if(len(files) == 0):
		files = None
	return render_template("publication.html", publication=data, files=files, username=session["USERNAME"])

@app.route("/publications/<id>", methods=["POST"])
@requires_auth
def publications_id_post(id):
	if(request.form["btn"] == "Back"):
		return redirect(url_for("render_publications"))
	elif(request.form["btn"] == "Add file"):
		file = request.files.get("file")
		files = {"file": (file.filename, file, "application/pdf")}
		if(file.filename != ""):
				token = create_jwt(PUBLICATIONS_ACCESS)
				if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
					session.clear()
					return token
				headers= {"Authorization": token}
				requests.post(API_URL + "/publications/" + str(id) + "/files", files=files, headers=headers)
		return redirect(url_for("render_publications_id", id=id))

@app.route("/publications/<id>/edit", methods=["GET"])
@requires_auth
def render_publication_id_edit(id):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get(API_URL + "/publications/" + id, headers=headers)
	data = response.json()
	if((response.status_code != 200) or ("publication" not in data)):
		return redirect(url_for("render_publications_id", id=id))
	data = data["publication"]
	data = data[0]
	date = data["pub_date"]
	date = date[5:-13]
	day = date[0:2]
	month = {
		"Jan" : 1,
        "Feb" : 2,
        "Mar" : 3,
        "Apr" : 4,
        "May" : 5,
        "Jun" : 6,
        "Jul" : 7,
        "Aug" : 8,
        "Sep" : 9, 
        "Oct" : 10,
        "Nov" : 11,
        "Dec" : 12}
	tmp_mon = date[3:6]
	month = month[tmp_mon]
	if(month < 10):
		month = "0" + str(month)
	year = date[7:11]
	data["pub_date"] = str(year) + "-" + str(month) + "-" + day
	return render_template("edit_publication.html", publication=data, username=session["USERNAME"])

@app.route("/publications/<id>/edit", methods=["POST"])
@requires_auth
def send_publications_id_edit(id):
	if(request.form["btn"] == "Save"):
		title = request.form["title"]
		author = request.form["author"]
		publisher = request.form["publisher"]
		date = request.form["date"]
		token = create_jwt(PUBLICATIONS_ACCESS)
		if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
			session.clear()
			return token
		headers= {"Authorization": token}
		requests.put(API_URL + "/publications/" + id, json={"id": id, "title": title, "author": author, "publisher": publisher, "date":date}, headers=headers)
	return redirect(url_for("render_publications_id", id=id))

@app.route("/publications/<id>/delete", methods=["GET"])
@requires_auth
def publications_id_delete(id):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	requests.delete(API_URL + "/publications/" + id, headers=headers)
	return redirect(url_for("render_publications"))

@app.route("/publications/<pid>/files/<fid>", methods=["GET"])
@requires_auth
def file_download(pid, fid):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	response = requests.get(API_URL + "/publications/" + pid + "/files/" + fid, headers=headers)
	if(response.status_code != 200):
		return redirect(url_for("render_publications_id", id=pid))
	resp = Response(response=response.content, content_type="application/pdf")
	return resp
	
@app.route("/publications/<pid>/files/<fid>/delete", methods=["GET"])
@requires_auth
def file_delete(pid, fid):
	token = create_jwt(PUBLICATIONS_ACCESS)
	if(str(type(token)) == "<class 'werkzeug.wrappers.response.Response'>"):
		session.clear()
		return token
	headers= {"Authorization": token}
	requests.delete(API_URL + "/publications/" + pid + "/files/" + fid, headers=headers)
	return redirect(url_for("render_publications_id", id=pid))

def create_jwt(expire_time):
	if(("SESSION_ID" in session) and ("USERNAME" in session)):
		token = {"username": session["USERNAME"], "session_id": session["SESSION_ID"], "exp": datetime.now() + timedelta(seconds=expire_time)}
		token = jwt.encode(token, JWT_SECRET, algorithm="HS256")
		return token
	else:
		return redirect(url_for("login", error="Session expired"))

def verify_password(password):
	pattern = re.compile("""(?=^.{8,20}$)(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&amp;*()_+}{&quot;:;"?&gt;.&lt;,])(?!.*\s).*$""")
	if(pattern.match(password) == None):
		return False
	return True

def hashString(password, num):
	new_password = password
	for i in range(0, num):
		new_password = str.encode(new_password)
		new_password = SHA256.new(new_password)
		new_password = new_password.hexdigest()
	return new_password

if __name__ == "__main__":  
	app.run()