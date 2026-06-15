from __future__ import annotations

from scripts.probe_telescope_endpoints import build_endpoints


def test_probe_defaults_are_safe_gets() -> None:
    endpoints = build_endpoints(device_number=0, include_axis=False, include_actions=False)

    assert endpoints
    assert all(endpoint.method == "GET" for endpoint in endpoints)
    assert all(endpoint.safe for endpoint in endpoints)
    assert any(endpoint.path == "/api/v1/telescope/0/rightascension" for endpoint in endpoints)
    assert not any(endpoint.path == "/api/v1/telescope/0/park" for endpoint in endpoints)


def test_probe_can_include_axis_and_actions() -> None:
    endpoints = build_endpoints(device_number=0, include_axis=True, include_actions=True)
    paths = {endpoint.path for endpoint in endpoints}

    assert "/api/v1/telescope/0/canmoveaxis?Axis=0" in paths
    assert "/api/v1/telescope/0/axisrates?Axis=0" in paths
    assert "/api/v1/telescope/0/park" not in paths
    assert any(endpoint.method == "PUT" for endpoint in endpoints)


def test_probe_park_actions_are_separate() -> None:
    endpoints = build_endpoints(
        device_number=0,
        include_axis=False,
        include_actions=False,
        include_park_actions=True,
    )
    paths = {endpoint.path for endpoint in endpoints}

    assert "/api/v1/telescope/0/park" in paths
    assert "/api/v1/telescope/0/unpark" in paths
