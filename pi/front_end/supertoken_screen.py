import time

from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal as Signal

import back_end.session as session
from back_end.manage_db import DBManager
from back_end.buzzer import Buzzer
from front_end.welcome_screen import WelcomeScreen

from back_end.get_password import DBPasswordCipher

import RUNTIME_CONFIG as cfg
DEBUG = cfg.DEBUG

if not DEBUG:
    from back_end.nfc_reader import NfcWorker


class SupertokenScreen(QMainWindow):
    work_requested = Signal(int)
    
    def __del__(self):
        print("[DESTRUCTOR LOG] Supertoken Screen is beeing destroyed")
        if not DEBUG:
            try:
                self.worker.setn(0)
                self.worker.deleteLater()
            except:
                print("[EXCEPTION HANDLED] Worker already deleted, continue ...")


    def __init__(self, stackedPages, goingTo=None, nfcThread=None, sidebar=None):
        super().__init__() 

        loadUi("front_end/ui_files/supertoken_screen.ui",self)

        self.stackedPages = stackedPages

        self.goingTo = goingTo

        self.sidebar = sidebar

        ## disable sidebar buttons
        if self.sidebar:
            self.sidebar.setEnabled(False)

        if not DEBUG:
            self.nfcThread = nfcThread
            self.worker = NfcWorker()

            self.worker.moveToThread(self.nfcThread)

            self.worker.tag.connect(self.checkPassword)
            self.work_requested.connect(self.worker.setn)

            self.nfcThread.start()
            self.work_requested.emit(1)
            print("[Thread Log] Stared NfcReader Thread from Supertoken screen!")
        else:
            self.nfcThread = nfcThread

    def checkPassword(self, uid):
        print(f"UID: {uid}")
        decipher = DBPasswordCipher()
        password = decipher.get_password(uid)
        session.DB_PASSWORD = password

        # test connection
        db = DBManager()
        time = db.getTime()
        db.close_connection()

        if time is None:
            print("Supertoken Failed")
            bz = Buzzer()
            bz.buzz_decline()
            bz.buzz_close()
            self.lblError.setText("Connection to DB failed!")
            time.sleep(3)
            self.lblError.setText("")

        else:
            print("Connection to DB established")
            if not DEBUG:
                self.worker.setn(0)
                self.worker.deleteLater()
                bz = Buzzer()
                bz.buzz_confirm()
                bz.buzz_close()
            # enable buttons again and switch page
            self.sidebar.setEnabled(True)
            self.goToPage()
    
    def goToPage(self):  
        if self.goingTo == "WELCOME":
            self.welcome = WelcomeScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
            self.stackedPages.addWidget(self.welcome.welcomePage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

