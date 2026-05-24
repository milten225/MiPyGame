import sys
import os
import pygame
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
                             QLabel, QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QToolBar, QMainWindow, QTextEdit, QInputDialog,
                             QPushButton, QTabWidget, QColorDialog, QListWidget, QCheckBox,
                             QDockWidget, QSlider, QComboBox, QMenu, QToolButton, QMessageBox)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QAction, QFont
from core.scene import SceneTree
from core.node import Node2D
from core.object_type import ObjectType, ObjectKind

class PygameWidget(QLabel):
    clicked = pyqtSignal(int, int); dragged = pyqtSignal(int, int, bool)
    panned = pyqtSignal(int, int); dropped = pyqtSignal()
    def __init__(self, width, height):
        super().__init__(); self.setFixedSize(width, height)
        self.surface = pygame.Surface((width, height)); self.last_pos = None
    def update_frame(self):
        img = QImage(pygame.image.tostring(self.surface, "RGBA", False), self.surface.get_width(), self.surface.get_height(), QImage.Format.Format_RGBA8888)
        self.setPixmap(QPixmap.fromImage(img))
    def mousePressEvent(self, event):
        self.last_pos = event.pos();
        if event.button() == Qt.MouseButton.LeftButton: self.clicked.emit(event.pos().x(), event.pos().y())
    def mouseMoveEvent(self, event):
        if self.last_pos:
            dx = event.pos().x() - self.last_pos.x(); dy = event.pos().y() - self.last_pos.y(); self.last_pos = event.pos()
            if event.buttons() & Qt.MouseButton.RightButton: self.panned.emit(dx, dy)
            elif event.buttons() & Qt.MouseButton.LeftButton: self.dragged.emit(dx, dy, bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
    def mouseReleaseEvent(self, event): self.last_pos = None; self.dropped.emit()

class EditorWindow(QMainWindow):
    def __init__(self, width=1400, height=850):
        super().__init__()
        self.setWindowTitle("MipyGame Engine Pro - Professional Edition")
        self.resize(width, height)
        if not os.path.exists("assets"): os.makedirs("assets")

        pygame.mixer.init()
        self.scenes = {"Level_1": SceneTree()}
        self.active_scene_name = "Level_1"
        self.active_scene = self.scenes[self.active_scene_name]
        self.node_map = {}; self.reverse_node_map = {}; self.selected_node = None

        self.init_ui(); self.setup_default_scene(); self.refresh_assets()
        self.timer = QTimer(); self.timer.timeout.connect(self.editor_loop); self.timer.start(16)

    def init_ui(self):
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AllowTabbedDocks)

        # --- ТУЛБАР ---
        toolbar = QToolBar(); self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        toolbar.addWidget(QLabel(" 🎬 Сцена: "))
        self.scene_combo = QComboBox(); self.scene_combo.addItem("Level_1"); self.scene_combo.currentTextChanged.connect(self.switch_scene)
        toolbar.addWidget(self.scene_combo)

        btn_new_scene = QPushButton("➕ Сцена"); btn_new_scene.clicked.connect(self.create_scene); toolbar.addWidget(btn_new_scene)
        btn_del_scene = QPushButton("🗑️ Удалить"); btn_del_scene.clicked.connect(self.delete_scene); toolbar.addWidget(btn_del_scene)
        toolbar.addSeparator()

        btn_add = QToolButton(); btn_add.setText("➕ Добавить ▾"); btn_add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        add_menu = QMenu()
        add_menu.addAction("🟩 Спрайт", lambda: self.spawn_node("sprite"))
        add_menu.addAction("🏃‍♂️ Аниматор", lambda: self.spawn_node("anim"))
        add_menu.addAction("🔤 Текст", lambda: self.spawn_node("text"))
        btn_add.setMenu(add_menu); toolbar.addWidget(btn_add)
        toolbar.addSeparator()
        act_play = QAction("▶ ЗАПУСК ИГРЫ", self); act_play.triggered.connect(self.launch_game); toolbar.addAction(act_play)

        # --- ЦЕНТР ---
        view_container = QWidget(); view_layout = QVBoxLayout(view_container)
        grid_toolbar = QHBoxLayout()
        self.chk_grid = QCheckBox("Сетка"); self.chk_grid.setChecked(True); self.chk_grid.stateChanged.connect(self.toggle_grid)
        self.chk_snap = QCheckBox("Магнит")
        btn_reset_cam = QPushButton("🎯 Сброс камеры"); btn_reset_cam.clicked.connect(self.reset_camera)
        btn_delete = QPushButton("🗑️ Удалить (Del)"); btn_delete.setStyleSheet("color: #ff4444;"); btn_delete.clicked.connect(self.delete_selected_node)
        grid_toolbar.addWidget(self.chk_grid); grid_toolbar.addWidget(self.chk_snap); grid_toolbar.addStretch()
        grid_toolbar.addWidget(btn_reset_cam); grid_toolbar.addWidget(btn_delete); view_layout.addLayout(grid_toolbar)

        self.viewport = PygameWidget(800, 600)
        self.viewport.clicked.connect(self.on_canvas_click); self.viewport.dragged.connect(self.on_canvas_drag)
        self.viewport.dropped.connect(self.on_canvas_drop); self.viewport.panned.connect(self.on_camera_pan)
        view_layout.addWidget(self.viewport, alignment=Qt.AlignmentFlag.AlignCenter); self.setCentralWidget(view_container)

        # --- ЛЕВО (ДЕРЕВО) ---
        self.dock_tree = QDockWidget("Иерархия", self); self.tree = QTreeWidget(); self.tree.setHeaderLabel("Объекты")
        self.tree.itemClicked.connect(self.on_node_selected); self.dock_tree.setWidget(self.tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_tree)

        # --- ПРАВО (КОНТЕКСТНЫЙ ИНСПЕКТОР) ---
        self.dock_inspector = QDockWidget("Инспектор", self); self.tabs = QTabWidget()
        self.tab_inspector = QWidget(); ins_main_layout = QVBoxLayout(self.tab_inspector); ins_main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # БЛОК 1: Трансформация (Instance)
        self.grp_transform = QGroupBox("Трансформация (Instance)")
        form_trans = QFormLayout(self.grp_transform)
        self.name_edit = QLineEdit(); self.name_edit.textChanged.connect(self.sync_to_node)
        self.pos_x = QDoubleSpinBox(); self.pos_x.setRange(-5000, 5000); self.pos_x.valueChanged.connect(self.sync_to_node)
        self.pos_y = QDoubleSpinBox(); self.pos_y.setRange(-5000, 5000); self.pos_y.valueChanged.connect(self.sync_to_node)
        self.z_index_box = QSpinBox(); self.z_index_box.setRange(-100, 100); self.z_index_box.valueChanged.connect(self.sync_to_node)
        form_trans.addRow("Имя:", self.name_edit); form_trans.addRow("Слой (Z):", self.z_index_box); form_trans.addRow("X:", self.pos_x); form_trans.addRow("Y:", self.pos_y)
        ins_main_layout.addWidget(self.grp_transform)

        # БЛОК 2: Параметры типа (DNA)
        self.grp_type = QGroupBox("Свойства Типа (DNA)")
        form_type = QFormLayout(self.grp_type)
        self.size_w = QSpinBox(); self.size_w.setRange(1, 2000); self.size_w.valueChanged.connect(self.sync_to_node)
        self.size_h = QSpinBox(); self.size_h.setRange(1, 2000); self.size_h.valueChanged.connect(self.sync_to_node)
        self.chk_static = QCheckBox("Статичный объект"); self.chk_static.stateChanged.connect(self.sync_to_node)
        self.color_btn = QPushButton("Цвет заливки"); self.color_btn.clicked.connect(self.pick_color)
        form_type.addRow("Ширина:", self.size_w); form_type.addRow("Высота:", self.size_h)
        form_type.addRow(self.chk_static); form_type.addRow(self.color_btn)

        # Контекстные поля
        self.txt_content = QLineEdit(); self.txt_content.textChanged.connect(self.sync_to_node)
        self.txt_font_size = QSpinBox(); self.txt_font_size.setRange(8, 200); self.txt_font_size.valueChanged.connect(self.sync_to_node)
        self.anim_frames = QSpinBox(); self.anim_frames.setRange(1, 100); self.anim_frames.valueChanged.connect(self.sync_to_node)
        self.anim_fps = QSpinBox(); self.anim_fps.setRange(1, 60); self.anim_fps.valueChanged.connect(self.sync_to_node)

        form_type.addRow("Текст:", self.txt_content); form_type.addRow("Разм. шрифта:", self.txt_font_size)
        form_type.addRow("Всего кадров:", self.anim_frames); form_type.addRow("Скорость (FPS):", self.anim_fps)
        ins_main_layout.addWidget(self.grp_type)

        ins_main_layout.addStretch()
        self.tabs.addTab(self.tab_inspector, "⚙ Свойства")
        self.tab_code = QWidget(); code_layout = QVBoxLayout(self.tab_code)
        self.code_edit = QTextEdit(); self.code_edit.setFont(QFont("Consolas", 10))
        btn_save = QPushButton("💾 Сохранить в Тип"); btn_save.clicked.connect(self.save_script)
        code_layout.addWidget(QLabel("Код поведения (Behavior)")); code_layout.addWidget(self.code_edit); code_layout.addWidget(btn_save)
        self.tabs.addTab(self.tab_code, "📄 Скрипт")

        self.dock_inspector.setWidget(self.tabs); self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_inspector)

        # --- НИЗ ---
        self.dock_assets = QDockWidget("Ресурсы", self); asset_widget = QWidget(); asset_layout = QVBoxLayout(asset_widget)
        btn_refresh = QPushButton("🔄 Обновить"); btn_refresh.clicked.connect(self.refresh_assets)
        self.asset_list = QListWidget(); self.asset_list.itemDoubleClicked.connect(self.apply_asset)
        asset_layout.addWidget(btn_refresh); asset_layout.addWidget(self.asset_list); self.dock_assets.setWidget(asset_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_assets)

        # МЕНЮ "ОКНА"
        menubar = self.menuBar(); view_menu = menubar.addMenu("👁️ Окна")
        view_menu.addAction(self.dock_tree.toggleViewAction())
        view_menu.addAction(self.dock_inspector.toggleViewAction())
        view_menu.addAction(self.dock_assets.toggleViewAction())

    def setup_default_scene(self):
        t = ObjectType("Player", ObjectKind.SPRITE, width=64, height=64)
        node = Node2D(t, "Hero", x=300, y=300)
        self.active_scene.add_node(node)
        self.rebuild_tree_ui()

    def rebuild_tree_ui(self):
        self.tree.clear(); self.node_map.clear(); self.reverse_node_map.clear(); self.selected_node = None
        self._add_node_to_tree(self.active_scene.root, None)
        self.tree.expandAll()

    def _add_node_to_tree(self, node, parent_item):
        item = QTreeWidgetItem(parent_item if parent_item else self.tree, [node.get_name()])
        self.node_map[id(item)] = node; self.reverse_node_map[node] = item
        for child in node.children: self._add_node_to_tree(child, item)

    def spawn_node(self, kind_str):
        if kind_str == "sprite": ot = ObjectType("NewSprite", ObjectKind.SPRITE)
        elif kind_str == "anim": ot = ObjectType("NewAnim", ObjectKind.ANIMATED, frames=4)
        elif kind_str == "text": ot = ObjectType("NewText", ObjectKind.TEXT)

        node = Node2D(ot, f"{ot.name}_{len(self.node_map)}")
        node.set_position(self.active_scene.camera_x + 350, self.active_scene.camera_y + 250)
        self.active_scene.add_node(node)
        self.rebuild_tree_ui(); self.select_node(node)

    def select_node(self, node):
        self.selected_node = node
        item = self.reverse_node_map.get(node)
        if item: self.tree.setCurrentItem(item)
        self.refresh_ui()

    def refresh_ui(self):
        if not self.selected_node: return
        n, ot = self.selected_node, self.selected_node.object_type
        self.name_edit.blockSignals(True); self.name_edit.setText(n.get_name()); self.name_edit.blockSignals(False)
        self.pos_x.blockSignals(True); self.pos_x.setValue(n.get_position().x); self.pos_x.blockSignals(False)
        self.pos_y.blockSignals(True); self.pos_y.setValue(n.get_position().y); self.pos_y.blockSignals(False)
        self.z_index_box.blockSignals(True); self.z_index_box.setValue(n.get_z_index()); self.z_index_box.blockSignals(False)

        self.size_w.blockSignals(True); self.size_w.setValue(ot.width); self.size_w.blockSignals(False)
        self.size_h.blockSignals(True); self.size_h.setValue(ot.height); self.size_h.blockSignals(False)
        self.chk_static.blockSignals(True); self.chk_static.setChecked(ot.is_static); self.chk_static.blockSignals(False)

        self.txt_content.blockSignals(True); self.txt_content.setText(ot.text_content); self.txt_content.blockSignals(False)
        self.txt_font_size.blockSignals(True); self.txt_font_size.setValue(ot.font_size); self.txt_font_size.blockSignals(False)
        self.anim_frames.blockSignals(True); self.anim_frames.setValue(ot.frames); self.anim_frames.blockSignals(False)
        self.anim_fps.blockSignals(True); self.anim_fps.setValue(ot.fps); self.anim_fps.blockSignals(False)

        self.code_edit.setPlainText(ot.behavior_code)

    def sync_to_node(self):
        if not self.selected_node: return
        n, ot = self.selected_node, self.selected_node.object_type
        n.set_name(self.name_edit.text()); n.set_z_index(self.z_index_box.value())
        n.set_position(self.pos_x.value(), self.pos_y.value())

        ot.width, ot.height = self.size_w.value(), self.size_h.value()
        ot.is_static = self.chk_static.isChecked()
        ot.text_content = self.txt_content.text(); ot.font_size = self.txt_font_size.value()
        ot.frames, ot.fps = self.anim_frames.value(), self.anim_fps.value()

        item = self.reverse_node_map.get(n)
        if item: item.setText(0, n.get_name())

    def save_script(self):
        if self.selected_node: self.selected_node.object_type.behavior_code = self.code_edit.toPlainText()

    def pick_color(self):
        if not self.selected_node: return
        c = QColorDialog.getColor()
        if c.isValid():
            self.selected_node.object_type.color = (c.red(), c.green(), c.blue())
            self.selected_node.object_type.sprite_path = ""

    def on_canvas_click(self, x, y):
        ax, ay = x + self.active_scene.camera_x, y + self.active_scene.camera_y
        found = None
        for node in self.active_scene._get_all_nodes_flat(self.active_scene.root):
            if node == self.active_scene.root: continue
            pos, ot = node.get_position(), node.object_type
            if pygame.Rect(pos.x, pos.y, ot.width, ot.height).collidepoint(ax, ay):
                found = node; break
        if found: self.select_node(found)
        else: self.selected_node = None; self.tree.clearSelection(); self.clear_ui()

    def on_canvas_drag(self, dx, dy, res):
        if self.selected_node and self.selected_node != self.active_scene.root:
            if res:
                self.selected_node.object_type.width += dx; self.selected_node.object_type.height += dy
            else:
                p = self.selected_node.get_position()
                self.selected_node.set_position(p.x + dx, p.y + dy)
            self.refresh_ui()

    def on_canvas_drop(self):
        if self.selected_node and self.chk_snap.isChecked():
            p, g = self.selected_node.get_position(), self.active_scene.grid_size
            self.selected_node.set_position(round(p.x/g)*g, round(p.y/g)*g); self.refresh_ui()

    def on_camera_pan(self, dx, dy): self.active_scene.camera_x -= dx; self.active_scene.camera_y -= dy
    def toggle_grid(self, s): self.active_scene.show_grid = (s == 2)
    def reset_camera(self): self.active_scene.camera_x = self.active_scene.camera_y = 0
    def delete_selected_node(self):
        if self.selected_node and self.selected_node != self.active_scene.root:
            self.active_scene.remove_node(self.selected_node); self.rebuild_tree_ui()

    def switch_scene(self, name):
        if name in self.scenes: self.active_scene_name = name; self.active_scene = self.scenes[name]; self.rebuild_tree_ui()

    def create_scene(self):
        n, ok = QInputDialog.getText(self, "Сцена", "Имя:");
        if ok and n:
            self.scenes[n] = SceneTree()
            self.scene_combo.blockSignals(True); self.scene_combo.addItem(n); self.scene_combo.setCurrentText(n); self.scene_combo.blockSignals(False)
            self.switch_scene(n)

    def delete_scene(self):
        if len(self.scenes) <= 1:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить последнюю сцену!")
            return
        reply = QMessageBox.question(self, 'Подтверждение', f"Удалить сцену '{self.active_scene_name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.scenes[self.active_scene_name]
            idx = self.scene_combo.findText(self.active_scene_name)
            self.scene_combo.blockSignals(True); self.scene_combo.removeItem(idx); self.scene_combo.blockSignals(False)
            self.switch_scene(self.scene_combo.currentText())

    def refresh_assets(self):
        self.asset_list.clear()
        if os.path.exists("assets"):
            for f in os.listdir("assets"):
                if f.endswith(('.png', '.jpg')): self.asset_list.addItem(f)

    def apply_asset(self, item):
        if self.selected_node: self.selected_node.object_type.sprite_path = os.path.join("assets", item.text())

    def launch_game(self):
        # 1. Сохраняем состояние (Construct Classic: игра начинается с чистого листа)
        self.active_scene.save_state()

        # 2. Настраиваем UI перед запуском
        was_grid = self.active_scene.show_grid
        self.active_scene.show_grid = False
        self.timer.stop()

        # 3. Запуск физики и игры
        self.active_scene.start_physics()
        pygame.display.init(); screen = pygame.display.set_mode((800, 600)); clock = pygame.time.Clock(); run = True

        while run:
            dt = clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: run = False
            self.active_scene.update(dt); self.active_scene.draw(screen); pygame.display.flip()

        # 4. Завершение игры и восстановление состояния
        pygame.display.quit(); pygame.display.init()
        self.active_scene.stop_physics()
        self.active_scene.restore_state()
        self.active_scene.show_grid = was_grid
        self.timer.start(16)

    def editor_loop(self):
        pygame.event.pump(); self.active_scene.draw(self.viewport.surface); self.viewport.update_frame()
    def on_node_selected(self, item, col):
        n = self.node_map.get(id(item));
        if n: self.select_node(n)
    def clear_ui(self):
        self.name_edit.clear(); self.pos_x.setValue(0); self.pos_y.setValue(0)
