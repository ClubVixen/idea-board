import sys
import os
import math
import json
import random
import base64
import uuid
from io import BytesIO

from PySide6.QtCore import (Qt, QPointF, QRectF, Signal, QObject, QTimer, QSize, 
                           QRect, QPoint, QByteArray, QBuffer, QIODevice)
from PySide6.QtGui import (QAction, QColor, QPainter, QPen, QBrush, QFont, 
                          QPixmap, QPainterPath, QCursor, QTransform, QFontDatabase,
                          QMouseEvent, QIcon, QImage, QWheelEvent)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, 
    QGraphicsItem, QGraphicsTextItem, QGraphicsPathItem, QGraphicsRectItem,
    QGraphicsPixmapItem, QGraphicsObject, QToolBar, QInputDialog, QFileDialog, QMenu, 
    QMessageBox, QGraphicsProxyWidget, QWidget, QVBoxLayout, QLabel, QFrame,
    QPushButton, QDialog, QRubberBand, QHBoxLayout, QStyle, QSizePolicy
)

# --- Helper Functions for Serialization ---

def pixmap_to_base64(pixmap):
    ba = QByteArray()
    buff = QBuffer(ba)
    buff.open(QIODevice.WriteOnly)
    pixmap.save(buff, "PNG")
    return ba.toBase64().data().decode()

def base64_to_pixmap(data_str):
    ba = QByteArray.fromBase64(data_str.encode())
    pixmap = QPixmap()
    pixmap.loadFromData(ba, "PNG")
    return pixmap

# --- Custom UI Components ---

class NodeButton(QGraphicsRectItem):
    """A button that sits on the graphics scene attached to a node."""
    def __init__(self, text, parent, callback, color=QColor(60, 60, 60)):
        super().__init__(-15, -15, 30, 30, parent) # Centered rect
        self.callback = callback
        self.text = text
        self.base_color = color
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(200, 200, 200), 1))
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptHoverEvents(True)
        self.setZValue(100) 
        
        # Label
        self.label = QGraphicsTextItem(text, self)
        font = QFont("Arial", 10, QFont.Bold)
        self.label.setFont(font)
        self.label.setDefaultTextColor(Qt.white)
        br = self.label.boundingRect()
        self.label.setPos(-br.width()/2, -br.height()/2)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self.base_color.lighter(150)))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self.base_color))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        # Capture press to ensure we receive release
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.isUnderMouse():
            # Defer callback to next event loop tick to avoid deleting self during event handling
            QTimer.singleShot(0, self.callback)
        event.accept()

class RotateHandle(QGraphicsRectItem):
    """A handle at the bottom of the node to rotate it."""
    def __init__(self, parent_node):
        super().__init__(-10, -10, 20, 20, parent_node)
        self.parent_node = parent_node
        self.setBrush(QBrush(QColor(200, 50, 50)))
        self.setPen(QPen(Qt.white, 2))
        self.setCursor(Qt.PointingHandCursor)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(100)
        
        # Icon visual (circular arrow)
        path = QPainterPath()
        path.addEllipse(-5, -5, 10, 10)
        self.icon = QGraphicsPathItem(path, self)
        self.icon.setBrush(Qt.NoBrush)
        self.icon.setPen(QPen(Qt.white, 1))
        
        self.is_rotating = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_rotating = True
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_rotating:
            node_pos = self.parent_node.scenePos()
            mouse_pos = event.scenePos()
            dx = mouse_pos.x() - node_pos.x()
            dy = mouse_pos.y() - node_pos.y()
            angle_rad = math.atan2(dy, dx)
            angle_deg = math.degrees(angle_rad)
            self.parent_node.setRotation(angle_deg - 90)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_rotating = False
        self.setCursor(Qt.PointingHandCursor)
        super().mouseReleaseEvent(event)

class ResizeHandle(QGraphicsRectItem):
    """Drag handle at the bottom-right corner of an image to resize it."""
    def __init__(self, parent_node):
        super().__init__(-8, -8, 16, 16, parent_node)
        self.parent_node = parent_node
        self.setBrush(QBrush(QColor(50, 120, 200)))
        self.setPen(QPen(Qt.white, 2))
        self.setCursor(Qt.SizeFDiagCursor)
        self.setZValue(100)
        self.setVisible(False)
        self.is_resizing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_resizing = True
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            local = self.parent_node.mapFromScene(event.scenePos())
            new_w = max(80, min(2000, abs(local.x()) * 2 - 40))
            self.parent_node.set_display_width(new_w)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_resizing = False
        super().mouseReleaseEvent(event)

class ImageStickyNote(QGraphicsRectItem):
    """A sticky note attached to an image."""
    def __init__(self, text="Note", x=0, y=0, parent=None):
        super().__init__(0, 0, 100, 60, parent)
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(255, 255, 200, 220)))
        self.setPen(QPen(QColor(0, 0, 0, 50)))
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setOpacity(0.5) 
        
        # High Z-Value to ensure it appears above the image
        self.setZValue(50)

        self.text_item = QGraphicsTextItem(text, self)
        self.text_item.setTextWidth(90)
        self.text_item.setFont(QFont("Arial", 8))
        self.text_item.setPos(5, 5)
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        
        # Close button (only visible on hover/select)
        self.close_btn = QGraphicsRectItem(85, 0, 15, 15, self)
        self.close_btn.setBrush(QBrush(Qt.red))
        self.close_btn.setPen(Qt.NoPen)
        self.close_btn.setVisible(False)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setZValue(1) # Above text
        
    def hoverEnterEvent(self, event):
        self.setOpacity(1.0)
        self.close_btn.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self.isSelected() and not self.text_item.hasFocus():
            self.setOpacity(0.5)
            self.close_btn.setVisible(False)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if self.close_btn.isUnderMouse():
            self.scene().removeItem(self)
        else:
            super().mousePressEvent(event)

    def to_dict(self):
        return {
            'text': self.text_item.toPlainText(),
            'x': self.pos().x(),
            'y': self.pos().y()
        }

# --- In-Place Cropping Overlay ---

class InPlaceCropOverlay(QGraphicsObject):
    cropCompleted = Signal(QRectF)
    cropCancelled = Signal()

    def __init__(self, target_rect, parent=None):
        super().__init__(parent)
        self.target_rect = target_rect 
        self.current_rect = QRectF(target_rect)
        self.current_rect.adjust(20, 20, -20, -20)
        
        self.handle_size = 20 # Increased for easier grabbing
        self.drag_corner = None 
        self.last_mouse_pos = QPointF()
        
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setZValue(2000)

        self.ok_btn = NodeButton("OK", self, self.emit_ok, QColor(50, 150, 50))
        self.cancel_btn = NodeButton("X", self, self.emit_cancel, QColor(150, 50, 50))
        self.layout_ui()

    def emit_ok(self):
        self.cropCompleted.emit(self.current_rect)

    def emit_cancel(self):
        self.cropCancelled.emit()

    def layout_ui(self):
        cx = self.current_rect.center().x()
        by = self.current_rect.bottom() + 25
        self.ok_btn.setPos(cx - 20, by)
        self.cancel_btn.setPos(cx + 20, by)

    def boundingRect(self):
        return self.target_rect.adjusted(-50, -50, 50, 150)

    def paint(self, painter, option, widget):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        path = QPainterPath()
        path.addRect(self.target_rect)
        path.addRect(self.current_rect)
        painter.drawPath(path)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(Qt.white, 2, Qt.DashLine))
        painter.drawRect(self.current_rect)

        painter.setBrush(Qt.white)
        painter.setPen(QPen(Qt.black, 1))
        rects = self.get_handle_rects()
        for r in rects:
            painter.drawRect(r)

    def get_handle_rects(self):
        r = self.current_rect
        hs = self.handle_size
        half = hs / 2
        return [
            QRectF(r.left()-half, r.top()-half, hs, hs), # TL
            QRectF(r.right()-half, r.top()-half, hs, hs), # TR
            QRectF(r.left()-half, r.bottom()-half, hs, hs), # BL
            QRectF(r.right()-half, r.bottom()-half, hs, hs), # BR
        ]

    def mousePressEvent(self, event):
        pos = event.pos()
        rects = self.get_handle_rects()
        
        # Priority check: Handles first
        for i, r in enumerate(rects):
            if r.contains(pos):
                self.drag_corner = i
                self.grabMouse() # Explicitly grab mouse to prevent View from stealing event
                event.accept()
                return
        
        # Then Body
        if self.current_rect.contains(pos):
            self.drag_corner = 4
            self.last_mouse_pos = pos
            self.grabMouse() # Explicitly grab mouse
            event.accept()
            return

        self.drag_corner = None
        event.ignore()

    def mouseMoveEvent(self, event):
        if self.drag_corner is None: 
            event.ignore()
            return
            
        pos = event.pos()
        r = self.current_rect
        min_size = 40
        tr = self.target_rect
        left, top, right, bottom = r.left(), r.top(), r.right(), r.bottom()

        if self.drag_corner == 0: # TL
            left = min(pos.x(), right - min_size)
            left = max(left, tr.left())
            top = min(pos.y(), bottom - min_size)
            top = max(top, tr.top())
        elif self.drag_corner == 1: # TR
            right = max(pos.x(), left + min_size)
            right = min(right, tr.right())
            top = min(pos.y(), bottom - min_size)
            top = max(top, tr.top())
        elif self.drag_corner == 2: # BL
            left = min(pos.x(), right - min_size)
            left = max(left, tr.left())
            bottom = max(pos.y(), top + min_size)
            bottom = min(bottom, tr.bottom())
        elif self.drag_corner == 3: # BR
            right = max(pos.x(), left + min_size)
            right = min(right, tr.right())
            bottom = max(pos.y(), top + min_size)
            bottom = min(bottom, tr.bottom())
        elif self.drag_corner == 4: # Move Body
            delta = pos - self.last_mouse_pos
            self.last_mouse_pos = pos
            
            # Robust Clamping
            dx = delta.x()
            dy = delta.y()
            
            # Check X bounds against target rect
            if r.left() + dx < tr.left(): dx = tr.left() - r.left()
            if r.right() + dx > tr.right(): dx = tr.right() - r.right()
            
            # Check Y bounds against target rect
            if r.top() + dy < tr.top(): dy = tr.top() - r.top()
            if r.bottom() + dy > tr.bottom(): dy = tr.bottom() - r.bottom()

            candidate = r.translated(dx, dy)
            left, top, right, bottom = candidate.left(), candidate.top(), candidate.right(), candidate.bottom()

        self.current_rect = QRectF(left, top, right - left, bottom - top)
        self.layout_ui()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_corner is not None:
            self.ungrabMouse() # Release mouse grab
        self.drag_corner = None
        event.accept()

# --- Nodes ---

class ConnectionLine(QGraphicsPathItem):
    def __init__(self, start_item, end_item):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setZValue(-10) 
        
        pen = QPen(QColor(200, 30, 30))
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        
        self.shadow = QGraphicsPathItem(self)
        shadow_pen = QPen(QColor(0, 0, 0, 100))
        shadow_pen.setWidth(5)
        self.shadow.setPen(shadow_pen)
        self.shadow.setZValue(-1)
        self.update_position()

    def update_position(self):
        if not self.scene(): return
        start_pos = self.start_item.sceneBoundingRect().center()
        end_pos = self.end_item.sceneBoundingRect().center()
        path = QPainterPath()
        path.moveTo(start_pos)
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        dist = math.sqrt(dx*dx + dy*dy)
        slack = min(dist * 0.2, 100)
        mid_x = (start_pos.x() + end_pos.x()) / 2
        mid_y = (start_pos.y() + end_pos.y()) / 2 + slack
        path.quadTo(mid_x, mid_y, end_pos.x(), end_pos.y())
        self.setPath(path)
        self.shadow.setPath(path)

class BaseNode(QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(-w/2, -h/2, w, h)
        self.setPos(x, y)
        self.w = w
        self.h = h
        self.uuid = str(uuid.uuid4())
        self.setFlags(QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemIsSelectable | 
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.connections = []
        self.is_cropping = False
        
        # Shadow
        self.shadow = QGraphicsRectItem(-w/2 + 5, -h/2 + 5, w, h, self)
        self.shadow.setBrush(QBrush(QColor(0, 0, 0, 100)))
        self.shadow.setPen(Qt.NoPen)
        self.shadow.setZValue(-1)
        
        # Controls Container (Centered at bottom edge)
        self.controls_y_offset = h/2 + 25 
        self.controls = QGraphicsRectItem(0, 0, 0, 0, self)
        self.controls.setPos(0, self.controls_y_offset)
        self.controls.setVisible(False)
        self.button_list = []
        
        # Rotate Handle (Below controls)
        self.rotate_handle = RotateHandle(self)
        self.rotate_handle.setPos(0, self.controls_y_offset + 35)
        self.rotate_handle.setVisible(False)
        
        # Add Standard Buttons
        self.add_button("L", self.start_link, QColor(50, 50, 150))
        self.add_button("X", self.delete_self, QColor(150, 50, 50))

    def add_button(self, text, callback, color):
        btn = NodeButton(text, self.controls, callback, color)
        self.button_list.append(btn)
        self.layout_buttons()
    
    def layout_buttons(self):
        count = len(self.button_list)
        btn_width = 30
        gap = 10
        total_w = count * btn_width + (count - 1) * gap
        start_x = -total_w / 2 + btn_width / 2
        for i, btn in enumerate(self.button_list):
            btn.setPos(start_x + i * (btn_width + gap), 0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            for line in self.connections:
                line.update_position()
        if change == QGraphicsItem.ItemSelectedChange:
            self.update_ui_visibility()
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event):
        self.update_ui_visibility(hovering=True)
        if not self.is_cropping:
            self.setZValue(50) 
            self.setScale(1.02)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.update_ui_visibility(hovering=False)
        if not self.is_cropping:
            self.setZValue(0 if not self.isSelected() else 50)
            self.setScale(1.0)
        super().hoverLeaveEvent(event)

    def update_ui_visibility(self, hovering=None):
        if self.is_cropping:
            self.controls.setVisible(False)
            self.rotate_handle.setVisible(False)
            return
        is_hovering = hovering if hovering is not None else self.isUnderMouse()
        visible = self.isSelected() or is_hovering
        self.controls.setVisible(visible)
        self.rotate_handle.setVisible(visible)

    def start_link(self):
        view = self.scene().views()[0]
        # Check if view is our custom class with the helper method
        if hasattr(view, 'start_connection'):
            view.start_connection(self)

    def delete_self(self):
        scene = self.scene()
        if not scene: return
        for line in self.connections:
            scene.removeItem(line)
            other = line.end_item if line.start_item == self else line.start_item
            if line in other.connections:
                other.connections.remove(line)
        scene.removeItem(self)

    def to_dict(self):
        return {
            'type': 'base',
            'uuid': self.uuid,
            'x': self.pos().x(),
            'y': self.pos().y(),
            'rotation': self.rotation(),
            'w': self.w,
            'h': self.h
        }

class NoteNode(BaseNode):
    def __init__(self, text="New Idea", x=0, y=0):
        super().__init__(x, y, 200, 200)
        self.setBrush(QBrush(QColor(254, 243, 199))) 
        
        self.pin = QGraphicsRectItem(-5, -10, 10, 10, self)
        self.pin.setBrush(QBrush(QColor(180, 20, 20)))
        self.pin.setPos(0, -90)
        
        # Clipping viewport so long text stays inside the note (scroll with mouse wheel)
        self.text_view_h = 170
        self.text_clip = QGraphicsRectItem(-90, -80, 180, self.text_view_h, self)
        self.text_clip.setPen(Qt.NoPen)
        self.text_clip.setFlag(QGraphicsItem.ItemClipsChildrenToShape, True)
        self.scroll_offset = 0

        self.text_item = QGraphicsTextItem(text, self.text_clip)
        self.text_item.setTextWidth(180)
        font = QFont("Courier New", 14, QFont.Bold)
        self.text_item.setFont(font)
        self.text_item.setDefaultTextColor(QColor(20, 20, 20))
        self.text_item.setPos(-90, -80)
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.text_item.document().contentsChanged.connect(self.ensure_cursor_visible)

    def max_scroll(self):
        return max(0, self.text_item.boundingRect().height() - self.text_view_h)

    def scroll_by(self, dy):
        """Scroll the note text. Returns True if the note could scroll."""
        if self.max_scroll() <= 0:
            self.set_scroll(0)
            return False
        self.set_scroll(self.scroll_offset + dy)
        return True

    def set_scroll(self, value):
        self.scroll_offset = min(max(0, value), self.max_scroll())
        self.text_item.setPos(-90, -80 - self.scroll_offset)

    def ensure_cursor_visible(self):
        cursor = self.text_item.textCursor()
        layout = self.text_item.document().documentLayout()
        block_rect = layout.blockBoundingRect(cursor.block())
        line = cursor.block().layout().lineForTextPosition(cursor.positionInBlock())
        top = block_rect.top() + (line.y() if line.isValid() else 0)
        bottom = top + (line.height() if line.isValid() else 20)
        if top < self.scroll_offset:
            self.set_scroll(top)
        elif bottom > self.scroll_offset + self.text_view_h:
            self.set_scroll(bottom - self.text_view_h)
        else:
            self.set_scroll(self.scroll_offset)

    def to_dict(self):
        d = super().to_dict()
        d['type'] = 'note'
        d['text'] = self.text_item.toPlainText()
        return d

class ImageNode(BaseNode):
    def __init__(self, pixmap, x=0, y=0, display_w=300):
        self.display_w = display_w
        # Initial dimensions
        w = display_w
        h = w * (pixmap.height() / pixmap.width())
        padding = 20
        bottom_pad = 60
        total_w = w + padding*2
        total_h = h + padding + bottom_pad
        
        super().__init__(x, y, total_w, total_h)
        
        self.add_button("C", self.start_crop, QColor(50, 150, 50))
        self.add_button("N", self.add_note, QColor(200, 150, 50))

        # Dark Background for Photo
        self.setBrush(QBrush(QColor(20, 20, 25))) 
        self.setPen(QPen(QColor(60, 60, 60), 1))
        
        self.current_pixmap = pixmap
        self.resize_handle = ResizeHandle(self)
        self.pixmap_item = QGraphicsPixmapItem(self)
        self.update_pixmap(pixmap)
        
        # Tape
        tape = QGraphicsRectItem(-50, -total_h/2 - 15, 100, 30, self)
        tape.setBrush(QBrush(QColor(255, 255, 200, 100)))
        tape.setPen(Qt.NoPen)
        tape.setRotation(random.uniform(-2, 2))
        tape.setZValue(5)

        self.crop_overlay = None

    def update_pixmap(self, pixmap):
        self.current_pixmap = pixmap
        if pixmap.width() == 0 or pixmap.height() == 0:
            return

        w = self.display_w
        h = w * (pixmap.height() / pixmap.width())
        
        # Explicitly cast to int for PySide6 scaled()
        target_w = int(w)
        target_h = int(h)
        if target_w < 1: target_w = 1
        if target_h < 1: target_h = 1

        scaled = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pixmap_item.setPixmap(scaled)
        
        # Recalculate dimensions
        padding = 20
        bottom_pad = 60
        self.w = target_w + padding*2
        self.h = target_h + padding + bottom_pad
        
        # Update Node Geometry (Rect and Shadow)
        self.setRect(-self.w/2, -self.h/2, self.w, self.h)
        self.shadow.setRect(-self.w/2 + 5, -self.h/2 + 5, self.w, self.h)

        # Center image
        self.pixmap_item.setPos(-scaled.width()/2, -self.h/2 + 20)
        self.pixmap_item.setZValue(1)
        
        # Recalculate controls position
        photo_bottom_rel = self.pixmap_item.pos().y() + scaled.height()
        self.controls_y_offset = photo_bottom_rel + 30
        self.controls.setPos(0, self.controls_y_offset)
        self.rotate_handle.setPos(0, self.controls_y_offset + 35)
        self.resize_handle.setPos(self.w/2, self.h/2)
        for line in self.connections:
            line.update_position()

    def set_display_width(self, w):
        self.prepareGeometryChange()
        self.display_w = w
        self.update_pixmap(self.current_pixmap)

    def update_ui_visibility(self, hovering=None):
        super().update_ui_visibility(hovering)
        if hasattr(self, 'resize_handle'):
            visible = self.controls.isVisible() or self.resize_handle.is_resizing
            self.resize_handle.setVisible(visible)

    def start_crop(self):
        if self.crop_overlay: return
        self.is_cropping = True
        
        # Disable parent movement so dragging crop handles doesn't move the node
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        
        # Temporarily disable RubberBandDrag on View to ensure clicks go to overlay
        views = self.scene().views()
        if views:
            views[0].setDragMode(QGraphicsView.NoDrag)
        
        self.update_ui_visibility() 
        brect = self.pixmap_item.boundingRect()
        target_rect = self.pixmap_item.mapRectToParent(brect)
        self.crop_overlay = InPlaceCropOverlay(target_rect, self)
        self.crop_overlay.cropCompleted.connect(self.apply_crop)
        self.crop_overlay.cropCancelled.connect(self.cancel_crop)

    def apply_crop(self, rect):
        try:
            mapped_rect = self.pixmap_item.mapRectFromParent(rect)
            scaled_pixmap = self.pixmap_item.pixmap()
            
            if scaled_pixmap.width() == 0 or scaled_pixmap.height() == 0:
                return

            scale_x = self.current_pixmap.width() / scaled_pixmap.width()
            scale_y = self.current_pixmap.height() / scaled_pixmap.height()
            
            ox = mapped_rect.x() * scale_x
            oy = mapped_rect.y() * scale_y
            ow = mapped_rect.width() * scale_x
            oh = mapped_rect.height() * scale_y
            
            # Ensure proper integers
            iox = int(ox)
            ioy = int(oy)
            iow = int(ow)
            ioh = int(oh)

            # Prevent zero or negative dimensions
            if iow <= 0 or ioh <= 0:
                return
            
            # Use safe intersection to avoid crashes if rect is out of bounds
            safe_rect = QRect(iox, ioy, iow, ioh).intersected(self.current_pixmap.rect())
            if safe_rect.isEmpty():
                return

            new_pix = self.current_pixmap.copy(safe_rect)
            if not new_pix.isNull():
                self.update_pixmap(new_pix)
        
        except Exception as e:
            print(f"Crop Error: {e}")
        finally:
            # Always ensure we exit crop mode to restore controls
            self.cancel_crop()

    def cancel_crop(self):
        if self.crop_overlay:
            self.scene().removeItem(self.crop_overlay)
            self.crop_overlay = None
        self.is_cropping = False
        
        # Re-enable parent movement
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        
        # Restore RubberBandDrag
        views = self.scene().views()
        if views:
            views[0].setDragMode(QGraphicsView.RubberBandDrag)
        
        self.update_ui_visibility()

    def delete_self(self):
        # Override delete to ensure we exit crop mode (and restore View DragMode) before removal
        if self.is_cropping:
            self.cancel_crop()
        super().delete_self()

    def add_note(self):
        # Add note near the center of the image
        note = ImageStickyNote("Note", 0, 0, self)
        # Random offset to avoid stacking
        note.setPos(random.randint(-50, 50), random.randint(-50, 50))

    def to_dict(self):
        d = super().to_dict()
        d['type'] = 'image'
        d['display_w'] = self.display_w
        d['pixmap_base64'] = pixmap_to_base64(self.current_pixmap)
        
        notes_data = []
        for child in self.childItems():
            if isinstance(child, ImageStickyNote):
                notes_data.append(child.to_dict())
        d['notes'] = notes_data
        return d

# --- Custom Graphics View for Panning ---

class BoardView(QGraphicsView):
    def __init__(self, scene, parent_window):
        super().__init__(scene)
        self.parent_window = parent_window
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setAcceptDrops(True)
        
        self.panning = False
        self.last_pan_pos = QPoint()

    def wheelEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        while item is not None and not isinstance(item, NoteNode):
            item = item.parentItem()
        if item is not None and item.scroll_by(-event.angleDelta().y() / 4):
            event.accept()
            return
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.last_pan_pos = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # Check for connection mode interaction
        if self.parent_window.connection_source:
            if event.button() == Qt.LeftButton:
                pos = event.position().toPoint()
                item = self.itemAt(pos)
                
                # Traverse up to find BaseNode (in case we clicked a child item like text)
                while item and not isinstance(item, BaseNode):
                    item = item.parentItem()
                
                if isinstance(item, BaseNode):
                    # Complete connection if not the same node
                    if item != self.parent_window.connection_source:
                        self.parent_window.finalize_connection(item)
                        event.accept()
                        return
                    else:
                         # Clicked on source node again, ignore or cancel?
                         # Let's ignore for now so they can click elsewhere
                         pass
                else:
                    # Clicked empty space - cancel connection
                    self.parent_window.cancel_connection_mode()
                    event.accept()
                    return
            elif event.button() == Qt.RightButton:
                self.parent_window.cancel_connection_mode()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.panning:
            current_pos = event.position().toPoint()
            delta = current_pos - self.last_pan_pos
            self.last_pan_pos = current_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp']:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        scene_pos = self.mapToScene(event.position().toPoint())
                        node = ImageNode(pixmap, scene_pos.x(), scene_pos.y())
                        self.scene().addItem(node)
        event.accept()

    def start_connection(self, node):
        self.parent_window.start_connection_mode(node)

# --- Main Application Window ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Idea Board")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #1a1a1a; color: #eeeeee;")
        
        self.scene = QGraphicsScene(0, 0, 5000, 3000)
        self.scene.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        
        # Grid Pattern
        grid_pix = QPixmap(40, 40)
        grid_pix.fill(QColor(30, 30, 30))
        painter = QPainter(grid_pix)
        painter.setPen(QColor(40, 40, 40))
        painter.drawPoint(0, 0)
        painter.end()
        self.scene.setBackgroundBrush(QBrush(grid_pix))

        self.view = BoardView(self.scene, self)
        self.setCentralWidget(self.view)

        # Toolbar
        toolbar = QToolBar("Tools")
        toolbar.setStyleSheet("QToolBar { background: #2a2a2a; border: none; padding: 5px; } QToolButton { color: white; padding: 5px; }")
        self.addToolBar(toolbar)

        add_note_action = QAction("Add Note", self)
        add_note_action.triggered.connect(self.add_note)
        toolbar.addAction(add_note_action)

        add_image_action = QAction("Add Image", self)
        add_image_action.triggered.connect(self.add_image)
        toolbar.addAction(add_image_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_board)
        toolbar.addAction(save_action)

        load_action = QAction("Load", self)
        load_action.triggered.connect(self.load_board)
        toolbar.addAction(load_action)

        export_action = QAction("Export PNG", self)
        export_action.triggered.connect(self.export_image)
        toolbar.addAction(export_action)

        self.connection_source = None
        self.active_temp_line = None

    def add_note(self):
        # Create note at center of current view
        center = self.view.mapToScene(self.view.viewport().rect().center())
        note = NoteNode("New Idea", center.x(), center.y())
        self.scene.addItem(note)

    def add_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                center = self.view.mapToScene(self.view.viewport().rect().center())
                node = ImageNode(pixmap, center.x(), center.y())
                self.scene.addItem(node)

    def start_connection_mode(self, node):
        self.connection_source = node
        self.view.setCursor(Qt.CrossCursor)
    
    def finalize_connection(self, target_node):
        if self.connection_source and target_node:
            line = ConnectionLine(self.connection_source, target_node)
            self.scene.addItem(line)
            self.connection_source.connections.append(line)
            target_node.connections.append(line)
        self.cancel_connection_mode()

    def cancel_connection_mode(self):
        self.connection_source = None
        self.view.setCursor(Qt.ArrowCursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.scene.selectedItems():
                if hasattr(item, 'delete_self'):
                    item.delete_self()
        elif event.key() == Qt.Key_Escape:
             self.cancel_connection_mode()

    def mousePressEvent(self, event):
        # Global click handling if needed
        super().mousePressEvent(event)

    def save_board(self):
        data = []
        for item in self.scene.items():
            if hasattr(item, 'to_dict') and not item.parentItem(): # Only root items
                data.append(item.to_dict())
            elif isinstance(item, ConnectionLine):
                data.append({
                    'type': 'connection',
                    'start_uuid': item.start_item.uuid,
                    'end_uuid': item.end_item.uuid
                })
        
        path, _ = QFileDialog.getSaveFileName(self, "Save Board", "", "JSON (*.json)")
        if path:
            with open(path, 'w') as f:
                json.dump(data, f)

    def load_board(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Board", "", "JSON (*.json)")
        if not path: return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
            return
            
        if not isinstance(data, list):
            QMessageBox.warning(self, "Invalid File", "The selected file is not a valid board file.")
            return

        self.scene.clear()
        
        uuid_map = {}
        connections_data = []

        # First pass: Nodes
        for item_data in data:
            if not isinstance(item_data, dict):
                continue
            
            item_type = item_data.get('type')

            if item_type == 'note':
                node = NoteNode(item_data['text'], item_data['x'], item_data['y'])
                node.uuid = item_data['uuid']
                node.setRotation(item_data['rotation'])
                self.scene.addItem(node)
                uuid_map[node.uuid] = node
            elif item_type == 'image':
                pixmap = base64_to_pixmap(item_data['pixmap_base64'])
                node = ImageNode(pixmap, item_data['x'], item_data['y'], item_data.get('display_w', 300))
                node.uuid = item_data['uuid']
                node.setRotation(item_data['rotation'])
                
                # Restore sticky notes on image
                if 'notes' in item_data:
                    for note_data in item_data['notes']:
                        note = ImageStickyNote(note_data['text'], note_data['x'], note_data['y'], node)
                
                self.scene.addItem(node)
                uuid_map[node.uuid] = node
            elif item_type == 'connection':
                connections_data.append(item_data)

        # Second pass: Connections
        for conn in connections_data:
            start_node = uuid_map.get(conn['start_uuid'])
            end_node = uuid_map.get(conn['end_uuid'])
            if start_node and end_node:
                line = ConnectionLine(start_node, end_node)
                self.scene.addItem(line)
                start_node.connections.append(line)
                end_node.connections.append(line)

    def export_image(self):
        self.scene.clearSelection()
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            QMessageBox.information(self, "Info", "The board is empty.")
            return

        rect.adjust(-50, -50, 50, 50)
        image = QImage(rect.size().toSize(), QImage.Format_ARGB32)
        
        # Fill with a default color matching background or transparent
        # Since scene.render draws the background brush, starting with transparent is fine
        image.fill(Qt.transparent)

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        self.scene.render(painter, QRectF(image.rect()), rect)
        painter.end()

        path, _ = QFileDialog.getSaveFileName(self, "Export Image", "idea_board.png", "PNG (*.png)")
        if path:
            image.save(path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
