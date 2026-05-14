# src/hivemind/client/cli.py
import argparse
import sys
import asyncio

# === WINDOWS FIX – must be set VERY early ===
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ============================================

from hivemind.client.run_node import run_node

def main():
    parser = argparse.ArgumentParser(
        prog="hivemind",
        description="HiveMind Shared Compute — P2P distributed supercomputer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-node subcommand
    run_parser = subparsers.add_parser(
        "run-node",
        help="Start a HiveMind contributor node on the tailnet"
    )
    run_parser.add_argument("--node-id", required=True, help="Unique node identifier")
    run_parser.add_argument(
        "--control-port",
        type=int,
        default=4242,
        help="Control port for discovery/heartbeats (default 4242)"
    )

    args = parser.parse_args()

    if args.command == "run-node":
        asyncio.run(run_node(args.node_id, args.control_port))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()