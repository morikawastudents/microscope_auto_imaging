from PySide6.QtCore import QThread, Signal, Slot
from ...services.imaging_workflow import ImagingWorkflow
from ...core.exceptions import AutoMicroscopeError

class WorkflowThread(QThread):
    """
    時間のかかる自動撮影シーケンスをバックグラウンドで実行するスレッド。
    (ユーザーの AutomationWorker を QThread + ImagingWorkflow を使う形に修正)
    """
    
    # --- シグナル定義 ---
    log_message = Signal(str)
    workflow_finished = Signal()
    workflow_error = Signal(str)
    
    # (Ver2以降)
    # current_target_changed = Signal(dict)
    
    def __init__(self, workflow: ImagingWorkflow, parent=None):
        super().__init__(parent)
        self.workflow = workflow # MainWindow で初期化された実体
        self._is_running = False

    def run(self):
        """ (QThread) スレッドのメインループ (シーケンス実行) """
        if not self.workflow or not self.workflow._is_initialized:
            self.workflow_error.emit("ワークフローが初期化されていません。")
            return
            
        self._is_running = True
        
        try:
            self.log_message("[WorkflowThread] 自動シーケンスを開始します...")
            
            targets = self.workflow.get_targets()
            total = len(targets)
            
            # (Ver1) 原点設定はGUIスレッド (MainWindow) で実行済みと仮定
            # self.workflow.set_stage_origin()
            
            for i, target in enumerate(targets):
                if not self._is_running:
                    self.log_message("[WorkflowThread] ユーザーによって中断されました。")
                    break
                
                self.log_message("-" * 20)
                self.log_message(f"[WorkflowThread] ターゲット {i+1}/{total} (ID: {target['id']}) へ移動します...")
                
                self.workflow.move_to_target(target)
                
                if not self._is_running: # 移動完了後に再度チェック
                    break
                
                self.log_message(f"[WorkflowThread] ID {target['id']} (Type: {target['type']}) 移動完了。")
                
                # (Ver1) 移動のみ。撮影は手動。
                # (Ver2) ここでピント合わせと自動撮影
                
                # (GUI更新のため少し待機)
                self.msleep(100) 

            if self._is_running:
                self.log_message("[WorkflowThread] 全てのターゲットへの移動が完了しました。")
            
        except AutoMicroscopeError as e:
            self.workflow_error.emit(f"ワークフローエラー: {e}")
        except Exception as e:
            self.workflow_error.emit(f"予期せぬワークフローエラー: {e}")
        finally:
            self._is_running = False
            self.workflow_finished.emit()

    @Slot()
    def stop(self):
        """ (スロット) ワークフローを安全に停止する (次のターゲット移動前に) """
        self.log_message("[WorkflowThread] 停止リクエストを受信しました。")
        self._is_running = False