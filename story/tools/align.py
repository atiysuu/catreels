"""Tek parca anlatimi kelime zamanlarina doker.

Kullanim:
    python story/tools/align.py <ses.mp3> <cikti.json>

ElevenLabs gibi arayuzlerden butun bolum tek dosya geliyor; prep.py bu
kelime zamanlarini kullanarak dosyayi bolumlere ayiriyor ve altyaziyi
kelime kelime oturtuyor.
"""
import json
import sys

from faster_whisper import WhisperModel

src, dst = sys.argv[1], sys.argv[2]
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, _ = model.transcribe(src, language="tr", word_timestamps=True, vad_filter=False)
words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
         for seg in segments for w in seg.words]
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(words, fh, ensure_ascii=False, indent=0)
print(len(words), "kelime")
print(" ".join(f"{x['w']}@{x['s']}" for x in words))
