import pygame
import pymunk
from typing import Dict, List, Optional
from core.node import Node2D
from core.object_type import ObjectType, ObjectKind

class SceneTree:
    """
    SceneTree manages the hierarchy of Node2D instances and the Pymunk physics world.
    """

    def __init__(self):
        self._root_type = ObjectType("RootType")
        self.root: Node2D = Node2D(self._root_type, "Root")
        self.camera_x: float = 0.0
        self.camera_y: float = 0.0
        self.game_camera_x: float = 0.0
        self.game_camera_y: float = 0.0
        self.show_grid: bool = True
        self.grid_size: int = 50
        self.background_color: tuple = (30, 30, 35)
        self.grid_color: tuple = (50, 50, 55)
        self.space: Optional[pymunk.Space] = None
        self.gravity: tuple = (0, 900)
        self.physics_bodies: Dict[Node2D, pymunk.Body] = {}
        self.node_state: Dict[Node2D, dict] = {}
        self.is_playing: bool = False

    def add_node(self, node: Node2D, parent: Optional[Node2D] = None) -> None:
        if parent is None: parent = self.root
        node.parent = parent
        parent.children.append(node)
        self.node_state[node] = {"anim_frame": 0, "anim_timer": 0.0}

    def remove_node(self, node: Node2D) -> None:
        """Recursively removes node and its children from hierarchy and physics."""
        for child in list(node.children):
            self.remove_node(child)

        if node.parent:
            node.parent.children.remove(node)
            node.parent = None

        if node in self.physics_bodies:
            body = self.physics_bodies.pop(node)
            if self.space:
                for shape in body.shapes: self.space.remove(shape)
                self.space.remove(body)
        if node in self.node_state: del self.node_state[node]

    def save_state(self) -> None: self._save_recursive(self.root)
    def _save_recursive(self, node: Node2D) -> None:
        node.save_state()
        for child in node.children: self._save_recursive(child)

    def restore_state(self) -> None: self._restore_recursive(self.root)
    def _restore_recursive(self, node: Node2D) -> None:
        node.restore_state()
        for child in node.children: self._restore_recursive(child)

    def start_physics(self) -> None:
        self.is_playing = True
        self.game_camera_x = self.game_camera_y = 0
        self.space = pymunk.Space()
        self.space.gravity = self.gravity
        self._init_physics_recursive(self.root)
        self._on_start_recursive(self.root)

    def _on_start_recursive(self, node: Node2D) -> None:
        for behavior in node.object_type.behaviors: behavior.on_start(node)
        for child in node.children: self._on_start_recursive(child)

    def _init_physics_recursive(self, node: Node2D) -> None:
        if node != self.root:
            ot = node.object_type
            mass = 1.0
            moment = pymunk.moment_for_box(mass, (ot.width, ot.height))
            body = pymunk.Body(mass, moment, body_type=pymunk.Body.STATIC if ot.is_static else pymunk.Body.DYNAMIC)
            gpos = node.get_global_position()
            body.position = (gpos.x + ot.width / 2, gpos.y + ot.height / 2)
            shape = pymunk.Poly.create_box(body, (ot.width, ot.height))
            shape.friction = 0.5; shape.elasticity = 0.5
            self.space.add(body, shape)
            self.physics_bodies[node] = body
        for child in node.children: self._init_physics_recursive(child)

    def stop_physics(self) -> None:
        self.is_playing = False; self.space = None; self.physics_bodies.clear()

    def update(self, dt: float) -> None:
        self._update_recursive(self.root, dt)
        if self.space:
            self.space.step(dt)
            for node, body in self.physics_bodies.items():
                if not node.object_type.is_static:
                    ot = node.object_type
                    # Update local position based on global body movement (simplified for now)
                    parent_gpos = node.parent.get_global_position() if node.parent else pygame.math.Vector2(0,0)
                    new_gpos_x = body.position.x - ot.width / 2
                    new_gpos_y = body.position.y - ot.height / 2
                    node.set_position(new_gpos_x - parent_gpos.x, new_gpos_y - parent_gpos.y)

    def _update_recursive(self, node: Node2D, dt: float) -> None:
        if node in self.node_state:
            state, ot = self.node_state[node], node.object_type
            if ot.kind == ObjectKind.ANIMATED and ot.frames > 1:
                state["anim_timer"] += dt
                if state["anim_timer"] >= 1.0 / ot.fps:
                    state["anim_timer"] = 0; state["anim_frame"] = (state["anim_frame"] + 1) % ot.frames
        if self.is_playing:
            for behavior in node.object_type.behaviors: behavior.on_update(node, dt, self)
        for child in node.children: self._update_recursive(child, dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(self.background_color)
        cx, cy = (self.game_camera_x if self.is_playing else self.camera_x), (self.game_camera_y if self.is_playing else self.camera_y)
        if self.show_grid and not self.is_playing:
            w, h = surface.get_size()
            for x in range(int(-cx % self.grid_size), w, self.grid_size): pygame.draw.line(surface, self.grid_color, (x, 0), (x, h))
            for y in range(int(-cy % self.grid_size), h, self.grid_size): pygame.draw.line(surface, self.grid_color, (0, y), (w, y))

        all_nodes = self._get_all_nodes_flat(self.root)
        all_nodes.sort(key=lambda n: n.get_z_index())
        for node in all_nodes:
            if node == self.root: continue
            gpos, ot = node.get_global_position(), node.object_type
            rx, ry = gpos.x - cx, gpos.y - cy

            if ot.kind == ObjectKind.ANIMATED and ot.sprite_path:
                full_surf = ot.get_render_surface()
                frame_w = full_surf.get_width() / ot.frames
                curr_f = self.node_state.get(node, {}).get("anim_frame", 0)
                frame_surf = pygame.Surface((frame_w, full_surf.get_height()), pygame.SRCALPHA)
                frame_surf.blit(full_surf, (0, 0), pygame.Rect(curr_f * frame_w, 0, frame_w, full_surf.get_height()))
                surface.blit(pygame.transform.scale(frame_surf, (ot.width, ot.height)), (rx, ry))
            else:
                surface.blit(ot.get_render_surface(), (rx, ry))

    def _get_all_nodes_flat(self, node: Node2D) -> List[Node2D]:
        flat = [node]
        for child in node.children: flat.extend(self._get_all_nodes_flat(child))
        return flat

    def get_node_at(self, x: float, y: float) -> Optional[Node2D]:
        """Hit test for nodes using global positions."""
        for node in reversed(self._get_all_nodes_flat(self.root)):
            if node == self.root: continue
            gp, ot = node.get_global_position(), node.object_type
            if pygame.Rect(gp.x, gp.y, ot.width, ot.height).collidepoint(x, y): return node
        return None
