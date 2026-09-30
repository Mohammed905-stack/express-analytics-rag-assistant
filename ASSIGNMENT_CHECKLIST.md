# Assignment mapping — one application

| Requirement | Implementation | Status |
|---|---|---|
| 3–5 real technical documents | Five official FastAPI guides, corpus manifest and refresh script | Included |
| Python + FastAPI + LangGraph | app/main.py, app/workflow.py, requirements.txt | Implemented |
| Query analysis / rewrite | query_analysis node; original question retained | Implemented |
| Vector retrieval with metadata | Gemini embeddings, FAISS, SQLite metadata | Implemented |
| Per-chunk LLM relevance grading | document_grading node | Implemented |
| Conditional routing and bounded retries | StateGraph edges and query_rewrite, MAX_RETRIES | Implemented |
| Grounded generation with citations | internal labels, code validation, returned excerpts | Implemented |
| Ingestion files OR URLs | UTF-8 md/txt/html file uploads | Files option implemented |
| POST /query, POST /ingest, GET /documents, POST /feedback | FastAPI routes + request validation | Implemented and tested |
| Optional support checker | grounding_check, enabled by default | Included |
| Optional UI | Local HTML/CSS/JavaScript interface | Included |
| README/setup/examples/tradeoffs | README.md, START_HERE.md | Included |
| Thought process and improvements | README architecture/chunking/tradeoffs | Included |
| GitHub repository submission | Public repository, source code, tests and submission guide | Repository created; source upload and CI verification in progress |
| Optional live test evidence | User's Windows run with their own key; screenshots in evidence/live-user/ | Five guides indexed; four useful questions, outside-corpus refusal and feedback demonstrated |

No additional separate project is required. Public hosting, web fallback and multi-turn memory are not required and are not claimed.
