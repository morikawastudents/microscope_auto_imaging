import time
import math
from .abstract_stage import AbstractStage
from ...core.exceptions import StageConnectionError

class DummyStage(AbstractStage):
    """
    AbstractStageインターフェースを実装したダミーステージ。
    (更新: アップロードされた DummyStageController の
     原点オフセットロジックを採用し、より現実に近いシミュレーションを行います)
    """
    def __init__(self):
        self._connected = False
        # (更新) _x, _y はステージの「内部」絶対座標とする
        self._x = 0.0 
        self._y = 0.0
        # (更新) _origin_x, _origin_y はユーザーが設定した原点の「内部」座標
        self._origin_x = 0.0 
        self._origin_y = 0.0
        self._moving = False
        print("[DummyStage] Initialized (Offset-based).")

    def connect(self) -> None:
        if self._connected:
            print("[DummyStage] Already connected.")
            return

        print("[DummyStage] Connecting...")
        time.sleep(0.5) # 接続のフリ
        self._connected = True
        print("[DummyStage] Connected.")

    def disconnect(self) -> None:
        if not self._connected:
            print("[DummyStage] Already disconnected.")
            return
            
        print("[DummyStage] Disconnecting...")
        time.sleep(0.1)
        self._connected = False
        print("[DummyStage] Disconnected.")

    def move_abs(self, x: float, y: float) -> None:
        """ (更新) ユーザー指定の座標 (原点基準) に移動 """
        if not self._connected:
            raise StageConnectionError("Dummy stage is not connected.")
        
        # (更新) 原点を考慮した「内部」絶対座標を計算
        target_abs_x = self._origin_x + x
        target_abs_y = self._origin_y + y
            
        print(f"[DummyStage] Moving from (App: {self.get_position()}) to (App: {x:.2f}, {y:.2f})...")
        print(f"             (Internal: ({self._x:.2f}, {self._y:.2f}) to ({target_abs_x:.2f}, {target_abs_y:.2f}))")
        self._moving = True
        
        # 移動時間のシミュレーション (距離に応じて)
        distance = ((self._x - target_abs_x)**2 + (self._y - target_abs_y)**2)**0.5
        move_time = max(0.1, distance / 10.0) # 10mm/secと仮定
        time.sleep(move_time) 
        
        # (更新) 内部座標を更新
        self._x = target_abs_x
        self._y = target_abs_y
        
        self._moving = False
        print(f"[DummyStage] Move complete. App Position: ({self.get_position()})")

    def move_rel(self, dx: float, dy: float) -> None:
        if not self._connected:
            raise StageConnectionError("Dummy stage is not connected.")
            
        # (更新) 原点基準の現在位置を取得
        current_x, current_y = self.get_position()
        
        target_x = current_x + dx
        target_y = current_y + dy
        self.move_abs(target_x, target_y) # move_abs (原点基準) を呼び出す

    def get_position(self) -> tuple[float, float]:
        """ (更新) 原点基準の現在位置を返す """
        if not self._connected:
            raise StageConnectionError("Dummy stage is not connected.")
            
        # (更新) 内部座標 - 原点オフセット = アプリケーション座標
        app_x = self._x - self._origin_x
        app_y = self._y - self._origin_y
        
        # print(f"[DummyStage] Getting position: ({app_x:.2f}, {app_y:.2f})")
        return (app_x, app_y)

    def set_origin(self) -> None:
        """ (更新) 現在の「内部」座標を、新しい原点オフセットとして設定 """
        if not self._connected:
            raise StageConnectionError("Dummy stage is not connected.")
            
        # (更新)
        self._origin_x = self._x
        self._origin_y = self._y
        print(f"[DummyStage] Setting current position as origin (0, 0).")
        print(f"             (Internal Origin offset is now: {self._origin_x:.2f}, {self._origin_y:.2f})")

    def is_moving(self) -> bool:
        return self._moving

    def wait_for_move(self) -> None:
        print("[DummyStage] Waiting for move... (already complete in this dummy)")
        # ダミー実装では move_abs が完了待機型なので、即座にリターン
        pass
        
    def is_connected(self) -> bool:
        return self._connected