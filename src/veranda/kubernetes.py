import asyncio

from typing import Generator
from urllib.parse import urljoin

import httpx

from kubernetes_asyncio import client, config


class KubernetesAuth(httpx.Auth):
    """Auth helper for httpx to pull from a K8s config."""

    def __init__(self, config: client.Configuration):
        self._config = config

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, None, None]:
        settings = self._config.auth_settings()
        if settings:
            # TODO something better if one day other auth options are supported in the client lib.
            token_settings = settings["BearerToken"]
            request.headers[token_settings["key"]] = token_settings["value"]
        yield request


class Kubernetes:
    """A facade for talking to services inside Kubernetes via the apiserver proxy."""

    def __init__(self, context: str):
        self.context = context
        self.config = client.Configuration()
        self.loader = None
        self.reload_task = None
        self.api = None
        self.core_v1 = None
        self.client = None

    async def load(self) -> None:
        self.loader = await config.load_kube_config(
            context=self.context, client_configuration=self.config, persist_config=False
        )
        self.reload_task = asyncio.create_task(
            config.refresh_token(self.loader, self.config)
        )
        self.api = client.ApiClient(configuration=self.config)
        self.core_v1 = client.CoreV1Api(self.api)
        # Build an HTTPX client that can talk to kube-apiserver.
        client_cert = None
        if self.config.cert_file:
            client_cert = (self.config.cert_file, self.config.key_file)
        ssl_context = httpx.create_ssl_context(
            verify=self.config.verify_ssl,
            cert=client_cert,
        )
        if self.config.ssl_ca_cert:
            ssl_context.load_verify_locations(cafile=self.config.ssl_ca_cert)
        self.client = httpx.AsyncClient(
            auth=KubernetesAuth(self.config),
            base_url=urljoin(self.config.host, "api/"),
            verify=ssl_context,
        )

    def proxy_request(
        self, method: str, name: str, namespace: str, path: str, *args, **kwargs
    ) -> httpx.Response:
        url = f"v1/namespaces/{namespace}/services/{name}/proxy/{path.lstrip('/')}"
        return self.client.request(method, url, *args, **kwargs)

    def for_service(self, name: str, namespace: str) -> "ScopedKubernetes":
        return ScopedKubernetes(self, name, namespace)


class ScopedKubernetes:
    """A helper object for scoped access so the name/namespace doesn't need to be repeated."""

    def __init__(self, parent: Kubernetes, name: str, namespace: str):
        self._parent = parent
        self._name = name
        self._namespace = namespace

    def get(self, path: str, *args, **kwargs) -> httpx.Response:
        return self._parent.proxy_request(
            "GET", self._name, self._namespace, path, *args, **kwargs
        )

    def post(self, path: str, *args, **kwargs) -> httpx.Response:
        return self._parent.proxy_request(
            "POST", self._name, self._namespace, path, *args, **kwargs
        )


dev = Kubernetes("wallspice-develop")
prod = Kubernetes("wallspice-prod")


async def load_all() -> None:
    await asyncio.gather(dev.load(), prod.load())
