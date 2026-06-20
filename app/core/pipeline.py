"""Core NL-to-SQL pipeline - orchestrates the full question-to-answer flow."""

import time
from typing import Optional

from app.core.models import PipelineResult
from app.db.connection import execute_read_query
from app.guardrails.sql_validator import validate_sql
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_provider
from app.schema.context_builder import build_schema_context


MAX_RETRY_ATTEMPTS = 1


async def run_pipeline(
    question: str,
    conversation_context: Optional[str] = None,
    provider: Optional[BaseLLMProvider] = None,
) -> PipelineResult:
    """
    Run the full NL-to-SQL pipeline.

    Steps:
    1. Assess ambiguity - if ambiguous, return clarifying question
    2. Classify domain
    3. Build schema context for domain
    4. Generate SQL
    5. Validate SQL
    6. Execute query
    7. Return results (formatting happens in the formatter layer)

    Args:
        question: User's natural language question
        conversation_context: Optional context from previous clarification
        provider: LLM provider (uses default if None)

    Returns:
        PipelineResult with answer, SQL, and metadata
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

        # Step 3: Assess ambiguity
        ambiguity = await llm.assess_ambiguity(effective_question, schema_context)
        if ambiguity.is_ambiguous and not conversation_context:
            elapsed = (time.time() - start_time) * 1000
            return PipelineResult(
                answer=ambiguity.clarifying_question or "Could you please be more specific about what you'd like to know?",
                is_clarification=True,
                domain=domain,
                execution_time_ms=elapsed,
            )

        # Step 4: Generate SQL
        sql = await llm.generate_sql(effective_question, schema_context)

        # Step 5: Validate SQL
        validation = validate_sql(sql)

        if not validation.is_valid:
            # Retry once - feed error back to LLM
            retry_question = (
                f"{effective_question}\n\n"
                f"IMPORTANT: Your previous SQL was invalid: {validation.error_message}. "
                f"Generate ONLY a valid SELECT query."
            )
            sql = await llm.generate_sql(retry_question, schema_context)
            validation = validate_sql(sql)

            if not validation.is_valid:
                elapsed = (time.time() - start_time) * 1000
                return PipelineResult(
                    answer="I couldn't generate a valid query for that question. Could you try rephrasing it?",
                    sql=sql,
                    domain=domain,
                    error=validation.error_message,
                    execution_time_ms=elapsed,
                )

        # Step 6: Execute query
        try:
            results = await execute_read_query(validation.sanitized_sql)
        except RuntimeError as e:
            elapsed = (time.time() - start_time) * 1000
            error_msg = str(e)
            # Generate a friendly error response
            answer = await llm.generate_response(
                effective_question, sql, [], error=error_msg
            )
            return PipelineResult(
                answer=answer,
                sql=sql,
                domain=domain,
                error=error_msg,
                execution_time_ms=elapsed,
            )

        # Step 7: Return results (formatting handled externally)
        elapsed = (time.time() - start_time) * 1000
        return PipelineResult(
            answer="",  # Will be filled by formatter
            sql=sql,
            domain=domain,
            raw_results=results,
            row_count=len(results),
            execution_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        import logging
        logging.error(f"Pipeline error for question '{question}': {type(e).__name__}: {e}")
        return PipelineResult(
            answer=f"I encountered an error processing your question. Please try again.",
            error=str(e),
            execution_time_ms=elapsed,
        )
