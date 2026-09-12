import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "orange-backend" / "orange_community.db"
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "local-d1-data.sql"


def sql_value(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def export_table(connection, table, columns):
    rows = connection.execute(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
    ).fetchall()
    statements = []
    column_sql = ", ".join(columns)
    for row in rows:
        values = ", ".join(sql_value(value) for value in row)
        statements.append(
            f"INSERT OR REPLACE INTO {table} ({column_sql}) VALUES ({values});"
        )
    return statements


def main():
    if not SOURCE.exists():
        raise SystemExit(f"Local database not found: {SOURCE}")

    connection = sqlite3.connect(SOURCE)
    tables = [
        ("users", ["id", "email", "username", "password", "created_at", "orange_balance", "last_sign_in_date", "role"]),
        ("codes", ["id", "email", "code", "expires_at", "is_used"]),
        ("checkin_records", ["id", "email", "checkin_date", "points", "created_at"]),
        (
            "admin_audit_logs",
            [
                "id",
                "admin_email",
                "admin_username",
                "target_user_id",
                "target_email",
                "target_username",
                "old_balance",
                "new_balance",
                "old_role",
                "new_role",
                "created_at",
            ],
        ),
    ]

    statements = [
        "-- Generated from the local SQLite database. Do not commit this file.",
    ]
    for table, columns in tables:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists:
            statements.extend(export_table(connection, table, columns))
    connection.close()

    OUTPUT.write_text("\n".join(statements) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
