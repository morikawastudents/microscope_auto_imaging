from ctypes import WinDLL, create_string_buffer, c_int
import os
import sys
import time
import re # COMポート名の数値抽出用にインポート
from typing import Tuple # 型ヒント (Tuple) のためにインポート

class PriorStageHelper:
    """
    (修正) X軸の座標系の反転を、このヘルパー層で吸収します。
    """
    
    def __init__(self, dll_path: str):
        self.sessionID = -1
        self.sdk = None
        self.rx = create_string_buffer(1000) # 受信バッファ
        self.dll_path = dll_path
        self._is_initialized = False

    def initialize_stage(self, com_port_str: str) -> bool:
        """ DLLをロードし、ステージコントローラーに接続する """
        
        original_cwd = os.getcwd() 
        dll_full_path = os.path.abspath(self.dll_path)
        dll_dir = os.path.dirname(dll_full_path)
        
        try:
            if not os.path.exists(dll_full_path):
                print(f"エラー: DLLが見つかりません: {dll_full_path}")
                return False

            print(f"DLLディレクトリに一時的に移動: {dll_dir}")
            os.chdir(dll_dir) 

            ftd_dll_path = os.path.join(dll_dir, "ftd2xx.dll")
            if os.path.exists(ftd_dll_path):
                try:
                    WinDLL(ftd_dll_path)
                    print(f"{ftd_dll_path} をプリロードしました。")
                except Exception as e:
                    print(f"警告: {ftd_dll_path} のロードに失敗: {e}")
            
            print(f"{dll_full_path} をロードします...")
            self.sdk = WinDLL(dll_full_path)
            
            ret = self.sdk.PriorScientificSDK_Initialise()
            if ret:
                print(f"SDK初期化エラー: {ret}")
                return False

            self.sessionID = self.sdk.PriorScientificSDK_OpenNewSession()
            if self.sessionID < 0:
                print(f"セッションID取得エラー: {self.sessionID}")
                return False

            print(f"セッションID = {self.sessionID} で接続します...")

            match = re.search(r'(\d+)$', com_port_str)
            if not match:
                print(f"エラー: 無効なCOMポート名です: {com_port_str}")
                return False
            com_port_number = match.group(1)
            
            ret, response = self._send_command(f"controller.connect {com_port_number}")
            
            if ret != 0:
                print(f"ステージコントローラへの接続失敗 ({com_port_str}): {response} (戻り値: {ret})")
                return False
                
            print(f"ステージコントローラ ({com_port_str}) に接続しました。 (応答: {response})")
            self._is_initialized = True
            return True

        except Exception as e:
            print(f"ステージ初期化中に予期せぬエラー: {e}")
            self._is_initialized = False
            return False
        
        finally:
            print(f"カレントディレクトリを元に戻します: {original_cwd}")
            os.chdir(original_cwd)

    def _send_command(self, command_str: str) -> Tuple[int, str]:
        if not self.sdk or self.sessionID < 0:
            return -1, "SDK not initialized"
            
        self.rx.value = b""
        cmd_bytes = create_string_buffer(command_str.encode('utf-8'))
        
        ret = self.sdk.PriorScientificSDK_cmd(
            c_int(self.sessionID), 
            cmd_bytes, 
            self.rx
        )
        
        response_str = self.rx.value.decode('utf-8').strip() 
        return ret, response_str

    def close(self):
        print("ステージコントローラの切断処理...")
        if self._is_initialized:
            self._send_command("controller.disconnect")
        
        if self.sdk and self.sessionID >= 0:
            self.sdk.PriorScientificSDK_CloseSession(c_int(self.sessionID))
            print("SDKセッションをクローズしました。")
            
        self._is_initialized = False
        self.sdk = None

    def set_origin_to_current(self) -> bool:
        """ 
        現在位置を (0, 0) に設定する
        (X軸が反転していても、コントローラの内部座標 0 を設定する)
        """
        ret, response = self._send_command("controller.stage.position.set 0 0")
        return ret == 0

    def get_position(self) -> Tuple[float, float]:
        """ 
        現在の位置 (x, y) を取得する (単位: microns) 
        (修正: X軸の符号を反転させる)
        """
        ret, response = self._send_command("controller.stage.position.get")
        if ret == 0:
            try:
                parts = response.split(',')
                x_controller = float(parts[0]) 
                y_controller = float(parts[1])
                
                # (修正) コントローラのX座標を反転させて、実際の座標に合わせる
                x_actual = -x_controller
                
                return x_actual, y_controller
            except (IndexError, ValueError) as e:
                print(f"位置データのパース失敗: {response} ({e})")
                return 0.0, 0.0
        print(f"位置データの取得失敗: {response} (戻り値: {ret})")
        return 0.0, 0.0

    def move_to_position(self, x: float, y: float):
        """ 
        指定された (x, y) 座標に移動する (単位: microns) 
        (修正: X軸の符号を反転させてコントローラに指示する)
        """
        
        # (修正) 目的のX座標 (x) に移動するため、
        # コントローラには反転したX座標 (-x) を指示する
        x_controller = -x
        
        ret, response = self._send_command(f"controller.stage.goto-position {x_controller} {y}")
        
        if ret != 0:
            print(f"移動開始エラー: {response} (戻り値: {ret})")
            return
        
        # 移動完了まで待機 (ポーリング)
        while self._is_initialized:
            time.sleep(0.1) 
            ret, busy_response = self._send_command("controller.stage.busy.get")
            
            if ret == 0:
                try:
                    status = int(busy_response.split(',')[0]) 
                    if status == 0:
                        break 
                except (IndexError, ValueError):
                    print(f"Busyステータス取得失敗: {busy_response}")
                    break 
            else:
                print(f"Busyステータス取得失敗: {busy_response} (戻り値: {ret})")
                break 

    def stop_move(self):
        """ ステージの移動を緊急停止する """
        self._send_command("controller.stage.move-at-velocity 0 0")