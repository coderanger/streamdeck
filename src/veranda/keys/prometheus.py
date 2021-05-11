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


class PrometheusKey(Key):
    def __init__(self, prom, query, key, **kwargs):
        super().__init__(**kwargs)
        self._prom = prom
        self._query = query
        self._key = GrafanaExploreURLKey("https://grafana.mysugarcube.com", query, key)
        self._task = None

    def mount(self, deck, index):
        self._key.mount(deck, index)
        if self._task is None:
            self._task = asyncio.ensure_future(self.update(deck, index))
            self._task.add_done_callback(print)

    def unmount(self, _, __):
        self._key.unmount(deck, index)
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def on_press(self, deck, index):
        await self._key.on_press(deck, index)

    async def on_release(self, deck, index):
        await self._key.on_release(deck, index)

    async def update(self, deck, index):
        while True:
            to_set = await self.query()
            await self._key.set_value(deck, index, **to_set)
            await asyncio.sleep(30)

    async def query(self):
        raise NotImplementedError


class PrometheusSingleStatKey(PrometheusKey):
    def __init__(self, prom, query, label, **kwargs):
        key = TextKey("", label)
        super().__init__(prom, query, key, **kwargs)

    async def query(self):
        value = await self._prom.instant(self._query)
        if isinstance(value, float):
            return {"text", f"{value:.2f}"}
        else:
            return {"text": str(value)}


class PrometheusSparklineKey(PrometheusKey):
    def __init__(self, prom, query, label, **kwargs):
        key = SparklineKey([0, 0], label)
        super().__init__(prom, query, key, **kwargs)

    async def query(self):
        values = await self._prom.range(self._query)
        return {"values": values}
