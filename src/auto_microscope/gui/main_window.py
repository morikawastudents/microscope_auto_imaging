import sys
import time
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QMessageBox, QLineEdit
)
from PySide6.QtCore import Slot, QCoreApplication
from PySide6.QtGui import QCloseEvent

# --- プロジェクトのコンポーネントをインポート ---
from ..services.imaging_workflow import ImagingWorkflow
from ..core.exceptions import AutoMicroscopeError

# --- GUIコンポーネントをインポート ---
from .widgets.camera_view_widget import CameraViewWidget
from .widgets.control_panel_widget import ControlPanelWidget
from .threads.camera_thread import CameraThread
from .threads.workflow_thread import WorkflowThread
from .utils import populate_com_ports

class MainWindow(QMainWindow):
    """
    メインウィンドウ (司令塔)。
    UIウィジェット (View) とバックグラウンドスレッド (Worker) を管理し、
    両者間のシグナル/スロットを接続します。
    """
    
    # (仮設定) 起動時にダミーデバイスを使うか？
    # (将来的には設定ファイルやGUIで切り替え)
    USE_DUMMY_DEVICES = False 

    def __init__(self):
        super().__init__()
        self.setWindowTitle("顕微鏡自動撮影システム v2.0 (Refactored)")
        self.setGeometry(100, 100, 1100, 700) # 少し大きく

        # --- 内部コンポーネントの保持 ---
        self.workflow: ImagingWorkflow | None = None
        self.camera_thread: CameraThread | None = None
        self.workflow_thread: WorkflowThread | None = None

        # --- UIの初期化 ---
        self.init_ui()
        
        # --- UI とロジックの接続 ---
        self.connect_signals()

        # --- 起動処理 ---
        self.start_camera_thread()
        self.panel.refresh_ports_requested.emit() # COMポートの初期読み込み

    def init_ui(self):
        """ UIの骨格 (左右ペイン) を作成 """
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 左側: カメラビュー
        self.camera_view = CameraViewWidget(self)
        main_layout.addWidget(self.camera_view, 2) # 伸縮比率 2
        
        # 右側: 操作パネル
        self.panel = ControlPanelWidget(self)
        main_layout.addWidget(self.panel, 1) # 伸縮比率 1

    def connect_signals(self):
        """ ウィジェットとスレッド間のシグナル/スロットを接続 """
        
        # --- 1. ControlPanel (UI) -> MainWindow (ロジック) ---
        self.panel.refresh_ports_requested.connect(self.on_refresh_ports)
        self.panel.connect_stage_requested.connect(self.on_connect_stage)
        self.panel.set_origin_requested.connect(self.on_set_origin)
        
        # ワークフロー開始/停止
        self.panel.start_workflow_requested.connect(self.on_start_workflow)
        self.panel.stop_workflow_requested.connect(self.on_stop_workflow)
        
        # パス設定 (MainWindowがWorkflowに中継)
        self.panel.load_layout_requested.connect(self.on_set_layout_path)
        self.panel.load_map_requested.connect(self.on_set_map_path)
        self.panel.output_dir_requested.connect(self.on_set_output_dir)
        
        # 手動撮影
        self.panel.manual_capture_requested.connect(self.on_manual_capture)
        # (CSVエクスポートは workflow_thread ではなく config に直接依頼)
        self.panel.csv_export_requested.connect(self.on_export_csv)

        # --- 2. CameraThread -> UI ---
        # (CameraThread は start_camera_thread() で作成)
        
        # --- 3. WorkflowThread -> UI ---
        # (WorkflowThread は on_start_workflow() で作成)
        
    def start_camera_thread(self):
        """ カメラスレッドを初期化して起動 """
        if self.camera_thread and self.camera_thread.isRunning():
            return
            
        driver = "dummy" if self.USE_DUMMY_DEVICES else "telicam"
        self.camera_thread = CameraThread(driver_type=driver, parent=self)
        
        # シグナルを接続
        self.camera_thread.frame_ready.connect(self.camera_view.update_camera_view)
        self.camera_thread.focus_score_ready.connect(self.camera_view.update_focus_score)
        self.camera_thread.camera_error.connect(self.on_device_error)
        
        self.log(f"[App] カメラスレッド (Driver: {driver}) を起動します...")
        self.camera_thread.start()

    # --- スロット (ControlPanel からの要求) ---

    @Slot()
    def on_refresh_ports(self):
        if self.USE_DUMMY_DEVICES:
            self.panel.com_port_combo.clear()
            self.panel.com_port_combo.addItem("ダミーモード")
            self.panel.com_port_combo.setEnabled(False)
            self.panel.btn_refresh_ports.setEnabled(False)
            self.panel.btn_connect_stage.setEnabled(True) # ダミーは即接続可
            self.panel.btn_connect_stage.setText("ステージ接続 (Dummy)")
            return

        self.log("[App] COMポートを更新しています...")
        try:
            detected = populate_com_ports(self.panel.com_port_combo)
            self.log(f"[App] {len(detected)} 件のポートを検出しました。")
        except Exception as e:
            self.show_error(f"COMポートの列挙に失敗しました: {e}")

    @Slot(str)
    def on_connect_stage(self, com_port: str):
        """ ステージ接続（ImagingWorkflow の初期化）を実行 """
        if self.workflow and self.workflow._is_initialized:
            self.log("[App] すでに接続済みです。")
            return

        self.log("[App] システムの初期化を開始します...")
        try:
            cam_driver = "dummy" if self.USE_DUMMY_DEVICES else "telicam"
            stage_driver = "dummy" if self.USE_DUMMY_DEVICES else "prior"
            
            # (重要) メインスレッドで ImagingWorkflow を初期化
            self.workflow = ImagingWorkflow(
                camera_driver=cam_driver,
                stage_driver=stage_driver,
                com_port_str=com_port # "prior" の場合は kwargs に渡される
            )
            
            # (注) initialize_systems はファイル読み込みも含むため、
            # ワークフロー開始時に移動させた。ここでは接続のみ。
            self.log("[App] ステージに接続しています...")
            self.workflow.stage.connect()
            
            # (注) カメラはカメラスレッドが接続済み
            if not self.camera_thread or not self.camera_thread.isRunning():
                 self.log("[App] 警告: カメラスレッドが実行されていません。")
                 # (ここではカメラ接続は行わず、スレッドに任せる)
            
            self.workflow._is_initialized = True # (手動でフラグ立て)
            
            self.log("[App] ステージ接続成功。")
            self.panel.set_ui_state_connected()
            
        except Exception as e:
            self.show_error(f"ステージの接続に失敗しました: {e}")
            self.workflow = None # 失敗したらリセット

    @Slot()
    def on_set_origin(self):
        if not self.workflow:
            return self.show_error("ステージが接続されていません。")
        try:
            self.workflow.set_stage_origin()
            self.log("[App] ステージの原点を設定しました。")
        except Exception as e:
            self.show_error(f"原点設定エラー: {e}")

    @Slot(str)
    def on_set_layout_path(self, path: str):
        if self.workflow:
            self.workflow.config.load_layout(path)
            self.log(f"[App] 基板位置ファイルを読み込みました: {path}")

    @Slot(str)
    def on_set_map_path(self, path: str):
        if self.workflow:
            self.workflow.config.load_map(path)
            self.log(f"[App] 基板種類ファイルを読み込みました: {path}")
            
    @Slot(str)
    def on_set_output_dir(self, path: str):
        # (Ver1) Workflow に保存先を渡す仕組みがなかったので、
        # MainWindow が保持しておく (手動撮影とCSVエクスポート用)
        self.output_dir = path
        self.log(f"[App] 保存先を設定: {path}")

    @Slot()
    def on_start_workflow(self):
        if not self.workflow or not self.workflow._is_initialized:
            return self.show_error("ステージが接続されていません。")
        if not self.workflow.config.is_ready():
            return self.show_error("設定ファイル（位置・種類）が読み込まれていません。")
            
        try:
            # 撮影対象リストを取得 (エラーチェック)
            targets = self.workflow.get_targets()
            if not targets:
                raise AutoMicroscopeError("設定ファイルから撮影対象が見つかりませんでした。")
            self.log(f"[App] {len(targets)} 件の撮影対象でワークフローを開始します。")

        except Exception as e:
            return self.show_error(f"ワークフロー開始エラー: {e}")

        # ワークフロースレッドを初期化・起動
        self.workflow_thread = WorkflowThread(self.workflow, self)
        self.workflow_thread.log_message.connect(self.log)
        self.workflow_thread.workflow_error.connect(self.on_device_error)
        self.workflow_thread.workflow_finished.connect(self.on_workflow_finished)
        
        self.workflow_thread.start()
        self.panel.set_ui_state_workflow_running()

    @Slot()
    def on_stop_workflow(self):
        if self.workflow_thread and self.workflow_thread.isRunning():
            self.log("[App] ワークフローに停止を要求します...")
            self.workflow_thread.stop()
            # UI は on_workflow_finished() で更新される

    @Slot()
    def on_manual_capture(self):
        if not self.camera_thread or not self.camera_thread.isRunning():
            return self.show_error("カメラスレッドが実行されていません。")
        if not hasattr(self, 'output_dir') or not self.output_dir:
            return self.show_error("先に「画像保存先」を設定してください。")
        if not self.workflow or not self.workflow.stage.is_connected():
            return self.show_error("ステージが接続されていません。")

        try:
            pos = self.workflow.stage.get_position()
            # (X軸反転修正後の座標が返るはず)
            filename = f"manual_X{pos[0]:.3f}_Y{pos[1]:.3f}_{int(time.time())}.png"
            save_path = os.path.join(self.output_dir, filename)
            
            # カメラスレッドに撮影を依頼
            self.camera_thread.capture_now(save_path)
            self.log(f"[App] 手動撮影を要求しました: {save_path}")
            
        except Exception as e:
            self.show_error(f"手動撮影エラー: {e}")

    @Slot()
    def on_export_csv(self):
        if not self.workflow:
            self.workflow = ImagingWorkflow("dummy", "dummy") # (CSV書き込みのためだけに仮作成)
            
        csv_path = self.panel.csv_export_edit.findChild(QLineEdit).text()
        if not csv_path:
            return self.show_error("先に「CSV保存先」を設定してください。")
        
        # マップファイルが読み込まれているか確認
        if not self.workflow.config.map_data:
            # 読み込まれていなければ、パスから読み込む
            map_path = self.panel.map_path_edit.findChild(QLineEdit).text()
            if not map_path:
                return self.show_error("先に「基板種類ファイル」を読み込んでください。")
            try:
                self.on_set_map_path(map_path)
            except Exception as e:
                return self.show_error(f"CSVエクスポートのためのファイル読込失敗: {e}")

        try:
            self.workflow.config.export_map_to_csv(csv_path)
            self.log(f"[App] CSVをエクスポートしました: {csv_path}")
        except Exception as e:
            self.show_error(f"CSVエクスポート失敗: {e}")


    # --- スロット (スレッドからの通知) ---

    @Slot(str)
    def log(self, message: str):
        """ アプリケーションのメインログ（ControlPanel に表示）"""
        self.panel.log_message(message)

    @Slot(str)
    def on_device_error(self, message: str):
        """ CameraThread や WorkflowThread からのエラー通知 """
        self.log(f"エラー: {message}")
        QMessageBox.warning(self, "デバイスエラー", message)
        
        # (重大度に応じてUI状態を変更)
        # self.panel.set_ui_state_disconnected()

    @Slot()
    def on_workflow_finished(self):
        """ WorkflowThread が完了したときの処理 """
        self.log("[App] ワークフローが完了または停止しました。")
        self.panel.set_ui_state_connected() # UIを「接続済み」状態に戻す
        self.workflow_thread = None # スレッドを破棄

    # --- アプリケーション終了処理 ---

    def closeEvent(self, event: QCloseEvent):
        """ ウィンドウが閉じられるときの処理 """
        self.log("[App] 終了処理を開始します...")
        
        # 1. ワークフロースレッドを停止
        if self.workflow_thread and self.workflow_thread.isRunning():
            self.log("[App] ワークフローを停止しています...")
            self.workflow_thread.stop()
            self.workflow_thread.wait(2000) # 最大2秒待機
        
        # 2. カメラスレッドを停止
        if self.camera_thread and self.camera_thread.isRunning():
            self.log("[App] カメラを停止しています...")
            self.camera_thread.stop()
            self.camera_thread.wait(3000) # 最大3秒待機

        # 3. ワークフロー (ステージ) をシャットダウン
        # (注: camera は camera_thread が切断するので、ここでは stage のみ)
        if self.workflow and self.workflow.stage.is_connected():
            self.log("[App] ステージを切断しています...")
            self.workflow.stage.disconnect()
            
        self.log("[App] 終了します。")
        event.accept()