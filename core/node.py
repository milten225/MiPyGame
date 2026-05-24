import pygame
import os
import pymunk

class Node2D:
    def __init__(self, name="Node"):
        self.name = name; self.parent = None; self.children = []
        self.position = pygame.math.Vector2(0, 0)
        self.selected = False; self.custom_code = ""; self.z_index = 0
        self.is_ui = False  
        self._start_pos = pygame.math.Vector2(0, 0)

    def add_child(self, child_node):
        child_node.parent = self
        self.children.append(child_node)

    # НОВОЕ: Отсоединение и удаление объекта
    def remove_child(self, child_node):
        if child_node in self.children:
            self.children.remove(child_node)
            child_node.parent = None

    def get_global_position(self):
        if self.parent: return self.parent.get_global_position() + self.position
        return self.position

    def save_state(self):
        self._start_pos = pygame.math.Vector2(self.position.x, self.position.y)
        for child in self.children: child.save_state()

    def restore_state(self):
        self.position.x = self._start_pos.x
        self.position.y = self._start_pos.y
        if hasattr(self, 'update_surface'): self.update_surface()
        for child in self.children: child.restore_state()

    def update(self, dt):
        if self.custom_code.strip():
            try:
                keys = pygame.key.get_pressed()
                local_scope = {'node': self, 'dt': dt, 'pygame': pygame, 'keys': keys, 'scene': self.get_root()}
                exec(self.custom_code, globals(), local_scope)
            except Exception as e:
                pass # Скрываем спам ошибок в консоль для удобства
        for child in self.children: child.update(dt)

    def get_root(self):
        root = self
        while root.parent: root = root.parent
        return root

    def draw(self, surface, cam_x=0, cam_y=0):
        self.children.sort(key=lambda x: x.z_index)
        for child in self.children:
            cx = 0 if child.is_ui else cam_x
            cy = 0 if child.is_ui else cam_y
            child.draw(surface, cx, cy)

class SpriteNode(Node2D):
    def __init__(self, name="Sprite", width=100, height=100, color=(100, 150, 250)):
        super().__init__(name)
        self.width = width; self.height = height
        self.color = color; self.image_path = ""
        self.update_surface()

    def update_surface(self):
        if self.image_path and os.path.exists(self.image_path):
            try:
                img = pygame.image.load(self.image_path)
                self.surface = pygame.transform.smoothscale(img, (max(1, int(self.width)), max(1, int(self.height))))
            except:
                self.surface = pygame.Surface((max(1, int(self.width)), max(1, int(self.height)))); self.surface.fill((255, 0, 255))
        else:
            self.surface = pygame.Surface((max(1, int(self.width)), max(1, int(self.height)))); self.surface.fill(self.color)
        self.rect = self.surface.get_rect()

    def draw(self, surface, cam_x=0, cam_y=0):
        global_pos = self.get_global_position()
        self.rect.topleft = (global_pos.x - cam_x, global_pos.y - cam_y)
        surface.blit(self.surface, self.rect)
        if self.selected: pygame.draw.rect(surface, (255, 255, 255), self.rect, 2)
        super().draw(surface, cam_x, cam_y)

class AnimatedSpriteNode(SpriteNode):
    def __init__(self, name="AnimSprite", width=100, height=100):
        super().__init__(name, width, height, (255, 200, 100))
        self.frames = 1        
        self.anim_fps = 10     
        self._current_frame = 0
        self._timer = 0

    def update(self, dt):
        super().update(dt)
        if self.frames > 1:
            self._timer += dt
            if self._timer >= 1.0 / self.anim_fps:
                self._timer = 0
                self._current_frame = (self._current_frame + 1) % self.frames

    def draw(self, surface, cam_x=0, cam_y=0):
        global_pos = self.get_global_position()
        self.rect.topleft = (global_pos.x - cam_x, global_pos.y - cam_y)
        frame_width = self.width / max(1, self.frames)
        crop_rect = pygame.Rect(self._current_frame * frame_width, 0, frame_width, self.height)
        try: surface.blit(self.surface, self.rect, crop_rect)
        except: surface.blit(self.surface, self.rect) 
        if self.selected: pygame.draw.rect(surface, (255, 255, 255), (self.rect.x, self.rect.y, frame_width, self.height), 2)
        Node2D.draw(self, surface, cam_x, cam_y)

class RigidBodyNode(SpriteNode):
    def __init__(self, name="PhysicsBody", width=50, height=50, is_static=False):
        super().__init__(name, width, height, (200, 100, 50))
        self.is_static = is_static
        self.mass = 1.0
        self.elasticity = 0.5 
        self.friction = 0.5   
        self.pm_body = None
        self.pm_shape = None

    def init_physics(self, space):
        body_type = pymunk.Body.STATIC if self.is_static else pymunk.Body.DYNAMIC
        self.pm_body = pymunk.Body(self.mass, pymunk.moment_for_box(self.mass, (self.width, self.height)), body_type=body_type)
        self.pm_body.position = (self.get_global_position().x + self.width/2, self.get_global_position().y + self.height/2)
        self.pm_shape = pymunk.Poly.create_box(self.pm_body, (self.width, self.height))
        self.pm_shape.elasticity = self.elasticity
        self.pm_shape.friction = self.friction
        space.add(self.pm_body, self.pm_shape)

    def update(self, dt):
        super().update(dt)
        if self.pm_body and not self.is_static:
            self.position.x = self.pm_body.position.x - self.width/2
            self.position.y = self.pm_body.position.y - self.height/2

class TextUINode(Node2D):
    def __init__(self, name="TextNode", text="Hello World"):
        super().__init__(name)
        self.is_ui = True       # По умолчанию это UI, но теперь это можно менять
        self.text = text
        self.color = (255, 255, 255)
        self.font_size = 32     # Влияет на размер текста
        
        # Для текста ширина и высота вычисляются автоматически из шрифта
        self.width = 100 
        self.height = 50
        self.update_surface()

    def update_surface(self):
        pygame.font.init()
        font = pygame.font.Font(None, max(10, self.font_size)) # Защита от краша при размере < 10
        self.surface = font.render(self.text, True, self.color)
        self.rect = self.surface.get_rect()
        # Обновляем системные размеры под размер отрендеренного текста
        self.width = self.rect.width
        self.height = self.rect.height

    def draw(self, surface, cam_x=0, cam_y=0):
        global_pos = self.get_global_position()
        
        # Если это UI - игнорируем камеру. Если нет - отнимаем камеру (World Space)
        render_x = global_pos.x if self.is_ui else global_pos.x - cam_x
        render_y = global_pos.y if self.is_ui else global_pos.y - cam_y
        
        self.rect.topleft = (render_x, render_y)
        surface.blit(self.surface, self.rect)
        
        if self.selected: 
            pygame.draw.rect(surface, (0, 255, 0), self.rect, 1)
            
        # Вызываем базовый метод для отрисовки дочерних объектов
        super().draw(surface, cam_x, cam_y)