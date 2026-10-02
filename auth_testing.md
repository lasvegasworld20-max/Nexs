# NEXUS wallet authentication testing

See `memory/test_credentials.md` for current authentication and wallet guidance.

Run the existing backend test suite with `pytest backend/tests/ -q` from `/app`.
It signs nonce-bound messages with ephemeral Ed25519 keys and cleans up temporary MongoDB fixtures.
Public-chain mint, swap and payout tests are not authorized to spend real funds.
No browser wallet is injected in the running product; missing extensions offer official installation links.