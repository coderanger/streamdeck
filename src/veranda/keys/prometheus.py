import asyncio

from .base import Key
from .chart import SparklineKey
from .text import TextKey
from .url import GrafanaExploreURLKey


class PrometheusKey(Key):
    def __init__(self, prom, query, key, **kwargs):
        super().__init__(
            key=GrafanaExploreURLKey("https://grafana.mysugarcube.com", query, key),
            **kwargs,
        )
        self._prom = prom
        self._query = query

    async def update(self, deck, index):
        while True:
            to_set = await self.query()
            await self.set_value(deck, index, **to_set)
            await asyncio.sleep(30)

    async def query(self):
        raise NotImplementedError


class PrometheusSingleStatKey(PrometheusKey):
    def __init__(self, prom, query, label, **kwargs):
        key = TextKey("", label)
        super().__init__(prom, query, key, **kwargs)

    async def query(self):
        value = await self._prom.instant(self._query)
        if isinstance(value, float):
            return {"text", f"{value:.2f}"}
        else:
            return {"text": str(value)}


class PrometheusSparklineKey(PrometheusKey):
    def __init__(self, prom, query, label, **kwargs):
        key = SparklineKey([0, 0], label)
        super().__init__(prom, query, key, **kwargs)

    async def query(self):
        values = await self._prom.range(self._query)
        return {"values": values}
