# src/hivemind/client/run_node.py
import asyncio
import argparse
import sys

from hivemind.network.discovery import HiveMindDiscovery
from hivemind.network.transport import HiveMindControlListener

async def run_node(node_id: str, control_port: int = 4242):
    """Main HiveMind node entrypoint."""
    print(f"[HiveMind] Starting node '{node_id}' on Tailnet (port {control_port})...")

    # 1. Start control listener
    listener = HiveMindControlListener(node_id, control_port)
    listener_task = asyncio.create_task(listener.handle_handshake())

    # 2. Start discovery engine
    discovery = HiveMindDiscovery(node_id, control_port)

    async def periodic_discovery():
        while True:
            peers = await discovery.discover_and_heartbeat()
            print(f"[Discovery] Found {len(peers)} active HiveMind peers")
            await asyncio.sleep(15)

    discovery_task = asyncio.create_task(periodic_discovery())

    print("[HiveMind] Node running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass

    print("\n[HiveMind] Shutting down gracefully...")
    listener_task.cancel()
    discovery_task.cancel()
    await listener.stop()
    print("[HiveMind] Node stopped cleanly.")

def main():
    # Fallback for direct python -m calls
    parser = argparse.ArgumentParser(description="HiveMind Shared Compute Node")
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--control-port", type=int, default=4242)
    args = parser.parse_args()
    asyncio.run(run_node(args.node_id, args.control_port))

if __name__ == "__main__":
    main()