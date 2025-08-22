
from PyQt5.QtCore import QSize,Qt 
from PyQt5.QtWidgets import QApplication, QMainWindow,QPushButton

# Only needed for access to command line arguments
import sys


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")
        self.setMinimumSize(QSize(300,300)) 
        self.button = QPushButton("Press Me!")
        self.button.clicked.connect(self.the_button_was_clicked)
        #button.setCheckable(True)
        #self.button.released.connect(self.the_button_was_released)
        #self.button.setChecked(self.button_is_checked)
        

        # Set the central widget of the Window.
        self.setCentralWidget(self.button)

    
    def the_button_was_clicked(self):
        self.button.setText("You already clicked me.")
        self.button.setEnabled(False)

        # Also change the window title.
        self.setWindowTitle("A new window title")

def main():
    
    app = QApplication(sys.argv)

    # Create a Qt widget, which will be our window.
    window = MainWindow()
    window.show()  # IMPORTANT!!!!! Windows are hidden by default.

    # Start the event loop.
    app.exec()
    

if __name__ == '__main__':
    main()

