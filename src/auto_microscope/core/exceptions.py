"""
アプリケーション全体で使用するカスタム例外クラスを定義します。
"""

class AutoMicroscopeError(Exception):
    """
    このアプリケーション固有のすべての例外の基底クラス。
    """
    pass

# --- Camera Exceptions ---

class CameraError(AutoMicroscopeError):
    """
    カメラ関連のすべてのエラーの基底クラス。
    """
    pass

class CameraConnectionError(CameraError):
    """
    カメラの接続、初期化、または切断に失敗した場合に送出される例外。
    (例: ドライバが見つからない、SDKの初期化失敗など)
    """
    pass

# --- Stage Exceptions ---

class StageError(AutoMicroscopeError):
    """
    ステージ関連のすべてのエラーの基底クラス。
    """
    pass

class StageConnectionError(StageError):
    """
    ステージの接続、初期化、または切断に失敗した場合に送出される例外。
    (例: COMポートが開けない、DLLが見つからないなど)
    """
    pass

# --- Config/File Exceptions ---

class ConfigError(AutoMicroscopeError):
    """
    設定ファイル（config.ini, .json など）の読み書きやパースに関するエラー。
    """
    pass

class ValueError(AutoMicroscopeError):
    pass