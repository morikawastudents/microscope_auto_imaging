import json
import csv
import os
from ..core.exceptions import ConfigError # (更新) カスタム例外をインポート

class ConfigManager:
    """ 
    基板位置、基板種類のJSONファイルの読み書きと、CSVエクスポートを担当 
    (src/auto_microscope/services/config_service.py)
    """
    def __init__(self):
        self.layout_data = {} # 基板位置 {"1": {"x": 10, "y": 5}, ...}
        self.map_data = {}    # 基板種類 {"1": "TypeA", "2": "TypeB", ...}

    def load_layout(self, filepath: str) -> None:
        """
        基板位置ファイル (JSON) を読み込みます。
        :param filepath: substrate_layout.json へのパス
        :raises ConfigError: ファイルが存在しない、JSON形式が不正、中身が辞書でない場合
        """
        if not filepath or not os.path.exists(filepath):
            raise ConfigError(f"基板位置ファイルが見つかりません: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.layout_data = json.load(f)
            if not isinstance(self.layout_data, dict):
                raise ConfigError("基板位置ファイルはJSONオブジェクト（辞書）である必要があります。")
        except json.JSONDecodeError as e:
            raise ConfigError(f"基板位置ファイルのJSONパースに失敗: {e}")
        except Exception as e:
            raise ConfigError(f"基板位置ファイルの読み込み中に予期せぬエラー: {e}")

    def load_map(self, filepath: str) -> None:
        """
        基板種類マップファイル (JSON) を読み込みます。
        :param filepath: substrate_map.json へのパス
        :raises ConfigError: ファイルが存在しない、JSON形式が不正、中身が辞書でない場合
        """
        if not filepath or not os.path.exists(filepath):
            raise ConfigError(f"基板種類ファイルが見つかりません: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.map_data = json.load(f)
            if not isinstance(self.map_data, dict):
                raise ConfigError("基板種類ファイルはJSONオブジェクト（辞書）である必要があります。")
        except json.JSONDecodeError as e:
            raise ConfigError(f"基板種類ファイルのJSONパースに失敗: {e}")
        except Exception as e:
            raise ConfigError(f"基板種類ファイルの読み込み中に予期せぬエラー: {e}")
            
    def is_ready(self) -> bool:
        """ レイアウトとマップの両方が読み込まれているか確認 """
        return bool(self.layout_data) and bool(self.map_data)

    def get_target_positions(self) -> list[dict]:
        """
        map_data に存在する ID (値が null や空でない) の座標リストを返す
        """
        if not self.is_ready():
            raise ConfigError("基板位置ファイルまたは種類ファイルが読み込まれていません。")
            
        targets = []
        
        # IDを数値としてソート（推奨）
        try:
            sorted_ids = sorted(self.map_data.keys(), key=lambda x: int(x))
        except ValueError:
            # "1", "2", "SiteA" のような混合IDの場合は単純ソート
            sorted_ids = sorted(self.map_data.keys())
        
        for substrate_id in sorted_ids:
            # (修正) map_data.get(substrate_id) で値の存在 (Noneや空文字でないか) をチェック
            pattern_type = self.map_data.get(substrate_id)
            
            if pattern_type: # 種類がnullや空文字でない場合
                if substrate_id in self.layout_data:
                    pos = self.layout_data[substrate_id]
                    if "x" in pos and "y" in pos:
                        targets.append({
                            "id": substrate_id,
                            "type": pattern_type,
                            "x": pos["x"],
                            "y": pos["y"]
                        })
                    else:
                        print(f"警告: ID {substrate_id} の位置データに 'x' または 'y' がありません。スキップします。")
                else:
                    print(f"警告: ID {substrate_id} (種類: {pattern_type}) はマップにありますが、位置ファイルに存在しません。スキップします。")
            else:
                 print(f"情報: ID {substrate_id} は基板が設定されていない (null または空) ためスキップします。")
        
        return targets

    def export_map_to_csv(self, filepath: str) -> None:
        """ (Ver1) 現在の基板種類マップをCSVにエクスポート """
        if not self.map_data:
            raise ConfigError("エクスポートする基板種類データがありません。")
            
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Substrate_ID", "Pattern_Type"]) # ヘッダー
                
                try:
                    sorted_ids = sorted(self.map_data.keys(), key=lambda x: int(x))
                except ValueError:
                    sorted_ids = sorted(self.map_data.keys())
                    
                for substrate_id in sorted_ids:
                    writer.writerow([substrate_id, self.map_data.get(substrate_id, "")]) # (修正) .get()で安全にアクセス
            print(f"CSVエクスポート成功: {filepath}")
        except IOError as e:
            raise ConfigError(f"CSVファイルへの書き込みに失敗しました: {e}")
        except Exception as e:
            raise ConfigError(f"CSVエクスポート中に予期せぬエラー: {e}")