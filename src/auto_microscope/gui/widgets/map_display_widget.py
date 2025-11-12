import sys
from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPaintEvent
from PySide6.QtCore import Qt, Slot, QPointF, QRectF

class MapDisplayWidget(QWidget):
    """
    基板のレイアウト、種類、現在のステージ位置を視覚的に表示するウィジェット。
    """
    
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        
        # 描画データ
        self.targets = [] # ConfigManager.get_target_positions() のリスト
        self.layout_bounds = QRectF(0, 0, 100, 100) # 基板全体の範囲 (mm)
        self.current_stage_pos = QPointF(0, 0) # 現在のステージ位置 (mm)
        self.current_target_id = None # ハイライト対象のID
        
        # 描画設定
        self.padding = 20 # (px)
        self.point_radius = 5 # (px)
        
        # 基板タイプごとの色 (カスタマイズ可)
        self.type_colors = {
            "Type-A": QColor("#FF5733"), # (朱色)
            "Type-B": QColor("#33FF57"), # (緑色)
            "Type-C": QColor("#3357FF"), # (青色)
            "default": QColor("#AAAAAA") # (灰色)
        }

    def _calculate_bounds(self):
        """ ターゲットリストから描画範囲 (mm) を計算 """
        if not self.targets:
            self.layout_bounds = QRectF(0, 0, 100, 100)
            return

        min_x = min(t['x'] for t in self.targets)
        max_x = max(t['x'] for t in self.targets)
        min_y = min(t['y'] for t in self.targets)
        max_y = max(t['y'] for t in self.targets)
        
        # 軸が反転していても対応できるように
        if min_x > max_x: min_x, max_x = max_x, min_x
        if min_y > max_y: min_y, max_y = max_y, min_y
        
        # マージンを持たせる
        margin_x = (max_x - min_x) * 0.1 + 10
        margin_y = (max_y - min_y) * 0.1 + 10
        
        self.layout_bounds = QRectF(
            min_x - margin_x,
            min_y - margin_y,
            (max_x - min_x) + 2 * margin_x,
            (max_y - min_y) + 2 * margin_y
        )

    def _transform_coords(self, mm_pos: QPointF) -> QPointF:
        """ (mm) 座標を QWidget の (px) 座標に変換 """
        widget_rect = self.rect().adjusted(self.padding, self.padding, -self.padding, -self.padding)
        
        if not self.layout_bounds.isValid() or self.layout_bounds.width() == 0 or self.layout_bounds.height() == 0:
            return QPointF(widget_rect.center())

        # (mm) -> (px) スケール
        scale_x = widget_rect.width() / self.layout_bounds.width()
        scale_y = widget_rect.height() / self.layout_bounds.height()
        
        # (Y軸反転)
        # (mm) 座標系: Yは上に行くほど大
        # (px) 座標系: Yは下に行くほど大
        
        px_x = widget_rect.left() + (mm_pos.x() - self.layout_bounds.left()) * scale_x
        px_y = widget_rect.bottom() - (mm_pos.y() - self.layout_bounds.top()) * scale_y
        
        return QPointF(px_x, px_y)

    # --- Public Slots ---

    @Slot(list)
    def update_targets(self, targets: list[dict]):
        """ (スロット) MainWindow からターゲットリストを受け取る """
        self.targets = targets
        self._calculate_bounds()
        self.update() # 再描画をトリガー

    @Slot(float, float)
    def update_stage_position(self, x_mm: float, y_mm: float):
        """ (スロット) MainWindow から現在のステージ位置 (mm) を受け取る """
        self.current_stage_pos = QPointF(x_mm, y_mm)
        self.update() # 再描画をトリガー

    @Slot(str)
    def highlight_target(self, target_id: str):
        """ (スロット) MainWindow から現在移動中のターゲットIDを受け取る """
        self.current_target_id = target_id
        self.update()

    # --- QPainter Event ---

    def paintEvent(self, event: QPaintEvent):
        """ ウィジェットが再描画されるときに呼び出される """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 背景を塗りつぶし
        painter.fillRect(self.rect(), QColor("#F0F0F0"))
        
        # 2. 描画領域の枠線
        widget_rect = self.rect().adjusted(self.padding, self.padding, -self.padding, -self.padding)
        painter.setPen(QPen(QColor("#AAAAAA"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(widget_rect)

        if not self.targets:
            painter.setPen(QColor("#888888"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "設定ファイルが読み込まれていません")
            return

        # 3. ターゲット (基板位置) を描画
        for target in self.targets:
            pos_mm = QPointF(target['x'], target['y'])
            pos_px = self._transform_coords(pos_mm)
            
            color_key = target.get('type', 'default')
            color = self.type_colors.get(color_key, self.type_colors['default'])
            
            # ハイライト処理
            if target['id'] == self.current_target_id:
                painter.setPen(QPen(QColor("yellow"), 4))
                painter.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))
                painter.drawEllipse(pos_px, self.point_radius + 2, self.point_radius + 2)
            else:
                painter.setPen(QPen(color, 2))
                painter.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))
                painter.drawEllipse(pos_px, self.point_radius, self.point_radius)
            
            # IDテキスト (オプション)
            # painter.drawText(pos_px + QPointF(5, 5), target['id'])

        # 4. 現在のステージ位置 (十字カーソル) を描画
        pos_px = self._transform_coords(self.current_stage_pos)
        painter.setPen(QPen(QColor("red"), 1, Qt.PenStyle.SolidLine))
        
        # 十字
        painter.drawLine(pos_px.x() - 10, pos_px.y(), pos_px.x() + 10, pos_px.y())
        painter.drawLine(pos_px.x(), pos_px.y() - 10, pos_px.x(), pos_px.y() + 10)
        
        painter.end()