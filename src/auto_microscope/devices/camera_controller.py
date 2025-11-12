import numpy as np
from ..drivers.camera.abstract_camera import AbstractCamera
from ..drivers.camera.dummy_camera import DummyCamera
from ..drivers.camera.telicam_sdk import TeliCamSdk
from ..core.exceptions import CameraError, CameraConnectionError
from ..devices.analysis.focus_analyzer import FocusAnalyzer

class CameraControl:
    def __init__(self, driver_type: str = "dummy"): 
        # ドライバの初期化
        print(f"[CameraControl] Initializing with driver: {driver_type}")
        self.driver: AbstractCamera | None = None

        try:
            if driver_type == "dummy":
                self.driver = DummyCamera()
            elif driver_type == "telicam":
                self.driver = TeliCamSdk()
            else:
                raise ValueError(f"不明なカメラドライバタイプです: {driver_type}")

        except (ValueError, ImportError) as e:
            # 既知の初期化エラーはそのまま伝播
            raise e
        except Exception as e:
            # その他の例外はカメラ接続エラーとして扱う
            print(f"[CameraControl] ドライバ {driver_type} の初期化に失敗しました: {e}")
            raise CameraConnectionError(f"ドライバ {driver_type} の初期化に失敗: {e}")

        if self.driver is None:
             raise CameraError("ドライバのインスタンス化に失敗しました。")

    def connect(self) -> None:
        # カメラへの接続
        if not self.driver:
            raise CameraError("ドライバが初期化されていません。")
        self.driver.connect()

    def disconnect(self) -> None:
        if self.driver and self.driver.is_connected():
            self.driver.disconnect()

    def get_frame(self) -> np.ndarray:
        if not self.driver or not self.driver.is_connected():
            raise CameraError("カメラが接続されていません。")
        return self.driver.get_frame()

    def set_exposure(self, exposure_ms: float) -> None:
        if not self.driver or not self.driver.is_connected():
            raise CameraError("カメラが接続されていません。")
        self.driver.set_exposure(exposure_ms)

    def get_exposure(self) -> float:
        if not self.driver or not self.driver.is_connected():
            raise CameraError("カメラが接続されていません。")
        return self.driver.get_exposure()

    def is_connected(self) -> bool:
        if not self.driver:
            return False
        return self.driver.is_connected()

    def calculate_focus_score(self, frame: np.ndarray) -> float:
        return FocusAnalyzer.calculate_laplacian_variance(frame)