# Local Content Assistant

A local Python RAG assistant for PDFs, notes, and audio/video files of any subject.
All project files are in English, but the assistant can answer in Portuguese.

Example:

> Tell me how I can manage my thoughts to keep positivity.

The prompt explains the perspective of the imported materials and can organize supported practices into a routine. It does not verify claims scientifically and does not invent citations.

## What runs where

| Component | Implementation |
| --- | --- |
| Conversation | Local Qwen3 4B via Ollama |
| Embeddings | Local EmbeddingGemma via Ollama |
| PDF extraction | pypdf |
| Optional transcription | faster-whisper, multilingual base, CPU INT8 |
| Storage | SQLite |
| Interface | Terminal + desktop GUI (Tkinter) |

No OpenAI API, API keys, paid service, Docker, database server, or dedicated GPU is required. The app uses Ollama locally on your machine.

## Desktop interface

The project also includes a simple desktop interface built with Tkinter for chatting and indexing without the terminal.

Windows:

```powershell
.\.venv\Scripts\python.exe gui.py
```

Or run the helper script:

```powershell
.\open-ui.bat
```

The GUI lets you:

- choose or create a chat session
- send questions to the local assistant
- index files from inside the app
- review previous turns from the selected session

The underlying logic still uses the same local Ollama + SQLite pipeline as the terminal app.

## Hardware

Designed for ~16 GB RAM and a Intel i7 with integrated graphics. The app runs on CPU with four threads by default. qwen3:4b-instruct is about 2.5 GB; EmbeddingGemma is about 622 MB. Allow several GB of free disk space for models, packages, and source files.

The default context and budget settings keep requests modest. `think:false` is used, models unload after each request, and embedding batches are small.

## 1. Install Python and Ollama

Use Python 3.11-3.13: https://www.python.org/downloads/
Install Ollama: https://ollama.com/download
Start Ollama and leave it running. If not using the desktop app, run `ollama serve` in another terminal.

For local-only Ollama on Windows:

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_NO_CLOUD", "1", "User")
```

Then restart Ollama.

Download the models:

```powershell
ollama pull qwen3:4b
ollama pull embeddinggemma:latest
ollama list
```

## 2. Install the project

Open PowerShell in the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py doctor
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py doctor
```

## 3. Try the demo notes

Sample files are outside `data/input/` by default, so they are not indexed unless copied in:

```powershell
Copy-Item examples/sample-notes.txt data/input/sample-notes.txt
.\.venv\Scripts\python.exe app.py index
.\.venv\Scripts\python.exe app.py ask "What routine do these notes suggest for organizing my thoughts?"
```

To exclude it later:

```powershell
.\.venv\Scripts\python.exe app.py remove "sample-notes.txt"
```

## 4. Add books and notes

Place PDFs, UTF-8 TXT, or MD files under `data/input/`. Subfolders work.

```powershell
.\.venv\Scripts\python.exe app.py index
.\.venv\Scripts\python.exe app.py sources
```

Text is extracted per PDF page and split into overlapping chunks. Scanned or image-only pages need OCR outside the app. Blank pages can warn. Complex columns and tables may extract poorly. Citation positions are based on the PDF structure, not always the printed page number.

## 5. Optional audio/video transcription

Install optional packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-audio.txt
.\.venv\Scripts\python.exe app.py prepare-audio
```

Copy an MP3, MP4, M4A, WAV, WEBM, MOV, OGG, FLAC, or MPEG file into `data/input/reels/` and run `index` again. Transcripts are saved under `data/transcripts/` with approximate time ranges.

For Portuguese audio, set `"audio_language": "pt"` in `settings.json`; use `"en"` for English or `null` for auto detection. Do not use the English-only `base.en` model for Portuguese content.

## 6. Ask questions or continue a chat

```powershell
.\.venv\Scripts\python.exe app.py ask "Tell me how I can manage my thoughts and vibrations to attract good things."
.\.venv\Scripts\python.exe app.py chat --session abundance
```

Try prompts such as:

- Which practices do the materials describe?
- Organize them into a morning and evening routine.
- Which source supports each step?
- Where do the authors disagree?

Type `/exit` to finish. Use the same session name to resume later. `ask` also accepts `--session`; the default is `main`.

To restrict sources:

```powershell
.\.venv\Scripts\python.exe app.py ask "Which practices does this author recommend?" --source "xyz.pdf"
```

You can ask in Portuguese and explicitly request a Portuguese answer.

## How indexing works

This is RAG indexing, not model training.

| Change | Next `index` run |
| --- | --- |
| New file | Extract/transcribe, embed, and save |
| Unchanged file | Skip extraction and embedding |
| Modified file | Reprocess and replace old chunks |
| Deleted file | Keep indexed data until manually removed |
| Renamed file | Treat as a new source |
| Changed model or prompt | No reindex required |
| Changed embedding model or digest | Reindex all sources |
| Changed Whisper model or language | Reprocess affected media |

The app hashes file bytes, settings, and model digest. Failed extraction or embedding keeps the prior indexed version. Successful files remain saved. To remove one source:

```powershell
.\.venv\Scripts\python.exe app.py remove "books/ancient-book.pdf"
```

`index --force` regenerates embeddings for all sources while reusing cached transcripts.

## What persists

`data/memory.sqlite3` stores sources, chunks, vectors, and successful chat turns. Model files stay on disk. Restarting loads previous state without retraining.

Each question retrieves up to four similar excerpts. The last two turns are used for follow-ups when relevant. Question size is limited to 1000 UTF-8 bytes; chat context and JSON payload are also limited. Excerpts take priority over older conversation text.

Source IDs such as [1], [2], etc. refer to the excerpts included in a response. The footer lists provided sources, not necessarily all cited ones.

This app may still misunderstand, hallucinate, fail to follow instructions, or retrieve irrelevant excerpts. It asks to acknowledge missing information, but that is not a guarantee.

### Autor

* **Paulo Otávio Ferreira dos Santos** - [LinkedIn](https://www.linkedin.com/in/paulo-otavio-ferreira/)
