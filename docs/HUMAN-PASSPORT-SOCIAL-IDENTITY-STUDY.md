# Human Passport / HUMN study for ZirohNeth social identity

Status: research only. No integration is implemented by this document.

## Goal and product stance

Evaluate Human Passport (formerly Gitcoin Passport / Passport.xyz) as an optional signal for safer ZirohNeth social spaces. The goal is durable, user-controlled participation and resistance to automated Sybil abuse, not anonymous activism as a product requirement and not compulsory identity disclosure.

Keep three questions separate:

1. Account control: does the user control the cryptographic key for this ZirohNeth identity?
2. Uniqueness / Sybil resistance: is this likely one distinct participant rather than a farm of coordinated accounts?
3. Social trust: has this identity built relationships and a history that other users or communities choose to recognize?

A Passport score can only help with the second question. It must not become a substitute for account ownership, social reputation, moderation evidence or legal identity.

## Current Human Passport landscape

Human Passport is the current product name for the project previously known as Gitcoin Passport and Passport.xyz. Its current developer platform describes several distinct mechanisms:

- Stamps: user-selected credentials from web2, web3, social, professional, biometrics and other sources, aggregated into a score.
- Models API: scores EVM addresses using on-chain activity models, including an aggregate model and chain-specific models.
- Individual verifications: reusable zero-knowledge attestations for selected checks, intended to avoid repeatedly sharing underlying personal data.
- On-chain Passport: smart-contract-based access to score / Stamp data, where supported by the chosen integration.

This is not a magic proof that an account is a unique human. Scores are probabilistic signals, models can produce false positives and false negatives, Stamp weights can change, and API-based decisions introduce a service dependency.

Official references:
- Human Passport overview: https://docs.human.tech/passport
- Developer documentation: https://docs.passport.human.tech/
- Stamps: https://docs.passport.human.tech/building-with-passport/stamps/introduction
- Models API: https://docs.passport.human.tech/building-with-passport/models/introduction
- Models API reference: https://docs.passport.human.tech/building-with-passport/models/api-reference
- Passport XYZ original project: https://github.com/passportxyz/passport
- HUMN token context: https://passport.human.tech/blog/humn-is-coming-what-you-should-know

## Recommended integration shape

### 1. Optional trust signal, never a root identity

Keep the Ethereum (or legacy Bitcoin) signing key as the authority for the ZirohNeth site/account. Passport must not issue, replace or custody the user's ZirohNeth signing key.

A user may link a Passport credential to an address they control. Store only the minimum verification result needed by a feature, preferably a signed, expiring attestation or a reference to a verifiable proof. Do not copy raw stamps, government-ID data, biometric data, email addresses or social-account details into content.json, public profile files or replicated site databases.

### 2. Progressive trust, not a hard global gate

Use Passport as one optional signal in a layered anti-abuse system:

- Rate limits, proof-of-work / resource costs and abuse throttles for baseline access.
- Account age, signed history and consistency checks.
- Community-issued trust attestations and user-controlled web-of-trust edges.
- Optional Passport Stamps or Models checks for high-impact actions, such as mass invitations, high-volume posting, moderation elections or scarce community resources.
- Human review and appeal for disputed restrictions.

Do not require a Passport score to read public sites, create a basic identity, publish ordinary posts or participate in low-risk discussions. Avoid a single universal score threshold. Different actions have different abuse costs and should use different policies.

### 3. Decentralization requirements

Do not make api.passport.xyz, a single scorer, a single RPC endpoint or a single chain the permanent authority for social participation.

Preferred order of evaluation:

1. Verify portable, cryptographically signed credentials locally whenever the protocol supports it.
2. Evaluate on-chain Passport attestations with an explicit chain, contract, block and freshness policy.
3. Use Stamps / Models APIs as an optional convenience or fallback, not an availability-critical dependency.
4. Permit independent community scorers and local trust policies.
5. Preserve the ability to export, migrate and verify identity history without Passport.

Any API integration must specify caching, expiry, outage behavior, rate limits, data retention and how users can challenge a stale or incorrect result. An API response must not silently become a permanent ban.

### 4. Privacy and selective disclosure

- Ask only for the proof required by the action.
- Prefer zero-knowledge or selective-disclosure proofs over raw credentials.
- Avoid correlating multiple social identities unless the user explicitly opts in.
- Do not expose a public global human score by default.
- Do not leak Passport stamps or verification choices to peers.
- Make unlinking and revocation behavior explicit. A revoked credential must stop authorizing new actions after the documented freshness window.
- Treat biometrics, government identity and other highly sensitive stamps as optional and never required for ordinary social use.

### 5. Social graph and community governance

The most decentralizing value may come from portable, community-issued trust rather than a universal vendor score.

Explore:
- Signed endorsements from identities a user already trusts.
- Community-specific trust graphs instead of one global reputation number.
- Revocable, expiring attestations.
- Multiple independent issuers and scorers.
- Transparent policy documents and versioned moderation rules.
- Delegated moderation and appeal records that can be mirrored across peers.
- Sybil-resistant voting only for explicitly defined governance actions, with privacy-preserving eligibility proofs where feasible.

A social graph is not automatically decentralized merely because it is stored on a blockchain. Users must be able to choose issuers, leave communities, export their records and continue with a different verifier.

## Threat model and failure modes

| Threat / failure | Required response |
|---|---|
| Passport API outage | Existing accounts remain usable; defer only the high-risk action or use local policy |
| False negative / low score | Appeal and alternative verification; no automatic account deletion |
| False positive / Sybil farm | Combine signals, rate limits and community review |
| Stolen wallet | Key rotation / recovery procedure independent of Passport |
| Correlation across sites | Pairwise identifiers or selective disclosure; avoid global public scores |
| Scorer manipulation or policy change | Version scorer policy, timestamp results and allow independent scorers |
| Provider lock-in | Exportable credentials and local verification path |
| Chain / RPC reorg or outage | Explicit finality and freshness policy; fail safely without locking ordinary access |

## Suggested staged experiment

1. Research prototype: document exact Passport API / on-chain data formats, terms, data flows, cost and operational dependencies.
2. Opt-in linking: let a user link a Passport proof to a wallet without changing the ZirohNeth identity or publishing private stamp details.
3. Non-blocking signal: show a local trust indicator to the user; do not use it to deny ordinary access.
4. One narrow abuse case: test a configurable threshold only for a high-impact action, with an alternative route and appeal.
5. Decentralized alternative: implement community attestations and local trust policies, then compare effectiveness and portability.
6. Independent review: security, privacy, accessibility, false-positive and governance review before wider deployment.

## Open decisions

- Which exact Human Passport product and API version is appropriate for a new integration?
- Can required proofs be verified without a mandatory centralized API key?
- Which on-chain contracts, networks, block finality rules and upgrade controls would be trusted?
- How can a Passport proof be linked to a ZirohNeth identity without making wallet correlation public?
- What minimum signal is useful without excluding users who do not use EVM, social platforms, biometrics or KYC?
- Should ZirohNeth ship a built-in community trust protocol first and treat Passport as one issuer among many?

## Recommendation

Proceed only with an optional adapter behind a provider-neutral credential interface. Keep identity ownership, ordinary social access and moderation governance independent of Human Passport. Prioritize portable credentials, community trust and local verification over a centralized score gate. Treat $HUMN token incentives as separate from the security architecture: token ownership or staking must not be equated with personhood or social legitimacy.
