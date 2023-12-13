import getpass
import os
import time
import json
from Crypto.Cipher import AES
from base64 import b64encode
import logging
import board
import busio
from adafruit_pn532.i2c import PN532_I2C


logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    i2c = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c=i2c, debug=False)
    pn532.SAM_configuration()
    print("Scan token")
    uid = pn532.read_passive_target(timeout=10)
    print(len(uid))
    if uid is not None:
        uid_hex = uid.hex()
        id = int(uid_hex, 16)
    print(f"ID: {id}")
    print(f"ID: {hex(id).replace('0x','')[:8]}")
    key = "{:<16}".format(id)
    #print("{}".format(key))
    print("Enter password")
    pw = getpass.getpass()
    iv = os.urandom(16)
    #print("iv {}".format(iv))
    cipher = AES.new(key, AES.MODE_CFB, iv)
    ct_bytes = cipher.encrypt(pw)
    #print("ct {}".format(ct_bytes))
    iv_t = b64encode(iv).decode("utf-8")
    ct = b64encode(ct_bytes).decode("utf-8")
    result = json.dumps({"iv":iv_t, "ct":ct})
    f = open("pw.txt", "w")
    f.write(result)
    f.close()
