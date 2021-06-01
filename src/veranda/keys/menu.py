import asyncio
import time

from typing import Optional

from PIL import Image, ImageColor, ImageDraw

from ..deck import Deck, Scene
from .base import Key


class MenuKey(Key):
    def __init__(self, key: Key, scene: Optional[Scene] = None, **kwargs):
        super().__init__(key=key, **kwargs)
        self._scene = scene

    async def on_press(self, deck, index):
        await super().on_press(deck, index)
        deck.push_scene(MenuAnimationScene(self, index, self._scene))


class PopSceneKey(Key):
    async def on_press(self, deck, index):
        await super().on_press(deck, index)
        deck.pop_scene()


class MenuAnimationScene(Scene):
    animation_speed = 0.000000004
    background_color = ImageColor.getrgb("black")
    line_color = ImageColor.getrgb("white")

    _animation_image: Optional[Image.Image]
    _draw: Optional[ImageDraw.ImageDraw]

    def __init__(self, origin_key: Key, origin_index: int, next_scene: Optional[Scene]):
        super().__init__()
        self._origin_key = origin_key
        self._origin_index = origin_index
        self._next_scene = next_scene
        self._task = None

    def mount(self, deck: Deck) -> None:
        # Create the overall image canvas.
        self._animation_image = Image.new(
            "RGB",
            (
                deck.key_size[0] * deck.key_layout[1],
                deck.key_size[1] * deck.key_layout[0],
            ),
        )
        self._draw = ImageDraw.Draw(self._animation_image)
        # Spawn the update task.
        if self._task is None:
            self._task = asyncio.ensure_future(self.update(deck))
        super().mount(deck)

    def unmount(self, _) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def update(self, deck: Deck) -> None:
        # Work out the start and end states to tween.
        start_rect = deck.key_rect(self._origin_index)
        end_rect = (
            0,  # left
            0,  # top
            self._animation_image.width,  # right
            self._animation_image.height,  # bottom
        )
        if self._next_scene is None:
            start_rect, end_rect = end_rect, start_rect

        # Simple lerp tween.
        def tween(v0: float, v1: float, t: float) -> float:
            return v0 + t * (v1 - v0)

        # Compte all the crop rects for each key.
        crop_rects = [deck.key_rect(i) for i in range(deck.key_count)]

        start_time = time.monotonic_ns()
        completion = 0.0
        while True:
            # Update the completion percentage.
            elapsed = time.monotonic_ns() - start_time
            completion = elapsed * self.animation_speed
            if completion >= 1:
                # We're done!
                break
            # Draw the new overall image.
            self._draw.rectangle(
                (
                    0,
                    0,
                    self._animation_image.width + 1,
                    self._animation_image.height + 1,
                ),
                self.background_color,
                None,
                0,
            )
            # Just use a linear tween for now.
            tween_rect = (
                tween(start_rect[0], end_rect[0], completion),
                tween(start_rect[1], end_rect[1], completion),
                tween(start_rect[2], end_rect[2], completion),
                tween(start_rect[3], end_rect[3], completion),
            )
            self._draw.rectangle(tween_rect, None, self.line_color, 2)
            # Blit to all key images.
            for i, crop_rect in enumerate(crop_rects):
                deck.set_key_image(i, self._animation_image.crop(crop_rect))
            # Zzzz.
            await asyncio.sleep(0.016)

        # Animation complete, advance.
        deck.clear()
        self._task = None
        if self._next_scene is None:
            deck.pop_scene(2)
        else:
            deck.replace_scene(self._next_scene)
