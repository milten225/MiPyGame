from typing import Optional, Tuple
from enum import Enum

class ObjectKind(Enum):
    SPRITE = "sprite"
    TEXT = "text"
    ANIMATED = "animated"

class ObjectType:
    """
    ObjectType represents the 'DNA' of an object in the engine.
    It stores shared data like textures, physics settings, and behavior scripts.
    """

    def __init__(
        self,
        name: str,
        kind: ObjectKind = ObjectKind.SPRITE,
        width: int = 50,
        height: int = 50,
        sprite_path: str = "",
        color: Tuple[int, int, int] = (100, 150, 250),
        is_static: bool = False,
        behavior_code: str = "",
        # Text specific
        text_content: str = "Hello",
        font_size: int = 32,
        # Animation specific
        frames: int = 1,
        fps: int = 10
    ):
        """
        Initializes an ObjectType.
        """
        self.name: str = name
        self.kind: ObjectKind = kind
        self.width: int = width
        self.height: int = height
        self.sprite_path: str = sprite_path
        self.color: Tuple[int, int, int] = color
        self.is_static: bool = is_static
        self.behavior_code: str = behavior_code

        self.text_content: str = text_content
        self.font_size: int = font_size

        self.frames: int = frames
        self.fps: int = fps

    def __repr__(self) -> str:
        return f"<ObjectType(name='{self.name}', kind='{self.kind.value}', is_static={self.is_static})>"
