from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap, QImage

class CameraViewWidget(QWidget):
    """
    UIの左側（カメラ映像とピントスコア）を担当するウィジェット。
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. カメラビュー
        self.camera_label = QLabel("カメラ映像を待機中...")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        self.camera_label.setStyleSheet("background-color: #000; color: #fff; border-radius: 8px;")
        layout.addWidget(self.camera_label)
        
        # 2. ピントスコア
        focus_layout = QHBoxLayout()
        focus_layout.addWidget(QLabel("ピントスコア:"))
        
        self.focus_progress = QProgressBar()
        self.focus_progress.setRange(0, 2000) # (調整) 最大値を2000に設定
        self.focus_progress.setValue(0)
        self.focus_progress.setTextVisible(False)
        focus_layout.addWidget(self.focus_progress, 1) # プログレスバーを伸縮させる
        
        self.focus_label = QLabel("0.0")
        self.focus_label.setMinimumWidth(50) # 幅を固定
        self.focus_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        focus_layout.addWidget(self.focus_label)
        
        layout.addLayout(focus_layout)

    @Slot(QImage)
    def update_camera_view(self, q_image: QImage):
        """ (スロット) カメラスレッドから QImage を受け取り、表示を更新 """
        if q_image.isNull():
            return
        
        # ラベルのサイズに合わせて映像をスケーリング (アスペクト比維持)
        self.camera_label.setPixmap(QPixmap.fromImage(q_image).scaled(
            self.camera_label.width(), self.camera_label.height(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    @Slot(float)
    def update_focus_score(self, score: float):
        """ (スロット) カメラスレッドからピントスコアを受け取り、表示を更新 """
        self.focus_label.setText(f"{score:.2f}")
        
        max_val = self.focus_progress.maximum()
        self.focus_progress.setValue(min(int(score), max_val))