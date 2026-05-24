import pygame
import pymunk
from typing import Dict, List, Optional
from core.node import Node2D
from core.object_type import ObjectType

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

        # Physics world
        self.space: Optional[pymunk.Space] = None
        self.gravity: tuple = (0, 900)

        # Mapping between Node2D and Pymunk bodies
        self.physics_bodies: Dict[Node2D, pymunk.Body] = {}

    def add_node(self, node: Node2D, parent: Optional[Node2D] = None) -> None:
        """Adds a node to the hierarchy."""
        if parent is None:
            parent = self.root

        node.parent = parent
        parent.children.append(node)

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

    def start_physics(self) -> None:
        """Initializes the Pymunk space and creates physics bodies for nodes."""
        self.space = pymunk.Space()
        self.space.gravity = self.gravity
        self._init_physics_recursive(self.root)

    def _init_physics_recursive(self, node: Node2D) -> None:
        if node != self.root:
            obj_type = node.object_type

            # Simple box physics for now (could be expanded)
            # We assume a default size if not specified elsewhere (e.g. 50x50)
            width, height = 50, 50
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
                    # Subtracting half-width/height to sync with top-left rendering
                    node.set_position(body.position.x - 25, body.position.y - 25)

        self._update_recursive(self.root, dt)

    def _update_recursive(self, node: Node2D, dt: float) -> None:
        # Execute behavior code if present
        if node.object_type.behavior_code.strip():
            try:
                # We can provide 'node', 'dt', and 'scene' to the behavior script
                local_scope = {'node': node, 'dt': dt, 'scene': self, 'pygame': pygame}
                exec(node.object_type.behavior_code, globals(), local_scope)
            except Exception as e:
                # In a real engine, we'd log this to an editor console
                pass

        for child in node.children:
            self._update_recursive(child, dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Renders the scene."""
        # Sort all nodes by Z-index for correct draw order
        all_nodes = self._get_all_nodes_flat(self.root)
        all_nodes.sort(key=lambda n: n.get_z_index())

        for node in all_nodes:
            if node == self.root:
                continue

            pos = node.get_position()
            sprite_path = node.object_type.sprite_path

            # Simple rendering logic: if sprite exists, draw it; else draw a rect
            rect = pygame.Rect(pos.x - self.camera_x, pos.y - self.camera_y, 50, 50)

            # In a real engine, we'd cache these surfaces
            if sprite_path:
                try:
                    image = pygame.image.load(sprite_path)
                    image = pygame.transform.scale(image, (50, 50))
                    surface.blit(image, rect)
                except:
                    pygame.draw.rect(surface, (255, 0, 255), rect) # Error purple
            else:
                pygame.draw.rect(surface, (100, 150, 250), rect) # Default blue

    def _get_all_nodes_flat(self, node: Node2D) -> List[Node2D]:
        flat_list = [node]
        for child in node.children:
            flat_list.extend(self._get_all_nodes_flat(child))
        return flat_list
