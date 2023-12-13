import time
import RUNTIME_CONFIG as cfg

if not cfg.DEBUG:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)


class Buzzer:
    def __init__(self):
        self.BUZZER_PIN = 12
        self.init_buzzer()

    def init_buzzer(self):
        if not cfg.DEBUG:
            GPIO.setup(self.BUZZER_PIN, GPIO.OUT)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def buzz_confirm(self):
        if not cfg.DEBUG:
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.4)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def buzz_decline(self):
        if not cfg.DEBUG:
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)

    def buzz_close(self):
        if not cfg.DEBUG:
            GPIO.cleanup(self.BUZZER_PIN)

    def __del__(self):
        self.buzz_close()