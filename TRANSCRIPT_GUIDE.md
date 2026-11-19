## Transcript writing guide: Hindi vs Hinglish

Maya Transcribe gives you a **first draft**. A person reviews it and corrects it in the editable box, then saves it.

### 1. Pick the style

| Style | Model prompt | Use it when | Example output |
|---|---|---|---|
| **Hindi** (native) | `style: native` | The final transcript must be pure Devanagari: subtitles for Hindi audiences, government or legal records, Hindi NLP datasets | कल की मीटिंग में हमने प्रोजेक्ट की डेडलाइन डिस्कस की। |
| **Hinglish** (mixed) | `style: mixed` | The speaker switches between Hindi and English: business calls, customer support, interviews, tech talks | कल की meeting में हमने project की deadline discuss की। |

Rule of thumb: **if an English word would look odd transliterated (brand names, tech terms, acronyms), use Hinglish.**

### 2. House conventions (suggested, so adjust them for your team)

**Script**
- Hindi words go in Devanagari and English words in Latin script (Hinglish), even when the speaker's accent is strong.
- Don't romanize Hindi ("kal ki meeting" ✗). The model doesn't output Roman Hindi, and mixing scripts in a single word hurts search.
- Acronyms stay uppercase in Hinglish: `KYC`, `EMI`, `UPI`. In Hindi style they are transliterated: `केवाईसी`.

**Punctuation** (the model outputs **none**, so add it during review)
- End Hindi sentences with the danda `।` and English-ending sentences with `.`
- Use `?` and `,` the normal way.

**Watch for in Hinglish output** (seen in testing)
- Spelled-out acronyms come out broken, for example `यू p आई` → fix to `UPI` and `आई d` → `ID`.
- Some English words stay in Devanagari (`जीरा` → `Jira`), and capitals are lost (`friday` → `Friday`).

**Numbers, dates, money**
- Pick one form and stick to it. We suggest digits for amounts, dates and phone numbers: `₹2,500`, `15 अगस्त`, `9:30 बजे`.
- The model may write numbers as words (`पच्चीस सौ`). Fix this during review.

**Names**
- Write people's and place names the way the person writes them (check the CRM or ticket). The model may spell them in several valid ways.

**Non-speech tags** (add these by hand)
- `[अस्पष्ट]` / `[inaudible]` for unclear audio
- `[हँसी]` / `[laughs]` and `[शोर]` / `[noise]`
- `[क्रॉसटॉक]` / `[crosstalk]` when people talk over each other

**Speakers**
- The model **does not** separate speakers. Add `Agent:` / `Customer:` (or `A:` / `B:`) at the start of each turn during review.

### 3. Known limits (from the model card)
- **Max 30 s per clip**. This app cuts longer audio at pauses automatically.
- Timestamps here are **chunk level** (about every 20–28 s), not word level.
- Phone and low-bitrate audio is harder: about 20% WER on Gram Vaani compared with about 9–12% on clean Hindi sets, and about 17% WER on code-mix.
- Only evaluated on Hindi and Hindi-English. Don't use it for English-only or other Indian languages.

### 4. Review checklist
1. Play the audio and read along. Fix misheard words first.
2. Check names, numbers and English terms.
3. Add speaker labels and non-speech tags.
4. Click **💾 Save my edited transcript**.
