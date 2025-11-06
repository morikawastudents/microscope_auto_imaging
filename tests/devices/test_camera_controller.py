import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from auto_microscope.devices.camera_controller import CameraControl
from auto_microscope.core.exceptions import CameraConnectionError, CameraError

def test_camera_control_dummy_full_workflow():
    """
    CameraControl (dummy) を使った基本的なワークフローをテスト
    """
    cam = None
    try:
        cam = CameraControl(driver_type="dummy")
        assert not cam.is_connected()
        cam.connect()
        assert cam.is_connected()

        frame = cam.get_frame()
        assert isinstance(frame, np.ndarray)
        # 修正: DummyCameraは3チャンネル画像を返す仕様に変更
        assert frame.shape == (480, 640, 3)
        assert frame.dtype == np.uint8

        score = cam.calculate_focus_score(frame)
        assert isinstance(score, float)
        assert score >= 0.0

        cam.disconnect()
        assert not cam.is_connected()
    except Exception as e:
        assert False, f"CameraControl (dummy) test failed: {e}"
    finally:
        if cam and cam.is_connected():
            cam.disconnect()

def test_camera_control_dummy_get_frame_when_disconnected():
    """
    切断状態で get_frame を呼んだら CameraError が発生するか
    """
    cam = CameraControl(driver_type="dummy")
    with pytest.raises(CameraError, match="カメラが接続されていません"):
        cam.get_frame()

def test_camera_control_telicam_init_success(mocker):
    """
    "telicam" を指定した際、TeliCamSdk のインスタンス化が試みられるか (モック)
    """
    mock_sdk_class = mocker.patch('auto_microscope.devices.camera_controller.TeliCamSdk')
    mock_sdk_instance = MagicMock()
    mock_sdk_class.return_value = mock_sdk_instance

    cam = CameraControl(driver_type="telicam")
    mock_sdk_class.assert_called_once_with()
    assert cam.driver == mock_sdk_instance

    cam.connect()
    mock_sdk_instance.connect.assert_called_once()

def test_camera_control_telicam_init_import_error(mocker):
    """
    TeliCamSdk (pytelicam) がインストールされておらず ImportError が発生した場合、
    ImportError がそのまま送出されるか
    """
    mocker.patch('auto_microscope.devices.camera_controller.TeliCamSdk',
                 side_effect=ImportError("No module named 'pytelicam'"))
    with pytest.raises(ImportError):
        cam = CameraControl(driver_type="telicam")

def test_camera_control_invalid_driver():
    """
    存在しないドライバ名を指定したら ValueError が発生するか
    """
    with pytest.raises(ValueError, match="不明なカメラドライバタイプ"):
        cam = CameraControl(driver_type="non_existent_driver_xyz")