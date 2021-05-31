import asyncio

from . import kubernetes, prometheus
from .beachball import BeachballScene
from .deck import Deck, Scene
from .keys import (
    AnimatedKey,
    EmojiKey,
    ImageKey,
    MenuKey,
    MultiKey,
    PopSceneKey,
    PowerKey,
    PrometheusSingleStatKey,
    PrometheusSparklineKey,
    TextKey,
    URLKey,
)
from .keys.base import Key
from .rabbitmq import RabbitMQScene


class HackKey(Key):
    def __init__(self, n):
        self.n = n

    async def on_press(self, deck, index):
        deck.X_PADDING += self.n
        deck.Y_PADDING = deck.X_PADDING
        print(deck.X_PADDING)
        key = deck[0]
        img = key._image
        key.mount(deck, 0)
        key.draw(deck, img)


class RainbowScene(Scene):
    keys = {
        0: MultiKey(PopSceneKey()),
        # 24: HackKey(1),
        # 25: HackKey(-1),
    }

    def mount(self, deck: Deck):
        super().mount(deck)
        from PIL import Image

        self[0].draw(deck, Image.open("img/gradient.png").convert("RGB"))
        # self[0].draw(deck, Image.open("img/rays.png").convert("RGB"))


class NumberScene(Scene):
    keys = {
        0: MenuKey(TextKey("0")),
        1: MenuKey(TextKey("1")),
        2: MenuKey(TextKey("2")),
        3: MenuKey(TextKey("3")),
        4: MenuKey(TextKey("4")),
        5: MenuKey(TextKey("5")),
    }


class InitialScene(Scene):
    keys = {
        0: URLKey("https://geomagical.com/", ImageKey("img/logo2.png")),
        1: PrometheusSingleStatKey(
            prometheus.thanos_prod,
            query='sum(kube_node_info{k8s_cluster="wallspice-develop"})',
            label="Dev Nodes",
        ),
        2: PrometheusSingleStatKey(
            prometheus.thanos_prod,
            query="""
                round(
                    sum(
                        container_memory_working_set_bytes{namespace="pipeline", k8s_cluster="wallspice-develop"}
                    ) / 1000000000
                )
                """,
            label="Dev RAM",
        ),
        3: PrometheusSparklineKey(
            prometheus.thanos_prod,
            query="""
                sum(
                    avg_over_time(
                        container_memory_working_set_bytes{namespace="pipeline", k8s_cluster="wallspice-develop"}[5m]
                    )
                )
                """,
            label="Dev RAM",
        ),
        4: PrometheusSingleStatKey(
            prometheus.thanos_prod,
            query='round(sum(container_memory_working_set_bytes{k8s_cluster="wallspice-develop"}) / 1000000000)',
            label="Dev RAM",
        ),
        5: PrometheusSparklineKey(
            prometheus.thanos_prod,
            query='sum(avg_over_time(container_memory_working_set_bytes{k8s_cluster="wallspice-develop"}[5m]))',
            label="Dev RAM",
        ),
        6: MenuKey(EmojiKey("🐇"), RabbitMQScene(prometheus.thanos_prod)),
        7: EmojiKey("🔔"),
        8: AnimatedKey("img/kart.gif"),
        16: AnimatedKey("img/taco.gif"),
        17: MenuKey(TextKey("Test Menu"), NumberScene()),
        18: MenuKey(EmojiKey("🌈"), BeachballScene()),
        31: PowerKey(),
    }


async def init():
    await kubernetes.load_all()
    deck = Deck.get()
    deck.push_scene(InitialScene())


def main():
    # logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    # loop.set_debug(True)
    try:
        asyncio.ensure_future(init())
        loop.run_forever()
    except KeyboardInterrupt:
        pass  # Exiting cleanly.
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == "__main__":
    main()
