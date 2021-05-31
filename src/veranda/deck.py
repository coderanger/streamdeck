from __future__ import annotations

import atexit
import copy
import time

from typing import TYPE_CHECKING, Optional

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers.PILHelper import to_native_format


if TYPE_CHECKING:
    from .keys.base import Key


class Scene:
    keys = {}

    def __init__(self):
        self._keys = copy.copy(self.__class__.keys)
        # Only set while mounted.
        self._deck = None

    def __getitem__(self, index: int) -> Optional[Key]:
        return self._keys.get(index)

    def __setitem__(self, index: int, key: Key) -> None:
        if self._deck is not None:
            old_key = self._keys.get(index)
            if old_key is not None:
                old_key.unmount(self._deck, index)
        self._keys[index] = key
        if self._deck is not None and key is not None:
            key.mount(self._deck, index)

    def mount(self, deck):
        if self._deck is not None:
            raise Exception("Scene is already mounted")
        self._deck = deck
        for index, key in list(self._keys.items()):
            if key is not None:
                key.mount(deck, index)

    def unmount(self, deck):
        if self._deck is None:
            raise Exception("Scene is not mounted")
        if self._deck is not deck:
            raise Exception("Unmounting from the wrong deck")
        for index, key in self._keys.items():
            if key is not None:
                key.unmount(deck, index)
        self._deck = None

    def close(self):
        if self._deck is not None:
            for index, key in self._keys.items():
                if key is not None:
                    try:
                        key.unmount(self._deck, index)
                    except Exception:
                        # Ignore exceptions so we try to unmount all keys.
                        pass
                self._deck.set_key_image(index, None)


class Deck:
    # Pixels between keys in the X direction.
    X_PADDING = 34

    # Pixels between keys in the Y direction.
    Y_PADDING = X_PADDING

    @classmethod
    def enumerate(cls):
        return [cls(deck) for deck in DeviceManager().enumerate()]

    @classmethod
    def get(cls):
        decks = cls.enumerate()
        if len(decks) != 1:
            raise ValueError(f"Did not find exactly one deck: {decks}")
        return decks[0]

    def __init__(self, deck):
        self._deck = deck
        self._scenes = [Scene()]
        self._scenes[0].mount(self)
        self._debounce_times = {}

        # Open the connection!
        self._deck.open()

        # Store the key info for use elsewhere.
        self.key_count = deck.key_count()
        self.key_layout = deck.key_layout()
        self.key_size = deck.key_image_format()["size"]

        # Initialize the display and hooks.
        self.clear()
        self._deck.set_key_callback_async(self.callback)
        atexit.register(self.close)

    def set_key_image(self, index, image):
        if isinstance(image, Image.Image):
            image = to_native_format(self._deck, image)
        self._deck.set_key_image(index, image)

    def key_image_format(self):
        return self._deck.key_image_format()

    def key_rect(self, index: int) -> tuple[float, float, float, float]:
        """Return the rectangle for a given index in global coordinates. (0,0) is the top-left
        corner of the top-left key. Rect is in PIL (left, top, right, bottom) format.
        """
        y, x = divmod(index, self.key_layout[1])
        padded_x = self.key_size[0] + self.X_PADDING
        padded_y = self.key_size[1] + self.Y_PADDING
        return (
            x * padded_x,  # left
            y * padded_y,  # top
            ((x + 1) * padded_x) - self.X_PADDING,  # right
            ((y + 1) * padded_y) - self.Y_PADDING,  # bottom
        )

    def clear(self, brightness: float = 1.0):
        for i in range(self.key_count):
            self.set_key_image(i, None)
        self.set_brightness(brightness)

    def set_brightness(self, brightness: float):
        self._deck.set_brightness(brightness)

    def __getitem__(self, index):
        return self._scenes[-1][index]

    def __setitem__(self, index, value):
        self._scenes[-1][index] = value

    def push_scene(self, scene):
        self._scenes[-1].unmount(self)
        self._scenes.append(scene)
        scene.mount(self)

    def pop_scene(self, n: int = 1):
        if len(self._scenes) <= n:
            raise Exception("No scene to pop")
        self._scenes[-1].unmount(self)
        del self._scenes[-1 * n :]
        self._scenes[-1].mount(self)

    def replace_scene(self, scene: Scene) -> None:
        """Pop and push a new scene without running the intermediary mounts."""
        if len(self._scenes) <= 1:
            raise Exception("No scene to pop")
        self._scenes[-1].unmount(self)
        self._scenes.pop(-1)
        self._scenes.append(scene)
        scene.mount(self)

    async def callback(self, _deck, index, state):
        # Check for a debounce timer.
        now = time.monotonic()
        last = self._debounce_times.get((index, state))
        if last is not None:
            since = now - last
            if since < 0.05:  # 50ms
                return
        self._debounce_times[(index, state)] = now

        key = self._scenes[-1][index]
        if key is not None:
            fn = key.on_press if state else key.on_release
            await fn(self, index)

    def close(self):
        self._scenes[-1].close()
        self._deck.set_brightness(0)
        self._deck.close()
