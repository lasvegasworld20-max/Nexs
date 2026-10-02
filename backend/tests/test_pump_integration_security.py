import pytest


# pump integration module coverage: auth guards, validation, provenance, and activity responses
def test_pump_config_points_to_official_create(api_client, base_url):
    response = api_client.get(f"{base_url}/api/pump/config")
    assert response.status_code == 200
    data = response.json()
    assert data["launch_mode"] == "official_redirect"
    assert data["create_url"] == "https://pump.fun/create"


def test_pump_verify_requires_auth(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/pump/verify",
        json={"mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump", "signature": "1" * 88},
    )
    assert response.status_code == 401


def test_pump_import_requires_auth(api_client, base_url):
    response = api_client.post(
        f"{base_url}/api/pump/import",
        json={
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "signature": "1" * 88,
            "district": "meme",
            "color": "#b6f36e",
        },
    )
    assert response.status_code == 401


def test_pump_verify_rejects_malformed_mint(api_client, base_url, creator_auth_headers):
    response = api_client.post(
        f"{base_url}/api/pump/verify",
        json={"mint": "short", "signature": "1" * 88},
        headers=creator_auth_headers,
    )
    assert response.status_code == 422


def test_pump_verify_rejects_invalid_signature_encoding(api_client, base_url, creator_auth_headers):
    response = api_client.post(
        f"{base_url}/api/pump/verify",
        json={"mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump", "signature": "0" * 88},
        headers=creator_auth_headers,
    )
    assert response.status_code == 400
    assert "Invalid Solana transaction signature" in response.json()["detail"]


def test_pump_verify_rejects_spoofed_extra_fields(api_client, base_url, creator_auth_headers):
    response = api_client.post(
        f"{base_url}/api/pump/verify",
        json={
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "signature": "1" * 88,
            "creator": "fake",
            "name": "fake",
        },
        headers=creator_auth_headers,
    )
    assert response.status_code == 422


def test_pump_import_rejects_spoofed_extra_fields(api_client, base_url, creator_auth_headers):
    response = api_client.post(
        f"{base_url}/api/pump/import",
        json={
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "signature": "1" * 88,
            "district": "meme",
            "color": "#b6f36e",
            "creator": "fake",
            "name": "fake",
        },
        headers=creator_auth_headers,
    )
    assert response.status_code == 422


def test_pump_verify_wrong_wallet_rejected_for_real_creation(api_client, base_url, creator_auth_headers):
    payload = {
        "mint": "2mh3b9fhXhkjqNrUjNqSbR1czsy6sz4Xh3WJkKYvpump",
        "signature": "4T9picqmw7jgntdFJYFGvN3woMqCAcWVM7eF5Zv3bARYjhvCoVXQwyaUjB9DoZTWWPvsguUcQguLVDrC2iXiXB9A",
    }
    response = api_client.post(f"{base_url}/api/pump/verify", json=payload, headers=creator_auth_headers)
    if response.status_code in [429, 500, 502, 503, 504]:
        pytest.skip(f"RPC temporarily unavailable/rate-limited: {response.status_code}")
    assert response.status_code == 403
    assert "created this token" in response.json()["detail"]


def test_pump_import_wrong_wallet_rejected_for_real_creation(api_client, base_url, creator_auth_headers):
    payload = {
        "mint": "2mh3b9fhXhkjqNrUjNqSbR1czsy6sz4Xh3WJkKYvpump",
        "signature": "4T9picqmw7jgntdFJYFGvN3woMqCAcWVM7eF5Zv3bARYjhvCoVXQwyaUjB9DoZTWWPvsguUcQguLVDrC2iXiXB9A",
        "district": "meme",
        "color": "#b6f36e",
    }
    response = api_client.post(f"{base_url}/api/pump/import", json=payload, headers=creator_auth_headers)
    if response.status_code in [429, 500, 502, 503, 504]:
        pytest.skip(f"RPC temporarily unavailable/rate-limited: {response.status_code}")
    assert response.status_code == 403
    assert "created this token" in response.json()["detail"]


def test_pump_verify_rejects_mint_signature_mismatch(api_client, base_url, creator_auth_headers):
    response = api_client.post(
        f"{base_url}/api/pump/verify",
        json={
            "mint": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "signature": "4T9picqmw7jgntdFJYFGvN3woMqCAcWVM7eF5Zv3bARYjhvCoVXQwyaUjB9DoZTWWPvsguUcQguLVDrC2iXiXB9A",
        },
        headers=creator_auth_headers,
    )
    if response.status_code in [429, 500, 502, 503, 504]:
        pytest.skip(f"RPC temporarily unavailable/rate-limited: {response.status_code}")
    assert response.status_code == 400


def test_world_pump_provenance_not_suffix_only(api_client, base_url):
    response = api_client.get(f"{base_url}/api/world")
    assert response.status_code == 200
    data = response.json()["tokens"]
    by_id = {t["id"]: t for t in data}
    assert by_id["fartcoin"].get("pump_verified") is True
    assert by_id["fartcoin"].get("launch_provider") == "pump.fun"
    assert by_id["jup"].get("pump_verified") in [None, False]


def test_fartcoin_trading_activity_endpoint_shape(api_client, base_url):
    response = api_client.get(f"{base_url}/api/tokens/fartcoin/trading-activity")
    assert response.status_code == 200
    data = response.json()
    assert "trades" in data and isinstance(data["trades"], list)
    assert "scope" in data and "sample" in data["scope"].lower()


def test_jup_trading_activity_honest_empty(api_client, base_url):
    response = api_client.get(f"{base_url}/api/tokens/jup/trading-activity")
    assert response.status_code == 200
    data = response.json()
    assert data["trades"] == []
    assert data["available"] is False
