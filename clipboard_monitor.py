import subprocess
import time
import sys


def get_clipboard():
    """Return the current clipboard contents as a string."""
    try:
        result = subprocess.run(
            ["wl-paste", "-n"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def main(poll_interval: float = 1.0) -> None:
    """Monitor the clipboard and print a message whenever it changes."""
    current = get_clipboard()
    print("Initial clipboard:", repr(current))
    try:
        while True:
            time.sleep(poll_interval)
            new = get_clipboard()
            if new != current:
                print("Clipboard changed:")
                print(repr(new))
                current = new
    except KeyboardInterrupt:
        print("\nExiting")
        sys.exit(0)


if __name__ == "__main__":
    main()
