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


class TextKey(Key):
    def __init__(
        self,
        text,
        label=None,
        label_spacing=5,
        size=50,
        label_size=20,
        font="Roboto-Regular.ttf",
        color="white",
        label_color=None,
        background="black",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._text = text
        self._label = label
        self._label_spacing = label_spacing
        self._font = ImageFont.truetype(f"fonts/{font}", size)
        self._label_font = self._font.font_variant(
            size=label_size
        )  # ImageFont.truetype(f"fonts/{font}", label_size)
        self._color = color
        self._label_color = label_color or color
        self._background = background

    def mount(self, deck, index):
        image = create_image(deck, self._background)
        draw = ImageDraw.Draw(image)
        fit_width = image.width - 10
        font, size = self._fit_font(self._font, self._text, fit_width)

        if self._label:
            label_font, label_size = self._fit_font(
                self._label_font, self._label, fit_width
            )
            total_height = size[1] + label_size[1] + self._label_spacing
            label_y = (image.height - total_height) // 2
            y = label_y + label_size[1] + self._label_spacing
            label_x = (image.width - label_size[0]) // 2
            x = (image.width - size[0]) // 2
            draw.text((label_x, label_y), self._label, self._label_color, label_font)
            draw.text((x, y), self._text, self._color, font)
        else:
            x = (image.width - size[0]) // 2
            y = (image.height - size[1]) // 2
            draw.text((x, y), self._text, self._color, font)
        deck.set_key_image(index, image)

    async def set_value(self, deck, index, text=NOT_PRESENT, color=NOT_PRESENT):
        if text is not NOT_PRESENT:
            self._text = text
        if color is not NOT_PRESENT:
            self._color = color
        self.mount(deck, index)

    # async def on_press(self, deck, index):
    #     # FOR TESTING
    #     new_text = str(int(self._text) - 1)
    #     if int(new_text) < 80:
    #         self._color = 'yellow'
    #     await self.set_value(new_text, deck, index)

    def _getsize(self, font, text):
        x, y = font.getsize(text)
        # The approximated 0.21 correct factor to offset that getsize is based on max glypy height, found via https://stackoverflow.com/questions/55773962/pillow-how-to-put-the-text-in-the-center-of-the-image
        return (x, int(y * 1.21))

    def _fit_font(self, font, text, width):
        size = None
        while (size is None or size[0] > width) and font.size >= 15:
            font = font.font_variant(size=font.size - 1)
            size = self._getsize(font, text)
        return (font, size)
