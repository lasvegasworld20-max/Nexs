# NEXUS — Living Solana World

## Original problem statement

Build a crypto launchpad that feels like a living open-world game, not a traditional token launchpad.

Use Ingress (https://ingress.com/) for its open-world map, locations, territories, exploration and map-based interaction. Use GitCity (https://gitcity.xyz/) for a world made from buildings, where entities are represented as buildings.

Every token launched through the platform becomes part of a persistent crypto world. The primary experience is an interactive open-world map containing token buildings, not token cards. The world should feel like a real place, continuously changing as the crypto market changes.

The homepage opens directly into a large, explorable map with different territories/locations, roads/areas, token buildings, different building sizes, points of interest, community activity, territory boundaries, zoom and movement. The world itself is the main interface.

Every token gets a building. Building height is determined by market cap: $500K is a small building, $5M medium, $50M a skyscraper. Heights grow/shrink with market cap. Buildings have visual token identity. Clicking a building navigates to its Token Dashboard, not a popup. Dashboard: token name/ticker/image, market cap, price, volume, holders, price chart, buy, sell, token information, community activity, active bounties and history.

Creators define custom bounties, not fixed quests: bounty name, reward, objective, rules/conditions, duration, eligibility, winner/reward distribution. Creator creates the game; community plays for the bounty. Bounties belong to token territories. Territories should read as actual locations, not rectangular UI cards.

Launch flow: a token receives a world location and building; building reflects market cap; creator customizes token presence and creates bounties; community interacts with territory; building always leads to dashboard.

Design: Crypto + Open World + City + Game, not crypto dashboard + map background. World is the hero, modern game-like interface, depth and scale, different building heights/silhouettes, clean functional overlays. Full-screen primary world map with top logo/search/connect wallet/explore and side/bottom map controls/world information/bounties/leaderboard/activity. No landing page. Core loop: Launch → World → Building → Territory → Bounty → Community → Token Dashboard → Trade. Intuitive without long explanations.

## Explicit user choices

- **Real wallet connection and on-chain trading; Solana chain.**
- **Top-down territory map featuring 3D token buildings; Stylized 3D crypto city with explorable districts and a dynamic skyline; Let me choose the best direction based on the concept.**
- **“Jangan ada tulisan demo atau simulate semacamnta buat sudah produk jadi walaupun masih belum public.”**
- Communicate with user in Indonesian. Interface is polished English, following original brief. No fabricated market data, holders, balances, rewards or successful transactions.

## Personas

1. Explorer/trader: discover tokens spatially, inspect live market data, swap non-custodially, return to the world.
2. Token creator: mint a token, establish a territory, customize its presence, publish custom bounties, approve and pay winners.
3. Community participant: sign in with wallet, post messages, discover bounties and submit work.

## Architecture decisions

- React 19 / CRA + CRACO, React Router; Shadcn primitives, Sonner, Lucide, Recharts. Route pages `/`, `/token/:id`, `/launch`, `/bounties`, `/leaderboard`.
- Imperative Three.js orthographic world with OrbitControls. Full-screen live canvas, deterministic city scenery via instancing, irregular district boundaries, roads/canal/bridges/Genesis Plaza, ambient traffic, token towers and collision-aware projected labels. Decorative low-rise scenery does not represent extra tokens.
- Market cap determines smoothly interpolated tower height using logarithmic visual scaling. Heights update with real market snapshots, not random movement.
- FastAPI modular routers, Motor/MongoDB. Models/data in `tokens`, `activity`, `bounties`, `submissions`, `challenges`, `sessions`. Queries exclude BSON `_id`; ISO UTC dates for world records, native UTC datetimes for TTL authentication.
- Real catalog: 16 Solana token identities cross-checked against CoinGecko platform registry, exact mint addresses. Do not discover identities by ticker alone because cloned tokens can appear in DEX search.
- DEX Screener token snapshots, request-driven 60-second cache; GeckoTerminal actual OHLCV candles with 120-second cache. Missing/stale data retained explicitly with timestamp; no invented values. No background job/scheduler was introduced.
- Four districts: Meme Quarter (green), DeFi Heights (amber), Neural District (lavender), The Waterfront (cyan). Dark neutral technical palette, Unbounded + Manrope + JetBrains Mono.
- Non-custodial Phantom/Solflare injected wallet integration. Ed25519, origin-bound, one-use, 5-minute challenges. Hashed random bearer sessions expire after 12 hours. No seed/private keys persisted.
- Solana mainnet RPC proxied through `/api/rpc` using a method allowlist. Protected `MONGO_URL` and `REACT_APP_BACKEND_URL` preserved. Service URLs stored in environment.
- Official keyless Jupiter Plugin integrated on token dashboard, actual SOL/token swap routing, explicit buy/sell defaults, official external Jupiter deep link fallback. Plugin handles its own wallet connection. POSIX locale normalization avoids Intl crash in embedded browsers.
- **Superseded by the Pump.fun integration below:** the initial independent SPL mint flow is removed. No client-side independent token creation remains; authenticated `/api/launches` now returns 410.
- Pump token name/symbol/metadata URI come from independently verified Pump creation instructions/events. Off-chain image/description are read from the referenced metadata, subject to safe URL and payload bounds. NEXUS only controls its world representation.
- Bounties: creator-only creation; custom text conditions/eligibility/distribution; SOL reward, deadline. Entries are wallet-authenticated, one per wallet; owner cannot self-enter. Winner payout requires a real wallet-signed SOL transfer and backend verifies source/destination/amount before award. Rewards creator-managed, not escrow; UI explicitly states this. Pending payout signature stored for safe retry.

## Implemented — 2026-10-02

- Full-screen navigable city, 16 real token buildings, market-cap heights, colored territories, minimap, camera coordinates, zoom/pan/rotate/recenter/top-down/fullscreen, map layers and district focus.
- Search by name/symbol/mint, Ctrl/Cmd+K, routed dashboard, global wallet connection and launch access (including mobile).
- World pulse, real market cap/volume, token ranking, honest empty activity/bounty states.
- Token dashboard: live metrics, real historical chart/periods, Jupiter buy/sell, mint address/copy/explorer, community posts, bounties/history, creator presence customization.
- Leaderboard with filters/search/sort and token navigation.
- Wallet-authenticated real token-creation flow and verified persistent world registration. Mainnet acknowledgement and cost/liquidity disclosures.
- Creator bounty publishing, participant submissions, public entries, verified single-winner SOL payout flow, creator-only ownership checks.
- Responsive layouts tested at desktop 1920px and mobile 390px, no body horizontal overflow.
- Chart sizing warning fixed after testing by measuring positive dimensions via ResizeObserver before rendering Recharts; sub-dollar price precision and intraday chart axes improved.
- Expired/invalid wallet sessions clear on HTTP 401 so the next authenticated attempt requests a fresh wallet signature.
- Initial screenshot showed labels overlapping; collision logic now uses measured DOM dimensions. Map control/bounty footer collision fixed; header launch remains available when sidebar launch is hidden on shorter screens.

## Validation

- `/app/test_reports/iteration_1.json`: 21/21 backend tests passed; frontend flows passed except chart sizing warning subsequently fixed.
- Automated coverage: real data APIs, token/404/chart, wallet malformed/invalid/replay rejection, session login with ephemeral signing keys, creator-only bounties/presence, entry validation/duplicates/closed states, community persistence, payout authorization rejection, launch rejection. Temporary world fixtures removed after tests.
- Browser: canvas rendered, controls/district/layers, search/Ctrl+K, token routing, real chart, wallet modal, launch validation, leaderboard, mobile overflow. Jupiter rendered after locale normalization.
- Final self-check showed explicit chart size 854×295 and real chart SVG, period switches, rendered Jupiter SOL→JUP form, launch form and return to world.
- **No real funds were spent and no funded wallet mint/swap/payout was executed by the agent.** Those branches require the user's own wallet approval. Never label their success as verified until confirmed on-chain.
- Test auth guidance: `/app/memory/test_credentials.md`, `/app/auth_testing.md`. No passwords or permanent funded test wallets.

## Known limitations and prioritized backlog

### P0 — Before accepting public real-money use
- User-authorized launch on official Pump.fun, then creator-authenticated verify/import in the browser. Read-only verification of a real successful Pump mainnet creation has passed; no launch/trade funds were spent. Non-Pump legacy catalog swaps and bounty payout remain wallet-approved external financial flows.
- Dedicated production-grade Solana RPC configuration. Current public mainnet RPC is functional but rate-limited and unsuitable for sustained heavy traffic.
- Transaction lifecycle hardening: recovery for rejected/dropped/expired transactions, deeper adversarial on-chain validation, concurrency control around payout finalization, API anti-abuse limits.
- Formal security audit before public financial usage (not performed; no audit was requested).

### P1 — Complete market/launch ecosystem
- Optional direct official Pump SDK launch only with a verified supported metadata-publication pipeline and current pinned instruction compatibility. Never reintroduce independent SPL minting or alter Pump fee fields.
- Liquidity, bonding curve, graduation and creator fees remain Pump infrastructure, not an independently implemented NEXUS subsystem.
- Holder analytics/indexer integration. Current upstream does not provide holder totals; UI says Not available.
- Confirmed on-chain trade history/indexer; existing history covers world launches, bounties, community milestones.
- Multi-winner reward distribution and/or audited escrow. Current supported payout is one winner receiving the stated SOL reward.
- Creator claim mechanism for curated external tokens; these correctly have no NEXUS creator and cannot have bounties issued by arbitrary wallets.
- Backend pagination / large-world chunks for thousands of actual tokens beyond initial catalog. Current API caps world token queries at 1000 and dynamic city plotting should gain occupancy management for scale.

### P2 — World/community depth
- Token-specific custom 3D silhouettes, more landmarks, expanded navigable territories and persistent camera position.
- Shareable territory deep links and community invite/referral links.
- Moderation/reporting, notifications, bounty search and more filters.
- Optional wallet-adapter passthrough to eliminate separate Jupiter wallet connect step.

## Next suggested product enhancement

Shareable territory URLs with token/camera focus and a community invite would make each token's location easy to circulate.

## Pump.fun integration layer — 2026-10-02

### User request and explicit choice

Preserve the existing website, concept, map, buildings, territory system and visual direction. Add only the real Pump.fun integration layer. Pump.fun owns token launches and underlying trading infrastructure; NEXUS owns the visual/game/community layer. Do not create independent tokens, fake launches/trades, or a separate creator-fee system. Do not replace, redirect, recreate or modify Pump.fun creator fees.

Creator loop: Launch Token → Pump.fun → Token Appears in World → Building Created → Height Follows MC → Create Bounty. User loop: Explore → Building → Dashboard → Buy/Sell → Bounty. Use real token address/name/symbol/image/cap/price/volume/holders/activity where available, plus Pump.fun link, chart and community.

Explicit choice: **“Utamakan SDK/API resmi; jika tidak tersedia, gunakan halaman resmi Pump.fun lalu verifikasi token untuk memasukkannya ke dunia.”** No third-party transaction provider authorized.

### Delivered architecture

- Official SDK/IDL researched. Current Pump creation supports evolving Token-2022/mayhem/cashback/holder-reward/fee options; direct hosted metadata publication was not established as a supported public end-to-end API. Implemented the authorized official-page handoff, not a private frontend endpoint or third-party transaction service. Direct SDK transaction launch is not enabled.
- `/launch` retains prior style and building preview, replacing standalone mint form with official `https://pump.fun/create` link, mint + original creation signature fields, creator wallet, verification, existing district/color picker, then registration. Draft persists across visiting Pump.fun. Opening Pump.fun is not counted as a successful launch; no automatic callback is claimed.
- Removed frontend `createToken`, Keypair mint generation, initializeMint/mintTo/revoke mint instruction assembly. Retained independent SOL transfer solely for community bounty rewards, unrelated to creator fees.
- New authenticated `/api/pump/verify` and `/api/pump/import`, plus public `/api/pump/config`. Client cannot submit authoritative name/symbol/creator/verified fields. Import adds or claims one persistent token representation; an existing catalog location/district/color is preserved.
- Verification modules pin official `pump-fun/pump-public-docs` IDL commit `e0687ae9b7e064a0f54efc7297c65eecfbba3a8f`. Supports official create/create_v2 compatible prefixes with bounded Borsh readers. Checks confirmed successful transaction, exact program/discriminator/mint, create-user account equals authenticated signer, mint authority/curve/ATA/global/metadata-or-mayhem/event/program PDAs, successful runtime-attributed CreateEvent and matching fields, mint owner/initialized flag/decimals and Pump-owned curve.
- Runtime event stack ignores foreign nested Program data and failed invocation subtrees. Creator world ownership is original signed creation user; Pump's creator/fee destination is read-only and never changed, including supported fee-beneficiary variations.
- Metadata: allowlisted HTTPS/IPFS hosts, 256KiB streaming limit, timeout, no redirects. Unknown metadata URLs safely yield unavailable image/description; token identity remains on-chain name/symbol.
- Periodic world refresh is still request-driven/polled, no scheduler. Adds read-only batched curve/mint checks. Pump provenance is from the actual PDA owner/discriminator, never a `pump` suffix.
- Active native-SOL curves use real reserves + mint supply/decimals and sourced SOL/USD to display a clearly labeled reserve-derived price/cap. Graduated curves do not determine current market price; DEX data is used and obsolete curve quotes are cleared if no graduated market quote is available. MC still feeds the existing unmodified tower-height renderer.
- Recent observed USD curve quotes stored as snapshots for chart fallback; not reconstructed historical candles. Up to 7 days retained, max 1000 returned. Existing GeckoTerminal charts remain.
- Pump-proven tokens route to a new panel in the existing dashboard slot. Buy/Sell links open exact official `/coin/{mint}` page; UI explicitly tells user to select Buy/Sell there. No invented side deep-link or execution claim. Existing non-Pump catalog entries retain functioning Jupiter swaps.
- Pump token dashboard adds provenance, Pump link, source/method text, official chart/activity link and Trades tab. Activity endpoint decodes confirmed Pump TradeEvent logs from bounded last-eight curve transactions; explicitly not a comprehensive 24-hour feed or PumpSwap indexer.
- Holders remain `Not available` because existing public sources do not provide a reliable indexed total; never estimate/fabricate it. Graduated PumpSwap trades can be viewed on the official Pump token page; native bounded event decoding only covers Pump bonding-curve activity.
- Existing creator bounty, submission, community and presence authorization continue to use the verified creator wallet. No fee collection/claiming/sharing/redirection functions added.

### Preservation and verification evidence

- `git diff --exit-code -- frontend/src/world/ frontend/src/pages/World.jsx frontend/src/App.css backend/catalog.py` passed: these existing visual/map/territory files unchanged.
- World remained 16 original tokens and the same four territory coordinates; no test/public-example tokens retained.
- Successful **read-only real-mainnet creation verification**: mint `2mh3b9fhXhkjqNrUjNqSbR1czsy6sz4Xh3WJkKYvpump`, original creation signature `4T9picqmw7jgntdFJYFGvN3woMqCAcWVM7eF5Zv3bARYjhvCoVXQwyaUjB9DoZTWWPvsguUcQguLVDrC2iXiXB9A`, public creator `JNpVNLrY5b1wkHBx6grNmHge6Zi8K5uqAbZGFBxLSmv`. Token was not imported into the world and no wallet authority/private key was available or invented.
- `/app/test_reports/iteration_2.json`: 34/34 pytest tests passed, zero skipped/failed, frontend desktop/mobile validated. Tests cover auth, malformed/spoofed fields, wrong-wallet rejection on a real Pump creation, mismatched mint/signature, deprecated independent launch410, provenance, activity scope, previous community/bounty behavior. Legacy launch test expectation updated intentionally. Full positive wallet-authorized browser import not executed; no real-user wallet provided.
- Screenshots verified unchanged world, updated launch page with exact official URL, and FARTCOIN Pump panel/Buy-Sell external handoff. FARTCOIN's provenance is verified from actual program-owned graduated curve; other catalog tokens are not falsely labeled Pump.

### Next priorities

P0: creator-authorized browser verify→import validation with an actual owned Pump launch; dedicated RPC/anti-abuse/concurrency hardening before heavy public traffic. P1: reliable holder indexer, fuller confirmed trading history, safe additional metadata hosts if needed, optional supported official SDK metadata+launch. P2: shareable territory links. Do not build an independent mint, liquidity or creator-fee system.
