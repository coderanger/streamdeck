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


class EmojiKey(Key):
    def __init__(self, text, background="black", **kwargs):
        super().__init__(**kwargs)
        codepoints = "-".join(f"{ord(c):x}" for c in text)
        path = f"twemoji/{codepoints}.png"
        self._image = Image.open(path).convert("RGBA")
        self._background = background

    def mount(self, deck, index):
        image_format = deck.key_image_format()
        canvas = Image.new("RGBA", image_format["size"], self._background)
        canvas.alpha_composite(
            self._image,
            (
                (canvas.width - self._image.width) // 2,
                (canvas.height - self._image.height) // 2,
            ),
        )
        deck.set_key_image(index, canvas.convert("RGB"))
