プロジェクト構成案: 自動顕微鏡システム (PySide6版)

このドキュメントでは、PySide6をGUIフレームワークとして使用する場合のディレクトリ構成と各モジュールの役割について説明します。

## 技術選定

GUI (フロントエンド): PySide6

Pythonで直接GUIを構築し、ハードウェア制御ロジックをシームレスに呼び出すモノリシックなデスクトップアプリケーション構成を採用します。

ハードウェア/ロジック (バックエンド): Python

OpenCV, リニアステージの制御ライブラリなど、Pythonモジュールとして実装します。

## ディレクトリ構成 (トップレベル)

APIサーバーが不要になるため、frontend/ ディレクトリは削除し、すべてのコードを src/ 配下に統合します。

auto_microscope_system/
├── .gitignore
├── pyproject.toml         # Pythonプロジェクト設定、依存関係 (PySide6, OpenCVなど)
├── README.md
└── src/                   # Python ソースコード
    └── auto_microscope/


3. バックエンド・GUI (src/auto_microscope/) の詳細

GUIとロジックが統合されたディレクトリ構成です。

src/
    └── auto_microscope/
        ├── __init__.py
        ├── main.py        # PySide6 アプリケーションのメインエントリポイント (QApplicationの起動)
        ├── gui/           # PySide6 GUIコンポーネント (View)
        │   ├── __init__.py
        │   ├── main_window.py # メインウィンドウ (QMainWindow)
        │   ├── video_widget.py  # カメラ映像とピントスコア表示 (QWidget)
        │   ├── control_panel.py # 操作ボタン (QGroupBox or QWidget)
        │   └── config_widget.py # 設定ファイルI/Oやパス設定用ウィジェット
        │
        ├── core/            # コアロジック, データモデル (Model)
        │   ├── __init__.py
        │   ├── config_loader.py # YAML/CSVの読み書きロジック
        │   ├── exceptions.py  # カスタム例外 (例: StageConnectionError)
        │   └── models.py      # Pydanticデータモデル (設定ファイル構造)
        │
        ├── devices/         # ハードウェア制御の抽象化レイヤー (Model/Interface)
        │   ├── __init__.py
        │   ├── camera_control.py  # カメラI/F (ピント計算含む) - アプリ側窓口
        │   ├── stage_control.py   # ステージI/F - アプリ側窓口
        │   └── analysis/        # (ver2以降) 画像解析
        │       ├── __init__.py
        │       ├── focus_analyzer.py # ピントスコア計算ロジック
        │       └── pattern_recognition.py # (ver3-4) パターン認識, 位置合わせ
        │
        ├── drivers/         # SDK固有の実装 (Hardware Drivers)
        │   ├── __init__.py
        │   ├── camera/        # カメラドライバ パッケージ
        │   │   ├── __init__.py
        │   │   ├── abstract_camera.py # (必須) カメラ共通の抽象基底クラス
        │   │   ├── dummy_camera.py    # ダミーカメラ実装
        │   │   ├── maker_a_sdk.py     # メーカーAのSDKラッパー
        │   │   ├── opencv_camera.py   # OpenCV (Webカメラ) 用ラッパー
        │   │   ├── telicam_sdk.py   # TeliCam SDK ラッパー
        │   │   └── sdk_files_a/       # メーカーAの構成ファイル (DLL, .iniなど)
        │   │       ├── config.ini
        │   │       └── ASdk.dll
        │   │
        │   ├── stage/         # ステージドライバ パッケージ
        │   │   ├── __init__.py
        │   │   ├── abstract_stage.py  # (必須) ステージ共通の抽象基dクラス
        │   │   ├── dummy_stage.py     # ダミーステージ実装 (オフセットロジック)
        │   │   ├── prior_sdk.py     # Prior SDK ラッパー (AbstractStageを実装)
        │   │   ├── prior_helper.py  # (追加) Prior SDK (DLL) と通信するヘルパー
        │   │   └── Prior_driver/    # (更新) Priorの構成ファイル (DLL)
        │   │       └── PriorScientificSDK.dll
        │   │
        │
        └── services/          # ビジネスロジック (Controller)
            ├── __init__.py
            ├── imaging_workflow.py # 自動撮影シーケンス管理 (QThread内で実行)
            └── system_signals.py   # (旧status_manager) Qtシグナル(QObject)を定義 (状態更新、ログ表示用)



4. モジュールの役割詳細

src/auto_microscope/

main.py: アプリケーションの起動点。QApplication を初期化し、gui/main_window.py の MainWindow を生成・表示します。

gui/: GUI（ビュー）関連のモジュール。

main_window.py: メインウィンドウ。video_widget や control_panel を配置します。ボタンのシグナル（クリック）を services のロジック（スロット）に接続する役割を持ちます。

video_widget.py: カメラ映像を表示するウィジェット。devices/camera_control からの映像フレーム（QImage）をQtシグナル経由で受け取り描画します。ピントスコアも表示します。

control_panel.py: 「原点設定」「実行開始」「手動撮影」などのボタンを配置します。

config_widget.py: (ver1) config ウィンドウとして、各ディレクトリパスを設定ファイルダイアログ（QFileDialog）で設定するUIを提供します。

core/: (変更なし) アプリケーション全体で使用する共通ロジック（設定ファイルI/O、データモデル）。

devices/: ハードウェア制御の「抽象インターフェース」層（ファサード）。services 層や gui 層は、ハードウェアの具体的なメーカー（SDK）を知ることなく、この層のメソッド（例: move_abs(x, y)）だけを呼び出します。

camera_control.py: アプリケーション側（GUIやWorkflow）への窓口。drivers/camera/ から設定に応じて具象クラス（MakerACamera や OpenCvCamera）をインポートし、そのインスタンスを内部で保持します。ピントスコア計算（OpenCV利用）もこの層で行います。

stage_control.py: 同様に drivers/stage/ から具象クラスをインポートし、アプリケーション側に統一されたI/F（move_abs, set_origin等）を提供します。

drivers/: (構成変更) SDKなど、特定のハードウェアに強く依存する「具象」コードを格納します。

camera/ (新設パッケージ):

maker_a_sdk.py: メーカー提供のSDKライブラリ（sdk_files_a/ 内のDLLなど）をインポートし、Pythonから扱えるようにラップするクラス。

opencv_camera.py: WebカメラをOpenCV経由で操作するクラス。

sdk_files_a/: SDKのDLL、設定ファイルなどを格納します。

stage/ (新設パッケージ):

maker_b_sdk.py: メーカーBのSDK（シリアル通信など）をラップするクラス。

sdk_files_b/: SDKのDLL、設定ファイルなどを格納します。

dummy_hardware.py: SDKが接続されていない状態でも開発・テストができるよう、統一I/Fを持つダミークラス。

services/: GUIとデバイス（ハードウェア）を仲介するビジネスロジック（コントローラー）。

imaging_workflow.py: 自動撮影シーケンスを実行します。devices/stage_control や devices/camera_control の抽象I/Fを呼び出してシーケンスを実行します。GUIのフリーズを防ぐため、必ず QThread の run() メソッド内で実行します。

system_signals.py: QObject を継承したクラスを定義し、アプリケーション全体で使用するカスタムシグナル（例: stagePositionUpdated, focusScoreUpdated, logMessageGenerated）を定義します。

5. 開発バージョン計画 (PySide6版)

(変更なし)

ver1: gui/ の基本コンポーネントと devices/ の制御クラスを実装します。control_panel のボタンクリック（シグナル）で devices/stage_control のメソッド（スロット）が直接呼ばれる形を実装します。config_widget でパスを設定し、手動撮影ボタンで imaging_workflow (ver1) がCSVをエクスポートするロジックを実装します。

ver2: devices/analysis/image_stability.py を実装し、imaging_workflow (QThread) 内でピントスコアと安定性を監視し、自動で撮影（camera_control.capture()）をトリガーするように改良します。

ver3: devices/analysis/pattern_recognition.py を実装。imaging_workflow が認識結果をCSVに含めます。GUI側で確認ダイアログ（QMessageBox やカスタム QDialog）を表示します。

ver4: pattern_recognition に位置合わせロジックを追加し、imaging_workflow が複数の座標を計画的に撮影・結合（スティッチング）するように拡張します。