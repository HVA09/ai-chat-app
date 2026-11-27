"""SSRF-resistant HTTP transport for optional MCP connections.

Every new TCP connection resolves and validates all A/AAAA answers, connects to
one vetted IP literal (not the hostname), and verifies the connected peer.
MCP remains disabled by default; this transport is a defense-in-depth gate.
"""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterable
from typing import Any

import anyio
import httpcore2
import httpx2


class SSRFProtectionError(OSError):
    """Raised when an MCP destination or connected peer is not public."""


IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
_SPECIAL_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "192.0.0.0/24",       # IETF protocol assignments (includes globally-reachable exceptions)
        "192.88.99.0/24",     # Deprecated 6to4 relay anycast
        "2001:20::/28",       # ORCHIDv2
        "64:ff9b::/96",       # Well-known NAT64 translation prefix
        "64:ff9b:1::/48",     # Local-use NAT64 translation prefix
    )
)


def _public_ip(value: str) -> IPAddress:
    if not isinstance(value, str) or not value or "%" in value:
        raise SSRFProtectionError("MCP destination contains an invalid IP address.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise SSRFProtectionError("MCP destination contains an invalid IP address.") from exc

    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if (
        not address.is_global
        or address.is_reserved
        or any(address.version == network.version and address in network for network in _SPECIAL_NETWORKS)
    ):
        raise SSRFProtectionError("MCP destination resolves to a non-public IP address.")
    return address


async def _resolve_public_addresses(host: str, port: int) -> tuple[IPAddress, ...]:
    """Resolve a host and reject the entire answer set if any address is unsafe."""
    if (
        not isinstance(host, str)
        or not host
        or host != host.strip()
        or any(character in host for character in ("%", "/", "@", "\\"))
    ):
        raise SSRFProtectionError("MCP destination hostname is invalid.")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        return (_public_ip(host),)

    normalized_host = host.rstrip(".")
    if not normalized_host:
        raise SSRFProtectionError("MCP destination hostname is invalid.")

    try:
        records = await anyio.getaddrinfo(
            normalized_host,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except Exception as exc:
        raise SSRFProtectionError("MCP destination DNS resolution failed.") from exc

    addresses: list[IPAddress] = []
    for family, _socktype, _proto, _canonname, sockaddr in records:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        try:
            address = _public_ip(sockaddr[0])
        except (IndexError, TypeError) as exc:
            raise SSRFProtectionError("MCP destination DNS answer is malformed.") from exc
        addresses.append(address)

    if not addresses:
        raise SSRFProtectionError("MCP destination has no usable DNS addresses.")
    # Reject mixed public/private answers; do not silently select only the safe ones.
    return tuple(dict.fromkeys(addresses))


def _peer_ip(stream: Any) -> IPAddress:
    peer = stream.get_extra_info("server_addr")
    if not isinstance(peer, tuple) or not peer:
        raise SSRFProtectionError("Unable to verify the connected MCP peer.")
    try:
        return _public_ip(str(peer[0]))
    except (IndexError, TypeError) as exc:
        raise SSRFProtectionError("Unable to verify the connected MCP peer.") from exc


class _VerifiedNetworkStream(httpcore2.AsyncNetworkStream):
    def __init__(self, stream: Any, expected_peer: IPAddress) -> None:
        self._stream = stream
        self._expected_peer = expected_peer
        self._verify_peer()

    def _verify_peer(self) -> None:
        if _peer_ip(self._stream) != self._expected_peer:
            raise SSRFProtectionError("Connected MCP peer does not match the vetted IP.")

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        del timeout
        return await self._stream.receive(max_bytes)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        del timeout
        await self._stream.send(buffer)

    async def aclose(self) -> None:
        await self._stream.aclose()

    async def start_tls(
        self,
        ssl_context: Any,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        tls_stream = await self._stream.start_tls(
            ssl_context=ssl_context,
            hostname=server_hostname,
            standard_compatible=True,
            handshake_timeout=timeout,
        )
        try:
            return _VerifiedNetworkStream(tls_stream, self._expected_peer)
        except Exception:
            await tls_stream.aclose()
            raise

    def get_extra_info(self, info: str) -> Any:
        return self._stream.get_extra_info(info)


class _GuardedNetworkBackend(httpcore2.AsyncNetworkBackend):
    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        if socket_options:
            raise SSRFProtectionError("Custom socket options are not supported by guarded MCP transport.")

        addresses = await _resolve_public_addresses(host, port)
        # Connect to the vetted IP literal. The original hostname is retained by
        # HTTPCore for Host and TLS SNI, but is never resolved again by connect_tcp.
        selected = addresses[0]
        if timeout is None:
            stream = await anyio.connect_tcp(
                remote_host=str(selected),
                remote_port=port,
                local_host=local_address,
            )
        else:
            with anyio.fail_after(timeout):
                stream = await anyio.connect_tcp(
                    remote_host=str(selected),
                    remote_port=port,
                    local_host=local_address,
                )
        try:
            return _VerifiedNetworkStream(stream, selected)
        except Exception:
            await stream.aclose()
            raise

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        del path, timeout, socket_options
        raise SSRFProtectionError("Unix socket MCP connections are not supported.")

    async def sleep(self, seconds: float) -> None:
        await anyio.sleep(seconds)


class _CoreResponseStream(httpx2.AsyncByteStream):
    def __init__(self, stream: Any) -> None:
        self._stream = stream

    async def __aiter__(self):
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


class SSRFGuardTransport(httpx2.AsyncBaseTransport):
    """HTTPX2 transport backed by a DNS-pinning HTTPCore2 network backend."""

    def __init__(self) -> None:
        self._pool = httpcore2.AsyncConnectionPool(
            ssl_context=httpx2.create_ssl_context(verify=True, trust_env=False),
            max_connections=10,
            max_keepalive_connections=5,
            keepalive_expiry=15.0,
            http1=True,
            http2=False,
            retries=0,
            network_backend=_GuardedNetworkBackend(),
        )

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        if not isinstance(request.stream, httpx2.AsyncByteStream):
            raise TypeError("MCP HTTP request body must be an asynchronous byte stream.")

        core_request = httpcore2.Request(
            method=request.method,
            url=httpcore2.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        response = await self._pool.handle_async_request(core_request)
        return httpx2.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_CoreResponseStream(response.stream),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()
