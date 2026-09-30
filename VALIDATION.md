# Validation — 30 September 2026

## Automated checks

- Python 3.12 Linux: **70 tests passed**; actual output is in evidence/python-tests.txt.
- Node frontend tests: **8 passed**; actual output is in evidence/frontend-tests.txt.
- Chromium browser: real local page loads, missing-key instructions work, and no horizontal overflow occurs at 390/768/1440 pixels. Controlled HTTP fixtures verify indexing display, answers/sources/trace, safe text rendering, feedback, original-question download and HTTP 503 recovery. No JavaScript exceptions. See evidence/browser-checks.txt.
- Seven real HTTP checks without a key: homepage, health, documents, Swagger, OpenAPI, empty-corpus refusal and missing-key ingestion failure. See evidence/local-http-smoke.json.
- requirements-tested.txt records direct dependency versions used for validation. Production requirements use compatible version ranges.

Successful model responses in automated tests use doubles, and browser success scenarios intercept HTTP with explicit fixtures. These tests verify implementation behaviour rather than live Google availability or general answer accuracy.

## Optional live candidate demonstration

The candidate ran the application on their Windows laptop with their own Gemini key. Five guides were indexed. User-supplied screenshots show:

1. A cited request-body answer with a passed support check.
2. An outside-corpus weather question receiving an insufficient-context response and one corrective retrieval retry.
3. A cited optional-query-parameter answer with a passed support check.
4. A cited HTTPException/404 answer with a passed support check.
5. A cited bytes-versus-UploadFile answer with a passed support check.
6. The file-upload answer's feedback interface showing "Feedback saved."

The screenshots are preserved unchanged in evidence/live-user/. These are observations of the candidate's live interface, separate from automated fixture-based checks. They do not expose the key. Five original user-downloaded API responses now include the answer/refusal, source excerpts and full application decision trace. Four recorded successful support checks; the outside-corpus question recorded one retrieval retry and a refusal. The two earlier pre-fix citation failures are separately labelled in evidence/live-user/earlier-failures/. Raw provider transcripts are not included. Expand source excerpts and review them during a demo; an LLM support check is not a guarantee of factual correctness. CAPTURE_EVIDENCE.cmd can record full API responses on a configured installation if more evidence is needed.

The initial text model encountered provider HTTP 503 high demand. The candidate switched the text model to gemini-3.5-flash-lite while retaining the document embedding model. The final source defaults to that text model; model availability and quota can still vary by account and time.

## Citation corrections

An earlier live response reached retrieval and relevance grading but failed citation validation. Generation now records diagnostic failure categories, normalizes explicit single/double-bracket S-labels and allows one citation-format correction. It still rejects unknown sources and runs grounding validation before accepting an answer.

A second response declared known but unused citation IDs. Validation now attaches only explicitly cited inline sources, dropping unused known metadata IDs. Unknown declared IDs and undeclared inline IDs still fail. Eight additional regression tests across the two fixes raised the Python test count from 62 to 70. The later screenshots show successful cited answers following those fixes.

## Delivery status and limits

The local working demo and source package are prepared. A public GitHub repository has been created at https://github.com/Mohammed905-stack/express-analytics-rag-assistant. All 67 source/evidence files were uploaded through the GitHub connection. GitHub Actions passed for source commit 4f940bfc2140550c2e50531f3408324e916a044e: https://github.com/Mohammed905-stack/express-analytics-rag-assistant/actions/runs/36745906222. Both the Python and frontend test steps succeeded. GitHub Actions runs on every push; check the latest run before submission. Follow GITHUB_SUBMISSION.md. No public deployment has occurred or is required by the assignment.

This is a single-process local prototype. Automated checks and the shown questions do not establish production readiness, exhaustive answer accuracy, performance at scale or future API availability.
