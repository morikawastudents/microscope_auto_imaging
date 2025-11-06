import pytest
from unittest.mock import MagicMock, patch
from auto_microscope.devices.stage_controller import StageControl
from auto_microscope.core.exceptions import StageConnectionError, StageError, ValueError

def test_stage_control_dummy_full_workflow():
    """
    StageControl (dummy) を使った基本的なワークフローをテスト
    """
    stage = None
    try:
        stage = StageControl(driver_type="dummy")
        assert not stage.is_connected()
        stage.connect()
        assert stage.is_connected()

        stage.set_origin()
        assert stage.get_position() == (0.0, 0.0)

        stage.move_abs(10.0, -20.0)
        assert stage.get_position() == (10.0, -20.0)

        stage.move_rel(-5.0, 5.0)
        assert stage.get_position() == (5.0, -15.0)

        stage.disconnect()
        assert not stage.is_connected()
    except Exception as e:
        assert False, f"StageControl (dummy) test failed: {e}"
    finally:
        if stage and stage.is_connected():
            stage.disconnect()

def test_stage_control_dummy_get_pos_when_disconnected():
    """
    切断状態で get_position を呼んだら StageError が発生するか
    """
    stage = StageControl(driver_type="dummy")
    # 修正: 実際のエラーメッセージに合わせる
    with pytest.raises(StageError, match="ステージが接続されていません"):
        stage.get_position()

def test_stage_control_prior_init_success(mocker):
    """
    "prior" を指定した際、PriorSdk が正しい引数でインスタンス化されるか
    """
    mock_sdk_class = mocker.patch('auto_microscope.devices.stage_controller.PriorSdk')
    mock_sdk_instance = MagicMock()
    mock_sdk_class.return_value = mock_sdk_instance

    stage = StageControl(driver_type="prior",
                         com_port_str="COM99",
                         dll_path="Test.dll")
    mock_sdk_class.assert_called_once_with(com_port_str="COM99",
                                           dll_path="Test.dll")
    assert stage.driver == mock_sdk_instance

    stage.connect()
    mock_sdk_instance.connect.assert_called_once()

def test_stage_control_prior_init_missing_kwargs():
    """
    "prior" を指定した際、com_port_str がないと ValueError が発生するか
    """
    with pytest.raises(ValueError, match="'com_port_str' がkwargsに必要です"):
        stage = StageControl(driver_type="prior")

def test_stage_control_invalid_driver():
    """
    存在しないドライバ名を指定したら ValueError が発生するか
    """
    with pytest.raises(ValueError, match="不明なステージドライバタイプ"):
        stage = StageControl(driver_type="non_existent_driver_xyz")