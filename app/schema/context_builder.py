"""Schema context builder - merges introspection with curated annotations."""

import os
from typing import Any

import yaml

from app.schema.introspector import get_full_schema


_annotations_cache: dict | None = None


def load_annotations() -> dict:
    """Load the curated annotations YAML file."""
    global _annotations_cache
    if _annotations_cache is None:
        annotations_path = os.path.join(
            os.path.dirname(__file__), "annotations.yaml"
        )
        with open(annotations_path, "r") as f:
            _annotations_cache = yaml.safe_load(f)
    return _annotations_cache


def get_domain_tables(domain: str) -> list[str]:
    """Get the list of tables relevant to a specific domain."""
    annotations = load_annotations()
    domains = annotations.get("domains", {})
    if domain in domains:
        return domains[domain].get("tables", [])
    # If domain not found, return all tables
    all_tables = set()
    for d in domains.values():
        all_tables.update(d.get("tables", []))
    return list(all_tables)


def get_domain_notes(domain: str) -> list[str]:
    """Get domain-specific notes and guidelines."""
    annotations = load_annotations()
    domains = annotations.get("domains", {})
    if domain in domains:
        return domains[domain].get("notes", [])
    return []


def get_excluded_columns() -> list[str]:
    """Get columns that should be excluded from schema context."""
    annotations = load_annotations()
    return annotations.get("excluded_columns", [])


def get_table_annotation(table_name: str) -> dict[str, Any]:
    """Get annotation for a specific table."""
    annotations = load_annotations()
    tables = annotations.get("tables", {})
    return tables.get(table_name, {})


def get_relationships() -> list[str]:
    """Get all relationship definitions."""
    annotations = load_annotations()
    return annotations.get("relationships", [])


async def build_schema_context(
    domain: str | None = None, include_relationships: bool = True
) -> str:
    """
    Build a schema context string for the LLM prompt.

    Args:
        domain: If specified, only include tables for this domain.
                If None, include all tables.
        include_relationships: Whether to include relationship info.

    Returns:
        Formatted schema context string ready for LLM prompt.
    """
    # Get live schema from DB
    full_schema = await get_full_schema()
    excluded_cols = get_excluded_columns()

    # Determine which tables to include
    if domain:
        relevant_tables = get_domain_tables(domain)
    else:
        relevant_tables = list(full_schema.keys())

    # Build the context string
    lines = []

    if domain:
        annotations = load_annotations()
        domain_info = annotations.get("domains", {}).get(domain, {})
        lines.append(f"## Domain: {domain.title()}")
        if domain_info.get("description"):
            lines.append(f"Description: {domain_info['description']}")
        lines.append("")

        # Domain notes
        notes = get_domain_notes(domain)
        if notes:
            lines.append("### Important Notes:")
            for note in notes:
                lines.append(f"- {note}")
            lines.append("")

    lines.append("### Database Tables:\n")

    for table_name in relevant_tables:
        if table_name not in full_schema:
            continue

        columns = full_schema[table_name]
        annotation = get_table_annotation(table_name)

        # Table header with description
        table_desc = annotation.get("description", "")
        lines.append(f"**{table_name}** - {table_desc}")

        # Column details
        col_annotations = annotation.get("columns", {})
        lines.append("| Column | Type | Description |")
        lines.append("|--------|------|-------------|")

        for col in columns:
            col_name = col["column_name"]
            # Skip excluded columns
            if col_name in excluded_cols:
                continue
            col_type = col["data_type"]
            col_desc = col_annotations.get(col_name, "")
            pk_marker = " (PK)" if col.get("is_primary_key") else ""
            lines.append(f"| {col_name}{pk_marker} | {col_type} | {col_desc} |")

        lines.append("")

    # Add relationships
    if include_relationships:
        relationships = get_relationships()
        # Filter to relevant tables
        relevant_rels = []
        for rel in relationships:
            # Check if either side of the relationship mentions a relevant table
            for table in relevant_tables:
                if table in rel:
                    relevant_rels.append(rel)
                    break

        if relevant_rels:
            lines.append("### Relationships (JOINs):")
            for rel in relevant_rels:
                lines.append(f"- {rel}")
            lines.append("")

    return "\n".join(lines)


def get_available_domains() -> list[str]:
    """Get list of all available domains."""
    annotations = load_annotations()
    return list(annotations.get("domains", {}).keys())
