#!/usr/bin/env python3
"""
yt_transcribe.py — YouTube link -> ElevenLabs Scribe transcript -> .txt

Usage:
  python yt_transcribe.py "https://youtu.be/VIDEO_ID"
  python yt_transcribe.py                      # prompts for a link
  python yt_transcribe.py URL --diarize        # label speakers + timestamps
  python yt_transcribe.py URL --language eng   # skip auto language detection
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import yt_dlp
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

MODEL_ID = "scribe_v2"


def download_audio(url: str, out_dir: Path):
    """Download only the audio stream. No re-encoding, so ffmpeg isn't required."""
    opts = {
        # Prefer m4a (small, universally accepted); fall back to any audio stream.
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,   # a link like ...&list=... grabs just the one video
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    return path, info


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]+', "", name).strip()
    return cleaned[:120] or "transcript"


def fmt_time(seconds: float) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_diarized(result) -> str:
    """Group consecutive words by speaker into '[hh:mm:ss] Speaker N: ...' blocks."""
    blocks, current = [], None
    for w in result.words or []:
        speaker = getattr(w, "speaker_id", None) or "speaker_0"
        if current is None or speaker != current["speaker"]:
            if current:
                blocks.append(current)
            current = {"speaker": speaker, "start": w.start, "text": ""}
        current["text"] += w.text  # 'spacing' tokens carry the spaces
    if current:
        blocks.append(current)

    lines = []
    for b in blocks:
        num = b["speaker"].split("_")[-1]
        label = f"Speaker {int(num) + 1}" if num.isdigit() else b["speaker"]
        lines.append(f"[{fmt_time(b['start'])}] {label}: {b['text'].strip()}")
    return "\n\n".join(lines)


def transcribe(client: ElevenLabs, audio_path: Path, diarize: bool, language: str | None):
    with open(audio_path, "rb") as f:
        return client.speech_to_text.convert(
            file=f,
            model_id=MODEL_ID,
            diarize=diarize,
            tag_audio_events=True,       # (laughter), (applause), etc.
            language_code=language,      # None = auto-detect
        )


def main():
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video with ElevenLabs.")
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument("--diarize", action="store_true", help="Label speakers with timestamps")
    parser.add_argument("--language", help="Language code, e.g. eng, spa (default: auto)")
    parser.add_argument("--out", help="Output .txt path (default: <video title>.txt)")
    parser.add_argument("--keep-audio", action="store_true", help="Keep the downloaded audio file")
    args = parser.parse_args()

    load_dotenv(Path(__file__).with_name(".env.local"))
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("Missing ELEVENLABS_API_KEY (set it in .env or your environment).")

    url = args.url or input("YouTube URL: ").strip()
    if not url:
        sys.exit("No URL given.")

    client = ElevenLabs(api_key=api_key)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        print("Downloading audio…")
        try:
            audio_path, info = download_audio(url, tmp_dir)
        except yt_dlp.utils.DownloadError as e:
            sys.exit(f"Download failed: {e}")
        title = info.get("title", info.get("id", "transcript"))
        print(f"  → {title}  ({audio_path.stat().st_size / 1e6:.1f} MB)")

        print(f"Transcribing with {MODEL_ID}…")
        try:
            result = transcribe(client, audio_path, args.diarize, args.language)
        except Exception as e:
            sys.exit(f"Transcription failed: {e}")

        body = format_diarized(result) if args.diarize else result.text.strip()

        out_path = Path(args.out) if args.out else Path(f"{safe_filename(title)}.txt")
        header = (
            f"Title: {title}\n"
            f"URL: {info.get('webpage_url', url)}\n"
            f"Language: {getattr(result, 'language_code', 'unknown')}\n"
            f"{'-' * 60}\n\n"
        )
        out_path.write_text(header + body + "\n", encoding="utf-8")
        print(f"Saved transcript → {out_path.resolve()}")

        if args.keep_audio:
            kept = Path.cwd() / audio_path.name
            audio_path.replace(kept)
            print(f"Kept audio → {kept}")


if __name__ == "__main__":
    main()