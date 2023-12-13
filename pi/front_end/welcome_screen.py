import subprocess
import random
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import * 
import time

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QEvent
from PyQt5.QtGui import QMouseEvent

import back_end.session as session
from back_end.manage_db import DBManager, rfid_to_hex
from back_end.buzzer import Buzzer

from front_end.billing_screen import BillOrLimitScreen

import RUNTIME_CONFIG as cfg 
DEBUG = cfg.DEBUG

if not DEBUG:
    from back_end.nfc_reader import NfcWorker

class WelcomeScreen(QMainWindow):
    # Define a signal 
    work_requested = pyqtSignal(int)

    # Destructor method to handle cleanup
    def __del__(self):
        print("[DESTRUCTOR LOG] welcome_screen is beeing destroyed")
        if not DEBUG:
            try:
                self.worker.setn(0)
                self.worker.deleteLater()
            except:
                print("[EXCEPTION HANDLED] Worker already deleted, continue ...")


    def __init__(self, stackedPages, nfcThread=None):
        print("NEW WELCOME SCREEN")
        
        super().__init__() # in super : self.__class__, self
        loadUi("front_end/ui_files/welcome_screen.ui", self)

        self.stackedPages = stackedPages

        if not DEBUG:
            # configure NFC worker and thread
            self.nfcThread = nfcThread
            self.worker = NfcWorker()

            # Move the NFC worker to the NFC thread
            self.worker.moveToThread(self.nfcThread)

            # Connect signals and slots for NFC communication
            self.worker.tag.connect(self.searchUid)
            self.work_requested.connect(self.worker.setn)

            # Start the thread and request work
            self.nfcThread.start()
            self.work_requested.emit(1)
            print("[Thread Log] Stared NfcReader Thread from welcome_screen!")
        else:
            self.nfcThread = nfcThread

    # Search for a user's RFID in database
    def searchUid(self, uid):
        rfid = rfid_to_hex(uid)
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
                self.work_requested.emit(0)
                bz = Buzzer()
                bz.buzz_confirm()
                bz.buzz_close()
            
            if session.MAINWINDOW:
                session.MAINWINDOW.enable_idle_timeout(True)
            
            try:
                subprocess.call(["xset", "dpms", "force", "on"])
                pos = random.randint(1, 400)
                subprocess.call(["xdotool", "mousemove", f"{pos}", f"{pos}"])
            except:
                print("xset or xdotool not supported")

            self.billingScreen = BillOrLimitScreen(self.stackedPages)
                
            