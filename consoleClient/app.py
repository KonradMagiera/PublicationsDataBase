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



# TODO  add_file (used in 2 places); open_pub; delete_pub (used in 2 places 1/2); edit_pub (used in 2 places)


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

def publications_options(id, title):
    print("\n%d. %s" % (id, title))
    print("Options:")
    print("1. Open      2. Edit     3. Delete       4. Cancel\n")
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

def delete_publication(id):
    headers= {"Authorization": create_jwt(PUBLICATIONS_ACCESS)}
    requests.delete('http://localhost:5000/publications/' + str(id), headers=headers)


while(True): # login/exit       1
    start_menu()
    try:
        choice = int(input())
    except ValueError:
        print("give valid number")
        continue
    if(choice == 1): #login
        is_logged_in, SESSION_ID, CURRENT_USER = login()

        while(is_logged_in): #          2
            profile_menu()
            try:
                choice = int(input())
            except ValueError:
                print("give valid number")
                continue
            if(choice == 1): #publications
                while(True): #choose publication and option     3
                    pubs = publications()
                    print_publications(pubs)
                    publications_menu()
                    try:
                        choice = int(input())
                    except ValueError:
                        print("give valid number")
                        continue
                    
                    if(choice == 0): #Add publication TODO
                        print("AddXX")
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

                            if(choice == 1): #Open TODO
                                print() # print pub; choice add/back/edit
                            elif(choice == 2): #Edit TODO
                                print()







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