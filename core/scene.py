import pygame
import pymunk
import time
from typing import Dict, List, Optional
from core.node import Node2D
from core.object_type import ObjectType, ObjectKind

class SceneTree:
    """
    SceneTree manages the hierarchy of Node2D instances and the Pymunk physics world.
    It is responsible for updating and drawing the scene.
    """

    def __init__(self):
        # We need a dummy object type for the root node
        self._root_type = ObjectType("RootType")
        self.root: Node2D = Node2D(self._root_type, "Root")

        self.camera_x: float = 0.0
        self.camera_y: float = 0.0

        # Grid settings
        self.show_grid: bool = True
        self.grid_size: int = 50
        self.background_color: tuple = (30, 30, 35)
        self.grid_color: tuple = (50, 50, 55)

        # Physics world
        self.space: Optional[pymunk.Space] = None
        self.gravity: tuple = (0, 900)

        # Mapping between Node2D and Pymunk bodies
        self.physics_bodies: Dict[Node2D, pymunk.Body] = {}

        # Volatile state for nodes (animations, etc.)
        self.node_state: Dict[Node2D, dict] = {}

    def add_node(self, node: Node2D, parent: Optional[Node2D] = None) -> None:
        """Adds a node to the hierarchy."""
        if parent is None:
            parent = self.root

        node.parent = parent
        parent.children.append(node)
        self.node_state[node] = {"anim_frame": 0, "anim_timer": 0.0}

    def remove_node(self, node: Node2D) -> None:
        """Removes a node from the hierarchy and physics world."""
        if node.parent:
            node.parent.children.remove(node)
            node.parent = None

        if node in self.physics_bodies:
            body = self.physics_bodies.pop(node)
            if self.space:
                for shape in body.shapes:
                    self.space.remove(shape)
                self.space.remove(body)

        if node in self.node_state:
            del self.node_state[node]

    def start_physics(self) -> None:
        """Initializes the Pymunk space and creates physics bodies for nodes."""
        self.space = pymunk.Space()
        self.space.gravity = self.gravity
        self._init_physics_recursive(self.root)

    def _init_physics_recursive(self, node: Node2D) -> None:
        if node != self.root:
            obj_type = node.object_type

            width, height = obj_type.width, obj_type.height
            mass = 1.0
            moment = pymunk.moment_for_box(mass, (width, height))

            body_type = pymunk.Body.STATIC if obj_type.is_static else pymunk.Body.DYNAMIC
            body = pymunk.Body(mass, moment, body_type=body_type)

            pos = node.get_position()
            body.position = (pos.x + width / 2, pos.y + height / 2)

            shape = pymunk.Poly.create_box(body, (width, height))
            shape.friction = 0.5
            shape.elasticity = 0.5

            self.space.add(body, shape)
            self.physics_bodies[node] = body

        for child in node.children:
            self._init_physics_recursive(child)

    def stop_physics(self) -> None:
        """Clears the physics world."""
        self.space = None
        self.physics_bodies.clear()

    def update(self, dt: float) -> None:
        """Updates the physics and the node behaviors."""
        if self.space:
            self.space.step(dt)
            # Sync node positions with physics bodies
            for node, body in self.physics_bodies.items():
                if not node.object_type.is_static:
                    width, height = node.object_type.width, node.object_type.height
                    node.set_position(body.position.x - width / 2, body.position.y - height / 2)

        self._update_recursive(self.root, dt)

    def _update_recursive(self, node: Node2D, dt: float) -> None:
        # Update volatile state (animations)
        if node in self.node_state:
            state = self.node_state[node]
            if node.object_type.kind == ObjectKind.ANIMATED and node.object_type.frames > 1:
                state["anim_timer"] += dt
                if state["anim_timer"] >= 1.0 / node.object_type.fps:
                    state["anim_timer"] = 0
                    state["anim_frame"] = (state["anim_frame"] + 1) % node.object_type.frames

        # Execute behavior code if present
        if node.object_type.behavior_code.strip():
            try:
                local_scope = {'node': node, 'dt': dt, 'scene': self, 'pygame': pygame}
                exec(node.object_type.behavior_code, globals(), local_scope)
            except Exception as e:
                pass

        for child in node.children:
            self._update_recursive(child, dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Renders the scene."""
        surface.fill(self.background_color)

        # Draw grid
        if self.show_grid:
            w, h = surface.get_size()
            offset_x = -self.camera_x % self.grid_size
            offset_y = -self.camera_y % self.grid_size
            for x in range(int(offset_x), w, self.grid_size):
                pygame.draw.line(surface, self.grid_color, (x, 0), (x, h))
            for y in range(int(offset_y), h, self.grid_size):
                pygame.draw.line(surface, self.grid_color, (0, y), (w, y))

        all_nodes = self._get_all_nodes_flat(self.root)
        all_nodes.sort(key=lambda n: n.get_z_index())

        for node in all_nodes:
            if node == self.root: continue

            pos = node.get_position()
            ot = node.object_type
            render_rect = pygame.Rect(pos.x - self.camera_x, pos.y - self.camera_y, ot.width, ot.height)

            if ot.kind == ObjectKind.TEXT:
                pygame.font.init()
                font = pygame.font.Font(None, ot.font_size)
                text_surf = font.render(ot.text_content, True, ot.color)
                surface.blit(text_surf, (pos.x - self.camera_x, pos.y - self.camera_y))
            elif ot.kind == ObjectKind.ANIMATED:
                if ot.sprite_path:
                    try:
                        full_sprite = pygame.image.load(ot.sprite_path)
                        frame_w = full_sprite.get_width() / ot.frames
                        curr_frame = self.node_state.get(node, {}).get("anim_frame", 0)
                        crop_rect = pygame.Rect(curr_frame * frame_w, 0, frame_w, full_sprite.get_height())
                        frame_surf = pygame.Surface((frame_w, full_sprite.get_height()), pygame.SRCALPHA)
                        frame_surf.blit(full_sprite, (0, 0), crop_rect)
                        frame_surf = pygame.transform.scale(frame_surf, (ot.width, ot.height))
                        surface.blit(frame_surf, render_rect)
                    except:
                        pygame.draw.rect(surface, (255, 0, 255), render_rect)
                else:
                    pygame.draw.rect(surface, ot.color, render_rect)
            else: # SPRITE
                if ot.sprite_path:
                    try:
                        image = pygame.image.load(ot.sprite_path)
                        image = pygame.transform.scale(image, (ot.width, ot.height))
                        surface.blit(image, render_rect)
                    except:
                        pygame.draw.rect(surface, (255, 0, 255), render_rect)
                else:
                    pygame.draw.rect(surface, ot.color, render_rect)

    def _get_all_nodes_flat(self, node: Node2D) -> List[Node2D]:
        flat_list = [node]
        for child in node.children:
            flat_list.extend(self._get_all_nodes_flat(child))
        return flat_list
