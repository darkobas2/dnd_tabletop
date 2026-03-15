from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem
from PySide6.QtGui import QPixmap, QColor, QPen, QKeyEvent, QPainter
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer

class TokenItem(QGraphicsPixmapItem):
    def __init__(self, pixmap, name, grid_size, token_scale):
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.grid_size = grid_size
        self.name = name
        
        # Calculate base size to fit ~80% of a square
        base_size = grid_size * 0.8
        # Get the current pixmap size
        pw = self.pixmap().width()
        ph = self.pixmap().height()
        # Initial scale to fit square, multiplied by user scale
        initial_scale = base_size / max(pw, ph)
        self.setScale(initial_scale * token_scale)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            # Snap to grid center
            # Width/Height are scaled here
            sw = self.pixmap().width() * self.scale()
            sh = self.pixmap().height() * self.scale()
            
            gx = (new_pos.x() // self.grid_size) * self.grid_size + self.grid_size / 2 - sw / 2
            gy = (new_pos.y() // self.grid_size) * self.grid_size + self.grid_size / 2 - sh / 2
            return QPointF(gx, gy)
        return super().itemChange(change, value)

class MapViewer(QGraphicsView):
    def __init__(self, map_path, width_sq, height_sq, tokens_to_add, map_scale=1.0):
        super().__init__()
        self.setBackgroundBrush(QColor(0, 0, 0)) # Black background for the "void"
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        self.base_pixmap = QPixmap(map_path)
        # Apply global scale factor to the whole map image
        self.map_pixmap = self.base_pixmap.scaled(
            self.base_pixmap.width() * map_scale,
            self.base_pixmap.height() * map_scale,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        self.map_item = self.scene.addPixmap(self.map_pixmap)
        self.scene.setSceneRect(self.map_pixmap.rect())
        
        self.width_sq = width_sq
        self.height_sq = height_sq
        self.grid_size = self.map_pixmap.width() / width_sq
        
        self.grid_visible = True
        self.grid_items = []
        self._draw_grid()
        
        # Add tokens
        for token_data, (count, token_scale) in tokens_to_add.items():
            pixmap = QPixmap(token_data.path)
            for i in range(count):
                token = TokenItem(pixmap, token_data.name, self.grid_size, token_scale)
                self.scene.addItem(token)
                # Spread them out slightly at start
                token.setPos(i * self.grid_size, 0)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Initial fit
        QTimer.singleShot(100, self.fit_to_screen)
        
    def fit_to_screen(self):
        self.fitInView(self.map_item, Qt.KeepAspectRatio)

    def _draw_grid(self):
        pen = QPen(QColor(255, 255, 255, 50)) # Subtle light grid on dark maps
        pen.setWidth(1)
        
        mw = self.map_pixmap.width()
        mh = self.map_pixmap.height()

        # Vertical lines - based on width_sq
        for i in range(self.width_sq + 1):
            x = i * self.grid_size
            if x > mw: x = mw
            line = self.scene.addLine(x, 0, x, mh, pen)
            self.grid_items.append(line)
            
        # Horizontal lines - based on how many fit in height
        y = 0
        while y <= mh + 0.1:
            line = self.scene.addLine(0, y, mw, y, pen)
            self.grid_items.append(line)
            y += self.grid_size
            if self.grid_size <= 0: break

    def toggle_grid(self):
        self.grid_visible = not self.grid_visible
        for item in self.grid_items:
            item.setVisible(self.grid_visible)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_G:
            self.toggle_grid()
        elif event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
