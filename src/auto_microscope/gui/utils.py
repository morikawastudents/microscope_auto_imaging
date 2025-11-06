import numpy as np
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QComboBox

# pyserial が必要です (pip install pyserial)
try:
    import serial.tools.list_ports
except ImportError:
    print("CRITICAL: 'pyserial' ライブラリが見つかりません。")
    print("           'pip install pyserial' を実行してください。")
    # GUI起動前にクラッシュさせるため、ここで例外を送出する
    raise

def np_array_to_qimage(frame: np.ndarray) -> QImage:
    """
    OpenCV の numpy 配列 (BGR) を PySide6 の QImage に変換します。
    """
    if frame is None:
        return QImage()
    
    height, width, channel = frame.shape
    bytes_per_line = 3 * width
    
    # BGR (OpenCV) から RGB (Qt) に変換
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # QImage を作成
    q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    
    # メモリリークを防ぐために .copy() が重要
    return q_image.copy()

def populate_com_ports(combo_box: QComboBox) -> list[str]:
    """
    利用可能なCOMポートを列挙し、QComboBox に追加します。
    検出されたポートデバイス名のリストを返します。
    """
    combo_box.clear()
    ports = serial.tools.list_ports.comports()
    
    detected_devices = []
    if not ports:
        combo_box.addItem("利用可能なポートがありません")
    else:
        for port in ports:
            # 表示名 (例: "USB Serial (COM3)") と 内部データ (例: "COM3") を分けて追加
            combo_box.addItem(f"{port.description}", port.device)
            detected_devices.append(port.device)
            
    return detected_devices

# cv2 (OpenCV) のインポート
# camera_thread.py と utils.py の両方で必要になる
try:
    import cv2
except ImportError:
    print("CRITICAL: 'opencv-python' ライブラリが見つかりません。")
    print("           'pip install opencv-python' を実行してください。")
    raise