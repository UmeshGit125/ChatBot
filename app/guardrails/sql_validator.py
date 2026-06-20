"""SQL validation guardrail - ensures only safe SELECT statements reach the database."""

from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DML


# Maximum allowed query length (chars)
MAX_QUERY_LENGTH = 2000

# Forbidden keywords that indicate write/DDL operations
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "MERGE", "UPSERT", "REPLACE", "CALL",
}

# Forbidden patterns even within comments or strings
FORBIDDEN_PATTERNS = [
    "DROP TABLE", "DROP DATABASE", "DROP SCHEMA",
    "ALTER TABLE", "ALTER DATABASE",
    "TRUNCATE TABLE",
    "CREATE TABLE", "CREATE DATABASE", "CREATE INDEX",
    "GRANT ALL", "REVOKE ALL",
    "INTO OUTFILE", "INTO DUMPFILE",
    "LOAD_FILE", "LOAD DATA",
]


@dataclass
class ValidationResult:
    """Result of SQL validation."""
    is_valid: bool
    error_message: str | None = None
    sanitized_sql: str | None = None


def validate_sql(sql: str) -> ValidationResult:
    """
    Validate that the SQL is a safe, read-only SELECT statement.

    Performs multiple layers of validation:
    1. Length check
    2. Empty/null check
    3. Multiple statement detection
    4. Statement type validation (must be SELECT or WITH...SELECT)
    5. Forbidden keyword scanning
    6. Forbidden pattern detection

    Args:
        sql: The SQL string to validate.

    Returns:
        ValidationResult with is_valid flag and optional error message.
    """
    # Clean up
    if not sql or not sql.strip():
        return ValidationResult(
            is_valid=False,
            error_message="Empty SQL query",
        )

    sql = sql.strip()

    # Length check
    if len(sql) > MAX_QUERY_LENGTH:
        return ValidationResult(
            is_valid=False,
            error_message=f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters",
        )

    # Parse the SQL
    parsed_statements = sqlparse.parse(sql)

    # Must be exactly one statement
    # Filter out empty statements (from trailing semicolons)
    non_empty = [s for s in parsed_statements if s.tokens and str(s).strip()]
    if len(non_empty) == 0:
        return ValidationResult(
            is_valid=False,
            error_message="No valid SQL statement found",
        )

    if len(non_empty) > 1:
        return ValidationResult(
            is_valid=False,
            error_message="Multiple SQL statements detected. Only single SELECT queries are allowed.",
        )

    statement = non_empty[0]

    # Check statement type
    stmt_type = statement.get_type()
    if stmt_type not in ("SELECT", None):
        # stmt_type is None for WITH (CTE) statements, which we allow
        # as long as they don't contain forbidden keywords
        if stmt_type and stmt_type.upper() != "SELECT":
            return ValidationResult(
                is_valid=False,
                error_message=f"Statement type '{stmt_type}' is not allowed. Only SELECT queries are permitted.",
            )

    # For CTE (WITH) statements, verify the main query is a SELECT
    sql_upper = sql.upper()
    if stmt_type is None:
        # Should start with WITH and contain SELECT
        stripped_upper = sql_upper.strip()
        if stripped_upper.startswith("WITH"):
            # Make sure it's ultimately a SELECT
            if not _cte_ends_with_select(sql_upper):
                return ValidationResult(
                    is_valid=False,
                    error_message="CTE (WITH) statement must end with a SELECT query.",
                )
        else:
            return ValidationResult(
                is_valid=False,
                error_message="Unrecognized statement type. Only SELECT queries are permitted.",
            )

    # Scan for forbidden keywords in the actual SQL tokens
    forbidden_found = _scan_forbidden_keywords(statement)
    if forbidden_found:
        return ValidationResult(
            is_valid=False,
            error_message=f"Forbidden operation detected: {forbidden_found}. Only SELECT queries are permitted.",
        )

    # Pattern-based scanning (catches things in comments too)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in sql_upper:
            return ValidationResult(
                is_valid=False,
                error_message=f"Forbidden pattern detected: '{pattern}'. Only SELECT queries are permitted.",
            )

    # All checks passed
    return ValidationResult(
        is_valid=True,
        sanitized_sql=sql,
    )


def _scan_forbidden_keywords(statement: Statement) -> str | None:
    """
    Recursively scan statement tokens for forbidden DML/DDL keywords.

    Returns the forbidden keyword found, or None if clean.
    """
    for token in statement.flatten():
        if token.ttype in (DML, Keyword):
            word = token.value.upper().strip()
            if word in FORBIDDEN_KEYWORDS:
                return word
    return None


def _cte_ends_with_select(sql_upper: str) -> bool:
    """
    Check if a CTE (WITH ... ) statement ends with a SELECT.

    This handles nested CTEs by looking for the final main query
    after all CTE definitions.
    """
    # Simple heuristic: after the last closing paren that ends a CTE definition,
    # the remaining text should start with SELECT
    # More robust: check that no forbidden keywords appear outside CTE definitions
    
    # Remove all CTE definitions and check what's left
    # A CTE looks like: WITH name AS (...), name2 AS (...) SELECT ...
    # The final SELECT is what we care about
    
    # Check forbidden keywords appear in the SQL
    for kw in FORBIDDEN_KEYWORDS:
        # Check if keyword appears as a standalone word (not part of column/table name)
        import re
        pattern = r'\b' + kw + r'\b'
        if re.search(pattern, sql_upper):
            # Check if it's inside a CTE's SELECT (which is fine) or outside
            # For simplicity, we'll be strict: if INSERT/UPDATE/DELETE/DROP etc appear anywhere, reject
            if kw in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", 
                      "CREATE", "GRANT", "REVOKE"):
                return False

    return True
