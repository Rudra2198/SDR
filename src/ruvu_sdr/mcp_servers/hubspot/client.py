"""HubSpot REST client boundary (Plane 04 tooling).

The ONLY place that touches the HubSpot network. Tools depend on the
``HubSpotClientProtocol`` interface (not a concrete class), so tests and the
contract eval inject a fake and run with no token and no network.

Eval-first (step 3) defines the error type and the interface; the real httpx
client (``HubSpotClient``) lands in step 4.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Protocol, runtime_checkable

import httpx

from ruvu_sdr.config import get_settings

HUBSPOT_BASE_URL = "https://api.hubapi.com"
DEFAULT_TIMEOUT = 30.0


class HubSpotError(RuntimeError):
    """Raised on a non-2xx HubSpot response. Carries the HTTP status code.

    ``read_company`` inspects ``status`` to turn a 404 into ``None`` (a contact may
    have no associated company); any other status propagates.
    """

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"HubSpot {status}: {message}")
        self.status = status
        self.message = message


@runtime_checkable
class HubSpotClientProtocol(Protocol):
    """The narrow surface the tools need: authed GET/POST returning parsed JSON.

    Both the real ``HubSpotClient`` and the test/eval ``FakeHubSpotClient`` satisfy
    this. Non-2xx responses raise ``HubSpotError``.
    """

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]: ...


class HubSpotClient:
    """The real HubSpot REST client (httpx). The network boundary — nothing else
    in the package talks to HubSpot directly.

    Bearer-authed with the private-app token from ``Settings.hubspot_access_token``
    (override with ``token=``). Every non-2xx response becomes a ``HubSpotError``
    carrying the status, so callers branch on ``err.status`` (e.g. 404 -> None) and
    never see a raw ``httpx`` exception. Satisfies ``HubSpotClientProtocol``.

    Pass ``http_client=`` (e.g. an ``httpx.Client`` over a ``MockTransport``) to test
    transport/error handling without a network or token.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = HUBSPOT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        if http_client is not None:
            self._client = http_client
            return
        token = token or get_settings().hubspot_access_token
        if not token:
            raise ValueError(
                "HUBSPOT_ACCESS_TOKEN is not set (see .env / .env.example) and no "
                "token was passed to HubSpotClient."
            )
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._parse(self._client.get(path, params=params))

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._parse(self._client.post(path, json=json))

    @staticmethod
    def _parse(resp: httpx.Response) -> dict[str, Any]:
        """Return the JSON body on 2xx (``{}`` when empty), else raise HubSpotError."""
        if resp.is_success:
            return resp.json() if resp.content else {}
        raise HubSpotError(resp.status_code, resp.text[:500])

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HubSpotClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
