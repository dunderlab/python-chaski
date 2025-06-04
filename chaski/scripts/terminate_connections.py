import os
import subprocess
import sys


def close_connections(port):
    """"""

    try:
        # Run the lsof command to get the PIDs of active connections on the specified port
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            stdout=subprocess.PIPE,
            text=True,
        )
        pids = result.stdout.strip().splitlines()

        if pids:
            # Close all active connections
            for pid in pids:
                os.kill(int(pid), 9)

    except Exception as e:
        print(
            f"An error occurred while trying to close connections on port {port}: {e}"
        )


def main(nodes=None):

    if nodes is None:
        try:
            port_range = sys.argv[1]
            START_PORT, END_PORT = map(int, port_range.split("-"))
            if START_PORT > END_PORT:
                raise ValueError(
                    "The start port must be less than or equal to the end port."
                )
            nodes = range(START_PORT, END_PORT + 1)

        except:
            nodes = range(65440, 65500 + 1)

    # Iterate over the range of ports and close active connections
    for port in nodes:
        close_connections(port)


if __name__ == "__main__":
    main()
