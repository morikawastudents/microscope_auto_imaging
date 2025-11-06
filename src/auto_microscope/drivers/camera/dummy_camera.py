import time
import numpy as np

# (修正) ... (3ドット) から .. (2ドット) へ変更
from ...core.exceptions import CameraConnectionError 
from .abstract_camera import AbstractCamera

# (おまけ) cv2 がない環境でも動作確認するための最小限のスタブ
# (本番環境では `pip install opencv-python-headless` が必要)
try:
    import cv2
except ImportError:
    print("WARNING: OpenCV (cv2) が見つかりません。ダミー画像にテキストを描画できません。")
    # cv2 と FONT_HERSHEY_SIMPLEX のダミースタブを作成
    class cv2:
        FONT_HERSHEY_SIMPLEX = 0 # ダミーの値
        
        @staticmethod
        def putText(img, text, org, fontFace, fontScale, color, thickness):
            # テキスト描画の代わりにコンソールに出力
            # print(f"[DummyCV2] putText: {text} at {org}")
            pass 

class DummyCamera(AbstractCamera):
    """
    AbstractCameraインターフェースを実装したダミーカメラ。
    実際のハードウェアなしでテストするために使用します。
    """
    def __init__(self, resolution=(640, 480)):
        self._resolution = resolution
        self._is_connected = False
        self._exposure = 10.0  # ms
        print("[DummyCamera] Initialized.")

    def connect(self) -> None:
        if self._is_connected:
            print("[DummyCamera] Already connected.")
            return
            
        print("[DummyCamera] Connecting...")
        time.sleep(0.5) # 接続のフリ
        self._is_connected = True
        print("[DummyCamera] Connected.")

    def disconnect(self) -> None:
        if not self._is_connected:
            print("[DummyCamera] Already disconnected.")
            return
            
        print("[DummyCamera] Disconnecting...")
        time.sleep(0.1)
        self._is_connected = False
        print("[DummyCamera] Disconnected.")

    def get_frame(self) -> np.ndarray:
        """
        (修正) ダミーのフレーム（3チャンネル BGR ノイズ画像）を生成して返す。
        """
        if not self._is_connected:
            raise CameraConnectionError("[DummyCamera] カメラが接続されていません。")

        # 解像度 (height, width) を指定
        height, width = self._resolution[1], self._resolution[0]
        
        # (修正) BGRの3チャンネルカラー画像を生成
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        # 画像中央に時刻（ミリ秒）を描画して、画像が更新されていることを示す
        timestamp = f"{time.time() * 1000:.0f}"
        cv2.putText(frame, timestamp, (50, height // 2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame

    def set_exposure(self, exposure_ms: float) -> None:
        if not self._is_connected:
            raise CameraConnectionError("Dummy camera is not connected.")
            
        self._exposure = exposure_ms
        print(f"[DummyCamera] Exposure set to {exposure_ms} ms.")

    def get_exposure(self) -> float:
        if not self._is_connected:
            raise CameraConnectionError("Dummy camera is not connected.")
            
        print(f"[DummyCamera] Getting exposure: {self._exposure} ms.")
        return self._exposure
    
    def is_connected(self) -> bool:
        return self._is_connected