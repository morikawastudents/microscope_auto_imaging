import pytelicam
import numpy as np
import time
from .abstract_camera import AbstractCamera
from ...core.exceptions import CameraConnectionError, CameraError

# (cv2 は画像保存 (imwrite) にのみ使われていたため、
#  get_frame (ndarray) のみを返すこの層では不要になりました)

class TeliCamSdk(AbstractCamera):
    """
    AbstractCameraインターフェースを実装した、
    東芝テリー (Teli) 製カメラ (pytelicam SDK) 用のラッパークラス。
    
    アップロードされた TeliCamHelper を AbstractCamera に適合させたものです。
    """
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cam_system = None
        self.cam_device = None
        self._connected = False # AbstractCamera.is_connected() のためのフラグ
        print(f"[TeliCamSdk] Initialized for camera index {camera_index}.")

    def connect(self) -> None:
        """ (AbstractCamera) カメラの初期化とストリーミング開始 """
        if self._connected:
            print("[TeliCamSdk] Already connected.")
            return

        try:
            print("[TeliCamSdk] pytelicam システムを初期化します...")
            self.cam_system = pytelicam.get_camera_system()
            
            cam_num = self.cam_system.get_num_of_cameras()
            if cam_num == 0:
                print(f"[TeliCamSdk] エラー: TeliCamカメラが {cam_num} 台見つかりました。")
                raise CameraConnectionError("TeliCamが見つかりません。")

            print(f"[TeliCamSdk] {cam_num} 台の TeliCam カメラを検出しました。")
            
            self.cam_device = self.cam_system.create_device_object(self.camera_index)
            if self.cam_device is None:
                 print(f"[TeliCamSdk] エラー: カメラ {self.camera_index} のデバイスオブジェクトを作成できません。")
                 raise CameraConnectionError(f"TeliCam (Index {self.camera_index}) の作成に失敗。")
                 
            self.cam_device.open()
            self.cam_device.cam_stream.open()
            
            # 連続取得モードでストリーミング開始
            self.cam_device.cam_stream.start(pytelicam.CameraAcquisitionMode.Continuous)
            print(f"[TeliCamSdk] カメラ {self.camera_index} のストリーミングを開始しました。")
            self._connected = True

        except pytelicam.PytelicamError as e:
            print(f"[TeliCamSdk] Pytelicam SDK 初期化エラー: {e.message} (Status: {e.status})")
            # 接続失敗時にはリソースをクリーンアップ
            self.disconnect() 
            raise CameraConnectionError(f"Pytelicam SDK エラー: {e.message}")
        except Exception as e:
            print(f"[TeliCamSdk] 予期せぬ初期化エラー: {e}")
            self.disconnect()
            raise CameraConnectionError(f"予期せぬ初期化エラー: {e}")

    def get_frame(self) -> np.ndarray:
        """
        (AbstractCamera) カメラから次のフレームを取得し、Numpy配列 (BGR) として返す。
        """
        if not self._connected:
            raise CameraError("TeliCamに接続されていません。")

        try:
            # タイムアウトは2000ms (2秒) に設定
            with self.cam_device.cam_stream.get_next_image(timeout=2000) as image_data:
                
                if image_data.status == pytelicam.CamApiStatus.Success:
                    # BU030Cはカラーカメラのため Bgr24 を指定 (元のコードコメントより)
                    frame = image_data.get_ndarray(pytelicam.OutputImageType.Bgr24)
                    return frame
                
                elif image_data.status == pytelicam.CamApiStatus.Timeout:
                    print("[TeliCamSdk] カメラ取得タイムアウト。")
                    # タイムアウトはリカバリ可能かもしれないので、空の配列を返すか例外を送出
                    raise CameraError("TeliCamフレーム取得タイムアウト。")
                else:
                    print(f"[TeliCamSdk] カメラエラー: {image_data.status}")
                    time.sleep(0.1) # エラー時は少し待つ
                    raise CameraError(f"TeliCamエラー: {image_data.status}")

        except pytelicam.PytelicamError as e:
            print(f"[TeliCamSdk] Pytelicam SDK フレーム取得エラー: {e.message} (Status: {e.status})")
            # ストリーミングが停止している可能性があるため、切断状態とみなす
            self._connected = False 
            raise CameraError(f"Pytelicam SDK フレーム取得エラー: {e.message}")
        except Exception as e:
            print(f"[TeliCamSdk] 予期せぬフレーム取得エラー: {e}")
            self._connected = False
            raise CameraError(f"予期せぬフレーム取得エラー: {e}")

    def disconnect(self) -> None:
        """ (AbstractCamera) カメラのリソースを解放する """
        print("[TeliCamSdk] カメラリソースの解放処理を開始します。")
        self._connected = False
        try:
            # cam_device や cam_system が None の場合も安全に実行
            if self.cam_device:
                if self.cam_device.cam_stream.is_open:
                    self.cam_device.cam_stream.stop()
                    self.cam_device.cam_stream.close()
                if self.cam_device.is_open:
                    self.cam_device.close()
                print("[TeliCamSdk] カメラデバイスをクローズしました。")
            
            self.cam_device = None
                
            if self.cam_system:
                self.cam_system.terminate()
                print("[TeliCamSdk] pytelicam システムを終了しました。")
            
            self.cam_system = None
                
        except pytelicam.PytelicamError as e:
            print(f"[TeliCamSdk] Pytelicam SDK クローズエラー: {e.message} (Status: {e.status})")
        except Exception as e:
            print(f"[TeliCamSdk] 予期せぬクローズエラー: {e}")

    def set_exposure(self, exposure_ms: float) -> None:
        """ (AbstractCamera) 露光時間を設定します (ミリ秒)。"""
        if not self._connected:
            raise CameraError("TeliCamに接続されていません。")
        
        # (注: 元のコードには露光設定がありませんでした)
        # pytelicam SDKに露光時間設定の機能がある場合は、ここで実装します。
        # 例: self.cam_device.set_parameter("ExposureTime", exposure_ms * 1000) # (SDKの仕様によります)
        print(f"[TeliCamSdk] (Warning) set_exposure({exposure_ms}ms) は実装されていません。")
        pass # 未実装

    def get_exposure(self) -> float:
        """ (AbstractCamera) 現在の露光時間 (ミリ秒) を取得します。"""
        if not self._connected:
            raise CameraError("TeliCamに接続されていません。")
        
        # (注: 元のコードには露光取得がありませんでした)
        # 例: exposure_us = self.cam_device.get_parameter("ExposureTime")
        #     return exposure_us / 1000.0
        print("[TeliCamSdk] (Warning) get_exposure() は実装されていません。ダミー値 10.0 を返します。")
        return 10.0 # ダミー値

    def is_connected(self) -> bool:
        """ (AbstractCamera) カメラが現在接続されているか確認します。"""
        # (元の _is_initialized フラグを _connected にリネームしました)
        return self._connected