import numpy as np
import time
from .abstract_camera import AbstractCamera
from ...core.exceptions import CameraConnectionError

class DummyCamera(AbstractCamera):
    """
    AbstractCameraインターフェースを実装したダミーカメラ。
    実際のハードウェアなしでテストするために使用します。
    """
    def __init__(self):
        self._connected = False
        self._exposure = 10.0  # ms
        self._image_width = 640
        self._image_height = 480
        print("[DummyCamera] Initialized.")

    def connect(self) -> None:
        if self._connected:
            print("[DummyCamera] Already connected.")
            return
            
        print("[DummyCamera] Connecting...")
        time.sleep(0.5) # 接続のフリ
        # if connection_failed:
        #    raise CameraConnectionError("Failed to connect to dummy camera.")
        self._connected = True
        print("[DummyCamera] Connected.")

    def disconnect(self) -> None:
        if not self._connected:
            print("[DummyCamera] Already disconnected.")
            return
            
        print("[DummyCamera] Disconnecting...")
        time.sleep(0.1)
        self._connected = False
        print("[DummyCamera] Disconnected.")

    def get_frame(self) -> np.ndarray:
        if not self._connected:
            raise CameraConnectionError("Dummy camera is not connected.")
            
        # ダミー画像 (グレースケールのノイズ) を生成
        noise = np.random.randint(0, 255, 
                                  (self._image_height, self._image_width), 
                                  dtype=np.uint8)
        
        # 現在時刻を描画 (動作確認のため)
        # (OpenCVがインストールされていれば、よりリッチな描画も可能)
        # cv2.putText(noise, f"Dummy Frame {time.time():.2f}", (10, 30), 
        #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255), 2)
                      
        return noise

    def set_exposure(self, exposure_ms: float) -> None:
        if not self._connected:
            raise CameraConnectionError("Dummy camera is not connected.")
            
        self._exposure = exposure_ms
        print(f"[DummyCamera] Exposure set to {exposure_ms} ms.")

    def get_exposure(self) -> float:
        if not self._connected:
            raise CameraConnectionError("Dummy camera is not connected.")
            
        print(f"[DummyCamera] Getting exposure: {self._exposure} ms.")
        return self._exposure
    
    def is_connected(self) -> bool:
        return self._connected