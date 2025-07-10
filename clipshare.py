import argparse
import socket
import subprocess
import sys
import threading
import time


def get_clipboard() -> str:
    """Return current clipboard contents."""
    if sys.platform.startswith("linux"):
        try:
            result = subprocess.run([
                "wl-paste",
                "-n",
            ], capture_output=True, text=True, check=True)
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
    elif sys.platform.startswith("win"):
        try:
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
    else:
        raise NotImplementedError("Unsupported platform")


def set_clipboard(text: str) -> None:
    """Set clipboard contents to text."""
    if sys.platform.startswith("linux"):
        try:
            subprocess.run([
                "wl-copy",
            ], input=text, text=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    elif sys.platform.startswith("win"):
        try:
            subprocess.run(
                ["powershell", "-command", "Set-Clipboard"],
                input=text,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    else:
        raise NotImplementedError("Unsupported platform")


def send_clipboard(host: str, port: int, text: str) -> None:
    """Send clipboard text to remote host."""
    data = text.encode("utf-8")
    length = len(data).to_bytes(4, "big")
    with socket.create_connection((host, port)) as sock:
        sock.sendall(length)
        sock.sendall(data)


def server_thread(port: int) -> None:
    """Listen for clipboard updates on the given port."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port))
    srv.listen()
    print(f"Listening for clipboard updates on port {port}.")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


def handle_client(conn: socket.socket, addr) -> None:
    """Receive clipboard data from a connection."""
    with conn:
        header = conn.recv(4)
        if not header:
            return
        size = int.from_bytes(header, "big")
        data = b""
        while len(data) < size:
            packet = conn.recv(size - len(data))
            if not packet:
                break
            data += packet
        text = data.decode("utf-8", errors="replace")
        set_clipboard(text)
        print(f"Received clipboard update from {addr} ({len(text)} bytes)")


def monitor_clipboard(host: str, port: int, interval: float = 1.0) -> None:
    """Monitor clipboard and send updates to host."""
    current = get_clipboard()
    while True:
        time.sleep(interval)
        new = get_clipboard()
        if new != current:
            send_clipboard(host, port, new)
            print(f"Sent clipboard update to {host}:{port} ({len(new)} bytes)")
            current = new


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Share clipboard contents over the network")
    parser.add_argument("--listen", type=int, metavar="PORT", help="Port to listen for incoming updates")
    parser.add_argument("--peer", metavar="HOST:PORT", help="Send clipboard changes to this peer")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds")
    args = parser.parse_args()

    if args.listen is None and args.peer is None:
        parser.error("must specify --listen and/or --peer")

    if args.listen is not None:
        threading.Thread(target=server_thread, args=(args.listen,), daemon=True).start()

    if args.peer:
        host, sep, p = args.peer.rpartition(":")
        if not sep:
            parser.error("--peer must be in HOST:PORT format")
        monitor_clipboard(host, int(p), args.interval)
    else:
        # If only listening, keep the main thread alive.
        while True:
            time.sleep(1)

