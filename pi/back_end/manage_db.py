import pyodbc
import numpy as np
import RUNTIME_CONFIG as cfg
import back_end.session as session
from datetime import datetime, timedelta, timezone
import re

def return_on_failure(f):
    def decorate(self,*args, **kwargs):
        try:
            return f(self,*args,**kwargs)
        except (Exception, pyodbc.DatabaseError) as error:
            print(f"[DBManager] {error}")
            return str(error)
        # finally:
        #     self.close_connection()
    return decorate

def sql_time_to_python_time(time):
    #return datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f %z")
    return datetime.strptime(time.split(".")[0], '%Y-%m-%d %H:%M:%S')

def convert_str_to_datetime_with_timezone(time):
    date_time_str, timezone_str = time.rsplit(' ', 1)
    date_time_str = date_time_str.split('.')[0]
    date_time_obj = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")

    # Extract the timezone offset
    timezone_match = re.match(r"([-+]\d{2}:\d{2})", timezone_str)
    timezone_offset = timezone_match.group(0)

    # Create a timedelta object for the timezone offset
    offset_hours, offset_minutes = map(int, timezone_offset.split(':'))
    offset = timedelta(hours=offset_hours, minutes=offset_minutes)

    # Create a timezone-aware datetime object
    date_obj = date_time_obj.replace(tzinfo=timezone(offset))
    return date_obj

def python_time_to_sql_time(time):
    tmp_str = time.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
    time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
    return time_str

def rfid_to_hex(rfid):
    if type(rfid) != int:
        rfid = int(rfid)
    return hex(rfid).replace('0x','')[:8]


class DBManager:

    def __init__(self):
        self.conn = None
        self.create_connection()
        self.driver = "/usr/lib/aarch64-linux-gnu/odbc/libtdsodbc.so"

    ## Desktop version to connect to DB
    def create_connection(self):
        """ create a database connection to a SQL database """
        if cfg.DEBUG:
            try:
                self.conn = pyodbc.connect("DRIVER={SQL Server};"
                "SERVER=;"
                "DATABASE=;"
                "Trusted_Connection=yes;")
                #print("[DBManager] Connection successfully established.")
            except e:
                print(e)
        else:
            try:
                self.conn = pyodbc.connect(driver = "/usr/lib/aarch64-linux-gnu/odbc/libtdsodbc.so",
                                    TDS_Version = "8.0",
                                    server = "",
                                    port = 1433,
                                    database = "",
                                    uid = "",
                                    pwd = session.DB_PASSWORD)
                #print("[DBManager] Connection successfully established.")
            except e:
                print(e)


    def close_connection(self):
        if self.conn:
            self.conn.close()

    @return_on_failure
    def createMilkProduct(self, name, type):
        cur = self.conn.cursor()

        cur.execute("SELECT * FROM milk_products")
        rows = cur.fetchall()

        cur.execute("INSERT INTO milk_products (name, type) VALUES('{}', '{}')".format(name, type))
        self.conn.commit()

    @return_on_failure
    def createBeanProduct(self, name, bean_type):
        cur = self.conn.cursor()

        cur.execute("SELECT * FROM bean_products")
        rows = cur.fetchall()

        cur.execute("INSERT INTO bean_products (name, bean_type) VALUES('{}' ,'{}')".format(name, bean_type))
        self.conn.commit()

    @return_on_failure
    def createUser(self, rfid, rfid1, rfid2, rfid3, rfid4, first_name, last_name, discord_name = "", discord_id = "", email = ""):
        cur = self.conn.cursor()

        cur.execute("SELECT first_name, last_name, rfid, rfid1, rfid2, rfid3, rfid4 FROM users")
        rows = cur.fetchall()

        for row in rows:
            if [rfid, rfid1, rfid2, rfid3, rfid4] in row:
                print(f"[Error] User with RFID {[rfid, rfid1, rfid2, rfid3, rfid4]} already exists")
                return
            if first_name in row[0] and last_name in row[1]:
                print("[Error] User with name {} {} already exists.".format(first_name,last_name))
                return

        cur.execute(f"INSERT INTO users (rfid, rfid1, rfid2, rfid3, rfid4, first_name, last_name, discord_name, email, discord_id) VALUES('{rfid}', '{rfid1}', '{rfid2}', '{rfid3}', '{rfid4}', '{first_name}', '{last_name}', '{discord_name}', '{email}', '{discord_id}')")

        self.conn.commit()
        user_id = self.getIDfromRFID(rfid)
        self.insertPayment(user_id, 0)
        self.createUserProfile(user_id)
    
    @return_on_failure
    def setUserCredentials(self, user_id, login_name, password):
        if not self.checkUser(user_id): return
        cur = self.conn.cursor()
        cur.execute(f"UPDATE users SET login_name='{login_name}', password_hash=HASHBYTES('SHA2_512', '{password}') WHERE id = '{user_id}'")
        self.conn.commit()
        
    @return_on_failure
    def checkCredentials(self, login_name, password):
        cur = self.conn.cursor()
        cur.execute(f"SELECT id FROM users WHERE login_name='{login_name}' AND password_hash=HASHBYTES('SHA2_512', '{password}')")
        res = cur.fetchone()
        if res:
            return res[0]
        else:
            return None

    @return_on_failure
    def changeUsersRFIDs(self, id, rfids: list):
        # check for rfids first
        for rfid in rfids:
            user_id = self.getIDfromRFID(rfid)
            if user_id != "" and int(user_id) != int(id):
                print(f"[Error] RFID {rfid} already exists for different user in the database.")
                return
        cur = self.conn.cursor()
        if len(rfids) < 1: 
            print("[Error] no rfids provided.")
            return
            
        cur.execute(f"UPDATE users SET rfid='{rfids[0]}' WHERE id = '{id}'")
        if len(rfids) > 1 and len(rfids) <=5:
            for i in range(1,len(rfids)):
                cur.execute(f"UPDATE users SET rfid{i}='{rfids[i]}' WHERE id = '{id}'")

        self.conn.commit()

    @return_on_failure
    def changeUsersDiscordName(self, uid, discord_name):
        if discord_name == "":
            return
        if (discord_name.endswith("#0")):
            discord_name = discord_name[:-2]
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET discord_name='{}' WHERE id = '{}'".format(discord_name,uid))
        self.conn.commit()

    @return_on_failure
    def changeUsersDiscordID(self, uid, discord_id):
        if discord_id == "":
            return
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET discord_id='{}' WHERE id = '{}'".format(discord_id,uid))
        self.conn.commit()

    @return_on_failure
    def changeUsersEmail(self, uid, email):
        if email == "":
            return
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET email='{}' WHERE id = '{}'".format(email,uid))
        self.conn.commit()
    
    @return_on_failure
    def changeUsersName(self, id, first_name, last_name):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET first_name='{}',last_name='{}' WHERE id = '{}'".format(first_name, last_name,id))
        self.conn.commit()
    
    @return_on_failure
    def setUserInactive(self, id):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET inactive=1 WHERE id = '{}'".format(id))
        self.conn.commit()

    @return_on_failure
    def setUserActive(self, id):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET inactive=0 WHERE id = '{}'".format(id))
        self.conn.commit()

    @return_on_failure
    def printTable(self, table):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM {}".format(table))
        rows = cur.fetchall()
        for row in rows:
            string = ""
            for key in row:
                string += "{}, ".format(key)
            print(string)

    @return_on_failure
    def getAllDiscordIDs(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, discord_id FROM users")
        rows = cur.fetchall()
        return rows

    @return_on_failure
    def getTableData(self, table):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM {}".format(table))
        rows = cur.fetchall()
        return rows
    
    @return_on_failure
    def getCoffeeDataByTimeFrame(self, start_date = "", end_date = ""):
        cur = self.conn.cursor()
        if start_date == "" and end_date == "":
            cur.execute("SELECT user_id, price, date FROM coffees ORDER BY id ASC")
        elif start_date != "" and end_date == "":
            tmp_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            start_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT user_id, price, date FROM coffees WHERE date >= '{start_time_str}' ORDER BY id ASC")
        elif start_date == "" and end_date != "":
            tmp_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            end_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT user_id, price, date FROM coffees WHERE date < '{end_time_str}' ORDER BY id ASC")
        elif start_date != "" and end_date != "":
            tmp_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            start_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            tmp_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            end_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT user_id, price, date FROM coffees WHERE date >= '{start_time_str}' AND date < '{end_time_str}' ORDER BY id ASC")
        rows = cur.fetchall()
        return rows
    
    @return_on_failure
    def getCoffeeData(self, num = -1):
        cur = self.conn.cursor()
        if num < 0:
            cur.execute("SELECT user_id, price, date FROM coffees ORDER BY id ASC")
        else:
            cur.execute(f"SELECT TOP({num}) user_id, price, date FROM coffees ORDER BY id DESC")
        rows = cur.fetchall()
        return rows

    @return_on_failure
    def getCoffeesOfUser(self, user_id, num = -1):
        if not self.checkUser(user_id):
            return [[None]]
        cur = self.conn.cursor()
        if num < 0:
            cur.execute(f"SELECT price, date FROM coffees WHERE user_id = '{user_id}' ORDER BY id ASC")
        else:
            cur.execute(f"SELECT TOP({num}) price, date FROM coffees WHERE user_id = '{user_id}' ORDER BY id DESC")
            # cur.execute("SELECT * FROM coffees WHERE user_id = {} ORDER BY id DESC LIMIT {}".format(user_id, num))
        rows = cur.fetchall()
        return rows
    
    @return_on_failure
    def getCoffeesOfUserByTimeFrame(self, user_id, start_date = "", end_date = ""):
        if not self.checkUser(user_id):
            return [[None]]
        cur = self.conn.cursor()
        if start_date == "" and end_date == "":
            cur.execute(f"SELECT price, date FROM coffees WHERE user_id = '{user_id}' ORDER BY id ASC")
        elif start_date != "" and end_date == "":
            tmp_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            start_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT price, date FROM coffees WHERE user_id = '{user_id}' AND date >= '{start_time_str}' ORDER BY id ASC")
        elif start_date == "" and end_date != "":
            tmp_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            end_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT price, date FROM coffees WHERE user_id = '{user_id}' AND date < '{end_time_str}' ORDER BY id ASC")
        elif start_date != "" and end_date != "":
            tmp_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            start_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            tmp_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            end_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT price, date FROM coffees WHERE user_id = '{user_id}' AND date >= '{start_time_str}' AND date < '{end_time_str}' ORDER BY id ASC")
        rows = cur.fetchall()
        return rows
    
    @return_on_failure
    def getPaymentDataOfUser(self, user_id):
        if not self.checkUser(user_id):
            return [[None]]
        cur = self.conn.cursor()
        cur.execute("SELECT amount_paid, date FROM payments WHERE user_id = {}".format(user_id))
        rows = cur.fetchall()
        return rows
    
    @return_on_failure
    def getPaymentDataByTimeFrame(self, start_date = "", end_date = ""):
        cur = self.conn.cursor()
        if start_date == "" and end_date == "":
            cur.execute("SELECT amount_paid, date FROM payments ORDER BY date ASC")
        elif start_date != "" and end_date == "":
            tmp_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            start_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT amount_paid, date FROM payments WHERE date >= '{start_time_str}' ORDER BY date ASC")
        elif start_date == "" and end_date != "":
            tmp_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            end_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT amount_paid, date FROM payments WHERE date < '{end_time_str}' ORDER BY date ASC")
        elif start_date != "" and end_date != "":
            tmp_str = start_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            start_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            tmp_str = end_date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f %z")
            end_time_str = tmp_str[:-2] + ":" + tmp_str[-2:]
            cur.execute(f"SELECT amount_paid, date FROM payments WHERE date >= '{start_time_str}' AND date < '{end_time_str}' ORDER BY date ASC")
        rows = cur.fetchall()
        return rows

    @return_on_failure
    def getTableColumnNames(self, table):
        cur = self.conn.cursor()
        cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(table))
        names = cur.fetchall()
        return names
    
    @return_on_failure
    def addCoffeePurchase(self, id, price):
        if not self.checkUser(id):
            return False
        cur = self.conn.cursor()
        cur.execute("INSERT INTO coffees (user_id, price) VALUES('{}', '{}')".format(id, price))
        #cur.execute("INSERT INTO coffees VALUES('{}', NULL, '{}')".format(id, datetime.datetime.now().replace(microsecond=0), self.current_price))
        self.conn.commit()
        return True

    @return_on_failure
    def checkUser(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT first_name FROM users WHERE id ='{}'".format(id))
        result = cur.fetchall()
        if (len(result) == 0):
            print("[ERROR] Id {} does not exist.".format(id))
            return False
        return True

    @return_on_failure
    def checkBeanProduct(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM bean_products WHERE product_id = '{}'".format(id))
        result = cur.fetchall()
        if (len(result) == 0):
            print("[ERROR] Bean product ID {} does not exist.".format(id))
            return False
        return True

    @return_on_failure
    def checkMilkProduct(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM milk_products WHERE product_id = '{}'".format(id))
        result = cur.fetchall()
        if (len(result) == 0):
            print("[ERROR] Milk product ID {} does not exist.".format(id))
            return False
        return True

    @return_on_failure
    def insertPayment(self, user_id, amount, date = ""):
        if not self.checkUser(user_id):
            return False
        cur = self.conn.cursor()
        if date != "":
            cur.execute("INSERT INTO payments (user_id, amount_paid, date) VALUES('{}', '{}', '{}')".format(user_id, amount, date))
        else:
            cur.execute("INSERT INTO payments (user_id, amount_paid) VALUES('{}', '{}')".format(user_id, amount))
        self.conn.commit()
        return True
    
    @return_on_failure
    def insertPendingPayment(self, user_id, amount):
        if not self.checkUser(user_id):
            return False
        cur = self.conn.cursor()
        cur.execute("INSERT INTO pending_payments (user_id, amount_paid) VALUES('{}', '{}')".format(user_id, amount))
        self.conn.commit()
        cur.execute("SELECT id FROM pending_payments WHERE id=(SELECT max(id) FROM pending_payments)")
        payment_id = cur.fetchall()
        return payment_id[0][0]
    
    @return_on_failure
    def transferPendingPayment(self, payment_id):
        cur = self.conn.cursor()
        cur.execute("SELECT user_id, amount_paid, date FROM pending_payments WHERE id ='{}'".format(payment_id))
        payment_details = cur.fetchall()
        if len(payment_details[0]) != 3:
            return ""
        else:
            user_id = payment_details[0][0]
            amount = payment_details[0][1]
            date = payment_details[0][2]
            cur.execute("INSERT INTO payments (user_id, amount_paid, date) VALUES('{}', '{}', '{}')".format(user_id, amount, date))
            cur.execute("DELETE FROM pending_payments WHERE id={}".format(payment_id))
            self.conn.commit()
            return payment_details[0][0]

    @return_on_failure
    def getDebts(self, id):
        if not self.checkUser(id):
            return
        cur = self.conn.cursor()
        cur.execute("SELECT balance FROM user_balance WHERE user_id ='{}'".format(id))
        bal = cur.fetchall()
        if len(bal) == 0:
            cur.execute("SELECT total_cost FROM user_balance WHERE user_id ='{}'".format(id))
            cost = cur.fetchall()
            if len(cost) == 0:
                return 0
            else:
                return cost[0][0]
        else:
            return -1*bal[0][0]

    @return_on_failure
    def getTotalCoffeesEuro(self, id):
        if not self.checkUser(id):
            return
        cur = self.conn.cursor()
        cur.execute("SELECT total_cost FROM user_coffees WHERE user_id ='{}'".format(id))
        coffee = cur.fetchall()
        print("User {} has spent a total of {} Euro on coffee.".format(id, coffee[0][0]))
        return coffee[0][0]
    
    @return_on_failure
    def getTotalUserCoffees(self, id):
        if not self.checkUser(id):
            return
        cur = self.conn.cursor()
        cur.execute("SELECT count FROM user_coffees WHERE user_id ='{}'".format(id))
        coffee = cur.fetchall()
        print("User {} has bought a total of {} coffees.".format(id, coffee[0][0]))
        return coffee[0][0]

    @return_on_failure
    def getTotalCoffeesAllUsers(self):
        cur = self.conn.cursor()
        cur.execute("SELECT first_name, last_name, count, inactive FROM user_coffees")
        rows = cur.fetchall()
        return rows

    @return_on_failure
    def getTotalPaid(self, id):
        if not self.checkUser(id):
            return
        cur = self.conn.cursor()
        cur.execute("SELECT total_paid FROM user_payments WHERE user_id ='{}'".format(id))
        paid = cur.fetchall()
        print("User {} already paid {} Euro to the coffee administration.".format(id, paid[0][0]))
        return paid[0][0]

    @return_on_failure
    def getName(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT first_name, last_name FROM users WHERE id = '{}'".format(id))
        result = cur.fetchall()
        if (len(result) == 0):
            print("[ERROR] Id {} does not exist.".format(id))
            return "", ""
        else:
            print("User {} {} has ID {}".format(result[0][0], result[0][1],id))
            return result[0][0], result[0][1]

    @return_on_failure
    def getNumUsers(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()
        return len(rows)

    @return_on_failure
    def getAllUserNames(self):
        cur = self.conn.cursor()
        cur.execute("SELECT first_name, last_name FROM users")
        users = cur.fetchall()
        first_name_list = []
        last_name_list = []
        for user in users:
            first_name_list.append(user[0])
            last_name_list.append(user[1])
        return first_name_list, last_name_list

    @return_on_failure
    def getIDfromRFID(self, rfid):
        if type(rfid) == list:
            print(f"[ERROR] getIDfromRFID does not accept a list of rfids")
            return ""
        cur = self.conn.cursor()
        cur.execute(f"SELECT id FROM users WHERE '{rfid}' IN(rfid, rfid1, rfid2, rfid3, rfid4)")
        result = cur.fetchall()
        if len(result) != 1:
            print(f"[WARNING] There is no user with RFID {rfid}")
            return ""
        else:
            return result[0][0]
        
    @return_on_failure
    def getNamefromRFID(self, rfid):
        if type(rfid) == list:
            print(f"[ERROR] getNamefromRFID does not accept a list of rfids")
            return "", ""
        cur = self.conn.cursor()
        cur.execute(f"SELECT first_name, last_name FROM users WHERE '{rfid}' IN(rfid, rfid1, rfid2, rfid3, rfid4)")
        result = cur.fetchone()
        if not result:
            print(f"[WARNING] There is no user with RFID {rfid}")
            return "", ""
        else:
            return result[0], result[1]

    @return_on_failure
    def getIDfromName(self, first_name, last_name):
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM users WHERE (first_name LIKE '{}' AND last_name LIKE '{}')".format(first_name, last_name))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] Could not find user with name {} {}".format(first_name, last_name))
            return ""
        else:
            return result[0][0]
        
    @return_on_failure
    def getIDfromDiscordID(self, discord_id):
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM users WHERE (discord_id LIKE '{}')".format(discord_id))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] Could not find user with discord_id {}".format(discord_id))
            return ""
        else:
            return result[0][0]
        
    @return_on_failure
    def getIDfromDiscordName(self, discord_name):
        if (discord_name.endswith("#0")):
            discord_name = discord_name[:-2]
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM users WHERE (discord_name LIKE '{}')".format(discord_name))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] Could not find user with discord_name {}".format(discord_name))
            return ""
        else:
            return result[0][0]
        
    @return_on_failure
    def getDiscordName(self, uid):
        cur = self.conn.cursor()
        cur.execute("SELECT discord_name FROM users WHERE id = '{}'".format(uid))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] There is no user with Name {}".format(uid))
            return ""
        else:
            if result[0][0] != None: 
                return result[0][0]
            else:
                return ""
            
    @return_on_failure
    def getDiscordID(self, uid):
        cur = self.conn.cursor()
        cur.execute("SELECT discord_id FROM users WHERE id = '{}'".format(uid))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] There is no user with ID {}".format(uid))
            return ""
        else:
            if result[0][0] != None: 
                return result[0][0]
            else:
                return ""
    
    @return_on_failure
    def getEmail(self, uid):
        cur = self.conn.cursor()
        cur.execute("SELECT email FROM users WHERE id = '{}'".format(uid))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] There is no user with ID {}".format(uid))
            return ""
        else:
            if result[0][0] != None: 
                return result[0][0]
            else:
                return ""

    @return_on_failure
    def getRFIDs(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT rfid, rfid1, rfid2, rfid3, rfid4 FROM users WHERE id = '{}'".format(id))
        result = cur.fetchall()
        rfids = []
        for res in result[0]:
            if res != "" and res != None:
                rfids.append(res)
        if len(rfids) < 1:
            print("[ERROR] There is no RFIDs for user with ID {}".format(id))
            return ""
        else:
            return rfids

    @return_on_failure
    def getCreationDate(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT date FROM users WHERE id = '{}'".format(id))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] There is no user with ID {}".format(id))
            return ""
        else:
            return result[0][0]

    @return_on_failure
    def isInactive(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT inactive FROM users WHERE id = '{}'".format(id))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] There is no user with ID {}".format(id))
            return ""
        else:
            return result[0][0]

    @return_on_failure
    def getBeanProductIDfromName(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id FROM bean_products WHERE name LIKE '{}'".format(name))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] Could not find bean product with name {}".format(name))
            return ""
        else:
            return result[0][0]
        
    def getBeanProductName(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM bean_products WHERE product_id = '{}'".format(id))
        result = cur.fetchone()
        if (len(result) == 0):
            print("[ERROR] Bean product with ID {} does not exist.".format(id))
            return ""
        return result[0]

    @return_on_failure
    def getMilkProductIDfromName(self, name):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id FROM milk_products WHERE name LIKE '{}'".format(name))
        result = cur.fetchall()
        if len(result) != 1:
            print("[ERROR] Could not find milk product with name {}".format(name))
            return ""
        else:
            return result[0][0]
        
    @return_on_failure
    def getMilkProductName(self, id):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM milk_products WHERE product_id = '{}'".format(id))
        result = cur.fetchone()
        if (len(result) == 0):
            print("[ERROR] Milk product with ID {} does not exist.".format(id))
            return ""
        return result[0]

    @return_on_failure
    def getAllMilkProducts(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM milk_products")
        products = cur.fetchall()
        name_list = []
        for product in products:
            name_list.append(product[1])
        return name_list

    @return_on_failure
    def getAllBeanProducts(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM bean_products")
        products = cur.fetchall()
        name_list = []
        for product in products:
            name_list.append(product[1])
        return name_list

    @return_on_failure
    def addBeanPurchase(self, product_id, date, price, user_id, weight):
        if not self.checkBeanProduct(product_id):
            return False
        cur = self.conn.cursor()
        cur.execute("INSERT INTO bean_purchase (product_id, user_id, price, date, grams) VALUES('{}', '{}', '{}', '{}', '{}')".format(product_id, user_id, price, date, weight))
        self.conn.commit()
        return True

    @return_on_failure
    def addMilkPurchase(self, product_id, date, price, liters, user_id):
        if not self.checkMilkProduct(product_id):
            return False
        cur = self.conn.cursor()
        cur.execute("INSERT INTO milk_purchase (product_id, user_id, price, date, liters) VALUES('{}', '{}', '{}', '{}', '{}')".format(product_id, user_id, price, date, liters))
        self.conn.commit()
        return True

    @return_on_failure
    def getMilkPurchased(self, user_id):
        if not self.checkUser(user_id):
            return
        cur = self.conn.cursor()
        cur.execute("SELECT price FROM milk_purchase WHERE user_id = '{}'".format(user_id))
        milk = cur.fetchall()
        milk = np.array(milk)
        print("User {} has spent a total of {} Euro purchasing milk.".format(user_id, milk.sum()))
        return milk.sum()

    @return_on_failure
    def getBeansPurchased(self, user_id):
        if not self.checkUser(user_id):
            return
        cur = self.conn.cursor()
        cur.execute("SELECT price FROM bean_purchase WHERE user_id = '{}'".format(user_id))
        beans = cur.fetchall()
        beans = np.array(beans)
        print("User {} has spent a total of {} Euro purchasing beans.".format(user_id, beans.sum()))
        return beans.sum()

    @return_on_failure
    def addTreasuryDeposit(self, date, amount, comment):
        if comment == "":
            print("Donations must contain a comment!")
            return False
        cur = self.conn.cursor()
        cur.execute("INSERT INTO treasury_deposits (date, amount, comment) VALUES('{}', '{}', '{}')".format(date, amount, comment))
        self.conn.commit()
        return True

    @return_on_failure
    def getCurrentCoffeePrice(self):
        cur = self.conn.cursor()
        cur.execute("SELECT current_coffee_price FROM constants WHERE id = 1")
        price = cur.fetchall()[0][0]
        if price <= 0.0:
            raise Exception("Coffee price is kaputt.")
        return price

    @return_on_failure
    def addGearPurchase(self, product_str, date, price, user_id):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO gear_purchase (user_id, date, name, price) VALUES('{}', '{}', '{}', '{}')".format(user_id, date, product_str, price))
        self.conn.commit()
        return True

    @return_on_failure
    def getTotalBalance(self):
        cur = self.conn.cursor()
        cur.execute("SELECT total_balance FROM total_balance")
        tot_bal = cur.fetchall()
        return tot_bal[0][0]

    @return_on_failure
    def getTotalCoffees(self):
        cur = self.conn.cursor()
        cur.execute("SELECT total_count FROM total_balance")
        tot_count = cur.fetchall()
        return tot_count[0][0]
    
    @return_on_failure
    def getCoffeeTypes(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM coffee_types")
        types = cur.fetchall()
        type_ids = []
        type_names = []
        for type in types:
            type_ids.append(type[0])
            type_names.append(type[1])
        return type_ids, type_names
    
    @return_on_failure
    def getMilkTypes(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM milk_types")
        types = cur.fetchall()
        type_ids = []
        type_names = []
        for type in types:
            type_ids.append(type[0])
            type_names.append(type[1])
        return type_ids, type_names
    
    @return_on_failure
    def getMilkTypeFromID(self, milk_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT type_name FROM milk_types WHERE type_id='{milk_id}'")
        type_name = cur.fetchone()
        return type_name[0]
    
    @return_on_failure
    def getMilkTypeIDFromName(self, milk_type):
        cur = self.conn.cursor()
        cur.execute(f"SELECT type_id FROM milk_types WHERE (type_name LIKE '{milk_type}')")
        type_id = cur.fetchone()
        return type_id[0]
    
    @return_on_failure
    def getMilkTypeIDFromProduct(self, product_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT type FROM milk_products WHERE product_id='{product_id}'")
        type_id = cur.fetchone()
        return type_id[0]
    
    @return_on_failure
    def getSugarTypeFromID(self, sugar_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT type_name FROM sugar_types WHERE type_id='{sugar_id}'")
        type_name = cur.fetchone()
        return type_name[0]
    
    @return_on_failure
    def getSugarTypes(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sugar_types")
        types = cur.fetchall()
        type_ids = []
        type_names = []
        for type in types:
            type_ids.append(type[0])
            type_names.append(type[1])
        return type_ids, type_names
    
    @return_on_failure
    def getSugarTypeIDFromName(self, sugar_type):
        cur = self.conn.cursor()
        cur.execute(f"SELECT type_id FROM sugar_types WHERE (type_name LIKE '{sugar_type}')")
        type_id = cur.fetchone()
        return type_id[0]

    # check refill_screen
    @return_on_failure
    def insertOrUpdateRecipe(self, bean_product_id, user_id, portafilter, grind_size, grind_duration, extraction_duration, recipe_name, comment = ""):
        cur = self.conn.cursor()
        #cur.execute(f"INSERT INTO coffee_recipes (bean_product_id, user_id, portafilter, grind_size, grind_duration, extraction_duration, recipe_name, comment) VALUES ({bean_product_id}, {user_id}, {portafilter}, {grind_size}, {grind_duration}, {extraction_duration}, {recipe_name}, {comment})")
        cur.execute(f"""IF EXISTS (SELECT * FROM coffee_recipes WHERE (recipe_name LIKE '{recipe_name}'))
                        BEGIN
                            UPDATE coffee_recipes SET user_id='{user_id}', bean_product_id='{bean_product_id}', portafilter='{portafilter}', grind_size='{grind_size}', grind_duration='{grind_duration}', extraction_duration='{extraction_duration}', comment='{comment}'
                            WHERE (recipe_name LIKE '{recipe_name}')
                        END
                        ELSE
                        BEGIN
                            INSERT INTO coffee_recipes (bean_product_id, user_id, portafilter, grind_size, grind_duration, extraction_duration, recipe_name, comment) VALUES ('{bean_product_id}', '{user_id}', '{portafilter}', '{grind_size}', '{grind_duration}', '{extraction_duration}', '{recipe_name}', '{comment}')
                        END""")
        self.conn.commit()

    # check refill_screen
    @return_on_failure
    def getRecipe(self, recipe_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM coffee_recipes WHERE (recipe_name LIKE '{recipe_name}')")
        columns = [column[0] for column in cur.description]
        data = cur.fetchone()
        return dict(zip(columns, data))
    
    # check refill_screen
    @return_on_failure
    def getRecipeNames(self):
        cur = self.conn.cursor()
        cur.execute("SELECT recipe_name FROM coffee_recipes")
        row = cur.fetchall()
        return row
    
    # check refill_screen
    @return_on_failure
    def getRecipePortafilter(self, recipe_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT portafilter FROM coffee_recipes WHERE recipe_name='{recipe_name}'")
        row = cur.fetchone()
        return row

    # check refill_screen
    @return_on_failure
    def getRecipeGrindSize(self, recipe_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT grind_size FROM coffee_recipes WHERE recipe_name='{recipe_name}'")
        row = cur.fetchone()
        return row
    
    # check refill_screen
    @return_on_failure
    def getRecipeGrindDuration(self, recipe_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT grind_duration FROM coffee_recipes WHERE recipe_name='{recipe_name}'")
        row = cur.fetchone()
        return row
    
    # check refill_screen
    @return_on_failure
    def getRecipeExecutionDuration(self, recipe_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT execution_duration FROM coffee_recipes WHERE recipe_name='{recipe_name}'")
        row = cur.fetchone()
        return row
    
    # check refill_screen
    @return_on_failure
    def getRecipeCoffee(self, recipe_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT coffee_bean_type FROM coffee_recipes WHERE recipe_name='{recipe_name}'")
        row = cur.fetchone()
        return row

    @return_on_failure
    def getUserData(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users JOIN user_profiles ON users.user_id = user_profiles.user_id WHERE users.user_id='{user_id}' OR user_profiles.user_id='{user_id}';")
        data = cur.fetchone()
        return data

    @return_on_failure
    def getRefillBeanType(self):
        bean_id = self.getRefillBeanID()
        return self.getBeanProductName(bean_id)
    
    @return_on_failure
    def getRefillBeanID(self):
        cur = self.conn.cursor()
        cur.execute("SELECT bean_product_id FROM refill ORDER BY refill_time DESC")
        row = cur.fetchone()
        return row[0]
    
    @return_on_failure
    def getTodaysCoffeeAmount(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT COUNT(date) FROM coffees WHERE date >= CONVERT(DATETIMEOFFSET, CONVERT(DATE, SYSDATETIMEOFFSET())) AND user_id='{user_id}'") 
        data = cur.fetchone()
        self.conn.commit()
        if data is None:
            return 0
        else:
            return data[0]

    @return_on_failure
    def getConfigBillingData(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT bsc_amount_coffee_today, bsc_debts, bsc_weekly_stats, bsc_daily_coffee_limit, bsc_coffee_limit_notification FROM user_profiles WHERE user_id='{user_id}'")
        columns = [column[0] for column in cur.description]
        data = cur.fetchone()
        return dict(zip(columns, data))

    @return_on_failure
    def getUserProfileData(self, user_id):
        cur = self.conn.cursor()
        cur.description
        cur.execute(f"SELECT * FROM user_profiles WHERE user_id='{user_id}'")
        columns = [column[0] for column in cur.description]
        data = cur.fetchone()
        return dict(zip(columns, data))
    
    @return_on_failure
    def billCoffee(self, user_id):
        price = self.getCurrentCoffeePrice()
        bean_product_id = self.getRefillBeanID()
        user_profile_data = self.getUserProfileData(user_id)
        coffee_type = user_profile_data["cc_coffee_type"]
        milk_type_id = user_profile_data["cc_milk_type"]
        milk_shots = user_profile_data["cc_milk_shots"]
        sugar_type_id = user_profile_data["cc_sugar_type"]
        sugar_tsp = user_profile_data["cc_sugar_tsp"]
        cur = self.conn.cursor()
        cur.execute(f"INSERT INTO coffees (user_id, price, coffee_type, bean_product_id, milk_type_id, milk_shots, sugar_type_id, sugar_tsp) VALUES ('{user_id}', '{price}', '{coffee_type}', '{bean_product_id}', '{milk_type_id}', '{milk_shots}', '{sugar_type_id}', '{sugar_tsp}')")   
        self.conn.commit()

    @return_on_failure
    def getBeanStockOf(self, bean_product_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT stock FROM bean_stock WHERE product_id='{bean_product_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
        
    @return_on_failure
    def getMilkStockOf(self, milk_product_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT stock FROM milk_stock WHERE product_id='{milk_product_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
        
    @return_on_failure
    def getSugarStockOf(self, sugar_type_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT stock FROM sugar_stock WHERE type_id='{sugar_type_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None

    
    @return_on_failure
    def getUserProfilePortafilter(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT cc_portafilter FROM user_profiles WHERE user_id='{user_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
    
    @return_on_failure
    def getUserProfileMilkType(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT cc_milk_type FROM user_profiles WHERE user_id='{user_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
    
    @return_on_failure
    def getUserProfileMilkShots(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT cc_milk_shots FROM user_profiles WHERE user_id='{user_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
    
    @return_on_failure
    def getUserProfileSugarType(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT cc_sugar_type FROM user_profiles WHERE user_id='{user_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
    
    @return_on_failure
    def getUserProfileSugarTSP(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT cc_sugar_tsp FROM user_profiles WHERE user_id='{user_id}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None

    @return_on_failure
    def getStockOfMilkType(self, milk_type):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id, stock FROM milk_stock WHERE stock > '0.0'")
        rows = cur.fetchall()
        type_amount = 0.0
        if rows:
            for row in rows:
                product_id = row[0]
                stock = row[1]
                type_id = self.getMilkTypeIDFromProduct(product_id)
                if type_id == milk_type:
                    type_amount += stock
            return type_amount
        else:
            return 0.0
        
    @return_on_failure
    def getSugarTypeAmount(self, sugar_type):
        cur = self.conn.cursor()
        cur.execute(f"SELECT stock FROM sugar_stock WHERE type_id='{sugar_type}'")
        row = cur.fetchone()
        if row:
            return row[0]
        else:
            return None
    
    @return_on_failure
    def updateResourcesOnCoffeeBill(self, bean_product_id, milk_product_id, sugar_type_id, cal_coffee, cal_milk, cal_sugar):
        cur = self.conn.cursor()
        if not 'NoneType' in str(cal_coffee):
            cur.execute(f"UPDATE bean_stock SET stock='{cal_coffee}', last_edit_timestamp=SYSDATETIMEOFFSET()  WHERE product_id='{bean_product_id}' AND stock!='{cal_coffee}'")
        if not 'NoneType' in str(cal_milk):
            cur.execute(f"UPDATE milk_stock SET stock='{cal_milk}', last_edit_timestamp=SYSDATETIMEOFFSET()  WHERE product_id='{milk_product_id}' AND stock!='{cal_milk}'")
        if not 'NoneType' in str(cal_sugar):
            cur.execute(f"UPDATE sugar_stock SET stock='{cal_sugar}', last_edit_timestamp=SYSDATETIMEOFFSET()  WHERE type_id='{sugar_type_id}' AND stock!='{cal_sugar}'")
        self.conn.commit()

    @return_on_failure
    def getAllResources(self):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id, stock FROM bean_stock")
        coffee_resource_list = cur.fetchall()

        cur.execute("SELECT product_id, stock FROM milk_stock")
        milk_resource_list = cur.fetchall()

        cur.execute("SELECT type_id, stock FROM sugar_stock")
        sugar_resource_list = cur.fetchall()

        return coffee_resource_list, milk_resource_list, sugar_resource_list
    
    def getAllResourcesWithNames(self):
        coffee_list, milk_list, sugar_list = self.getAllResources()
        new_coffee_list = []
        for coffee in coffee_list:
            name = self.getBeanProductName(coffee[0])
            new_coffee_list.append([name, coffee[1]])

        new_milk_list = []
        for milk in milk_list:
            name = self.getMilkProductName(milk[0])
            new_milk_list.append([name, milk[1]])

        new_sugar_list = []
        for sugar in sugar_list:
            name = self.getSugarTypeFromID(sugar[0])
            new_sugar_list.append([name, sugar[1]])

        return new_coffee_list, new_milk_list, new_sugar_list
    
    @return_on_failure
    def getEarliestAndLatestDrinkerLast7Days(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        coffee_date,
                        earliest_coffee_timestamp,
                        CASE
                            WHEN up_earliest.ps_earliest_latest_drinker_ranking = 1 THEN CONCAT(u_earliest.first_name, ' ', u_earliest.last_name)
                            ELSE 'anonymous'
                        END AS earliest_coffee_user,
                        latest_coffee_timestamp,
                        CASE
                            WHEN up_latest.ps_earliest_latest_drinker_ranking = 1 THEN CONCAT(u_latest.first_name, ' ', u_latest.last_name)
                            ELSE 'anonymous'
                        END AS latest_coffee_user
                    FROM (
                        SELECT
                            CONVERT(DATE, date) AS coffee_date,
                            MIN(date) AS earliest_coffee_timestamp,
                            MAX(date) AS latest_coffee_timestamp
                        FROM coffees
                        WHERE date >= DATEADD(DAY, -7, GETDATE()) AND date <= GETDATE()
                        GROUP BY CONVERT(DATE, date)
                    ) cc
                    LEFT JOIN coffees eb_earliest ON cc.coffee_date = CONVERT(DATE, eb_earliest.date) AND cc.earliest_coffee_timestamp = eb_earliest.date
                    LEFT JOIN coffees eb_latest ON cc.coffee_date = CONVERT(DATE, eb_latest.date) AND cc.latest_coffee_timestamp = eb_latest.date
                    LEFT JOIN users u_earliest ON eb_earliest.user_id = u_earliest.id
                    LEFT JOIN users u_latest ON eb_latest.user_id = u_latest.id
                    LEFT JOIN user_profiles up_earliest ON u_earliest.id = up_earliest.user_id
                    LEFT JOIN user_profiles up_latest ON u_latest.id = up_latest.user_id 
                    ORDER BY coffee_date
                    """)
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getTime(self):
        cur = self.conn.cursor()
        cur.execute("SELECT SYSDATETIMEOFFSET()")
        time = cur.fetchone()
        return time[0]

    @return_on_failure
    def getUserData(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM users JOIN user_profiles ON users.id = user_profiles.user_id WHERE users.id='{user_id}' OR user_profiles.user_id='{user_id}'")
        columns = [column[0] for column in cur.description]
        data = cur.fetchone()
        return dict(zip(columns, data))
    
    @return_on_failure
    def updateUser(self, user_id, first_name, last_name, rfids: list, email = ""):
        cur = self.conn.cursor()
        print(f"[BDManager] rfids: {rfids}")
        if rfids == []:
            cur.execute(f"UPDATE users SET first_name='{first_name}', last_name='{last_name}', email='{email}', WHERE id='{user_id}'")
        else:
            rfids_for_db = ["" for x in range(5)]
            codes = len(rfids) if len(rfids) <= 5 else 5
            for i in range(codes):
                rfids_for_db[i] = rfids[i]
            cur.execute(f"UPDATE users SET first_name='{first_name}', last_name='{last_name}', email='{email}', rfid='{rfids_for_db[0]}', rfid1='{rfids_for_db[1]}', rfid2='{rfids_for_db[2]}', rfid3='{rfids_for_db[3]}', rfid4='{rfids_for_db[4]}' WHERE id='{user_id}'")
        self.conn.commit()

    @return_on_failure
    def createUserProfile(self, user_id):
        cur = self.conn.cursor()
        if self.checkUser(user_id):
            cur.execute(f"INSERT INTO user_profiles (user_id) VALUES('{user_id}')")
            self.conn.commit()

    @return_on_failure
    def getUserIdList(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM users")
        res = cur.fetchall()
        user_ids = []
        for id in res:
            user_ids.append(id[0])
        return user_ids

    @return_on_failure
    def updateUserCoffeeOrder(self, user_id, coffee_type, milk_type_id, milk_shots, sugar_type_id, sugar_tsp):
        cur = self.conn.cursor()
        #cur.execute(f"INSERT INTO user_profiles (user_id, cc_coffee_type, cc_milk_type, cc_milk_shots, cc_sugar_type, cc_sugar_tsp) VALUES ('{user_id}','{coffee_type}','{milk_type_id}','{milk_shots}','{sugar_type_id}','{sugar_tsp}') ON CONFLICT (user_id) DO UPDATE SET cc_coffee_type='{coffee_type}', cc_milk_type='{milk_type_id}', cc_milk_shots='{milk_shots}', cc_sugar_type='{sugar_type_id}', cc_sugar_tsp='{sugar_tsp}'")
        cur.execute(f"""IF EXISTS (SELECT * FROM user_profiles WHERE user_id='{user_id}')
                        BEGIN
                            UPDATE user_profiles SET cc_coffee_type='{coffee_type}', cc_milk_type='{milk_type_id}', cc_milk_shots='{milk_shots}', cc_sugar_type='{sugar_type_id}', cc_sugar_tsp='{sugar_tsp}'
                            WHERE user_id='{user_id}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO user_profiles (user_id, cc_coffee_type, cc_milk_type, cc_milk_shots, cc_sugar_type, cc_sugar_tsp) VALUES ('{user_id}','{coffee_type}','{milk_type_id}','{milk_shots}','{sugar_type_id}','{sugar_tsp}')
                        END""")
        self.conn.commit()

    @return_on_failure
    def updateUserProfile(self, user_id, amount_coffee, amount_debt, weekly_stats, daily_limit, notification):
        cur = self.conn.cursor()
        #cur.execute(f"INSERT INTO user_profiles (user_id, bsc_amount_coffee_today, bsc_debts, bsc_weekly_stats, bsc_daily_coffee_limit, bsc_coffee_limit_notification) VALUES ('{user_id}','{amount_coffee}','{amount_debt}','{weekly_stats}','{daily_limit}','{notification}') ON CONFLICT (user_id) DO UPDATE SET bsc_amount_coffee_today='{amount_coffee}', bsc_debts='{amount_debt}', bsc_weekly_stats='{weekly_stats}', bsc_daily_coffee_limit='{daily_limit}', bsc_coffee_limit_notification='{notification}'")
        cur.execute(f"""IF EXISTS (SELECT * FROM user_profiles WHERE user_id='{user_id}')
                        BEGIN
                            UPDATE user_profiles SET bsc_amount_coffee_today='{amount_coffee}', bsc_debts='{amount_debt}', bsc_weekly_stats='{weekly_stats}', bsc_daily_coffee_limit='{daily_limit}', bsc_coffee_limit_notification='{notification}'
                            WHERE user_id='{user_id}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO user_profiles (user_id, bsc_amount_coffee_today, bsc_debts, bsc_weekly_stats, bsc_daily_coffee_limit, bsc_coffee_limit_notification) VALUES ('{user_id}','{amount_coffee}','{amount_debt}','{weekly_stats}','{daily_limit}','{notification}')
                        END""")
        self.conn.commit()

    @return_on_failure
    def updateUserConsent(self, user_id, consent_highscore, consent_debt_ranking, consent_EL_drinkers, consent_resources_purchase, consent_refill):
        cur = self.conn.cursor()
        #cur.execute(f"INSERT INTO user_profiles (user_id, ps_highscore_ranking, ps_debts_ranking, ps_earliest_latest_drinker_ranking, ps_resource_purchase_ranking, ps_refill_ranking) VALUES ('{user_id}','{consent_highscore}','{consent_debt_ranking}','{consent_EL_drinkers}','{consent_resources_purchase}','{consent_refill}') ON CONFLICT (user_id) DO UPDATE SET ps_highscore_ranking='{consent_highscore}', ps_debts_ranking='{consent_debt_ranking}', ps_earliest_latest_drinker_ranking='{consent_EL_drinkers}', ps_resource_purchase_ranking='{consent_resources_purchase}', ps_refill_ranking='{consent_refill}'")
        cur.execute(f"""IF EXISTS (SELECT * FROM user_profiles WHERE user_id='{user_id}')
                        BEGIN
                            UPDATE user_profiles SET ps_highscore_ranking='{consent_highscore}', ps_debts_ranking='{consent_debt_ranking}', ps_earliest_latest_drinker_ranking='{consent_EL_drinkers}', ps_resource_purchase_ranking='{consent_resources_purchase}', ps_refill_ranking='{consent_refill}'
                            WHERE user_id='{user_id}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO user_profiles (user_id, ps_highscore_ranking, ps_debts_ranking, ps_earliest_latest_drinker_ranking, ps_resource_purchase_ranking, ps_refill_ranking) VALUES ('{user_id}','{consent_highscore}','{consent_debt_ranking}','{consent_EL_drinkers}','{consent_resources_purchase}','{consent_refill}') 
                        END""")
        self.conn.commit()

    @return_on_failure
    def submitBeanRating(self, user_id, bean_product_id, rating):
        cur = self.conn.cursor()
        cur.execute(f"""IF EXISTS (SELECT * FROM bean_rating WHERE user_id='{user_id}' AND product_id='{bean_product_id}')
                        BEGIN
                            UPDATE bean_rating SET rating='{rating}', time_of_rating=SYSDATETIMEOFFSET()
                            WHERE product_id='{bean_product_id}' AND user_id='{user_id}' AND rating!='{rating}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO bean_rating (user_id, product_id, rating) VALUES ('{user_id}','{bean_product_id}','{rating}')
                        END""")
        self.conn.commit()

    @return_on_failure
    def submitBeanRefill(self, user_id, bean_product_id, db_timestamp):
        cur = self.conn.cursor()
        cur.execute(f"INSERT INTO refill (user_id, bean_product_id, refill_time) VALUES ('{user_id}','{bean_product_id}','{db_timestamp}')")
        self.conn.commit()

    @return_on_failure
    def getCoffeeResources(self):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id, stock FROM bean_stock")
        columns = [column[0] for column in cur.description]
        rows = cur.fetchall()
        data = []
        for row in rows:
            data.append(dict(zip(columns, row)))
        return data
    
    @return_on_failure
    def updateBeanStock(self, user_id, new_stock, bean_product_id, price_per_kg = 0):
        cur = self.conn.cursor()
        #cur.execute(f"UPDATE bean_stock SET stock='{new_stock}', last_edit_timestamp=SYSDATETIMEOFFSET(), last_update_user_id='{user_id}' WHERE product_id='{bean_product_id}' AND stock!='{new_stock}'")
        cur.execute(f"""IF EXISTS (SELECT * FROM bean_stock WHERE product_id='{bean_product_id}')
                        BEGIN
                            UPDATE bean_stock SET stock='{new_stock}', last_edit_timestamp=SYSDATETIMEOFFSET(), last_update_user_id='{user_id}'
                            WHERE product_id='{bean_product_id}' AND stock!='{new_stock}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO bean_stock (product_id, stock, last_update_user_id, current_price_per_kg)
                            VALUES ('{bean_product_id}', '{new_stock}', '{user_id}', '{price_per_kg}')
                        END""")
        self.conn.commit()

    @return_on_failure
    def updateMilkStock(self, user_id, new_stock, milk_product_id, price_per_liter = 0):
        cur = self.conn.cursor()
        #cur.execute(f"UPDATE milk_stock SET stock='{new_stock}', last_edit_timestamp=SYSDATETIMEOFFSET(), last_update_user_id='{user_id}' WHERE product_id='{milk_product_id}' AND stock!='{new_stock}'")
        cur.execute(f"""IF EXISTS (SELECT * FROM milk_stock WHERE product_id='{milk_product_id}')
                        BEGIN
                            UPDATE milk_stock SET stock='{new_stock}', last_edit_timestamp=SYSDATETIMEOFFSET(), last_update_user_id='{user_id}'
                            WHERE product_id='{milk_product_id}' AND stock!='{new_stock}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO milk_stock (product_id, stock, last_update_user_id, current_price_per_liter)
                            VALUES ('{milk_product_id}', '{new_stock}', '{user_id}', '{price_per_liter}')
                        END""")
        self.conn.commit()

    @return_on_failure
    def updateSugarStock(self, user_id, new_stock, sugar_type_id):
        cur = self.conn.cursor()
        #cur.execute(f"UPDATE sugar_stock SET stock='{new_stock}', last_edit_timestamp=SYSDATETIMEOFFSET(), last_update_user_id='{user_id}' WHERE type_id='{sugar_type_id}' AND stock!='{new_stock}'")
        cur.execute(f"""IF EXISTS (SELECT * FROM sugar_stock WHERE type_id='{sugar_type_id}')
                        BEGIN
                            UPDATE sugar_stock SET stock='{new_stock}', last_edit_timestamp=SYSDATETIMEOFFSET(), last_update_user_id='{user_id}' 
                            WHERE type_id='{sugar_type_id}' AND stock!='{new_stock}'
                        END
                        ELSE
                        BEGIN
                            INSERT INTO sugar_stock (type_id, stock, last_update_user_id)
                            VALUES ('{sugar_type_id}', '{new_stock}', '{user_id}')
                        END""")
        self.conn.commit()

    @return_on_failure
    def getBeanProductIDAndRating(self):
        cur = self.conn.cursor()
        cur.execute("SELECT product_id, rating FROM bean_rating")
        rows = cur.fetchall()
        return rows
    
    def getBeanProductNameAndRating(self):
        rows = self.getBeanProductIDAndRating()
        print(rows)
        new_list = []
        for row in rows:
            bean_name = self.getBeanProductName(row[0])
            new_list.append([bean_name, row[1]])
        return new_list

    @return_on_failure
    def getPeakHoursData(self):
        cur = self.conn.cursor()
        cur.execute("""WITH intervals AS (
                        SELECT TOP 48
                            DATEADD(MINUTE, (ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1) * 30, DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()), 0)) AS interval_start
                        FROM master..spt_values
                        )
                        SELECT intervals.interval_start,
                            COUNT(coffees.date) AS entry_count
                        FROM intervals
                        LEFT JOIN coffees ON coffees.date >= intervals.interval_start
                            AND coffees.date < DATEADD(MINUTE, 30, intervals.interval_start)
                        WHERE CAST(coffees.date AS DATE) = CAST(GETDATE() AS DATE) OR coffees.date IS NULL
                        GROUP BY intervals.interval_start
                        ORDER BY intervals.interval_start;""")
        data = cur.fetchall()
        return data

    @return_on_failure
    def getHighscoreLast365Days(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        CASE
                            WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                            ELSE 'anonym'
                        END AS display_name,
                        COUNT(*) AS total_coffees_ordered
                        FROM
                            coffees c
                        JOIN
                            users u ON c.user_id = u.id
                        LEFT JOIN
                            user_profiles up ON u.id = up.user_id
                        WHERE
                            c.date >= DATEADD(DAY, -365, GETDATE())
                        GROUP BY
                            CASE
                                WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                                ELSE 'anonym'
                            END
                        ORDER BY
                            total_coffees_ordered ASC
                        OFFSET 0 ROWS FETCH NEXT 6 ROWS ONLY;""")
        data = cur.fetchall()
        return data


    #check stats_screen
    @return_on_failure
    def getHighscoreLast30Days(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        CASE
                            WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                            ELSE 'anonymous'
                        END AS display_name,
                        COUNT(*) AS total_coffees_ordered
                        FROM
                            coffees c
                        JOIN
                            users u ON c.user_id = u.id
                        LEFT JOIN
                            user_profiles up ON u.id = up.user_id
                        WHERE
                            c.date >= DATEADD(DAY, -30, GETDATE())
                        GROUP BY
                            CASE
                                WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                                ELSE 'anonymous'
                            END
                        ORDER BY
                            total_coffees_ordered ASC
                        OFFSET 0 ROWS FETCH NEXT 6 ROWS ONLY;""")
        data = cur.fetchall()
        return data

    #check stats_screen
    @return_on_failure
    def getHighscoreLast7Days(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        CASE
                            WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                            ELSE 'anonymous'
                        END AS display_name,
                        COUNT(*) AS total_coffees_ordered
                        FROM
                            coffees c
                        JOIN
                            users u ON c.user_id = u.id
                        LEFT JOIN
                            user_profiles up ON u.id = up.user_id
                        WHERE
                            c.date >= DATEADD(DAY, -7, GETDATE())
                        GROUP BY
                            CASE
                                WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                                ELSE 'anonymous'
                            END
                        ORDER BY
                            total_coffees_ordered ASC
                        OFFSET 0 ROWS FETCH NEXT 6 ROWS ONLY;""")
        data = cur.fetchall()
        return data
        
    #check stats_screen
    @return_on_failure
    def getHighscoreToday(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        CASE
                            WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                            ELSE 'anonymous'
                        END AS display_name,
                        COUNT(*) AS total_coffees_ordered
                        FROM
                            coffees c
                        JOIN
                            users u ON c.user_id = u.id
                        LEFT JOIN
                            user_profiles up ON u.id = up.user_id
                        WHERE
                            CAST(c.date AS DATE) = CAST(GETDATE() AS DATE)
                        GROUP BY
                            CASE
                                WHEN up.ps_highscore_ranking = 1 THEN CONCAT(u.first_name, ' ', u.last_name)
                                ELSE 'anonymous'
                            END
                        ORDER BY
                            total_coffees_ordered ASC
                        OFFSET 0 ROWS FETCH NEXT 6 ROWS ONLY;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getDebtsRanking(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        CASE
                            WHEN up.ps_debts_ranking = 1 THEN CONCAT(ub.first_name, ' ', ub.last_name)
                            ELSE 'anonymous'
                        END AS display_name,
                        ub.balance
                        FROM
                            user_balance ub
                        LEFT JOIN
                            user_profiles up ON ub.user_id = up.user_id
                        ORDER BY
                            ub.balance ASC
                        OFFSET 0 ROWS FETCH NEXT 6 ROWS ONLY;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getPurchaseOverview(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                        CASE
                            WHEN up.ps_resource_purchase_ranking = 1 THEN MAX(CONCAT(u.first_name, ' ', u.last_name))
                            ELSE 'anonymous'
                        END AS u_name,
                        SUM(price) AS total_price
                        FROM
                        (
                            SELECT user_id, price
                            FROM bean_purchase
                            WHERE date >= DATEADD(DAY, -365, GETDATE())
                            UNION ALL
                            SELECT user_id, price
                            FROM milk_purchase
                            WHERE date >= DATEADD(DAY, -365, GETDATE())
                        ) AS combined_purchases
                        JOIN users u ON combined_purchases.user_id = u.id
                        LEFT JOIN user_profiles up ON u.id = up.user_id
                        GROUP BY
                            u.id,
                            up.ps_resource_purchase_ranking;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getRefillPerUser(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                            CASE
                                WHEN up.ps_refill_ranking = 1 THEN MAX(CONCAT(u.first_name, ' ', u.last_name))
                                ELSE 'anonymous'
                            END AS user_name,
                            COUNT(rh.user_id) AS refill_count
                        FROM
                            refill rh
                        JOIN
                            users u ON rh.user_id = u.id
                        LEFT JOIN
                            user_profiles up ON u.id = up.user_id
                        GROUP BY
                            u.id, up.ps_refill_ranking
                        ORDER BY
                            refill_count DESC
                        OFFSET 0 ROWS FETCH NEXT 6 ROWS ONLY;""")
        data = cur.fetchall()
        return data

    @return_on_failure
    def getBillCoffeeLast12MonthByCoffeeType(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                            CONVERT(VARCHAR(7), months.month, 120) AS month,
                            CAST(coffees.coffee_type AS VARCHAR(MAX)) AS coffee_type,
                            COUNT(coffees.date) AS entry_count
                        FROM
                        (
                            SELECT
                                DATEADD(MONTH, -n, DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)) AS month
                            FROM
                                (SELECT TOP 12 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n FROM master..spt_values) AS Numbers
                        ) AS months
                        LEFT JOIN coffees ON DATEADD(MONTH, DATEDIFF(MONTH, 0, coffees.date), 0) = months.month
                                        AND coffees.coffee_type IS NOT NULL
                        GROUP BY
                            months.month,
                            CAST(coffees.coffee_type AS VARCHAR(MAX))
                        ORDER BY
                            months.month;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getBillCoffeeLast30DaysByCoffeeType(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                            CONVERT(VARCHAR(10), dates.date, 120) AS date,
                            CAST(coffees.coffee_type AS VARCHAR(MAX)) AS coffee_type,
                            COUNT(coffees.date) AS entry_count
                        FROM
                        (
                            SELECT
                                DATEADD(DAY, -n, DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()), 0)) AS date
                            FROM
                                (SELECT TOP 30 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n FROM master..spt_values) AS Numbers
                        ) AS dates
                        LEFT JOIN
                        coffees ON CAST(coffees.date AS DATE) = dates.date
                        WHERE coffees.coffee_type IS NOT NULL
                        GROUP BY
                        dates.date,
                        CAST(coffees.coffee_type AS VARCHAR(MAX))
                        ORDER BY
                        dates.date;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getBillCoffeeLast7DaysByCoffeeType(self):
        cur = self.conn.cursor()
        cur.execute("""SELECT
                            CONVERT(VARCHAR(10), dates.date, 120) AS date,
                            CAST(coffees.coffee_type AS VARCHAR(MAX)) AS coffee_type,
                            COUNT(coffees.date) AS entry_count
                        FROM
                        (
                            SELECT
                                DATEADD(DAY, -n, DATEADD(DAY, DATEDIFF(DAY, 0, GETDATE()), 0)) AS date
                            FROM
                                (SELECT TOP 7 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n FROM master..spt_values) AS Numbers
                        ) AS dates
                        LEFT JOIN
                        coffees ON CAST(coffees.date AS DATE) = dates.date
                        WHERE coffees.coffee_type IS NOT NULL
                        GROUP BY
                        dates.date,
                        CAST(coffees.coffee_type AS VARCHAR(MAX))
                        ORDER BY
                        dates.date;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getPersonalCoffeeOverMonth(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"""SELECT 
                            CAST(date AS DATE) AS billing_date,
                            COUNT(*) AS entries_per_day
                        FROM 
                            coffees
                        WHERE 
                            user_id = '{user_id}'
                            AND date >= DATEADD(DAY, -30, GETDATE()) 
                            AND date <= GETDATE()
                        GROUP BY 
                            CAST(date AS DATE)
                        ORDER BY 
                            billing_date;
                        """)
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getPersonalCoffeeOverYear(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"""SELECT 
                            FORMAT(date, 'yyyy-MM') AS billing_month,
                            COUNT(*) AS entries_per_month
                        FROM 
                            coffees
                        WHERE 
                            user_id = '{user_id}'
                            AND date >= DATEADD(DAY, -365, GETDATE()) 
                            AND date <= GETDATE()
                        GROUP BY 
                            FORMAT(date, 'yyyy-MM')
                        ORDER BY 
                            billing_month;""")
        data = cur.fetchall()
        return data
    
    @return_on_failure
    def getPersonalCoffeeOverWeek(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"""WITH DateSeries AS (
                            SELECT DATEADD(DAY, n, DATEADD(DAY, -6, GETDATE())) AS generated_date
                            FROM (SELECT TOP 7 ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n FROM master.dbo.spt_values) n
                        )
                        SELECT 
                            CAST(generated_date AS DATE) AS billing_date,
                            COUNT(coffees.date) AS entries_per_day
                        FROM 
                            DateSeries
                        LEFT JOIN 
                            coffees
                            ON CAST(coffees.date AS DATE) = CAST(generated_date AS DATE) AND coffees.user_id = '{user_id}'
                        GROUP BY 
                            CAST(generated_date AS DATE)
                        ORDER BY 
                            billing_date;""")
        data = cur.fetchall()
        return data

    @return_on_failure
    def getAvgDebtsWOUser(self, user_id):
        cur = self.conn.cursor()
        cur.execute(f"""SELECT AVG(-balance) AS average_debts
            FROM user_balance
            WHERE user_id <> '{user_id}';""")
        data = cur.fetchone()
        return data
    
    def getMilkProductIDsOfTypeInStock(self, milk_type):
        cur = self.conn.cursor()
        cur.execute(f"""SELECT ms.product_id
                        FROM milk_stock ms
                        INNER JOIN milk_products mp ON ms.product_id = mp.product_id
                        WHERE mp.type = '{milk_type}' AND ms.stock > 0.0;
                    """)
        data = cur.fetchall()
        return data

    @return_on_failure
    def updateResourcesBeans(self, bean_name, priceCoffee, amountCoffee, user_id):
        product_id = self.getBeanProductIDfromName(bean_name)
        if product_id == "":
            print("[DBManager:updateResourcesBeans] ERROR: Bean product is not in product list.")
            return
        
        cur = self.conn.cursor()
        cur.execute(f"""MERGE INTO bean_stock AS target
                        USING (VALUES ({product_id})) AS source(product_id)
                        ON target.product_id = source.product_id
                        WHEN MATCHED THEN
                            UPDATE SET 
                                current_price_per_kg = {priceCoffee},
                                stock = target.stock + {amountCoffee},
                                last_edit_timestamp = SYSDATETIMEOFFSET(),
                                last_update_user_id = {user_id}
                        WHEN NOT MATCHED THEN
                            INSERT (product_id, current_price_per_kg, stock, last_update_user_id)
                            VALUES ({product_id}, {priceCoffee}, {amountCoffee}, {user_id});""")

        self.conn.commit()

    @return_on_failure
    def updateResourcesMilk(self, milk_name, priceMilk, amountMilk, user_id):
        product_id = self.getMilkProductIDfromName(milk_name)
        if product_id == "":
            print("[DBManager:updateResourcesMilk] ERROR: Milk product is not in product list.")
            return
        
        cur = self.conn.cursor()
        cur.execute(f"""MERGE INTO milk_stock AS target
                        USING (VALUES ({product_id})) AS source(product_id)
                        ON target.product_id = source.product_id
                        WHEN MATCHED THEN
                            UPDATE SET 
                                current_price_per_liter = {priceMilk},
                                stock = target.stock + {amountMilk},
                                last_edit_timestamp = SYSDATETIMEOFFSET(),
                                last_update_user_id = {user_id}
                        WHEN NOT MATCHED THEN
                            INSERT (product_id, current_price_per_liter, stock, last_update_user_id)
                            VALUES ({product_id}, {priceMilk}, {amountMilk}, {user_id});""")

        self.conn.commit()

    @return_on_failure
    def updateResourcesSugar(self, sugar_type_name, amountSugar, user_id):
        type_id = self.getSugarTypeIDFromName(sugar_type_name)
        if type_id == "":
            print("[DBManager:updateResourcesSugar] ERROR: Sugar type is not in type list.")
            return
        
        cur = self.conn.cursor()
        cur.execute(f"""MERGE INTO sugar_stock AS target
                        USING (VALUES ({type_id})) AS source(product_id)
                        ON target.product_id = source.product_id
                        WHEN MATCHED THEN
                            UPDATE SET 
                                stock = target.stock + {amountSugar},
                                last_edit_timestamp = SYSDATETIMEOFFSET(),
                                last_update_user_id = {user_id}
                        WHEN NOT MATCHED THEN
                            INSERT (type_id, stock, last_update_user_id)
                            VALUES ({type_id}, {amountSugar}, {user_id});""")

        self.conn.commit()


if __name__ == '__main__':
    mngr = DBManager()

