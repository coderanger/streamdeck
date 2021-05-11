import atexit
import copy
import time

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers.PILHelper import to_native_format


class Scene:
    keys = {}

    def __init__(self):
        self._keys = copy.copy(self.__class__.keys)
        # Only set while mounted.
        self._deck = None

    def __getitem__(self, index):
        return self._keys.get(index)

    def __setitem__(self, index, key):
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
        for index, key in self._keys.items():
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

        self._deck.open()
        self._deck.set_key_callback_async(self.callback)
        self._deck.set_brightness(1.0)
        atexit.register(self.close)

        # Store the key count for use elsewhere.
        self.key_count = deck.key_count()

    def set_key_image(self, index, image):
        if isinstance(image, Image.Image):
            image = to_native_format(self._deck, image)
        self._deck.set_key_image(index, image)

    def key_image_format(self):
        return self._deck.key_image_format()

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

    def pop_scene(self):
        if len(self._scenes) <= 1:
            raise Exception("No scene to pop")
        self._scenes[-1].unmount(self)
        self._scenes.pop(-1)
        self._scenes[-1].mount(self)

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
