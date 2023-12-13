from PyQt5.QtChart import QChart, QChartView
import os

from PyQt5.QtCore import *
from PyQt5.uic import loadUi

 # Import necessary libraries and classes
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import *  

import back_end.session as session
from back_end.manage_db import DBManager
from back_end.focus_tracker import FocusTracker

from front_end.login_screen import LoginScreen
from front_end.thank_you_screen import ThankYouScreen
from front_end.charts.drilldown_chart import *
# from front_end.rating_screen import RatingScreen

import RUNTIME_CONFIG as cfg 

class CustomTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, parent=None):
        super().__init__(text)
        self.parent_table = parent  # Store a reference to the parent table

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.parent_table.focus_tracker.last_focused_widget = self

class ResourcesScreen(QMainWindow):
    # Class Variables to access data from database
    coffee_resource_list=[]
    milk_resource_list=[]
    sugar_resource_list=[]

    def __init__(self, stackedPages, nfcThread=None):

        super().__init__() # in super :self.__class__, self
        loadUi("front_end/ui_files/resources_screen.ui", self)

        self.stackedPages = stackedPages

        self.nfcThread = nfcThread

        self.tabWidget.setCurrentIndex(0)
        
        self.chartContainer.setContentsMargins(0,0,0,0)
        self.lay = QHBoxLayout(self.chartContainer)
        self.lay.setContentsMargins(0,0,0,0)

        self.reload()

        # Reload resources when tab is changed
        self.tabWidget.currentChanged.connect(self.reload)

        #self.dateTimeEdit.setDateTime(QDateTime.currentDateTime())

        #list_coffee_type = self.resources_coffee()
        db = DBManager()
        list_coffee_type = db.getAllBeanProducts()
        db.close_connection()
        self.cbCoffee.addItems(list_coffee_type)

        #list_milk_type = self.resources_milk()
        db = DBManager()
        list_milk_type = db.getAllMilkProducts()
        db.close_connection()
        self.cbMilk.addItems(list_milk_type)

        list_sugar_type = self.resources_sugar()
        self.cbSugar.addItems(list_sugar_type)

        self.btnAddToStock.clicked.connect(self.add_stock)
        self.btnUpdateStock.clicked.connect(self.update_stock)

        self.btnKeyboard.clicked.connect(self.show_keyboard)
        self.btnKeyboard_es.clicked.connect(self.show_keyboard)

        self.tableWidget.setColumnWidth(0, 120)
        self.tableWidget.setColumnWidth(1, 350)
        self.tableWidget.setColumnWidth(2, 110)
        
        # Connect focus events to the custom slot
        self.focus_tracker = FocusTracker(self)
        self.cbAmountCoffee.installEventFilter(self.focus_tracker)
        self.cbPriceCoffee.installEventFilter(self.focus_tracker)
        self.cbAmountMilk.installEventFilter(self.focus_tracker)
        self.cbPriceMilk.installEventFilter(self.focus_tracker)
        self.cbAmountSugar.installEventFilter(self.focus_tracker)

        self.generate_edit_resources()

    def show_keyboard(self):
        try:
            os.system('dbus-send --type=method_call --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.Show')
        except:
            pass
        if self.focus_tracker.last_focused_widget:
            self.focus_tracker.last_focused_widget.setFocus()
    

    # Reload:    refreshes self.coffee_resource_list, self.milk_resource_list, self.sugar_resource_list from DB
    #            deletes items in QHBoxLayout and creates bar chart
    def reload(self):
        print("Reloading")

        db = DBManager()
        self.coffee_resource_list, self.milk_resource_list, self.sugar_resource_list= db.getAllResourcesWithNames()
        db.close_connection()

        # delete all widgets before adding new chart view
        for i in reversed(range(self.lay.count())): 
            self.lay.itemAt(i).widget().deleteLater()

        chart_view = self.create_bar()
        self.lay.addWidget(chart_view)
        self.btnDrillUp.setVisible(False)

    # Resource Stock Overview Tab
    def create_bar(self):
        # 1st level
        categorie_list = ["Coffee", "Milk", "Sugar"]

        # removing 0 valued resources from chart
        m_coffee_resource_list = []
        for ele in self.coffee_resource_list:
            if ele[1]>0:
                m_coffee_resource_list.append(ele)

        m_milk_resource_list = []    
        for ele in self.milk_resource_list:
            if ele[1]>0:
                m_milk_resource_list.append([ele[0], ele[1] * 1000])

        m_sugar_resource_list = []
        for ele in self.sugar_resource_list:
            if ele[1]>0:
                m_sugar_resource_list.append([ele[0], ele[1]])

        # 2nd level
        resource_list = [m_coffee_resource_list, m_milk_resource_list, m_sugar_resource_list]


        print(resource_list)

        # Create the drilldown chart
        drilldownChart = DrilldownChart(self.btnDrillUp, 'Resources Overview', categorie_list, resource_list)
        drilldownChart.setAnimationOptions(QChart.SeriesAnimations)
        chartView = QChartView(drilldownChart)
        drilldownChart.genChart()
        drilldownChart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        return chartView
    
    # resources_coffee, -milk, -sugar: fills respective combobox
    def resources_coffee(self):
        db = DBManager()
        return_coffee_type_list =[]
        for x in self.coffee_resource_list:
            return_coffee_type_list.append(x[0])
        db.close_connection()
        return return_coffee_type_list
        
    def resources_milk(self):
        db = DBManager()
        return_milk_type_list =[]
        for x in self.milk_resource_list:
            return_milk_type_list.append(x[0])
        db.close_connection()
        return return_milk_type_list
    
    def resources_sugar(self):
        db = DBManager()
        return_sugar_type_list =[]
        for x in self.sugar_resource_list:
            return_sugar_type_list.append(x[0])
        db.close_connection()
        return return_sugar_type_list
        
    # add_stock: adds coffee, milk and sugar stocks based on user entries
    def add_stock(self):
        
        contentCoffee = self.cbCoffee.currentText()
        contentMilk = self.cbMilk.currentText()
        contentSugar = self.cbSugar.currentText()
        
        amountCoffee = self.cbAmountCoffee.currentText()
        amountMilk = self.cbAmountMilk.currentText()
        amountSugar = self.cbAmountSugar.currentText()

        priceCoffee = self.cbPriceCoffee.currentText()
        priceMilk = self.cbPriceMilk.currentText()
        #priceSugar = self.cbPriceSugar.currentText()

        #timestamp = self.dateTimeEdit.dateTime()
        #db_timestamp = timestamp.toString(Qt.DateFormat.ISODateWithMs)

        if session.LOGGED_IN == True:
            if contentCoffee !="":
                db = DBManager()
                db.updateResourcesBeans(contentCoffee, priceCoffee, amountCoffee, session.USER_ID)
                db.close_connection()
            if contentMilk !="":
                db = DBManager()
                db.updateResourcesMilk(contentMilk, priceMilk, amountMilk, session.USER_ID)
                db.close_connection()    
            if contentSugar !="":
                db = DBManager()
                db.updateResourcesSugar(contentSugar, amountSugar, session.USER_ID)
                db.close_connection()            
        
            content = "ap"
            ty = ThankYouScreen(content)
        
            self.stackedPages.addWidget(ty.thankYouPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        else:
            print("LOGIN SCREEN")
            goingTo = "RESOURCES"
            self.login = LoginScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread, goingTo=goingTo)
            self.stackedPages.addWidget(self.login.loginPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

    # generate_edit_resources: creates editable resource table for coffee, milk and sugar into one big table
    def generate_edit_resources(self):
        for coffee_entry in self.coffee_resource_list:
            row_count = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_count)
            self.tableWidget.setRowHeight(row_count, 80)

            item_type = CustomTableWidgetItem("Coffee", self.tableWidget)
            item_type.setFlags(item_type.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_type_name = CustomTableWidgetItem(coffee_entry[0], self.tableWidget)
            item_type_name.setFlags(item_type_name.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.tableWidget.setItem(row_count,0,item_type)
            self.tableWidget.setItem(row_count,1,item_type_name)
            # self.tableWidget.setItem(row_count,2,QTableWidgetItem(str(coffee_entry[1])))
            sb = QDoubleSpinBox(self)
            #sb.setButtonSymbols(QAbstractSpinBox.PlusMinus)
            font = sb.font()
            # setting point size
            font.setPointSize(15)
            # reassigning this font to the spin box
            sb.setFont(font)
            sb.setMaximum(999999)
            sb.setValue(coffee_entry[1]/1000)
            self.tableWidget.setCellWidget(row_count,2,sb)

        for milk_entry in self.milk_resource_list:
            row_count = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_count)
            self.tableWidget.setRowHeight(row_count, 80)

            item_type = CustomTableWidgetItem("Milk", self.tableWidget)
            item_type.setFlags(item_type.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_type_name = CustomTableWidgetItem(milk_entry[0], self.tableWidget)
            item_type_name.setFlags(item_type_name.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.tableWidget.setItem(row_count,0,item_type)
            self.tableWidget.setItem(row_count,1,item_type_name)
            # self.tableWidget.setItem(row_count,2,QTableWidgetItem(str(milk_entry[1])))
            sb = QDoubleSpinBox(self)
            #sb.setButtonSymbols(QAbstractSpinBox.PlusMinus)
            # getting font of the spin box
            font = sb.font()
            # setting point size
            font.setPointSize(15)
            # reassigning this font to the spin box
            sb.setFont(font)
            sb.setMaximum(999999)
            sb.setValue(milk_entry[1])
            self.tableWidget.setCellWidget(row_count,2,sb)

        for sugar_entry in self.sugar_resource_list:
            row_count = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_count)
            self.tableWidget.setRowHeight(row_count, 80)

            item_type = CustomTableWidgetItem("Sugar", self.tableWidget)
            item_type.setFlags(item_type.flags() & ~Qt.ItemFlag.ItemIsEditable)

            item_type_name = CustomTableWidgetItem(sugar_entry[0], self.tableWidget)
            item_type_name.setFlags(item_type_name.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.tableWidget.setItem(row_count,0,item_type)
            self.tableWidget.setItem(row_count,1,item_type_name)
            # self.tableWidget.setItem(row_count,2,QTableWidgetItem(str(sugar_entry[1])))
            sb = QDoubleSpinBox(self)
            #sb.setButtonSymbols(QAbstractSpinBox.PlusMinus)
            font = sb.font()
            # setting point size
            font.setPointSize(15)
            # reassigning this font to the spin box
            sb.setFont(font)
            sb.setMaximum(999999)
            sb.setValue(sugar_entry[1])
            self.tableWidget.setCellWidget(row_count,2,sb)

    # update_stock: updates existing resources based on user entries
    def update_stock(self):
        if session.LOGGED_IN == True:
            for row in range(self.tableWidget.rowCount()):
                product_type = self.tableWidget.item(row, 0).text()
                product_name =self.tableWidget.item(row, 1).text()
                sb = self.tableWidget.cellWidget(row, 2).value()

                if product_type == "Coffee":
                    sb = sb *1000
                    db = DBManager()
                    bean_product_id = db.getBeanProductIDfromName(product_name)
                    db.updateBeanStock(session.USER_ID, sb, bean_product_id)
                    db.close_connection()
                if product_type == "Milk":
                    db = DBManager()
                    milk_product_id = db.getMilkProductIDfromName(product_name)
                    db.updateMilkStock(session.USER_ID, sb, milk_product_id)
                    db.close_connection()
                if product_type == "Sugar":
                    sb = sb
                    db = DBManager()
                    sugar_type_id = db.getSugarTypeIDFromName(product_name)
                    db.updateSugarStock(session.USER_ID, sb, sugar_type_id)
                    db.close_connection()
        
            content = "es"
            ty = ThankYouScreen(content)
        
            self.stackedPages.addWidget(ty.thankYouPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

        else:
            print("LOGIN SCREEN")
            goingTo = "RESOURCES"
            self.login = LoginScreen(stackedPages=self.stackedPages, nfcThread=self.nfcThread, goingTo=goingTo)
            self.stackedPages.addWidget(self.login.loginPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)