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
        """
        Initializes a Node2D instance.

        Args:
            object_type (ObjectType): The type this instance belongs to.
            name (str): Unique name of the instance.
            x (float): Initial X position.
            y (float): Initial Y position.
            z_index (int): Rendering order.
        """
        self._object_type: ObjectType = object_type
        self._name: str = name
        self._position: pygame.math.Vector2 = pygame.math.Vector2(x, y)
        self._z_index: int = z_index

        # State restoration
        self._start_position: pygame.math.Vector2 = pygame.math.Vector2(x, y)

        # Hierarchy attributes
        self.parent: Optional['Node2D'] = None
        self.children: List['Node2D'] = []

    @property
    def object_type(self) -> ObjectType:
        return self._object_type

    # Methods for position management
    def set_position(self, x: float, y: float) -> None:
        """Sets the local position of the node."""
        self._position.update(x, y)

    def get_position(self) -> pygame.math.Vector2:
        """Returns the local position of the node."""
        return self._position

    # Methods for name management
    def set_name(self, name: str) -> None:
        """Sets the name of the instance."""
        self._name = name

    def get_name(self) -> str:
        """Returns the name of the instance."""
        return self._name

    # Methods for Z-index management
    def set_z_index(self, z_index: int) -> None:
        """Sets the Z-index (rendering order)."""
        self._z_index = z_index

    def get_z_index(self) -> int:
        """Returns the Z-index."""
        return self._z_index

    # State management
    def save_state(self) -> None:
        """Saves current position as start position."""
        self._start_position.update(self._position.x, self._position.y)

    def restore_state(self) -> None:
        """Restores position from start position."""
        self._position.update(self._start_position.x, self._start_position.y)

    def __repr__(self) -> str:
        return f"<Node2D(name='{self._name}', type='{self._object_type.name}', pos={self._position})>"
