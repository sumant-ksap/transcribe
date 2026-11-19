"""Gradio demo: Hindi & Hinglish transcript writing with Maya Transcribe.

Run:  python app.py            (opens http://127.0.0.1:7860)
      python app.py --share    (temporary public link to show the team)
"""

from __future__ import annotations

import argparse
import tempfile
import time
import zipfile
from pathlib import Path

import gradio as gr

from maya_tx import STYLES, MayaTranscriber, load_audio, to_json, to_srt, to_txt, to_vtt
from maya_tx.engine import SAMPLE_RATE

TX = MayaTranscriber()
OUT = Path(tempfile.mkdtemp(prefix="maya_tx_"))

STYLE_CHOICES = {
    "Hinglish: Hindi + English code-mix": ["hinglish"],
    "Hindi: Devanagari only": ["hindi"],
    "Both, side by side": ["hindi", "hinglish"],
}

GUIDE_MD = Path(__file__).with_name("TRANSCRIPT_GUIDE.md")


def _write(stem: str, style: str, segs, meta: dict) -> list[str]:
    files = []
    for ext, text in {
        "txt": to_txt(segs),
        "srt": to_srt(segs),
        "vtt": to_vtt(segs),
        "json": to_json(segs, style=style, **meta),
    }.items():
        p = OUT / f"{stem}.{style}.{ext}"
        p.write_text(text, encoding="utf-8")
        files.append(str(p))
    return files


def _table(segs):
    return [[f"{s.start:.1f}", f"{s.end:.1f}", s.text] for s in segs]


def _merge_tables(hindi_rows, hinglish_rows):
    """Both styles use the same audio chunks, so align rows on (start, end)."""
    merged: dict[tuple, list[str]] = {}
    for rows, col in ((hindi_rows, 0), (hinglish_rows, 1)):
        for start, end, text in rows:
            merged.setdefault((start, end), ["", ""])[col] = text
    keys = sorted(merged, key=lambda k: float(k[0]))
    return [[i, s, e, *merged[(s, e)]] for i, (s, e) in enumerate(keys, 1)]


def run_single(audio_path, choice, progress=gr.Progress()):
    if not audio_path:
        raise gr.Error("Upload or record some audio first.")
    progress(0, desc="Loading model (first run downloads ~1.6 GB) ...")
    TX.load()
    audio = load_audio(audio_path)
    dur = len(audio) / SAMPLE_RATE
    stem = Path(audio_path).stem

    result = {"hindi": ("", [], []), "hinglish": ("", [], [])}
    timings = []
    for style in STYLE_CHOICES[choice]:
        t0 = time.time()
        segs = TX.transcribe(
            audio,
            style=style,
            progress=lambda d, n, s=style: progress(d / n, desc=f"{STYLES[s]['label']}: chunk {d}/{n}"),
        )
        took = time.time() - t0
        timings.append(f"**{STYLES[style]['label']}**: {took:.1f}s for {dur:.1f}s audio ({len(segs)} segments)")
        if any(s.truncated for s in segs):
            timings.append("⚠️ some segments hit the token limit, so please check the end of those lines")
        files = _write(stem, style, segs, {"file": Path(audio_path).name, "model": TX.model_id, "duration": dur})
        result[style] = (to_txt(segs).strip(), _table(segs), files)

    status = f"Device: `{TX.device}`  \n" + "  \n".join(timings)
    show_hi = "hindi" in STYLE_CHOICES[choice]
    show_hn = "hinglish" in STYLE_CHOICES[choice]
    return (
        status,
        gr.update(value=result["hindi"][0], visible=show_hi),
        gr.update(value=result["hinglish"][0], visible=show_hn),
        _merge_tables(result["hindi"][1], result["hinglish"][1]),
        result["hindi"][2] + result["hinglish"][2],
    )


def save_edits(hindi_text, hinglish_text, audio_path):
    stem = Path(audio_path).stem if audio_path else "transcript"
    files = []
    for style, text in (("hindi", hindi_text), ("hinglish", hinglish_text)):
        if text and text.strip():
            p = OUT / f"{stem}.{style}.edited.txt"
            p.write_text(text.strip() + "\n", encoding="utf-8")
            files.append(str(p))
    if not files:
        raise gr.Error("Nothing to save yet.")
    return files


def run_batch(paths, choice, progress=gr.Progress()):
    if not paths:
        raise gr.Error("Add one or more audio files.")
    TX.load()
    zpath = OUT / f"transcripts_{int(time.time())}.zip"
    rows = []
    with zipfile.ZipFile(zpath, "w") as z:
        for i, path in enumerate(paths, 1):
            progress((i - 1) / len(paths), desc=f"{Path(path).name} ({i}/{len(paths)})")
            audio = load_audio(path)
            dur = len(audio) / SAMPLE_RATE
            for style in STYLE_CHOICES[choice]:
                segs = TX.transcribe(audio, style=style)
                for f in _write(Path(path).stem, style, segs, {"file": Path(path).name, "duration": dur}):
                    z.write(f, arcname=Path(f).name)
                preview = to_txt(segs).strip().replace("\n", " ")
                rows.append([Path(path).name, STYLES[style]["label"], f"{dur:.1f}", preview[:200]])
    return rows, str(zpath)


CSS = """
.transcript textarea { font-size: 1.15rem !important; line-height: 1.7 !important;
  font-family: 'Noto Sans Devanagari', 'Nirmala UI', 'Mangal', sans-serif !important; }
"""


def build() -> gr.Blocks:
    with gr.Blocks(title="Maya Transcribe: Hindi & Hinglish") as demo:
        gr.Markdown(
            "# 🎙️ Hindi & Hinglish Transcript Writer\n"
            "Powered by the open-weight [**Maya Transcribe**](https://huggingface.co/maya-research/maya-transcribe) "
            "speech-to-text model. It runs fully on this machine, so audio never leaves it.\n\n"
            f"- **Hindi** → {STYLES['hindi']['help']}\n"
            f"- **Hinglish** → {STYLES['hinglish']['help']}"
        )
        with gr.Tab("Transcribe"):
            with gr.Row():
                with gr.Column(scale=1):
                    audio = gr.Audio(sources=["upload", "microphone"], type="filepath", label="Audio (any length)")
                    choice = gr.Radio(list(STYLE_CHOICES), value="Both, side by side", label="Output style")
                    go = gr.Button("Transcribe", variant="primary")
                    status = gr.Markdown()
                    samples = sorted(Path("samples").glob("*.mp3")) if Path("samples").exists() else []
                    if samples:
                        gr.Examples([[str(p)] for p in samples], inputs=[audio], label="Sample clips")
                with gr.Column(scale=2):
                    with gr.Row():
                        hindi_box = gr.Textbox(label="Hindi (Devanagari): edit freely", lines=12,
                                               elem_classes="transcript", interactive=True)
                        hinglish_box = gr.Textbox(label="Hinglish (code-mix): edit freely", lines=12,
                                                  elem_classes="transcript", interactive=True)
                    seg_table = gr.Dataframe(headers=["#", "start (s)", "end (s)", "Hindi", "Hinglish"],
                                             label="Timed segments (same audio chunk, both styles)",
                                             wrap=True, interactive=False)
                    with gr.Row():
                        files = gr.File(label="Downloads (TXT / SRT / VTT / JSON)", file_count="multiple")
                        save_btn = gr.Button("💾 Save my edited transcript")
                        edited = gr.File(label="Edited transcript", file_count="multiple")

            go.click(run_single, [audio, choice], [status, hindi_box, hinglish_box, seg_table, files])
            save_btn.click(save_edits, [hindi_box, hinglish_box, audio], edited)

        with gr.Tab("Batch"):
            gr.Markdown("Drop several recordings. You get one ZIP with TXT, SRT, VTT and JSON for each file.")
            bfiles = gr.File(file_count="multiple", type="filepath", label="Audio files")
            bchoice = gr.Radio(list(STYLE_CHOICES), value="Hinglish: Hindi + English code-mix", label="Output style")
            bgo = gr.Button("Transcribe all", variant="primary")
            btable = gr.Dataframe(headers=["file", "style", "duration (s)", "preview"], wrap=True)
            bzip = gr.File(label="ZIP")
            bgo.click(run_batch, [bfiles, bchoice], [btable, bzip])

        with gr.Tab("Writing guide"):
            gr.Markdown(GUIDE_MD.read_text(encoding="utf-8") if GUIDE_MD.exists() else "See TRANSCRIPT_GUIDE.md")
    return demo


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--share", action="store_true", help="create a temporary public gradio.live link")
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--preload", action="store_true", help="load the model before starting the UI")
    args = ap.parse_args()
    if args.preload:
        TX.load()
    build().queue(default_concurrency_limit=1).launch(server_port=args.port, share=args.share, inbrowser=True, css=CSS, theme=gr.themes.Soft())
