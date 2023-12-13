# This script contains the email configuration parameters
# In the config_object.read("C:/Users/example/path/to/EMAIL_CONFIG.ini")
# insert the path of your email config. Please us the back_end/EMAIL_CONFIG_TEMPLATE.ini file!
# For testing a Gmail account was created, you can use whatever you want!
# Helpful video for setting up Gmail: https://www.youtube.com/watch?v=g_j6ILT-X0k&ab_channel=ThePyCoach

from configparser import ConfigParser
import RUNTIME_CONFIG as cfg 
DEBUG = cfg.DEBUG

#Read config.ini file
config_object = ConfigParser()
if not DEBUG:
    config_object.read("/home/visus/Projects/ConsumAcup_Prod/delete/EMAIL_CONFIG.ini")
else:
    config_object.read("C:/Users/zaina/Desktop/EMAIL_CONFIG.ini")

co = config_object["EMAIL_CONFIG"]

EMAIL_SENDER=co["EMAIL_SENDER"]
EMAIL_PASSWORD = co["EMAIL_PASSWORD"]
SMTP_SERVER = co["SMTP_SERVER"]
PORT = co["PORT"]

# Resource email notification delta in days
NOTIFICATION_DELTA = 7

# Threshold email notification
THRESHOLD_COFFEE = 2000
THRESHOLD_MILK = 2000
THRESHOLD_SUGAR = 1000