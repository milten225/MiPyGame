import pygame
from typing import Optional, Tuple, List, Dict
from enum import Enum

class ObjectKind(Enum):
    SPRITE = "sprite"
    TEXT = "text"
    ANIMATED = "animated"

class ObjectType:
    """
    ObjectType represents the 'DNA' of an object in the engine.
    It stores shared data like textures, physics settings, and behaviors.
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
        text_content: str = "Hello",
        font_size: int = 32,
        frames: int = 1,
        fps: int = 10
    ):
        self.name: str = name
        self.kind: ObjectKind = kind
        self._width: int = width
        self._height: int = height
        self._sprite_path: str = sprite_path
        self.color: Tuple[int, int, int] = color
        self.is_static: bool = is_static

        self.text_content: str = text_content
        self.font_size: int = font_size

        self.frames: int = frames
        self.fps: int = fps

        # Resource caching
        self._cached_surface: Optional[pygame.Surface] = None
        self._cached_font: Optional[pygame.font.Font] = None
        self._cache_dirty: bool = True

        from core.behavior import BaseBehavior
        self.behaviors: List[BaseBehavior] = []

    @property
    def width(self) -> int: return self._width
    @width.setter
    def width(self, val: int):
        if self._width != val: self._width = val; self._cache_dirty = True

    @property
    def height(self) -> int: return self._height
    @height.setter
    def height(self, val: int):
        if self._height != val: self._height = val; self._cache_dirty = True

    @property
    def sprite_path(self) -> str: return self._sprite_path
    @sprite_path.setter
    def sprite_path(self, val: str):
        if self._sprite_path != val: self._sprite_path = val; self._cache_dirty = True

    def get_render_surface(self) -> pygame.Surface:
        """Returns a cached surface for rendering."""
        if self._cache_dirty or self._cached_surface is None:
            self._cached_surface = self._load_resource()
            self._cache_dirty = False
        return self._cached_surface

    def get_font(self) -> pygame.font.Font:
        """Returns a cached font."""
        if self._cached_font is None:
            pygame.font.init()
            self._cached_font = pygame.font.Font(None, self.font_size)
        return self._cached_font

    def _load_resource(self) -> pygame.Surface:
        if self.kind == ObjectKind.TEXT:
            font = self.get_font()
            return font.render(self.text_content, True, self.color)

        if self.sprite_path:
            try:
                img = pygame.image.load(self.sprite_path).convert_alpha()
                if self.kind == ObjectKind.SPRITE:
                    return pygame.transform.scale(img, (self.width, self.height))
                return img # For animated, we scale frames during draw or cache frames
            except: pass

        surf = pygame.Surface((self.width, self.height))
        surf.fill(self.color)
        return surf

    def __repr__(self) -> str:
        return f"<ObjectType(name='{self.name}', kind='{self.kind.value}', behaviors={len(self.behaviors)})>"
