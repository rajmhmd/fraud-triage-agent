# Giving a fraud-triage agent a sense of place: impossible-travel detection with Amazon Location Service

> Paste into Builder Center → Your project. Replace the `[...]` placeholders with your real run output before submitting.

## The agent I started with
A card-fraud triage assistant built with the **Strands Agents SDK** on **Amazon Bedrock (Amazon Nova Pro)**. A fraud-ops analyst asks "triage the pending transactions on CARD-001" and the agent pulls the card profile (masked PAN, home city, travel notice) and recent transactions, then recommends APPROVE, STEP_UP or BLOCK_AND_REISSUE for each one.

It was good at the obvious signals: high amount, a risky MCC like jewellery or watches, an online versus chip transaction. But it had a blind spot every fraud analyst would spot in seconds. To the agent, "Dubai Mall" and "Oxford Street, London" were just two strings.

## The gap
Card-present fraud from skimmed or cloned cards often shows up as **impossible travel**: the genuine cardholder buys coffee in Dubai, and 75 minutes later the same card is tapped for a £4,890 watch in London. No one flies 5,500 km in 75 minutes.

Before: [To triage the PENDING_REVIEW transactions on CARD-001, I need to first get the card profile to understand the cardholder's home city and any travel notices. Then, I need to retrieve the recent transactions to review the PENDING_REVIEW transactions. Based on the card profile and transaction details, I can make a recommendation for each transaction.].

## The one tool I added: `check_travel_feasibility`
- **Amazon Location Service (Places API v2, `Geocode`)** resolves each merchant address to coordinates and a time zone, with IAM auth and `IntendedUse=SingleUse`.
- A **deterministic geo-velocity engine** computes great-circle distance, elapsed time and implied speed, and returns `FEASIBLE_SAME_AREA`, `FEASIBLE_BY_GROUND`, `FEASIBLE_BY_AIR` or `IMPOSSIBLE`.
- The **LLM decides which pairs to check and explains the result**; it never calculates the verdict. That split is the important design choice: a fraud decision has to be reproducible for an analyst, a cardholder dispute and an auditor.

Why this tool: geography is the one fraud signal a language model genuinely cannot see in text, and it's the signal that separates "big purchase" from "this card has been cloned".

## After
[| txn_id | recommendation | key evidence |
| --- | --- | --- |
| TXN-1002 | BLOCK_AND_REISSUE | IMPOSSIBLE travel (5478 km in 1.25 h implies ~4382 km/h; even a direct flight needs >= 7.9 h) |
| TXN-1003 | APPROVE | FEASIBLE_BY_GROUND travel (108 km in 2.92 h is achievable by road (<= 120 km/h)) |
| TXN-1004 | STEP_UP | ECOM transaction, recommend additional verification |
--- v2 done in 14.7s | tokens: {'inputTokens': 7042, 'outputTokens': 664, 'totalTokens': 7706}]. In my run the agent:
- **Blocked TXN-1002 (London):** ≈5,478 km in 1.25 h ≈ 4,382 km/h, and even a direct flight needs ≈7.9 h.
- **Approved TXN-1003 (Abu Dhabi):** it compared against the last *trusted* card-present transaction (Dubai Mall), not the fraudulent London one — ≈108 km in 2.9 h by road.
- **Skipped TXN-1004 (online):** a merchant's registered address says nothing about where the cardholder is.
- On **CARD-002**, Cairo → Dubai in 6.5 h came back `FEASIBLE_BY_AIR`, and the travel notice turned a likely false positive into an approval.

## How it plugs into Strands (reusable pattern)
```python
@tool
def check_travel_feasibility(from_location: str, from_timestamp_utc: str,
                             to_location: str, to_timestamp_utc: str) -> dict:
    """Check whether one cardholder could physically be at two places at two times..."""
    origin, dest = geocoder.geocode(from_location), geocoder.geocode(to_location)
    return {"status": "success", "content": [{"json": assess(origin, from_timestamp_utc,
                                                                dest, to_timestamp_utc).to_dict()}]}

agent = Agent(model=build_model(), tools=[get_card_profile, get_recent_transactions,
                                                      check_travel_feasibility])
```
The docstring tells the model when *not* to use the tool (online transactions), and the system prompt maps each verdict to an action. Drop the tool into any Strands agent that deals with logistics, field service or delivery ETAs.

## Built responsibly
- Least-privilege IAM: `bedrock:InvokeModel*` on the approved model and `geo-places:Geocode` only.
- Model-agnostic: the same tools run on any Strands model provider via one `.env` setting.
- Only merchant addresses leave the boundary; no PAN or cardholder PII goes to the geocoder. The agent only ever sees masked PANs.
- 11 unit tests cover the engine, including order-independence, same-timestamp edge cases and Location Service response parsing.
- A short ADR with a STRIDE table for the new tool surface is in the repo.

## AWS services
Amazon Bedrock (Amazon Nova Pro) · Amazon Location Service (Places API v2) · AWS IAM · Strands Agents SDK

**Repo:** [[github.com/rajmhmd/fraud-triage-agent](https://github.com/rajmhmd/fraud-triage-agent)] · **Demo (< 3 min):** [[link](https://youtu.be/r6BbSt4tGrM)]


