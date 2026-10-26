# Demo video script — target 2:40, hard limit < 3:00

Record terminal + face-cam or voice-over (OBS / QuickTime / Loom). Terminal font ≥ 18 pt.
Pre-run both versions once so Bedrock is warm; trim waiting time in the edit.

| Time | Screen | Say (paraphrase in your own voice) |
|---|---|---|
| 0:00–0:15 | Title slide / README diagram | "I'm Raj, a payments architect. This is a card-fraud triage agent on Strands and Amazon Bedrock. This weekend I gave it one tool: a sense of place." |
| 0:15–0:35 | `data/transactions.json` — highlight TXN-1001 Dubai 04:10 UTC and TXN-1002 London 05:25 UTC | "Same card. Coffee in Dubai, then a £4,890 watch in London 75 minutes later. Any analyst sees it instantly. Can the agent?" |
| 0:35–1:05 | `python -m agent.app --version v1 "Triage the PENDING_REVIEW transactions on CARD-001"` | "Version one: it flags the watch on amount and category, but it has no evidence about geography. It can't tell Dubai from London as places." Point at the weak reasoning. |
| 1:05–1:25 | `agent/tools_geo.py` docstring + `geo_velocity.assess` | "The new tool geocodes both merchants with Amazon Location Service, then a deterministic engine computes distance, time and speed. The model decides when to call it and explains; it never computes the verdict." |
| 1:25–2:10 | `python -m agent.app --version v2 ...` — pause on the tool call and the table | "Now: 5,476 km in 1.25 hours, about 4,400 km/h. Block and reissue. And notice the Abu Dhabi fuel stop: it compared against the trusted Dubai transaction, not the cloned one, so it approves. The online purchase is skipped, correctly." |
| 2:10–2:30 | `--version v2` on CARD-002 | "The flip side: Cairo to Dubai in six and a half hours is feasible by air, and there's a travel notice, so no false positive." |
| 2:30–2:45 | `iam-policy.json` + test run | "Least-privilege IAM, no card data sent to the geocoder, 11 unit tests. The pattern drops into any Strands agent. Repo link is below." |

Upload checklist: public visibility · title "Give your Agent a Tool — impossible-travel detection with Amazon Location Service" · repo link in the description.
