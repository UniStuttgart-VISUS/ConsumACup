# Bachelor Thesis Project
# ConsumAcup
# @author Zainab Al-Taie

# This is the entry point of the application

# Import necessary libraries and classes
import sys, os
from PyQt5.QtWidgets import *       # This gets the Qt stuff
import front_end.main_window
from PyQt5.QtCore import Qt

import RUNTIME_CONFIG as cfg 

DEBUG = cfg.DEBUG

# Call the main function if this script is being run as the main program
if __name__ == "__main__":
    # Create a new QApplication object which initializes the PyQt5 framework to use in our application
    app = QApplication(sys.argv)
    
    # Create an instance of the MainWindow class which represents the main window of the application
    main_window = front_end.main_window.MainWindow()

    main_window.show()

    # Ensure that the application is terminated correctly when the user closes the main window
    sys.exit(app.exec_())