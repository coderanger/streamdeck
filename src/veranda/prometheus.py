import datetime

from typing import List, Union

from . import kubernetes


Number = Union[int, float]


class Prometheus:
    def __init__(self, kubernetes: kubernetes.Kubernetes):
        self._client = kubernetes.for_service("prometheus-operated:web", "prometheus")

    async def instant(self, query: str) -> Union[Number, List[Number]]:
        results = await self._request("query", data={"query": query})
        values = [d["value"][1] for d in results]
        if len(values) == 1:
            return values[0]
        return values

    async def instant_by_label(self, query: str, label: str) -> dict[str, Number]:
        results = await self._request("query", data={"query": query})
        return {d["metric"][label]: d["value"][1] for d in results}

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
        results = await self._request("query_range", params)
        if len(results) != 1:
            raise Exception(f"Got {len(results)} results")
        return [float(d[1]) for d in results[0]["values"]]

    async def _request(self, url: str, data: dict) -> Union[dict, list]:
        """Make a request to the Prometheus API."""
        response = await self._client.post(f"api/v1/{url}", data=data)
        response.raise_for_status()
        data = response.json()
        if data["status"] != "success":
            query = data.get("query")
            raise Exception(f"Got a {data['status']} response for {query:r}")
        return data["data"]["result"]


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
