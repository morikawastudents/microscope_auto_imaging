import pytest
from PySide6.QtWidgets import QApplication

# (注) pytest-qt が必要: pip install pytest-qt

# (重要) 相対インポートが正しく動作するよう、
# auto_microscope パッケージ自体をインポート
import auto_microscope
from auto_microscope.gui.main_window import MainWindow

# 'qtbot' フィクスチャは pytest-qt が提供する
def test_main_window_startup(qtbot, mocker):
    """
    MainWindow がクラッシュせずに起動できるか、
    QSettings の読み込みをモックしてテストする。
    """
    
    # --- モック設定 ---
    # QSettings をモックし、value() が None (または空文字) を返すようにする
    mock_settings = mocker.MagicMock()
    mock_settings.value.return_value = ""
    mocker.patch('auto_microscope.gui.main_window.QSettings', return_value=mock_settings)
    
    # デバイスの初期化 (CameraThread, StageControl) をモック
    # (GUIのテストでは、ハードウェアに接続しない)
    mocker.patch('auto_microscope.gui.main_window.CameraThread')
    mocker.patch('auto_microscope.gui.main_window.ImagingWorkflow')
    
    # COMポート列挙をモック (空のリストを返す)
    mocker.patch('auto_microscope.gui.main_window.populate_com_ports', return_value=[])

    # --- テスト実行 ---
    
    # (QApplication が存在しない場合は作成)
    if not QApplication.instance():
        app = QApplication([])
    
    window = MainWindow()
    qtbot.addWidget(window) # qtbot にウィジェットを登録
    
    # ウィンドウが正常に表示されたか
    assert window.isVisible()
    assert window.windowTitle().startswith("顕微鏡自動撮影システム")
    
    # QSettings.value が呼び出されたか (起動時に load_settings が呼ばれたか)
    assert mock_settings.value.call_count > 0
    mock_settings.value.assert_any_call("geometry")
    mock_settings.value.assert_any_call("layout_path", "")

    # (クリーンアップ)
    window.close()