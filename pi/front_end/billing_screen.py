import numpy as np

from PyQt5.uic import loadUi
from PyQt5.QtWidgets import *
from PyQt5.QtGui import * 
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.ticker import MaxNLocator

from back_end.manage_db import DBManager
# from back_end.email_factory import EmailFactory
# import back_end.email_config as email_config
import back_end.coffee_config as coffee_config
import back_end.session as session
from datetime import datetime, timedelta

from front_end.rating_screen import RatingScreen

import RUNTIME_CONFIG as cfg 
DEBUG = cfg.DEBUG

THRESHOLD_COFFEE = 1.0
THRESHOLD_MILK = 1.0
THRESHOLD_SUGAR = 1.0

user_config_data = None
user_config_limit = None
today_coffee_amount = None

class BillOrLimitScreen():

    def __init__(self, stackedPages):
        global user_config_data
        global user_config_limit
        global today_coffee_amount

        self.stackedPages = stackedPages

        db = DBManager()
        user_config_data = db.getConfigBillingData(session.USER_ID)
        db.close_connection()

        user_config_limit = user_config_data["bsc_daily_coffee_limit"]

        db = DBManager()
        today_coffee_amount = db.getTodaysCoffeeAmount(session.USER_ID)
        db.close_connection()

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


        print(f"[BILLING_OR_LIMIT] today_coffee_amount {today_coffee_amount}; user_config_limit {user_config_limit}")
        if user_config_limit == 0:
            self.billing_screen = BillingScreen(self.stackedPages)
            self.stackedPages.addWidget(self.billing_screen.billingPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
            return
        
        if today_coffee_amount >= user_config_limit:
            self.limit = LimitScreen(self.stackedPages)
            self.stackedPages.addWidget(self.limit.limitPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
        else:
            self.billing_screen = BillingScreen(self.stackedPages)
            self.stackedPages.addWidget(self.billing_screen.billingPage)
            self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)

class LimitScreen(QMainWindow):
    def __init__(self, stackedPages):
        super().__init__() # in super :self.__class__, self
        loadUi("front_end/ui_files/limit_screen.ui",self)
        tcoii = today_coffee_amount+1
        
        self.lblLimit.setText(  '<html><head/><body><p align="center"><span style=" color:#aa0000;">'+
                                "You have reached your daily coffee limit of "+str(user_config_limit)+" cups!"+
                                "<br/> This would be your "+ str(tcoii)+ " cup.<br/>"
                                "Press ignore to bill anyway!"+
                                '</span></p></body></html>')

        # super().__init__()
        self.stackedPages = stackedPages
        self.btnIgnore.clicked.connect(self.go_to_billing_screen)
            
    def go_to_billing_screen(self):
        self.billing_screen = BillingScreen(self.stackedPages)
        self.stackedPages.addWidget(self.billing_screen.billingPage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)


class BillingScreen(QMainWindow):
    def __init__(self, stackedPages):
        super().__init__()
        loadUi("front_end/ui_files/billing_screen.ui",self)
        self.stackedPages = stackedPages

        self.btnRating.clicked.connect(self.rating_function)

        # self.chartContainer.setStyleSheet("background-color: white;")
        self.lay = QHBoxLayout(self.chartContainer)

        self.bill_coffee()

        self.display_billing_information()

    def rating_function(self):
        print ("Coffeebean Rating")
        self.rating = RatingScreen(self.stackedPages)
        self.stackedPages.addWidget(self.rating.ratingPage)
        self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)


    def bill_coffee(self):
        def checkNotNoneType(t):
            if 'NoneType' in str(t) or 'None' in str(t):
                return False
            else:
                return True
        # getting all information to bill coffee       
        user_id = session.USER_ID

        notification_resource_names = []

        # buy coffee
        db = DBManager()
        db.billCoffee(user_id)
        # Coffee Amount Calculation
        self.coffee_bean_id = db.getRefillBeanID()
        self.bean_stock = db.getBeanStockOf(self.coffee_bean_id)
        # get insert for coffee amount measurement
        self.u_portafilter = db.getUserProfilePortafilter(user_id)
        db.close_connection()

        if self.u_portafilter == "small":
            c_insert = coffee_config.COFFEE_WEIGHT_SMALL_INSERT
        elif self.u_portafilter == "large":
            c_insert = coffee_config.COFFEE_WEIGHT_LARGE_INSERT
        else: #default ist small
            c_insert = coffee_config.COFFEE_WEIGHT_DEFAULT_INSERT


        if checkNotNoneType(self.bean_stock):
            cal_coffee = float(self.bean_stock) - c_insert
            if cal_coffee < 0:
                cal_coffee = 0
            if cal_coffee <= THRESHOLD_COFFEE: #email_config.THRESHOLD_COFFEE:
                notification_resource_names.append((self.coffee_bean_id, cal_coffee))
        else:
            cal_coffee = None

        # Milk Amount Calculation
        db = DBManager()
        milk_type = db.getUserProfileMilkType(user_id)
        self.milk_stock = db.getStockOfMilkType(milk_type)
        self.milk_shots = db.getUserProfileMilkShots(user_id)
        milk_product_ids = db.getMilkProductIDsOfTypeInStock(milk_type)
        db.close_connection()

        if milk_product_ids is None:
            milk_product_id = None
        elif milk_product_ids == []:
            milk_product_id = None
        else:
            if len(milk_product_ids) > 1:
                db = DBManager()
                lowest_stock = float("inf")
                mp_id_stocks = []
                for mp_id in milk_product_ids:
                    mp_id_stock = db.getMilkStockOf(mp_id[0])
                    mp_id_stocks.append(mp_id_stock)
                    lowest_stock = min(lowest_stock, mp_id_stock)
                db.close_connection()
                if np.isinf(lowest_stock):
                    milk_product_id = None
                else:
                    self.milk_stock = lowest_stock
                    mp_id_stocks = np.array(mp_id_stocks)
                    milk_product_id = np.where(mp_id_stocks == lowest_stock)[0][0]
            else:
                milk_product_id = milk_product_ids[0][0]
            

        def numeric(equation):
            y = equation[:-4].split('/') #removing the " cup" from 1/8 cup and splitting by /
            x = float(y[0])/float(y[1])
            return x

        print(self.milk_shots)

        if checkNotNoneType(self.milk_stock) and checkNotNoneType(self.milk_shots):
            cal_milk = float(self.milk_stock) - (numeric(self.milk_shots) * coffee_config.CUP_INFILL)
        elif checkNotNoneType(self.milk_stock):
            cal_milk = float(self.milk_stock) - 0
        else:
            cal_milk = None
      
        if cal_milk and cal_milk < 0:
            cal_milk = 0

        if checkNotNoneType(cal_milk):
            if cal_milk <= THRESHOLD_MILK: #email_config.THRESHOLD_MILK:
                notification_resource_names.append((milk_type, cal_milk))

        # Milk Amount Calculation
        db = DBManager()
        sugar_type = db.getUserProfileSugarType(user_id)
        self.sugar_amount = db.getSugarTypeAmount(sugar_type)
        self.sugar_tsp = db.getUserProfileSugarTSP(user_id)
        db.close_connection()

        if checkNotNoneType(self.sugar_amount) and checkNotNoneType(self.sugar_tsp):
            cal_sugar = float(self.sugar_amount) - coffee_config.TSP_WEIGHT * float(self.sugar_tsp)
        elif checkNotNoneType(self.sugar_amount):
            cal_sugar = float(self.sugar_amount) - 0
        else:
            cal_sugar = None

        if cal_sugar and cal_sugar < 0:
            cal_sugar = 0

        if checkNotNoneType(cal_sugar):
            if cal_sugar <= THRESHOLD_SUGAR: #email_config.THRESHOLD_SUGAR:
                notification_resource_names.append((sugar_type, cal_sugar))

        print(f"[BILLCOFFEE] Bean_Product_ID: {self.coffee_bean_id} Milk_Product_ID: {milk_product_id} Sugar_type_ID: {sugar_type}")
        print(f"[BILLCOFFEE] Bean_amount {cal_coffee} Milk_amount {cal_milk} Sugar_amount {cal_sugar}")
        db = DBManager()
        db.updateResourcesOnCoffeeBill(self.coffee_bean_id, milk_product_id, sugar_type, cal_coffee, cal_milk, cal_sugar)
        db.close_connection()
        
        self.send_notification(notification_resource_names)
    
    def send_notification(self, resource_names):
        pass
        # db = DBManager()
        # recipients = db.getRecipients()
        # db.close_connection()

        # db = DBManager()
        # coffee_resource_list, milk_resource_list, sugar_resource_list = db.getAllResources()
        # db.close_connection()

        # print(coffee_resource_list)

        # attachments_raw = [coffee_resource_list, milk_resource_list, sugar_resource_list]

        # email_factory = EmailFactory(recipients, resource_names, attachments_raw)
        # email_factory.send_mail()


    def display_billing_information(self):
        global user_config_data
        global today_coffee_amount
        data = user_config_data

        self.today_coffee_amount = today_coffee_amount

        db = DBManager()
        self.user_overall_coffee = db.getTotalUserCoffees(session.USER_ID)
        db.close_connection()
        
        db = DBManager()
        self.debts = db.getDebts(session.USER_ID)
        db.close_connection()

        if self.today_coffee_amount == 0:
            s = "1st"
        elif self.today_coffee_amount == 1:
            s = "2nd"
        elif self.today_coffee_amount == 2:
            s = "3rd"
        else:
            s = str(self.today_coffee_amount+1)+"th"

        #If nothing checked show default billing screen
        if data["bsc_amount_coffee_today"] == False and data["bsc_debts"] == False and data["bsc_weekly_stats"] == False:
            self.lblEnjoy.setText("Enjoy your cup of coffee!")
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfCoffees.setHidden(True)
            self.lblAmountOfDebt.setHidden(True)
        
        # Show #Coffee
        elif data["bsc_amount_coffee_today"] == True and data["bsc_debts"] == False and data["bsc_weekly_stats"] == False:
            self.lblEnjoy.setText("Enjoy your %s cup of coffee!" % s)
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 35pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfCoffees.setWordWrap(True)
            self.lblAmountOfCoffees.setText("#Coffees Overall: %s" % self.user_overall_coffee)
            self.lblAmountOfCoffees.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")
            self.lblAmountOfCoffees.adjustSize()
            self.lblAmountOfCoffees.move(215, 180)

            self.iconCoffee.setHidden(True)
            self.lblAmountOfDebt.setHidden(True)

        # Show $Debt
        elif data["bsc_amount_coffee_today"] == False and data["bsc_debts"] == True and data["bsc_weekly_stats"] == False:

            self.lblEnjoy.setText("Enjoy your cup of coffee!")
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfDebt.setWordWrap(True)
            self.lblAmountOfDebt.setText(f"$Debt:\n{self.debts:.2f}")
            self.lblAmountOfDebt.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")
            self.lblAmountOfDebt.adjustSize()
            self.lblAmountOfDebt.move(244, 180)

            self.iconCoffee.setHidden(True)
            self.lblAmountOfCoffees.setHidden(True)

        # Show #Coffee & $Debt
        elif data["bsc_amount_coffee_today"] == True and data["bsc_debts"] == True and data["bsc_weekly_stats"] == False:
            self.lblEnjoy.setText("Enjoy your %s cup of coffee!" % s)
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfCoffees.setWordWrap(True)
            self.lblAmountOfCoffees.setText("#Coffees Overall:\n%s" % self.user_overall_coffee)
            self.lblAmountOfCoffees.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")
            self.lblAmountOfCoffees.adjustSize()
            self.lblAmountOfCoffees.move(200, 140)

            self.lblAmountOfDebt.setWordWrap(True)
            self.lblAmountOfDebt.setText(f"$Debt:\n{self.debts:.2f}")
            self.lblAmountOfDebt.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")
            self.lblAmountOfDebt.adjustSize()
            self.lblAmountOfDebt.move(200, 220)

            self.iconCoffee.setHidden(True)

        # Show ALL
        elif data["bsc_amount_coffee_today"] == True and data["bsc_debts"] == True and data["bsc_weekly_stats"] == True:
            self.lblEnjoy.setText("Enjoy your %s cup of coffee!" %s)
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfCoffees.setWordWrap(True)
            self.lblAmountOfCoffees.setText("#Coffees Overall:\n%s" % self.user_overall_coffee)
            self.lblAmountOfCoffees.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")

            self.chartContainer.setGeometry(210, 80, 500, 300)

            self.lblAmountOfDebt.setWordWrap(True)
            self.lblAmountOfDebt.setText(f"$Debt:\n{self.debts:.2f}")
            self.lblAmountOfDebt.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")

            self.iconCoffee.setHidden(True)
            self.display_personal_coffee_chart()
            
        # Show #Coffee & Weekly Stats
        elif data["bsc_amount_coffee_today"] == True and data["bsc_debts"] == False and data["bsc_weekly_stats"] == True:
            self.lblEnjoy.setText("Enjoy your %s cup of coffee!" % s)
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfCoffees.setWordWrap(True)
            self.lblAmountOfCoffees.setText("#Coffees Overall:\n%s" % self.user_overall_coffee)
            self.lblAmountOfCoffees.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")
            self.lblAmountOfCoffees.adjustSize()
            self.lblAmountOfCoffees.move(10, 180)

            self.chartContainer.setGeometry(210, 80, 500, 300)

            self.lblAmountOfDebt.setHidden(True)
            self.iconCoffee.setHidden(True)
            self.display_personal_coffee_chart()

        # Show $Debts & Weekly Stats
        elif data["bsc_amount_coffee_today"] == False and data["bsc_debts"] == True and data["bsc_weekly_stats"] == True:

            self.lblEnjoy.setText("Enjoy your %s cup of coffee!" % s)
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.lblAmountOfDebt.setWordWrap(True)
            self.lblAmountOfDebt.setText(f"$Debt:\n{self.debts:.2f}")
            self.lblAmountOfDebt.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 20pt;}")
            self.lblAmountOfDebt.adjustSize()
            self.lblAmountOfDebt.move(10, 180)

            self.chartContainer.setGeometry(210, 80, 500, 300)

            self.lblAmountOfCoffees.setHidden(True)
            self.iconCoffee.setHidden(True)
            self.display_personal_coffee_chart()

        # Show only Weekly Stats
        elif data["bsc_amount_coffee_today"] == False and data["bsc_debts"] == False and data["bsc_weekly_stats"] == True:
            self.lblEnjoy.setText("Enjoy your cup of coffee!")
            self.lblEnjoy.setStyleSheet("QLabel{font-family: Segoe UI; font-size: 24pt;}")
            self.lblEnjoy.setAlignment(Qt.AlignCenter)

            self.chartContainer.setGeometry(10, 65, 679, 320)

            self.lblAmountOfCoffees.setHidden(True)
            self.lblAmountOfDebt.setHidden(True)
            self.iconCoffee.setHidden(True)

            self.display_personal_coffee_chart()

        session.BILLED_COFFEE = True
        
    def display_personal_coffee_chart(self):
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay.addWidget(self.canvas)

        db = DBManager()
        self.data = db.getPersonalCoffeeOverWeek(session.USER_ID)
        db.close_connection()

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        x = []
        y= []
        for entry in self.data:
            x.append(datetime.strptime(entry[0], "%Y-%m-%d"))
            y.append(entry[1])
        y = np.array(y)

        x_ = []
        for v in x:
            x_.append(v.strftime('%m/%d'))

        ax.set_xticks(np.arange(len(x_)))
        ax.set_xticklabels(x_, rotation=45)
        ax.plot(x_, y)
        ax.set_ylim([0,y.max() + 1])

        plt.tight_layout(pad=3)
        

        ax.set(ylabel='#Coffee')
        # ax.set_xticklabels(x, rotation=45)

        # ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.canvas.draw()

            



