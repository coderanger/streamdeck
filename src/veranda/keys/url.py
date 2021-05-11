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


class URLKey(Key):
    def __init__(self, url, key, **kwargs):
        super().__init__(**kwargs)
        self._url = url
        self._key = key

    def mount(self, deck, index):
        self._key.mount(deck, index)

    def unmount(self, deck, index):
        self._key.unmount(deck, index)

    async def on_press(self, deck, index):
        webbrowser.open(self._url, new=2)
        await self._key.on_press(deck, index)

    async def set_value(self, deck, index, **kwargs):
        await self._key.set_value(deck, index, **kwargs)


class GrafanaExploreURLKey(URLKey):
    def __init__(self, grafana_url: str, query: str, key: Key, **kwargs):
        # https://grafana.example.com/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Thanos%22,%7B%22expr%22:%22sum(avg_over_time(container_memory_working_set_bytes%7Bnamespace%3D%5C%22pipeline%5C%22%7D%5B5m%5D))%22%7D,%7B%22ui%22:%5Btrue,true,true,%22none%22%5D%7D%5D
        params = [
            "now-30m",
            "now",
            "Thanos",
            {"expr": query},
            {"ui": [True, True, True, "none"]},
        ]
        qs = urlencode(
            {
                "orgId": "1",
                "left": json.dumps(params),
            }
        )
        url = f"{grafana_url}/explore?{qs}"
        super().__init__(url, key, **kwargs)
