import sys
from PySide6.QtWidgets import QApplication
from .gui.main_window import MainWindow

def main():
    """
    アプリケーションのエントリポイント。
    QApplication と MainWindow を初期化して実行します。
    """
    app = QApplication(sys.argv)
    
    # MainWindow がすべてのコンポーネント (スレッド、サービス、UI) を
    # 内部で初期化します。
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()