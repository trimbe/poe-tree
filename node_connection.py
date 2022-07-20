import math
from PyQt5 import QtCore, QtGui, QtWidgets
from util import get_orbit_angle
from PIL import Image, ImageQt, ImageOps, ImageEnhance
import image_manager

class NodeConnection(QtWidgets.QGraphicsItem):
    def __init__(self, first_node, second_node, data):
        super().__init__()
        self.first_node = first_node
        self.second_node = second_node
        self.active = False
        orbit = first_node.orbit
        self.tree_data = data
        self.intermediate_state = False

        self.node_group = first_node.node_group

        self.is_arc = first_node.orbit == second_node.orbit and first_node.group_id == second_node.group_id

        self.last_state = "Normal"

        # arc path
        if self.is_arc:
            self.image = f"Orbit{orbit}"
        else: # line path
            self.image = f"LineConnector"

        self.image += "Active" if self.active else "Normal"
        self.clip_path = self.generate_clip_path()

    def get_state(self):
        if self.first_node.active and self.second_node.active:
            return "Active"
        elif self.first_node.on_hover_path and self.second_node.on_hover_path:
            return "HoverPath"
        elif self.first_node.active or self.second_node.active:
            return "Intermediate"
        else:
            return "Normal"

    def get_connector_name(self):
        if self.is_arc:
            return f"Orbit{self.first_node.orbit}{self.get_state()}"
        else:
            return f"LineConnector{self.get_state()}"

    def boundingRect(self) -> QtCore.QRectF:
        return self.clip_path.boundingRect()

    def generate_clip_path(self):
        first_pos = self.first_node.get_position()
        second_pos = self.second_node.get_position()

        connection_path = QtGui.QPainterPath(QtCore.QPointF(first_pos[0], first_pos[1]))

        if self.is_arc:
            group_center = (self.node_group['x'] * 0.3835, self.node_group['y'] * 0.3835)

            first_angle = get_orbit_angle(self.first_node.orbit, self.first_node.orbit_index, self.tree_data)
            second_angle = get_orbit_angle(self.second_node.orbit, self.second_node.orbit_index, self.tree_data)

            orbit_radius = self.tree_data['constants']['orbitRadii'][self.first_node.orbit] * 0.3835

            span = second_angle - first_angle
            span = (span + 180) % 360 - 180
            span = -span

            start_angle = (90 - first_angle) % 360

            arc_bounds = QtCore.QRectF(group_center[0] - orbit_radius, group_center[1] - orbit_radius, orbit_radius * 2, orbit_radius * 2)
            
            connection_path.arcTo(arc_bounds, start_angle, span)
        else:
            connection_path.lineTo(second_pos[0], second_pos[1])

        stroker = QtGui.QPainterPathStroker()
        stroker.setCapStyle(QtCore.Qt.FlatCap)
        stroker.setWidth(28)
        stroke = stroker.createStroke(connection_path)

        return stroke

    def paint(self, painter, option, widget):
        painter.setClipPath(self.clip_path)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)    

        state = self.get_state()
        image = image_manager.get_images()['connectors'][self.get_connector_name()]
        if self.last_state != state:
            self.last_state = state
            self.update()

        if self.is_arc:
            group_center = (self.node_group['x'] * 0.3835, self.node_group['y'] * 0.3835)
            path_pos = QtCore.QPointF(group_center[0] - image.width() / 2, group_center[1] - image.height() / 2)

            painter.drawImage(path_pos, image)
        else:                
            first_pos = self.first_node.position
            second_pos = self.second_node.position
            dx = second_pos[0] - first_pos[0]
            dy = second_pos[1] - first_pos[1]
            angle = math.atan2(dy, dx) * 180 / math.pi

            distance = math.dist(first_pos, second_pos)

            painter.translate(first_pos[0], first_pos[1])
            painter.rotate(angle)
            painter.drawImage(QtCore.QPointF(0, -image.height() / 2), image)
            # tile if longer than original image
            for i in range(1, math.ceil(distance / image.width())):
                painter.drawImage(QtCore.QPointF(image.width() * i - 2, -image.height() / 2), image)