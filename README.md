# Card Fraud Triage Agent — "Give your Agent a Tool"

**AWS Builder Center Weekend Challenge** · closes **Mon 26 Oct 2026, 1:00 PM PDT** (= **Tue 27 Oct, 00:00 Dubai**).

A Strands Agents + Amazon Bedrock agent that triages pending card transactions for a fraud-ops analyst. **v1** could read card profiles and transactions. **v2 adds one tool** — `check_travel_feasibility`, backed by **Amazon Location Service** — so the agent can now catch *impossible travel*: a card used in Dubai and, 75 minutes later, tapped in London.

```
analyst ──► Strands Agent (Claude on Amazon Bedrock)
              ├─ get_card_profile            (v1)
              ├─ get_recent_transactions     (v1)
              └─ check_travel_feasibility    (v2, NEW) ──► Amazon Location Service geo-places:Geocode
                                                       └─► deterministic geo-velocity engine (km, h, km/h → verdict)
```

## Project layout
```
fraud-triage-agent/
├── agent/
│   ├── config.py          # env-driven config + tiny .env loader
│   ├── tools_base.py      # v1 tools (card profile, transactions)
│   ├── geo_velocity.py    # NEW: haversine + verdict engine + Location Service geocoder
│   ├── tools_geo.py       # NEW: the @tool wrapper the agent calls
│   └── app.py             # build_agent("v1"|"v2"), CLI
├── demo/
│   ├── check_location.py  # tests the new tool against AWS without Bedrock
│   └── before_after.py    # same question → v1 then v2 (record this)
├── data/transactions.json # synthetic, masked-PAN demo data
├── infra/iam-policy.json  # least-privilege policy
├── infra/setup.sh         # creates IAM user + policy
├── tests/test_geo_velocity.py
├── docs/ADR-001-geo-velocity-tool.md   # decision record + STRIDE
├── SUBMISSION.md          # paste-ready write-up
└── VIDEO_SCRIPT.md        # < 3 min demo script
```

---

## Step-by-step

### Step 0 — Prerequisites (10 min)
- Python **3.10+**, AWS CLI v2, an AWS account you can create IAM resources in.
- Builder Center profile, and click **Join** on the challenge page. Read the **Rules** tab (country/employee exclusions).

### Step 1 — Python environment
```bash
cd fraud-triage-agent
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v                 # 11 tests, no AWS needed
```

### Step 2 — Bedrock model access
1. Console → **Amazon Bedrock** → region **us-east-1** → **Model catalog**.
2. Open **Claude Sonnet 4** (or the newest Claude Sonnet listed). If it asks for Anthropic use-case details, submit them; access is usually immediate.
3. Note the **inference profile ID** (starts with `us.anthropic.`) and put it in `.env` as `BEDROCK_MODEL_ID`.

Quick check:
```bash
aws bedrock list-inference-profiles --region us-east-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId,'anthropic')].inferenceProfileId"
```

### Step 3 — IAM (least privilege)
```bash
chmod +x infra/setup.sh
AWS_PROFILE=<your-admin-profile> ./infra/setup.sh
aws iam create-access-key --user-name fraud-triage-agent-dev
aws configure --profile hackathon        # paste key, region us-east-1
```
The policy (`infra/iam-policy.json`) allows only `bedrock:InvokeModel*` on Anthropic models and `geo-places:Geocode`. No Location resources (maps/place indexes/API keys) need to be created — the v2 Places API works with IAM auth directly.

### Step 4 — Configure
```bash
cp .env.example .env     # set AWS_PROFILE=hackathon and BEDROCK_MODEL_ID
```

### Step 5 — Prove the new tool works (no LLM)
```bash
python -m demo.check_location
```
Expected verdicts: Dubai→London in 75 min `IMPOSSIBLE`; Dubai→Abu Dhabi in ~3 h `FEASIBLE_BY_GROUND`; Cairo→Dubai in 6.5 h `FEASIBLE_BY_AIR`.
`AccessDeniedException` → recheck Step 3 and the region in the policy ARN.

### Step 6 — Run the BEFORE agent
```bash
python -m agent.app --version v1 "Triage the PENDING_REVIEW transactions on CARD-001"
```
Typical v1 behaviour: flags the £4,890 watch purchase on *amount and MCC* only, and either misses the geography or guesses at it without evidence. It may also treat the Abu Dhabi fuel purchase as suspicious or approve it with no reasoning.

### Step 7 — Run the AFTER agent
```bash
python -m agent.app --version v2 "Triage the PENDING_REVIEW transactions on CARD-001"
```
v2 calls `check_travel_feasibility` for the card-present pairs and should:
- **TXN-1002 London → BLOCK_AND_REISSUE** (≈5,476 km in 1.25 h ≈ 4,381 km/h — counterfeit card pattern)
- **TXN-1003 Abu Dhabi → APPROVE** (compared with the trusted Dubai Mall txn, not the London one: ≈124 km in 2.9 h by road)
- **TXN-1004 ECOM → skipped** for travel, with the reason stated.

Second scenario (travel notice turns a would-be false positive into an approval):
```bash
python -m agent.app --version v2 "Triage the PENDING_REVIEW transactions on CARD-002"
```

### Step 8 — Record the demo
```bash
python -m demo.before_after            # v1 then v2, same question, same data
```
Follow `VIDEO_SCRIPT.md`; keep it under 3 minutes; upload as **Public** or **Unlisted-but-public-link** to YouTube.

### Step 9 — Publish code and submit
```bash
git init && git add . && git commit -m "Fraud triage agent + Amazon Location travel-feasibility tool"
gh repo create fraud-triage-agent --public --source=. --push
```
On the challenge page → **Your project** → paste `SUBMISSION.md`, put the video URL in **demo**, add the repo link. Submit before **Mon 1:00 PM PDT**.

### Step 10 — Clean up
```bash
aws iam delete-access-key --user-name fraud-triage-agent-dev --access-key-id <id>
```
Cost for the whole weekend should be cents to low single-digit dollars (a few hundred Bedrock calls + geocodes).

---

## Reusing the pattern in your own Strands agent
```python
from strands import Agent
from agent.tools_geo import check_travel_feasibility
agent = Agent(tools=[check_travel_feasibility, *your_tools])
```
The rule: **the LLM chooses when to call and explains; the tool computes the verdict deterministically.**

## Troubleshooting
| Symptom | Fix |
|---|---|
| `AccessDeniedException` on Bedrock | Model access not granted in that region, or wrong `BEDROCK_MODEL_ID` |
| `ValidationException ... on-demand throughput isn't supported` | Use the `us.` inference profile ID, not the bare model ID |
| `UnknownServiceError: geo-places` | Upgrade boto3: `pip install -U boto3` |
| `AccessDeniedException` on geocode | Policy ARN region must match `LOCATION_REGION` |
| Agent never calls the new tool | You ran `--version v1`, or the prompt didn't mention pending transactions |
