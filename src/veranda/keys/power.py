from ..deck import Scene
from .base import Key
from .image import ImageKey


class PowerKey(ImageKey):
    def __init__(self, **kwargs):
        super().__init__("img/power.png", **kwargs)

    async def on_press(self, deck, index):
        deck.set_brightness(0.0)
        deck.push_scene(PowerOffScene())


class PowerOnKey(Key):
    async def on_press(self, deck, index):
        deck.pop_scene()
        deck.set_brightness(1.0)


class PowerOffScene(Scene):
    def mount(self, deck):
        for index in range(deck.key_count):
            self[index] = PowerOnKey()
        super().mount(deck)
