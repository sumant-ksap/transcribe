"""Generate demo clips (pure Hindi + Hinglish) using Microsoft Edge neural TTS.

Optional, for demos only: real recordings from your team are the better test.
Needs internet:  pip install edge-tts && python make_samples.py
"""

import asyncio
from pathlib import Path

import edge_tts

SAMPLES = {
    "01_hindi_news": (
        "hi-IN-SwaraNeural",
        "आज दिल्ली में मौसम साफ़ रहेगा। दोपहर में तापमान पैंतीस डिग्री तक पहुँच सकता है। "
        "मौसम विभाग ने लोगों को पर्याप्त पानी पीने की सलाह दी है।",
    ),
    "02_hinglish_meeting": (
        "hi-IN-MadhurNeural",
        "Hi team, कल की meeting में हमने project की deadline discuss की थी। "
        "Client चाहता है कि demo Friday तक ready हो जाए, तो please अपने tasks Jira में update कर दो।",
    ),
    "03_hinglish_support": (
        "hi-IN-SwaraNeural",
        "Thank you for calling. मैं आपकी क्या help कर सकती हूँ? "
        "अच्छा, आपका UPI payment fail हो गया है। कोई बात नहीं, मैं अभी आपका transaction ID check करती हूँ।",
    ),
}


async def main():
    out = Path(__file__).with_name("samples")
    out.mkdir(exist_ok=True)
    for name, (voice, text) in SAMPLES.items():
        dest = out / f"{name}.mp3"
        await edge_tts.Communicate(text, voice).save(str(dest))
        (out / f"{name}.reference.txt").write_text(text + "\n", encoding="utf-8")
        print("wrote", dest)


if __name__ == "__main__":
    asyncio.run(main())
