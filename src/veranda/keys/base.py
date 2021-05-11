from abc import ABC, abstractmethod


class Key(ABC):
    # @abstractmethod
    async def on_press(self, deck, index):
        pass

    # @abstractmethod
    async def on_release(self, deck, index):
        pass

    # @abstractmethod
    def mount(self, deck, index):
        pass

    # @abstractmethod
    def unmount(self, deck, index):
        pass

    # @abstractmethod
    async def set_value(self, deck, index, value):
        pass


# Sentinel object for some APIs.
NOT_PRESENT = object()
