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


class ToggleKey(Key):
    def __init__(self, keys, **kwargs):
        super().__init__(**kwargs)
        self._keys = itertools.cycle(keys)
        self._key = next(self._keys)

    def mount(self, deck, index):
        self._key.mount(deck, index)

    def unmount(self, deck, index):
        self._key.unmount(deck, index)

    async def on_press(self, deck, index):
        await self._key.on_press(deck, index)
        self._key.unmount(deck, index)
        self._key = next(self._keys)
        self._key.mount(deck, index)
