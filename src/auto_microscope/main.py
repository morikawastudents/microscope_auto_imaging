import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication
from .gui.main_window import MainWindow

def main():
    """
    アプリケーションのエントリポイント。
    QApplication と MainWindow を初期化して実行します。
    """
    
    # --- (修正) QSettings のために組織名とアプリ名を設定 ---
    QCoreApplication.setOrganizationName("Morikawalab") # (任意の名前に変更可)
    QCoreApplication.setApplicationName("AutoMicroscopeImager")
    # --------------------------------------------------
    
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()