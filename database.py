import hashlib
import json
import sqlite3

from utils import (
    hash_password,
    is_legacy_hash,
    validate_password_strength,
    verify_password,
)

DB_NAME = "database.db"
DB_TIMEOUT_SECONDS = 10

# Legacy SHA-256 С…РµС€Рё РІСЃС‚СЂРѕРµРЅРЅС‹С… СѓС‡С‘С‚РЅС‹С… Р·Р°РїРёСЃРµР№ вЂ” РґР»СЏ РїРѕРјРµС‚РєРё must_change_password
# РІ СѓР¶Рµ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… Р‘Р”, СЃРѕР·РґР°РЅРЅС‹С… РґРѕ РІРІРµРґРµРЅРёСЏ С„Р»Р°РіР°.
LEGACY_DEFAULT_HASHES = {
    "admin": hashlib.sha256(b"password").hexdigest(),
    "operator": hashlib.sha256(b"operator").hexdigest(),
}

PERMISSION_LABELS = {
    "live_view": "Live View",
    "events_tab": "Р–СѓСЂРЅР°Р» СЃРѕР±С‹С‚РёР№",
    "recordings_tab": "РџСЂРѕСЃРјРѕС‚СЂ Р·Р°РїРёСЃРµР№",
    "add_camera": "Р”РѕР±Р°РІР»РµРЅРёРµ РєР°РјРµСЂ",
    "delete_camera": "РЈРґР°Р»РµРЅРёРµ РєР°РјРµСЂ",
    "camera_settings": "РќР°СЃС‚СЂРѕР№РєРё РєР°РјРµСЂ",
    "toggle_cameras": "Р—Р°РїСѓСЃРє Рё РѕСЃС‚Р°РЅРѕРІРєР° РєР°РјРµСЂ",
    "restart_cameras": "РџРµСЂРµР·Р°РїСѓСЃРє РєР°РјРµСЂ",
    "export_csv": "Р­РєСЃРїРѕСЂС‚ CSV",
    "clear_events": "РћС‡РёСЃС‚РєР° Р¶СѓСЂРЅР°Р»Р°",
    "manage_users": "РЈРїСЂР°РІР»РµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРјРё",
    "recording_settings": "РќР°СЃС‚СЂРѕР№РєРё Р·Р°РїРёСЃРё",
}


def get_default_permissions(role):
    if role == "admin":
        return {key: True for key in PERMISSION_LABELS}

    return {
        "live_view": True,
        "events_tab": True,
        "recordings_tab": True,
        "add_camera": False,
        "delete_camera": False,
        "camera_settings": False,
        "toggle_cameras": True,
        "restart_cameras": False,
        "export_csv": True,
        "clear_events": False,
        "manage_users": False,
        "recording_settings": False,
    }


def normalize_permissions(permissions=None, role="operator"):
    normalized = {key: False for key in PERMISSION_LABELS}

    if permissions is None:
        normalized.update(get_default_permissions(role))
        return normalized

    for key in normalized:
        normalized[key] = bool(permissions.get(key, False))

    return normalized


def permissions_to_json(permissions, role="operator"):
    return json.dumps(normalize_permissions(permissions, role), ensure_ascii=False)


def permissions_from_json(raw_permissions, role="operator"):
    if not raw_permissions:
        return normalize_permissions(None, role)

    try:
        parsed = json.loads(raw_permissions)
    except (json.JSONDecodeError, TypeError):
        return normalize_permissions(None, role)

    return normalize_permissions(parsed, role)


def row_to_user(row):
    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "role": row[3],
        "permissions": permissions_from_json(row[4], row[3]),
        "must_change_password": bool(row[5]),
    }


def get_db():
    return sqlite3.connect(DB_NAME, timeout=DB_TIMEOUT_SECONDS)


def ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def count_admins(cursor):
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    return cursor.fetchone()[0]


def ensure_user(cursor, username, password, role):
    default_permissions = permissions_to_json(None, role)
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password_hash, role, permissions, must_change_password)
        VALUES (?, ?, ?, ?, 1)
        """,
        (username, hash_password(password), role, default_permissions),
    )
    cursor.execute(
        """
        UPDATE users
        SET role = COALESCE(role, ?),
            permissions = COALESCE(permissions, ?)
        WHERE username = ?
        """,
        (role, default_permissions, username),
    )


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            permissions TEXT
        )
        """
    )
    ensure_column(c, "users", "permissions", "TEXT")
    ensure_column(c, "users", "must_change_password", "INTEGER DEFAULT 0")
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            camera_name TEXT,
            timestamp TEXT,
            file_path TEXT,
            description TEXT
        )
        """
    )

    ensure_user(c, "admin", "password", "admin")
    ensure_user(c, "operator", "operator", "operator")

    # РџРѕРјРµС‡Р°РµРј СѓС‡С‘С‚РєРё СЃ РґРµС„РѕР»С‚РЅС‹РјРё РїР°СЂРѕР»СЏРјРё, СЃРѕР·РґР°РЅРЅС‹Рµ РґРѕ РІРІРµРґРµРЅРёСЏ С„Р»Р°РіР°
    for username, legacy_hash in LEGACY_DEFAULT_HASHES.items():
        c.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ? AND password_hash = ?",
            (username, legacy_hash),
        )

    conn.commit()
    conn.close()


def fetch_usernames():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username FROM users ORDER BY username")
    usernames = [row[0] for row in c.fetchall()]
    conn.close()
    return usernames


def get_user_by_id(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, role, permissions, must_change_password FROM users WHERE id = ?", (user_id,))
    user = row_to_user(c.fetchone())
    conn.close()
    return user


def get_user_by_username(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, role, permissions, must_change_password FROM users WHERE username = ?", (username,))
    user = row_to_user(c.fetchone())
    conn.close()
    return user


def authenticate_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, username, password_hash, role, permissions, must_change_password FROM users WHERE username = ?",
        (username,),
    )
    user = row_to_user(c.fetchone())

    if not user or not verify_password(password, user["password_hash"]):
        conn.close()
        return None

    # Прозрачный апгрейд legacy-хеша (несолёный SHA-256) на PBKDF2
    if is_legacy_hash(user["password_hash"]):
        c.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user["id"]),
        )
        conn.commit()

    conn.close()
    return user


def change_own_password(user_id, new_password):
    error = validate_password_strength(new_password)
    if error:
        raise ValueError(error)

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
        (hash_password(new_password), user_id),
    )
    conn.commit()
    conn.close()


def fetch_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, role, permissions, must_change_password FROM users ORDER BY username")
    users = [row_to_user(row) for row in c.fetchall()]
    conn.close()
    return users


def create_user(username, password, role, permissions):
    error = validate_password_strength(password)
    if error:
        raise ValueError(error)

    conn = get_db()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO users (username, password_hash, role, permissions)
        VALUES (?, ?, ?, ?)
        """,
        (username, hash_password(password), role, permissions_to_json(permissions, role)),
    )
    conn.commit()
    conn.close()


def update_user(user_id, username, role, permissions, password=None):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError("Пользователь не найден")

    if row[0] == "admin" and role != "admin" and count_admins(c) <= 1:
        conn.close()
        raise ValueError("Нельзя понизить роль последнего администратора")

    if password:
        error = validate_password_strength(password)
        if error:
            conn.close()
            raise ValueError(error)
        c.execute(
            """
            UPDATE users
            SET username = ?, password_hash = ?, role = ?, permissions = ?
            WHERE id = ?
            """,
            (username, hash_password(password), role, permissions_to_json(permissions, role), user_id),
        )
    else:
        c.execute(
            """
            UPDATE users
            SET username = ?, role = ?, permissions = ?
            WHERE id = ?
            """,
            (username, role, permissions_to_json(permissions, role), user_id),
        )

    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError("РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")

    if row[0] == "admin":
        if count_admins(c) <= 1:
            conn.close()
            raise ValueError("РќРµР»СЊР·СЏ СѓРґР°Р»РёС‚СЊ РїРѕСЃР»РµРґРЅРµРіРѕ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°")

    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def check_database_health():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        users_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM events")
        events_count = c.fetchone()[0]
        conn.close()
        return True, f"Р‘Р”: OK ({users_count} users, {events_count} events)"
    except Exception as error:
        return False, f"Р‘Р”: РѕС€РёР±РєР° ({error})"
