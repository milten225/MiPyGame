import pygame
from typing import List, Optional
from core.object_type import ObjectType

class Node2D:
    """
    Node2D represents an instance of an ObjectType on the scene.
    It stores only unique data such as position, name, and Z-index.
    """

    def __init__(
        self,
        object_type: ObjectType,
        name: str,
        x: float = 0.0,
        y: float = 0.0,
        z_index: int = 0
    ):
        self._object_type: ObjectType = object_type
        self._name: str = name
        self._position: pygame.math.Vector2 = pygame.math.Vector2(x, y)
        self._z_index: int = z_index
        self._start_position: pygame.math.Vector2 = pygame.math.Vector2(x, y)

        self.parent: Optional['Node2D'] = None
        self.children: List['Node2D'] = []

    @property
    def object_type(self) -> ObjectType: return self._object_type

    def set_position(self, x: float, y: float) -> None: self._position.update(x, y)
    def get_position(self) -> pygame.math.Vector2: return self._position

    def get_global_position(self) -> pygame.math.Vector2:
        """Returns the world-space position (relative to all parents)."""
        if self.parent:
            return self.parent.get_global_position() + self._position
        return self._position

    def set_name(self, name: str) -> None: self._name = name
    def get_name(self) -> str: return self._name

    def set_z_index(self, z_index: int) -> None: self._z_index = z_index
    def get_z_index(self) -> int: return self._z_index

    def save_state(self) -> None: self._start_position.update(self._position.x, self._position.y)
    def restore_state(self) -> None: self._position.update(self._start_position.x, self._start_position.y)

    def __repr__(self) -> str:
        return f"<Node2D(name='{self._name}', type='{self._object_type.name}', pos={self._position})>"
