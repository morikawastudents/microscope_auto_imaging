import sys
import os
import time

# --- プロジェクトの 'src' フォルダを Python の検索パスに追加 ---
# (このスクリプトを 'microscope_auto_imaging/' ルートに置くことを想定)
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)
# -----------------------------------------------------------

try:
    from auto_microscope.devices.stage_controller import StageControl
    from auto_microscope.core.exceptions import StageConnectionError, StageError
except ImportError as e:
    print(f"エラー: {e}")
    print("プロジェクトのインポートに失敗しました。")
    print("1. 'pip install -e .' を実行しましたか？")
    print("2. このスクリプトはプロジェクトルート ('microscope_auto_imaging/') に置いていますか？")
    sys.exit(1)

# +++ 実行前に設定してください +++
YOUR_COM_PORT = "COM9"  # 例: "COM3", "COM4" など
# ++++++++++++++++++++++++++++++

def run_stage_test():
    """
    Priorステージ (実機) に接続し、原点設定と移動のテストを実行します。
    """
    stage = None
    print(f"Priorステージ (実機) テストを開始します (ポート: {YOUR_COM_PORT})...")
    
    if YOUR_COM_PORT == "COM3": # デフォルト値のままの場合
        print("\n[警告] スクリプト内の 'YOUR_COM_PORT' を、")
        print("       お使いのCOMポート名に書き換えてから実行してください。")
        # return # (テストのため続行)

    try:
        # 1. 'prior' ドライバを指定して初期化
        print(f"StageControl('prior', com_port_str='{YOUR_COM_PORT}') を初期化中...")
        stage = StageControl(
            driver_type="prior",
            com_port_str=YOUR_COM_PORT
            # dll_path はデフォルト (PriorScientificSDK.dll) を使用
        )
        
        # 2. 接続
        print("ステージに接続中...")
        stage.connect()
        print("ステージ接続成功。")

        # 3. 原点設定
        print("\n[テスト1] 現在位置を原点 (0, 0) に設定します...")
        stage.set_origin()
        pos = stage.get_position()
        print(f"原点設定完了。現在位置: {pos} (mm)")
        if abs(pos[0]) > 0.01 or abs(pos[1]) > 0.01:
             print("[警告] 原点設定後の位置が (0, 0) ではありません。")

        time.sleep(1.0) # 動作確認のため1秒待機

        # 4. 絶対座標 (mm) へ移動
        target_x_abs, target_y_abs = 1.0, -1.0
        print(f"\n[テスト2] 絶対座標 ({target_x_abs}, {target_y_abs}) mm へ移動します...")
        stage.move_abs(target_x_abs, target_y_abs)
        stage.wait_for_move() # (prior_sdk の move_abs はブロック型だが念のため)
        
        pos = stage.get_position()
        print(f"移動完了。現在位置: {pos} (mm)")
        if (abs(pos[0] - target_x_abs) > 0.01 or 
            abs(pos[1] - target_y_abs) > 0.01):
            print(f"[警告] 移動後の位置が ({target_x_abs}, {target_y_abs}) ではありません。")
            
        time.sleep(1.0)

        # 5. 相対座標 (mm) で移動
        target_dx_rel, target_dy_rel = -1.0, 1.0
        print(f"\n[テスト3] 相対座標 ({target_dx_rel}, {target_dy_rel}) mm (原点に戻るはず) へ移動します...")
        stage.move_rel(target_dx_rel, target_dy_rel)
        stage.wait_for_move()
        
        pos = stage.get_position()
        print(f"移動完了。現在位置: {pos} (mm)")
        if abs(pos[0]) > 0.01 or abs(pos[1]) > 0.01:
            print("[警告] 原点に戻っていません。")

        print("\n[成功] ステージテストが完了しました。")

    except StageConnectionError as e:
        print(f"\n[エラー] ステージ接続に失敗しました: {e}")
        print(" - COMポート ('{YOUR_COM_PORT}') の指定は正しいですか？")
        print(" - ステージの電源はオンで、PCに接続されていますか？")
        print(" - DLLファイルは 'src/auto_microscope/drivers/stage/Prior_driver/' にありますか？")
    except StageError as e:
        print(f"\n[エラー] ステージエラーが発生しました: {e}")
    except ImportError as e:
        print(f"\n[エラー] 必要なライブラリが見つかりません: {e}")
    except Exception as e:
        print(f"\n[予期せぬエラー] 予期せぬエラーが発生しました: {e}")
    
    finally:
        # 6. 切断とリソース解放
        if stage and stage.is_connected():
            print("ステージ接続を切断します...")
            stage.disconnect()
            print("切断完了。")
        
        print("テストスクリプトを終了します。")

if __name__ == "__main__":
    run_stage_test()