import asyncio
import json as json_lib
from typing import Optional, Union, Any

from kubernetes_asyncio import client, config


class KubernetesResponse:
    """A helper object to make the weird 'HTTP info' return values from the K8s client look more like an httpx response object."""

    def __init__(self, data: str, status: int, headers: dict[str, str]):
        self._data = data
        self._status = status
        self._headers = headers

    def raise_for_status(self) -> None:
        if self._status != 200:
            raise Exception(f"Request failed {self._status}: {self._data}")

    def json(self) -> Any:
        return json_lib.loads(self._data)


class Kubernetes:
    """A facade for talking to services inside Kubernetes via the apiserver proxy."""

    def __init__(self, context: str):
        self.context = context
        self.config = client.Configuration()
        self.loader = None
        self.reload_task = None
        self.api = None
        self.core_v1_api = None

    async def load(self) -> None:
        self.loader = await config.load_kube_config(
            context=self.context, client_configuration=self.config, persist_config=False
        )
        self.reload_task = asyncio.create_task(
            config.refresh_token(self.loader, self.config)
        )
        self.api = client.ApiClient(configuration=self.config)
        self.core_v1_api = client.CoreV1Api(self.api)

    async def get(self, name: str, namespace: str, path: str) -> KubernetesResponse:
        if self.core_v1_api is None:
            raise Exception("Kubernetes client is not initialized")
        (
            data,
            status,
            headers,
        ) = await self.core_v1_api.connect_get_namespaced_service_proxy_with_path_with_http_info(
            name, namespace, path
        )
        return KubernetesResponse(data, status, headers)

    async def post(
        self,
        name: str,
        namespace: str,
        path: str,
        data: Optional[Union[str, dict]] = None,
        json: Optional[Any] = None,
    ) -> KubernetesResponse:
        # There is a connect_post_namespaced_service_proxy_with_path but it doesn't allow setting a body.
        if data is not None and json is not None:
            raise ValueError("cannot pass both body and json")
        if json is not None:
            data = json_lib.dumps(json)
        post_params = {}
        body = data
        if isinstance(data, dict):
            post_params = data
            body = None

        data, status, headers = await self.api.call_api(
            "/api/v1/namespaces/{namespace}/services/{name}/proxy/{path}",
            "POST",
            {"name": name, "namespace": namespace, "path": path},
            {},
            {"Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded"},
            body=body,
            post_params=post_params,
            response_type="str",
            auth_settings=["BearerToken"],
            async_req=False,
            _return_http_data_only=False,
        )
        print(repr(data))
        return KubernetesResponse(data, status, headers)

    def for_service(self, name: str, namespace: str) -> "ScopedKubernetes":
        return ScopedKubernetes(self, name, namespace)


class ScopedKubernetes:
    """A helper object for scoped access so the name/namespace doesn't need to be repeated."""

    def __init__(self, parent: Kubernetes, name: str, namespace: str):
        self._parent = parent
        self._name = name
        self._namespace = namespace

    def get(self, path: str) -> KubernetesResponse:
        return self._parent.get(name=self._name, namespace=self._namespace, path=path)

    def post(
        self,
        path: str,
        data: Optional[Union[str, dict]] = None,
        json: Optional[Any] = None,
    ) -> KubernetesResponse:
        return self._parent.post(self._name, self._namespace, path, data, json)


dev = Kubernetes("wallspice-develop")
prod = Kubernetes("wallspice-prod")


async def load_all() -> None:
    await asyncio.gather(dev.load(), prod.load())
