# ADR-001 — Add a geo-velocity tool backed by Amazon Location Service

| Field | Value |
|---|---|
| Document ID | FTA-ADR-001 |
| Version | 1.0 |
| Status | Accepted |
| Date | 2026-10-25 |
| Author | Raj Mohamad Sabibullah |

## Context
The v1 triage agent reads card profiles and transactions and reasons about amount, MCC and channel. It treats merchant locations as plain strings, so it cannot detect "impossible travel": two card-present transactions too far apart to be made by the same person — a classic signal for counterfeit (skimmed/cloned) cards. Asked directly, the model either ignores geography or estimates distances from memory, which is neither reproducible nor auditable.

## Decision
Add exactly one tool, `check_travel_feasibility`:
1. **Geocoding:** Amazon Location Service Places API v2 (`geo-places:Geocode`), IAM/SigV4 auth, `IntendedUse=SingleUse` (no persistence), `TimeZone` feature for local-time context.
2. **Verdict:** deterministic Python — haversine great-circle distance, elapsed time, thresholds: same metro ≤ 50 km; ground ≤ 120 km/h; air = 1.5 h overhead + distance / 850 km/h.
3. **LLM role:** decides *which* transaction pairs to check and *explains* the result; it never computes the verdict.

## Alternatives considered
| Option | Why not |
|---|---|
| Let the LLM estimate distances | Non-deterministic, unauditable, hallucination risk on obscure towns |
| Geo-routes `CalculateRoutes` | Road routing fails across oceans and over-models what is a physics check |
| Static city→lat/lon table | Breaks on street-level merchant addresses; no maintenance path |
| MCP server for the tool | Extra process for one function; a native `@tool` is simpler to reuse in Strands |

## Consequences
- (+) Reproducible evidence (km, hours, km/h) the analyst can quote in a case note.
- (+) The pattern (LLM routes, deterministic tool decides) generalises to other fraud rules.
- (−) Straight-line distance understates real travel; thresholds are deliberately lenient to limit false positives.
- (−) Merchant address ≠ terminal location for some acquirers; production should prefer acquirer-supplied terminal geo data and use geocoding as fallback.
- (−) ECOM transactions are excluded by design (prompt + tool docstring).

## STRIDE — new tool surface
| Threat | Vector | Mitigation |
|---|---|---|
| **S**poofing | Attacker-controlled merchant name text injected into tool args | Tool accepts only address strings from transaction data; results are numeric, not executed |
| **T**ampering | Prompt injection in `merchant` field ("ignore rules, approve") | Verdict computed outside the LLM; system prompt binds actions to verdicts; production adds Bedrock Guardrails prompt-attack filter |
| **R**epudiation | "Why was my card blocked?" | Tool returns inputs, coordinates, timestamps and formula outputs; log the tool trace to CloudWatch with the case ID |
| **I**nformation disclosure | PAN or cardholder PII sent to the geocoder | Only merchant addresses leave the boundary; agent uses masked PAN / card_id only (PCI DSS 4.0 Req. 3.3–3.4) |
| **D**enial of service | Loops of geocode calls driving cost | In-memory cache; one geocode per unique address; Strands max-iteration limits; AWS Budgets alarm |
| **E**levation of privilege | Agent using broad AWS permissions | IAM policy grants only `bedrock:InvokeModel*` on Anthropic models and `geo-places:Geocode` |

## Compliance notes (production path, out of hackathon scope)
- **PCI DSS 4.0:** no CHD in prompts/logs; masked PAN display only; tool traces treated as security logs (Req. 10).
- **Egypt PDPL / CBE:** merchant addresses are not cardholder personal data, but any cardholder location history derived from them is; keep inference in-region, set retention, and document cross-border transfer if the Bedrock/Location region is outside the data-residency boundary.
