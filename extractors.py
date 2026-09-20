"""Local PDF/text extraction and optional CPU Whisper transcription."""
import hashlib
import json
from pathlib import Path
from storage import split_text

MEDIA = {'.mp3', '.mp4', '.m4a', '.wav', '.webm', '.mov', '.ogg', '.flac', '.mpeg'}
SUPPORTED = MEDIA | {'.pdf', '.txt', '.md'}


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def whisper(settings, root, download=False):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError('Audio support is optional. Install requirements-audio.txt first.') from exc
    return WhisperModel(settings['whisper_model'], device='cpu', compute_type='int8',
                        cpu_threads=settings['cpu_threads'],
                        download_root=str(root / 'models' / 'whisper'),
                        local_files_only=not download)


def extract(path, digest, settings, root):
    if path.suffix.lower() in {'.txt', '.md'}:
        return [('text', piece) for piece in split_text(path.read_text(encoding='utf-8-sig'))]
    if path.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        result = []
        for number, page in enumerate(PdfReader(path).pages, 1):
            text = page.extract_text() or ''
            if not text.strip():
                print(f'Warning: {path.name}, PDF page {number} has no text; it may need OCR.')
            result.extend((f'PDF page {number}', piece) for piece in split_text(text))
        return result
    identity = f"{digest}:{settings['whisper_model']}:{settings['audio_language']}:transcript-v1"
    cache = root / 'data' / 'transcripts' / (hashlib.sha256(identity.encode()).hexdigest() + '.json')
    if cache.exists():
        segments = json.loads(cache.read_text(encoding='utf-8'))['segments']
    else:
        model = whisper(settings, root)
        output, _ = model.transcribe(str(path), language=settings['audio_language'],
                                     beam_size=1, vad_filter=True)
        segments = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in output if s.text.strip()]
        del model
        if not segments:
            return []
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix('.tmp')
        temporary.write_text(json.dumps({'source': path.name, 'segments': segments}, ensure_ascii=False), encoding='utf-8')
        temporary.replace(cache)
    # Group speech segments so retrieval has enough surrounding context.
    result, group = [], []
    def flush():
        if group:
            location = f"audio {group[0]['start']:.1f}s–{group[-1]['end']:.1f}s"
            result.extend((location, text) for text in split_text(' '.join(s['text'] for s in group)))
    for segment in segments:
        if group and sum(len(s['text']) for s in group) + len(segment['text']) > 900:
            flush()
            group = []
        group.append(segment)
    flush()
    return result
