import os
import urllib
from typing import List, Union

import httpx

Number = Union[int, float]


class Prometheus:
    def __init__(self, url: str, cookie: str):
        self._url = url
        api_url = urllib.parse.urljoin(url, '/api/v1/')
        cookies = httpx.Cookies({'_forward_auth': cookie})
        self._client = httpx.AsyncClient(base_url=api_url, cookies=cookies)

    async def instant(self, query: str) -> Union[Number, List[Number]]:
        response = await self._client.post('query', data={'query': query})
        response.raise_for_status()
        data = response.json()
        if data['status'] != 'success':
            raise Exception(f"Got a {data['status']} response for {query:r}")
        values = [d['value'][1] for d in data['data']['result']]
        if len(values) == 1:
            return values[0]
        return values

dev = Prometheus('https://prometheus.develop.mysugarcube.com', os.environ['DEV_COOKIE'])
prod = Prometheus('https://prometheus.prod.mysugarcube.com', os.environ['PROD_COOKIE'])
