from pipeline.minutes import generate_minutes
from pipeline.refine import format_transcript, refine_segments
from pipeline.stt import transcribe
from pipeline.verify import verify_record


def process_audio(path, glossary=None, backend="auto", on_status=None,
                  refiner_model=None, minutes_model=None):
    """Run STT -> refiner (LLM #1) -> minutes (LLM #2) -> verifier.

    refiner_model / minutes_model are optional; when None the defaults from
    .env (REFINER_MODEL / MINUTES_MODEL) are used, exactly as before.
    """
    def status(message):
        if on_status:
            on_status(message)

    refine_kwargs = {"model": refiner_model} if refiner_model else {}
    minutes_kwargs = {"model": minutes_model} if minutes_model else {}

    status("Transcribing audio")
    stt = transcribe(path, backend=backend, glossary=glossary)
    status("Refining transcript")
    refined = refine_segments(stt["segments"], glossary=glossary, **refine_kwargs)
    refined_text = format_transcript(refined["segments"], "text")
    raw_text = format_transcript(refined["segments"], "raw_text")
    status("Generating meeting record")
    minutes = generate_minutes(refined_text, **minutes_kwargs)
    record = verify_record(minutes["record"], refined["segments"])
    status("Done")
    return {
        "stt_backend": stt["backend"],
        "refiner_model": refined["model"],
        "minutes_model": minutes["model"],
        "raw_transcript": raw_text,
        "refined_transcript": refined_text,
        "segments": refined["segments"],
        "flags": refined["flags"],
        "record": record,
    }