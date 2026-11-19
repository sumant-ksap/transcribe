"""Batch transcription from the command line.

Examples
--------
  python transcribe_cli.py call.mp3                      # Hinglish (code-mix), prints text
  python transcribe_cli.py call.mp3 --style hindi        # pure Devanagari
  python transcribe_cli.py recordings/ --style both --formats txt srt json --out transcripts/
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from maya_tx import STYLES, MayaTranscriber, load_audio, to_json, to_srt, to_txt, to_vtt
from maya_tx.engine import iter_audio_files

WRITERS = {"txt": to_txt, "srt": to_srt, "vtt": to_vtt}


def main() -> int:
    ap = argparse.ArgumentParser(description="Hindi / Hinglish transcription with Maya Transcribe")
    ap.add_argument("inputs", nargs="+", help="audio/video files or folders")
    ap.add_argument("--style", choices=[*STYLES, "both"], default="hinglish")
    ap.add_argument("--formats", nargs="+", choices=[*WRITERS, "json"], default=["txt"])
    ap.add_argument("--out", help="output folder (default: print to console)")
    ap.add_argument("--device", choices=["cpu", "cuda", "mps"], help="force a device")
    ap.add_argument("--batch-size", type=int, default=4)
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Devanagari on Windows consoles
    except Exception:
        pass

    files = iter_audio_files(args.inputs)
    if not files:
        print("No audio files found.", file=sys.stderr)
        return 1

    styles = list(STYLES) if args.style == "both" else [args.style]
    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    tx = MayaTranscriber(device=args.device)
    print(f"Loading model ({tx.model_id}) ...", file=sys.stderr)
    tx.load()
    print(f"Running on {tx.device}", file=sys.stderr)

    for path in files:
        audio = load_audio(path)
        dur = len(audio) / 16_000
        for style in styles:
            t0 = time.time()
            segs = tx.transcribe(audio, style=style, batch_size=args.batch_size)
            took = time.time() - t0
            print(f"\n== {Path(path).name} [{STYLES[style]['label']}] {dur:.1f}s audio in {took:.1f}s ==", file=sys.stderr)
            if any(s.truncated for s in segs):
                print("  ! some segments hit the token limit and may be cut off", file=sys.stderr)
            if not out_dir:
                print(to_txt(segs, with_times=len(segs) > 1))
                continue
            stem = Path(path).stem + (f".{style}" if len(styles) > 1 else "")
            for fmt in args.formats:
                text = (
                    to_json(segs, file=Path(path).name, style=style, model=tx.model_id, duration=dur)
                    if fmt == "json"
                    else WRITERS[fmt](segs)
                )
                dest = out_dir / f"{stem}.{fmt}"
                dest.write_text(text, encoding="utf-8")
                print(f"  -> {dest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
