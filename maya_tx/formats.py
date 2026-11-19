"""Export transcripts: plain text, SRT, WebVTT, JSON (all UTF-8)."""

from __future__ import annotations

import json

from .engine import Segment


def _ts(seconds: float, sep: str = ",") -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_txt(segments: list[Segment], with_times: bool = False) -> str:
    if with_times:
        return "\n".join(f"[{_ts(s.start, '.')[:-4]}] {s.text}" for s in segments) + "\n"
    return "\n".join(s.text for s in segments) + "\n"


def to_srt(segments: list[Segment]) -> str:
    return "\n".join(
        f"{i}\n{_ts(s.start)} --> {_ts(s.end)}\n{s.text}\n" for i, s in enumerate(segments, 1)
    )


def to_vtt(segments: list[Segment]) -> str:
    body = "\n".join(f"{_ts(s.start, '.')} --> {_ts(s.end, '.')}\n{s.text}\n" for s in segments)
    return "WEBVTT\n\n" + body


def to_json(segments: list[Segment], **meta) -> str:
    return json.dumps(
        {**meta, "segments": [s.to_dict() for s in segments], "text": " ".join(s.text for s in segments)},
        ensure_ascii=False,
        indent=2,
    )
