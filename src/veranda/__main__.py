import asyncio

from . import kubernetes
from .deck import Deck
from .keys import AnimatedKey, PrometheusSingleStatKey, PrometheusSparklineKey, URLKey


async def init():
    await kubernetes.load_all()
    deck = Deck.get()
    deck[0] = URLKey("https://geomagical.com/", ImageKey("img/logo2.png"))
    deck[1] = PrometheusSingleStatKey(
        prometheus.thanos_prod,
        query='sum(kube_node_info{k8s_cluster="wallspice-develop"})',
        label="Dev Nodes",
    )
    deck[2] = PrometheusSingleStatKey(
        prometheus.thanos_prod,
        query='round(sum(container_memory_working_set_bytes{namespace="pipeline", k8s_cluster="wallspice-develop"}) / 1000000000)',
        label="Dev RAM",
    )
    deck[3] = PrometheusSparklineKey(
        prometheus.thanos_prod,
        query='sum(avg_over_time(container_memory_working_set_bytes{namespace="pipeline", k8s_cluster="wallspice-develop"}[5m]))',
        label="Dev RAM",
    )

    deck[4] = PrometheusSingleStatKey(
        prometheus.thanos_prod,
        query='round(sum(container_memory_working_set_bytes{k8s_cluster="wallspice-develop"}) / 1000000000)',
        label="Dev RAM",
    )
    deck[5] = PrometheusSparklineKey(
        prometheus.thanos_prod,
        query='sum(avg_over_time(container_memory_working_set_bytes{k8s_cluster="wallspice-develop"}[5m]))',
        label="Dev RAM",
    )
    deck[8] = AnimatedKey("img/kart.gif")
    deck[16] = AnimatedKey("img/taco.gif")


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
