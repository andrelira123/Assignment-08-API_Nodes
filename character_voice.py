#!/usr/bin/env python3
"""
character_voice.py: describe a character's voice, then make them say things.

  python character_voice.py                     # interactive prompts
  python character_voice.py --say "Hello there." --sound "A gravelly old pirate, slow and amused."
  python character_voice.py --say "Back again." --character "Captain"   # reuse a saved voice
"""
import argparse
import base64
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

HERE = Path(__file__).parent
VOICES_FILE = HERE / "characters.json"   # character name -> {voice_id, description}
OUT_DIR = HERE / "output"

DESIGN_MODEL = "eleven_multilingual_ttv_v2"
TTS_MODEL = "eleven_multilingual_v2"
MIN_PREVIEW_CHARS = 100   # voice design needs a preview script of at least ~100 chars


# ---------- storage ----------
def load_characters() -> dict:
    return json.loads(VOICES_FILE.read_text()) if VOICES_FILE.exists() else {}


def save_character(name: str, voice_id: str, description: str):
    chars = load_characters()
    chars[name] = {"voice_id": voice_id, "description": description}
    VOICES_FILE.write_text(json.dumps(chars, indent=2))


def slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")[:40] or "voice"


# ---------- voice design ----------
def design_voice(client: ElevenLabs, description: str, line: str, name: str) -> tuple[str, bool]:
    """
    Generate 3 preview voices, let the user pick one, and save it.
    Returns (voice_id, line_already_spoken).
    """
    # If the line is long enough, the previews speak *your* line, so picking a
    # preview also gives you the finished audio. Otherwise ElevenLabs writes a
    # sample script and we generate your line afterward.
    use_line = len(line) >= MIN_PREVIEW_CHARS
    print("Designing voices…")
    result = client.text_to_voice.design(
        model_id=DESIGN_MODEL,
        voice_description=description,
        text=line if use_line else None,
        auto_generate_text=not use_line,
    )

    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    preview_paths = []
    for i, p in enumerate(result.previews, 1):
        path = OUT_DIR / f"{slug(name)}_option{i}_{stamp}.mp3"
        path.write_bytes(base64.b64decode(p.audio_base_64))
        preview_paths.append(path)
        print(f"  {i}: {path.name}")

    while True:
        pick = input(f"Listen in {OUT_DIR.name}/, then choose 1-{len(result.previews)} "
                     "(r = regenerate, q = quit): ").strip().lower()
        if pick == "q":
            sys.exit("No voice saved.")
        if pick == "r":
            for path in preview_paths:
                path.unlink(missing_ok=True)
            return design_voice(client, description, line, name)
        if pick.isdigit() and 1 <= int(pick) <= len(result.previews):
            break

    idx = int(pick) - 1
    chosen = result.previews[idx]
    voice = client.text_to_voice.create(
        voice_name=name,
        voice_description=description,
        generated_voice_id=chosen.generated_voice_id,
    )
    save_character(name, voice.voice_id, description)
    print(f"Saved character '{name}'.")

    # Delete the options you didn't pick; keep the chosen one if it spoke your line.
    for i, path in enumerate(preview_paths):
        if i != idx or not use_line:
            path.unlink(missing_ok=True)
    if use_line:
        print(f"Your line → {preview_paths[idx]}")
    return voice.voice_id, use_line


# ---------- speech ----------
def speak(client: ElevenLabs, voice_id: str, line: str, name: str) -> Path:
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=line,
        model_id=TTS_MODEL,
        output_format="mp3_44100_128",
    )
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{slug(name)}_{datetime.now():%Y%m%d_%H%M%S}.mp3"
    with open(out, "wb") as f:
        for chunk in audio:   # convert() streams back byte chunks
            f.write(chunk)
    return out


# ---------- main ----------
def main():
    p = argparse.ArgumentParser(description="Make a described character say a line.")
    p.add_argument("--say", help="What the character should say")
    p.add_argument("--sound", help="How the character should sound (voice description)")
    p.add_argument("--character", help="Character name (reuses a saved voice if it exists)")
    args = p.parse_args()

    load_dotenv(HERE / ".env.local")
    load_dotenv(HERE / ".env")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("Missing ELEVENLABS_API_KEY in .env.local")
    client = ElevenLabs(api_key=api_key)

    chars = load_characters()

    # 1) What should they say?
    line = args.say or input("What should the character say?\n> ").strip()
    if not line:
        sys.exit("Nothing to say.")

    # 2) Who's saying it / how should they sound?
    name = args.character
    if not name and not args.sound and chars:
        print("Saved characters: " + ", ".join(chars))
        name = input("Character name (existing to reuse, or new): ").strip()

    if name in chars and not args.sound:
        voice_id = chars[name]["voice_id"]
        print(f"Using saved voice for '{name}' ({chars[name]['description']})")
        already_spoken = False
    else:
        description = args.sound or input(
            "How should they sound? (age, accent, pitch, pace, mood)\n> ").strip()
        if not description:
            sys.exit("Need a voice description.")
        name = name or input("Name this character: ").strip() or "Character"
        voice_id, already_spoken = design_voice(client, description, line, name)

    if not already_spoken:
        print("Generating speech…")
        out = speak(client, voice_id, line, name)
        print(f"Your line → {out}")


if __name__ == "__main__":
    main()