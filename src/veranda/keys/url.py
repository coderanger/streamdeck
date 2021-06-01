import json
import webbrowser

from urllib.parse import urlencode

from .base import Key


class URLKey(Key):
    def __init__(self, url: str, key: Key, **kwargs):
        super().__init__(key=key, **kwargs)
        self._url = url

    async def on_press(self, deck, index):
        await super().on_press(deck.index)
        webbrowser.open(self._url, new=2)


class GrafanaExploreURLKey(URLKey):
    def __init__(self, grafana_url: str, query: str, key: Key, **kwargs):
        # https://grafana.example.com/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Thanos%22,%7B%22expr%22:%22sum(avg_over_time(container_memory_working_set_bytes%7Bnamespace%3D%5C%22pipeline%5C%22%7D%5B5m%5D))%22%7D,%7B%22ui%22:%5Btrue,true,true,%22none%22%5D%7D%5D
        params = [
            "now-30m",
            "now",
            "Thanos",
            {"expr": query},
            {"ui": [True, True, True, "none"]},
        ]
        qs = urlencode(
            {
                "orgId": "1",
                "left": json.dumps(params),
            }
        )
        url = f"{grafana_url}/explore?{qs}"
        super().__init__(url, key, **kwargs)
