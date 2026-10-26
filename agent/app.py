"""Build and run the Card Fraud Triage Agent.

    python -m agent.app --version v1 "Triage the pending transactions on CARD-001"
    python -m agent.app --version v2 "Triage the pending transactions on CARD-001"
    python -m agent.app --version v2            # interactive chat
"""
import argparse

from strands import Agent
from strands.models import BedrockModel

from . import config
from .tools_base import BASE_TOOLS
from .tools_geo import GEO_TOOLS

BASE_PROMPT = """You are a card fraud triage assistant for a bank's fraud operations team.
Given a card, review its PENDING_REVIEW transactions and recommend one action each:
APPROVE, STEP_UP (contact cardholder / 3DS / OTP), or BLOCK_AND_REISSUE.

Rules:
- Only ever refer to cards by card_id or masked PAN. Never ask for or output a full PAN, CVV or PIN.
- Base every claim on tool output. If you lack evidence, say so instead of guessing.
- Consider the card profile (home city, travel notice), amount, MCC and channel.
- Finish with a table: txn_id | recommendation | key evidence."""

GEO_ADDENDUM = """

You also have check_travel_feasibility (Amazon Location Service).
- For each pending CARD-PRESENT transaction, compare it with the most recent earlier
  card-present transaction you still trust (not one you are recommending to block).
- Skip ECOM transactions for travel checks; say why.
- IMPOSSIBLE -> BLOCK_AND_REISSUE (likely counterfeit/cloned card or compromised credentials).
- FEASIBLE_BY_AIR -> APPROVE only if a matching travel notice exists, otherwise STEP_UP.
- Quote distance_km, elapsed_hours and implied_speed_kmh as evidence."""


def build_agent(version: str = "v2") -> Agent:
    model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
        temperature=config.BEDROCK_TEMPERATURE,
    )
    if version == "v1":
        return Agent(model=model, tools=BASE_TOOLS, system_prompt=BASE_PROMPT)
    return Agent(model=model, tools=BASE_TOOLS + GEO_TOOLS, system_prompt=BASE_PROMPT + GEO_ADDENDUM)


def main() -> None:
    parser = argparse.ArgumentParser(description="Card Fraud Triage Agent")
    parser.add_argument("--version", choices=["v1", "v2"], default="v2")
    parser.add_argument("prompt", nargs="?", help="One-shot prompt; omit for interactive mode")
    args = parser.parse_args()

    agent = build_agent(args.version)
    if args.prompt:
        agent(args.prompt)  # Strands streams the answer to stdout by default
        print()
        return
    print(f"Fraud triage agent {args.version} — type 'exit' to quit")
    while True:
        q = input("\nanalyst> ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        if q:
            agent(q)
            print()


if __name__ == "__main__":
    main()
