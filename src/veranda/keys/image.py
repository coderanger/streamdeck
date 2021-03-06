import asyncio
import glob
import itertools

from PIL import Image, ImageSequence
from StreamDeck.ImageHelpers.PILHelper import to_native_format

from ..deck import Deck
from .base import Key


class ImageKey(Key):
    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        if isinstance(image, str):
            image = Image.open(image).convert("RGB")
        self._image = image

    def draw(self, deck, index):
        deck.set_key_image(index, self._image)


class AnimatedKey(Key):
    def __init__(self, paths: list[str], speed=None, **kwargs):
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

    def mount(self, deck: Deck, index: int):
        self._native_frames = itertools.cycle(
            (to_native_format(deck._deck, f), d) for f, d in self._frames
        )
        super().mount(deck, index)

    async def update(self, deck: Deck, index: int):
        while self._mounted:
            image, delay = next(self._native_frames)
            deck.set_key_image(index, image)
            await asyncio.sleep(delay / 1000)
