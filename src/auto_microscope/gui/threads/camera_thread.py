from PySide6.QtCore import QThread, Signal, Slot
from ...devices.camera_controller import CameraControl
from ...core.exceptions import CameraError
from ..utils import np_array_to_qimage # (cv2インポートも含む)

class CameraThread(QThread):
    """
    カメラ映像の取得とピント計算をバックグラウンドで行うスレッド。
    (ユーザーの CameraWorker を QThread + CameraControl を使う形に修正)
    """
    
    # --- シグナル定義 ---
    # メインスレッド (MainWindow, CameraViewWidget) へ通知
    frame_ready = Signal(object) # QImage (object)
    focus_score_ready = Signal(float)
    camera_error = Signal(str)

    def __init__(self, driver_type: str, parent=None):
        super().__init__(parent)
        self.driver_type = driver_type
        self.camera_control: CameraControl | None = None
        self._is_running = False
        self._capture_path: str | None = None # 手動撮影フラグ

    def run(self):
        """ (QThread) スレッドのメインループ """
        self._is_running = True
        
        try:
            # --- 1. スレッド内で CameraControl を初期化・接続 ---
            self.camera_control = CameraControl(driver_type=self.driver_type)
            self.camera_control.connect()
            
        except Exception as e:
            self.camera_error.emit(f"カメラの初期化/接続に失敗: {e}")
            self._is_running = False
            return # スレッド終了

        print("[CameraThread] カメラ接続完了。ストリーミングを開始します。")

        # --- 2. メインループ (フレーム取得) ---
        while self._is_running:
            try:
                frame = self.camera_control.get_frame()
                if frame is None:
                    continue
                
                # ピントスコア計算
                score = self.camera_control.calculate_focus_score(frame)
                self.focus_score_ready.emit(score)
                
                # 手動撮影フラグが立っていたら撮影
                if self._capture_path:
                    self._perform_capture(frame, self._capture_path)
                    self._capture_path = None # フラグを下ろす

                # GUI用に QImage に変換して送信 (重い処理)
                q_image = np_array_to_qimage(frame)
                self.frame_ready.emit(q_image)

                # (重要) CPUを占有しないよう、少し待機する
                self.msleep(10) # 約 100 FPS (処理時間による)

            except CameraError as e:
                # フレーム取得失敗 (タイムアウトなど)
                self.camera_error.emit(f"フレーム取得エラー: {e}")
                self.msleep(100)
            except Exception as e:
                # 予期せぬエラー
                self.camera_error.emit(f"予期せぬスレッドエラー: {e}")
                self._is_running = False # ループを止める

        # --- 3. クリーンアップ ---
        print("[CameraThread] ループ終了。カメラ接続を切断します。")
        if self.camera_control:
            self.camera_control.disconnect()
        print("[CameraThread] スレッド終了。")

    def _perform_capture(self, frame, save_path):
        """ (内部) フレームをファイルに保存する """
        try:
            # (注意) utils の cv2 を使用
            from ..utils import cv2
            cv2.imwrite(save_path, frame)
            # (注) ここから log_message シグナルを送ることもできる
            print(f"[CameraThread] 手動撮影成功: {save_path}")
        except Exception as e:
            self.camera_error.emit(f"手動撮影失敗 ({save_path}): {e}")

    @Slot(str)
    def capture_now(self, save_path: str):
        """ (スロット) MainWindow からの手動撮影要求 """
        # 次のループで撮影を実行するためにパスをセット
        self._capture_path = save_path

    @Slot()
    def stop(self):
        """ (スロット) スレッドを安全に停止する """
        print("[CameraThread] 停止リクエストを受信しました。")
        self._is_running = False