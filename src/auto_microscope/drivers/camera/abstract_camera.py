import numpy as np
from abc import ABC, abstractmethod

class AbstractCamera(ABC):
    """
    全てのカメラ実装が従うべき抽象基底クラス(インターフェース)。
    """

    @abstractmethod
    def connect(self) -> None:
        """
        カメラに接続します。
        失敗した場合は例外 (例: core.exceptions.CameraConnectionError) を送出します。
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        カメラとの接続を切断します。
        """
        pass

    @abstractmethod
    def get_frame(self) -> np.ndarray:
        """
        カメラから1フレーム分の画像を取得します。
        画像は numpy 配列 (OpenCV互換) として返します。

        :return: 画像データ (np.ndarray)
        """
        pass

    @abstractmethod
    def set_exposure(self, exposure_ms: float) -> None:
        """
        露光時間を設定します (ミリ秒)。
        """
        pass

    @abstractmethod
    def get_exposure(self) -> float:
        """
        現在の露光時間 (ミリ秒) を取得します。
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        カメラが現在接続されているか確認します。
        """
        pass