import asyncio
import time

from PIL import Image

from .deck import Deck, Scene
from .keys import MultiKey, PopSceneKey


class BeachballScene(Scene):
    speed = 180

    keys = {
        2: MultiKey(
            key=PopSceneKey(), image="img/gradient_circle.png", height=4, width=4
        ),
    }

    def __init__(
        self,
    ):
        super().__init__()
        self._task = None

    def mount(self, deck: Deck) -> None:
        # Spawn the update task.
        if self._task is None:
            self._task = asyncio.ensure_future(self.update(deck))
        super().mount(deck)

    def unmount(self, _) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def update(self, deck: Deck):
        start_time = time.monotonic()
        key: MultiKey = self[2]
        start_img = key._image
        while True:
            elapsed = time.monotonic() - start_time
            rotation = (elapsed * self.speed * -1) % 360
            img = start_img.rotate(rotation, Image.BILINEAR)
            key.draw(deck, img)
            await asyncio.sleep(0.05)
