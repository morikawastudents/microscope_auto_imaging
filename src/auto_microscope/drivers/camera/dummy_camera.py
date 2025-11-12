import time
import numpy as np
import os

from ...core.exceptions import CameraConnectionError 
from .abstract_camera import AbstractCamera

try:
    import cv2
except ImportError:
    print("CRITICAL WARNING: OpenCV (cv2) が見つかりません。")
    print("画像ファイルの読み込みとテキスト描画ができません。")
    class cv2:
        FONT_HERSHEY_SIMPLEX = 0 # ダミーの値
        
        @staticmethod
        def putText(img, text, org, fontFace, fontScale, color, thickness): pass
        @staticmethod
        def imread(path): return None # 読み込み失敗をシミュレート
        @staticmethod
        def resize(img, dsize): return img

class DummyCamera(AbstractCamera):
    # ダミーカメラドライバの実装
    def __init__(self, resolution=(640, 480), image_filename="dummy_image.jpg"):
        self._resolution = resolution
        self._image_filename = image_filename # 読み込む画像ファイル名
        self._dummy_frame = None             # 読み込んだ画像を保持する変数
        self._is_connected = False
        self._exposure = 10.0  # ms
        print(f"[DummyCamera] Initialized. Target image: {image_filename}")

    def connect(self) -> None:
        if self._is_connected:
            print("[DummyCamera] Already connected.")
            return
            
        print("[DummyCamera] Connecting...")
        
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, self._image_filename)
            
            print(f"[DummyCamera] Loading image from: {image_path}")
            
            image = cv2.imread(image_path)
            
            if image is None:
                raise FileNotFoundError(f"ダミー画像ファイルが見つかりません: {image_path}")
                
            self._dummy_frame = cv2.resize(image, self._resolution)
            
            self._is_connected = True
            print("[DummyCamera] Connected and image loaded.")
            
        except Exception as e:
            self._is_connected = False
            # 画像読み込み失敗時には接続失敗として扱う
            raise CameraConnectionError(f"[DummyCamera] Failed to load dummy image: {e}") 

    def disconnect(self) -> None:
        if not self._is_connected:
            print("[DummyCamera] Already disconnected.")
            return
            
        print("[DummyCamera] Disconnecting...")
        self._dummy_frame = None #　読み込んだ画像を解放
        self._is_connected = False
        print("[DummyCamera] Disconnected.")

    def get_frame(self) -> np.ndarray:
        # ロードしたダミー画像をフレームとして返す。
        if not self._is_connected or self._dummy_frame is None:
            raise CameraConnectionError("[DummyCamera] カメラが接続されていないか、画像がロードされていません。")

        # (変更) グラデーションの代わりに、ロードした画像のコピーを返す
        frame = self._dummy_frame.copy()
        
        # 画像左上に時刻（ミリ秒）を描画
        timestamp = f"{time.time() * 1000:.0f}"
        cv2.putText(frame, timestamp, (50, 50), # 座標を (50, 50) に変更
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