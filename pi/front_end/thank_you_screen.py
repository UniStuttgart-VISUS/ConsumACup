from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QMainWindow

import RUNTIME_CONFIG as cfg 

class ThankYouScreen(QMainWindow):
    def __init__(self, content,*args, **kwargs):
        super(self.__class__, self).__init__()
        loadUi("front_end/ui_files/thank_you_screen.ui", self)

        self.content = content

        # set the Thank You message according to content 
        if content == "cbr":
            print("TY screen for coffee bean rating")
            self.lblThankYou.setText("Thank you for rating!")
        elif content =="su":
            print("TY screen for Sign Up")
            self.lblThankYou.setText("Thank you for signing up!")
        elif content =="rb":
            print("TY screen for refill beans")
            self.lblThankYou.setText("Thank you for refilling!")
        elif content =="ap":
            print("TY screen for add purchase")
            self.lblThankYou.setText("Thank you for restocking!")
        elif content =="es":
            print("TY screen for edit stock")
            self.lblThankYou.setText("Thank you for updating!")
        elif content =="rc":
            print("TY screen for creating recipe")
            self.lblThankYou.setText("Thank you for creating a recipe!")