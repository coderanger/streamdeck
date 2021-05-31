import weakref

from typing import Optional

from PIL import Image

from ..deck import Deck
from .base import Key


class MultiKey(Key):
    def __init__(
        self,
        key: Optional[Key] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        image: Optional[Image.Image] = None,
    ):
        super().__init__()
        self._key = key
        self._width = width
        self._height = height
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        self._initial_image = image
        self._rect = None
        self._image = None
        self._key_crop_rects = {}

    def mount(self, deck: Deck, index: int) -> None:
        if self._key is not None:
            self._key.mount(deck, index)
        y, x = divmod(index, deck.key_layout[1])
        width = min(self._width or deck.key_layout[1], deck.key_layout[1] - x)
        height = min(self._height or deck.key_layout[0], deck.key_layout[0] - y)
        for sub_x in range(width):
            for sub_y in range(height):
                sub_index = sub_x + (sub_y * deck.key_layout[1])
                self._key_crop_rects[sub_index + index] = deck.key_rect(sub_index)
                if sub_index != 0:
                    deck[sub_index + index] = MultiKeyProxy(self)
        top_left_rect = self._key_crop_rects[index]
        bottom_right_rect = self._key_crop_rects[sub_index + index]
        self._rect = (
            top_left_rect[0],
            top_left_rect[1],
            bottom_right_rect[2],
            bottom_right_rect[3],
        )
        size = (self._rect[2] - self._rect[0], self._rect[3] - self._rect[1])
        if self._initial_image is None:
            self._image = Image.new("RGB", size)
        else:
            self._image = self._initial_image.resize(size)
        self.draw(deck)

    def unmount(self, deck: Deck, index: int) -> None:
        if self._key is not None:
            self._key.unmount(deck, index)
        self._rect = None
        self._image = None
        self._key_crop_rects = {}

    async def on_press(self, deck: Deck, index: int) -> None:
        if self._key is not None:
            await self._key.on_press(deck, index)

    async def on_release(self, deck: Deck, index: int) -> None:
        if self._key is not None:
            await self._key.on_release(deck, index)

    def draw(self, deck: Deck, image: Optional[Image.Image] = None):
        # Safety check.
        if self._image is None:
            raise ValueError("cannot call draw() before mounting")
        if image is not None:
            # New image, scale it to size if needed.
            if image.size != self._image.size:
                self._image = image.resize(self._image.size)
            else:
                self._image = image
        # Repaint all the keys.
        for index, rect in self._key_crop_rects.items():
            deck.set_key_image(index, self._image.crop(rect))


class MultiKeyProxy(Key):
    """A placeholder to grab press/release events for the non-primary index spots."""

    def __init__(self, parent: MultiKey):
        super().__init__()
        self._parent = weakref.ref(parent)

    async def on_press(self, deck: Deck, index: int) -> None:
        parent = self._parent()
        if parent is not None:
            await parent.on_press(deck, index)

    async def on_release(self, deck: Deck, index: int) -> None:
        parent = self._parent()
        if parent is not None:
            await parent.on_release(deck, index)
