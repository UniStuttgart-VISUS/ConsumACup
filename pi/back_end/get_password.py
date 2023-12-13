from Crypto.Cipher import AES
from base64 import b64decode
import json

class DBPasswordCipher():
    def __init__(self):
        self.file = "pw.txt"

    def get_password(self, uid):
        key = "{:<16}".format(str(uid))
        f = open(self.file, "r")
        json_dump = f.read()
        f.close()
        b64 = json.loads(json_dump)
        iv = b64decode(b64["iv"])
        ct = b64decode(b64["ct"])
        cipher = AES.new(key, AES.MODE_CFB, iv)
        pw = cipher.decrypt(ct).decode("utf8")
        pw = pw.strip()
        return pw
