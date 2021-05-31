from PIL import ImageDraw
from StreamDeck.ImageHelpers.PILHelper import create_image

from .base import NOT_PRESENT, Key


class SparklineKey(Key):
    def __init__(
        self,
        values,
        label=None,
        label_spacing=5,
        draw_height=50,
        line_width=1,
        color="white",
        background_upper="black",
        background_lower="red",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._values = values
        self._label = label
        self._label_spacing = label_spacing
        self._draw_height = draw_height
        self._line_width = line_width
        self._color = color
        self._background_upper = background_upper
        self._background_lower = background_lower

    def mount(self, deck, index):
        image = create_image(deck, self._background_upper)
        draw = ImageDraw.Draw(image)
        yoffset = (image.height - self._draw_height) // 2
        minval = min(self._values)
        maxoffset = max(self._values) - minval
        if maxoffset == 0:
            maxoffset = 1
        ys = [
            int(
                # Scaled to 1.0-0.0
                (1.0 - ((v - minval) / maxoffset))
                # Scaled to 0-draw_height
                * self._draw_height
                # To absolute Y.
                + yoffset
            )
            for v in self._values
        ]
        xstep = image.width / (len(self._values) - 1)
        xs = [int(xstep * i) for i in range(len(self._values))]
        coords = list(zip(xs, ys))
        # Draw the bottom section.
        draw.polygon(
            coords + [(image.width, image.height), (0, image.height)],
            self._background_lower,
        )
        # Draw the line.
        draw.line(coords, self._color, self._line_width, "curve")
        deck.set_key_image(index, image)

    async def set_value(self, deck, index, values=NOT_PRESENT):
        if values is not NOT_PRESENT:
            self._values = values
        self.mount(deck, index)

    # async def on_press(self, deck, index):
    #     # FOR TESTING
    #     n = random.randint(4, 20)
    #     vals = [random.randint(0, 100) for _ in range(n)]
    #     self._values = vals
    #     self.mount(deck, index)
