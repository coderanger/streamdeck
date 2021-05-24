import asyncio

from . import kubernetes, prometheus
from .deck import Deck, Scene
from .keys import (
    AnimatedKey,
    ImageKey,
    MenuKey,
    PopSceneKey,
    PowerKey,
    PrometheusSingleStatKey,
    PrometheusSparklineKey,
    TextKey,
    URLKey,
)


class NumberScene(Scene):
    keys = {
        0: PopSceneKey(TextKey("0")),
        1: TextKey("1"),
        2: TextKey("2"),
        3: TextKey("3"),
        4: TextKey("4"),
        5: TextKey("5"),
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
        8: AnimatedKey("img/kart.gif"),
        16: AnimatedKey("img/taco.gif"),
        17: MenuKey(TextKey("Test Menu"), NumberScene()),
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
