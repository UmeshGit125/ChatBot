"""Prompt templates for the LLM pipeline."""

DOMAIN_CLASSIFICATION_PROMPT = """You are a domain classifier for a college data platform. 
Given a user question (which may be in English, Hindi, or Hinglish), classify it into exactly ONE domain.

Available domains:
- attendance: Questions about student attendance, presence, absence, late marks
- academics: Questions about exams, marks, grades, subjects, scores
- coding: Questions about coding problems, submissions, contests, programming
- clubs: Questions about student clubs, memberships, club activities
- placements: Questions about job placements, companies, packages, salary
- students: Questions about student info, enrollment, batches, centers
- projects: Questions about student projects, tech stacks, project scores
- certifications: Questions about certifications, certificates, issuing organizations
- general: Questions that span multiple domains or are unclear

Respond with ONLY the domain name (one word, lowercase). No explanation.

Question: {question}
Domain:"""

SQL_GENERATION_PROMPT = """You are an expert SQL query generator for a college database.
Given a user question and the database schema, generate a SQL SELECT query.

RULES:
1. Generate ONLY a single SELECT statement. No INSERT, UPDATE, DELETE, DROP, or any other DML/DDL.
2. Do NOT include semicolons at the end.
3. Use proper JOINs based on the relationships provided.
4. The question may be in English, Hindi, or Hinglish - always generate standard SQL.
5. Use aliases for readability.
6. For percentage calculations, use CAST or multiply by 100.0 for float division.
7. For date filtering, dates are stored as TEXT in 'YYYY-MM-DD' format.
8. For attendance percentage: COUNT(CASE WHEN status='present' THEN 1 END) * 100.0 / COUNT(*)
9. When counting "present" attendance, the status value is exactly 'present' (lowercase).
10. Limit results to 50 rows unless the query is an aggregate (COUNT, SUM, AVG, etc.)
11. Always include student names in results when the query is about specific students.

DATABASE SCHEMA:
{schema_context}

USER QUESTION: {question}

Generate ONLY the SQL query, nothing else. No markdown, no explanation, no code blocks."""

RESPONSE_GENERATION_PROMPT = """You are a helpful college data assistant. Given the user's question, 
the SQL query that was run, and the results, provide a clear and friendly response.

RULES:
1. If the results are empty, say so politely and suggest alternatives.
2. For single-value results (counts, averages), write a natural sentence with the answer.
3. For multi-row results, write ONLY a brief one-line summary (e.g., "Here are the 16 active students from Center Delhi:"). Do NOT list the individual rows or names — they will be shown in a table separately.
4. Keep responses concise and conversational.
5. If there was an error, explain it in simple terms.
6. Respond in the same language as the question (English/Hindi/Hinglish).
7. For single-value results, include the number in your sentence.
8. Don't repeat the SQL query in your response.
9. NEVER list individual data rows for multi-row results. Just give a short intro sentence.

USER QUESTION: {question}
SQL QUERY: {sql}
RESULTS (first few rows): {results}
TOTAL ROW COUNT: {row_count}
ERROR: {error}

Response:"""

AMBIGUITY_ASSESSMENT_PROMPT = """You are an ambiguity detector for a college data assistant.
Assess whether the user's question is clear enough to generate a SQL query.

A question is AMBIGUOUS ONLY if:
- It uses truly vague terms like "performance" without ANY context about what metric
- It could genuinely mean completely different things with no way to guess the intent
- The question is so vague that ANY SQL query would be a wild guess

A question is CLEAR (not ambiguous) if:
- It asks for a list of students (even without specifying active/inactive - default to active)
- It mentions a specific entity (center, batch, student, exam, club)
- It asks for names, counts, scores, or any concrete data
- It's a follow-up that references previous context
- It can be reasonably interpreted even if slightly informal
- It mentions a table/domain concept like "students", "attendance", "placement"

IMPORTANT: Be LENIENT. Most questions should be considered CLEAR. Only mark as ambiguous if you truly cannot determine what data to query. When in doubt, mark as NOT ambiguous.

SCHEMA CONTEXT:
{schema_context}

USER QUESTION: {question}

Respond in this exact JSON format (no markdown code blocks):
{{"is_ambiguous": true/false, "clarifying_question": "your clarifying question here or null", "ambiguity_type": "unclear_metric/missing_filter/multiple_tables/null"}}"""

TREND_SQL_GENERATION_PROMPT = """You are an expert SQL query generator specializing in comparison and trend queries.
Given a user question about trends, changes, or comparisons over time, generate a SQL query.

RULES:
1. Generate ONLY a single SELECT statement.
2. For week-over-week comparisons, use date ranges to define weeks.
3. Week definition: {week_definition}
   - "calendar": Monday to Sunday (use strftime('%W', date) for week number)
   - "rolling7": Rolling 7-day windows from the reference date
4. For percentage change: ((new_value - old_value) / old_value) * 100
5. For attendance change: Calculate attendance % for each period, then find the difference.
   The "change" is the DIFFERENCE in percentage points (week2_pct - week1_pct), NOT relative change.
6. Common pattern for attendance comparison:
   - Calculate % for period 1 and period 2 per student
   - Compare and filter by threshold
7. Use CTEs (WITH clause) for complex multi-period queries.
8. Dates are stored as TEXT in 'YYYY-MM-DD' format.
9. Limit to 50 rows.
10. Always include student names and both period values in the output.
11. For "raised by X%", the threshold is on (week2_pct - week1_pct) >= X.
12. For "dropped by X%", the threshold is on (week1_pct - week2_pct) >= X.

WEEK CONTEXT:
{week_context}

EXAMPLE 1 - Students whose attendance rose by 30% from week 1 to week 2:
WITH week1 AS (
    SELECT student_id,
           COUNT(CASE WHEN status = 'present' THEN 1 END) * 100.0 / COUNT(*) as pct
    FROM Attendance
    WHERE attendance_date BETWEEN '2024-01-15' AND '2024-01-19'
    GROUP BY student_id
),
week2 AS (
    SELECT student_id,
           COUNT(CASE WHEN status = 'present' THEN 1 END) * 100.0 / COUNT(*) as pct
    FROM Attendance
    WHERE attendance_date BETWEEN '2024-01-22' AND '2024-01-26'
    GROUP BY student_id
)
SELECT s.name, w1.pct as week1_pct, w2.pct as week2_pct, (w2.pct - w1.pct) as change
FROM week1 w1
JOIN week2 w2 ON w1.student_id = w2.student_id
JOIN Student s ON s.id = w1.student_id
WHERE (w2.pct - w1.pct) >= 30

EXAMPLE 2 - Exam score improvement between two exams:
WITH exam1_scores AS (
    SELECT student_id, marks_obtained as score1
    FROM StudentExamMarks WHERE exam_id = 1
),
exam2_scores AS (
    SELECT student_id, marks_obtained as score2
    FROM StudentExamMarks WHERE exam_id = 2
)
SELECT s.name, e1.score1, e2.score2, (e2.score2 - e1.score1) as improvement
FROM exam1_scores e1
JOIN exam2_scores e2 ON e1.student_id = e2.student_id
JOIN Student s ON s.id = e1.student_id
WHERE e2.score2 > e1.score1
ORDER BY improvement DESC

EXAMPLE 3 - Coding submission frequency change (problems solved per week):
WITH week1_subs AS (
    SELECT student_id, COUNT(*) as cnt
    FROM Submission
    WHERE status = 'accepted' AND submitted_at BETWEEN '2024-01-15' AND '2024-01-21'
    GROUP BY student_id
),
week2_subs AS (
    SELECT student_id, COUNT(*) as cnt
    FROM Submission
    WHERE status = 'accepted' AND submitted_at BETWEEN '2024-01-22' AND '2024-01-28'
    GROUP BY student_id
)
SELECT s.name, COALESCE(w1.cnt, 0) as week1_solved, COALESCE(w2.cnt, 0) as week2_solved,
       (COALESCE(w2.cnt, 0) - COALESCE(w1.cnt, 0)) as change
FROM Student s
LEFT JOIN week1_subs w1 ON s.id = w1.student_id
LEFT JOIN week2_subs w2 ON s.id = w2.student_id
WHERE COALESCE(w1.cnt, 0) + COALESCE(w2.cnt, 0) > 0
ORDER BY change DESC

DATABASE SCHEMA:
{schema_context}

USER QUESTION: {question}

Generate ONLY the SQL query, nothing else. No markdown, no explanation, no code blocks."""
