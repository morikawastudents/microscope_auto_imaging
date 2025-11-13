## 自動撮影ソフトウェア 概要
基板の自動撮影ソフトウェアの設計ドキュメント。
最初にソフトウェアの仕様、インストール手順、起動コマンドを示し、その後プロジェクト構成、各モジュールの役割、クラス一覧と継承関係を説明する。

## 仕様 (自動走査とマップ表示まで実装)
- **対応カメラ:** TeliCam (pytelicam SDK)
- **対応ステージ:** Prior Scientific (Prior SDK)

main.py から起動し、PySide6 GUIで操作する。生成されたGUIウィンドウ上には以下のコンポーネントが含まれる:
  - カメラ映像表示エリア (CameraViewWidget)
    - リアルタイム映像表示
    - ピントスコア表示
  - 基板マップ表示エリア (MapDisplayWidget)
    - 基板位置・種類表示
    - ステージ現在位置表示
  - 操作パネル (ControlPanelWidget)
    - ファイル選択、COMポート選択
    - 接続、原点設定、自動撮影開始ボタン
    - ログ表示エリア
    - 手動撮影ボタン

GUI上で基板位置の設定ファイル、基板種類の設定ファイルを指定し、ステージを接続、原点設定後、「自動撮影開始」ボタンでワークフローを実行する。撮影された画像は指定ディレクトリに保存される。ワークフローが実行されると、ステージは所定の基板位置に自動で移動し、写真撮影が実行され次第、次の位置へ移動する。撮影中はマップ表示エリアで現在のステージ位置が更新される。


## インストール手順と起動コマンド

**リポジトリのクローン**
```bash
git clone git@github.com:morikawastudents/microscope_auto_imaging.git
```

**仮想環境の作成と有効化**
```bash
cd microscope_auto_imaging
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux 
# source venv/bin/activate
pip install -r requirements.txt
```

**カメラドライバのインストール**
TeliCam SDK
```bash
cd microscope_auto_imaging
pip install ./src/drivers/camera/lib/pytelicam-1.1.1-cp312-cp312-win_amd64.whl
```

**ステージドライバのインストール**
Prior Scientific SDK

./src/drivers/stage/Prior_driver/PriorScientificSDK.dll をコード内で直接参照するため、インストール不溶。


**起動コマンド:**
```bash
python -m auto_microscope.main
```

---

## プロジェクト構成と各モジュールの役割

### ディレクトリツリー

```
src/auto_microscope/
├── __init__.py
├── main.py                          # アプリケーション起動点
├── core/                            # コア機能（例外、設定管理）
│   ├── __init__.py
│   ├── exceptions.py                # カスタム例外定義
│   └── utils.py                     # 共通ユーティリティ
├── devices/                         # ハードウェア制御のファサード層
│   ├── __init__.py
│   ├── camera_controller.py         # カメラ制御の統一I/F
│   ├── stage_controller.py          # ステージ制御の統一I/F
│   └── analysis/
│       ├── __init__.py
│       └── focus_analyzer.py        # ピントスコア計算
├── drivers/                         # SDK固有の具体的な実装
│   ├── __init__.py
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── abstract_camera.py       # カメラ抽象基底クラス
│   │   ├── dummy_camera.py          # ダミーカメラ実装
│   │   ├── telicam_sdk.py           # TeliCam SDK ラッパー
│   │   └── lib/                     # SDKライブラリ
│   │       └── pytelicam-1.1.1-...
│   └── stage/
│       ├── __init__.py
│       ├── abstract_stage.py        # ステージ抽象基底クラス
│       ├── dummy_stage.py           # ダミーステージ実装
│       ├── prior_sdk.py             # Prior SDK ラッパー
│       ├── prior_helper.py          # Prior SDK DLL通信ヘルパー
│       └── Prior_driver/
│           └── PriorScientificSDK.dll
├── services/                        # ビジネスロジック層
│   ├── __init__.py
│   ├── imaging_workflow.py          # 撮影ワークフロー
│   └── config_service.py            # 設定ファイル管理（ConfigManager）
├── gui/                             # GUIコンポーネント（PySide6）
│   ├── __init__.py
│   ├── main_window.py               # メインウィンドウ
│   ├── utils.py                     # GUI用ユーティリティ
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── camera_view_widget.py    # カメラ映像表示
│   │   ├── control_panel_widget.py  # 操作パネル
│   │   └── map_display_widget.py    # 基板マップ表示
│   └── threads/
│       ├── __init__.py
│       ├── camera_thread.py         # カメラスレッド
│       └── workflow_thread.py       # ワークフロースレッド
└── tests/                           # ユニットテスト
    ├── devices/
    ├── gui/
    └── services/
```

---

## クラス一覧と継承関係

### 1. **抽象基底クラス (Abstract Base Classes)**

#### AbstractCamera
```python
class AbstractCamera(ABC):
    """全カメラ実装が従うべきインターフェース"""
    
    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def get_frame(self) -> np.ndarray: ...
    @abstractmethod
    def set_exposure(self, exposure_ms: float) -> None: ...
    @abstractmethod
    def get_exposure(self) -> float: ...
    @abstractmethod
    def is_connected(self) -> bool: ...
```

**受け取る値:** なし（インターフェース定義のみ）  
**継承元:** ABC  
**役割:** カメラ実装の統一インターフェース定義

---

#### AbstractStage
```python
class AbstractStage(ABC):
    """全ステージ実装が従うべきインターフェース（座標系: mm）"""
    
    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def move_abs(self, x: float, y: float) -> None: ...
    @abstractmethod
    def move_rel(self, dx: float, dy: float) -> None: ...
    @abstractmethod
    def get_position(self) -> tuple[float, float]: ...
    @abstractmethod
    def set_origin(self) -> None: ...
    @abstractmethod
    def is_moving(self) -> bool: ...
    @abstractmethod
    def wait_for_move(self) -> None: ...
    @abstractmethod
    def is_connected(self) -> bool: ...
```

**受け取る値:** なし（インターフェース定義のみ）  
**継承元:** ABC  
**役割:** ステージ実装の統一インターフェース定義（座標単位: mm）

---

### 2. **ドライバ層（具体的な実装）**

#### DummyCamera
```python
class DummyCamera(AbstractCamera):
    """デバッグ・テスト用ダミーカメラ"""
    
    def __init__(self, resolution=(640, 480), image_filename="dummy_image.png")
```

**受け取る値:** 
- resolution: タプル（幅, 高さ）
- image_filename: 読み込む画像ファイル名

**継承元:** AbstractCamera  
**役割:** 
- ファイルから画像を読み込んでフレームとして返す
- 実カメラなしでGUIテスト可能

---

#### TeliCamSdk
```python
class TeliCamSdk(AbstractCamera):
    """TeliCam SDK ラッパー（実カメラ制御）"""
    
    def __init__(self, camera_index=0)
```

**受け取る値:**
- camera_index: カメラインデックス（デフォルト: 0）

**継承元:** AbstractCamera  
**役割:**
- pytelicam SDK経由でTeliCamを制御
- フレーム取得、露光時間設定

---

#### DummyStage
```python
class DummyStage(AbstractStage):
    """デバッグ・テスト用ダミーステージ（オフセット座標系）"""
    
    def __init__(self)
```

**受け取る値:** なし  
**継承元:** AbstractStage  
**役割:**
- メモリ内で仮想ステージの座標を保持
- _origin_x, _origin_yでオフセット基準を管理
- 実ステージなしでGUIテスト可能

---

#### PriorSdk
```python
class PriorSdk(AbstractStage):
    """Prior Scientific ステージ SDK ラッパー（実ステージ制御）"""
    
    def __init__(self, com_port_str: str, dll_path: str = "PriorScientificSDK.dll")
```

**受け取る値:**
- com_port_str: COMポート（例: "COM3"）
- dll_path: DLLファイルパス

**継承元:** AbstractStage  
**役割:**
- PriorStageHelper経由でSDK DLL通信
- mm ↔ μm 単位変換を実装
- X軸座標系反転に対応

---

#### PriorStageHelper
```python
class PriorStageHelper:
    """Prior SDK DLL との低レベル通信ヘルパー"""
    
    def __init__(self, dll_path: str)
```

**受け取る値:**
- dll_path: DLLファイルパス

**継承元:** なし（ヘルパークラス）  
**役割:**
- ctypes.WinDLLでPriorSDKをロード
- controller.connect, controller.move_abs コマンド送信
- X軸座標系反転を内部で吸収

---

### 3. **デバイス制御層（ファサード）**

#### CameraControl
```python
class CameraControl:
    """カメラ制御の統一I/F（ファサード）"""
    
    def __init__(self, driver_type: str = "dummy", **kwargs)
```

**受け取る値:**
- driver_type: "dummy" または "telicam"
- **kwargs: ドライバ固有オプション

**継承元:** なし（ファサード）  
**役割:**
- driver_typeに応じてDummyCameraまたはTeliCamSdkをインスタンス化
- CameraControl.connect(), .get_frame()など統一I/Fを提供
- GUI/ワークフローはドライバ詳細を知らない

---

#### StageControl
```python
class StageControl:
    """ステージ制御の統一I/F（ファサード）"""
    
    def __init__(self, driver_type: str = "dummy", **kwargs)
```

**受け取る値:**
- driver_type: "dummy" または "prior"
- **kwargs: ドライバ固有オプション（例: com_port_str）

**継承元:** なし（ファサード）  
**役割:**
- driver_typeに応じてDummyStageまたはPriorSdkをインスタンス化
- StageControl.move_abs(), .get_position()など統一I/Fを提供

---

### 4. **分析層**

#### FocusAnalyzer
```python
class FocusAnalyzer:
    """画像フレームのピント評価"""
    
    @staticmethod
    def calculate_laplacian_variance(frame: np.ndarray) -> float:
        """ラプラシアン分散でピントスコア計算"""
```

**受け取る値:** 
- frame: numpy配列（OpenCV画像）

**継承元:** なし（ユーティリティクラス）  
**役割:**
- OpenCVのLaplacian関数でエッジ検出
- 分散（ピントスコア）を計算・返却

---

### 5. **サービス層（ビジネスロジック）**

#### ConfigManager
```python
class ConfigManager:
    """基板位置・種類のJSONファイル I/O とCSVエクスポート"""
    
    def __init__(self)
```

**受け取る値:** なし  
**継承元:** なし  
**役割:**
- layout_data: {"1": {"x": 10.0, "y": 5.0}, ...} を読み込み
- map_data: {"1": "TypeA", "2": "TypeB", ...} を読み込み
- get_target_positions(): 両データを統合してターゲットリスト返却
- export_map_to_csv(): 基板種類マップをCSV出力

---

#### ImagingWorkflow
```python
class ImagingWorkflow:
    """撮影ワークフロー管理（高レベル操作）"""
    
    def __init__(self, camera_driver: str, stage_driver: str, **stage_kwargs)
```

**受け取る値:**
- camera_driver: "dummy" または "telicam"
- stage_driver: "dummy" または "prior"
- **stage_kwargs: ステージドライバへのオプション（例: com_port_str）

**継承元:** なし  
**役割:**
- CameraControl, StageControl, ConfigManagerを保持
- connect_stage(), set_stage_origin(), move_to_target(target)など高レベルメソッド提供
- load_config(layout_path, map_path): 設定ファイル読み込み
- get_targets(): 撮影ターゲットリスト取得

---

### 6. **GUI層（PySide6ウィジェット）**

#### CameraViewWidget
```python
class CameraViewWidget(QWidget):
    """カメラ映像リアルタイム表示"""
```

**受け取る値:** 
- parent: 親ウィジェット

**継承元:** QWidget（PySide6）  
**役割:**
- カメラスレッドからのQImage信号を受け取り表示
- ピントスコア値をテキストで表示
- スケーリング対応

---

#### ControlPanelWidget
```python
class ControlPanelWidget(QWidget):
    """操作パネル（設定、接続、操作）"""
    
    # シグナル例：
    load_layout_requested = Signal(str)
    connect_stage_requested = Signal(str)
    start_workflow_requested = Signal()
```

**受け取る値:** 
- parent: 親ウィジェット

**継承元:** QWidget（PySide6）  
**役割:**
- ファイルパス選択UI（基板位置JSON、基板種類JSON、出力ディレクトリ）
- COMポート選択＆「接続」ボタン
- 「原点設定」「自動撮影開始」「手動撮影」ボタン
- ログメッセージ表示エリア
- メインウィンドウへシグナル emission で要求を通知

---

#### MapDisplayWidget
```python
class MapDisplayWidget(QWidget):
    """基板レイアウト・種類・ステージ位置の視覚表示"""
    
    @Slot(list)
    def update_targets(self, targets: list[dict]): ...
    
    @Slot(float, float)
    def update_stage_position(self, x_mm: float, y_mm: float): ...
```

**受け取る値:**
- targets: ターゲット辞書リスト [{"id": "1", "type": "TypeA", "x": 10.0, "y": 5.0}, ...]
- x_mm, y_mm: 現在ステージ位置（mm）

**継承元:** QWidget（PySide6）  
**役割:**
- mm座標 → px座標に変換して描画
- ターゲットを色分け表示（種別ごと）
- 現在ステージ位置を十字マーカーで表示
- ハイライト機能（撮影中のターゲットを強調）

---

#### MainWindow
```python
class MainWindow(QMainWindow):
    """メインウィンドウ（全ウィジェット統合）"""
    
    USE_DUMMY_DEVICES = True  # ダミーモード切り替え
    
    def __init__(self)
```

**受け取る値:** なし  
**継承元:** QMainWindow（PySide6）  
**役割:**
- CameraViewWidget, MapDisplayWidget, ControlPanelWidgetを配置
- ウィジェット間のシグナル/スロット接続
- ImagingWorkflowインスタンス管理
- CameraThread, WorkflowThread管理
- QSettingsでウィンドウ状態・ファイルパス保存
- ステージ位置ポーリングタイマー（100ms間隔）

---

### 7. **スレッド層**

#### CameraThread
```python
class CameraThread(QThread):
    """カメラフレーム取得スレッド（GUIブロック回避）"""
    
    frame_ready = Signal(QImage)  # フレーム準備シグナル
    focus_score_updated = Signal(float)  # ピントスコア更新シグナル
```

**受け取る値:**
- camera: CameraControlインスタンス

**継承元:** QThread（PySide6）  
**役割:**
- 別スレッドでカメラから連続フレーム取得
- FocusAnalyzerでピントスコア計算
- 計算結果をシグナル emission でGUIに通知（ブロッキング回避）

---

#### WorkflowThread
```python
class WorkflowThread(QThread):
    """撮影ワークフロー実行スレッド（GUIブロック回避）"""
    
    target_image_captured = Signal(str, np.ndarray)  # 撮影完了シグナル
    workflow_finished = Signal()
    error_occurred = Signal(str)
```

**受け取る値:**
- workflow: ImagingWorkflowインスタンス

**継承元:** QThread（PySide6）  
**役割:**
- 別スレッドでImagingWorkflowメソッド実行
- ステージ移動、撮影を順序実行
- 進捗をシグナル emission でGUIに通知

---

---

## データフロー例：「自動撮影開始」の流れ

```
[GUI] ControlPanelWidget
  ↓ (ボタンクリック)
  → start_workflow_requested シグナル emission
    ↓
[GUI] MainWindow.on_start_workflow()
  ↓ (WorkflowThreadを起動)
  → WorkflowThread.run()
    ↓
[Logic] ImagingWorkflow.run()
  ├→ ConfigManager.get_target_positions() → ターゲット取得
  ├→ StageControl.move_abs(target_x, target_y) → 移動
  ├→ CameraControl.get_frame() → 撮影
  ├→ FocusAnalyzer.calculate_laplacian_variance() → ピント評価
  └→ ファイル保存
    ↓
[Thread] target_image_captured シグナル → MainWindow
  ↓
[GUI] MapDisplayWidget.highlight_target() → マップ更新
[GUI] CameraViewWidget 映像更新
```

---

## 設定ファイル例

### data/substrate_layout.json （基板位置）
```json
{
  "1": {"x": 0.0, "y": 0.0},
  "2": {"x": 17.5, "y": 0.0},
  "3": {"x": 35.0, "y": 0.0}
}
```

### data/substrate_map.json （基板種類）
```json
{
  "1": "TypeA",
  "2": "TypeB",
  "3": "TypeA"
}
```

---

## 例外定義 (core/exceptions.py)

```python
class AutoMicroscopeError(Exception): ...
class CameraError(AutoMicroscopeError): ...
class CameraConnectionError(CameraError): ...
class StageError(AutoMicroscopeError): ...
class StageConnectionError(StageError): ...
class ConfigError(AutoMicroscopeError): ...
```

---

## テストスクリプト

- manual_test_camera.py: TeliCam実機テスト
- manual_test_stage.py: Prior実機テスト  
- manual_test_workflow.py: 統合ワークフローテスト
- tests/: ユニットテスト（pytest）

---

## 開発バージョン計画

| Ver | 機能 | 実装状況 |
|-----|------|--------|
| 1.0 | 基本UI、ダミーデバイス | ✅ |
| 2.0 | 実デバイス接続、リアルタイム表示 | ✅ |
| 2.1 | マップ表示、ステージ位置同期 | ✅ |
| 2.2 | 自動ワークフロー、CSV出力 | 進行中 |
| 3.0 | 画像安定性監視、自動撮影トリガー | 計画中 |
| 4.0 | パターン認識、位置合わせ | 計画中 |