import json
import sqlite3

from utils import hash_password

DB_NAME = "database.db"

PERMISSION_LABELS = {
    "live_view": "Live View",
    "events_tab": "Журнал событий",
    "recordings_tab": "Просмотр записей",
    "add_camera": "Добавление камер",
    "delete_camera": "Удаление камер",
    "camera_settings": "Настройки камер",
    "toggle_cameras": "Запуск и остановка камер",
    "restart_cameras": "Перезапуск камер",
    "export_csv": "Экспорт CSV",
    "clear_events": "Очистка журнала",
    "manage_users": "Управление пользователями",
    "recording_settings": "Настройки записи",
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
    }


def get_db():
    return sqlite3.connect(DB_NAME)


def ensure_permissions_column(cursor):
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cursor.fetchall()}
    if "permissions" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT")


def ensure_user(cursor, username, password, role):
    default_permissions = permissions_to_json(None, role)
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password_hash, role, permissions)
        VALUES (?, ?, ?, ?)
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
    ensure_permissions_column(c)
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
    c.execute("SELECT id, username, password_hash, role, permissions FROM users WHERE id = ?", (user_id,))
    user = row_to_user(c.fetchone())
    conn.close()
    return user


def get_user_by_username(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, role, permissions FROM users WHERE username = ?", (username,))
    user = row_to_user(c.fetchone())
    conn.close()
    return user


def authenticate_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT id, username, password_hash, role, permissions FROM users WHERE username = ?",
        (username,),
    )
    user = row_to_user(c.fetchone())
    conn.close()

    if not user or user["password_hash"] != hash_password(password):
        return None

    return user


def fetch_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, role, permissions FROM users ORDER BY username")
    users = [row_to_user(row) for row in c.fetchall()]
    conn.close()
    return users


def create_user(username, password, role, permissions):
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

    if password:
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
        raise ValueError("Пользователь не найден")

    if row[0] == "admin":
        c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = c.fetchone()[0]
        if admin_count <= 1:
            conn.close()
            raise ValueError("Нельзя удалить последнего администратора")

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
        return True, f"БД: OK ({users_count} users, {events_count} events)"
    except Exception as error:
        return False, f"БД: ошибка ({error})"
