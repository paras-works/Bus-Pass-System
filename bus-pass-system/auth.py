import hashlib
import hmac
import secrets

# ---------------------------------------------------------------
# PASSWORD HASHING (PBKDF2 - part of Python's standard library,
# no extra package needed)
# ---------------------------------------------------------------
_HASH_ALGORITHM = "sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(plain_password):
    """
    Returns a single string that contains BOTH the salt and the hash,
    separated by '$', e.g.  "a1b2c3...$9f8e7d...".
    Storing them together means we don't need an extra database
    column just for the salt.
    """
    salt = secrets.token_hex(_SALT_BYTES)
    hashed = hashlib.pbkdf2_hmac(
        _HASH_ALGORITHM,
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    ).hex()
    return f"{salt}${hashed}"


def verify_password(plain_password, stored_hash):
    """Recompute the hash using the SAME salt and compare safely."""
    try:
        salt, hashed = stored_hash.split("$")
    except ValueError:
        return False

    new_hash = hashlib.pbkdf2_hmac(
        _HASH_ALGORITHM,
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    ).hex()

    # hmac.compare_digest avoids leaking timing information that could
    # theoretically help an attacker guess the password character by character.
    return hmac.compare_digest(new_hash, hashed)


# ---------------------------------------------------------------
# SIMPLE VALIDATION HELPERS (used by app.py)
# ---------------------------------------------------------------
def is_valid_email(email):
    return bool(email) and "@" in email and "." in email.split("@")[-1]


def is_valid_password(password):
    return bool(password) and len(password) >= 6
