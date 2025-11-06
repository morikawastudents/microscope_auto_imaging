from ctypes import WinDLL, create_string_buffer, c_int
import os
import sys
import time
import re # COMポート名の数値抽出用にインポート
from typing import Tuple

class PriorStageHelper:
    """
    Prior Scientific SDK (DLL) の具体的な処理をカプセル化するヘルパークラス。
    prior_sdk.py (PriorSdkクラス) がこのクラスのインターフェースのみを使用する。
    """
    
    # (更新) デフォルトのパスを削除し、コンストラクタで必須引数として受け取る
    def __init__(self, dll_path: str):
        """
        :param dll_path: "PriorScientificSDK.dll" への完全なパス
        """
        self.sessionID = -1
        self.sdk = None
        self.rx = create_string_buffer(1000) # 受信バッファ
        self.dll_path = dll_path
        self._is_initialized = False

    def initialize_stage(self, com_port_str: str) -> bool: # 引数を int から str (例: "COM3") に変更
        """ DLLをロードし、ステージコントローラーに接続する """
        try:
            # (更新) 渡されたdll_pathをチェックする
            if not os.path.exists(self.dll_path):
                print(f"エラー: DLLが見つかりません: {self.dll_path}")
                return False

            print(f"{self.dll_path} をロードします...")
            self.sdk = WinDLL(self.dll_path)
            
            # SDK自体の初期化
            ret = self.sdk.PriorScientificSDK_Initialise()
            if ret:
                print(f"SDK初期化エラー: {ret}")
                return False

            # セッションIDの取得
            self.sessionID = self.sdk.PriorScientificSDK_OpenNewSession()
            if self.sessionID < 0:
                print(f"セッションID取得エラー: {self.sessionID}")
                return False

            print(f"セッションID = {self.sessionID} で接続します...")

            # --- COMポート名の処理 (修正) ---
            # "COM3" のような文字列から数値 "3" を抽出
            match = re.search(r'(\d+)$', com_port_str)
            if not match:
                print(f"エラー: 無効なCOMポート名です: {com_port_str}")
                return False
            com_port_number = match.group(1)
            # -------------------------------
            
            # COMポート経由でコントローラに接続
            # サンプルコードの cmd("controller.connect 3") に相当
            ret, response = self._send_command(f"controller.connect {com_port_number}")
            
            if ret != 0 or "OK" not in response:
                print(f"ステージコントローラへの接続失敗 ({com_port_str}): {response}")
                return False
                
            print(f"ステージコントローラ ({com_port_str}) に接続しました。")
            self._is_initialized = True
            return True

        except Exception as e:
            print(f"ステージ初期化中に予期せぬエラー: {e}")
            self._is_initialized = False
            return False

    def _send_command(self, command_str: str) -> Tuple[int, str]:
        """ SDKにテキストコマンドを送信し、結果タプル (ret_code, response_str) を返す """
        if not self.sdk or self.sessionID < 0:
            return -1, "SDK not initialized"
            
        # print(f"[CMD] -> {command_str}") # デバッグ用
        
        # バッファをクリア
        self.rx.value = b""
        
        # コマンドをバイト文字列にエンコードして送信
        cmd_bytes = create_string_buffer(command_str.encode('utf-8'))
        
        ret = self.sdk.PriorScientificSDK_cmd(
            c_int(self.sessionID), 
            cmd_bytes, 
            self.rx
        )
        
        response_str = self.rx.value.decode('utf-8')
        # print(f"[RES] <- {ret}, {response_str}") # デバッグ用
        
        return ret, response_str

    def close(self):
        """ コントローラから切断し、セッションを閉じる """
        print("ステージコントローラの切断処理...")
        if self._is_initialized:
            self._send_command("controller.disconnect")
        
        if self.sdk and self.sessionID >= 0:
            self.sdk.PriorScientificSDK_CloseSession(c_int(self.sessionID))
            print("SDKセッションをクローズしました。")
            
        self._is_initialized = False
        self.sdk = None

    def set_origin_to_current(self):
        """ 現在位置を (0, 0) に設定する """
        ret, response = self._send_command("controller.stage.position.set 0 0")
        return ret == 0

    def get_position(self) -> Tuple[float, float]:
        """ 現在の位置 (x, y) を取得する (単位: microns) """
        ret, response = self._send_command("controller.stage.position.get")
        if ret == 0 and "OK" in response:
            try:
                # 応答 "OK,1234.0,5678.0" から数値を抽出
                parts = response.split(',')
                # (更新) Prior SDK はマイクロメートル単位
                x_microns = float(parts[1])
                y_microns = float(parts[2])
                return x_microns, y_microns
            except (IndexError, ValueError) as e:
                print(f"位置データのパース失敗: {response} ({e})")
                return 0.0, 0.0
        return 0.0, 0.0

    def move_to_position(self, x: float, y: float):
        """ 指定された (x, y) 座標に移動する (単位: microns) """
        # 移動開始コマンド
        ret, response = self._send_command(f"controller.stage.goto-position {x} {y}")
        
        if ret != 0:
            print(f"移動開始エラー: {response}")
            return
        
        # 移動完了まで待機 (ポーリング)
        # サンプルコードの 'controller.stage.busy.get' に相当
        while self._is_initialized:
            time.sleep(0.1) # 100ms待機
            ret, busy_response = self._send_command("controller.stage.busy.get")
            
            if ret == 0 and "OK" in busy_response:
                try:
                    # 応答 "OK,1" (Busy) または "OK,0" (Ready)
                    status = int(busy_response.split(',')[1])
                    if status == 0:
                        # print("移動完了。")
                        break # ループを抜ける
                except (IndexError, ValueError):
                    print(f"Busyステータス取得失敗: {busy_response}")
                    break # エラー時はループを抜ける
            else:
                print("Busyステータス取得失敗。")
                break # エラー時はループを抜ける

    def stop_move(self):
        """ ステージの移動を緊急停止する """
        # サンプルコードの 'controller.stage.move-at-velocity 0 0' (速度0) に相当
        self._send_command("controller.stage.move-at-velocity 0 0")