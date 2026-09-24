"""Free local RAG: index, ask, chat, sources, remove, doctor, prepare-audio."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

from extractors import MEDIA, SUPPORTED, extract, file_hash, whisper
from data.input.local_models import Ollama
from storage import connect, history, replace_source, search

ROOT = Path(__file__).resolve().parent
PIPELINE = 'local-rag-v1:chunks900-overlap120:embedding-prefix-v1'


def load_settings(root=ROOT):
    settings = json.loads((root / 'settings.json').read_text(encoding='utf-8'))
    for key in ('cpu_threads', 'context_tokens', 'answer_tokens', 'top_k', 'history_turns', 'timeout_seconds'):
        if type(settings[key]) is not int or settings[key] <= 0:
            raise ValueError(f'{key} must be a positive integer.')
    if settings['context_tokens'] < 8192 or settings['answer_tokens'] > 1024:
        raise ValueError('This prototype requires context_tokens >=8192 and answer_tokens <=1024.')
    if settings['audio_language'] is not None and not isinstance(settings['audio_language'], str):
        raise ValueError('audio_language must be null or a language code such as en or pt.')
    return settings


def index(db, settings, client, root=ROOT, force=False):
    folder = root / 'data' / 'input'
    paths = sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED)
    if not paths:
        print('No input files. Add PDFs, text or media to data/input/.')
        return 0
    embedding_id = client.model_id(settings['embedding_model']) + ':' + PIPELINE
    errors = 0
    for path in paths:
        source = path.relative_to(folder).as_posix()
        try:
            digest = file_hash(path)
            identity = digest + embedding_id
            if path.suffix.lower() in MEDIA:
                identity += f":{settings['whisper_model']}:{settings['audio_language']}:transcript-v1"
            fingerprint = hashlib.sha256(identity.encode()).hexdigest()
            old = db.execute('SELECT fingerprint FROM sources WHERE source=?', (source,)).fetchone()
            if old and old['fingerprint'] == fingerprint and not force:
                print(f'Unchanged, skipped: {source}')
                continue
            print(f'Processing: {source}', flush=True)
            pieces = extract(path, digest, settings, root)
            if not pieces:
                raise ValueError('No text extracted. Use OCR for scanned PDFs; check audio for speech.')
            vectors = client.embed([text for _, text in pieces])
            replace_source(db, source, fingerprint, embedding_id, pieces, vectors)
            print(f'Indexed: {source} ({len(pieces)} chunks)')
        except Exception as exc:
            errors += 1
            print(f'Failed: {source}: {exc}', file=sys.stderr)
    return 1 if errors else 0


def clipped(text, maximum):
    return text.encode('utf-8')[:maximum].decode('utf-8', errors='ignore')


def context_payload(question, previous, matches):
    payload = {'question': question, 'history_not_evidence': [], 'excerpts': []}
    # Budget UTF-8 bytes conservatively for the small local model, rather than
    # assuming English-only token counts. Preserve the current question first.
    for number, row in enumerate(matches, 1):
        item = {'id': number, 'source': clipped(row['source'], 250),
                'location': row['location'], 'text': row['text']}
        payload['excerpts'].append(item)
        if len(json.dumps(payload, ensure_ascii=False).encode()) > 4200:
            payload['excerpts'].pop()
            break
    for turn in reversed(previous):
        item = {'question': clipped(turn['question'], 200), 'answer': clipped(turn['answer'], 500)}
        payload['history_not_evidence'].insert(0, item)
        if len(json.dumps(payload, ensure_ascii=False).encode()) > 5000:
            payload['history_not_evidence'].pop(0)
            break
    return payload


def answer(db, settings, client, question, session='main', source_filter=None, root=ROOT):
    question = question.strip()
    if not question or len(question.encode()) > 1000:
        raise ValueError('Enter a question of at most 1000 UTF-8 bytes.')

    identities = [r[0] for r in db.execute('SELECT DISTINCT embedding_id FROM sources')]
    if not identities:
        raise ValueError('The knowledge base is empty. Run: python app.py index')

    embedding_id = client.model_id(settings['embedding_model']) + ':' + PIPELINE
    if identities != [embedding_id]:
        raise ValueError(
            'Embedding model or pipeline changed. Run index again. Remove obsolete '
            'sources explicitly if their original files are no longer available.'
        )

    client.model_id(settings['chat_model'])
    previous = history(db, session, settings['history_turns'])

    query = question
    if previous:
        query = (
            'Previous question: ' + clipped(previous[-1]['question'], 300)
            + '\nCurrent question: ' + question
        )

    matches = search(
        db,
        client.embed([query], query=True)[0],
        embedding_id,
        settings['top_k'],
        source_filter,
    )
    if not matches:
        raise ValueError('No sources match the filter.')

    # Optional: refuse questions with no sufficiently similar document excerpt.
    # Uncomment these lines to enable it. Calibrate the threshold with your own
    # relevant and irrelevant questions; 0.45 is only an initial value.
    #
    # MIN_RELEVANCE = 0.45
    # if matches[0]['score'] < MIN_RELEVANCE:
    #     return "Não encontrei informações relevantes nos documentos para responder."

    payload = context_payload(question, previous, matches)
    if not payload['excerpts']:
        raise ValueError('Excerpts exceed the context budget; use shorter source text.')

    system = (root / 'prompt.txt').read_text(encoding='utf-8')
    if len(system.encode()) > 1800:
        raise ValueError('Keep prompt.txt within 1800 UTF-8 bytes for the current context budget.')

    response = client.chat(system, json.dumps(payload, ensure_ascii=False))
    response = sanitize_answer(response)

    sources = '\n'.join(
        f"[{r['id']}] {r['source']} — {r['location']}"
        for r in payload['excerpts']
    )

    with db:
        db.execute(
            'INSERT INTO turns(session,question,answer) VALUES (?,?,?)',
            (session, question, response),
        )

    return response + '\n\nRetrieved sources (not necessarily all cited):\n' + sources


def sanitize_answer(text):
    cleaned = (text or '').strip()
    if not cleaned:
        return cleaned
    markers = ['na perspectiva dos materiais', 'from the materials\' perspective']
    lowered = cleaned.lower()
    for marker in markers:
        index = lowered.find(marker)
        if index != -1:
            cleaned = cleaned[index:]
            break
    cleaned = re.sub(r'(?is)^(?:.*?)(?=na perspectiva dos materiais)', '', cleaned)
    cleaned = re.sub(r'(?is)\n\s*\n\s*(?:retrieved sources|fontes recuperadas|sources:?)\b.*$', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    return cleaned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('index', help='Import new/changed files; skip unchanged ones')
    ingest.add_argument('--force', action='store_true', help='Rebuild embeddings, reusing audio cache')
    for name in ('ask', 'chat'):
        cmd = commands.add_parser(name)
        if name == 'ask':
            cmd.add_argument('question')
        cmd.add_argument('--session', default='main')
        cmd.add_argument('--source', help='Filter by part of the relative source filename')
    commands.add_parser('sources', help='List indexed sources')
    remove = commands.add_parser('remove', help='Remove one exact source from the index')
    remove.add_argument('source')
    commands.add_parser('doctor', help='Check local Ollama and installed models')
    commands.add_parser('prepare-audio', help='Download/cache the optional Whisper model once')
    args = parser.parse_args()
    settings = load_settings()
    (ROOT / 'data' / 'input').mkdir(parents=True, exist_ok=True)
    if args.command == 'prepare-audio':
        print('Preparing local Whisper model. This step may download model files.', flush=True)
        model = whisper(settings, ROOT, download=True)
        del model
        print('Audio model ready. Future indexing uses cached local files only.')
        return 0
    client = Ollama(settings)
    if args.command == 'doctor':
        for key in ('embedding_model', 'chat_model'):
            print('Installed:', client.model_id(settings[key]))
        print('Local Ollama reachable. CPU execution configured. This is not an inference benchmark.')
        print('For audio, install requirements-audio.txt and run prepare-audio once.')
        return 0
    db = connect(ROOT / 'data' / 'memory.sqlite3')
    try:
        if args.command == 'index':
            return index(db, settings, client, force=args.force)
        if args.command == 'sources':
            for row in db.execute('SELECT source,COUNT(*) AS n FROM chunks GROUP BY source'):
                print(f"{row['source']} — {row['n']} chunks")
        elif args.command == 'remove':
            with db:
                count = db.execute('DELETE FROM sources WHERE source=?', (args.source,)).rowcount
            print(f'{count} source(s) removed from the index. Original files, transcript cache and chat history remain.')
        elif args.command == 'ask':
            print(answer(db, settings, client, args.question, args.session, args.source))
        else:
            print(f'Session: {args.session}. Type /exit to stop. Conversations are saved locally.')
            while True:
                question = input('\nYou: ').strip()
                if question == '/exit':
                    break
                if question:
                    try:
                        print('\nAssistant:', answer(db, settings, client, question, args.session, args.source))
                    except Exception as exc:
                        print(f'Error: {exc}', file=sys.stderr)
        return 0
    finally:
        db.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nStopped.')
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        raise SystemExit(1)
