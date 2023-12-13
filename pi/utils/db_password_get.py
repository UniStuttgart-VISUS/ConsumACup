import getpass
import os
import time
import json
from Crypto.Cipher import AES
from base64 import b64decode
import logging
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

if __name__ == "__main__":
    print("Scan token")
    i2c = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c=i2c, debug=False)
    pn532.SAM_configuration()
    uid = pn532.read_passive_target(timeout=10)
    if uid is not None:
        uid_hex = uid.hex()
        id = int(uid_hex, 16)
    key = "{:<16}".format(id)
    #print("{}".format(key))
    print("Enter password")
    f = open("pw.txt", "r")
    result = f.read()
    f.close()
    b64 = json.loads(result)
    iv = b64decode(b64["iv"])
    ct = b64decode(b64["ct"])
    cipher = AES.new(key, AES.MODE_CFB, iv)
    pw = cipher.decrypt(ct)
    print("Message: {}".format(pw))
