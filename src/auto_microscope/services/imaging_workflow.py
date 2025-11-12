import time
from ..devices.camera_controller import CameraControl
from ..devices.stage_controller import StageControl
from ..services.config_service import ConfigManager
from ..core.exceptions import AutoMicroscopeError

class ImagingWorkflow:
    """
    (Ver2 修正)
    自動撮影に必要なコンポーネント (Camera, Stage, Config) を保持し、
    個別の操作 (接続, 原点設定, 単一移動) を実行するサービス。
    """
    def __init__(self, camera_driver: str, stage_driver: str, **stage_kwargs):
        """
        :param camera_driver: "dummy" や "telicam" など
        :param stage_driver: "dummy" や "prior" など
        :param **stage_kwargs: ステージ初期化に必要な引数 (例: com_port_str="COM9")
        """
        # (注) カメラの初期化/接続は CameraThread が行うため、
        # Workflow は Config と Stage の管理に集中する。
        # self.camera = CameraControl(driver_type=camera_driver)
        self.stage = StageControl(driver_type=stage_driver, **stage_kwargs)
        self.config = ConfigManager()
        
        self.targets = [] # 撮影対象リスト
        self._is_initialized = False # (ステージが接続されたか)

    def load_config(self, layout_path: str, map_path: str):
        """
        設定ファイルを読み込み、撮影対象リストを生成する。
        """
        print("[Workflow] 設定ファイルを読み込んでいます...")
        self.config.load_layout(layout_path)
        self.config.load_map(map_path)
        
        self.targets = self.config.get_target_positions()
        if not self.targets:
            raise AutoMicroscopeError("設定ファイルから撮影対象が見つかりませんでした。")
        
        print(f"[Workflow] {len(self.targets)} 件の撮影対象をロードしました。")

    def connect_stage(self):
        """ ステージに接続する """
        if self._is_initialized:
            return
        print("[Workflow] ステージに接続しています...")
        self.stage.connect()
        self._is_initialized = True
        print("[Workflow] ステージ接続完了。")

    def disconnect_stage(self):
        """ ステージを切断する """
        if self.stage and self.stage.is_connected():
            print("[Workflow] ステージを切断しています...")
            self.stage.disconnect()
        self._is_initialized = False

    def set_stage_origin(self):
        """
        ステージの現在位置を原点として設定する。
        """
        if not self._is_initialized:
            raise AutoMicroscopeError("システムが初期化されていません。")
        
        print("[Workflow] ステージの現在位置を原点 (0, 0) として設定します...")
        self.stage.set_origin()
        pos = self.stage.get_position()
        print(f"[Workflow] 原点設定完了。現在位置: {pos}")

    def get_targets(self) -> list[dict]:
        """
        読み込まれた撮影対象のリストを返す。
        """
        if not self.targets:
            # まだロードされていない場合はロードを試みる (パスが ConfigManager にあれば)
            # (GUI側でロードするので、通常はここを通らない)
            raise AutoMicroscopeError("撮影対象リストがロードされていません。")
        return self.targets

    def move_to_target(self, target: dict):
        """
        指定されたターゲット辞書（get_targets() の要素）の位置に移動する。
        """
        if not self._is_initialized:
            raise AutoMicroscopeError("システムが初期化されていません。")
            
        target_id = target['id']
        x = target['x']
        y = target['y']
        
        # (単位は mm と仮定)
        
        print(f"[Workflow] ターゲット ID: {target_id} (x={x} mm, y={y} mm) へ移動します...")
        self.stage.move_abs(x, y)
        self.stage.wait_for_move() 
        
        pos = self.stage.get_position()
        print(f"[Workflow] 移動完了。現在位置: {pos}")