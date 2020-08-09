import asyncio
import atexit
import glob
import itertools
import os.path
import random
import time
import webbrowser

from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers.PILHelper import to_native_format, create_image
from PIL import Image, ImageSequence, ImageFont, ImageDraw

import prometheus


class Deck:
    @classmethod
    def enumerate(cls):
        return [cls(deck) for deck in DeviceManager().enumerate()]

    @classmethod
    def get(cls):
        decks = cls.enumerate()
        if len(decks) != 1:
            raise ValueError(f'Did not find exactly one deck: {decks}')
        return decks[0]

    def __init__(self, deck):
        self._deck = deck
        self._keys = [None] * self._deck.key_count()
        # self._image_cache = {}
        self._debounce_times = {}

        self._deck.open()
        self._deck.set_key_callback_async(self.callback)
        self._deck.set_brightness(1.0)
        atexit.register(self.close)

    # def _load_image(self, path):
    #     if instance(path, Image):
    #         return to_native_format(self._deck, path.convert('RGB'))
    #     path = os.path.abspath(path)
    #     image = self._image_cache.get(path)
    #     if image is None:
    #         image = to_native_format(self._deck, Image.open(path).convert('RGB'))
    #         self._image_cache[path] = image
    #     return image

    def set_key_image(self, index, image):
        if isinstance(image, Image.Image):
            image = to_native_format(self._deck, image)
        self._deck.set_key_image(index, image)

    def key_image_format(self):
        return self._deck.key_image_format()

    def __getitem__(self, key):
        return self._keys[key]

    def __setitem__(self, index, value):
        if self._keys[index]:
            self._keys[index].unmount(self, index)
        self._keys[index] = value
        if value:
            value.mount(self, index)

    async def callback(self, _deck, index, state):
        # Check for a debounce timer.
        now = time.monotonic()
        last = self._debounce_times.get((index, state))
        if last is not None:
            since = now - last
            if since < 0.05: # 50ms
                return
        self._debounce_times[(index, state)] = now

        key = self._keys[index]
        fn = key.on_press if state else key.on_release
        await fn(self, index)

    def close(self):
        for index, key in enumerate(self._keys):
            if key:
                try:
                    key.unmount(self, index)
                except Exception:
                    pass
            self.set_key_image(index, None)
        self._deck.set_brightness(0)
        self._deck.close()


class Key:
    async def on_press(self, deck, index):
        pass

    async def on_release(self, deck, index):
        pass

    def mount(self, deck, index):
        pass

    def unmount(self, deck, index):
        pass

    async def set_value(self, deck, index, value):
        pass


class ImageKey(Key):
    def __init__(self, image, **kwargs):
        super().__init__(**kwargs)
        if isinstance(image, str):
            image = Image.open(image).convert('RGB')
        self._image = image

    def mount(self, deck, index):
        deck.set_key_image(index, self._image)


class AnimatedKey(Key):
    def __init__(self, paths, speed=None, **kwargs):
        super().__init__(**kwargs)
        # Expand a single glob.
        if isinstance(paths, str):
            paths = glob.glob(paths)
            paths.sort()
        # Load a GIF.
        if len(paths) == 1 and paths[0].endswith('.gif'):
            speed = speed or 1
            frame_source = ((f, f.info['duration'] / speed) for f in ImageSequence.Iterator(Image.open(paths[0])))
        else:
            speed = speed or 50
            frame_source = ((Image.open(p), speed) for p in paths)
        self._frames = [(f.convert('RGB'), d) for f, d in frame_source]
        self._task = None

    def mount(self, deck, index):
        self._native_frames = itertools.cycle((to_native_format(deck._deck, f), d) for f, d in self._frames)
        if self._task is None:
            self._task = asyncio.ensure_future(self.update(deck, index))

    def unmount(self, _, __):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def update(self, deck, index):
        while True:
            image, delay = next(self._native_frames)
            deck.set_key_image(index, image)
            await asyncio.sleep(delay / 1000)


class TextKey(Key):
    def __init__(self, text, label=None, label_spacing=5, size=50, label_size=20, font='Roboto-Regular.ttf', color='white', label_color=None, background='black', **kwargs):
        super().__init__(**kwargs)
        self._text = text
        self._label = label
        self._label_spacing = label_spacing
        self._font = ImageFont.truetype(f"fonts/{font}", size)
        self._label_font = self._font.font_variant(size=label_size) #ImageFont.truetype(f"fonts/{font}", label_size)
        self._color = color
        self._label_color = label_color or color
        self._background = background

    def mount(self, deck, index):
        image = create_image(deck, self._background)
        draw = ImageDraw.Draw(image)
        fit_width = image.width - 10
        font, size = self._fit_font(self._font, self._text, fit_width)

        if self._label:
            label_font, label_size = self._fit_font(self._label_font, self._label, fit_width)
            total_height = size[1] + label_size[1] + self._label_spacing
            label_y = (image.height - total_height) // 2
            y = label_y + label_size[1] + self._label_spacing
            label_x = (image.width - label_size[0]) // 2
            x = (image.width - size[0]) // 2
            draw.text((label_x, label_y), self._label, self._label_color, label_font)
            draw.text((x, y), self._text, self._color, font)
        else:
            x = (image.width - size[0]) // 2
            y = (image.height - size[1]) // 2
            draw.text((x, y), self._text, self._color, font)
        deck.set_key_image(index, image)

    async def set_value(self, params, deck, index):
        if isinstance(params, str):
            params = {'text': params}
        if 'text' in params:
            self._text = params['text']
        if 'color' in params:
            self._color = params['color']
        self.mount(deck, index)

    async def on_press(self, deck, index):
        # FOR TESTING
        new_text = str(int(self._text) - 1)
        if int(new_text) < 80:
            self._color = 'yellow'
        await self.set_value(new_text, deck, index)

    def _getsize(self, font, text):
        x, y = font.getsize(text)
        # The approximated 0.21 correct factor to offset that getsize is based on max glypy height, found via https://stackoverflow.com/questions/55773962/pillow-how-to-put-the-text-in-the-center-of-the-image
        return (x, int(y * 1.21))

    def _fit_font(self, font, text, width):
        size = None
        while (size is None or size[0] > width) and font.size >= 15:
            font = font.font_variant(size=font.size-1)
            size = self._getsize(font, text)
        return (font, size)

class EmojiKey(Key):
    def __init__(self, text, background='black', **kwargs):
        super().__init__(**kwargs)
        codepoints = '-'.join(f"{ord(c):x}" for c in text)
        path = f"twemoji/{codepoints}.png"
        self._image = Image.open(path).convert('RGBA')
        self._background = background

    def mount(self, deck, index):
        image_format = deck.key_image_format()
        canvas = Image.new('RGBA', image_format['size'], self._background)
        canvas.alpha_composite(self._image, ((canvas.width - self._image.width) // 2, (canvas.height - self._image.height) // 2))
        deck.set_key_image(index, canvas.convert('RGB'))

class SparklineKey(Key):
    def __init__(self, values, draw_height=50, line_width=1, color='white', background_upper='black', background_lower='red', **kwargs):
        super().__init__(**kwargs)
        self._values = values
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
        ys = [int(
                # Scaled to 1.0-0.0
                (1.0 - ((v - minval) / maxoffset))
                # Scaled to 0-draw_height
                * self._draw_height
                # To absolute Y.
                + yoffset
            )
            for v in self._values]
        xstep = image.width / (len(self._values) - 1)
        xs = [int(xstep * i) for i in range(len(self._values))]
        coords = list(zip(xs, ys))
        # Draw the bottom section.
        draw.polygon(coords + [(image.width, image.height), (0, image.height)], self._background_lower)
        # Draw the line.
        draw.line(coords, self._color, self._line_width, 'curve')
        deck.set_key_image(index, image)

    async def on_press(self, deck, index):
        # FOR TESTING
        n = random.randint(4, 20)
        vals = [random.randint(0, 100) for _ in range(n)]
        self._values = vals
        self.mount(deck, index)


class ToggleKey(Key):
    def __init__(self, keys, **kwargs):
        super().__init__(**kwargs)
        self._keys = itertools.cycle(keys)
        self._key = next(self._keys)

    def mount(self, deck, index):
        self._key.mount(deck, index)

    def unmount(self, deck, index):
        self._key.unmount(deck, index)

    async def on_press(self, deck, index):
        self._key.unmount(deck, index)
        self._key = next(self._keys)
        self._key.mount(deck, index)


class URLKey(Key):
    def __init__(self, url, key, **kwargs):
        super().__init__(**kwargs)
        self._url = url
        self._key = key

    def mount(self, deck, index):
        self._key.mount(deck, index)

    def unmount(self, deck, index):
        self._key.unmount(deck, index)

    async def on_press(self, deck, index):
        webbrowser.open(self._url, new=2)
        await self._key.on_press(deck, index)


class PrometheusKey(Key):
    def __init__(self, prom, query, key, **kwargs):
        super().__init__(**kwargs)
        self._prom = prom
        self._query = query
        self._key = key
        self._task = None

    def mount(self, deck, index):
        self._key.mount(deck, index)
        if self._task is None:
            self._task = asyncio.ensure_future(self.update(deck, index))

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
            value = await self.query()
            await self._key.set_value(value, deck, index)
            await asyncio.sleep(30)

    async def query(self):
        raise NotImplementedError


class PrometheusSingleStateKey(PrometheusKey):
    def __init__(self, prom, query, label, **kwargs):
        key = TextKey('', label)
        super().__init__(prom, query, key, **kwargs)

    async def query(self):
        value = await self._prom.instant(self._query)
        if isinstance(value, float):
            return {'text', f"{value:.2f}"}
        else:
            return {'text': str(value)}


async def init():
    deck = Deck.get()
    deck[0] = URLKey('https://geomagical.com/', ToggleKey([
        ImageKey('img/logo.png'),
        ImageKey('img/logo2.png'),
    ]))
    deck[1] = AnimatedKey('img/gears.gif')
    deck[2] = AnimatedKey('img/kart*.png')
    deck[3] = ToggleKey([
        AnimatedKey('img/kart.gif'),
        AnimatedKey('img/kart.gif', speed=3),
        AnimatedKey('img/taco.gif'),
        AnimatedKey('img/charmander.gif'),
    ])
    deck[4] = TextKey('100')
    deck[4+8] = TextKey('1000.0', label='Hello World Really Long')
    deck[5+8] = PrometheusSingleStateKey(prometheus.dev, query='sum(kube_node_info)', label='Dev Nodes')
    deck[3+8] = PrometheusSingleStateKey(prometheus.dev, query='round(sum(container_memory_working_set_bytes{namespace="pipeline"}) / 1000000000)', label='Dev RAM')
    deck[5] = SparklineKey([0, 1, 2, 1, 4, 3])
    deck[6] = TextKey('✨', font='Symbola.otf')
    deck[7] = EmojiKey('✨')
    deck[7+8] = EmojiKey('🧛‍♂️')
    deck[6+8] = EmojiKey('🧛‍♀️')

def main():
    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(init())
        loop.run_forever()
    except KeyboardInterrupt:
        pass # Exiting cleanly.
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == '__main__':
    main()