from ..drivers.stage.abstract_stage import AbstractStage
from ..drivers.stage.dummy_stage import DummyStage
from ..drivers.stage.prior_sdk import PriorSdk
from ..core.exceptions import StageError, StageConnectionError, ValueError

class StageControl:
    """
    アプリケーション側（GUIやWorkflow）へのステージ機能の統一窓口（ファサード）。
    """

    def __init__(self, driver_type: str = "dummy", **kwargs):
        # ドライバの初期化
        print(f"[StageControl] Initializing with driver: {driver_type}")
        self.driver: AbstractStage | None = None

        try:
            if driver_type == "dummy":
                self.driver = DummyStage()
            elif driver_type == "prior":
                com_port = kwargs.get("com_port_str")
                if not com_port:
                    raise ValueError("'com_port_str' がkwargsに必要です。")
                dll_path = kwargs.get("dll_path", "PriorScientificSDK.dll")
                self.driver = PriorSdk(com_port_str=com_port, dll_path=dll_path)
            else:
                raise ValueError(f"不明なステージドライバタイプです: {driver_type}")

        except (ValueError, ImportError) as e:
            # プログラマの指定ミスや環境のセットアップミスはそのまま送出
            raise e
        except Exception as e:
            # それ以外のSDK初期化時エラーは StageConnectionError でラップ
            print(f"[StageControl] ドライバ {driver_type} の初期化に失敗しました: {e}")
            raise StageConnectionError(f"ドライバ {driver_type} の初期化に失敗: {e}")

        if self.driver is None:
             raise StageError("ドライバのインスタンス化に失敗しました。")

    def connect(self) -> None:
        if not self.driver:
            raise StageError("ドライバが初期化されていません。")
        self.driver.connect()

    def disconnect(self) -> None:
        if self.driver and self.driver.is_connected():
            self.driver.disconnect()

    def move_abs(self, x: float, y: float) -> None:
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        self.driver.move_abs(x, y)

    def move_rel(self, dx: float, dy: float) -> None:
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        self.driver.move_rel(dx, dy)

    def get_position(self) -> tuple[float, float]:
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        return self.driver.get_position()

    def set_origin(self) -> None:
        if not self.driver or not self.driver.is_connected():
            raise StageError("ステージが接続されていません。")
        self.driver.set_origin()

    def is_moving(self) -> bool:
        if not self.driver or not self.driver.is_connected():
            return False
        return self.driver.is_moving()

    def wait_for_move(self) -> None:
        if not self.driver or not self.driver.is_connected():
            return
        self.driver.wait_for_move()

    def is_connected(self) -> bool:
        if not self.driver:
            return False
        return self.driver.is_connected()