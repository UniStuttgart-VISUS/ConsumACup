# Import necessary libraries and classes
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import *       # This gets the Qt stuff
from PyQt5.QtCore import *
import os

import back_end.session as session 
from back_end.manage_db import DBManager

# from front_end.sidebar_base import SidebarBase

from front_end.login_screen import LoginScreen
from front_end.thank_you_screen import ThankYouScreen

import RUNTIME_CONFIG as cfg 


class RefillScreen(QMainWindow):
    def __init__(self, stackedPages, nfcThread=None):

        super().__init__()
        loadUi("front_end/ui_files/refill_screen.ui", self)
        self.stackedPages = stackedPages

        self.nfcThread = nfcThread

        self.coffee_resource_list = []
    
        self.btnSubmit.clicked.connect(self.submit_refill)
        self.btnSaveRecipe.clicked.connect(self.submit_recipe)
        self.dateTimeEdit.setDateTime(QDateTime.currentDateTime())

        self.btnKeyboard.clicked.connect(self.show_keyboard)
        self.btnKeyboard_2.clicked.connect(self.show_keyboard)


        self.generate_data()

        self.cbRecipeName.currentTextChanged.connect(self.fill_recipe_data)

        list_coffee_type = self.resources_coffee()
        self.cbBeanRefill.addItems(list_coffee_type)

    def show_keyboard(self):
        try:
            os.system('dbus-send --type=method_call --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.Show')
        except:
            pass
        

    # submit_refill: updates coffee bean type in refill DB table based on user input
    def submit_refill(self):

        content = self.cbBeanRefill.currentText()
        timestamp = self.dateTimeEdit.dateTime()
        refill_time = timestamp.toString(Qt.DateFormat.ISODateWithMs)
        db = DBManager()
        server_time = db.getTime()
        server_time_zone = server_time.split()[-1]
        refill_time = refill_time.replace('T', ' ') + f" {server_time_zone}"
        bean_product_id = db.getBeanProductIDfromName(content)
        db.close_connection()

        if session.LOGGED_IN == True:
            db = DBManager()
            db.submitBeanRefill(session.USER_ID, bean_product_id, refill_time)
            db.close_connection()

            content = "rb"
            ty = ThankYouScreen(content)
            self.stackedPages.addWidget(ty.thankYouPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        else:
            print("LOGIN SCREEN")
            goingTo = "REFILL"
            self.login = LoginScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread, goingTo=goingTo)
            self.stackedPages.addWidget(self.login.loginPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
    
    def submit_recipe(self):
        if session.LOGGED_IN == True:
            recipe_name = self.cbRecipeName.currentText()
            bean_product = self.cbBeanConfig.currentText()
            portafilter = self.cbInsert.currentText()
            grind_size = self.cbGrind.currentText()
            grind_duration = self.cbGrindDuration.currentText()
            extraction_duration = self.cbExtractionDuration.currentText()
            comment = "" # TODO
            
            db = DBManager()
            bean_product_id = db.getBeanProductIDfromName(bean_product)
            print(f"bean_product_id {bean_product_id}, session.USER_ID {session.USER_ID}, portafilter {portafilter}, grind_size {grind_size}, grind_duration {grind_duration}, extraction_duration {extraction_duration}, recipe_name {recipe_name}")
            res = db.insertOrUpdateRecipe(bean_product_id, session.USER_ID, portafilter, grind_size, grind_duration, extraction_duration, recipe_name)
            db.close_connection()

            if res:
                self.lblError.setText(res)
            else:
                self.generate_data()
                content = "rc"
                ty = ThankYouScreen(content)
                self.stackedPages.addWidget(ty.thankYouPage)
                self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() +1)
        else:
            goingTo = "REFILL"
            self.login = LoginScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread, goingTo=goingTo)
            self.stackedPages.addWidget(self.login.loginPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
        
    def generate_data(self):
        self.cbRecipeName.clear()
        rnl = self.get_recipe_names()
        self.cbRecipeName.addItems(rnl)

        self.cbBeanConfig.clear()
        ctl = self.resources_coffee()
        self.cbBeanConfig.addItems(ctl)

    def fill_recipe_data(self):
        self.lblError.setText("")
        recipe_name = self.cbRecipeName.currentText()

        if recipe_name == "": return

        db = DBManager()
        self.recipe = db.getRecipe(recipe_name)
        db.close_connection()

        if self.recipe:
            bean_product_id = self.recipe['bean_product_id']
            portafilter = self.recipe['portafilter']
            grind_size = self.recipe['grind_size']
            grind_duration = self.recipe['grind_duration']
            extraction_duration = self.recipe['extraction_duration']

            db = DBManager()
            bean_name = db.getBeanProductName(bean_product_id)
            db.close_connection()

            self.cbBeanConfig.setCurrentText(bean_name)
            self.cbInsert.setCurrentText(portafilter)
            self.cbGrind.setCurrentText(str(grind_size))
            self.cbGrindDuration.setCurrentText(str(grind_duration))
            self.cbExtractionDuration.setCurrentText(str(extraction_duration))

    def resources_coffee(self):
        db = DBManager()
        self.coffee_resource_list = db.getCoffeeResources()

        return_coffee_type_list =[]
        for entry in self.coffee_resource_list:
            bean_name = db.getBeanProductName(entry['product_id'])
            return_coffee_type_list.append(bean_name)

        db.close_connection()
        return return_coffee_type_list
    
    def get_recipe_names(self):
        db = DBManager()
        self.recipe_names = db.getRecipeNames()
        db.close_connection()
        recipe_names_list =[]
        recipe_names_list.append("") # first entry is empty string
        if len(self.recipe_names)>1:
            for x in self.recipe_names:
                recipe_names_list.append(x[0])
        else:
            recipe_names_list.append(self.recipe_names[0][0])
        return recipe_names_list