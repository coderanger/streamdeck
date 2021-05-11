import datetime
import os
import urllib

from typing import List, Union

import httpx

from . import kubernetes


Number = Union[int, float]


class Prometheus:
    def __init__(self, kubernetes: kubernetes.Kubernetes):
        self._client = kubernetes.for_service("prometheus-operated:web", "prometheus")

    async def instant(self, query: str) -> Union[Number, List[Number]]:
        response = await self._client.post("api/v1/query", data={"query": query})
        response.raise_for_status()
        data = response.json()
        if data["status"] != "success":
            raise Exception(f"Got a {data['status']} response for {query:r}")
        values = [d["value"][1] for d in data["data"]["result"]]
        if len(values) == 1:
            return values[0]
        return values

    async def range(self, query: str, range=datetime.timedelta(minutes=30), buckets=10):
        end = datetime.datetime.now()
        start = end - range
        step = float(range.total_seconds() / buckets)
        params = {
            "query": query,
            "start": str(int(start.timestamp())),
            "end": str(int(end.timestamp())),
            "step": str(step),
        }
        response = await self._client.post("api/v1/query_range", data=params)
        response.raise_for_status()
        data = response.json()
        if data["status"] != "success":
            raise Exception(f"Got a {data['status']} response for {query:r}")
        if len(data["data"]["result"]) != 1:
            raise Exception(f"Got {len(data['data']['result'])} results")
        return [float(d[1]) for d in data["data"]["result"][0]["values"]]


class Thanos(Prometheus):
    def __init__(self, kubernetes: kubernetes.Kubernetes):
        super().__init__(kubernetes)
        self._client = kubernetes.for_service("query:http", "thanos")


dev = Prometheus(kubernetes.dev)
prod = Prometheus(kubernetes.prod)
thanos_dev = Thanos(kubernetes.dev)
thanos_prod = Thanos(kubernetes.prod)

if __name__ == "__main__":
    import asyncio

    async def main():
        values = await dev.range("sum(container_memory_working_set_bytes)")
        print(values)

    asyncio.run(main())
