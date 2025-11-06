import cv2
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
    from auto_microscope.devices.camera_controller import CameraControl
    from auto_microscope.core.exceptions import CameraConnectionError, CameraError
except ImportError as e:
    print(f"エラー: {e}")
    print("プロジェクトのインポートに失敗しました。")
    print("1. 'pip install -e .' を実行しましたか？")
    print("2. このスクリプトはプロジェクトルート ('microscope_auto_imaging/') に置いていますか？")
    sys.exit(1)

def run_camera_test():
    """
    TeliCam (実機) に接続し、映像とピントスコアをリアルタイムで表示します。
    """
    cam = None
    
    # (修正) cv2.imshow() が文字化けしないよう、ASCII文字のみに変更
    window_name = "TeliCam Real-time Test (Focus Score) - Press 'q' to quit"
    print("TeliCam (実機) テストを開始します...")

    try:
        # 1. 'telicam' ドライバを指定して初期化
        # (pytelicam と SDK (DLL) が正しくインストールされている必要があります)
        print("CameraControl('telicam') を初期化中...")
        cam = CameraControl(driver_type="telicam")
        
        # 2. 接続
        print("カメラに接続中...")
        cam.connect()
        print("カメラ接続成功。ストリーミングを開始します。")

        last_time = time.time()
        frame_count = 0
        fps = 0.0

        while True:
            # 3. フレーム取得
            frame = cam.get_frame()
            if frame is None:
                print("フレームを取得できませんでした。")
                time.sleep(0.1)
                continue

            # 4. ピントスコア計算
            score = cam.calculate_focus_score(frame)

            # FPS計算
            frame_count += 1
            current_time = time.time()
            if (current_time - last_time) >= 1.0: # 1秒ごとに更新
                fps = frame_count / (current_time - last_time)
                last_time = current_time
                frame_count = 0

            # 5. 映像にスコアとFPSを描画して表示
            display_frame = frame.copy()
            # (描画するテキスト (putText) は日本語でも問題ない場合が多いですが、
            #  互換性のためこちらも英語にしておくとより安全です)
            cv2.putText(display_frame, f"Focus Score: {score:.2f}", 
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.putText(display_frame, f"FPS: {fps:.1f}", 
                        (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow(window_name, display_frame)

            # 'q' キーが押されたらループを終了
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("終了キー 'q' が押されました。")
                break

    except CameraConnectionError as e:
        print(f"\n[エラー] カメラ接続に失敗しました: {e}")
        print(" - TeliCam SDK (pytelicam, DLL) が正しくインストールされていますか？")
        print(" - カメラはPCに正しく接続されていますか？")
    except CameraError as e:
        print(f"\n[エラー] カメラエラーが発生しました: {e}")
    except ImportError as e:
        print(f"\n[エラー] 必要なライブラリが見つかりません: {e}")
        print(" - 'pip install opencv-python' を実行しましたか？")
    except Exception as e:
        print(f"\n[予期せぬエラー] 予期せぬエラーが発生しました: {e}")
    
    finally:
        # 6. 切断とリソース解放
        if cam and cam.is_connected():
            print("カメラ接続を切断します...")
            cam.disconnect()
            print("切断完了。")
        
        cv2.destroyAllWindows()
        print("テストスクリプトを終了します。")

if __name__ == "__main__":
    # (TeliCam SDK が OpenCV (cv2) に依存している場合があるため、先に追加)
    if not 'cv2' in sys.modules:
        try:
            import cv2
        except ImportError:
            print("エラー: OpenCV (cv2) がインストールされていません。")
            print("'pip install opencv-python' を実行してください。")
            sys.exit(1)
            
    run_camera_test()