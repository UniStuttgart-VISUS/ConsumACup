from PyQt5.QtCore import QObject

class FocusTracker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_focused_widget = None

    def eventFilter(self, obj, event):
        if event.type() == event.FocusIn:
            self.last_focused_widget = obj
        return False