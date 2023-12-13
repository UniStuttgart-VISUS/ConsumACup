import array
import os

from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import * 
from PyQt5.QtCore import pyqtSignal as Signal
import time

import back_end.session as session 
from back_end.manage_db import DBManager, rfid_to_hex
from back_end.buzzer import Buzzer

from front_end.billing_screen import BillOrLimitScreen

import RUNTIME_CONFIG as cfg 

DEBUG = cfg.DEBUG
if not DEBUG:
    from back_end.nfc_reader import NfcWorker # The class that interacts with the NFC reader


class ProfileScreen(QMainWindow):
    work_requested = Signal(int)

    def __del__(self):
        print("[DESTRUCTOR LOG] Profile Screen is beeing destroyed")
        if not DEBUG:
            try:
                self.worker.setn(0)
                self.worker.deleteLater()
            except:
                print("[EXCEPTION HANDLED] Worker already deleted, continue ...")

    def __init__(self, stackedPages, nfcThread=None):

        super().__init__()
        loadUi("front_end/ui_files/profile_screen.ui", self)

        self.stackedPages = stackedPages

        self.tabWidget.setCurrentIndex(0)
        self.btnBillCoffee.clicked.connect(self.bill_coffee)
        self.btnSaveOrder.clicked.connect(self.save_order)
        self.btnSaveConfig.clicked.connect(self.save_config)
        self.btnConsent.clicked.connect(self.consent)
        self.btnSaveChanges.clicked.connect(self.save_changes)

        self.btnKeyboard.clicked.connect(self.show_keyboard)

        self.reload()

        self.btnAdd.clicked.connect(self.add_entry)
        self.btnRemove.clicked.connect(self.remove_entry)

        if not DEBUG:
            self.nfcThread = nfcThread
            self.worker = NfcWorker()

            self.worker.moveToThread(self.nfcThread)

            self.worker.tag.connect(self.fill_entry)
            self.work_requested.connect(self.worker.setn)

            self.nfcThread.start()
            
            print("[Thread Log] Stared NfcReader Thread from profile_screen!")
        else:
            self.nfcThread = nfcThread


    def show_keyboard(self):
        try:
            os.system('dbus-send --type=method_call --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.Show')
        except:
            pass

    def add_entry(self):
        try:
            row_count = self.tblWidget.rowCount()
            if self.tblWidget.item(row_count-1,0).text() != "Scanning ...":
                self.tblWidget.insertRow(row_count)
                print("Added!")

                row_count = self.tblWidget.rowCount()-1
                self.lblError.setText("")
                self.tblWidget.setItem(row_count,0,QTableWidgetItem("Scanning ..."))
                self.work_requested.emit(1)
                print("Scanning ...")
            else:
                self.lblError.setText("Please scan first code, before adding a new one!")
        except AttributeError:
            if row_count == 0:
                self.tblWidget.insertRow(row_count)
                print("Added!")

                row_count = self.tblWidget.rowCount()-1
                self.lblError.setText("")
                self.tblWidget.setItem(row_count,0,QTableWidgetItem("Scanning ..."))
                self.work_requested.emit(1)
                print("Scanning ...")
        
    def remove_entry(self):
        if self.tblWidget.rowCount() > 0:
            self.tblWidget.removeRow(self.tblWidget.rowCount()-1)
            self.lblError.setText("")
        print("Removed!")
        if not DEBUG:
            self.work_requested.emit(0)
            # here try setn 0 

    def fill_entry(self, uid):
        rfid = rfid_to_hex(int(uid))
        name = self.searchUid(rfid)

        bz = Buzzer()
        if name != "":
            self.lblError.setText("RFID Code already in Database! \nPlease contact the coffee administration.")
            bz.buzz_decline()
            row_count = self.tblWidget.rowCount()
            if self.tblWidget.item(row_count-1,0).text() == "Scanning ...":
                self.tblWidget.removeRow(self.tblWidget.rowCount()-1)
        elif self.tblWidget.findItems(rfid,Qt.MatchContains):
            self.lblError.setText(f"Already added RFID Code: {rfid} \nPlease present a new RFID!")
            bz.buzz_decline()
            if self.tblWidget.item(row_count-1,0).text() == "Scanning ...":
                self.tblWidget.removeRow(self.tblWidget.rowCount()-1)
        elif self.tblWidget.rowCount() == 0:
            self.lblError.setText("Please press \"Add\" first to add an entry!")
            bz.buzz_decline()
            if self.tblWidget.item(row_count-1,0).text() == "Scanning ...":
                self.tblWidget.removeRow(self.tblWidget.rowCount()-1)
        else:
            bz.buzz_confirm()
            row_count = self.tblWidget.rowCount()-1
            print("ROW COUNT in the ADDING PROCESS: " + str(row_count))
            self.lblError.setText("")
            self.tblWidget.setItem(row_count,0,QTableWidgetItem(rfid))
        bz.buzz_close()
    
    def searchUid(self, rfid):
        print("Searching UID!")
        db = DBManager()
        first_name, last_name = db.getNamefromRFID(rfid)
        db.close_connection()

        if first_name == "":
            print("Could not find RFID in the database!")
            return ""
        else:
            print(f"Found RFID {rfid} in the database. The Name is {first_name} {last_name}")
            return f"{first_name} {last_name}"

    def save_changes(self):
        first_name = self.leFirstName.text()
        last_name = self.leLastName.text()
        #user_name = self.leUsername.text()
        e_mail = self.leEmail.text()
        # TODO: Discord name
        #d_name = self.leDname.text()

        rfid_codes = []
        column = 0
        # get all items from qtablewidget repr rfid codes
        for row in range(self.tblWidget.rowCount()): 
            # item(row, 0) Returns the item for the given row and column if one has been set; otherwise returns nullptr.
            item = self.tblWidget.item(row, column) 
            if item:            
                item = self.tblWidget.item(row, column).text()
                print(f'row: {row}, column: {column}, item={item}')
                rfid_codes.append(item)

        db = DBManager()
        resp = db.updateUser(session.USER_ID, first_name, last_name, rfid_codes, e_mail)
        db.close_connection()
        self.lblError.setText(resp)

        if not DEBUG:
            # self.work_requested.emit(0)
            self.worker.setn(0)
            # self.nfcThread.quit()
            self.worker.deleteLater()

        if not resp:
            self.lblDone.clear()
            self.lblDone.setText("Done!")
            self.lblDone.repaint()
            time.sleep(2)
            self.lblDone.clear()

    def reload(self):
        # Reload Credentials Tab with Userdetails
        print("RELOADING PROFILE")

        db = DBManager()
        data = db.getUserData(session.USER_ID)

        self.coffee_resource_list, self.milk_resource_list, self.sugar_resource_list= db.getAllResourcesWithNames()

        first_name = data['first_name']
        last_name = data['last_name']
        e_mail=data['email']

        milk_type_id = data['cc_milk_type']
        milk_type_name = db.getMilkTypeFromID(milk_type_id)
        sugar_type_id = data['cc_sugar_type']
        sugar_type_name = db.getSugarTypeFromID(sugar_type_id)

        _, coffee_types_list = db.getCoffeeTypes()
        _, milk_types = db.getMilkTypes()
        _, sugar_types = db.getSugarTypes()
        db.close_connection()
        
        self.leFirstName.setText(first_name)
        self.leLastName.setText(last_name)
        self.leEmail.setText(e_mail)

        # personal Coffee Order Tab
        self.cbCoffeeType.clear()
        self.cbCoffeeType.addItems(coffee_types_list)
        self.cbCoffeeType.setCurrentText(data['cc_coffee_type'])

        self.cbCoffeeInsert.setCurrentText(data['cc_portafilter'])

        self.cbMilkType.addItems(milk_types)
        self.cbMilkType.setCurrentText(milk_type_name)
        self.cbMilkShots.setCurrentText(data['cc_milk_shots'])

        self.cbSugarType.addItems(sugar_types)
        self.cbSugarType.setCurrentText(sugar_type_name)
        self.cbSugarTsp.setCurrentText(str(int(data['cc_sugar_tsp']))+ " tsp.")

        # Billing Screen Config Tab
        self.checkBoxAmountCoffeeToday.setChecked(data['bsc_amount_coffee_today'])
        self.checkBoxDebts.setChecked(data['bsc_debts'])
        self.checkBoxWeeklyStats.setChecked(data['bsc_weekly_stats'])
        self.checkBoxNotification.setChecked(data['bsc_coffee_limit_notification'])
        if data['bsc_daily_coffee_limit'] == 0:
            daily_limit = "off"
            self.cbDailyCoffeeLimit.setCurrentText(daily_limit)
        else:
            daily_limit = str(data['bsc_daily_coffee_limit'])
            self.cbDailyCoffeeLimit.setCurrentText(daily_limit)
        # Privacy Settings Tab
        self.checkBoxHighscore.setChecked(data['ps_highscore_ranking'])
        self.checkBoxDebtsRanking.setChecked(data['ps_debts_ranking'])
        self.checkBoxEarliestLatestDrinker.setChecked(data['ps_earliest_latest_drinker_ranking'])
        self.checkBoxResourcePurchase.setChecked(data['ps_resource_purchase_ranking'])
        self.checkBoxRefill.setChecked(data['ps_refill_ranking'])    

        rfid_codes = [data['rfid'], data['rfid1'], data['rfid2'], data['rfid3'], data['rfid4']]
        rfid_codes = [i for i in rfid_codes if i]
        row_count = 0
        for rfid_code in rfid_codes:
            self.tblWidget.insertRow(row_count)
            self.tblWidget.setItem(row_count,0,QTableWidgetItem(str(rfid_code)))
            row_count+=1


    def resources_milk(self):
        return_milk_type_list =[]
        for x in self.milk_resource_list:
            return_milk_type_list.append(x[0])
        return return_milk_type_list
    
    def resources_sugar(self):
        return_sugar_type_list =[]
        for x in self.sugar_resource_list:
            return_sugar_type_list.append(x[0])
        return return_sugar_type_list


    def bill_coffee(self):
        print ("Billing Screen!")
        print("Billing coffee order!")
        self.billcoffee = BillOrLimitScreen(self.stackedPages)


    def convert_input(self):
        milk_shots = self.cbMilkShots.currentText()
        sugar_tsp = self.cbSugarTsp.currentText()

        n_milk_shots = "" # this entry is a text in DB
        n_sugar_tsp = 0 # this entry is a real in DB

        if milk_shots == "" or milk_shots == "0":
            n_milk_shots = "0/8 cup"
        else :
            n_milk_shots = milk_shots

        if sugar_tsp == "":
            n_sugar_tsp = 0
        else: 
            n_sugar_tsp = sugar_tsp[:-5]

        return n_milk_shots, n_sugar_tsp


    def save_order(self):
        n_milk_shots, n_sugar_tsp = self.convert_input()
        #print(f"n_milk_shots {n_milk_shots}, n_sugar_tsp {n_sugar_tsp}")

        coffee_type = self.cbCoffeeType.currentText()
        milk_type = self.cbMilkType.currentText()
        # milk_shots = self.cbMilkShots.currentText()
        sugar_type = self.cbSugarType.currentText()
        # sugar_tsp = self.cbSugarTsp.currentText()

        #print(f"milk_type {milk_type}, sugar_type {sugar_type}")
        db = DBManager()
        milk_type_id = db.getMilkTypeIDFromName(milk_type)
        sugar_type_id = db.getSugarTypeIDFromName(sugar_type)
        # print("Save coffee order")
        # print(f"session.USER_ID {session.USER_ID}, coffee_type {coffee_type}, milk_type_id {milk_type_id}, n_milk_shots {n_milk_shots}, sugar_type_id {sugar_type_id}, n_sugar_tsp {n_sugar_tsp}")
        resp = db.updateUserCoffeeOrder(session.USER_ID, coffee_type, milk_type_id, n_milk_shots, sugar_type_id, n_sugar_tsp)
        db.close_connection()

        self.lblError_cc.setText(resp)  
        if resp is None:
            self.lblDone_cc.clear()
            self.lblDone_cc.setText("Done!")
            self.lblDone_cc.repaint()
            time.sleep(2)
            self.lblDone_cc.clear()
      

    # Billing Screen Config Tab
    def save_config(self):
        
        #checking if checked
        amount_coffee = self.checkBoxAmountCoffeeToday.isChecked()
        amount_debt = self.checkBoxDebts.isChecked()
        weekly_stats = self.checkBoxWeeklyStats.isChecked()
        notification = self.checkBoxNotification.isChecked()
        
        daily_limit = self.cbDailyCoffeeLimit.currentText()
        if daily_limit =="off":
            daily_limit = 0

        db = DBManager()
        resp = db.updateUserProfile(session.USER_ID ,amount_coffee, amount_debt, weekly_stats, daily_limit, notification)
        db.close_connection()

        self.lblError_c.setText(resp)
        if resp is None:
            self.lblDone_c.clear()
            self.lblDone_c.setText("Done!")
            self.lblDone_c.repaint()
            time.sleep(2)
            self.lblDone_c.clear()

    # Privacy Setting Tab
    def consent(self):
        #checking if checked
        consent_highscore = self.checkBoxHighscore.isChecked()
        consent_debt_ranking = self.checkBoxDebtsRanking.isChecked()
        consent_EL_drinkers = self.checkBoxEarliestLatestDrinker.isChecked()
        consent_resources_purchase = self.checkBoxResourcePurchase.isChecked()
        consent_refill = self.checkBoxRefill.isChecked()        

        db = DBManager()
        resp = db.updateUserConsent(session.USER_ID , consent_highscore, consent_debt_ranking, consent_EL_drinkers, consent_resources_purchase, consent_refill)
        db.close_connection()

        self.lblError_ps.setText(resp)
        if resp is None:
            self.lblDone_ps.clear()
            self.lblDone_ps.setText("Done!")
            self.lblDone_ps.repaint()
            time.sleep(2)
            self.lblDone_ps.clear()