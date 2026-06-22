"""Database schema introspection module."""

from typing import Any

from app.core.config import settings
from app.db.connection import execute_read_query


async def get_table_names() -> list[str]:
    """Get all table names from the database."""
    if settings.USE_METABASE and settings.METABASE_URL:
        from app.db.metabase_client import metabase_client
        return await metabase_client.get_tables()

    if settings.is_sqlite:
        results = await execute_read_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row["name"] for row in results]
    else:
        results = await execute_read_query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        return [row["table_name"] for row in results]


async def get_table_columns(table_name: str) -> list[dict[str, Any]]:
    """Get column info for a specific table."""
    if settings.USE_METABASE and settings.METABASE_URL:
        # Use Metabase's native query to get column info
        results = await execute_read_query(
            f"SELECT column_name, data_type, is_nullable, column_default "
            f"FROM information_schema.columns "
            f"WHERE table_schema = 'public' AND table_name = '{table_name}' "
            f"ORDER BY ordinal_position"
        )
        return [
            {
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "is_nullable": row.get("is_nullable", "YES") == "YES",
                "is_primary_key": False,
                "default_value": row.get("column_default"),
            }
            for row in results
        ]

    if settings.is_sqlite:
        results = await execute_read_query(f"PRAGMA table_info('{table_name}')")
        return [
            {
                "column_name": row["name"],
                "data_type": row["type"],
                "is_nullable": not row["notnull"],
                "is_primary_key": bool(row["pk"]),
                "default_value": row["dflt_value"],
            }
            for row in results
        ]
    else:
        results = await execute_read_query(
            f"SELECT column_name, data_type, is_nullable, column_default "
            f"FROM information_schema.columns "
            f"WHERE table_schema = 'public' AND table_name = '{table_name}' "
            f"ORDER BY ordinal_position"
        )
        return [
            {
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "is_nullable": row["is_nullable"] == "YES",
                "is_primary_key": False,  # Would need additional query for PK info
                "default_value": row.get("column_default"),
            }
            for row in results
        ]


async def get_full_schema() -> dict[str, list[dict[str, Any]]]:
    """Get complete schema: all tables with their columns."""
    tables = await get_table_names()
    schema = {}
    for table in tables:
        schema[table] = await get_table_columns(table)
    return schema
