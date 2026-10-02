import base64
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from base58 import b58encode
from dotenv import dotenv_values
from nacl.signing import SigningKey
from pymongo import MongoClient


def _base_url() -> str:
    raw = os.environ.get("REACT_APP_BACKEND_URL")
    if not raw:
        env = dotenv_values("/app/frontend/.env")
        raw = env.get("REACT_APP_BACKEND_URL")
    if not raw:
        raise RuntimeError("REACT_APP_BACKEND_URL is required for tests")
    return raw.rstrip("/")


@pytest.fixture(scope="session")
def base_url() -> str:
    return _base_url()


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def mongo_client():
    env = dotenv_values("/app/backend/.env")
    url = env.get("MONGO_URL")
    if not url:
        raise RuntimeError("MONGO_URL is required for cleanup/fixture setup")
    client = MongoClient(url)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(scope="session")
def mongo_db(mongo_client):
    env = dotenv_values("/app/backend/.env")
    name = env.get("DB_NAME")
    if not name:
        raise RuntimeError("DB_NAME is required for cleanup/fixture setup")
    return mongo_client[name]


@pytest.fixture(scope="session")
def creator_identity():
    sk = SigningKey.generate()
    wallet = b58encode(bytes(sk.verify_key)).decode()
    return {"sk": sk, "wallet": wallet}


@pytest.fixture(scope="session")
def participant_identity():
    sk = SigningKey.generate()
    wallet = b58encode(bytes(sk.verify_key)).decode()
    return {"sk": sk, "wallet": wallet}


def _sign_message(sk: SigningKey, message: str) -> str:
    signed = sk.sign(message.encode())
    return base64.b64encode(signed.signature).decode()


@pytest.fixture()
def creator_auth_headers(api_client, base_url, creator_identity):
    # auth feature: real ed25519 challenge and verify flow
    challenge = api_client.get(f"{base_url}/api/auth/challenge/{creator_identity['wallet']}")
    assert challenge.status_code == 200
    payload = challenge.json()
    signature = _sign_message(creator_identity["sk"], payload["message"])
    verify = api_client.post(
        f"{base_url}/api/auth/verify",
        json={
            "wallet": creator_identity["wallet"],
            "nonce": payload["nonce"],
            "signature": signature,
        },
    )
    assert verify.status_code == 200
    token = verify.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def participant_auth_headers(api_client, base_url, participant_identity):
    # auth feature: separate participant identity for permission checks
    challenge = api_client.get(f"{base_url}/api/auth/challenge/{participant_identity['wallet']}")
    assert challenge.status_code == 200
    payload = challenge.json()
    signature = _sign_message(participant_identity["sk"], payload["message"])
    verify = api_client.post(
        f"{base_url}/api/auth/verify",
        json={
            "wallet": participant_identity["wallet"],
            "nonce": payload["nonce"],
            "signature": signature,
        },
    )
    assert verify.status_code == 200
    token = verify.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def test_token_id():
    return "TEST_TOKEN_AUTOMATION"


@pytest.fixture(scope="session")
def test_bounty_id():
    return "TEST_BOUNTY_AUTOMATION"


@pytest.fixture(scope="session", autouse=True)
def test_data_setup_and_cleanup(mongo_db, creator_identity, test_token_id, test_bounty_id):
    # bounty module test data: insert a creator-owned token for authz/validation tests
    mongo_db.submissions.delete_many({"bounty_id": test_bounty_id})
    mongo_db.bounties.delete_many({"id": test_bounty_id})
    mongo_db.activity.delete_many({"token_id": test_token_id})
    mongo_db.tokens.delete_many({"id": test_token_id})

    mongo_db.tokens.insert_one(
        {
            "id": test_token_id,
            "name": "TEST Automation Token",
            "symbol": "TESTAUTO",
            "mint": creator_identity["wallet"],
            "district": "meme",
            "color": "#b6f36e",
            "x": -10,
            "z": -10,
            "creator": creator_identity["wallet"],
            "image": None,
            "market_cap": None,
            "price": None,
            "change_24h": None,
            "volume_24h": None,
            "liquidity": None,
            "holders": None,
            "source": "TEST",
            "listed_at": datetime.now(timezone.utc).isoformat(),
            "description": "Owned test token",
        }
    )

    end = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    mongo_db.bounties.insert_one(
        {
            "id": test_bounty_id,
            "token_id": test_token_id,
            "name": "TEST Bounty",
            "reward": 0.01,
            "objective": "Submit an objective with enough details",
            "rules": "TEST rules",
            "eligibility": "Open",
            "distribution": "One winner",
            "creator": creator_identity["wallet"],
            "token_symbol": "TESTAUTO",
            "token_image": None,
            "district": "meme",
            "status": "open",
            "funding": "creator-managed",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ends_at": end,
        }
    )

    yield

    mongo_db.submissions.delete_many({"bounty_id": test_bounty_id})
    mongo_db.bounties.delete_many({"id": test_bounty_id})
    mongo_db.activity.delete_many({"token_id": test_token_id})
    mongo_db.tokens.delete_many({"id": test_token_id})
    mongo_db.sessions.delete_many({"wallet": {"$in": [creator_identity["wallet"]]}})
