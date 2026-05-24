import sys
import pygame
from PyQt6.QtWidgets import QApplication 
from editor.main_window import EditorWindow

def main():
    pygame.init()
    
    app = QApplication(sys.argv)
    editor = EditorWindow(1024, 768)
    editor.show()
    
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()