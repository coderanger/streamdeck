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

from PIL import Image, ImageDraw, ImageFont, ImageSequence
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers.PILHelper import create_image, to_native_format

from .base import Key


class ImageKey(Key):
    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        self._image = image

    def mount(self, deck, index):
        deck.set_key_image(index, self._image)


class AnimatedKey(Key):
    def __init__(self, paths, speed=None, **kwargs):
        super().__init__(**kwargs)
        # Expand a single glob.
        if isinstance(paths, str):
            paths = glob.glob(paths)
            paths.sort()
        # Load a GIF.
        if len(paths) == 1 and paths[0].endswith(".gif"):
            speed = speed or 1
            frame_source = (
                (f, f.info["duration"] / speed)
                for f in ImageSequence.Iterator(Image.open(paths[0]))
            )
        else:
            speed = speed or 50
            frame_source = ((Image.open(p), speed) for p in paths)
        self._frames = [(f.convert("RGB"), d) for f, d in frame_source]
        self._task = None

    def mount(self, deck, index):
        self._native_frames = itertools.cycle(
            (to_native_format(deck._deck, f), d) for f, d in self._frames
        )
        if self._task is None:
            self._task = asyncio.ensure_future(self.update(deck, index))

    def unmount(self, _, __):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def update(self, deck, index):
        while True:
            image, delay = next(self._native_frames)
            deck.set_key_image(index, image)
            await asyncio.sleep(delay / 1000)
