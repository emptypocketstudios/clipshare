# clipshare

## Clipboard Monitor

The `clipboard_monitor.py` script watches the Wayland clipboard using the `wl-paste` command from `wl-clipboard`. It prints a message whenever the clipboard text changes.

Run it with Python 3 while in a Wayland session and ensure `wl-paste` is installed:

```bash
python3 clipboard_monitor.py
```

## Sharing the clipboard

The `clipshare.py` script synchronizes clipboard text between two peers. Each
instance can listen for updates and optionally send changes to a remote peer.

On each machine run something like:

```bash
python3 clipshare.py --listen 9000 --peer OTHER_HOST:9000
```

Replace `OTHER_HOST` with the peer's IP address or hostname. The `wl-copy` and
`wl-paste` commands (from `wl-clipboard`) must be available on Wayland systems,
while Windows uses PowerShell.

By default the clipboard is polled every second; use `--interval` to change
this.
