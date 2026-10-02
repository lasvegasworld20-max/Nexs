from datetime import datetime, timedelta, timezone
import base64

from base58 import b58encode
from nacl.signing import SigningKey


# health/world/tokens/chart/activity module coverage
def test_health_endpoint(api_client, base_url):
    response = api_client.get(f"{base_url}/api/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


def test_world_catalog_and_district_count(api_client, base_url):
    response = api_client.get(f"{base_url}/api/world")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tokens"]) >= 16
    assert len(data["districts"]) == 4


def test_token_jup_exists(api_client, base_url):
    response = api_client.get(f"{base_url}/api/tokens/jup")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "JUP"


def test_token_unknown_404(api_client, base_url):
    response = api_client.get(f"{base_url}/api/tokens/unknown-token")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_chart_jup_24h_returns_candles(api_client, base_url):
    response = api_client.get(f"{base_url}/api/tokens/jup/chart", params={"period": "24H"})
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert len(data["candles"]) >= 20


def test_activity_endpoint_shape(api_client, base_url):
    response = api_client.get(f"{base_url}/api/activity")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_bounties_endpoint_available(api_client, base_url):
    response = api_client.get(f"{base_url}/api/bounties")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# auth module coverage: challenge/verify/malformed/replay behavior
def test_auth_challenge_malformed_address(api_client, base_url):
    response = api_client.get(f"{base_url}/api/auth/challenge/not-a-wallet")
    assert response.status_code == 400
    assert "Invalid Solana address" in response.json()["detail"]


def test_auth_verify_invalid_signature_rejected(api_client, base_url):
    sk = SigningKey.generate()
    wallet = b58encode(bytes(sk.verify_key)).decode()

    challenge = api_client.get(f"{base_url}/api/auth/challenge/{wallet}")
    assert challenge.status_code == 200
    body = challenge.json()

    bad_sig = base64.b64encode(b"not-a-real-ed25519-signature").decode()
    verify = api_client.post(
        f"{base_url}/api/auth/verify",
        json={"wallet": wallet, "nonce": body["nonce"], "signature": bad_sig},
    )
    assert verify.status_code == 401
    assert "verified" in verify.json()["detail"].lower()


def test_auth_replay_nonce_rejected(api_client, base_url):
    sk = SigningKey.generate()
    wallet = b58encode(bytes(sk.verify_key)).decode()

    challenge = api_client.get(f"{base_url}/api/auth/challenge/{wallet}")
    payload = challenge.json()
    signature = base64.b64encode(sk.sign(payload["message"].encode()).signature).decode()

    first = api_client.post(
        f"{base_url}/api/auth/verify",
        json={"wallet": wallet, "nonce": payload["nonce"], "signature": signature},
    )
    assert first.status_code == 200

    replay = api_client.post(
        f"{base_url}/api/auth/verify",
        json={"wallet": wallet, "nonce": payload["nonce"], "signature": signature},
    )
    assert replay.status_code == 401
    assert "expired" in replay.json()["detail"].lower()


# launches module coverage: invalid tx/wrong wallet reject
def test_launch_rejects_unconfirmed_or_invalid_transaction(api_client, base_url, creator_auth_headers):
    payload = {
        "name": "Invalid Launch",
        "symbol": "INVLD",
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "signature": "5" * 88,
        "district": "meme",
        "description": "test",
        "color": "#b6f36e",
        "image": None,
    }
    response = api_client.post(f"{base_url}/api/launches", json=payload, headers=creator_auth_headers)
    assert response.status_code in [400, 403, 409]
    assert "detail" in response.json()


def test_launch_requires_auth(api_client, base_url):
    payload = {
        "name": "No Auth Launch",
        "symbol": "NOAUTH",
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "signature": "6" * 88,
        "district": "meme",
        "description": "test",
        "color": "#b6f36e",
        "image": None,
    }
    response = api_client.post(f"{base_url}/api/launches", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()


# community + bounty module coverage with test-only token fixture
def test_community_post_min_length_validation(api_client, base_url, creator_auth_headers, test_token_id):
    short_post = api_client.post(
        f"{base_url}/api/tokens/{test_token_id}/community",
        json={"content": "short"},
        headers=creator_auth_headers,
    )
    assert short_post.status_code == 422

    valid = api_client.post(
        f"{base_url}/api/tokens/{test_token_id}/community",
        json={"content": "TEST message over ten chars"},
        headers=creator_auth_headers,
    )
    assert valid.status_code == 200

    feed = api_client.get(f"{base_url}/api/activity", params={"token_id": test_token_id})
    assert any(item.get("kind") == "post" for item in feed.json())


def test_bounty_creation_creator_only(api_client, base_url, participant_auth_headers, test_token_id):
    end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = api_client.post(
        f"{base_url}/api/bounties",
        json={
            "token_id": test_token_id,
            "name": "Unauthorized Create",
            "reward": 0.01,
            "objective": "Objective text with enough characters",
            "rules": "rules",
            "eligibility": "open",
            "ends_at": end,
            "distribution": "one winner",
        },
        headers=participant_auth_headers,
    )
    assert response.status_code == 403


def test_bounty_creation_future_date_required(api_client, base_url, creator_auth_headers, test_token_id):
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    response = api_client.post(
        f"{base_url}/api/bounties",
        json={
            "token_id": test_token_id,
            "name": "Past Date Bounty",
            "reward": 0.01,
            "objective": "Objective text with enough characters",
            "rules": "rules",
            "eligibility": "open",
            "ends_at": past,
            "distribution": "one winner",
        },
        headers=creator_auth_headers,
    )
    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_bounty_submission_duplicate_and_own_entry_rules(
    api_client,
    base_url,
    creator_auth_headers,
    participant_auth_headers,
    test_bounty_id,
):
    own = api_client.post(
        f"{base_url}/api/bounties/{test_bounty_id}/submissions",
        json={"content": "creator should not be able to submit"},
        headers=creator_auth_headers,
    )
    assert own.status_code == 400

    first = api_client.post(
        f"{base_url}/api/bounties/{test_bounty_id}/submissions",
        json={"content": "participant first entry for duplicate check"},
        headers=participant_auth_headers,
    )
    assert first.status_code == 200

    duplicate = api_client.post(
        f"{base_url}/api/bounties/{test_bounty_id}/submissions",
        json={"content": "participant second entry should fail duplicate"},
        headers=participant_auth_headers,
    )
    assert duplicate.status_code == 409


def test_bounty_closed_rejects_entries(
    api_client, base_url, mongo_db, participant_auth_headers, test_bounty_id
):
    mongo_db.bounties.update_one(
        {"id": test_bounty_id},
        {"$set": {"ends_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}},
    )
    closed = api_client.post(
        f"{base_url}/api/bounties/{test_bounty_id}/submissions",
        json={"content": "should fail because closed bounty"},
        headers=participant_auth_headers,
    )
    assert closed.status_code == 400

    mongo_db.bounties.update_one(
        {"id": test_bounty_id},
        {"$set": {"ends_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()}},
    )


# payout module coverage: noncreator + forged signature rejection without spending funds
def test_award_noncreator_forbidden(
    api_client,
    base_url,
    mongo_db,
    creator_identity,
    participant_auth_headers,
    test_bounty_id,
):
    recipient_wallet = b58encode(bytes(SigningKey.generate().verify_key)).decode()
    submission = {
        "id": "TEST_SUBMISSION_FOR_AWARD",
        "bounty_id": test_bounty_id,
        "wallet": recipient_wallet,
        "content": "valid content for award test",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    mongo_db.submissions.delete_many({"id": "TEST_SUBMISSION_FOR_AWARD"})
    mongo_db.submissions.insert_one(submission)

    response = api_client.post(
        f"{base_url}/api/bounties/{test_bounty_id}/award",
        json={"submission_id": submission["id"], "signature": "8" * 88},
        headers=participant_auth_headers,
    )
    assert response.status_code == 403


def test_award_forged_signature_rejected(
    api_client,
    base_url,
    mongo_db,
    creator_auth_headers,
    creator_identity,
    test_bounty_id,
):
    recipient_wallet = b58encode(bytes(SigningKey.generate().verify_key)).decode()
    submission = {
        "id": "TEST_SUBMISSION_FOR_FORGED_SIG",
        "bounty_id": test_bounty_id,
        "wallet": recipient_wallet,
        "content": "valid content for forged signature test",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    mongo_db.submissions.delete_many({"id": "TEST_SUBMISSION_FOR_FORGED_SIG"})
    mongo_db.submissions.insert_one(submission)

    response = api_client.post(
        f"{base_url}/api/bounties/{test_bounty_id}/award",
        json={"submission_id": submission["id"], "signature": "9" * 88},
        headers=creator_auth_headers,
    )
    assert response.status_code in [400, 502]
    assert len(response.text) > 0


def test_presence_owner_only_patch(api_client, base_url, participant_auth_headers, test_token_id):
    response = api_client.patch(
        f"{base_url}/api/tokens/{test_token_id}/presence",
        json={"description": "new desc", "color": "#b6f36e", "image": None},
        headers=participant_auth_headers,
    )
    assert response.status_code == 403


def test_presence_validation_rejects_bad_payload(api_client, base_url, creator_auth_headers, test_token_id):
    response = api_client.patch(
        f"{base_url}/api/tokens/{test_token_id}/presence",
        json={"description": "ok", "color": "bad-color", "image": None},
        headers=creator_auth_headers,
    )
    assert response.status_code == 422
