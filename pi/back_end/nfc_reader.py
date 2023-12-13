# This script is responsible for reading the nfc chips/codes presented to the nfc reader.
# The reader functionality is running on a Thread to seamlessly allow other interactions
# with the application
# When a new chip is captured a signal is being set with the UID of the chip
import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

from PyQt5.QtCore import pyqtSignal, QObject, pyqtSlot as Slot


# Create a custom QThread to handle reading NFC tags in the background
class NfcWorker(QObject):

    # Define a custom PyQt5 signal to emit NFC tag UID strings
    tag = pyqtSignal(str)
    finished = pyqtSignal()
    n = -1
    
    i2c = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c=i2c, debug=False)

    pn532.SAM_configuration()

    @Slot(int)
    def setn(self,n):
        self.n = n
        print("[NFC WORKER] setting n=" + str(n))
        self.scan()
        
    def scan(self):
        # Use this main loop to read NFC tags
        while True:
            # Check if an NFC tag is present
            if self.n < 1:
                self.finished.emit()
                break
            try:
                # If an NFC tag is detected, convert its UID to a string and emit the tag signal
                uid = self.pn532.read_passive_target(timeout=1.5)
                if uid is not None:
                    # str_uid = str([hex(i) for i in uid]) # Convert the UID from a byte array to a string with hexadecimal values
                    #str_uid = ''.join(str(i) for i in uid)
                    # rfid = 0
                    # for i in range(4):
                    #     rfid = rfid * 256 + uid[i]
                    uid_hex = uid.hex()
                    uid_int = int(uid_hex, 16)
                    self.tag.emit(str(uid_int)) # Emit the tag signal with the UID string as its argument
                    time.sleep(3)

                    self.finished.emit()
                    time.sleep(0.5)
                    # break
            except RuntimeError: #going to be thrown when Thread object is being destroy in exit function
                print("[EXCEPTION HANDLED] NfcReaderThread destroyed through Exit function!")
