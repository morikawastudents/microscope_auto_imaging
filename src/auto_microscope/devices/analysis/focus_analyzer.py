import cv2
import numpy as np

class FocusAnalyzer:
    """
    画像フレームに関する分析機能を提供するクラス。
    現在はピントスコア計算 (ラプラシアン分散法) を静的メソッドとして提供します。
    """

    @staticmethod
    def calculate_laplacian_variance(frame: np.ndarray) -> float:
        """
        画像（カラーまたはグレースケール）を受け取り、ピントスコア（ラプラシアンの分散）を計算する。
        
        Args:
            frame (np.ndarray): 入力となる画像 (BGR または グレースケール)

        Returns:
            float: ピントスコア。値が大きいほどピントが合っている。
        """
        if frame is None or frame.size == 0:
            print("[FocusAnalyzer] ピント計算エラー: 無効な画像です。")
            return 0.0

        try:
            # 1. グレースケールに変換
            #    DummyCameraは元々グレースケールかもしれないので、チャネル数をチェック
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            elif len(frame.shape) == 2:
                gray = frame
            else:
                print(f"[FocusAnalyzer] 予期しないフレーム形状です: {frame.shape}")
                return 0.0
        
            # 2. ラプラシアンフィルタを適用 (64bit浮動小数点数で計算)
            #    ksize=3 (3x3カーネル) は一般的で高速な設定
            laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
            
            # 3. フィルタ結果の「分散」を計算
            variance = laplacian.var()
            
            return float(variance)
            
        except cv2.error as e:
            print(f"[FocusAnalyzer] ピント計算中にOpenCVエラーが発生しました: {e}")
            return 0.0
        except Exception as e:
            print(f"[FocusAnalyzer] ピント計算中に予期せぬエラーが発生しました: {e}")
            return 0.0

# --- このファイルが直接実行された場合のテストコード ---
if __name__ == "__main__":
    # ダミーの画像を作成してテスト
    
    # 1. ボケた画像 (分散が低いはず)
    blurry_img = np.zeros((480, 640), dtype=np.uint8)
    cv2.circle(blurry_img, (320, 240), 100, 150, -1)
    blurry_img = cv2.GaussianBlur(blurry_img, (51, 51), 0)
    
    # 2. シャープな画像 (分散が高いはず)
    sharp_img = np.zeros((480, 640), dtype=np.uint8)
    cv2.circle(sharp_img, (320, 240), 100, 150, -1)

    # クラスメソッドとして呼び出す
    score_blurry = FocusAnalyzer.calculate_laplacian_variance(blurry_img)
    score_sharp = FocusAnalyzer.calculate_laplacian_variance(sharp_img)

    print(f"ボケた画像のスコア: {score_blurry:.2f}")
    print(f"シャープな画像のスコア: {score_sharp:.2f}")

    # OpenCVで表示して確認
    cv2.imshow("Blurry (Score: {:.2f})".format(score_blurry), blurry_img)
    cv2.imshow("Sharp (Score: {:.2f})".format(score_sharp), sharp_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()