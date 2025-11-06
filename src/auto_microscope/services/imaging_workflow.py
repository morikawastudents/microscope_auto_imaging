import time
from ..devices.camera_controller import CameraControl
from ..devices.stage_controller import StageControl
from ..services.config_service import ConfigManager
from ..core.exceptions import AutoMicroscopeError

class ImagingWorkflow:
    """
    自動撮影の全シーケンス（接続、原点設定、移動、切断）を管理するクラス。
    CameraControl, StageControl, ConfigManager を組み合わせて使用する。
    """
    def __init__(self, camera_driver: str, stage_driver: str, **stage_kwargs):
        """
        :param camera_driver: "dummy" や "telicam" など
        :param stage_driver: "dummy" や "prior" など
        :param **stage_kwargs: ステージ初期化に必要な引数 (例: com_port_str="COM9")
        """
        self.camera = CameraControl(driver_type=camera_driver)
        self.stage = StageControl(driver_type=stage_driver, **stage_kwargs)
        self.config = ConfigManager()
        
        self.targets = [] # 撮影対象リスト
        self._is_initialized = False

    def initialize_systems(self, layout_path: str, map_path: str):
        """
        設定ファイルを読み込み、両方のデバイスに接続する。
        """
        if self._is_initialized:
            print("[Workflow] すでに初期化されています。")
            return
            
        print("[Workflow] 設定ファイルを読み込んでいます...")
        self.config.load_layout(layout_path)
        self.config.load_map(map_path)
        
        # スキップ対象を除いた、撮影対象のリストを取得
        self.targets = self.config.get_target_positions()
        if not self.targets:
            raise AutoMicroscopeError("設定ファイルから撮影対象が見つかりませんでした。")
        
        print(f"[Workflow] {len(self.targets)} 件の撮影対象をロードしました。")
        
        print("[Workflow] カメラに接続しています...")
        self.camera.connect()
        
        print("[Workflow] ステージに接続しています...")
        self.stage.connect()
        
        self._is_initialized = True
        print("[Workflow] 初期化が完了しました。")

    def shutdown_systems(self):
        """
        両方のデバイスを切断する。
        """
        print("[Workflow] シャットダウンしています...")
        if self.camera:
            self.camera.disconnect()
        if self.stage:
            self.stage.disconnect()
        self._is_initialized = False
        print("[Workflow] シャットダウン完了。")

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
        
        # PriorSDK は mm 単位、Config の JSON も mm 単位と仮定
        # (もし Config が μm なら、ここで / 1000.0 する)
        
        print(f"[Workflow] ターゲット ID: {target_id} (x={x} mm, y={y} mm) へ移動します...")
        self.stage.move_abs(x, y)
        self.stage.wait_for_move() # (PriorSDKはブロック型だが念のため)
        
        pos = self.stage.get_position()
        print(f"[Workflow] 移動完了。現在位置: {pos}")
        
        # (ver1 では手動撮影)
        # (ver2 ではここでピントスコアをチェックし、自動撮影)

    def run_ver1_manual_workflow(self):
        """
        (手動テスト用)
        原点を設定した後、Enterキーを押すごとに次のターゲットへ移動する。
        """
        if not self._is_initialized:
            raise AutoMicroscopeError("システムが初期化されていません。")
            
        print("\n--- 手動撮影ワークフロー (ver1) ---")
        self.set_stage_origin()
        
        targets = self.get_targets()
        
        for i, target in enumerate(targets):
            print("\n" + "="*30)
            print(f"ターゲット {i+1}/{len(targets)}: ID {target['id']} (Type: {target['type']})")
            print(f"座標: (x={target['x']:.3f} mm, y={target['y']:.3f} mm)")
            
            key = input("この位置へ移動しますか？ (Enter=移動, s=スキップ, q=中断): ")
            
            if key.lower() == 'q':
                print("[Workflow] ユーザーによって中断されました。")
                break
            elif key.lower() == 's':
                print(f"[Workflow] ID {target['id']} をスキップします。")
                continue
            
            self.move_to_target(target)
            
            # (ver1) 手動撮影フェーズ
            key_shot = input("  ピントを合わせてください。撮影したら 's' を、スキップなら Enter を押してください: ")
            
            if key_shot.lower() == 's':
                # (TODO: ver1)
                # frame = self.camera.get_frame()
                # cv2.imwrite(f"output/{target['id']}.png", frame)
                # self.config.export_map_to_csv("output/results.csv")
                print(f"  ID {target['id']} を撮影しました (仮)。")

        print("\n--- ワークフロー完了 ---")