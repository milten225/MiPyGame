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
from core.node import SpriteNode, RigidBodyNode, AnimatedSpriteNode, TextUINode

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
        self.setWindowTitle("MipyGame Engine Pro - Contextual UX")
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

        # --- ТУЛБАР (МЕНЕДЖЕР СЦЕН) ---
        toolbar = QToolBar(); self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        toolbar.addWidget(QLabel(" 🎬 Сцена: "))
        self.scene_combo = QComboBox(); self.scene_combo.addItem("Level_1"); self.scene_combo.currentTextChanged.connect(self.switch_scene)
        toolbar.addWidget(self.scene_combo)
        
        btn_new_scene = QPushButton("➕ Новая сцена"); btn_new_scene.clicked.connect(self.create_scene); toolbar.addWidget(btn_new_scene)
        btn_del_scene = QPushButton("🗑️ Удалить сцену"); btn_del_scene.clicked.connect(self.delete_scene); toolbar.addWidget(btn_del_scene)
        toolbar.addSeparator()

        btn_add = QToolButton(); btn_add.setText("➕ Добавить узел ▾"); btn_add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        add_menu = QMenu()
        add_menu.addAction("🟩 2D Спрайт", lambda: self.spawn_node("sprite")); add_menu.addAction("🏃‍♂️ Аниматор", lambda: self.spawn_node("anim"))
        add_menu.addSeparator(); add_menu.addAction("📦 Физика (RigidBody)", lambda: self.spawn_node("physics"))
        add_menu.addSeparator(); add_menu.addAction("🔤 Текст", lambda: self.spawn_node("ui"))
        btn_add.setMenu(add_menu); toolbar.addWidget(btn_add)
        toolbar.addSeparator()
        act_play = QAction("▶ ЗАПУСК ИГРЫ", self); act_play.triggered.connect(self.launch_game); toolbar.addAction(act_play)

        # --- ЦЕНТР ---
        view_container = QWidget(); view_layout = QVBoxLayout(view_container)
        grid_toolbar = QHBoxLayout()
        self.chk_grid = QCheckBox("Сетка"); self.chk_grid.setChecked(True); self.chk_grid.stateChanged.connect(self.toggle_grid)
        self.chk_snap = QCheckBox("Магнит")
        btn_reset_cam = QPushButton("🎯 Сброс камеры"); btn_reset_cam.clicked.connect(self.reset_camera)
        btn_delete = QPushButton("🗑️ Удалить объект (Del)"); btn_delete.setStyleSheet("color: #ff4444;"); btn_delete.clicked.connect(self.delete_selected_node)
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
        
        # БЛОК 1: Трансформация (Виден всегда)
        self.grp_transform = QGroupBox("Трансформация")
        form_trans = QFormLayout(self.grp_transform)
        self.name_edit = QLineEdit(); self.name_edit.textChanged.connect(self.sync_to_node)
        self.pos_x = QDoubleSpinBox(); self.pos_x.setRange(-5000, 5000); self.pos_x.valueChanged.connect(self.sync_to_node)
        self.pos_y = QDoubleSpinBox(); self.pos_y.setRange(-5000, 5000); self.pos_y.valueChanged.connect(self.sync_to_node)
        self.size_w = QSpinBox(); self.size_w.setRange(1, 2000); self.size_w.valueChanged.connect(self.sync_to_node)
        self.size_h = QSpinBox(); self.size_h.setRange(1, 2000); self.size_h.valueChanged.connect(self.sync_to_node)
        self.z_index_box = QSpinBox(); self.z_index_box.setRange(-100, 100); self.z_index_box.valueChanged.connect(self.sync_to_node)
        form_trans.addRow("Имя:", self.name_edit); form_trans.addRow("Слой (Z):", self.z_index_box)
        form_trans.addRow("Поз X:", self.pos_x); form_trans.addRow("Поз Y:", self.pos_y)
        form_trans.addRow("Ширина:", self.size_w); form_trans.addRow("Высота:", self.size_h)
        ins_main_layout.addWidget(self.grp_transform)

        # БЛОК 2: Внешний вид (Виден для всех, кроме текста)
        self.grp_visual = QGroupBox("Внешний вид")
        form_vis = QFormLayout(self.grp_visual)
        self.color_btn = QPushButton("Выбрать цвет"); self.color_btn.clicked.connect(self.pick_color)
        form_vis.addRow("Цвет заливки:", self.color_btn)
        ins_main_layout.addWidget(self.grp_visual)

        # БЛОК 3: Физика (Динамический)
        self.grp_physics = QGroupBox("Свойства RigidBody")
        form_phys = QFormLayout(self.grp_physics)
        self.chk_static = QCheckBox("Статичный объект (Стена)"); self.chk_static.stateChanged.connect(self.sync_to_node)
        form_phys.addRow(self.chk_static)
        ins_main_layout.addWidget(self.grp_physics)

        # БЛОК 4: Анимация (Динамический)
        self.grp_anim = QGroupBox("Спрайт-Анимация")
        form_anim = QFormLayout(self.grp_anim)
        self.anim_frames = QSpinBox(); self.anim_frames.setRange(1, 60); self.anim_frames.valueChanged.connect(self.sync_to_node)
        self.anim_fps = QSpinBox(); self.anim_fps.setRange(1, 60); self.anim_fps.valueChanged.connect(self.sync_to_node)
        form_anim.addRow("Всего кадров:", self.anim_frames); form_anim.addRow("Скорость (FPS):", self.anim_fps)
        ins_main_layout.addWidget(self.grp_anim)

        # БЛОК 5: Текст (Динамический)
        self.grp_text = QGroupBox("Свойства Текста")
        form_text = QFormLayout(self.grp_text)
        self.ui_text = QLineEdit(); self.ui_text.textChanged.connect(self.sync_to_node)
        self.ui_font_size = QSpinBox(); self.ui_font_size.setRange(10, 200); self.ui_font_size.valueChanged.connect(self.sync_to_node)
        self.chk_is_ui = QCheckBox("Интерфейс (Игнорировать камеру)"); self.chk_is_ui.stateChanged.connect(self.sync_to_node)
        self.text_color_btn = QPushButton("Цвет текста"); self.text_color_btn.clicked.connect(self.pick_color)
        form_text.addRow("Содержимое:", self.ui_text)
        form_text.addRow("Размер шрифта:", self.ui_font_size)
        form_text.addRow("Рендер:", self.chk_is_ui)
        form_text.addRow("Цвет:", self.text_color_btn)
        ins_main_layout.addWidget(self.grp_text)

        ins_main_layout.addStretch() # Поджимаем всё наверх
        self.tabs.addTab(self.tab_inspector, "⚙ Свойства")

        # Вкладки скриптов и аудио
        self.tab_code = QWidget(); code_layout = QVBoxLayout(self.tab_code)
        self.code_edit = QTextEdit(); self.code_edit.setFont(QFont("Consolas", 10))
        btn_save = QPushButton("💾 Сохранить скрипт"); btn_save.clicked.connect(self.save_script)
        code_layout.addWidget(self.code_edit); code_layout.addWidget(btn_save)
        self.tabs.addTab(self.tab_code, "📄 Скрипт")
        
        self.tab_audio = QWidget(); audio_layout = QVBoxLayout(self.tab_audio)
        self.vol_music = QSlider(Qt.Orientation.Horizontal); self.vol_music.setRange(0, 100); self.vol_music.setValue(100)
        self.vol_music.valueChanged.connect(lambda v: pygame.mixer.music.set_volume(v / 100.0))
        audio_layout.addWidget(QLabel("🎵 Глобальная громкость музыки")); audio_layout.addWidget(self.vol_music); audio_layout.addStretch()
        self.tabs.addTab(self.tab_audio, "🔊 Аудио")

        self.dock_inspector.setWidget(self.tabs); self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_inspector)

        # --- НИЗ (АССЕТЫ) ---
        self.dock_assets = QDockWidget("Ресурсы", self); asset_widget = QWidget(); asset_layout = QVBoxLayout(asset_widget)
        btn_refresh = QPushButton("🔄 Обновить"); btn_refresh.clicked.connect(self.refresh_assets)
        self.asset_list = QListWidget(); self.asset_list.itemDoubleClicked.connect(self.apply_asset)
        asset_layout.addWidget(btn_refresh); asset_layout.addWidget(self.asset_list); self.dock_assets.setWidget(asset_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_assets)

        menubar = self.menuBar(); view_menu = menubar.addMenu("👁️ Окна")
        view_menu.addAction(self.dock_tree.toggleViewAction()); view_menu.addAction(self.dock_inspector.toggleViewAction()); view_menu.addAction(self.dock_assets.toggleViewAction())

    # --- УПРАВЛЕНИЕ СЦЕНАМИ ---
    def create_scene(self):
        name, ok = QInputDialog.getText(self, "Новая сцена", "Введите название сцены:")
        if ok and name and name not in self.scenes:
            self.scenes[name] = SceneTree()
            self.scene_combo.blockSignals(True); self.scene_combo.addItem(name); self.scene_combo.setCurrentText(name); self.scene_combo.blockSignals(False)
            self.switch_scene(name)

    def delete_scene(self):
        if len(self.scenes) <= 1:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить последнюю сцену!")
            return
        reply = QMessageBox.question(self, 'Подтверждение', f"Удалить сцену '{self.active_scene_name}' навсегда?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.scenes[self.active_scene_name]
            idx = self.scene_combo.findText(self.active_scene_name)
            self.scene_combo.blockSignals(True)
            self.scene_combo.removeItem(idx)
            self.scene_combo.blockSignals(False)
            self.switch_scene(self.scene_combo.currentText())

    def switch_scene(self, scene_name):
        if scene_name in self.scenes:
            self.active_scene_name = scene_name
            self.active_scene = self.scenes[scene_name]
            self.rebuild_tree_ui()

    def rebuild_tree_ui(self):
        self.tree.clear(); self.node_map.clear(); self.reverse_node_map.clear(); self.selected_node = None
        self.clear_ui()
        root_item = QTreeWidgetItem(self.tree, [f"Root ({self.active_scene_name})"])
        self.node_map[id(root_item)] = self.active_scene.root; self.reverse_node_map[self.active_scene.root] = root_item
        for child in self.active_scene.root.children: self._add_node_to_tree(child, root_item)
        self.tree.expandAll()

    def _add_node_to_tree(self, node, parent_item):
        item = QTreeWidgetItem(parent_item, [node.name])
        self.node_map[id(item)] = node; self.reverse_node_map[node] = item
        for child in node.children: self._add_node_to_tree(child, item)

    def setup_default_scene(self):
        box = RigidBodyNode("TestBox", 50, 50, is_static=False); box.position.update(350, 250)
        self.active_scene.root.add_child(box)
        self.rebuild_tree_ui()

    def reset_camera(self):
        self.active_scene.camera_x = 0; self.active_scene.camera_y = 0

    def delete_selected_node(self):
        if not self.selected_node: return
        if self.selected_node == self.active_scene.root:
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить корень сцены!")
            return
        if self.selected_node.parent: self.selected_node.parent.remove_child(self.selected_node)
        self.rebuild_tree_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete: self.delete_selected_node()

    # --- АССЕТЫ ---
    def refresh_assets(self):
        self.asset_list.clear()
        if os.path.exists("assets"):
            for file in os.listdir("assets"):
                if file.endswith(('.png', '.jpg', '.wav', '.mp3')): self.asset_list.addItem(file)

    def apply_asset(self, item):
        if self.selected_node and item.text().endswith(('.png', '.jpg')) and not isinstance(self.selected_node, TextUINode):
            self.selected_node.image_path = os.path.join("assets", item.text())
            if hasattr(self.selected_node, 'update_surface'): self.selected_node.update_surface()

    def toggle_grid(self, state): self.active_scene.show_grid = (state == 2)

    def spawn_node(self, type_str):
        if type_str == "sprite": obj = SpriteNode(f"Sprite_{len(self.node_map)}", 50, 50)
        elif type_str == "physics": obj = RigidBodyNode(f"Box_{len(self.node_map)}", 50, 50)
        elif type_str == "ui": obj = TextUINode(f"Text_{len(self.node_map)}")
        elif type_str == "anim": obj = AnimatedSpriteNode(f"Anim_{len(self.node_map)}", 100, 100)
        
        obj.position.update(self.active_scene.camera_x + 350, self.active_scene.camera_y + 250)
        self.active_scene.root.add_child(obj)
        self.rebuild_tree_ui(); self.select_node(obj)

    def on_camera_pan(self, dx, dy): self.active_scene.camera_x -= dx; self.active_scene.camera_y -= dy

    def on_canvas_click(self, x, y):
        node = self.active_scene.get_node_at(x + self.active_scene.camera_x, y + self.active_scene.camera_y)
        if node: self.select_node(node)
        else: self.active_scene.clear_selection(); self.selected_node = None; self.tree.clearSelection(); self.clear_ui()

    def on_canvas_drag(self, dx, dy, is_resizing):
        if self.selected_node and self.selected_node != self.active_scene.root:
            if is_resizing and hasattr(self.selected_node, 'width'):
                self.selected_node.width += dx; self.selected_node.height += dy; self.selected_node.update_surface()
            else:
                self.selected_node.position.x += dx; self.selected_node.position.y += dy
            self.refresh_ui()

    def on_canvas_drop(self):
        if self.selected_node and self.chk_snap.isChecked() and self.selected_node != self.active_scene.root:
            g = self.active_scene.grid_size
            self.selected_node.position.x = round(self.selected_node.position.x / g) * g
            self.selected_node.position.y = round(self.selected_node.position.y / g) * g
            self.refresh_ui()

    def select_node(self, node):
        self.active_scene.clear_selection(); self.selected_node = node; self.selected_node.selected = True
        ui_item = self.reverse_node_map.get(node); 
        if ui_item: self.tree.setCurrentItem(ui_item)
        self.refresh_ui()

    def clear_ui(self):
        self.name_edit.blockSignals(True); self.name_edit.clear(); self.name_edit.blockSignals(False)
        self.pos_x.blockSignals(True); self.pos_x.setValue(0); self.pos_x.blockSignals(False)
        self.pos_y.blockSignals(True); self.pos_y.setValue(0); self.pos_y.blockSignals(False)
        self.size_w.blockSignals(True); self.size_w.setValue(0); self.size_w.blockSignals(False)
        self.size_h.blockSignals(True); self.size_h.setValue(0); self.size_h.blockSignals(False)
        self.grp_visual.setVisible(False); self.grp_physics.setVisible(False); self.grp_anim.setVisible(False); self.grp_text.setVisible(False)
        self.code_edit.clear()

    # МАГИЯ КОНТЕКСТНОГО ИНСПЕКТОРА
    def refresh_ui(self):
        if not self.selected_node: return
        self.name_edit.blockSignals(True); self.name_edit.setText(self.selected_node.name); self.name_edit.blockSignals(False)
        self.pos_x.blockSignals(True); self.pos_x.setValue(self.selected_node.position.x); self.pos_x.blockSignals(False)
        self.pos_y.blockSignals(True); self.pos_y.setValue(self.selected_node.position.y); self.pos_y.blockSignals(False)
        self.z_index_box.blockSignals(True); self.z_index_box.setValue(self.selected_node.z_index); self.z_index_box.blockSignals(False)
        
        # Обновляем ширину и высоту (если есть)
        if hasattr(self.selected_node, 'width'):
            self.size_w.blockSignals(True); self.size_w.setValue(self.selected_node.width); self.size_w.blockSignals(False)
            self.size_h.blockSignals(True); self.size_h.setValue(self.selected_node.height); self.size_h.blockSignals(False)

        # ДИНАМИЧЕСКОЕ СКРЫТИЕ БЛОКОВ
        self.grp_visual.setVisible(not isinstance(self.selected_node, TextUINode))
        self.grp_physics.setVisible(isinstance(self.selected_node, RigidBodyNode))
        self.grp_anim.setVisible(isinstance(self.selected_node, AnimatedSpriteNode))
        self.grp_text.setVisible(isinstance(self.selected_node, TextUINode))

        if isinstance(self.selected_node, RigidBodyNode): 
            self.chk_static.blockSignals(True); self.chk_static.setChecked(self.selected_node.is_static); self.chk_static.blockSignals(False)
        if isinstance(self.selected_node, AnimatedSpriteNode): 
            self.anim_frames.blockSignals(True); self.anim_frames.setValue(self.selected_node.frames); self.anim_frames.blockSignals(False)
            self.anim_fps.blockSignals(True); self.anim_fps.setValue(self.selected_node.anim_fps); self.anim_fps.blockSignals(False)
        if isinstance(self.selected_node, TextUINode):
            self.ui_text.blockSignals(True); self.ui_text.setText(self.selected_node.text); self.ui_text.blockSignals(False)
            self.ui_font_size.blockSignals(True); self.ui_font_size.setValue(self.selected_node.font_size); self.ui_font_size.blockSignals(False)
            self.chk_is_ui.blockSignals(True); self.chk_is_ui.setChecked(self.selected_node.is_ui); self.chk_is_ui.blockSignals(False)
            
        self.code_edit.setPlainText(self.selected_node.custom_code)

    def sync_to_node(self):
        if not self.selected_node: return
        self.selected_node.name = self.name_edit.text()
        self.selected_node.position.x = self.pos_x.value(); self.selected_node.position.y = self.pos_y.value()
        self.selected_node.z_index = self.z_index_box.value()
        
        # Запрещаем менять размер текстового узла вручную (он зависит от шрифта)
        if hasattr(self.selected_node, 'width') and not isinstance(self.selected_node, TextUINode):
            self.selected_node.width = self.size_w.value(); self.selected_node.height = self.size_h.value()
            self.selected_node.update_surface()

        if isinstance(self.selected_node, RigidBodyNode): self.selected_node.is_static = self.chk_static.isChecked()
        if isinstance(self.selected_node, AnimatedSpriteNode): 
            self.selected_node.frames = self.anim_frames.value(); self.selected_node.anim_fps = self.anim_fps.value()
        if isinstance(self.selected_node, TextUINode):
            self.selected_node.text = self.ui_text.text()
            self.selected_node.font_size = self.ui_font_size.value()
            self.selected_node.is_ui = self.chk_is_ui.isChecked()
            self.selected_node.update_surface()
            
        ui_item = self.reverse_node_map.get(self.selected_node)
        if ui_item: ui_item.setText(0, self.selected_node.name)

    def pick_color(self):
        if not self.selected_node: return
        color = QColorDialog.getColor()
        if color.isValid():
            if isinstance(self.selected_node, TextUINode):
                self.selected_node.color = (color.red(), color.green(), color.blue())
            else:
                self.selected_node.image_path = "" 
                self.selected_node.color = (color.red(), color.green(), color.blue())
            self.selected_node.update_surface()

    def save_script(self):
        if self.selected_node: self.selected_node.custom_code = self.code_edit.toPlainText()

    def on_node_selected(self, item, column):
        node = self.node_map.get(id(item)); 
        if node: self.select_node(node)

    def launch_game(self):
        self.timer.stop(); self.active_scene.root.save_state()
        was_grid = self.active_scene.show_grid; self.active_scene.show_grid = False; self.active_scene.clear_selection()
        start_cx, start_cy = self.active_scene.camera_x, self.active_scene.camera_y
        self.active_scene.camera_x = 0; self.active_scene.camera_y = 0

        self.active_scene.start_physics()

        pygame.display.init(); screen = pygame.display.set_mode((800, 600)); clock = pygame.time.Clock(); running = True
        
        while running:
            dt = clock.tick(60) / 1000.0
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
            self.active_scene.update(dt); self.active_scene.draw(screen); pygame.display.flip()
            
        pygame.display.quit(); pygame.display.init()
        self.active_scene.stop_physics()
        
        self.active_scene.root.restore_state()
        self.active_scene.camera_x, self.active_scene.camera_y = start_cx, start_cy; self.active_scene.show_grid = was_grid
        if self.selected_node: self.selected_node.selected = True
        self.timer.start(16)

    def editor_loop(self):
        pygame.event.pump(); self.active_scene.draw(self.viewport.surface); self.viewport.update_frame()