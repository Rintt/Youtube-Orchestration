import sys


def info(message: str):
    print(f"[INFO] {message}", file=sys.stderr)


def success(message: str):
    print(f"[SUCCESS] {message}", file=sys.stderr)


def warning(message: str):
    print(f"[WARNING] {message}", file=sys.stderr)


def error(message: str):
    print(f"[ERROR] {message}", file=sys.stderr)