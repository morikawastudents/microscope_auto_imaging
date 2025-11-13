import sys
import time
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QMessageBox, QLineEdit, QVBoxLayout
)
from PySide6.QtCore import Slot, QCoreApplication, QSettings, QTimer
from PySide6.QtGui import QCloseEvent

# --- プロジェクトのコンポーネントをインポート ---
from ..services.imaging_workflow import ImagingWorkflow
from ..core.exceptions import AutoMicroscopeError

# --- GUIコンポーネントをインポート ---
from .widgets.camera_view_widget import CameraViewWidget
from .widgets.control_panel_widget import ControlPanelWidget
from .widgets.map_display_widget import MapDisplayWidget
from .threads.camera_thread import CameraThread
from .threads.workflow_thread import WorkflowThread
from .utils import populate_com_ports

class MainWindow(QMainWindow):
    USE_DUMMY_DEVICES = True  # デバッグ用にダミーデバイスを使用するかどうか

    def __init__(self):
        super().__init__()
        self.setWindowTitle("顕微鏡自動撮影システム v2.2 (Map Display)")
        self.setGeometry(100, 100, 1300, 800)

        self.settings = QSettings()
        self.workflow: ImagingWorkflow | None = None
        self.camera_thread: CameraThread | None = None
        self.workflow_thread: WorkflowThread | None = None
        self.output_dir: str = ""
        
        self.target_list: list[dict] = []
        self.current_target_index: int = -1
        self.is_stage_busy: bool = False # ステージ移動中フラグ

        self.init_ui()
        self.connect_signals()

            # --- ステージ位置ポーリング用タイマー ---
        self.stage_poll_timer = QTimer(self)
        self.stage_poll_timer.timeout.connect(self.poll_stage_position)
        self.stage_poll_timer.setInterval(100)

        self.start_camera_thread()
        self.log("[App] アプリケーションを起動しました。")
        self.load_settings() 
        self.panel.refresh_ports_requested.emit() 

    def init_ui(self):
        """ UIレイアウト変更 (左側を上下に分割) """
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- 左側 (カメラとマップ) ---
        left_pane_layout = QVBoxLayout()
        
        # カメラビュー
        self.camera_view = CameraViewWidget(self)
        left_pane_layout.addWidget(self.camera_view, 3) # 伸縮比率 3
        
        # マップビュー
        self.map_display = MapDisplayWidget(self)
        left_pane_layout.addWidget(self.map_display, 2) # 伸縮比率 2
        
        main_layout.addLayout(left_pane_layout, 2) # 左側全体の伸縮比率 2

        # --- 右側 (操作パネル) ---
        self.panel = ControlPanelWidget(self)
        main_layout.addWidget(self.panel, 1) # 右側全体の伸縮比率 1

    def connect_signals(self):
        """ ウィジェットとスレッド間のシグナル/スロットを接続 """
        
        # 1. ControlPanel -> MainWindow
        self.panel.refresh_ports_requested.connect(self.on_refresh_ports)
        self.panel.connect_stage_requested.connect(self.on_connect_stage)
        self.panel.set_origin_requested.connect(self.on_set_origin)
        self.panel.start_workflow_requested.connect(self.on_start_workflow)
        self.panel.stop_workflow_requested.connect(self.on_stop_workflow)
        self.panel.load_layout_requested.connect(self.on_set_layout_path)
        self.panel.load_map_requested.connect(self.on_set_map_path)
        self.panel.output_dir_requested.connect(self.on_set_output_dir)
        self.panel.manual_capture_requested.connect(self.on_manual_capture)
        self.panel.csv_export_requested.connect(self.on_export_csv)
        
    def start_camera_thread(self):
        if self.camera_thread and self.camera_thread.isRunning():
            return
        driver = "dummy" if self.USE_DUMMY_DEVICES else "telicam"
        self.camera_thread = CameraThread(driver_type=driver, parent=self)
        
        self.camera_thread.frame_ready.connect(self.camera_view.update_camera_view)
        self.camera_thread.focus_score_ready.connect(self.camera_view.update_focus_score)
        self.camera_thread.camera_error.connect(self.on_device_error)
        
        self.log(f"[App] カメラスレッド (Driver: {driver}) を起動します...")
        self.camera_thread.start()

    def show_error(self, message: str):
        self.log(f"[エラー] {message}")
        QMessageBox.warning(self, "エラー", message)

    # --- ステージ位置ポーリング ---
    @Slot()
    def poll_stage_position(self):
        """ QTimer によって定期的に呼び出され、ステージ位置をマップに反映 """
        if self.is_stage_busy:
            return
        
        if self.workflow and self.workflow.stage.is_connected():
            try:
                x, y = self.workflow.stage.get_position()
                self.map_display.update_stage_position(x, y)
            except Exception as e:
                # 頻繁にエラーログが出ないよう、タイマーを止める
                self.stage_poll_timer.stop()
                self.show_error(f"ステージ位置のポーリングに失敗: {e}")

    # --- スロット (ControlPanel からの要求) ---

    @Slot()
    def on_refresh_ports(self):
        if self.USE_DUMMY_DEVICES:
            self.panel.com_port_combo.clear()
            self.panel.com_port_combo.addItem("ダミーモード")
            self.panel.com_port_combo.setEnabled(False)
            self.panel.btn_refresh_ports.setEnabled(False)
            self.panel.btn_connect_stage.setEnabled(True) 
            self.panel.btn_connect_stage.setText("ステージ接続 (Dummy)")
            return
        self.log("[App] COMポートを更新しています...")
        last_port = self.panel.com_port_combo.currentData() 
        try:
            detected = populate_com_ports(self.panel.com_port_combo)
            self.log(f"[App] {len(detected)} 件のポートを検出しました。")
            if last_port in detected:
                index = self.panel.com_port_combo.findData(last_port)
                if index >= 0:
                    self.panel.com_port_combo.setCurrentIndex(index)
                    self.log(f"[App] 前回のポート ({last_port}) を再選択しました。")
        except Exception as e:
            self.show_error(f"COMポートの列挙に失敗しました: {e}")

    @Slot(str)
    def on_connect_stage(self, com_port: str):
        if self.workflow and self.workflow._is_initialized:
            self.log("[App] すでに接続済みです。")
            return
        self.log("[App] システムの初期化を開始します...")
        try:
            cam_driver = "dummy" if self.USE_DUMMY_DEVICES else "telicam"
            stage_driver = "dummy" if self.USE_DUMMY_DEVICES else "prior"
            self.workflow = ImagingWorkflow(
                camera_driver=cam_driver,
                stage_driver=stage_driver,
                com_port_str=com_port 
            )
            self.log("[App] ステージに接続しています...")
            self.workflow.stage.connect()
            if not self.camera_thread or not self.camera_thread.isRunning():
                 self.log("[App] 警告: カメラスレッドが実行されていません。")
            self.workflow._is_initialized = True 
            self.log("[App] ステージ接続成功。")
            self.panel.set_ui_state_connected()
            self.stage_poll_timer.start()
        except Exception as e:
            self.show_error(f"ステージの接続に失敗しました: {e}")
            self.workflow = None 

    @Slot()
    def on_set_origin(self):
        if not self.workflow:
            return self.show_error("ステージが接続されていません。")
        try:
            self.workflow.set_stage_origin()
            self.log("[App] ステージの原点を設定しました。")
            self.poll_stage_position()
        except Exception as e:
            self.show_error(f"原点設定エラー: {e}")

    @Slot(str)
    def on_set_layout_path(self, path: str):
        if not self.workflow: self._init_temp_workflow() # (追加)
        self.workflow.config.load_layout(path)
        self.log(f"[App] 基板位置ファイルを読み込みました: {path}")
        self._update_map_targets() # (追加) マップを更新

    @Slot(str)
    def on_set_map_path(self, path: str):
        if not self.workflow: self._init_temp_workflow() # (追加)
        self.workflow.config.load_map(path)
        self.log(f"[App] 基板種類ファイルを読み込みました: {path}")
        self._update_map_targets() # (追加) マップを更新
            
    def _init_temp_workflow(self):
        """ (追加) ステージ未接続時にConfig読み込みを許可する """
        if not self.workflow:
            try:
                self.workflow = ImagingWorkflow("dummy", "dummy")
                self.workflow._is_initialized = False # (接続はしていない)
            except Exception as e:
                self.show_error(f"仮のWorkflow作成に失敗: {e}")

    def _update_map_targets(self):
        """ (追加) Configが両方揃ったら、マップ表示を更新 """
        if self.workflow and self.workflow.config.is_ready():
            try:
                targets = self.workflow.config.get_target_positions()
                self.map_display.update_targets(targets)
                self.log(f"[App] マップ表示を更新しました ({len(targets)}件)。")
            except Exception as e:
                self.show_error(f"マップ表示の更新に失敗: {e}")

    @Slot(str)
    def on_set_output_dir(self, path: str):
        self.output_dir = path
        self.log(f"[App] 保存先を設定: {path}")

    @Slot()
    def on_start_workflow(self):
        """ ワークフローを開始 """
        if not self.workflow or not self.workflow._is_initialized:
            return self.show_error("ステージが接続されていません。")
        if not self.workflow.config.is_ready():
            return self.show_error("設定ファイル（位置・種類）が読み込まれていません。")
            
        try:
            self.target_list = self.workflow.get_targets()
            if not self.target_list:
                raise AutoMicroscopeError("撮影対象が見つかりませんでした。")
            
            self.log(f"[App] {len(self.target_list)} 件の撮影対象でワークフローを開始します。")
            self.current_target_index = -1 # (リセット)
            self.panel.set_ui_state_workflow_running()
            
            # 最初のターゲットへ移動
            self.move_to_next_target() 
            
        except Exception as e:
            return self.show_error(f"ワークフロー開始エラー: {e}")

    def move_to_next_target(self):
        """ 次のターゲットへ移動を指示 """
        self.current_target_index += 1
        
        if self.current_target_index >= len(self.target_list):
            self.log("[App] 全てのターゲットへの移動が完了しました。")
            self.on_workflow_finished() # (手動で完了処理)
            return

        target = self.target_list[self.current_target_index]
        self.log(f"[App] 次のターゲット (ID: {target['id']}) へ移動します...")
        self.map_display.highlight_target(target['id']) # (追加) マップをハイライト

        # ワークフロースレッドを初期化・起動
        self.workflow_thread = WorkflowThread(self.workflow, self)
        self.workflow_thread.log_message.connect(self.log)
        self.workflow_thread.workflow_error.connect(self.on_device_error)
        
        # 完了シグナル (move_finished) を接続
        self.workflow_thread.move_finished.connect(self.on_target_move_finished)

        # ステージ移動中フラグを立てる
        self.is_stage_busy = True
        
        self.workflow_thread.move_to_target(target) # 単発移動を指示

    @Slot()
    def on_stop_workflow(self):
        # ワークフロー停止要求の処理
        if self.workflow_thread and self.workflow_thread.isRunning():
            self.log("[App] ワークフローに停止を要求します...")
            self.workflow_thread.stop()
            self.workflow_thread.wait(2000)

        self.is_stage_busy = False # 念のためフラグ解除
        
        self.on_workflow_finished() # 即時停止

    @Slot()
    def on_manual_capture(self):
        # 手動撮影要求をカメラスレッドに送信
        if not self.camera_thread or not self.camera_thread.isRunning():
            return self.show_error("カメラスレッドが実行されていません。")
        if not self.output_dir:
            return self.show_error("先に「画像保存先」を設定してください。")
        if not self.workflow or not self.workflow.stage.is_connected():
            return self.show_error("ステージが接続されていません。")
        try:
            
            if self.current_target_index != -1:
                # ワークフロー内の手動撮影
                count = self.current_target_index + 1
                filename = f"{count}.jpg"
            else:
                # ワークフロー外の手動撮影
                pos = self.workflow.stage.get_position()
                filename = f"manual_X{pos[0]:.3f}_Y{pos[1]:.3f}_{int(time.time())}.png"


            save_path = os.path.join(self.output_dir, filename)
            self.camera_thread.capture_now(save_path)
            self.log(f"[App] 手動撮影を要求しました: {save_path}")

            if self.current_target_index != -1:
                self.log("[App] 撮影完了。次のターゲットへ移動します。")
                # 撮影ボタンを無効化
                self.panel.btn_manual_capture.setEnabled(False) 
                # 次のターゲットへ移動
                self.move_to_next_target()
        except Exception as e:
            self.show_error(f"手動撮影エラー: {e}")

    @Slot()
    def on_export_csv(self):
        # マップデータをCSVにエクスポート
        if not self.workflow:
            self._init_temp_workflow()
            
        csv_path = self.panel.csv_export_edit.text()
        if not csv_path:
            return self.show_error("先に「CSV保存先」を設定してください。")
        if not self.workflow.config.map_data:
            map_path = self.panel.map_path_edit.text()
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


    @Slot(str)
    def log(self, message: str):
        # ログメッセージをパネルに表示
        self.panel.log_message(message)

    @Slot(str)
    def on_device_error(self, message: str):
        # デバイスエラー発生時の処理
        self.show_error(message)
        if self.workflow_thread:
             self.on_workflow_finished()

    @Slot(dict)
    def on_target_move_finished(self, target: dict):
        # ターゲットへの移動が完了したときの処理

        self.is_stage_busy = False # 移動完了フラグ解除

        self.poll_stage_position() # 位置を更新

        self.log(f"[App] ID {target['id']} への移動完了。")
        
        self.log(f"[App] 撮影準備ができました。手動撮影ボタンを押してください。")

        self.panel.btn_manual_capture.setEnabled(True)

    @Slot()
    def on_workflow_finished(self):

        self.is_stage_busy = False # 念のためフラグ解除

        # ワークフローが完了または停止したときの処理
        self.log("[App] ワークフローが完了または停止しました。")
        self.panel.set_ui_state_connected()
        self.workflow_thread = None 
        self.target_list = []
        self.current_target_index = -1
        self.map_display.highlight_target(None) # ハイライト解除

    # --- QSettings メソッド  ---
    
    def load_settings(self):
        # 設定の読み込み処理
        self.log("[App] 設定を読み込み中...")
        self.settings.beginGroup("MainWindow")
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.panel.layout_path_edit.setText(self.settings.value("layout_path", ""))
        self.panel.map_path_edit.setText(self.settings.value("map_path", ""))
        self.panel.output_dir_edit.setText(self.settings.value("output_dir", ""))
        self.panel.csv_export_edit.setText(self.settings.value("csv_export_path", ""))
        last_port = self.settings.value("last_com_port", "")
        if last_port:
            self.panel.com_port_combo.addItem(f"前回({last_port})", last_port)
        self.settings.endGroup()

    def save_settings(self):
        # 設定の保存処理
        self.log("[App] 設定を保存中...")
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("layout_path", self.panel.layout_path_edit.text())
        self.settings.setValue("map_path", self.panel.map_path_edit.text())
        self.settings.setValue("output_dir", self.panel.output_dir_edit.text())
        self.settings.setValue("csv_export_path", self.panel.csv_export_edit.text())
        if self.workflow and self.workflow.stage.is_connected() and not self.USE_DUMMY_DEVICES:
             self.settings.setValue("last_com_port", self.panel.com_port_combo.currentData())
        self.settings.endGroup()

    # --- アプリケーション終了処理 ---

    def closeEvent(self, event: QCloseEvent):
        self.log("[App] 終了処理を開始します...")
        self.save_settings()
        if self.workflow_thread and self.workflow_thread.isRunning():
            self.log("[App] ワークフローを停止しています...")
            self.workflow_thread.stop()
            self.workflow_thread.wait(2000) 
        if self.camera_thread and self.camera_thread.isRunning():
            self.log("[App] カメラを停止しています...")
            self.camera_thread.stop()
            self.camera_thread.wait(3000) 
        if self.workflow and self.workflow.stage.is_connected():
            self.log("[App] ステージを切断しています...")
            self.workflow.stage.disconnect()
        self.log("[App] 終了します。")
        event.accept()