from copy import copy
import io
import json
import sys
from typing import Callable, List
from collections import deque
from time import perf_counter

from PIL import Image, ImageOps, ImageQt
from PyQt5 import QtCore, QtGui, QtWidgets

import constants
import image_manager
from node import Node
from node_connection import NodeConnection

app = QtWidgets.QApplication(sys.argv)

class MainWindow(QtWidgets.QMainWindow):
    class_changed = QtCore.pyqtSignal(str)
    ascendancy_changed = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()

        with open('data.json') as f:
            self.data = json.load(f)

        self.graphics_view = SkillTreeView()
        self.graphics_view.allocated_points_changed.connect(self.update_points)
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_widget = QtWidgets.QWidget()
        controls_widget.setFixedHeight(30)
        controls_widget.setLayout(controls_layout)

        self.points_label = QtWidgets.QLabel()
        self.points_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.points_label.setFixedHeight(30)
        self.points_label.setText("Points: 0")

        self.class_selection = QtWidgets.QComboBox()
        self.class_selection.addItems([clazz['name'] for clazz in self.data['classes']])
        self.class_selection.currentIndexChanged.connect(self.graphics_view.class_changed)
        self.class_selection.currentTextChanged.connect(self.populate_ascendancies)
        self.graphics_view.class_changed(self.class_selection.currentIndex())

        self.ascendancy_selection = QtWidgets.QComboBox()
        self.populate_ascendancies(self.class_selection.currentText())    
        self.ascendancy_selection.currentTextChanged.connect(self.graphics_view.ascendancy_changed) 
        self.graphics_view.ascendancy_changed(self.ascendancy_selection.currentText())        

        controls_layout.addWidget(self.points_label)
        controls_layout.addWidget(self.class_selection)
        controls_layout.addWidget(self.ascendancy_selection)

        main_layout.addWidget(controls_widget)
        main_layout.addWidget(self.graphics_view)
        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(main_layout)

    def populate_ascendancies(self, class_name: str) -> None:
        self.ascendancy_selection.clear()
        self.ascendancy_selection.addItem('None')
        for clazz in self.data['classes']:
            if clazz['name'] == class_name:
                for ascendancy in clazz['ascendancies']:
                    self.ascendancy_selection.addItem(ascendancy['name'])   
                return

    def update_points(self, points: int) -> None:
        self.points_label.setText(f"Points: {points}")

class MainLayout(QtWidgets.QBoxLayout):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(QtWidgets.QBoxLayout.Direction.TopToBottom, parent, *args, **kwargs)

class SkillTreeView(QtWidgets.QGraphicsView):
    allocated_points_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

        with open('data.json') as f:
            self.data = json.load(f)

        self.class_roots = [""] * len(self.data['classes'])
        for root_node in self.data['nodes']['root']['out']:
            self.class_roots[self.data['nodes'][root_node]['classStartIndex']] = root_node

        self.ascendancy_roots = {}
        self.class_index = 0
        self.ascendancy = None

        constants.init(self.data['constants'])
        
        min_x = self.data['min_x']
        min_y = self.data['min_y']
        max_x = self.data['max_x']
        max_y = self.data['max_y']

        image_manager.init(self.data)

        self.setScene(QtWidgets.QGraphicsScene())
        self.setSceneRect(min_x - 1000, min_y - 1000, max_x - min_x, max_y - min_y)
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        # setting the drag mode also sets the cursor, so unset it to have an arrow instead
        self.viewport().unsetCursor()
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter)

        self.setWindowTitle("Skill Tree View")

        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(8, 13, 18), QtCore.Qt.BrushStyle.SolidPattern))

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        QtGui.QFontDatabase.addApplicationFont('Fontin-Regular.ttf')

        self.tooltip_title_font = QtGui.QFont('Fontin', 18)
        self.tooltip_stats_font = QtGui.QFont('Fontin', 10)
        self.tooltip_title_metrics = QtGui.QFontMetrics(self.tooltip_title_font)
        self.tooltip_stats_metrics = QtGui.QFontMetrics(self.tooltip_stats_font)

        self.scale(1, 1)

        self.nodes = {}

        self.hovered_node = None
        self.hover_path = []
        self.scene_mouse_pos = QtCore.QPoint()

        self.build_tree()


    def class_changed(self, class_index: int) -> None:
        self.class_index = class_index
        self.ascendancy_changed("None")

        self.test_unreachable(self.class_roots[class_index])

        for class_root in self.class_roots:
            self.nodes[class_root].active = False
        
        self.nodes[self.class_roots[class_index]].active = True
        self.viewport().update()

    def ascendancy_changed(self, ascendancy_name: str) -> None:
        for ascendancy_root in self.ascendancy_roots.items():
            root_name = ascendancy_root[0]
            root_id = ascendancy_root[1]
            self.nodes[root_id].active = False

            # some ascendancies span multiple groups so we can't just deallocate a group here
            for node in self.nodes.values():
                if node.ascendancy_name == root_name:
                    node.active = False
                    node.update()

        if ascendancy_name != 'None' and len(ascendancy_name) > 0:
            self.ascendancy = ascendancy_name
            self.nodes[self.ascendancy_roots[ascendancy_name]].active = True

    def node_hovered(self, node: Node) -> None:
        if self.hovered_node == node:
            return

        self.hovered_node = node

        if self.is_root_node(node.id):
            self.hover_path = []
            return

        shortest = ([], 999)
        id = node.id
        for start_id in self.nodes:
            if self.nodes[start_id].ascendancy_name is None and self.nodes[id].ascendancy_name is not None:
                continue

            if self.nodes[start_id].active and self.has_unallocated_neighbors(start_id) and not self.nodes[start_id].is_mastery:
                path = self.find_shortest_path(start_id, id)
                if len(path) < shortest[1]:
                    shortest = (path, len(path))

        path = shortest[0]
        self.hover_path = path
        for id in path:
            self.nodes[id].on_hover_path = True

    def node_unhovered(self) -> None:
        for id in self.hover_path:
            self.nodes[id].on_hover_path = False

        self.hovered_node = None

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)

        painter = QtGui.QPainter(self.viewport())
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        if self.hovered_node is None:
            return

        node_data = self.data['nodes'][self.hovered_node.id]

        painter.setFont(self.tooltip_title_font)
        
        title_height = self.tooltip_title_metrics.height() + 10
        tooltip_width = self.tooltip_title_metrics.width(node_data['name'])

        stats = node_data['stats']
        
        if self.hovered_node.is_mastery and self.hovered_node.selected_effect is not None:
            stats = [self.hovered_node.selected_effect]

        # find widest line after accounting for newlines, also increment count when encountering a newline
        stat_lines = len(stats)
        for stat in stats:
            if '\n' in stat:
                for line in stat.split('\n'):
                    tooltip_width = max(tooltip_width, self.tooltip_stats_metrics.width(line.replace('\n', '')))
            else:
                tooltip_width = max(tooltip_width, self.tooltip_stats_metrics.width(stat))
            
            stat_lines += stat.count('\n')

        width = tooltip_width + 20
        height = stat_lines * (self.tooltip_stats_metrics.height() + 5) + title_height + 5
        pos = copy(self.scene_mouse_pos)
        # offset slightly from cursor
        pos.setX(pos.x() + 15)
        pos.setY(pos.y() + 10)
        
        tooltip_rect = QtCore.QRectF(pos.x(), pos.y(), width, height)

        # move tooltip if it would intersect the viewport rect
        intersected = QtCore.QRect(pos.x(), pos.y(), width, height).intersected(self.viewport().rect())
        if intersected.width() < width:
            tooltip_rect.moveLeft(pos.x() - width - 25)
            pos.setX(pos.x() - width - 25)
        if intersected.height() < height:
            tooltip_rect.moveTop(pos.y() - height - 10)
            pos.setY(pos.y() - height - 10)

        tooltip_path = QtGui.QPainterPath()
        tooltip_path.addRoundedRect(tooltip_rect, 10, 10)
        painter.strokePath(tooltip_path, QtGui.QPen(QtGui.QColorConstants.White, 1))
        painter.fillPath(tooltip_path, QtGui.QBrush(QtGui.QColor(0, 0, 0, 200)))

        painter.setPen(QtGui.QColor(117, 116, 111))
        painter.drawText(QtCore.QRectF(pos.x(), pos.y(), width, title_height), QtCore.Qt.AlignmentFlag.AlignCenter, node_data['name'])

        offset = title_height
        painter.setFont(self.tooltip_stats_font)
        font_height = painter.fontMetrics().height()
        for i, stat in enumerate(stats):
            lines = 1 + stat.count('\n')
            painter.drawText(QtCore.QRectF(pos.x() + 10, pos.y() + offset, width, (font_height + 5) * lines), QtCore.Qt.AlignmentFlag.AlignVCenter, stat)
            offset += (font_height + 5) * lines

        self.viewport().update(QtCore.QRect(pos.x() - 10, pos.y() - 10, width + 20, height + 20))

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.angleDelta().y() > 0:
            self.scale(1.5, 1.5)
        else:
            self.scale(0.5, 0.5)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self.scene_mouse_pos = event.pos()
        return super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mousePressEvent(event)
        self.viewport().setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self.viewport().unsetCursor()

    def has_unallocated_neighbors(self, node_id: str):
        for neighbor in self.data['nodes'][node_id]['out'] + self.data['nodes'][node_id]['in']:
            if not self.nodes[neighbor].active and 'isMastery' not in self.data['nodes'][neighbor]:
                return True

        return False

    def update_num_nodes(self) -> None:
        num_nodes = 0
        for node in self.nodes.items():
            id = node[0]
            node_obj = node[1]

            if node_obj.active and not self.is_root_node(id) and not node_obj.is_ascendancy_start and not node_obj.is_multiple_choice_option:
                num_nodes += 1

        self.allocated_points_changed.emit(num_nodes)

    def allocate_to(self, target_id: str) -> None:
        if self.is_root_node(target_id):
            return

        start = perf_counter()
        shortest = ([], 999)
        for node in self.nodes:
            if self.nodes[node].ascendancy_name is None and self.nodes[target_id].ascendancy_name is not None:
                continue

            if self.nodes[node].active and self.has_unallocated_neighbors(node) and not self.nodes[node].is_mastery:
                path = self.find_shortest_path(node, target_id)
                if len(path) < shortest[1]:
                    shortest = (path, len(path))

        path = shortest[0]
        for node in path[1:]:
            self.allocate(node)
        
        print(f"Allocate to took {perf_counter() - start} seconds")
        self.update_num_nodes()

    def is_root_node(self, node_id: str) -> bool:
        return node_id in self.data['nodes']['root']['out']

    def test_unreachable(self, node_id: str) -> None:
        start = perf_counter()

        self.nodes[node_id].toggle_active()

        unreachable = []

        for node in self.nodes:
            if self.nodes[node].active and not self.is_root_node(node):
                if not self.is_reachable(self.class_roots[self.class_index], str(node)):
                    unreachable.append(node)

        for node in unreachable:
            self.nodes[node].toggle_active()

        self.update_num_nodes()

        print(f"Test unreachable took {perf_counter() - start} seconds")

    def is_reachable(self, node_id: str, target_id: str) -> bool:
        if self.is_root_node(target_id):
            return False

        def skip_criteria(id: str) -> bool:
            return ('isMastery' in self.data['nodes'][id]
                    or not self.nodes[id].active)

        path = self.bfs(node_id, target_id, skip_criteria)

        return len(path) > 0

    def bfs(self, start: str, end: str, skip_criteria: Callable[[str], bool] = lambda x: False) -> List[str]:
        path = None
        dist = {start: [start]}
        q = deque([start])
        while len(q):
            at = q.popleft()
            for next in self.data['nodes'][at]['out'] + self.data['nodes'][at]['in']:
                if skip_criteria(next):
                    continue

                if next != end and next != start and self.is_root_node(next):
                    continue

                if next == end:
                    path = dist[at] + [next]
                    q.clear()
                    break

                if next not in dist:
                    dist[next] = dist[at] + [next]
                    q.append(next)

        if path is None:
            return []

        return path

    def allocate(self, node_id: str) -> None:
        if self.nodes[node_id].is_multiple_choice_option: 
            parent = self.data['nodes'][node_id]['in'][0]
            parent = self.data['nodes'][parent]
            for out in parent['out']:
                if self.nodes[out].is_multiple_choice_option:
                    self.nodes[out].active = False

        self.nodes[node_id].toggle_active()

        if self.nodes[node_id].is_notable:
            for neighbor in self.data['nodes'][node_id]['out'] + self.data['nodes'][node_id]['in']:
                if self.nodes[neighbor].is_mastery:
                    self.nodes[neighbor].update()


    def is_mastery_active(self, mastery_id: str) -> bool:
        connected = self.data['nodes'][mastery_id]['out'] + self.data['nodes'][mastery_id]['in']

        return any(self.nodes[node].active for node in connected)

    def find_shortest_path(self, start: str, end: str) -> List[str]:
        end_in_ascendant = 'ascendancyName' in self.data['nodes'][end] and self.data['nodes'][end]['ascendancyName'] == self.ascendancy       

        def skip_criteria(id) -> bool:
            if not end_in_ascendant and 'ascendancyName' in self.data['nodes'][id]:
                return not self.nodes[id].active

            #  or id in self.class_roots
            return ('isMastery' in self.data['nodes'][id])

        return self.bfs(start, end, skip_criteria)

    def build_tree(self) -> None:
        group_background_1 = image_manager.get_images()['assets']['PSGroupBackground1']
        group_background_2 = image_manager.get_images()['assets']['PSGroupBackground2']
        group_background_3_base = image_manager.get_images()['assets']['PSGroupBackground3']
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.ReadWrite)
        group_background_3_base.save(buffer, "PNG")
        group_background_3_base = Image.open(io.BytesIO(buffer.data()))
        group_background_3 = Image.new('RGBA', (group_background_3_base.width, group_background_3_base.height * 2))
        group_background_3.paste(group_background_3_base, (0, 0))
        group_background_3.paste(ImageOps.flip(group_background_3_base), (0, group_background_3_base.height))


        # group backgrounds
        for group in self.data['groups'].items():
            group_data = group[1]

            if 'ascendancyName' in self.data['nodes'][group_data['nodes'][0]]:
                continue

            root_nodes = self.data['nodes']['root']['out']

            if any(node in root_nodes for node in group_data['nodes']):
                continue

            if 3 in group_data['orbits']:
                item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(ImageQt.ImageQt(group_background_3)))
                x_pos = group_data['x'] * 0.3835 - group_background_3.width / 2
                y_pos = group_data['y'] * 0.3835 - group_background_3.height / 2
                item.setOffset(x_pos, y_pos)
                self.scene().addItem(item)
                continue

            if 2 in group_data['orbits']:
                item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(group_background_2))
                x_pos = group_data['x'] * 0.3835 - group_background_2.width() / 2
                y_pos = group_data['y'] * 0.3835 - group_background_2.height() / 2
                item.setOffset(x_pos, y_pos)
                self.scene().addItem(item)
                continue

            if 1 in group_data['orbits']:
                item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(group_background_1))
                x_pos = group_data['x'] * 0.3835 - group_background_1.width() / 2
                y_pos = group_data['y'] * 0.3835 - group_background_1.height() / 2
                item.setOffset(x_pos, y_pos)
                self.scene().addItem(item)
                continue

        # ascendancy backgrounds
        for group in self.data['groups'].items():
            group_data = group[1]
            nodes = group_data['nodes']

            is_ascendancy_group = any('isAscendancyStart' in self.data['nodes'][node] for node in nodes)

            if is_ascendancy_group:
                ascendancy = self.data['nodes'][nodes[0]]['ascendancyName']
                image = image_manager.get_images()['assets'][f"Classes{ascendancy}"]
                item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))
                x_pos = group_data['x'] * 0.3835 - image.width() / 2
                y_pos = group_data['y'] * 0.3835 - image.height() / 2
                item.setOffset(x_pos, y_pos)
                self.scene().addItem(item)
                continue

        # nodes
        for node in self.data['nodes'].items():
            if node[0] == 'root':
                continue

            # ignore nodes not in a group, since they are not on the tree
            if 'group' not in node[1]:
                continue
                
            if 'isAscendancyStart' in node[1]:
                self.ascendancy_roots[node[1]['ascendancyName']] = node[0]

            node_data = node[1]
            node_obj = Node(node_data, self.data['constants'], self.data['groups'], self)
            self.nodes[node_obj.id] = node_obj
            self.scene().addItem(node_obj)

        # connections
        for node in self.data['nodes'].values():
            if 'out' not in node:
                continue
        
            # root node
            if 'skill' not in node:
                continue

            if 'classStartIndex' in node:
                continue

            is_ascendancy = False
            if 'ascendancyName' in node:
                is_ascendancy = True
            
            node_id = str(node['skill'])
            for out in node['out']:
                out_node = self.data['nodes'][out]
                out_node_id = str(out_node['skill'])

                if 'classStartIndex' in out_node:
                    continue

                if 'isMastery' in node or 'isMastery' in out_node:
                    continue
                
                if ('ascendancyName' in out_node and not is_ascendancy
                    or 'ascendancyName' not in out_node and is_ascendancy):
                    continue

                connection = NodeConnection(self.nodes[node_id], self.nodes[out_node_id], self.data)
                self.scene().addItem(connection)


window = MainWindow()
window.setGeometry(100, 100, 1200, 700)
window.setWindowTitle('PoE Tree Planner')
window.show()

sys.exit(app.exec_())
