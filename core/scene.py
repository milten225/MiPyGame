import pygame
import pymunk
from core.node import Node2D

class SceneTree:
    def __init__(self):
        self.root = Node2D("Root")
        self.camera_x = 0; self.camera_y = 0
        self.show_grid = True
        self.grid_size = 50
        
        # Физический мир
        self.space = None
        self.gravity_y = 900
    
    def clear_selection(self, node=None):
        if node is None: node = self.root
        node.selected = False
        for child in node.children: self.clear_selection(child)

    def get_node_at(self, x, y, node=None):
        if node is None: node = self.root
        for child in reversed(node.children):
            found = self.get_node_at(x, y, child)
            if found: return found
        if hasattr(node, 'rect') and node.rect.collidepoint(x, y): return node
        return None

    def start_physics(self):
        """Создает физический мир при нажатии PLAY"""
        self.space = pymunk.Space()
        self.space.gravity = (0, self.gravity_y)
        self._init_node_physics(self.root)

    def _init_node_physics(self, node):
        if hasattr(node, 'init_physics'):
            node.init_physics(self.space)
        for child in node.children:
            self._init_node_physics(child)

    def stop_physics(self):
        """Убивает физику при возврате в редактор"""
        self.space = None

    def update(self, dt):
        if self.space: # Если физика запущена - делаем шаг симуляции
            self.space.step(dt)
        self.root.update(dt)

    def draw(self, surface):
        surface.fill((30, 30, 35))
        if self.show_grid:
            w, h = surface.get_size()
            offset_x = -self.camera_x % self.grid_size
            offset_y = -self.camera_y % self.grid_size
            for x in range(int(offset_x), w, self.grid_size): pygame.draw.line(surface, (50, 50, 55), (x, 0), (x, h))
            for y in range(int(offset_y), h, self.grid_size): pygame.draw.line(surface, (50, 50, 55), (0, y), (w, y))

        self.root.draw(surface, self.camera_x, self.camera_y)