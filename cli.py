"""Command line interface. Every command takes positional arguments only.

    aegis run                 build the risk management file and write all outputs
    aegis summary             print headline numbers
    aegis trace NODE [forward|backward]
    aegis ask "QUESTION"
    aegis score S P D
    aegis evaluate            run the evaluation suite and print the report
    aegis figures             render the figures used in the documentation
    aegis serve               start the HTTP API
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from aegis_rmf.pipeline import export_outputs, run_evaluation, run_pipeline
from aegis_rmf.risk import load_policy, score
from aegis_rmf.settings import load_settings


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegis", description="Aegis RMF AI command line interface")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="Build the risk management file and write all outputs")
    commands.add_parser("summary", help="Print headline numbers")
    trace = commands.add_parser("trace", help="Trace a node through the knowledge graph")
    trace.add_argument("node_id")
    trace.add_argument("direction", nargs="?", default="forward", choices=["forward", "backward"])
    ask = commands.add_parser("ask", help="Ask a question over the risk management file")
    ask.add_argument("question")
    rate = commands.add_parser("score", help="Score severity, probability and detectability ratings")
    for name in ("severity", "probability", "detectability"):
        rate.add_argument(name, type=int)
    commands.add_parser("evaluate", help="Run the evaluation suite")
    commands.add_parser("figures", help="Render documentation figures")
    commands.add_parser("serve", help="Start the HTTP API")
    args = parser.parse_args(argv)

    if args.command == "score":
        _print(score(load_policy(load_settings().risk_policy_path), args.severity, args.probability, args.detectability).model_dump(mode="json"))
        return 0
    if args.command == "serve":
        import uvicorn

        uvicorn.run("aegis_rmf.api.main:app", host=os.environ.get("AEGIS_API_HOST", "0.0.0.0"),
                    port=int(os.environ.get("AEGIS_API_PORT", "8000")))
        return 0

    result = run_pipeline()
    if args.command == "run":
        paths = export_outputs(result)
        _print({"summary": result.summary(), "outputs": {name: str(path) for name, path in paths.items()}})
    elif args.command == "summary":
        _print(result.summary())
    elif args.command == "trace":
        if result.store.get_node(args.node_id) is None:
            print(f"Unknown node {args.node_id}", file=sys.stderr)
            return 1
        _print(result.store.trace(args.node_id, args.direction))
    elif args.command == "ask":
        answer = result.engine.answer(args.question)
        print(answer.answer)
        print("\nReferences: " + ", ".join(hit.ref_id for hit in answer.contexts))
    elif args.command == "evaluate":
        _print(run_evaluation(result))
    elif args.command == "figures":
        from aegis_rmf.reporting.figures import render_all

        _print({"figures": [str(path) for path in render_all(result, result.settings.home / "docs" / "images")]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
