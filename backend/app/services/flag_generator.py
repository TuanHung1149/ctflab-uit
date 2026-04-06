"""Generate unique, cryptographically random flags for CTF challenges."""

import secrets
import string

_ALPHABET = string.ascii_letters + string.digits
_FLAG_LENGTH = 18


def generate_flags(prefixes: list[str]) -> dict[str, str]:
    """Generate random flags for each prefix.

    Args:
        prefixes: List of flag prefixes, e.g. ["NBL01", "NBL02"].

    Returns:
        Mapping of prefix to full flag string.
        Example: {"NBL01": "NBL01{a8Kd9mPq2Lx5Rn7W}"}
    """
    return {
        prefix: f"{prefix}{{{_random_token()}}}"
        for prefix in prefixes
    }


def _random_token(length: int = _FLAG_LENGTH) -> str:
    """Return a cryptographically random alphanumeric string."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
