from PIL import Image

from ..deck import Deck
from .base import Key


class EmojiKey(Key):
    def __init__(self, text, background="black", **kwargs):
        super().__init__(**kwargs)
        codepoints = "-".join(f"{ord(c):x}" for c in text)
        path = f"twemoji/{codepoints}.png"
        self._image = Image.open(path).convert("RGBA")
        self._background = background

    def draw(self, deck: Deck, index: int) -> None:
        image_format = deck.key_image_format()
        canvas = Image.new("RGBA", image_format["size"], self._background)
        canvas.alpha_composite(
            self._image,
            (
                (canvas.width - self._image.width) // 2,
                (canvas.height - self._image.height) // 2,
            ),
        )
        deck.set_key_image(index, canvas.convert("RGB"))
