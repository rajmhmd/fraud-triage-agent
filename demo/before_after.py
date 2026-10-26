"""Run the SAME analyst question through v1 and v2, side by side — record this for the demo video.

    python -m demo.before_after
    python -m demo.before_after --card CARD-002
"""
import argparse
import time

from agent.app import build_agent

QUESTION = "Triage the PENDING_REVIEW transactions on {card}. Give a recommendation for each."


def run(version: str, card: str) -> None:
    banner = "BEFORE  (v1: no geo tool)" if version == "v1" else "AFTER   (v2: + Amazon Location Service travel check)"
    print("\n" + "=" * 78 + f"\n{banner}\n" + "=" * 78)
    start = time.time()
    agent = build_agent(version)
    result = agent(QUESTION.format(card=card))
    usage = result.metrics.accumulated_usage if hasattr(result, "metrics") else {}
    print(f"\n--- {version} done in {time.time() - start:.1f}s | tokens: {usage}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--card", default="CARD-001")
    a = p.parse_args()
    run("v1", a.card)
    run("v2", a.card)
