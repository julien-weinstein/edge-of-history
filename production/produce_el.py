#!/usr/bin/env python3
"""Render an Edge of History script with ElevenLabs v3 (realistic voices).

Usage:
    python3 production/produce_el.py episodes/ep01-kesey.md audio/ep01-kesey.mp3
    python3 production/produce_el.py SCRIPT OUT --until "INTRO" --voices jessica,eric   # short sample

The API key is read from ELEVENLABS_API_KEY and sent in the xi-api-key header.
(In a cloud session the network proxy injects the real key, so any placeholder works.)

Conversation is rendered with the Text to Dialogue endpoint, a few dozen lines
at a time, so the model handles turn-taking, laughs and interruptions itself.
Every chunk is cached under production/cache/ by a hash of its content, so a
re-render after a script edit only pays for the chunks that changed.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import produce  # noqa: E402  (sound effects, music and the script parser)

SR = 44100
produce.SR = SR          # synthesise SFX and music at full quality
produce.KEEP_TAGS = True  # keep [laughs], [sighs] and em dashes for v3

API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_v3"

# Fixed host voices. These ARE the characters; never change them mid-season.
VOICES = {
    "jessica": "cgSgspJ2msm6clMCkdW9",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    "eric": "cjVigY5qzO86Huf0OWal",
    "chris": "iP95p4xoKVk53GoZ742B",
    "brian": "nPczCjzI2devNBz1zQrb",
    "will": "bIHbv24MWmeRgasZH58o",
}
DEFAULT_CAST = {"NORA": "jessica", "CAL": "eric"}

CHUNK_CHARS = 1800       # stay well under the dialogue endpoint's input limit
CACHE = Path(__file__).parent / "cache"


def post(path, body, retries=4):
    key = os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")
    data = json.dumps(body).encode()
    for attempt in range(retries):
        req = urllib.request.Request(f"{API}/{path}", data=data, method="POST", headers={
            "xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"ElevenLabs error {e.code} on {path}: {msg}")


def decode(mp3_bytes):
    """MP3 bytes -> float mono numpy array at SR."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        f.write(mp3_bytes); f.flush()
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", f.name, "-f", "f32le",
                              "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def cached(kind, payload, fn):
    CACHE.mkdir(exist_ok=True)
    h = hashlib.sha256(json.dumps([kind, payload], sort_keys=True).encode()).hexdigest()[:20]
    f = CACHE / f"{h}.mp3"
    if not f.exists():
        f.write_bytes(fn())
    return decode(f.read_bytes())


def speakable(text):
    """A line that is only a cue, like "[laughs]", needs a sound to hang on."""
    import re
    if re.sub(r"\[[^\]]*\]", "", text).strip(" .…—"):
        return text
    tag = text.lower()
    if "laugh" in tag or "howl" in tag:
        return text + " Ha!"
    if "sigh" in tag:
        return text + " Hhh."
    return text + " Mm."


def dialogue(turns, cast):
    """turns: [(speaker, text)] -> audio. One API call for the whole exchange."""
    inputs = [{"text": speakable(t), "voice_id": VOICES[cast[s]]} for s, t in turns]
    body = {"inputs": inputs, "model_id": MODEL}
    return cached("dialogue", body, lambda: post("text-to-dialogue?output_format=mp3_44100_128", body))


def solo(voice, text):
    body = {"text": text, "model_id": MODEL}
    return cached("tts", [voice, body],
                  lambda: post(f"text-to-speech/{VOICES[voice]}?output_format=mp3_44100_128", body))


def trim(a, thresh=0.004):
    """Trim leading/trailing near-silence so our own gaps control pacing."""
    idx = np.where(np.abs(a) > thresh)[0]
    if not len(idx):
        return a
    pad = int(SR * 0.05)
    return a[max(0, idx[0] - pad): idx[-1] + pad]


def room_tone(n):
    """Very quiet, slightly warm noise, so silences sound like a room, not a void."""
    w = np.random.default_rng(3).standard_normal(n)
    w = produce.lowpass(w[: min(n, SR * 5)], 0.05)  # 5 s loop is enough
    w = np.tile(w, n // len(w) + 1)[:n]
    return w / (np.max(np.abs(w)) or 1) * 0.0025


def render(events, cast):
    out, chapters, batch = [], [], []
    pos = lambda: sum(len(x) for x in out) / SR

    def flush():
        if not batch:
            return
        # split the batch into chunks under CHUNK_CHARS, at speaker turns
        chunk, size = [], 0
        for turn in batch + [None]:
            if turn is None or (size + len(turn[1]) > CHUNK_CHARS and chunk):
                a = trim(dialogue(chunk, cast))
                out.append(np.zeros(int(SR * 0.28)))
                out.append(a)
                print(f"  rendered {len(chunk)} lines, now at {pos() / 60:.1f} min", file=sys.stderr)
                chunk, size = [], 0
            if turn is not None:
                chunk.append(turn); size += len(turn[1])
        batch.clear()

    for ev in events:
        kind = ev[0]
        if kind == "line" and ev[1] != "BOTH":
            batch.append((ev[1], ev[2]))
            continue
        flush()
        if kind == "chapter":
            chapters.append((round(pos(), 2), ev[1]))
        elif kind == "line":  # BOTH: the two hosts say it together
            a = produce.mix(trim(solo(cast["NORA"], ev[2])) * 0.8, trim(solo(cast["CAL"], ev[2])) * 0.8)
            out += [np.zeros(int(SR * 0.3)), a]
        elif kind == "sfx":
            out += [np.zeros(int(SR * 0.12)), produce.sfx_for(ev[1]) * 0.6]
        elif kind == "music":
            out += [np.zeros(int(SR * 0.25)), produce.sting_for(ev[1]) * 0.5, np.zeros(int(SR * 0.15))]
        elif kind == "pause":
            out.append(np.zeros(int(SR * ev[1])))
    flush()
    out.append(np.zeros(SR))
    audio = np.concatenate(out)
    return audio + room_tone(len(audio)), chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("out")
    ap.add_argument("--cast", default="", help="e.g. jessica,eric (Nora,Cal)")
    ap.add_argument("--until", default="", help="stop at this chapter (for samples)")
    ap.add_argument("--title", default=""); ap.add_argument("--track", default="")
    ap.add_argument("--cover", default="")
    ap.add_argument("--dry-run", action="store_true", help="count characters, call nothing")
    a = ap.parse_args()

    cast = dict(DEFAULT_CAST)
    if a.cast:
        cast["NORA"], cast["CAL"] = a.cast.split(",")

    events = produce.parse(Path(a.script).read_text())
    if a.until:
        cut = next((i for i, e in enumerate(events) if e[0] == "chapter" and e[1].lower() == a.until.lower()), None)
        events = events[:cut]
    chars = sum(len(e[2]) for e in events if e[0] == "line")
    chars += sum(len(e[2]) for e in events if e[0] == "line" and e[1] == "BOTH")  # said twice
    print(f"{chars} characters to synthesise (cached chunks are free)", file=sys.stderr)
    if a.dry_run:
        return

    audio, chapters = render(events, cast)
    audio = produce.norm(audio, 0.95)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "raw.f32"
        audio.astype(np.float32).tofile(wav)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(wav)]
        if a.cover:
            cmd += ["-i", a.cover, "-map", "0:a", "-map", "1:v", "-c:v", "mjpeg", "-vf", "scale=1400:1400",
                    "-disposition:v", "attached_pic"]
        # Gentle broadcast chain: rumble filter, light compression, podcast loudness.
        cmd += ["-af", "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=15:release=200,"
                       "loudnorm=I=-16:TP=-1.5:LRA=9",
                "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k", "-ac", "1", "-id3v2_version", "3",
                "-metadata", f"title={a.title}", "-metadata", "artist=Edge of History",
                "-metadata", "album=Edge of History", "-metadata", f"track={a.track}", a.out]
        subprocess.run(cmd, check=True)
    Path(a.out).with_suffix(".chapters.json").write_text(json.dumps(
        {"version": "1.2.0", "chapters": [{"startTime": s, "title": n} for s, n in chapters]}, indent=2))
    print(f"wrote {a.out}: {len(audio) / SR / 60:.1f} min", file=sys.stderr)


if __name__ == "__main__":
    main()
