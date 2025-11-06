import sys
import os
import time

# --- プロジェクトの 'src' フォルダを Python の検索パスに追加 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)
# -----------------------------------------------------------

try:
    # 制御クラスをすべてインポート
    from auto_microscope.services.imaging_workflow import ImagingWorkflow
    from auto_microscope.core.exceptions import AutoMicroscopeError
except ImportError as e:
    print(f"エラー: {e}")
    print("プロジェクトのインポートに失敗しました。")
    print("1. 'pip install -e .' を実行しましたか？")
    print("2. このスクリプトはプロジェクトルート ('microscope_auto_imaging/') に置いていますか？")
    sys.exit(1)

# +++ 実行前に設定してください +++
USE_DUMMY_DEVICES = False # 実機テストの場合は False に
YOUR_COM_PORT = "COM9"    # (実機の場合) PriorステージのCOMポート
# ++++++++++++++++++++++++++++++

# +++ 設定ファイルパス (data/ フォルダにあると仮定) +++
LAYOUT_FILE = os.path.join(script_dir, 'data', 'substrate_layout.json')
MAP_FILE = os.path.join(script_dir, 'data', 'substrate_map.json')
# ++++++++++++++++++++++++++++++

def run_workflow_test():
    
    workflow: ImagingWorkflow | None = None
    
    try:
        if USE_DUMMY_DEVICES:
            print("--- ダミーデバイスでテストを開始します ---")
            workflow = ImagingWorkflow(
                camera_driver="dummy",
                stage_driver="dummy"
            )
        else:
            print("--- 実機デバイスでテストを開始します ---")
            print(f"  Camera: telicam")
            print(f"  Stage: prior (Port: {YOUR_COM_PORT})")
            workflow = ImagingWorkflow(
                camera_driver="telicam",
                stage_driver="prior",
                com_port_str=YOUR_COM_PORT
            )

        # 1. 初期化 (設定ファイル読み込み、デバイス接続)
        print("\n[ステップ1] システムを初期化します...")
        if not os.path.exists(LAYOUT_FILE) or not os.path.exists(MAP_FILE):
            print(f"[エラー] 設定ファイルが見つかりません。")
            print(f"  {LAYOUT_FILE}")
            print(f"  {MAP_FILE}")
            print(f"  'data' フォルダに .json ファイルを配置してください。")
            return

        workflow.initialize_systems(
            layout_path=LAYOUT_FILE,
            map_path=MAP_FILE
        )
        print("[ステップ1] 初期化完了。")
        
        # 2. ワークフロー実行 (ver1 の手動シーケンス)
        # (原点設定、移動、手動撮影)
        print("\n[ステップ2] 手動ワークフロー (ver1) を開始します...")
        workflow.run_ver1_manual_workflow()
        
        print("\n[ステップ3] テストが正常に完了しました。")

    except AutoMicroscopeError as e:
        print(f"\n[エラー] ワークフローエラーが発生しました: {e}")
    except Exception as e:
        print(f"\n[予期せぬエラー] 予期せぬエラーが発生しました: {e}")
    
    finally:
        # 3. シャットダウン (必ず実行)
        if workflow and workflow._is_initialized:
            print("\n[ステップ4] システムをシャットダウンします...")
            workflow.shutdown_systems()
        
        print("テストスクリプトを終了します。")

if __name__ == "__main__":
    run_workflow_test()