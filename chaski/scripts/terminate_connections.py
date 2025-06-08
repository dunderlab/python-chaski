"""Utility script to terminate network connections on specified ports."""

import os
import subprocess
import sys
import signal
from typing import List, Optional, Union, Iterable, Iterator


def close_connections(port: int, mode: str = "ALL", sig: int = signal.SIGKILL) -> None:
    """Terminate processes connected to a specific port.

    Args:
        port: The port number to check for connections
        mode: Termination mode - "ALL", "LATEST", or "FIRST"
        sig: Signal to send to the processes (default: SIGKILL)
    """
    try:
        # Run the lsof command to get the PIDs of active connections on the specified port
        result: subprocess.CompletedProcess = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            stdout=subprocess.PIPE,
            text=True,
        )
        pids: List[str] = result.stdout.strip().splitlines()
        pids = sorted(pids)

        if mode == "ALL":
            if pids:
                # Close all active connections
                for pid in pids:
                    os.kill(int(pid), sig)
        elif mode == "LATEST" and pids:
            os.kill(int(pids[-1]), sig)
        elif mode == "FIRST" and pids:
            os.kill(int(pids[0]), sig)

    except Exception as e:
        print(
            f"An error occurred while trying to close connections on port {port}: {e}"
        )


def main(nodes: Optional[Iterable[int]] = None) -> None:
    """Terminate connections on the specified ports.

    Args:
        nodes: Iterable of port numbers to terminate connections on.
               If None, uses command line arguments or default range.
    """
    if nodes is None:
        try:
            port_range: str = sys.argv[1]
            START_PORT, END_PORT = map(int, port_range.split("-"))
            if START_PORT > END_PORT:
                raise ValueError(
                    "The start port must be less than or equal to the end port."
                )
            nodes = range(START_PORT, END_PORT + 1)

        except (IndexError, ValueError):
            nodes = range(65430, 65501)  # Default port range

    # Iterate over the range of ports and close active connections
    for port in nodes:
        close_connections(port)


if __name__ == "__main__":
    main()
