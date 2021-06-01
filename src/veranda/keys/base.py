from typing import Optional

from ..deck import Deck
from ..utils.tasks import AutoTasksMixin


class Key(AutoTasksMixin):
    def __init__(self, key: Optional["Key"] = None):
        super().__init__()
        self._mounted = False
        self._key = key

    async def on_press(self, deck: Deck, index: int) -> None:
        if not self._mounted:
            raise Exception(f"{self}@{index} on_press called while not mounted")
        if self._key is not None:
            await self._key.on_press(deck, index)

    async def on_release(self, deck: Deck, index: int) -> None:
        if not self._mounted:
            raise Exception(f"{self}@{index} on_release called while not mounted")
        if self._key is not None:
            await self._key.on_release(deck, index)

    def mount(self, deck: Deck, index: int) -> None:
        if self._mounted:
            raise Exception(f"{self}@{index} mount called while already mounted")
        self._mounted = True
        super().mount(deck, index)
        self.draw(deck, index)
        if self._key is not None:
            self._key.mount(deck, index)

    def unmount(self, deck: Deck, index: int):
        if not self._mounted:
            raise Exception(f"{self}@{index} unmount called while not mounted")
        self._mounted = False
        super().unmount(deck, index)
        deck.set_key_image(index, None)
        if self._key is not None:
            self._key.unmount(deck, index)

    def draw(self, deck: Deck, index: int) -> None:
        if self._key is not None:
            self._key.draw(deck, index)

    async def set_value(self, deck: Deck, index: int, *args, **kwargs) -> None:
        if self._key is not None:
            await self._key.set_value(deck, index, *args, **kwargs)


# Sentinel object for some APIs.
NOT_PRESENT = object()
