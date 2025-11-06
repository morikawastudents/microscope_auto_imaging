from ..drivers.stage.abstract_stage import AbstractStage
from ..drivers.stage.dummy_stage import DummyStage
from ..drivers.stage.prior_sdk import PriorSdk
# from ..drivers.stage.maker_c_sdk import MakerCSdk # 将来的に追加
from ..core.exceptions import StageError, StageConnectionError

class StageControl:
    """
    アプリケーション側（GUIやWorkflow）へのステージ機能の統一窓口（ファサード）。
    使用する具体的なドライバ (Dummy, Priorなど) を切り替えます。
    """
    
    def __init__(self, driver_type: str = "dummy", **kwargs):
        """
        指定されたドライバタイプに基づいてステージドライバを初期化します。

        :param driver_type: "dummy", "prior" などのドライバ識別子
        :param **kwargs: 
            "prior" の場合: com_port_str="COM3", dll_path="..." など
        """
        print(f"[StageControl] Initializing with driver: {driver_type}")
        self.driver: AbstractStage | None = None
        
        try:
            if driver_type == "dummy":
                self.driver = DummyStage()
                
            elif driver_type == "prior":
                # PriorSdk が要求する引数を kwargs から取得
                com_port = kwargs.get("com_port_str")
                if not com_port:
                    raise ValueError("'com_port_str' がkwargsに必要です。")
                
                dll_path = kwargs.get("dll_path", "PriorScientificSDK.dll")
                
                self.driver = PriorSdk(com_port_str=com_port, dll_path=dll_path)
            
            # elif driver_type == "maker_c":
            #     self.driver = MakerCSdk(...) # 将来的に実装
            else:
                raise ValueError(f"不明なステージドライバタイプです: {driver_type}")
                
        except ImportError as e:
            print(f"[StageControl] ドライバ {driver_type} の依存関係（{e.name}）が見つかりません。")
            raise StageConnectionError(f"ドライバ {driver_type} の依存ライブラリ({e.name})が見つかりません。")
        except Exception as e:
            # PriorSdk() の init 自体でのエラーなど
            print(f"[StageControl] ドライバ {driver_type} の初期化に失敗しました: {e}")
            raise StageConnectionError(f"ドライバ {driver_type} の初期化に失敗: {e}")

        if self.driver is None:
             raise StageError("ドライバのインスタンス化に失敗しました。")

    # --- 以下、AbstractStageのメソッドをドライバに委譲 ---

    def connect(self) -> None:
        """ 選択されたステージドライバを使用して接続します。 """
        if not self.driver:
            raise StageError("ドライバが初期化されていません。")
        
        print(f"[StageControl] Connecting via {self.driver.__class__.__name__}...")
        self.driver.connect() # 失敗した場合は StageConnectionError がスローされる

    def disconnect(self) -> None:
        """ ステージとの接続を切断します。 """
        if self.driver and self.driver.is_connected():
            print(f"[StageControl] Disconnecting from {self.driver.__class__.__name__}...")
            self.driver.disconnect()
        else:
            print("[StageControl] Not connected or driver not initialized.")

    def move_abs(self, x: float, y: float) -> None:
        """ 原点基準の絶対座標 (x, y) に移動します。 """
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        self.driver.move_abs(x, y)

    def move_rel(self, dx: float, dy: float) -> None:
        """ 現在位置から相対座標 (dx, dy) だけ移動します。 """
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        self.driver.move_rel(dx, dy)

    def get_position(self) -> tuple[float, float]:
        """ 原点基準の現在位置 (x, y) を取得します。 """
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        return self.driver.get_position()

    def set_origin(self) -> None:
        """ 現在の座標を原点 (0, 0) として設定します。 """
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        self.driver.set_origin()

    def is_moving(self) -> bool:
        """ ステージが現在移動中か確認します。 """
        if not self.driver or not self.driver.is_connected():
            # 接続されていない場合は「動いていない」
            return False
        return self.driver.is_moving()

    def wait_for_move(self) -> None:
        """ ステージの移動が完了するまで待機します。 """
        if not self.driver or not self.driver.is_connected():
            return
        self.driver.wait_for_move()
        
    def is_connected(self) -> bool:
        """ ステージが現在接続されているか確認します。 """
        if not self.driver:
            return False
        return self.driver.is_connected()