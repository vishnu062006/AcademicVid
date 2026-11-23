# Running costs and pay-per-use estimate (23 Nov 2026)

**Short version:** on the paid Gemini tier, one lesson costs about **₹1.7 (English) to ₹2.5 (Kannada)**
for the AI part, using the model the app uses today (Gemini 3.5 Flash-Lite). 1,000 lessons a month is about
**₹2,000–2,500**. Library chapters are cached, so a chapter many students open costs once, not once
per student. If we leave the free voice (edge-tts) for a paid official one, the voice can cost more than the AI.

All figures are estimates. ₹88 = $1 is assumed. Check the live price pages before quoting to KREIS.

---

## 1. What one lesson uses (measured where possible)

| Item | English | Kannada | How we know |
|---|---|---|---|
| Chapter text sent to Gemini | 4.9k–9.1k tokens | same | **Measured** with Gemini count-tokens on our 3 library PDFs (jemh101 4,851; jesc101 7,956; jesc102 9,142) |
| System prompt | 1.1k tokens | 1.4k tokens | **Measured** |
| Lesson Gemini writes back (≈8 sections) | ≈6.5k tokens | ≈10k tokens | **Estimated**: ≈530 words per section. Kannada costs **1.8× more tokens per word** than English (measured on our own UI text: EN 1.29, KN 2.86 tokens/word) |
| Handwritten notes OCR, per photo | ≈1.5k in + ≈0.4k out | same | **Estimated**: a 2000 px photo is ≈6 tiles × 258 tokens (Gemini docs) |

A Kannada script retry (wrong script detected) repeats the call, so the worst case is 3× one call.
Word-count retries are gone (audit task T4).

## 2. Gemini price per lesson (paid tier, Standard)

| Model | Price per 1M tokens (in / out) | English lesson | Kannada lesson |
|---|---|---|---|
| **Gemini 3.5 Flash-Lite** (what we use) | $0.30 / $2.50 | **$0.019 ≈ ₹1.7** | **$0.028 ≈ ₹2.5** |
| Gemini 3.8 Flash (from 1 Jan 2027) | $1.50 / $7.50 | $0.064 ≈ ₹5.6 | $0.091 ≈ ₹8.0 |
| Gemini 4 (Argon / Carbon, from 1 Dec 2026) | $4.00 / $20.00 | $0.17 ≈ ₹15 | $0.24 ≈ ₹21 |
| Flash-Lite **Batch** (pre-making library lessons) | $0.15 / $1.25 | ≈ ₹0.85 | ≈ ₹1.25 |

Handwritten notes, 10 photos: ≈ $0.015 ≈ ₹1.3 extra.
**Free tier:** Flash-Lite input and output are free of charge, but with low rate limits. That's fine for a pilot, not for a whole district.

## 3. Monthly cost at different scales (Flash-Lite, ≈₹2.1 average per new lesson)

| New lessons made per month | Gemini cost | Notes |
|---|---|---|
| 1,000 (one school, pilot) | ≈ ₹2,100 | Free tier may cover this if usage is spread out |
| 10,000 (a few hundred schools) | ≈ ₹21,000 | |
| 50,000 (district / state roll-out) | ≈ ₹1,05,000 | Pre-made library lessons cut this a lot |

"New lesson" = a chapter + language not made before. Re-opening a library chapter is free (cached).

## 4. The other costs

| Part | Today | If we move to a paid, official service |
|---|---|---|
| Voice (narration) | **edge-tts: free**, but it is Microsoft Edge's read-aloud service used without an official contract. There's no guarantee and it can stop working any day | Google Cloud Text-to-Speech: about $4 per 1M characters (Standard) to $16 per 1M (premium voices), with a monthly free allowance. A lesson is ≈14k characters → **₹5 (Standard) to ₹20 (premium) per lesson**. Check that the voice you pick exists in Kannada (kn-IN) |
| Hosting | Streamlit Community Cloud: free, sleeps after ≈12 h idle, no SLA | A small paid server or Google Cloud Run: roughly ₹1,500–5,000/month at pilot scale (needs a quote) |
| Video rendering | On our server CPU, free | Grows with users; this is why pre-made library videos matter |

## 5. Suggested pay-per-use plan (for discussion)

- **Students: free** for library chapters. Library lessons are pre-made (Batch, ≈₹1 each, once) and cached, so they cost ≈₹0 per student.
- **Teachers / institutions: pay per new lesson** from their own PDF, notes or topics:
  - Notes, flashcards, PPT: **₹5 per lesson** (cost ≈₹2–3 with Kannada and OCR).
  - Video: **₹10–15 per lesson** (adds rendering, and voice cost once off edge-tts).
- **Or a school plan:** e.g. ₹500/month for 100 new lessons.
- Keep a **monthly spending cap** in Google Cloud Billing so a mistake or misuse can't run up a bill.

## Sources
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing (read 23 Nov 2026; Flash-Lite $0.30 / $2.50, Batch 50% off, free tier "Free of charge")
- Gemini token counting (images = 258 tokens per 768×768 tile): https://ai.google.dev/gemini-api/docs/tokens
- Vertex AI pricing (same Flash-Lite rate): https://cloud.google.com/vertex-ai/generative-ai/pricing
- Google Cloud Text-to-Speech pricing: https://cloud.google.com/text-to-speech/pricing
- Streamlit sleep (≈12 h, forum moderator; no paid always-on plan): https://discuss.streamlit.io/t/web-apps-keeps-on-sleeping-after-30-minutes-or-a-day-of-inactivity/97350
