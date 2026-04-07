"""Utility functions for generating per-instance random flags."""

import secrets
import string


def generate_flags(prefixes):
    """Generate a random flag for each prefix.

    Each flag has the format ``PREFIX{<18 random alphanumeric chars>}``.

    Args:
        prefixes: List of flag prefix strings (e.g. ``["NBL01", "NBL02"]``).

    Returns:
        Dictionary mapping each prefix to its generated flag string.
    """
    alphabet = string.ascii_letters + string.digits
    return {
        prefix: (
            f"{prefix}"
            f"{{{''.join(secrets.choice(alphabet) for _ in range(18))}}}"
        )
        for prefix in prefixes
    }
