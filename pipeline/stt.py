import os
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

SUPPORTED = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".webm", ".aac", ".aiff"}
_whisper = None


class AudioError(Exception):
    pass


def prepare_audio(path):
    if not os.path.exists(path):
        raise AudioError("File not found.")
    if os.path.getsize(path) == 0:
        raise AudioError("The uploaded file is empty.")
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED:
        raise AudioError(f"Unsupported file type: {ext or 'unknown'}")
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", path, "-ar", "16000", "-ac", "1", out],
        capture_output=True,
    )
    if r.returncode != 0 or os.path.getsize(out) < 2000:
        raise AudioError("The audio file is unreadable or contains no audio.")
    return out


def normalize(segments, backend):
    return {
        "backend": backend,
        "text": " ".join(s["text"] for s in segments).strip(),
        "segments": segments,
    }


def transcribe_whisper(path, model_size="small"):
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(model_size, device="cpu", compute_type="int8")
    import wave
    import numpy as np
    with wave.open(path, "rb") as w:
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    segs, _ = _whisper.transcribe(audio, vad_filter=True, language="en")
    segments = [
        {"start": s.start, "end": s.end, "speaker": None, "text": s.text.strip()}
        for s in segs
    ]
    if not segments:
        raise AudioError("No speech was detected in the recording.")
    return normalize(segments, "faster-whisper")


def transcribe_assemblyai(path, glossary=None):
    import assemblyai as aai
    key = os.getenv("ASSEMBLYAI_API_KEY")
    if not key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not set")
    aai.settings.api_key = key
    kwargs = {"speaker_labels": True, "language_code": "en"}
    if glossary:
        kwargs["word_boost"] = glossary
        kwargs["boost_param"] = "high"
    t = aai.Transcriber().transcribe(path, aai.TranscriptionConfig(**kwargs))
    if t.status == aai.TranscriptStatus.error:
        raise RuntimeError(t.error)
    if not t.text:
        raise AudioError("No speech was detected in the recording.")
    if t.utterances:
        segments = [
            {"start": u.start / 1000, "end": u.end / 1000, "speaker": u.speaker, "text": u.text}
            for u in t.utterances
        ]
    else:
        segments = [{"start": 0.0, "end": 0.0, "speaker": None, "text": t.text}]
    return normalize(segments, "assemblyai")


def transcribe(path, backend="auto", glossary=None):
    wav = prepare_audio(path)
    if backend in ("auto", "assemblyai"):
        try:
            return transcribe_assemblyai(wav, glossary)
        except AudioError:
            raise
        except Exception:
            if backend == "assemblyai":
                raise
    return transcribe_whisper(wav)
