# Local Content Assistant

A free, local Python RAG assistant for your PDFs, notes and audio/video files.
All code, commands, settings, prompts and documentation are in English.
The assistant answers in English by default; you can ask it to answer in Portuguese.

Example question:

> Tell me how I can manage my thoughts and vibrations to attract good things.

The prompt explains the perspective of your materials and can organize supported
practices into a routine. It does not run scientific verification. It attributes
beliefs to the materials and does not invent citations.

## What runs where

| Component | Implementation |
| --- | --- |
| Conversation | Local Qwen3 4B through Ollama |
| Document/search embeddings | Local EmbeddingGemma through Ollama |
| PDF extraction | pypdf |
| Optional audio transcription | faster-whisper, multilingual `base`, CPU INT8 |
| Sources, chunks, vectors, history | SQLite, included with Python |
| Interface | Terminal |

No OpenAI API, API keys, paid subscription, Docker, database server or dedicated
GPU are required. The app calls Ollama on your own computer, not a remote provider.
"Free" means no API fees; you still use your computer, storage and electricity.
Internet is needed initially to install software and download model files.
After setup, indexing, transcription and chat can run offline.

## Hardware defaults

Designed as a starting point for 16 GB RAM, a Intel i7 13th and integrated
graphics. The application explicitly requests CPU execution and six CPU threads.
Qwen3 4B is roughly a 2.5 GB download; EmbeddingGemma is roughly 622 MB. Runtime RAM
is higher, and model files are not included in the ZIP. Allow several GB of free
disk space for models, Python packages and your sources. No speed guarantee is made.
Close memory-heavy programs. Local responses can be slow, especially on first load.

The default 8192-token context, 1024-token answer limit and small excerpt/history
budgets keep requests modest. Model reasoning output is disabled with `think:false`.
Models unload after a request (`keep_alive: "0"`) to favor available RAM over speed.
Embedding batches contain eight texts; this conservative choice adds load overhead.

## 1. Install Python and Ollama

Use 64-bit Python 3.11 - 3.13: https://www.python.org/downloads/
Install the desktop Ollama application: https://ollama.com/download
Start Ollama and leave it running. If not using the desktop app, run `ollama serve`
in a separate terminal. Do not start a second server if one is already running.

For explicitly local-only Ollama operation on Windows, set the following once in
PowerShell, then fully quit and restart Ollama so it receives the setting:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "User")
```

On Linux/macOS, set `OLLAMA_NO_CLOUD=1` in the environment of the Ollama server
(service environment when running as a service). Local model downloads still
require internet. This project rejects cloud model names and remote server URLs.

Download the two local models:

```powershell
ollama pull qwen3:4b
ollama pull embeddinggemma:latest
ollama list
```

Use a recent Ollama version with `/api/embed`, `think:false` and EmbeddingGemma support.

## 2. Install the project

Extract this ZIP. Open PowerShell in the `local-content-assistant` folder containing
`app.py`. You do not need to activate the virtual environment or change PowerShell
execution policy:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py doctor
```

Linux/macOS equivalents:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py doctor
```

For subsequent examples, replace `.\.venv\Scripts\python.exe` with
`.venv/bin/python` on Linux/macOS.

## 3. Try the included demonstration notes

The sample is explicitly marked as original demonstration text, not a quotation
from The Secret or another book. It is outside the input folder so it does not
enter your knowledge base unless you choose to copy it:

```powershell
Copy-Item examples/sample-notes.txt data/input/sample-notes.txt
.\.venv\Scripts\python.exe app.py index
.\.venv\Scripts\python.exe app.py ask "What routine do these notes suggest for organizing my thoughts?"
```

This first real inference is also your hardware smoke test. Afterward, to exclude
the sample from future answers, move it outside `data/input/` and run:

```powershell
.\.venv\Scripts\python.exe app.py remove "sample-notes.txt"
```

## 4. Add your books and notes

Place PDFs, UTF-8 TXT or MD files under `data/input/`. Subfolders work:

Run:

```powershell
.\.venv\Scripts\python.exe app.py index
.\.venv\Scripts\python.exe app.py sources
```

Text is extracted per PDF page and split into overlapping chunks. Scanned/image-only
pages require OCR outside this prototype. Blank pages produce warnings. Complex
columns/tables may extract poorly. Page citations refer to the position in the PDF,
not necessarily the printed page number. Import only materials you can access.

## 5. Add Reels using local transcription (optional)

Provide a downloaded video/audio file, or use an existing transcript as TXT.
This project does NOT log into Instagram or download content from Reel URLs.
It transcribes speech, not visual demonstrations or text displayed on the screen.

For audio/video support, install the optional packages and prepare the model once
while connected to the internet:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-audio.txt
.\.venv\Scripts\python.exe app.py prepare-audio
```

Now copy a Reel MP4 into `data/input/reels/` and run `index` again. MP3, MP4, M4A,
WAV, WEBM, MOV, OGG, FLAC and MPEG are recognized; decoding depends on the file's
codec. faster-whisper uses PyAV's bundled FFmpeg libraries, so a separate FFmpeg
installation is normally unnecessary. This is local transcription: the previous
project's cloud upload size limit no longer applies, but long media takes time.

Transcripts are cached under `data/transcripts/` with approximate segment time
ranges. These ranges identify groups of speech, not exact word-level citations.
Language detection is automatic. For predominantly Portuguese content, set
`"audio_language": "pt"` in `settings.json`; use `"en"` for English or `null` for auto.
Do not use the English-only `base.en` model for Portuguese audio.

Normal indexing sets `local_files_only=True` for Whisper. If its cache is missing,
it fails instead of silently downloading a model; run `prepare-audio` to fix that.
Changing the Whisper model requires running `prepare-audio` again before indexing.

## 6. Ask questions or continue a conversation

```powershell
.\.venv\Scripts\python.exe app.py ask "Tell me how I can manage my thoughts and vibrations to attract good things."
.\.venv\Scripts\python.exe app.py chat --session abundance
```

In chat, try:

- Which practices do the materials describe?
- Organize those into a morning and evening routine.
- Which source supports each step?
- Where do the authors disagree?

Type `/exit` to finish. Use the same session name to resume. Another name starts
a separate history. `ask` also accepts `--session`; the default is `main`.

Restrict the sources:

```powershell
.\.venv\Scripts\python.exe app.py ask "Which practices does this author recommend?" --source "xyz.pdf"
```

You can ask in Portuguese and explicitly request a Portuguese answer. Source files
can be in English or Portuguese; they do not need to be translated before importing.

## How new content is added

This is RAG indexing, NOT training the language model's weights.

| Change | Next `index` run |
| --- | --- |
| New file | Extract/transcribe, embed and save it |
| Unchanged file | Skip extraction, transcription and embeddings |
| Changed file at the same path | Reprocess that entire file and replace its old chunks |
| Deleted file | Keep its indexed data until explicitly removed |
| Renamed file | Treat as a new source; explicitly remove the old source |
| Changed chat model or prompt | No document reindex required |
| Changed embedding model or digest | Reindex all source files; mixed bases cannot answer |
| Changed Whisper model/language | Reprocess affected media using a separate cache identity |

The application hashes file bytes, processing settings and the embedding model
digest. Unchanged files still require reading their bytes and contacting the local
Ollama server for the installed model identity, but no inference is run for them.
Updates are transactional: extraction or embedding failure preserves the previous
indexed version. It processes files independently and reports failures with a
nonzero exit code; successful files remain saved.

To remove one source, copy its EXACT relative name from `sources`:

```powershell
.\.venv\Scripts\python.exe app.py remove "books/old-book.pdf"
```

Removal deletes that source and its chunks only. Original files, transcript cache
and chat history remain. Move the original outside the input folder if you do not
want the next `index` to add it again. Old conversations may still mention removed
content: start a new session when that matters.

`index --force` regenerates embeddings for all input files, reusing cached
transcripts. To deliberately redo an existing transcript, move its cache JSON out
of `data/transcripts/` and run `index --force`. Whisper model updates under the same
name are not automatically fingerprinted; use this procedure if needed.

## What persists and what enters each answer

`data/memory.sqlite3` saves sources, text chunks, vectors and all successful chat
turns. The model files stay on disk too. Restarting loads these files; no retraining
or reindexing is required. Chat responses are never automatically added as documents.

Each question retrieves up to four similar excerpts. At most the latest two turns
are considered for follow-ups. UTF-8 byte budgets may reduce excerpts/history
further; saved history is not unlimited model context. Question size is limited to
1000 UTF-8 bytes. The chat prompt is limited to 1800 bytes, and its JSON data to
5000 bytes. Excerpts have priority over old conversation text.

Source IDs [1], [2], etc. refer to the excerpts included in that response. The
footer lists all provided sources, not necessarily all cited ones. No automated
claim/citation verifier is included. A small local model can still misunderstand,
hallucinate, fail to follow the prompt, or retrieve irrelevant excerpts. The prompt
asks it to acknowledge missing information, but that is not a guarantee.

## Configuration and files

| File | Purpose |
| --- | --- |
| `app.py` | CLI, indexing, chat orchestration and context budgeting |
| `local_models.py` | Local Ollama client; no provider credentials |
| `extractors.py` | PDF/text extraction and cached local transcription |
| `storage.py` | SQLite and linear cosine search |
| `settings.json` | Models, CPU threads and request limits |
| `prompt.txt` | Editable assistant instructions, read on each question |
| `requirements.txt` | Minimal PDF dependency |
| `requirements-audio.txt` | Optional transcription dependencies |
| `examples/sample-notes.txt` | Clearly labeled demonstration content |
| `tests/test_project.py` | Automated tests without model downloads |
| `data/input/` | Your source files |
| `data/transcripts/` | Generated transcript JSON cache |
| `data/memory.sqlite3` | Generated knowledge/history database |
| `models/whisper/` | Generated local Whisper cache |

Keep the default settings for the first test. You may increase `timeout_seconds`
if CPU responses take longer. `base` is a starting point for Whisper; `small` may
improve transcription but uses more resources. The schema requires context_tokens
of at least 8192 and answer_tokens of at most 1024 to preserve conservative budgets.
Changing generation models may require compatible support for `think:false`.

This is a new local edition with a separate schema and English paths. Do not copy
the old API-based SQLite database into it. Copy your original files into `data/input/`
and index once with the local embedding model. Old chat history is not migrated.

## Backup and privacy

Close the app before copying `data/`, `settings.json` and `prompt.txt` for backup.
Back up `models/whisper/` and Ollama's own model directory if you want to restore
without downloading models. Ollama manages its model storage separately from this
project. SQLite and transcript files are plain local files, not encrypted.

Normal application requests use only a loopback Ollama URL and cached Whisper
files. Dependencies and model downloads contact their distributors during setup.
The app does not implement telemetry, upload documents, or call a cloud fallback.
Keep Ollama bound locally and configure its no-cloud setting as described above.
Run one indexing/chat process at a time for this small prototype.

## Tests and current validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover incremental imports, restart persistence, atomic failed updates,
embedding-model changes, sessions, source filtering/removal, UTF-8 context budgets,
local CPU request settings, cached audio extraction and scanned-PDF handling.
Models are simulated in these tests; no downloads or paid calls occur.
The test suite and CLI checks were run during preparation. Actual Qwen/Whisper
inference and performance on your laptop were not tested here. Use the demonstration
notes and one short Reel as your initial real-world validation.

Dependency ranges are provided, not a machine-specific lock. After installation
works on your computer, you may freeze the environment with:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > requirements-lock.txt
```

## Troubleshooting

| Problem | Action |
| --- | --- |
| Cannot reach Ollama | Start the desktop app or `ollama serve` |
| Model is not installed | Run the suggested `ollama pull` command |
| Audio support missing | Install `requirements-audio.txt` |
| Whisper cache/model missing | Run `prepare-audio` while online |
| Windows audio dependency DLL error | Check 64-bit Python and the Microsoft Visual C++ runtime required by CTranslate2 |
| No text extracted from PDF | Apply OCR externally; import searchable PDF |
| Model/pipeline changed | Run `index`; remove stale sources whose files are unavailable |
| Long pauses | Expected with CPU inference; close other apps or increase timeout |
| Output limit reached | Ask a narrower question or increase answer_tokens up to 1024 |
| Bad or unrelated answer | Narrow the question, filter a source, inspect its text/transcript |
| Source removal seems ineffective | Start a new session; old chat turns are deliberately preserved |

## Official references

- [Ollama download](https://ollama.com/download)
- [Qwen3 4B](https://ollama.com/library/qwen3:4b)
- [EmbeddingGemma](https://ollama.com/library/embeddinggemma)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama embeddings API](https://docs.ollama.com/api/embed)
- [Ollama FAQ and local-only mode](https://docs.ollama.com/faq)
- [EmbeddingGemma retrieval prefixes](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers)
- [faster-whisper installation and CPU usage](https://github.com/SYSTRAN/faster-whisper)

The project is delivered as one archive so code, settings, prompt and instructions
stay together. Third-party software and model licenses remain their own.
