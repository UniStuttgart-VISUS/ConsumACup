# This scripts checks if the raspberry pi receivs any kind of input to track
# the users activness. If the user is not active a logout signal is beeing emitted

import time
import subprocess
# from PyQt5.QtCore import QThread, pyqtSignal
import back_end.session as session 
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

# class IdleCheckerThread(QThread):
#     # Define a signal 'tag' to emit signals to the main application
#     tag = pyqtSignal(str)

#     # Define the __init__ function to initialize the thread
#     def __init__(self, time_to_logout, parent=None):
#         #super().__init__(parent)
#         QThread.__init__(self)
#         self.time_to_logout = time_to_logout

#     # Define the run function to execute the thread's main loop
#     def run(self):
#         while True:
#             time.sleep(1)
#             self.check_if_idle()

#     # Define a function to stop the thread
#     def stop(self):
#         self.terminate()

#     # Define a function to set the time threshold for automatic logout
#     def setTimeToLogout(self, t):
#         self.time_to_logout = t

#     # Checks if the user is idle on Linux
#     def check_if_idle(self):
#         idle_time = int(subprocess.getoutput('xprintidle')) / 1000
#         if not session.LOGGED_IN and idle_time > 10:
#             # subprocess.call(["xdotool", "mousemove", "100", "100"])
#             subprocess.call(["xdotool", "click", "2"]) # click middle mouse button to restart idle time
#             idle_time = int(subprocess.getoutput('xprintidle')) / 1000

#         if idle_time > self.time_to_logout and session.LOGGED_IN: # adjust this to determine when user should be logged out
#             subprocess.call(["xdotool", "mousemove", "100", "100"]) # preventing idle
#             str_logout="logout"
#             self.tag.emit(str_logout) 
#             print("You have been logged out due to inactivity.")
#         if session.BILLED_COFFEE:
#             str_logout="logout"
#             time.sleep(5)
#             session.BILLED_COFFEE = False
#             self.tag.emit(str_logout) # Emit a signal to indicate the user has been logged out
#             print("You have been logged out automatically after billing!")



class IdleChecker(QObject):
    def __init__(self, parent=None):
        super(IdleChecker, self).__init__(parent)
        self.parent = parent
        self.idle_threshold = 15000  # Set the idle threshold in milliseconds (10 seconds)
        self.idle_time = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_idle)
        #self.reset_timer()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.MouseMove or event.type() == QEvent.KeyPress:
            if self.timer.isActive():
                self.reset_timer()
        return super(IdleChecker, self).eventFilter(obj, event)

    def reset_timer(self):
        self.timer.stop()
        self.timer.start(self.idle_threshold)
        self.idle_time = 0

    def check_idle(self):
        # self.idle_time += self.idle_threshold
        # if session.LOGGED_IN:
        #     print("Idle detected! Idle time: {} seconds".format(self.idle_time*1e-3))
        #     self.reset_timer()
        #     self.parent.go_to_exit()
        self.reset_timer()
        self.parent.go_to_exit()



class ScreensaverTimer(QObject):
    def __init__(self, parent=None):
        super(ScreensaverTimer, self).__init__(parent)
        self.screensaver_threshold = 60000  # Set the idle threshold in milliseconds (10 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.activate_screensaver)
        self.reset_timer()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.MouseMove or event.type() == QEvent.KeyPress:
            if self.timer.isActive():
                self.reset_timer()
        return super(ScreensaverTimer, self).eventFilter(obj, event)

    def reset_timer(self):
        self.timer.stop()
        self.timer.start(self.screensaver_threshold)

    def activate_screensaver(self):
        try:
            subprocess.call(["xset", "dpms", "force", "off"])
        except:
            print("xset not supported")