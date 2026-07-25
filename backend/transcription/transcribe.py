import whisper
from pathlib import Path


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    language: str | None = None
) -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Args:
        audio_path (str): Path to audio file (.mp3/.wav)
        model_size (str): tiny | base | small | medium | large
        language (str | None): Language code (e.g., 'en') or None for auto-detect

    Returns:
        dict: Transcript text and detected language
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = whisper.load_model(model_size)

    result = model.transcribe(
        str(audio_path),
        language=language
    )

    return {
        "transcript": result["text"].strip(),
        "language": result.get("language") or language or "unknown",
    }


if __name__ == "__main__":
    # Simple manual test
    sample_audio = "data/audio/sample.ogg"
    print(transcribe_audio(sample_audio))
