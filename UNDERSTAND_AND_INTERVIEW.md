# Understand the project and prepare for the interview

## Your project in everyday language

You built one application: a question-answer assistant for technical documentation. It reads five FastAPI guides. A developer can ask how to handle an API request or return an error, and the app finds useful passages and gives a source-backed explanation. FastAPI is a Python tool for building APIs. Our app both uses FastAPI to expose its own endpoints and uses FastAPI documentation as its demonstration knowledge base.

Think of an open-book exam: first find the useful pages, check whether they answer the question, then explain using those pages. If the pages do not help, search once more using different wording; if evidence is still missing, say so.

## Each part and why it exists

| Term | Plain explanation | Where to look |
|---|---|---|
| RAG | Retrieve useful text before asking AI to write an answer | workflow.py |
| Ingestion | Turn a document into searchable stored passages | ingestion.py |
| Chunk | A small passage, rather than the whole guide | ingestion.py |
| Overlap | Some repeated surrounding text so a cut does not lose context | ingestion.py |
| Embedding | Numbers representing a passage's meaning | provider.py |
| Vector search | Find passages with similar numerical meaning | store.py / FAISS |
| LangGraph | Coordinates the steps and branches as a graph | workflow.py |
| State | The request's shared notebook: question, passages, retry count, answer | workflow.py |
| Relevance grading | AI checks whether each passage helps answer this question | workflow.py |
| Grounding | Check that the draft is supported by cited passages | workflow.py |
| API | A defined way for programs to send requests and receive results | main.py |
| SQLite | A local database file storing docs, vectors, queries and feedback | store.py |
| UI | The page the user clicks and types in | app/static/ |

## What happens when you click Index

The app reads the five packaged guides, checks their hashes, cleans the text, splits it into 1,800-character passages with 250 characters overlap, gets document embeddings and stores the document and vectors. FAISS builds the searchable index. Identical content is deduplicated. The database survives restarting the app. The guides do not become five applications.

## What happens when you ask a question

1. Preserve your question; produce a better search phrase and classify the type.
2. Embed the search phrase and retrieve up to four similar passages.
3. Grade each passage for usefulness. Similarity alone does not prove relevance.
4. If none is useful, rewrite and search again, at most one additional attempt by default.
5. If useful evidence exists, generate an answer using it. Validate citation labels in code.
6. Check support and source attribution. Return the answer with numbered sources, or a refusal.
7. Save the response and its id; thumbs-up/down feedback refers to that id.

## A 45-second introduction you can adapt

“I developed a technical documentation assistant using Python, FastAPI and LangGraph, with AI assistance. It indexes five official FastAPI guides using Gemini embeddings and FAISS. For each question, it rewrites the search query, retrieves passages, grades relevance and generates a cited answer. If retrieval is weak, it retries within a fixed limit. Citation validation and a grounding check help prevent unsupported answers. I also added a local interface, persistent storage, feedback and automated tests.”

The candidate has run the live demo on Windows with their own Gemini key. User-supplied screenshots show four useful answers, an outside-corpus refusal and saved feedback; see evidence/live-user/README.md. Describe the AI assistance honestly and distinguish live demonstrations from automated tests.

## Interview questions with short answers

**Why RAG instead of simply asking Gemini?** A general model may answer from its training or invent details. RAG supplies our chosen documentation and returns inspectable sources; it still needs checks and evaluation.

**Why LangGraph?** The workflow branches and loops. Explicit state and conditional edges make retry behavior inspectable and testable.

**Why keep the original question?** A rewrite is only for retrieval. The final answer and export must address what the user originally asked.

**Why chunk documents?** Small passages are easier to retrieve precisely and use less model context. Overlap helps preserve context across boundaries.

**Why these chunk settings?** 1,800 characters with 250 overlap is a practical starting balance. I would evaluate alternatives rather than claim it is optimal.

**How does similarity work?** Embeddings are normalized; FAISS computes inner product. For normalized vectors this equals cosine similarity. We use exact search because the corpus is small.

**Why grade after search?** A high similarity score may still select a passage that does not answer the question. The LLM checks usefulness separately.

**What stops an infinite loop?** The state tracks retries and routing compares it with MAX_RETRIES. A graph recursion limit is also set. The default permits one extra search.

**What if no evidence exists?** Return insufficient_context with no sources. An empty corpus uses no model calls.

**Does grounding guarantee no hallucinations?** No. The checker is another LLM judgment. Citation-label checks are deterministic, but factual quality still needs human/labeled evaluation.

**Why SQLite and FAISS?** SQLite persists metadata and vectors simply. FAISS handles similarity search. Rebuilding the small index at startup is convenient for this local prototype.

**What happens if embedding fails halfway?** A document is committed only after its embeddings succeed. For five-guide ingestion, earlier completed guides can remain; retrying deduplicates them.

**What are the endpoints?** POST /query, POST /ingest, GET /documents and POST /feedback are required. /health and /ingest-corpus support the interface; /docs exposes Swagger.

**How did you test it?** Seventy offline Python tests cover graph branches, retries, citation rejection, actual FAISS persistence, ingestion, APIs and safe provider errors. Eight frontend tests and browser checks cover interface behavior. Model successes in automated tests use controlled doubles/HTTP fixtures. I also ran the app on Windows with my own key, indexed the five guides, tried four useful questions and an outside-corpus question, and saved feedback. Screenshots record that separate live demonstration.

**What would you improve?** Build a labeled evaluation set, measure retrieval recall and grounded answer quality, add hybrid retrieval/reranking, reduce per-chunk model latency, add streaming and harden authentication/concurrency for deployment.

**Why no conversational memory or web search?** They are optional. This version keeps each question independent and the evidence boundary limited to uploaded documentation.

## Demo practice (about five minutes)

Open the app → show five guides → ask about JSON request bodies → show the cited excerpt → expand workflow trace → ask about Mumbai weather and explain the refusal → send feedback → open /docs → show workflow.py and identify the conditional edge/retry counter.

If the live API fails, describe the failure truthfully, show the safe error and explain key/quota/model checks. Fixture-based tests are useful evidence of behavior, not proof of a successful live answer.

## Study order

First run the app. Then read main.py (routes), ingestion.py (documents), store.py (search), workflow.py (decisions), provider.py (Gemini calls). You do not need to memorize every line. Be able to explain inputs, outputs, decisions and limitations. Practise the introduction aloud, then answer the questions in your own words.
