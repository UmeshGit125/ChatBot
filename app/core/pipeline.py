"""Core NL-to-SQL pipeline - orchestrates the full question-to-answer flow."""

import logging
import time
from typing import Optional

from app.core.models import PipelineResult
from app.db.connection import execute_read_query
from app.guardrails.sql_validator import validate_sql
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_provider
from app.schema.context_builder import build_schema_context


MAX_SQL_RETRIES = 3


async def _generate_and_execute_sql(
    llm: BaseLLMProvider,
    question: str,
    schema_context: str,
    attempt: int = 1,
    previous_sql: str | None = None,
    previous_error: str | None = None,
) -> tuple[str, list[dict] | None, str | None]:
    """
    Generate SQL, validate, and execute. Returns (sql, results, error).
    
    If previous attempts failed, includes that context for the LLM to learn from.
    """
    # Build the prompt with retry context if needed
    if previous_error and previous_sql:
        prompt_question = (
            f"{question}\n\n"
            f"PREVIOUS ATTEMPT (failed): {previous_sql}\n"
            f"ERROR/ISSUE: {previous_error}\n"
            f"Generate a DIFFERENT query that avoids this issue. "
            f"Try a simpler approach - maybe fewer JOINs or looser filters."
        )
    else:
        prompt_question = question

    # Generate SQL
    sql = await llm.generate_sql(prompt_question, schema_context)

    # Validate
    validation = validate_sql(sql)
    if not validation.is_valid:
        return sql, None, f"Invalid SQL: {validation.error_message}"

    # Execute
    try:
        results = await execute_read_query(validation.sanitized_sql)
        return sql, results, None
    except RuntimeError as e:
        return sql, None, f"Execution error: {str(e)}"


async def run_pipeline(
    question: str,
    conversation_context: Optional[str] = None,
    provider: Optional[BaseLLMProvider] = None,
) -> PipelineResult:
    """
    Run the full NL-to-SQL pipeline with self-healing retry.

    Flow:
    1. Classify domain
    2. Build schema context
    3. (Optional) Assess ambiguity for very short questions
    4. Generate SQL → Validate → Execute
    5. If no results or error: retry with feedback (up to 3 attempts)
    6. Return results

    The retry mechanism feeds the failed SQL and error back to the LLM
    so it can generate a better query on each attempt.
    """
    start_time = time.time()
    llm = provider or get_provider()

    # If there's conversation context (answer to a clarification), combine it
    effective_question = question
    if conversation_context:
        effective_question = f"{conversation_context}\nUser's answer: {question}"

    try:
        # Step 1: Classify domain
        domain = await llm.classify_domain(effective_question)

        # Step 2: Build schema context
        schema_context = await build_schema_context(domain)

        # Step 3: Assess ambiguity (only for very short vague questions)
        if not conversation_context and len(effective_question.split()) <= 3:
            ambiguity = await llm.assess_ambiguity(effective_question, schema_context)
            if ambiguity.is_ambiguous:
                elapsed = (time.time() - start_time) * 1000
                return PipelineResult(
                    answer=ambiguity.clarifying_question or "Could you please be more specific?",
                    is_clarification=True,
                    domain=domain,
                    execution_time_ms=elapsed,
                )

        # Step 4-5: Generate SQL with retry loop
        last_sql = None
        last_error = None
        all_attempts = []

        for attempt in range(1, MAX_SQL_RETRIES + 1):
            sql, results, error = await _generate_and_execute_sql(
                llm=llm,
                question=effective_question,
                schema_context=schema_context,
                attempt=attempt,
                previous_sql=last_sql,
                previous_error=last_error,
            )

            all_attempts.append({"sql": sql, "error": error, "row_count": len(results) if results else 0})
            logging.info(f"Attempt {attempt}: SQL={sql[:80]}... | Results={len(results) if results else 0} | Error={error}")

            # Success with results
            if results is not None and len(results) > 0:
                elapsed = (time.time() - start_time) * 1000
                return PipelineResult(
                    answer="",  # Filled by formatter
                    sql=sql,
                    domain=domain,
                    raw_results=results,
                    row_count=len(results),
                    execution_time_ms=elapsed,
                )

            # Query executed but returned 0 results
            if results is not None and len(results) == 0:
                if attempt < MAX_SQL_RETRIES:
                    last_sql = sql
                    last_error = (
                        "Query returned 0 results. The data might exist but your filters "
                        "are too strict. Try: removing semester/date filters, using ILIKE "
                        "for fuzzy matching, using LEFT JOINs, or querying the data with "
                        "fewer conditions to see what's available."
                    )
                    continue
                else:
                    # All retries exhausted with 0 results
                    elapsed = (time.time() - start_time) * 1000
                    return PipelineResult(
                        answer="",
                        sql=sql,
                        domain=domain,
                        raw_results=[],
                        row_count=0,
                        execution_time_ms=elapsed,
                    )

            # Query had an execution error
            if error:
                if attempt < MAX_SQL_RETRIES:
                    last_sql = sql
                    last_error = error
                    continue
                else:
                    # All retries exhausted with errors
                    elapsed = (time.time() - start_time) * 1000
                    answer = await llm.generate_response(
                        effective_question, sql, [], error=error
                    )
                    return PipelineResult(
                        answer=answer,
                        sql=sql,
                        domain=domain,
                        error=error,
                        execution_time_ms=elapsed,
                    )

        # Should not reach here, but just in case
        elapsed = (time.time() - start_time) * 1000
        return PipelineResult(
            answer="I couldn't find the data you're looking for after multiple attempts. Try rephrasing your question.",
            sql=last_sql,
            domain=domain,
            raw_results=[],
            row_count=0,
            execution_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logging.error(f"Pipeline error for question '{question}': {type(e).__name__}: {e}")
        return PipelineResult(
            answer="I encountered an error processing your question. Please try again.",
            error=str(e),
            execution_time_ms=elapsed,
        )
