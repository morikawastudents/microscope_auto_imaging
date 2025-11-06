from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QComboBox, QFileDialog,
    QGroupBox, QSizePolicy
)
from PySide6.QtCore import Signal, Slot

class ControlPanelWidget(QWidget):
    """
    UIの右側（設定、接続、操作、ログ）を担当するウィジェット。
    実際のロジックは持たず、MainWindow にシグナルを送信する。
    """
    
    # --- MainWindow への通知シグナル ---
    load_layout_requested = Signal(str)
    load_map_requested = Signal(str)
    output_dir_requested = Signal(str)
    csv_export_requested = Signal(str)
    
    refresh_ports_requested = Signal()
    connect_stage_requested = Signal(str) # COMポート名を渡す
    
    set_origin_requested = Signal()
    start_workflow_requested = Signal()
    stop_workflow_requested = Signal()
    
    manual_capture_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        
        # (UIの見た目)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(400) # 幅を固定
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- 1. 設定ファイル グループ ---
        config_group = QGroupBox("1. 設定ファイル")
        config_layout = QVBoxLayout()
        
        self.layout_path_edit = self._create_file_input("基板位置 (JSON):")
        self.map_path_edit = self._create_file_input("基板種類 (JSON):")
        self.output_dir_edit = self._create_dir_input("画像保存先:")
        self.csv_export_edit = self._create_dir_input("CSV保存先:", is_save=True)

        config_layout.addLayout(self.layout_path_edit)
        config_layout.addLayout(self.map_path_edit)
        config_layout.addLayout(self.output_dir_edit)
        config_layout.addLayout(self.csv_export_edit)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # --- 2. ステージ接続 グループ ---
        stage_group = QGroupBox("2. ステージ接続")
        stage_layout = QVBoxLayout()

        self.com_port_combo = QComboBox()
        self.btn_refresh_ports = QPushButton("ポート更新")
        
        com_layout = QHBoxLayout()
        com_layout.addWidget(self.com_port_combo, 1)
        com_layout.addWidget(self.btn_refresh_ports)
        stage_layout.addLayout(com_layout)
        
        self.btn_connect_stage = QPushButton("ステージ接続")
        stage_layout.addWidget(self.btn_connect_stage)
        stage_group.setLayout(stage_layout)
        layout.addWidget(stage_group)

        # --- 3. 操作パネル グループ ---
        op_group = QGroupBox("3. 操作パネル")
        op_layout = QVBoxLayout()
        
        self.btn_set_origin = QPushButton("現在位置を原点に設定")
        self.btn_start_workflow = QPushButton("自動シーケンス開始")
        self.btn_stop_workflow = QPushButton("停止")
        self.btn_manual_capture = QPushButton("手動撮影 (Ver1)")
        
        op_layout.addWidget(self.btn_set_origin)
        op_layout.addWidget(self.btn_start_workflow)
        op_layout.addWidget(self.btn_stop_workflow)
        op_layout.addWidget(self.btn_manual_capture)
        op_group.setLayout(op_layout)
        layout.addWidget(op_group)

        # --- 4. 操作ログ グループ ---
        log_group = QGroupBox("操作ログ")
        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFixedHeight(150)
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch() # 上に詰める

        # --- シグナルを接続 ---
        self.btn_refresh_ports.clicked.connect(self.refresh_ports_requested)
        self.btn_connect_stage.clicked.connect(self._on_connect_stage_clicked)
        self.btn_set_origin.clicked.connect(self.set_origin_requested)
        self.btn_start_workflow.clicked.connect(self._on_start_workflow_clicked)
        self.btn_stop_workflow.clicked.connect(self.stop_workflow_requested)
        self.btn_manual_capture.clicked.connect(self._on_manual_capture_clicked)
        
        # --- 初期状態 ---
        self.set_ui_state_disconnected()

    # --- プライベート スロット (UI内部処理) ---
    
    def _on_connect_stage_clicked(self):
        com_port = self.com_port_combo.currentData() # "COM9" などを取得
        if com_port:
            self.connect_stage_requested.emit(com_port)
        else:
            self.log_message("エラー: 有効なCOMポートが選択されていません。")

    def _on_start_workflow_clicked(self):
        # 実行前にファイルパスが設定されているか確認
        if not self.layout_path_edit.findChild(QLineEdit).text():
            self.log_message("エラー: '基板位置' ファイルパスが未設定です。")
            return
        if not self.map_path_edit.findChild(QLineEdit).text():
            self.log_message("エラー: '基板種類' ファイルパスが未設定です。")
            return
        if not self.output_dir_edit.findChild(QLineEdit).text():
            self.log_message("エラー: '画像保存先' が未設定です。")
            return
            
        self.load_layout_requested.emit(self.layout_path_edit.findChild(QLineEdit).text())
        self.load_map_requested.emit(self.map_path_edit.findChild(QLineEdit).text())
        self.output_dir_requested.emit(self.output_dir_edit.findChild(QLineEdit).text())
        
        self.start_workflow_requested.emit()

    def _on_manual_capture_clicked(self):
        if not self.output_dir_edit.findChild(QLineEdit).text():
            self.log_message("エラー: '画像保存先' が未設定です。")
            return
        self.output_dir_requested.emit(self.output_dir_edit.findChild(QLineEdit).text())
        self.manual_capture_requested.emit()
        
    # --- UIヘルパー (ファイル参照) ---
    
    def _create_file_input(self, label_text: str) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit()
        layout.addWidget(line_edit)
        button = QPushButton("参照...")
        button.clicked.connect(lambda: self._browse_file(line_edit))
        layout.addWidget(button)
        return layout

    def _create_dir_input(self, label_text: str, is_save: bool = False) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addWidget(QLabel(label_text))
        line_edit = QLineEdit()
        layout.addWidget(line_edit)
        button = QPushButton("参照...")
        if is_save:
             button.clicked.connect(lambda: self._browse_save_path(line_edit, "CSV Files (*.csv)"))
        else:
             button.clicked.connect(lambda: self._browse_directory(line_edit))
        layout.addWidget(button)
        return layout

    def _browse_file(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "ファイルを開く", "", "JSON Files (*.json);;All Files (*)")
        if path:
            line_edit.setText(path)

    def _browse_directory(self, line_edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "ディレクトリを選択")
        if path:
            line_edit.setText(path)
            
    def _browse_save_path(self, line_edit: QLineEdit, filter: str):
        path, _ = QFileDialog.getSaveFileName(self, "保存先を選択", "", filter)
        if path:
            line_edit.setText(path)

    # --- パブリック スロット (MainWindowから呼ばれる) ---
    
    @Slot(str)
    def log_message(self, message: str):
        """ (スロット) MainWindow やスレッドからログメッセージを受け取る """
        self.log_text_edit.append(message)
        print(message) # コンソールにも出力

    @Slot()
    def set_ui_state_disconnected(self):
        """ UIを「未接続」状態にする """
        # 接続グループ
        self.com_port_combo.setEnabled(True)
        self.btn_refresh_ports.setEnabled(True)
        self.btn_connect_stage.setEnabled(True)
        self.btn_connect_stage.setText("ステージ接続")
        
        # 操作グループ
        self.btn_set_origin.setEnabled(False)
        self.btn_start_workflow.setEnabled(False)
        self.btn_stop_workflow.setEnabled(False)
        self.btn_manual_capture.setEnabled(False)

    @Slot()
    def set_ui_state_connected(self):
        """ UIを「接続完了」状態にする """
        # 接続グループ
        self.com_port_combo.setEnabled(False)
        self.btn_refresh_ports.setEnabled(False)
        self.btn_connect_stage.setEnabled(False)
        self.btn_connect_stage.setText("接続済み")
        
        # 操作グループ
        self.btn_set_origin.setEnabled(True)
        self.btn_start_workflow.setEnabled(True)
        self.btn_stop_workflow.setEnabled(False) # 実行中ではない
        self.btn_manual_capture.setEnabled(True)

    @Slot()
    def set_ui_state_workflow_running(self):
        """ UIを「ワークフロー実行中」状態にする """
        self.set_ui_state_connected() # 基本は接続済み状態
        
        # 操作ボタンを上書き
        self.btn_set_origin.setEnabled(False)
        self.btn_start_workflow.setEnabled(False)
        self.btn_stop_workflow.setEnabled(True)
        self.btn_manual_capture.setEnabled(False)