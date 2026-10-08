import secrets


def new_id() -> int:
    # Random, so two hosts never hand out the same id; below 2**53 so JavaScript keeps it exact.
    return secrets.randbelow(2**53 - 1) + 1
