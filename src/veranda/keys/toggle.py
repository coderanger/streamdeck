import itertools

from .base import Key


class ToggleKey(Key):
    def __init__(self, keys, **kwargs):
        self._keys = itertools.cycle(keys)
        super().__init__(key=next(self._keys), **kwargs)

    async def on_press(self, deck, index):
        await super().on_press(deck, index)
        self._key.unmount(deck, index)
        self._key = next(self._keys)
        self._key.mount(deck, index)
