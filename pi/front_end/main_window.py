import os
import time

from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread, QTimer

import back_end.session as session 

from front_end.welcome_screen import WelcomeScreen
from front_end.rating_screen import RatingScreen
from front_end.login_screen import LoginScreen
from front_end.resources_screen import ResourcesScreen
from front_end.profile_screen import ProfileScreen
from front_end.refill_screen import RefillScreen
from front_end.stats_screen import StatsScreen
from front_end.supertoken_screen import SupertokenScreen

import RUNTIME_CONFIG as cfg 

DEBUG = cfg.DEBUG
# if not DEBUG:
#     from back_end.idle_checker import IdleCheckerThread
from back_end.idle_checker import IdleChecker, ScreensaverTimer

# Create the main window class, which inherits from QMainWindow
class MainWindow(QMainWindow):
    """
    A subclass of the QMainWindow with the eventFilter method.
    """
    def __init__(self, parent=None):

        QMainWindow.__init__(self)

        loadUi("front_end/ui_files/main_window.ui", self)

        self.style_sheet_unmarked = 'background-color: rgb(40, 57, 83);color: white;font: 14pt "Lora";'
        self.style_sheet_marked = 'background-color: rgb(81, 116, 168);color: white;font: 14pt "Lora";'

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_unmarked)

        self.btnProfileSidebar.clicked.connect(self.go_to_profile)
        self.btnStatsSidebar.clicked.connect(self.go_to_stats)
        self.btnRatingSidebar.clicked.connect(self.go_to_rating)
        self.btnResourcesSidebar.clicked.connect(self.go_to_resources)
        self.btnRefillSidebar.clicked.connect(self.go_to_refill)
        self.btnExitSidebar.clicked.connect(self.go_to_exit)
        
        qApp = QApplication.instance()

        if not DEBUG:
            self.nfcThread = QThread()

            self.screensaver_timer = ScreensaverTimer(self)
            qApp.installEventFilter(self.screensaver_timer)
            # self.idleThread = IdleCheckerThread(time_to_logout=15)
            # self.idleThread.tag.connect(self.go_to_exit) 
            # self.idleThread.start()
            # print("[Thread Log] Stared IdleCheckerThread in main_window!")
        else:
            self.nfcThread = None

        ## idle checker
        self.idle_checker = IdleChecker(self)
        # Install event filter on the application instance
        qApp.installEventFilter(self.idle_checker)

        self.idle_label =  self.btnExitSidebar
        self.idle_label_update_timer = QTimer(self)
        self.idle_label_update_timer.timeout.connect(self.update_idle_label)
        self.idle_label_update_frequency = 1000 # Update the label every second
        self.idle_label_update_timer.start(self.idle_label_update_frequency)

        ## start welcome or supertoken screen
        if not DEBUG:
            self.welcome = SupertokenScreen(stackedPages=self.stackedPages, goingTo="WELCOME", nfcThread=self.nfcThread, sidebar=self.sidebar)
            self.stackedPages.addWidget(self.welcome.supertokenPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
        else:
            self.welcome = WelcomeScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
            self.stackedPages.addWidget(self.welcome.welcomePage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        self.setWindowTitle("ConsumAcup")
        # self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.resize(800, 480)
        session.MAINWINDOW = self

        if not DEBUG:
            self.showFullScreen()
            time.sleep(3)
            # initially showing keyoard due to issues ...
            try:
                os.system('dbus-send --type=method_call --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.Show')
            except:
                pass
    
    def enable_idle_timeout(self, on):
        if self.idle_checker.timer.isActive() == on:
            return
        
        if on:
            self.idle_checker.timer.start(self.idle_checker.idle_threshold)
        else:
            self.idle_checker.timer.stop()

    def update_idle_label(self):
        if self.idle_checker.timer.isActive():
            time = self.idle_checker.timer.remainingTime()
            self.idle_label.setText(f"{time*1e-3:.0f}")
        else:
            self.idle_label.setText("")
        #self.idle_label.repaint()

    def clean_stackedpages(self):
        N = self.stackedPages.count()
        for i in range(N, 0, -1) :
            try:
                print("REMOVING WIDGET WITH NAME:  " + self.stackedPages.widget(i).objectName())
                self.stackedPages.widget(i).deleteLater()
                self.stackedPages.removeWidget(self.stackedPages.widget(i))
                print("CURRENT INDEX after deleting: " + str(self.stackedPages.currentIndex()))
            except AttributeError as e:
                print(str(e) + " # Top of stackedWidget is NoneType can be ignored")
        print("CURRENT INDEX after deleting all pages: " + str(self.stackedPages.currentIndex()))
        try:
            del self.welcome
        except:
            print("[EXCEPTED ERROR] Already deleted screen, continue ...")
        try:
            del self.profile 
        except:
            print("[EXCEPTED ERROR] Already deleted screen, continue ...")
        try:
            del self.login
        except:
            print("[EXCEPTED ERROR] Already deleted screen, continue ...")


    def go_to_profile(self):
        print ("Profile!")

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_marked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_unmarked)

        self.clean_stackedpages()

        if session.LOGGED_IN:
            print("LOGGED IN FOR PROFILE")
            self.profile = ProfileScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
            self.stackedPages.addWidget(self.profile.profilePage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
        else:
            print("GOING TO LOGIN SCREEN")
            goingTo = "PROFILE"
            self.login = LoginScreen(stackedPages=self.stackedPages, goingTo=goingTo, nfcThread=self.nfcThread)
            self.stackedPages.addWidget(self.login.loginPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

            self.enable_idle_timeout(True)

    def go_to_rating(self):
        print ("RATING!")

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_marked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_unmarked)

        self.clean_stackedpages()

        if session.LOGGED_IN:
            print("LOGGED IN FOR RATING")
            self.rating = RatingScreen(self.stackedPages)
            self.stackedPages.addWidget(self.rating.ratingPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
        else:
            print("GEN RATINGSCREEN in main_window 151")
            self.rating = RatingScreen(self.stackedPages)
            self.stackedPages.addWidget(self.rating.ratingPage)
            print("GOING TO LOGIN SCREEN from main_window 154")
            goingTo = "RATING"
            self.login = LoginScreen(stackedPages=self.stackedPages, goingTo=goingTo, nfcThread=self.nfcThread)
            self.stackedPages.addWidget(self.login.loginPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 2)

            self.enable_idle_timeout(True)

    def go_to_resources(self):
        print ("RESOURCES!")

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_marked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_unmarked)

        self.clean_stackedpages()

        print("LOGGED IN FOR RESOURCES")
        self.resources = ResourcesScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
        self.stackedPages.addWidget(self.resources.resourcePage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        self.enable_idle_timeout(True)

    def go_to_refill(self):
        print ("REFILL!")

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_marked)

        self.clean_stackedpages()
      
        self.refill = RefillScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
        self.stackedPages.addWidget(self.refill.refillPage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        self.enable_idle_timeout(True)

    def go_to_stats(self):
        print ("STATS!")

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_marked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_unmarked)

        self.clean_stackedpages()

        print("LOGGED IN FOR STATS")
        self.stats = StatsScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
        self.stackedPages.addWidget(self.stats.statsPage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        self.enable_idle_timeout(True)


    def go_to_exit(self):
        print ("Logging out and returning to Welcome")

        self.btnProfileSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnStatsSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRatingSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnResourcesSidebar.setStyleSheet(self.style_sheet_unmarked)
        self.btnRefillSidebar.setStyleSheet(self.style_sheet_unmarked)

        session.LOGGED_IN = False
        session.USER_ID = 0

        self.clean_stackedpages()

        print("CREATING WELCOME SCREEN AS FINAL STEP IN EXIT FUNCTION")
        self.welcome = WelcomeScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread)
        self.stackedPages.addWidget(self.welcome.welcomePage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex()+1)

        self.enable_idle_timeout(False)
