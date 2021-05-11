import asyncio
import atexit
import glob
import itertools
import json
import logging
import os.path
import random
import sys
import time
import webbrowser
from urllib.parse import urlencode

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers.PILHelper import to_native_format, create_image
from PIL import Image, ImageSequence, ImageFont, ImageDraw


NOT_PRESENT = object()


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
        self._keys = [None] * self._deck.key_count()
        self._debounce_times = {}

        self._deck.open()
        self._deck.set_key_callback_async(self.callback)
        self._deck.set_brightness(1.0)
        atexit.register(self.close)

    def set_key_image(self, index, image):
        if isinstance(image, Image.Image):
            image = to_native_format(self._deck, image)
        self._deck.set_key_image(index, image)

    def key_image_format(self):
        return self._deck.key_image_format()

    def __getitem__(self, key):
        return self._keys[key]

    def __setitem__(self, index, value):
        if self._keys[index]:
            self._keys[index].unmount(self, index)
        self._keys[index] = value
        if value:
            value.mount(self, index)

    async def callback(self, _deck, index, state):
        # Check for a debounce timer.
        now = time.monotonic()
        last = self._debounce_times.get((index, state))
        if last is not None:
            since = now - last
            if since < 0.05:  # 50ms
                return
        self._debounce_times[(index, state)] = now

        key = self._keys[index]
        fn = key.on_press if state else key.on_release
        await fn(self, index)

    def close(self):
        for index, key in enumerate(self._keys):
            if key:
                try:
                    key.unmount(self, index)
                except Exception:
                    pass
            self.set_key_image(index, None)
        self._deck.set_brightness(0)
        self._deck.close()
