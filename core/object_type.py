from typing import Optional, Tuple

class ObjectType:
    """
    ObjectType represents the 'DNA' of an object in the engine.
    It stores shared data like textures, physics settings, and behavior scripts.
    """

    def __init__(
        self,
        name: str,
        sprite_path: str = "",
        color: Tuple[int, int, int] = (100, 150, 250),
        is_static: bool = False,
        behavior_code: str = ""
    ):
        """
        Initializes an ObjectType.

        Args:
            name (str): The name of the object type (e.g., 'Player', 'Wall').
            sprite_path (str): The file path to the sprite image.
            color (tuple): Default color for rendering if no sprite is provided.
            is_static (bool): Whether objects of this type are static in the physics engine.
            behavior_code (str): Python code that defines the behavior of objects of this type.
        """
        self.name: str = name
        self.sprite_path: str = sprite_path
        self.color: Tuple[int, int, int] = color
        self.is_static: bool = is_static
        self.behavior_code: str = behavior_code

    def __repr__(self) -> str:
        return f"<ObjectType(name='{self.name}', is_static={self.is_static})>"
