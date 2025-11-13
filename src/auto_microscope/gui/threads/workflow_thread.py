from PySide6.QtCore import QThread, Signal, Slot
from ...services.imaging_workflow import ImagingWorkflow
from ...core.exceptions import AutoMicroscopeError

class WorkflowThread(QThread):
    """
    (Ver2.2 修正)
    単一ターゲットへの移動のみを担当するスレッド。
    MainWindow の move_to_next_target() によって、ターゲット1つごとに
    インスタンスが作成され、実行される。
    """

    # --- シグナル定義 ---
    log_message = Signal(str)
    workflow_error = Signal(str)
    
    # (Ver2.2 修正) v1 の workflow_finished は不要
    # workflow_finished = Signal() 
    
    # (Ver2.2 追加) 単一移動の完了を MainWindow に通知する
    move_finished = Signal(dict) 

    def __init__(self, workflow: ImagingWorkflow, parent=None):
        super().__init__(parent)
        self.workflow = workflow
        self._is_running = False # stop() のフラグ
        self._target_to_move: dict | None = None # (v2.2 追加)

    @Slot(dict)
    def move_to_target(self, target: dict):
        """ 
        (Ver2.2 追加) 
        MainWindow から移動対象を受け取り、スレッドを開始 (run) するためのスロット 
        """
        if not self.workflow or not self.workflow._is_initialized:
            self.workflow_error.emit("ワークフローが初期化されていません。")
            return
        
        self._target_to_move = target
        self._is_running = True # 実行フラグを立てる
        self.start() # run() を起動する

    def run(self):
        """ 
        (Ver2.2 修正) 
        単一ターゲットへの移動処理のみを実行 
        """
        
        # stop() が先に呼ばれた場合
        if not self._is_running:
            return 
            
        if not self._target_to_move:
            self.workflow_error.emit("WorkflowThread: 移動対象が設定されていません。")
            return

        target = self._target_to_move
        try:
            self.log_message.emit(f"[WorkflowThread] ターゲット ID: {target['id']} へ移動します...")
            
            # imaging_workflow の単一移動メソッドを呼び出す
            self.workflow.move_to_target(target) 
            
            # stop() が移動中に呼ばれた場合
            if not self._is_running: 
                self.log_message.emit("[WorkflowThread] 移動中に停止要求を受けました。")
                return

            self.log_message.emit(f"[WorkflowThread] ID {target['id']} 移動完了。")
            
            # MainWindow に完了を通知
            self.move_finished.emit(target) 

        except Exception as e:
            # エラーが発生した場合
            self.workflow_error.emit(f"WorkflowThread エラー (ID: {target['id']}): {e}")
        finally:
            self._is_running = False # 処理終了

    @Slot()
    def stop(self):
        """ 
        (Ver2.2) 
        移動処理を中断させるためのフラグを立てる 
        """
        self.log_message.emit("[WorkflowThread] 停止リクエストを受信しました。")
        self._is_running = False
        
        # (オプション)
        # もし StageControl に self.stage.stop_move() のような
        # 緊急停止メソッドがあれば、ここで呼び出す
        # if self.workflow and self.workflow.stage:
        #     self.workflow.stage.stop_move()