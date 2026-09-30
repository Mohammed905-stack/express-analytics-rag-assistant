# Start here — one project

This is the Express Analytics AI/ML intern assignment: a technical documentation assistant. The five FastAPI guides are its knowledge sources, not five projects.

## Windows: open and run

1. Download the ZIP. Right-click it → **Extract All**. Choose your Desktop and click Extract.
2. Open the extracted `express-analytics-assignment` folder. Work in this folder, not inside the ZIP preview.
3. If Python is not installed, install Python 3.12 from https://www.python.org/downloads/ (include the Python launcher and Tcl/Tk). Restart the folder after installation.
4. Double-click **START.cmd**. A key window appears if no key is saved. Click its entry box, press Ctrl+V once to paste your Gemini API key, optionally show it to check it, then save. Do not share your key.
5. Wait for the first dependency installation. Keep the terminal open. The app opens at http://127.0.0.1:8000.
6. Click **Index the five guides** once. Indexing makes real embedding API calls and can take time. Wait until five guides appear.
7. Click a sample question and **Find an answer**. Expand the sources and workflow trace. Try the outside-the-guides question to demonstrate refusal.
8. To stop, press Ctrl+C in the terminal. Closing the terminal also stops the local app. Start again with START.cmd; indexed guides persist.

If the key is wrong: stop the server, double-click **SETUP_KEY.cmd**, replace the key, then START.cmd. Never paste a key into the question box. If you lose the folder, search Windows for START.cmd or return to Desktop. OPEN_PROJECT_FOLDER.cmd opens this exact project folder.

## If something fails

- Failed download: download the ZIP again before extracting; a browser preview is not extraction.
- 'Python launcher not found': install Python with its launcher. Automated tests used Python 3.12 on Linux; the candidate also ran the app on Windows. A new machine still needs setup.
- A missing-key warning after changing a key: stop and restart START.cmd.
- 503 / quota / unavailable model: check your Gemini key, API access and quota. A saved key does not prove it is valid. Adjust GEMINI_MODEL in .env if your account cannot access the configured model.
- Port 8000 occupied: stop the previous app terminal and start once.
- Do not move files out of this folder or replace individual source files.

Before submission: follow GITHUB_SUBMISSION.md. After a successful live demo, double-click CAPTURE_EVIDENCE.cmd to record actual answers. Read UNDERSTAND_AND_INTERVIEW.md after the app works.

## Already running an earlier copy?

The final submission ZIP is a clean source package. It excludes your local key, installed dependencies and saved index. Keep your working folder for the demo; do not extract the submission package over it. The final source includes the citation fixes and defaults to gemini-3.5-flash-lite. A new installation needs its own Gemini key and indexing.
