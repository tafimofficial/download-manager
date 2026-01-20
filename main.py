import sys
import os

# Ensure we can import from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import TafimApp

if __name__ == "__main__":
    app = TafimApp()
    app.run()
