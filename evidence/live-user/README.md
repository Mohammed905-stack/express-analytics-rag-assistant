# Optional candidate live tests — 30 September 2026

Screenshots and downloaded response JSON are optional testing records, not required deliverables in the assignment.

These unchanged screenshots were supplied by Mohammed Kaderji from the local application running on his Windows laptop with his own Gemini key. They show the user interface, not mocked automated-test output. The source excerpts and complete workflow are recorded in the five original API response downloads alongside these screenshots. Raw provider request/response transcripts are not included.

| Screenshot | Visible result |
|---|---|
| 01-request-body.png | Request-body answer, citations and support check passed |
| 02-outside-corpus.png | Weather question refused; one corrective retrieval retry |
| 03-optional-parameters.png | Optional query parameters answer, citations and support check passed |
| 04-http-exception.png | HTTPException/404 answer, citation and support check passed |
| 05-file-uploads.png | bytes versus UploadFile answer, citations and support check passed |
| 06-feedback-saved.png | Comment submitted; Feedback saved confirmation |

See ../../VALIDATION.md for the distinction between these live observations and automated tests, plus known limits.

## Original API response downloads

The five JSON files preserve the candidate's downloads unchanged, including the original question, returned answer/refusal, source excerpts, request ID and decision trace. Four have status answered and a recorded successful support check; the weather question has status insufficient_context and one retrieval retry. response-summary.json maps filenames to questions and observed outcomes.

The earlier-failures/ folder contains two pre-fix citation failures, explicitly labelled as debugging evidence. They are retained honestly rather than presented as successful results. Duplicate downloads of those same failures are omitted.
