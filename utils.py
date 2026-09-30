import hashlib
import hmac
import os

PBKDF2_ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 8


def hash_password(password):
    """Солёный PBKDF2-SHA256 хеш в формате pbkdf2_sha256$iterations$salt_hex$digest_hex."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def is_legacy_hash(stored_hash):
    """True, если хеш в старом формате (несолёный SHA-256, 64 hex-символа)."""
    return bool(stored_hash) and "$" not in stored_hash


def verify_password(password, stored_hash):
    """Проверка пароля с constant-time сравнением; поддерживает legacy SHA-256."""
    if not stored_hash:
        return False

    if is_legacy_hash(stored_hash):
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored_hash)

    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def validate_password_strength(password):
    """Возвращает текст ошибки или None, если пароль допустим."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Пароль должен содержать минимум {MIN_PASSWORD_LENGTH} символов"
    return None
