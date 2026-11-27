import asyncio
import ipaddress
import socket
import pytest

from app.services.mcp_ssrf_transport import (
    SSRFProtectionError,
    _GuardedNetworkBackend,
    _VerifiedNetworkStream,
    SSRFGuardTransport,
    _public_ip,
    _resolve_public_addresses,
)


def _dns_records(*addresses, port=443):
    records = []
    for value in addresses:
        parsed = ipaddress.ip_address(value)
        family = socket.AF_INET if parsed.version == 4 else socket.AF_INET6
        sockaddr = (value, port) if parsed.version == 4 else (value, port, 0, 0)
        records.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr))
    return records


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("8.8.8.8", "8.8.8.8"),
        ("2606:4700:4700::1111", "2606:4700:4700::1111"),
        ("::ffff:8.8.8.8", "8.8.8.8"),
    ],
)
def test_public_ip_normalization(value, expected):
    assert str(_public_ip(value)) == expected


@pytest.mark.parametrize(
    "value",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.1.1",
        "::1",
        "fc00::1",
        "::ffff:127.0.0.1",
        "192.0.2.1",
        "192.0.0.9",
        "192.31.196.1",
        "192.52.193.1",
        "192.88.99.1",
        "192.175.48.1",
        "2001:3::1",
        "2001:20::1",
        "2001:30::1",
        "64:ff9b::808:808",
    ],
)
def test_non_public_ip_is_rejected(value):
    with pytest.raises(SSRFProtectionError):
        _public_ip(value)


def test_dns_rejects_mixed_public_and_private_answers(monkeypatch):
    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("8.8.8.8", "127.0.0.1")

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SSRFProtectionError, match="non-public"):
        asyncio.run(_resolve_public_addresses("mixed.example", 443))


def test_dns_accepts_only_public_ipv4_and_ipv6(monkeypatch):
    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("8.8.8.8", "2606:4700:4700::1111")

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    result = asyncio.run(_resolve_public_addresses("public.example", 443))
    assert {str(item) for item in result} == {"8.8.8.8", "2606:4700:4700::1111"}


def test_dns_answer_count_is_bounded(monkeypatch):
    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records(*(["8.8.8.8"] * 17))

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SSRFProtectionError, match="too many"):
        asyncio.run(_resolve_public_addresses("large.example", 443))


def test_nonstandard_numeric_hostname_is_rejected_after_resolution(monkeypatch):
    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("127.0.0.1")

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    with pytest.raises(SSRFProtectionError):
        asyncio.run(_resolve_public_addresses("2130706433", 443))


class FakeStream:
    def __init__(self, peer):
        self.peer = peer
        self.closed = False
        self.tls_hostname = None

    async def receive(self, _max_bytes):
        return b""

    async def send(self, _buffer):
        return None

    async def aclose(self):
        self.closed = True

    def get_extra_info(self, info):
        return self.peer if info == "server_addr" else None

    async def start_tls(self, *, ssl_context, hostname, standard_compatible, handshake_timeout):
        del ssl_context, standard_compatible, handshake_timeout
        self.tls_hostname = hostname
        return FakeStream(self.peer)


def test_peer_verification_uses_anyio_typed_socket_attributes():
    class TypedExtraStream:
        def extra(self, attribute):
            import anyio

            assert attribute is anyio.abc.SocketAttribute.remote_address
            return ("8.8.8.8", 443)

    wrapped = _VerifiedNetworkStream(
        TypedExtraStream(), ipaddress.ip_address("8.8.8.8")
    )
    assert wrapped.get_extra_info("server_addr") == ("8.8.8.8", 443)


def test_backend_connects_to_vetted_ip_and_verifies_peer(monkeypatch):
    connected = []

    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("8.8.8.8")

    async def fake_connect_tcp(**kwargs):
        connected.append(kwargs["remote_host"])
        return FakeStream(("8.8.8.8", 443))

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.connect_tcp", fake_connect_tcp)

    stream = asyncio.run(_GuardedNetworkBackend().connect_tcp("public.example", 443))
    assert connected == ["8.8.8.8"]
    assert stream.get_extra_info("server_addr") == ("8.8.8.8", 443)



def test_backend_falls_back_only_to_other_vetted_addresses(monkeypatch):
    connected = []

    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("2606:4700:4700::1111", "8.8.8.8")

    async def fake_connect_tcp(**kwargs):
        address = kwargs["remote_host"]
        connected.append(address)
        if address == "2606:4700:4700::1111":
            raise OSError("simulated IPv6 route failure")
        return FakeStream((address, 443))

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.connect_tcp", fake_connect_tcp)

    stream = asyncio.run(_GuardedNetworkBackend().connect_tcp("dualstack.example", 443))
    assert connected == ["2606:4700:4700::1111", "8.8.8.8"]
    assert stream.get_extra_info("server_addr") == ("8.8.8.8", 443)


def test_backend_applies_socket_options_to_the_connected_socket(monkeypatch):
    raw_socket = SimpleNamespace(options=[])

    def setsockopt(*option):
        raw_socket.options.append(option)

    raw_socket.setsockopt = setsockopt

    class SocketOptionStream(FakeStream):
        def extra(self, attribute, default=None):
            import anyio

            if attribute is anyio.abc.SocketAttribute.remote_address:
                return self.peer
            if attribute is anyio.abc.SocketAttribute.raw_socket:
                return raw_socket
            return default

    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("8.8.8.8")

    async def fake_connect_tcp(**_kwargs):
        return SocketOptionStream(("8.8.8.8", 443))

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.connect_tcp", fake_connect_tcp)

    asyncio.run(
        _GuardedNetworkBackend().connect_tcp(
            "public.example",
            443,
            socket_options=[(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)],
        )
    )
    assert raw_socket.options == [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]


def test_backend_closes_stream_when_peer_does_not_match(monkeypatch):
    stream = FakeStream(("1.1.1.1", 443))

    async def fake_getaddrinfo(*_args, **_kwargs):
        return _dns_records("8.8.8.8")

    async def fake_connect_tcp(**_kwargs):
        return stream

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.connect_tcp", fake_connect_tcp)

    with pytest.raises(SSRFProtectionError, match="does not match"):
        asyncio.run(_GuardedNetworkBackend().connect_tcp("public.example", 443))
    assert stream.closed is True


def test_dns_is_revalidated_for_each_new_connection(monkeypatch):
    dns_calls = 0
    connected = []

    async def fake_getaddrinfo(*_args, **_kwargs):
        nonlocal dns_calls
        dns_calls += 1
        return _dns_records("8.8.8.8" if dns_calls == 1 else "127.0.0.1")

    async def fake_connect_tcp(**kwargs):
        connected.append(kwargs["remote_host"])
        return FakeStream((kwargs["remote_host"], 443))

    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("app.services.mcp_ssrf_transport.anyio.connect_tcp", fake_connect_tcp)

    backend = _GuardedNetworkBackend()
    asyncio.run(backend.connect_tcp("rebind.example", 443))
    with pytest.raises(SSRFProtectionError):
        asyncio.run(backend.connect_tcp("rebind.example", 443))
    assert dns_calls == 2
    assert connected == ["8.8.8.8"]


def test_tls_stream_keeps_original_hostname_and_rechecks_peer(monkeypatch):
    original = FakeStream(("8.8.8.8", 443))

    async def fake_tls_wrap(stream, *, ssl_context, hostname, standard_compatible, server_side):
        del ssl_context, standard_compatible, server_side
        stream.tls_hostname = hostname
        return FakeStream(stream.peer)

    monkeypatch.setattr("anyio.streams.tls.TLSStream.wrap", fake_tls_wrap)
    wrapped = _VerifiedNetworkStream(original, ipaddress.ip_address("8.8.8.8"))
    tls_stream = asyncio.run(wrapped.start_tls(object(), "mcp.example", 5))
    assert original.tls_hostname == "mcp.example"
    assert tls_stream.get_extra_info("server_addr") == ("8.8.8.8", 443)


def test_tls_peer_mismatch_closes_tls_stream(monkeypatch):
    original = FakeStream(("8.8.8.8", 443))
    tls_stream = FakeStream(("127.0.0.1", 443))

    async def fake_tls_wrap(stream, *, ssl_context, hostname, standard_compatible, server_side):
        del stream, ssl_context, hostname, standard_compatible, server_side
        return tls_stream

    monkeypatch.setattr("anyio.streams.tls.TLSStream.wrap", fake_tls_wrap)
    wrapped = _VerifiedNetworkStream(original, ipaddress.ip_address("8.8.8.8"))
    with pytest.raises(SSRFProtectionError):
        asyncio.run(wrapped.start_tls(object(), "mcp.example", 5))
    assert tls_stream.closed is True


def test_tls_handshake_failure_closes_raw_stream(monkeypatch):
    original = FakeStream(("8.8.8.8", 443))

    async def failing_tls_wrap(*_args, **_kwargs):
        raise ssl.SSLError("TLS handshake failure")

    monkeypatch.setattr("anyio.streams.tls.TLSStream.wrap", failing_tls_wrap)
    wrapped = _VerifiedNetworkStream(original, ipaddress.ip_address("8.8.8.8"))
    with pytest.raises(httpcore2.ConnectError):
        asyncio.run(wrapped.start_tls(object(), "mcp.example", 5))
    assert original.closed is True


def test_transport_enters_and_closes_guarded_connection_pool(monkeypatch):
    captured = {}

    class FakePool:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.entered = False
            self.closed = False

        async def __aenter__(self):
            self.entered = True

        async def aclose(self):
            self.closed = True

    monkeypatch.setattr(
        "app.services.mcp_ssrf_transport.httpcore2.AsyncConnectionPool", FakePool
    )
    monkeypatch.setattr(
        "app.services.mcp_ssrf_transport.httpx2.create_ssl_context",
        lambda **_kwargs: object(),
    )
    transport = SSRFGuardTransport()
    assert isinstance(captured["network_backend"], _GuardedNetworkBackend)
    asyncio.run(transport.__aenter__())
    assert transport._pool.entered is True
    asyncio.run(transport.aclose())
    assert transport._pool.closed is True


def test_unix_socket_transport_is_rejected():
    with pytest.raises(SSRFProtectionError):
        asyncio.run(_GuardedNetworkBackend().connect_unix_socket("/tmp/mcp.sock"))
