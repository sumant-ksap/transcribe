# Hindi & Hinglish Transcript Writer (Maya Transcribe)

This is a local demo for turning Hindi and Hindi-English (Hinglish) audio into editable transcripts. It uses the open-weight
[`maya-research/maya-transcribe`](https://huggingface.co/maya-research/maya-transcribe) speech-recognition model, which is licensed under Apache-2.0.

- **Two output styles from one model**
  - **Hindi**: `कल की मीटिंग में प्रोजेक्ट पर बात हुई।`
  - **Hinglish**: `कल की meeting में project पर बात हुई।`
- **Any length audio**: it is cut at pauses into chunks of 28 s or less, because the model accepts at most 30 s per clip.
- **Any format**: mp3, m4a, wav, ogg, and mp4 or other video, all decoded through ffmpeg.
- **Exports**: TXT, SRT, VTT (subtitles with chunk-level timestamps) and JSON.
- **Edit and save**: the transcript boxes are editable, so reviewers can correct the draft and download it.
- **Private**: the model runs on your machine (CPU, NVIDIA GPU or Apple Silicon).

## Setup

You need Python 3.12 and ffmpeg (`winget install Gyan.FFmpeg`).

```powershell
python -m venv .venv
.venv\Scripts\activate
# CPU only (smaller download):
pip install torch --index-url https://download.pytorch.org/whl/cpu
# or, with an NVIDIA GPU:  pip install torch --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

The first run downloads the model (about 1.6 GB) into the Hugging Face cache.

## Use it

**Web app (for demos and reviewers)**

Double-click `run_app.bat`, or run:

```powershell
.venv\Scripts\python.exe app.py              # http://127.0.0.1:7860
.venv\Scripts\python.exe app.py --share      # temporary public link to show remote teammates
```

(If `activate` fails with "running scripts is disabled", just call `.venv\Scripts\python.exe` directly as shown.)

The app has three tabs:
- **Transcribe**: upload or record audio, then choose Hindi, Hinglish or both side by side.
- **Batch**: drop several files and get back a ZIP of transcripts.
- **Writing guide**: house conventions for the team (see [TRANSCRIPT_GUIDE.md](TRANSCRIPT_GUIDE.md)).

**Command line (for bulk jobs)**

```powershell
python transcribe_cli.py call.mp3                                   # Hinglish, printed to the console
python transcribe_cli.py call.mp3 --style hindi
python transcribe_cli.py recordings\ --style both --formats txt srt json --out transcripts\
```

**From Python**

```python
from maya_tx import MayaTranscriber, to_srt
tx = MayaTranscriber()
segs = tx.transcribe("call.mp3", style="hinglish")   # or "hindi"
print(to_srt(segs))
```

**Demo clips**: `pip install edge-tts && python make_samples.py` creates three synthetic clips in `samples/`, each with a reference text: pure Hindi news, a Hinglish meeting and a Hinglish support call. They show up as one-click examples in the app.

## Project layout

```
maya_tx/engine.py     model loading, ffmpeg decode, silence-based chunking, batching
maya_tx/formats.py    TXT / SRT / VTT / JSON writers
app.py                Gradio web app
transcribe_cli.py     batch CLI
make_samples.py       synthetic demo audio
TRANSCRIPT_GUIDE.md   transcript-writing conventions (also shown in the app)
```

## Limits to know

- There are no word-level timestamps and no speaker separation (diarization). Timestamps are per chunk.
- The model was evaluated only on Hindi and Hindi-English. Reported WER is about 9–12% on clean Hindi, about 17% on code-mix and about 20% on phone audio. Plan for human review.
- On CPU, expect roughly real time or slower. An NVIDIA GPU is far faster.
