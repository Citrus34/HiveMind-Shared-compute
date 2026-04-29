
import asyncio
import argparse
import signal
import sys
from hivemind.network.discovery import HiveMindDiscovery
from hivemind.network.transport import HiveMindControlListener

async def run_node(node_id: str):
    """Main HiveMind node entrypoint – discovery + control listener."""
    print(f"[HiveMind] Starting node '{node_id}' on Tailnet...")

    # 1. Start control listener (advertises resources)
    listener = HiveMindControlListener(node_id)
    listener_task = asyncio.create_task(listener.handle_handshake())

    # 2. Start discovery engine
    discovery = HiveMindDiscovery(node_id)

    async def periodic_discovery():
        while True:
            peers = await discovery.discover_peers()
            print(f"[Discovery] Found {len(peers)} active HiveMind peers")
            await asyncio.sleep(15)  # tune as needed

    discovery_task = asyncio.create_task(periodic_discovery())

    # 3. Graceful shutdown
    shutdown_event = asyncio.Event()

    def shutdown():
        print("\n[HiveMind] Shutting down gracefully...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Cleanup
    listener_task.cancel()
    discovery_task.cancel()
    await listener.stop()
    print("[HiveMind] Node stopped cleanly.")

def main():
    parser = argparse.ArgumentParser(description="HiveMind Shared Compute Node")
    parser.add_argument("--node-id", required=True, help="Unique node identifier (e.g. macbook-pro)")
    args = parser.parse_args()

    try:
        asyncio.run(run_node(args.node_id))
    except KeyboardInterrupt:
        print("\n[HiveMind] Interrupted by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()