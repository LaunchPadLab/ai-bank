"""CLI transport/auth gating logic."""

from aibank_mcp.cli import _build_parser, _is_loopback, _should_refuse_http


def test_is_loopback():
    assert _is_loopback("127.0.0.1")
    assert _is_loopback("localhost")
    assert _is_loopback("::1")
    assert not _is_loopback("0.0.0.0")
    assert not _is_loopback("192.168.1.5")


def test_should_refuse_http():
    # loopback without a token is fine (local client launches it)
    assert _should_refuse_http("127.0.0.1", has_token=False, allow_insecure=False) is False
    # non-loopback without a token and no opt-out: refuse (fail-safe)
    assert _should_refuse_http("0.0.0.0", has_token=False, allow_insecure=False) is True
    # non-loopback, no token, but explicitly allowed (behind a proxy): fine
    assert _should_refuse_http("0.0.0.0", has_token=False, allow_insecure=True) is False
    # non-loopback WITH a token: fine
    assert _should_refuse_http("0.0.0.0", has_token=True, allow_insecure=False) is False


def test_parser_defaults_and_flags():
    args = _build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.allow_insecure_http is False

    args = _build_parser().parse_args(["--transport", "http", "--host", "0.0.0.0", "--allow-insecure-http"])
    assert args.transport == "http"
    assert args.allow_insecure_http is True
