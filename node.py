from PyQt5.QtWidgets import QGraphicsItem
from PyQt5 import QtGui, QtCore, QtWidgets
import image_manager
from math import cos, sin, radians

class Node(QGraphicsItem):
    #TODO: don't just keep constants and groups in every node
    def __init__(self, node_obj, constants, groups, tree):
        super().__init__()
        try:
            self.node_obj = node_obj
            self.id = str(node_obj['skill'])
            self.name = node_obj['name']
            self.icon = node_obj['icon']
            self.orbit_index = node_obj.get('orbitIndex')
            self.orbit = node_obj.get('orbit')
            self.is_notable = node_obj.get('isNotable', False)
            self.is_mastery = node_obj.get('isMastery', False)
            self.ascendancy_name = node_obj.get('ascendancyName', None)
            self.is_keystone = node_obj.get('isKeystone', False)
            self.is_jewel_socket = node_obj.get('isJewelSocket', False)
            self.is_ascendancy_start = node_obj.get('isAscendancyStart', False)
            self.is_multiple_choice_option = node_obj.get('isMultipleChoiceOption', False)
            self.is_multiple_choice = node_obj.get('isMultipleChoice', False)
            self.is_class_start = 'classStartIndex' in node_obj
            self.group_id = node_obj.get('group')
            if self.group_id is not None:
                self.node_group = groups[str(self.group_id)]

            if self.is_mastery:
                self.inactive_icon = node_obj['inactiveIcon']
                self.active_icon = node_obj['activeIcon']
                self.active_effect_image = node_obj['activeEffectImage']

                self.mastery_effects = node_obj['masteryEffects']
                self.selected_effect = None

            self.skills_per_orbit = constants['skillsPerOrbit']
            self.orbit_radii = constants['orbitRadii']

            self.tree = tree

            self.active = False
            self.on_hover_path = False

            self.position = self.get_position()

            if not self.is_class_start and not self.is_ascendancy_start:
                self.setCursor(QtCore.Qt.PointingHandCursor)

            self.setZValue(10)

            self.shape_radius = self.get_shape_radius()

            self.setAcceptHoverEvents(True)
            self.setFlag(QGraphicsItem.ItemIsSelectable)

        except KeyError as e:
            print(e)
            print(node_obj)
            raise

        self.active = False

    def hoverEnterEvent(self, event) -> None:
        if not self.is_class_start and not self.is_ascendancy_start:
            self.tree.hovered_node = self

        self.tree.node_hovered(self)

        return super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.tree.hovered_node = None

        self.tree.node_unhovered()

        return super().hoverLeaveEvent(event)

    def get_shape_radius(self):
        if self.get_frame_image() is None:
            return 0

        frame = image_manager.get_images()['assets'][self.get_frame_image()]

        y_pos = 0
        # determine inner transparent circle of the frame for clickbox
        while QtGui.qAlpha(frame.pixel(int(frame.width() / 2), int(frame.height() / 2 + y_pos))) < 40:
            y_pos += 1

        return y_pos * 1.3
    
    def get_icon_image(self):
        # TODO: jewel slots
        category = "normal"
        if self.is_keystone:
            category = "keystone"
        elif self.is_notable:
            category = "notable"
        elif self.is_mastery:
            category = "masteryInactive"

        if not self.is_mastery:
            category += "Active" if self.active else "Inactive"

        if 'isAscendancyStart' in self.node_obj:
            return image_manager.get_images()['assets']['AscendancyMiddle']

        if 'classStartIndex' in self.node_obj:
            if not self.active:
                return image_manager.get_images()['assets']['PSStartNodeBackgroundInactive']
            
            class_lower = self.node_obj['name'].lower()
            # temp name never replaced i guess
            if class_lower == "seven":
                class_lower = "scion"
            elif class_lower == "six":
                class_lower = "shadow"
            return image_manager.get_images()['assets'][f'center{class_lower}']

        if not self.is_mastery:
            return image_manager.get_images()[category][self.icon]
        else:
            if self.active:
                category = "masteryActiveSelected"
                return image_manager.get_images()[category][self.active_icon]
            elif not self.active and self.tree.is_mastery_active(self.id):
                category = "masteryConnected"
                return image_manager.get_images()[category][self.inactive_icon]
            else:
                return image_manager.get_images()[category][self.inactive_icon] 

    def toggle_active(self):
        self.active = not self.active
        self.update()

    def activate_mastery(self):
        self.active = True
        self.update()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        print(f"Clicked on {self.name}, id: {self.id} - outs: {self.node_obj['out']}, ins: {self.node_obj['in']}")

        if self.is_class_start:
            return
        
        if self.is_mastery:
            item, ok = QtWidgets.QInputDialog.getItem(None, "Mastery", "Select a Mastery", [effect['stats'][0] for effect in self.mastery_effects], 0, False)

            if ok:
                print(item)
                print(self.active_icon, self.inactive_icon)
                self.selected_effect = item

        if self.active:
            self.tree.test_unreachable(self.id)
            return
        # for connected in self.node_obj['out'] + self.node_obj['in']:
        #     if self.tree.is_allocated(connected):
        #         self.toggle_active()
        #         self.update()
        #         break

        self.tree.allocate_to(str(self.id))
        print(self.active)

    def get_position(self):
        # TODO: handle clusters and passives given by jewels
        if self.orbit_index is None or self.orbit is None:
            return None        

        if self.orbit == 2 or self.orbit == 3:
            orbit_angles = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]
            angle = orbit_angles[self.orbit_index] - 90
        else:
            angle = 360 / self.skills_per_orbit[self.orbit]
            angle = angle * self.orbit_index - 90
            
        node_x = cos(radians(angle)) * ((self.orbit_radii[self.orbit]) * 0.3835) + self.node_group['x'] * 0.3835
        node_y = sin(radians(angle)) * ((self.orbit_radii[self.orbit]) * 0.3835) + self.node_group['y'] * 0.3835

        return (node_x, node_y)

    def boundingRect(self):
        if self.get_frame_image() is not None:
            image = image_manager.get_images()['assets'][self.get_frame_image()]
        else:
            image = self.get_icon_image()

        if self.is_mastery and self.tree.is_mastery_active(self.id):
            image = image_manager.get_images()['assets']['PassiveMasteryConnectedButton']
        pos = self.position
        if pos is not None:
            return QtCore.QRectF(pos[0] - image.width() / 2, pos[1] - image.height() / 2, image.width(), image.height())
        else:
            return QtCore.QRectF(0, 0, 0, 0)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        icon_image = self.get_icon_image()
        pos = self.position

        if pos is not None:
            if self.shape_radius > 0:
                path.addEllipse(pos[0] - self.shape_radius, pos[1] - self.shape_radius, self.shape_radius * 2, self.shape_radius * 2)
            else:
                path.addEllipse(QtCore.QPointF(pos[0], pos[1]), 58 / 2, 58 / 2)
            return path
        else:
            return path

    def get_frame_image(self):
        if ('isAscendancyStart' in self.node_obj
            or 'classStartIndex' in self.node_obj):
            return None

        # normal notable
        if self.is_notable and 'ascendancyName' not in self.node_obj:
            path = "NotableFrame"
            path += "Allocated" if self.active else "Unallocated"
            return path

        # ascendancy notable
        if self.is_notable:
            path = "AscendancyFrameLarge"
            path += "Allocated" if self.active else "Normal"
            return path

        # keystone
        if self.is_keystone:
            path = "KeystoneFrame"
            path += "Allocated" if self.active else "Unallocated"
            return path
        
        # mastery
        if self.is_mastery:
            return None
        
        # ascendancy normal
        if 'ascendancyName' in self.node_obj:
            path = "AscendancyFrameSmall"
            path += "Allocated" if self.active else "Normal"
            return path
        
        if self.is_jewel_socket and 'expansionJewel' in self.node_obj:
            path = "JewelSocketAlt"
            path += "Active" if self.active else "Normal"
            return path
        elif self.is_jewel_socket:            
            path = "JewelFrame"
            path += "Allocated" if self.active else "Unallocated"
            return path

        # normal
        path = "PSSkillFrame"
        path += "Active" if self.active else ""
        return path        

    def paint(self, painter, option, widget):
        icon_image = self.get_icon_image()
        pos = self.position
        if pos is not None:
            if self.is_mastery and self.tree.is_mastery_active(self.id):
                mastery_active_background = image_manager.get_images()['assets']['PassiveMasteryConnectedButton']
                center = QtCore.QPointF(pos[0] - mastery_active_background.width() / 2, pos[1] - mastery_active_background.height() / 2)
                painter.drawImage(center, mastery_active_background)

            center = QtCore.QPointF(pos[0] - icon_image.width() / 2, pos[1] - icon_image.height() / 2)
            painter.drawImage(center, icon_image)

            frame_path = self.get_frame_image()

            if frame_path is not None:
                frame = image_manager.get_images()['assets'][frame_path]
                center = QtCore.QPointF(pos[0] - frame.width() / 2, pos[1] - frame.height() / 2)
                painter.drawImage(center, frame)

        

