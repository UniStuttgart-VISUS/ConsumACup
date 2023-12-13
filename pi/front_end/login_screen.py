import time
import subprocess
import random

from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal as Signal

import back_end.session as session
from back_end.manage_db import DBManager, rfid_to_hex
from back_end.buzzer import Buzzer
#from front_end.signup_screen import SignupScreen1
from front_end.profile_screen import ProfileScreen

import RUNTIME_CONFIG as cfg 
DEBUG = cfg.DEBUG

if not DEBUG:
    from back_end.nfc_reader import NfcWorker


class LoginScreen(QMainWindow):
    work_requested = Signal(int)
    
    def __del__(self):
        print("[DESTRUCTOR LOG] Login Screen is beeing destroyed")
        if not DEBUG:
            try:
                self.worker.setn(0)
                self.worker.deleteLater()
            except:
                print("[EXCEPTION HANDLED] Worker already deleted, continue ...")


    def __init__(self, stackedPages, goingTo=None, nfcThread=None):
        super().__init__() 

        loadUi("front_end/ui_files/login_screen_no_signup.ui",self)

        self.stackedPages = stackedPages

        self.goingTo = goingTo

        # Set the password input field to hide the entered text
        self.lePassword.setEchoMode(QtWidgets.QLineEdit.Password)
        self.btnLogin.clicked.connect(self.login_function)
        # self.btnSignUp.clicked.connect(self.go_to_Signup)

        if not DEBUG:
            self.nfcThread = nfcThread
            self.worker = NfcWorker()

            self.worker.moveToThread(self.nfcThread)

            self.worker.tag.connect(self.searchUid)
            self.work_requested.connect(self.worker.setn)

            self.nfcThread.start()
            self.work_requested.emit(1)
            print("[Thread Log] Stared NfcReader Thread from login_screen!")
        else:
            self.nfcThread = nfcThread

    def searchUid(self, uid):
        rfid = rfid_to_hex(uid)
        print(f"Trying login with RFID {rfid}")
        db = DBManager()
        user_id = db.getIDfromRFID(rfid)
        db.close_connection()

        if user_id == "":
            print("Login Failed")
            bz = Buzzer()
            bz.buzz_decline()
            bz.buzz_close()
            session.LOGGED_IN = False
            self.lblError.setText("RFID Code not registered, please sign up first!")
            time.sleep(3)
            self.lblError.setText("")
        else:
            db = DBManager()
            first_name, last_name = db.getName(user_id)
            db.close_connection()
            print(f"Found RFID {rfid} in the database. The Name is {first_name} {last_name}")

            session.LOGGED_IN = True
            session.USER_ID = user_id
            if not DEBUG:
                self.worker.setn(0)
                self.worker.deleteLater()
                bz = Buzzer()
                bz.buzz_confirm()
                bz.buzz_close()
                # reset idle
                try:
                    pos = random.randint(1,400)
                    subprocess.call(["xdotool", "mousemove", f"{pos}", f"{pos}"])
                except:
                    print("xdotool not supported")
            self.goToPage()
    
    def check_credentials(self):
        print("Checking Credentials in login_screen")
        login_name = self.leUsername.text()
        password = self.lePassword.text()
        logged_in = False

        if len(login_name)==0 or len(password)==0:
            self.lblError.setText("Please input all fields.")
            logged_in = False
        else:
            self.lblError.setText("")

            db = DBManager()
            user_id = db.checkCredentials(login_name, password)
            db.close_connection()

            if user_id:
                self.lblError.setText("")
                session.LOGGED_IN = True
                session.USER_ID = user_id
                print("Successfully logged in.")
                logged_in = True
                #print("Print in login_screen: " + str(name_and_userId))
            else:
                self.lblError.setText("Invalid username or password")
                logged_in = False
        
        return logged_in

    def goToPage(self):  
        if self.goingTo == "PROFILE":
            self.profile = ProfileScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
            self.stackedPages.addWidget(self.profile.profilePage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
        
        if self.goingTo in ["RATING", "RESOURCES", "STATS", "REFILL"]:
            print("REMOVING WIDGET WITH NAME: " + self.stackedPages.widget(self.stackedPages.currentIndex()).objectName())
            self.stackedPages.widget(self.stackedPages.currentIndex()).deleteLater()
            self.stackedPages.removeWidget(self.stackedPages.widget(self.stackedPages.currentIndex()))
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex())

    def login_function(self):
        logged_in = self.check_credentials()
        if logged_in:
            self.goToPage()

    
    # def go_to_Signup(self):
    #     if not DEBUG:
    #         try:
    #             self.worker.setn(0)
    #             self.worker.deleteLater()
    #         except:
    #             print("[EXCEPTION HANDLED] Worker already deleted, continue ...")

    #     print ("Going to Signup")

    #     self.signup = SignupScreen1(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
    #     self.stackedPages.addWidget(self.signup.SignupPage1)
    #     self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)


            