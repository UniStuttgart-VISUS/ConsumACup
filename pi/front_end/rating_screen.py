from PyQt5.uic import loadUi
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt

import back_end.session as session

from front_end.thank_you_screen import ThankYouScreen
from back_end.manage_db import DBManager

import RUNTIME_CONFIG as cfg 

class RatingScreen(QMainWindow):
    def __init__(self, stackedPages):
        #super(LoginScreen, self).__init__()
        super(self.__class__, self).__init__()
        loadUi("front_end/ui_files/rating_screen.ui", self)

        self.stackedPages = stackedPages
        self.rating = 0
        self.bean_product = ''
        self.bean_product_id = -1

        self.update_coffeebeanlbl_function()

        self.style_sheet_unmarked = 'border-radius:15px;background-color: rgb(81, 116, 168);color: white;font: 14pt "Lora";'
        self.style_sheet_marked = 'border-radius:15px;background-color: rgb(40, 57, 83);color: white;font: 14pt "Lora";'

        self.btnSubmit.clicked.connect(self.submit_function)

        self.btnRating1.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating2.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating3.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating4.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating5.setStyleSheet(self.style_sheet_unmarked)

        self.btnRating1.clicked.connect(self.rating1_function)
        self.btnRating2.clicked.connect(self.rating2_function)
        self.btnRating3.clicked.connect(self.rating3_function)
        self.btnRating4.clicked.connect(self.rating4_function)
        self.btnRating5.clicked.connect(self.rating5_function)

    def update_coffeebeanlbl_function(self):
        print ("Update Coffee bean type")
        # Database request for checking user_name duplicates
        
        db = DBManager()
        self.bean_product = db.getRefillBeanType()
        self.bean_product_id = db.getRefillBeanID()
        db.close_connection()
        
        self.lblRatingBeanSort.setText(self.bean_product)
        self.lblRatingBeanSort.setAlignment(Qt.AlignCenter)

    def submit_function(self):
        db = DBManager()
        db.submitBeanRating(session.USER_ID, self.bean_product_id, self.rating)
        db.close_connection()  

        content = "cbr"
        ty = ThankYouScreen( content)
        
        self.stackedPages.addWidget(ty.thankYouPage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

    def rating1_function(self):
        self.rating = 1
        self.btnRating1.setStyleSheet(self.style_sheet_marked)
        self.btnRating2.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating3.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating4.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating5.setStyleSheet(self.style_sheet_unmarked)

    def rating2_function(self):
        self.rating = 2
        self.btnRating1.setStyleSheet(self.style_sheet_marked)
        self.btnRating2.setStyleSheet(self.style_sheet_marked)
        self.btnRating3.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating4.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating5.setStyleSheet(self.style_sheet_unmarked)

    def rating3_function(self):
        self.rating = 3
        self.btnRating1.setStyleSheet(self.style_sheet_marked)
        self.btnRating2.setStyleSheet(self.style_sheet_marked)
        self.btnRating3.setStyleSheet(self.style_sheet_marked)
        self.btnRating4.setStyleSheet(self.style_sheet_unmarked)
        self.btnRating5.setStyleSheet(self.style_sheet_unmarked)

    def rating4_function(self):
        self.rating = 4
        self.btnRating1.setStyleSheet(self.style_sheet_marked)
        self.btnRating2.setStyleSheet(self.style_sheet_marked)
        self.btnRating3.setStyleSheet(self.style_sheet_marked)
        self.btnRating4.setStyleSheet(self.style_sheet_marked)
        self.btnRating5.setStyleSheet(self.style_sheet_unmarked)

    def rating5_function(self):
        self.rating = 5
        self.btnRating1.setStyleSheet(self.style_sheet_marked)
        self.btnRating2.setStyleSheet(self.style_sheet_marked)
        self.btnRating3.setStyleSheet(self.style_sheet_marked)
        self.btnRating4.setStyleSheet(self.style_sheet_marked)
        self.btnRating5.setStyleSheet(self.style_sheet_marked)