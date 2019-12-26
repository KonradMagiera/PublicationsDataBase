import requests
import getpass
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import jwt

load_dotenv(verbose=True)
JWT_SECRET = os.getenv("JWT_SECRET")
REQUEST_CREDENTIALS_EXPIRE = int(os.getenv("REQUEST_CREDENTIALS_EXPIRE"))
PUBLICATIONS_ACCESS = int(os.getenv("PUBLICATIONS_ACCESS"))
CURRENT_USER = ""
SESSION_ID = ""



# TODO  delete_file; download_file


def start_menu():
    print("You will be shown menu options. Write NUMBER of your choice displayed next to label\n")
    print("Menu:")
    print("1. Login     2. Exit\n")
    print("Go to: ", end="")

def profile_menu():
    print("\nMenu:")
    print("1. Publications      2. Logout\n")
    print("Go to: ", end="")

def publications_menu():
    print("\nMenu:")
    print("-1. Back     0. Add publication")
    print("Type publication id for more options ([id]. [Title])\n")
    print("Go to: ", end="")

def pub_menu():
    print("\nMenu:")
    print("-3. Back     -2. Edit        -1. Delete      0, Add file")
    print("Type file id for more options ([id]. [Filename])\n")
    print("Go to: ", end="")

def publications_options(id, title):
    print("\n%d. %s" % (id, title))
    print("Options:")
    print("1. Open      2. Edit     3. Delete       4. Cancel\n")
    print("Go to: ", end="")

def file_options(id, filename):
    print("\n%d. %s" % (id, filename))
    print("Options:")
    print("1. Delete      2. Download       3. Cancel\n")
    print("Go to: ", end="")

def create_jwt(expire_time):
	token = {"username": CURRENT_USER, "session_id": SESSION_ID, "exp": datetime.now() + timedelta(seconds=expire_time)}
	token = jwt.encode(token, JWT_SECRET, algorithm='HS256')
	return token

def login():
    print("Username: ", end="")
    username = input()
    password = getpass.getpass("Password: ")
    token = {"username": username, "password": password, "exp": datetime.now() + timedelta(seconds=REQUEST_CREDENTIALS_EXPIRE)}
    token = jwt.encode(token, JWT_SECRET, algorithm='HS256')
    headers= {"Authorization": token}
    response = requests.post("http://localhost:5000/login", headers=headers)

    if(response.status_code == 200):
        token_decode = response.headers.get("Authorization")
        try:
            token_decode = jwt.decode(token_decode, JWT_SECRET, algorithm="HS256")
        except jwt.ExpiredSignatureError:
            return False, "", ""
            
        if("session_id" in token_decode):
            return True, token_decode["session_id"], username
        else:
            print("Session not generated")
            return False, "", ""
    else:
        data = response.json()
        if("message" in data):
            print(data["message"])
        return False, "", ""

def logout():
    headers= {"Authorization": create_jwt(REQUEST_CREDENTIALS_EXPIRE)}
    response = requests.post("http://localhost:5000/logout", headers=headers)
    if(response.status_code == 200):
        return "", ""
    else:
        print("\nerror occured\n")
        return "", ""

def publications():
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    response = requests.get("http://localhost:5000/publications", headers=headers)
    pubs = list()
    data = response.json()
    if(("publication" not in data) or (response.status_code != 200)):
        pubs = None
    else:	
        data = data['publication']
        for pub in data:
            pubs.append({'id': pub['id'], 'title': pub['title']})
    return pubs

def print_publications(pubs):
    if(pubs):
        for p in pubs:
            print("%d. %s" % (p["id"], p["title"]))

def add_publication():
    title = ""
    author = ""
    publisher = ""
    date = ""

    print("Title: ", end="")
    title = input()

    print("Author: ", end="")
    author = input()

    print("Publisher: ", end="")
    publisher = input()

    while(True):
        print("Date (YYYY-MM-DD or empty): ", end="")
        date = input()
        if(len(date) == 10 or date == ""):
            break
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    response = requests.post('http://localhost:5000/publications', json={"title": title, "author": author, "publisher": publisher, "date": date}, headers=headers)
    data = response.json()
    id = -1
    if('id' in data):
        id = data['id']
    return id

def edit_publication(id):
    print("Leave empty field if you want to keep current value\n")
    title = ""
    author = ""
    publisher = ""
    date = ""
    data = get_pub_data(id)
    if(data):
        title = data["title"]
        author = data["author"]
        publisher = data["publisher"]
        date = data["pub_date"]

    print("Title: ", end="")
    title_tmp = input()
    if(title_tmp != ""):
        title = title_tmp

    print("Author: ", end="")
    author_tmp = input()
    if(author_tmp != ""):
        author = author_tmp

    print("Publisher: ", end="")
    publisher_tmp = input()
    if(publisher_tmp != ""):
        publisher = publisher_tmp

    while(True):
        print("Date (YYYY-MM-DD or empty): ", end="")
        date_tmp = input()
        if(len(date_tmp) == 10):
            date = date_tmp
            break
        elif(date_tmp == ""):
            date = build_date(date)
            break
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    requests.put('http://localhost:5000/publications/' + str(id), json={"id": str(id), "title": title, "author": author, "publisher": publisher, "date":date}, headers=headers)
    
def delete_publication(id):
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    requests.delete('http://localhost:5000/publications/' + str(id), headers=headers)

def print_pub(id):
    data = get_pub_data(id)
    files = get_pub_files(id)
    if(data):
        print("%d. %s" % (data["id"], data["title"]))
        print("Author: %s" % data["author"])
        print("Publisher: %s" % data["publisher"])
        print("Date: %s" % data["pub_date"])
        if(files):
            print("")
            for f in files:
                print("%d. %s" % (f["id"], f["filename"]))
        return True
    return False

def get_pub_data(id):
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    response = requests.get('http://localhost:5000/publications/' + str(id), headers=headers)
    data = response.json()
    if((response.status_code != 200) or ("publication" not in data)):
        return None
    data = data['publication']
    data = data[0]
    return data

def get_pub_files(id):
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    response = requests.get('http://localhost:5000/publications/'+ str(id) + "/files", headers=headers)
    files = response.json()
    files = files['publication']
    if(len(files) == 0):
        files = None
    return files

def build_date(pub_date):
    date = pub_date[5:-13]
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
    date = str(year) + '-' + str(month) + '-' + day
    return date

def add_file(id):
    print("File (path): ", end="")
    file = input()
    try:
        file = open(file, "rb")
    except IOError:
        return False
    filename = os.path.basename(file.name)
    files = {'file': (filename, file, 'application/pdf')}
    if(filename != ''):
            headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
            response = requests.post('http://localhost:5000/publications/' + str(id) + "/files", files=files, headers=headers)
            if(response.status_code == 201):
                return True
    return False

def delete_file(pid, fid):
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    requests.delete('http://localhost:5000/publications/' + str(pid) + "/files/" + str(fid), headers=headers)

def download_file(pid, fid):
    print()


while(True): # login/exit       1
    start_menu()
    try:
        choice = int(input())
    except ValueError:
        print("give valid number")
        continue
    if(choice == 1): #login
        is_logged_in, SESSION_ID, CURRENT_USER = login()

        while(is_logged_in): #profile publications/logout        2
            profile_menu()
            try:
                choice = int(input())
            except ValueError:
                print("give valid number")
                continue
            if(choice == 1): #publications
                while(True): #choose publication and option    3
                    pubs = publications()
                    print_publications(pubs)
                    publications_menu()
                    try:
                        choice = int(input())
                    except ValueError:
                        print("give valid number")
                        continue
                    if(choice == 0): #Add publication
                        new_id = add_publication()
                        if(new_id != -1):
                            added = add_file(new_id)
                            if(not added):
                                print("\nFailed to add file!\n")
                    elif(choice == -1): #Back to profile
                        break
                    else:
                        id_exist = 0
                        pub_title = ""
                        for p in pubs:
                            if(int(p["id"]) == choice):
                                id_exist = choice
                                pub_title = p["title"]
                                break

                        while(id_exist != 0): #Do something with chosen publication         4
                            publications_options(id_exist, pub_title)
                            try:
                                choice = int(input())
                            except ValueError:
                                print("give valid number")
                                continue
                            if(choice == 1): #Open
                                found = print_pub(id_exist)
                                if(not found):
                                    break
                                pub_menu()
                                try:
                                    choice = int(input())
                                except ValueError:
                                    print("give valid number")
                                    continue
                                if(choice == -3): #Back
                                    break
                                elif(choice == -2): #Edit
                                    edit_publication(id_exist)
                                    break
                                elif(choice == -1): #Delete
                                    delete_publication(id_exist)
                                    break
                                elif(choice == 0): #add file
                                    added = add_file(id_exist)
                                    if(not added):
                                        print("\nFailed to add file!\n")
                                    break
                                else: #File
                                    fid = 0
                                    filename = ""
                                    files = get_pub_files(id_exist)
                                    for f in files:
                                        if(int(f["id"]) == choice):
                                            fid = choice
                                            filename = f["filename"]
                                            break

                                    while(fid != 0): #delete, download, cancel (file handling)      5
                                        file_options(fid, filename)
                                        try:
                                            choice = int(input())
                                        except ValueError:
                                            print("give valid number")
                                            continue
                                        if(choice == 1): #delete
                                            delete_file(id_exist, fid)
                                            break
                                        elif(choice == 2): #download TODO
                                            print()
                                            break
                                        elif(choice == 3): #cancel
                                            break                                  
                                        else:
                                            print("\nIncorrect number. Try again\n")
                                        print("\n%d\n" % fid)
                                    break
                            elif(choice == 2): #Edit
                                edit_publication(id_exist)
                                break
                            elif(choice == 3): #Delete
                                delete_publication(id_exist)
                                break
                            elif(choice == 4): #Cancel
                                break
                            else:
                                print("\nIncorrect number. Try again\n")
            elif(choice == 2): #logout
                SESSION_ID, CURRENT_USER = logout()
                break
            else:
                print("\nIncorrect number. Try again\n")
    elif(choice == 2): #exit
        exit()
    else:
        print("\nIncorrect number. Try again\n")