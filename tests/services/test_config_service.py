import pytest
import json
import csv
from unittest.mock import patch, mock_open, MagicMock

# テスト対象のクラスと、テストで使用する例外をインポート
from auto_microscope.services.config_service import ConfigManager
from auto_microscope.core.exceptions import ConfigError

# --- モックデータ ---

# load_layout 用のモックJSON文字列
MOCK_LAYOUT_JSON_STR = """
{
  "1": {"x": 10.0, "y": 5.0},
  "2": {"x": 20.0, "y": 5.0},
  "3": {"x": 30.0, "y": 5.0}
}
"""
MOCK_LAYOUT_DATA = json.loads(MOCK_LAYOUT_JSON_STR)

# load_map 用のモックJSON文字列
MOCK_MAP_JSON_STR = """
{
  "1": "Type-A",
  "2": "Type-B",
  "3": null
}
"""
MOCK_MAP_DATA = json.loads(MOCK_MAP_JSON_STR)

# --- テストクラス ---

@pytest.fixture
def config_manager():
    """ 各テストで使用する ConfigManager のインスタンスを生成するフィクスチャ """
    return ConfigManager()

def test_load_layout_success(mocker, config_manager):
    """
    load_layout が正常にJSONを読み込めるかテスト
    """
    # 'builtins.open' (Pythonの open() 関数) をモック
    mocker.patch("builtins.open", mock_open(read_data=MOCK_LAYOUT_JSON_STR))
    # 'os.path.exists' は常に True を返すようにモック
    mocker.patch("os.path.exists", return_value=True)
    
    config_manager.load_layout("dummy/path/layout.json")
    
    assert config_manager.layout_data == MOCK_LAYOUT_DATA

def test_load_map_success(mocker, config_manager):
    """
    load_map が正常にJSONを読み込めるかテスト
    """
    mocker.patch("builtins.open", mock_open(read_data=MOCK_MAP_JSON_STR))
    mocker.patch("os.path.exists", return_value=True)
    
    config_manager.load_map("dummy/path/map.json")
    
    assert config_manager.map_data == MOCK_MAP_DATA

def test_load_layout_file_not_found(config_manager):
    """
    指定されたファイルが見つからない場合に ConfigError が発生するか
    """
    # os.path.exists() が False を返すようにモック (mocker不要な場合)
    # mocker.patch("os.path.exists", return_value=False)
    
    with pytest.raises(ConfigError, match="見つかりません"):
        config_manager.load_layout("invalid/path/layout.json")

def test_load_map_invalid_json(mocker, config_manager):
    """
    JSON形式が不正な場合に ConfigError が発生するか
    """
    mocker.patch("builtins.open", mock_open(read_data="{invalid json"))
    mocker.patch("os.path.exists", return_value=True)
    
    with pytest.raises(ConfigError, match="JSONパースに失敗"):
        config_manager.load_map("dummy/path/map.json")

def test_load_layout_not_dict(mocker, config_manager):
    """
    JSONの中身が辞書 (オブジェクト) でない場合に ConfigError が発生するか
    """
    mocker.patch("builtins.open", mock_open(read_data="[1, 2, 3]")) # リストを返す
    mocker.patch("os.path.exists", return_value=True)
    
    with pytest.raises(ConfigError, match="JSONオブジェクト（辞書）である必要があります"):
        config_manager.load_layout("dummy/path/layout.json")

def test_get_target_positions_success(config_manager):
    """
    get_target_positions が正しくターゲットをフィルタリングして返すか
    """
    # テストデータを直接セットアップ
    config_manager.layout_data = {
        "1": {"x": 10, "y": 5},
        "2": {"x": 20, "y": 5},
        "3": {"x": 30, "y": 5}, # マップ側で null のためスキップされる
        "4": {"x": 40, "y": 5}  # マップに存在しないためスキップされる
    }
    config_manager.map_data = {
        "1": "TypeA",
        "3": None, # スキップ対象
        "2": "TypeB", # 順序がソートされるかのテスト
        "5": "TypeC"  # レイアウトに存在しないためスキップされる
    }
    
    targets = config_manager.get_target_positions()
    
    assert len(targets) == 2
    # "1", "2" の順にソートされていることを確認
    assert targets[0]["id"] == "1"
    assert targets[0]["type"] == "TypeA"
    assert targets[0]["x"] == 10
    
    assert targets[1]["id"] == "2"
    assert targets[1]["type"] == "TypeB"
    assert targets[1]["y"] == 5

def test_get_target_positions_not_ready(config_manager):
    """
    ファイル読み込み前に get_target_positions を呼ぶと ConfigError が発生するか
    """
    # layout_data のみロード
    config_manager.layout_data = {"1": {"x": 10, "y": 5}}
    
    with pytest.raises(ConfigError, match="読み込まれていません"):
        config_manager.get_target_positions()

def test_export_map_to_csv_success(mocker, config_manager):
    """
    export_map_to_csv が正しくCSVデータ（ヘッダーと行）を書き込むか
    """
    # データをセットアップ
    config_manager.map_data = {
        "2": "TypeB",
        "1": "TypeA"
    }
    
    # 'builtins.open' をモック
    mock_file = mock_open()
    mocker.patch("builtins.open", mock_file)
    
    # 'csv.writer' をモック
    mock_csv_writer = MagicMock()
    mocker.patch("csv.writer", return_value=mock_csv_writer)

    config_manager.export_map_to_csv("dummy/path/export.csv")
    
    # open が正しい引数で呼ばれたか
    mock_file.assert_called_once_with("dummy/path/export.csv", 'w', newline='', encoding='utf-8')
    
    # writer.writerow が呼ばれた回数と内容を確認
    assert mock_csv_writer.writerow.call_count == 3
    
    # 1回目の呼び出し (ヘッダー)
    mock_csv_writer.writerow.assert_any_call(["Substrate_ID", "Pattern_Type"])
    # 2回目の呼び出し (ID "1")
    mock_csv_writer.writerow.assert_any_call(["1", "TypeA"])
    # 3回目の呼び出し (ID "2")
    mock_csv_writer.writerow.assert_any_call(["2", "TypeB"])