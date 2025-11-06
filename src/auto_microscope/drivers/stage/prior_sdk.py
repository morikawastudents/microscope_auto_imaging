import time
import os # (更新) DLLパス解決のために import
from .abstract_stage import AbstractStage
from .prior_helper import PriorStageHelper # (更新) ローカルのヘルパーをインポート
from ...core.exceptions import StageConnectionError, StageError

class PriorSdk(AbstractStage):
    """
    AbstractStageインターフェースを実装した、
    Prior製ステージ (PriorStageHelper SDK) 用のラッパークラス。
    
    (更新) 単位を mm (AbstractStage) と μm (PriorStageHelper) の間で変換します。
    """
    
    def __init__(self, com_port_str: str, dll_path: str = "PriorScientificSDK.dll"):
        """
        Priorステージドライバを初期化します。
        
        :param com_port_str: "COM3" などのシリアルポート名
        :param dll_path: "PriorScientificSDK.dll" のファイル名 (またはパス)
        """
        print(f"[PriorSdk] Initializing for {com_port_str} (DLL: {dll_path})")
        self.com_port = com_port_str
        
        # --- (更新) DLLパスの解決 ---
        # `dll_path` が絶対パスでない場合、`Prior_driver` ディレクトリにあると仮定してパスを構築
        if not os.path.isabs(dll_path):
            # このファイル (prior_sdk.py) のディレクトリを取得
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # ユーザー指定の `Prior_driver` ディレクトリへのパス
            # (project_structure.md の 'sdk_files_prior' を 'Prior_driver' に読み替え)
            sdk_dir = os.path.join(current_dir, "Prior_driver") 
            self.resolved_dll_path = os.path.join(sdk_dir, dll_path)
        else:
            self.resolved_dll_path = dll_path
        
        print(f"[PriorSdk] Resolved DLL path: {self.resolved_dll_path}")
        # -------------------------
        
        self.helper: PriorStageHelper | None = None
        self._connected = False
        self._moving = False # is_moving() のための内部フラグ

    def connect(self) -> None:
        if self._connected:
            print("[PriorSdk] Already connected.")
            return

        try:
            print(f"[PriorSdk] Connecting to {self.com_port}...")
            # (更新) 解決したDLLパスを使用してヘルパーをインスタンス化
            self.helper = PriorStageHelper(dll_path=self.resolved_dll_path)
            
            # 接続処理 (元の initialize_stage)
            success = self.helper.initialize_stage(self.com_port)
            
            if not success:
                self.helper = None
                raise StageConnectionError(f"Priorステージ ({self.com_port}) の初期化/接続に失敗しました。")
                
            self._connected = True
            print(f"[PriorSdk] Connected to {self.com_port}.")
            
        except ImportError:
             raise StageConnectionError("Prior SDK (PriorScientificSDK) がインポートできませんでした。")
        except Exception as e:
            self.helper = None
            raise StageConnectionError(f"Priorステージ接続中に予期せぬエラー: {e}")

    def disconnect(self) -> None:
        if self.helper and self._connected:
            print(f"[PriorSdk] Disconnecting from {self.com_port}...")
            try:
                self.helper.close()
            except Exception as e:
                print(f"[PriorSdk] クローズ中にエラー: {e}")
            
            self._connected = False
            self.helper = None
            print("[PriorSdk] Disconnected.")
        
        self._connected = False

    def move_abs(self, x: float, y: float) -> None:
        """ (AbstractStage) 原点基準の絶対座標 (mm) に移動します """
        if not self._connected or not self.helper:
            raise StageError("Priorステージに接続されていません。")
            
        # (更新) mm -> μm に変換
        x_microns = x * 1000.0
        y_microns = y * 1000.0
            
        print(f"[PriorSdk] Moving to (mm: {x:.3f}, {y:.3f}) -> (μm: {x_microns:.1f}, {y_microns:.1f})...")
        self._moving = True
        try:
            # (更新) ヘルパーの move_to_position は μm 単位
            self.helper.move_to_position(x_microns, y_microns) 
            # (注: helper.move_to_position は完了待機 (ブロック) 型です)
        except Exception as e:
            self._moving = False
            raise StageError(f"Priorステージ移動エラー: {e}")
        
        self._moving = False
        print(f"[PriorSdk] Move complete.")

    def move_rel(self, dx: float, dy: float) -> None:
        """ (AbstractStage) 現在位置から相対座標 (mm) だけ移動します """
        if not self._connected or not self.helper:
            raise StageError("Priorステージに接続されていません。")
            
        # 1. 現在位置 (mm) を取得
        current_x_mm, current_y_mm = self.get_position()
        
        # 2. 目標座標 (mm) を計算
        target_x_mm = current_x_mm + dx
        target_y_mm = current_y_mm + dy
        
        # 3. 絶対座標 (mm) で移動
        self.move_abs(target_x_mm, target_y_mm)

    def get_position(self) -> tuple[float, float]:
        """ (AbstractStage) 原点基準の現在位置 (x, y) をタプル (mm) で取得します """
        if not self._connected or not self.helper:
            raise StageError("Priorステージに接続されていません。")
            
        try:
            # (更新) ヘルパーは (μm, μm) タプルを返す
            x_microns, y_microns = self.helper.get_position()
            
            # (更新) μm -> mm に変換して返す
            x_mm = x_microns / 1000.0
            y_mm = y_microns / 1000.0
            
            return (x_mm, y_mm)
        except Exception as e:
            raise StageError(f"Priorステージ位置取得エラー: {e}")

    def set_origin(self) -> None:
        """ (AbstractStage) 現在の座標を原点 (0, 0) として設定します """
        if not self._connected or not self.helper:
            raise StageError("Priorステージに接続されていません。")
            
        print("[PriorSdk] Setting current position as origin (0, 0)...")
        try:
            success = self.helper.set_origin_to_current()
            if not success:
                raise StageError("SDKが原点設定に失敗しました。")
            print("[PriorSdk] Origin set.")
        except Exception as e:
            raise StageError(f"Priorステージ原点設定エラー: {e}")

    def is_moving(self) -> bool:
        """ (AbstractStage) ステージが移動中か確認します """
        # (注: helper.move_to_position がブロック型のため、
        #  このフラグは move_abs の実行中のみ True になります)
        return self._moving

    def wait_for_move(self) -> None:
        """ (AbstractStage) 移動完了まで待機します """
        # (注: move_abs が完了待機型の場合、このメソッドは即座にリターンします)
        print("[PriorSdk] Waiting for move... (move_abs is blocking)")
        while self._moving:
             time.sleep(0.01) # (move_abs が非同期の場合はここでポーリング)
        pass 
        
    def is_connected(self) -> bool:
        return self._connected