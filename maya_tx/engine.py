"""Core transcription engine around maya-research/maya-transcribe.

The model accepts at most ~30 s of 16 kHz mono audio per clip, so longer
recordings are cut at quiet points (low-energy frames) into <= MAX_CHUNK_S
pieces, transcribed in batches, and returned as timed segments.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Callable, Iterable

import numpy as np

MODEL_ID = "maya-research/maya-transcribe"
SAMPLE_RATE = 16_000

# Max model input is 30 s; leave headroom. Prefer cutting in the last few seconds.
MAX_CHUNK_S = 28.0
MIN_CUT_S = 18.0
FRAME_S = 0.03

# Output styles supported by the model (passed as the prompt).
STYLES = {
    "hindi": {
        "prompt": "style: native",
        "label": "Hindi (Devanagari only)",
        "help": "Everything in Devanagari; English words are transliterated, e.g. 'मीटिंग', 'प्रोजेक्ट'.",
    },
    "hinglish": {
        "prompt": "style: mixed",
        "label": "Hindi-English code-mix (Hinglish)",
        "help": "Hindi in Devanagari, English words kept in Latin script, e.g. 'कल की meeting में project पर बात हुई'.",
    },
}


@dataclass
class Segment:
    index: int
    start: float
    end: float
    text: str
    truncated: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- audio


def load_audio(path: str) -> np.ndarray:
    """Decode any audio/video file to 16 kHz mono float32 using ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH. Install it (e.g. `winget install Gyan.FFmpeg`).")
    cmd = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", path, "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to decode {path!r}: {proc.stderr.decode(errors='ignore').strip()}")
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    if audio.size == 0:
        raise RuntimeError(f"No audio found in {path!r}")
    return audio


def _frame_rms(audio: np.ndarray, frame: int) -> np.ndarray:
    n = len(audio) // frame
    if n == 0:
        return np.array([float(np.sqrt(np.mean(audio**2)))])
    frames = audio[: n * frame].reshape(n, frame)
    return np.sqrt(np.mean(frames**2, axis=1) + 1e-12)


def split_on_silence(audio: np.ndarray) -> list[tuple[int, int]]:
    """Return (start, end) sample ranges, each <= MAX_CHUNK_S, cut at the quietest
    point between MIN_CUT_S and MAX_CHUNK_S. Near-silent chunks are dropped."""
    total = len(audio)
    max_len = int(MAX_CHUNK_S * SAMPLE_RATE)
    if total <= max_len:
        return [(0, total)]

    frame = int(FRAME_S * SAMPLE_RATE)
    rms = _frame_rms(audio, frame)
    silence_floor = max(float(np.percentile(rms, 10)) * 1.5, 1e-4)

    spans: list[tuple[int, int]] = []
    start = 0
    while start < total:
        if total - start <= max_len:
            spans.append((start, total))
            break
        lo = (start + int(MIN_CUT_S * SAMPLE_RATE)) // frame
        hi = (start + max_len) // frame
        window = rms[lo:hi]
        # Smooth a little so a single quiet frame mid-word doesn't win.
        if len(window) >= 5:
            window = np.convolve(window, np.ones(5) / 5, mode="same")
        cut = (lo + int(np.argmin(window))) * frame if len(window) else start + max_len
        spans.append((start, cut))
        start = cut

    # Drop chunks that are essentially silence (keeps the model from hallucinating).
    kept = []
    for s, e in spans:
        if e - s < int(0.3 * SAMPLE_RATE):
            continue
        if float(np.sqrt(np.mean(audio[s:e] ** 2))) < silence_floor:
            continue
        kept.append((s, e))
    return kept or [(0, min(total, max_len))]


# --------------------------------------------------------------------------- model


class MayaTranscriber:
    """Lazy-loading wrapper. One instance can serve both Hindi and Hinglish styles."""

    def __init__(self, model_id: str = MODEL_ID, device: str | None = None):
        self.model_id = model_id
        self.device_pref = device
        self._model = None
        self._processor = None

    # -- loading -----------------------------------------------------------
    def _pick_device(self):
        import torch

        if self.device_pref:
            dev = self.device_pref
        elif torch.cuda.is_available():
            dev = "cuda"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            dev = "mps"
        else:
            dev = "cpu"
        dtype = torch.bfloat16 if dev == "cuda" else (torch.float16 if dev == "mps" else torch.float32)
        return dev, dtype

    def load(self):
        if self._model is not None:
            return
        from transformers import AutoModelForMultimodalLM, AutoProcessor

        dev, dtype = self._pick_device()
        self._processor = AutoProcessor.from_pretrained(self.model_id, trust_remote_code=False)
        self._model = AutoModelForMultimodalLM.from_pretrained(
            self.model_id, dtype=dtype, trust_remote_code=False
        ).to(dev)
        self._model.eval()
        self.device = dev

    # -- inference ---------------------------------------------------------
    def _transcribe_clips(self, clips: list[np.ndarray], style: str, max_new_tokens: int) -> list[tuple[str, bool]]:
        import torch

        prompt = STYLES[style]["prompt"]
        inputs = self._processor.apply_transcription_request(
            audio=clips, prompt=prompt, language="Hindi"
        ).to(self._model.device, self._model.dtype)
        with torch.inference_mode():
            out = self._model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        gen = out[:, inputs["input_ids"].shape[1]:]
        texts = self._processor.decode(gen, return_format="transcription_only")
        if isinstance(texts, str):
            texts = [texts]
        # A row that used the whole token budget was probably cut off.
        pad_id = getattr(self._processor.tokenizer, "pad_token_id", None)
        results = []
        for row, text in zip(gen, texts):
            used = int((row != pad_id).sum()) if pad_id is not None else row.shape[0]
            results.append((text.strip(), used >= max_new_tokens))
        return results

    def transcribe(
        self,
        audio: np.ndarray | str,
        style: str = "hinglish",
        batch_size: int = 4,
        max_new_tokens: int = 512,
        progress: Callable[[int, int], None] | None = None,
    ) -> list[Segment]:
        if style not in STYLES:
            raise ValueError(f"style must be one of {list(STYLES)}")
        self.load()
        if isinstance(audio, str):
            audio = load_audio(audio)

        spans = split_on_silence(audio)
        segments: list[Segment] = []
        for b in range(0, len(spans), batch_size):
            batch = spans[b : b + batch_size]
            clips = [audio[s:e] for s, e in batch]
            for (s, e), (text, trunc) in zip(batch, self._transcribe_clips(clips, style, max_new_tokens)):
                segments.append(Segment(len(segments) + 1, s / SAMPLE_RATE, e / SAMPLE_RATE, text, trunc))
            if progress:
                progress(min(b + batch_size, len(spans)), len(spans))
        return [seg for seg in segments if seg.text]

    def transcribe_both(self, audio: np.ndarray | str, **kw) -> dict[str, list[Segment]]:
        if isinstance(audio, str):
            audio = load_audio(audio)
        return {style: self.transcribe(audio, style=style, **kw) for style in STYLES}


def iter_audio_files(paths: Iterable[str]) -> list[str]:
    """Expand folders into audio/video files."""
    from pathlib import Path

    exts = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wma", ".webm", ".mp4", ".mkv", ".mov"}
    out: list[str] = []
    for p in map(Path, paths):
        if p.is_dir():
            out += sorted(str(f) for f in p.rglob("*") if f.suffix.lower() in exts)
        elif p.exists():
            out.append(str(p))
        else:
            raise FileNotFoundError(p)
    return out
