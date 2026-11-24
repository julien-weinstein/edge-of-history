#!/usr/bin/env python3
"""Render an Edge of History script (Markdown) into a finished podcast MP3.

Usage:
    python3 production/produce.py episodes/ep01-mona-lisa.md audio/ep01.mp3 \
        --model path/to/kokoro-v1.0.onnx --voices path/to/voices-v1.0.bin

Each host has one fixed voice, set in HOSTS below, so they sound the same in
every episode. Sound effects and music stings are synthesised procedurally
(original audio, no samples), so the output has no third-party audio in it.
"""
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000  # Kokoro's native sample rate

# Fixed host voices. Changing these changes the show; don't.
HOSTS = {
    "NORA": {"voice": "af_heart", "speed": 1.08},
    "CAL": {"voice": "am_michael", "speed": 0.97},
}

rng = np.random.default_rng(7)


# ---------------------------------------------------------------- synthesis
def t(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, attack=0.005, decay=None):
    e = np.ones(n)
    a = max(1, int(SR * attack))
    e[:a] = np.linspace(0, 1, a)
    if decay:
        e *= np.exp(-np.arange(n) / (SR * decay))
    return e


def norm(x, peak=0.8):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def note(freq, sec, kind="sine", decay=0.4, vol=1.0):
    tt = t(sec)
    if kind == "sine":
        w = np.sin(2 * np.pi * freq * tt)
    elif kind == "pluck":
        w = sum(np.sin(2 * np.pi * freq * h * tt) / h ** 1.5 for h in range(1, 6))
    elif kind == "saw":
        w = sum(np.sin(2 * np.pi * freq * h * tt) / h for h in range(1, 12))
    elif kind == "square":
        w = np.sign(np.sin(2 * np.pi * freq * tt))
    elif kind == "piano":
        w = sum(np.sin(2 * np.pi * freq * h * tt) * (0.6 ** h) for h in range(1, 7))
    return w * env(len(tt), decay=decay) * vol


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def seq(notes, step, kind="pluck", decay=0.35, length=None, vol=1.0):
    """notes: list of freqs (or None for rest, or tuple for chord)."""
    total = length or step * len(notes) + 1.5
    out = np.zeros(int(SR * total))
    for i, f in enumerate(notes):
        if f is None:
            continue
        fs = f if isinstance(f, tuple) else (f,)
        for fr in fs:
            s = note(fr, min(2.5, total - i * step), kind, decay, vol / len(fs))
            st = int(SR * i * step)
            out[st: st + len(s)] += s[: len(out) - st]
    return out


def noise(sec, decay=0.1):
    return rng.standard_normal(int(SR * sec)) * env(int(SR * sec), decay=decay)


def lowpass(x, alpha=0.1):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # simple one-pole filter
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def hz(n):  # MIDI note number to Hz
    return 440 * 2 ** ((n - 69) / 12)


# Original show motif: a rising minor figure that "steps off the edge".
MOTIF = [57, 60, 64, 69, 67, 64, None, 62, 65, 69, 72]


def theme(long=False):
    mel = seq([hz(n) if n else None for n in MOTIF], 0.18, "pluck", 0.5, vol=0.9)
    bass = seq([hz(45), None, None, None, hz(41), None, None, None, hz(43), None, None, hz(45)],
               0.18, "saw", 0.6, vol=0.5)
    pad = note(hz(57), 2.5, "sine", 1.5, 0.25) + note(hz(64), 2.5, "sine", 1.5, 0.2)
    pad = np.concatenate([np.zeros(int(SR * 1.8)), pad])
    x = mix(mel, lowpass(bass, 0.08), pad)
    if long:
        x = np.concatenate([x, x * 0.85, x * 0.6, np.zeros(SR)])
        fade = np.linspace(1, 0, int(SR * 4))
        x[-len(fade):] *= fade
    return norm(x, 0.7)


def sting_for(desc):
    d = desc.lower()
    if "theme" in d or "outro" in d:
        return theme(long="outro" in d)
    if "piano" in d:
        return norm(seq([hz(n) for n in (60, 64, 67, 72, 67, 64)], 0.45, "piano", 1.2, vol=0.6), 0.45)
    if "accordion" in d or "melancholy" in d:
        return norm(seq([(hz(57), hz(64)), (hz(55), hz(62)), (hz(53), hz(60)), (hz(52), hz(59))],
                        0.7, "saw", 1.0, vol=0.4), 0.4)
    if "snare" in d or "military" in d:
        hits = np.zeros(int(SR * 2.5))
        for i in range(16):
            s = noise(0.08, 0.02) * (0.4 + 0.6 * (i % 4 == 0))
            st = int(SR * i * 0.12)
            hits[st: st + len(s)] += s
        return norm(mix(hits, seq([hz(55), None, hz(55), hz(60)], 0.48, "saw", 0.4, vol=0.5)), 0.55)
    if "bass" in d or "heist" in d:
        return norm(lowpass(seq([hz(n) if n else None for n in (40, 43, 45, 46, 47, None, 40, 43)], 0.22, "saw", 0.25), 0.12), 0.6)
    if "tick" in d:
        ticks = np.zeros(int(SR * 2.5))
        for i in range(10):
            s = noise(0.02, 0.004)
            st = int(SR * i * 0.25)
            ticks[st: st + len(s)] += s
        return norm(mix(ticks * 0.5, note(hz(45), 2.5, "sine", 2.0, 0.4)), 0.5)
    if "tense" in d or "plucked" in d:
        return norm(seq([hz(n) for n in (45, 45, 46, 45, 45, 46, 48, 45)], 0.2, "pluck", 0.15), 0.5)
    if "strings" in d or "reflective" in d or "slow" in d or "playful" in d:
        up = "playful" in d
        notes = (60, 64, 67, 64, 69, 67) if up else (57, 60, 64, 62)
        return norm(seq([hz(n) for n in notes], 0.25 if up else 0.8, "saw" if not up else "pluck",
                        0.8 if not up else 0.3, vol=0.5), 0.45)
    # dramatic / villain / sting default
    return norm(lowpass(mix(note(hz(45), 1.8, "saw", 0.7), note(hz(52), 1.8, "saw", 0.7),
                            note(hz(57), 1.8, "saw", 0.7), noise(0.3, 0.08) * 0.3), 0.15), 0.6)


def bell(freq=1760, dur=1.4):
    return mix(note(freq, dur, "sine", 0.5), note(freq * 2.76, dur, "sine", 0.15, 0.4),
               note(freq * 5.4, dur, "sine", 0.05, 0.2))


def sfx_for(desc):
    d = desc.lower()
    if d.startswith("ding") or "bell" in d:
        return norm(bell(), 0.6)
    if "air horn" in d:
        tt = t(0.9)
        w = sum(np.sign(np.sin(2 * np.pi * f * tt)) for f in (440, 554, 659)) * env(len(tt), 0.01)
        return norm(lowpass(w, 0.3), 0.55)
    if "buzzer" in d:
        return norm(lowpass(note(110, 0.7, "square", 2.0), 0.2), 0.5)
    if "cash register" in d:
        return norm(mix(noise(0.15, 0.03) * 0.6,
                        np.concatenate([np.zeros(int(SR * 0.12)), bell(2093, 1.0), ])), 0.55)
    if "typewriter" in d:
        clicks = np.zeros(int(SR * 1.6))
        for i in range(5):
            s = noise(0.03, 0.006)
            st = int(SR * i * 0.09)
            clicks[st: st + len(s)] += s
        clicks[int(SR * 0.55): int(SR * 0.55) + int(SR * 1.0)] += bell(2637, 1.0)[: int(SR * 1.0)] * 0.6
        return norm(clicks, 0.55)
    if "door" in d or "creak" in d:
        tt = t(1.2)
        f = 180 + 120 * np.sin(2 * np.pi * 1.5 * tt)
        w = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(len(tt), 0.1, 0.8)
        return norm(lowpass(w, 0.15), 0.35)
    if "crash" in d:
        return norm(lowpass(noise(1.0, 0.25), 0.4), 0.25)  # "distant"
    if "rustle" in d or "paper" in d:
        return norm(lowpass(noise(0.8, 0.4) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t(0.8))), 0.5), 0.3)
    if "squeak" in d:
        tt = t(0.35)
        return norm(np.sin(2 * np.pi * (900 + 1800 * tt) * tt) * env(len(tt), 0.01, 0.2), 0.35)
    if "morse" in d:  # C Q D
        code = "-.-. --.- -.."
        out = []
        for ch in code:
            if ch == " ":
                out.append(np.zeros(int(SR * 0.21)))
                continue
            out.append(note(700, 0.21 if ch == "-" else 0.07, "sine", None, 1.0))
            out.append(np.zeros(int(SR * 0.07)))
        x = np.concatenate(out * 2)
        return norm(x, 0.3)
    if "recorder" in d:
        # An original, deliberately wobbly and off-key tune. It is NOT the song
        # named in the script; the joke lands without the copyrighted melody.
        tune = [72, 74, 75, 74, 72, 70, 72, None, 75, 77, 79, 77, 75, 74, 72]
        out = []
        for i, n in enumerate(tune):
            if n is None:
                out.append(np.zeros(int(SR * 0.3)))
                continue
            tt = t(0.42)
            wob = 1 + 0.02 * np.sin(2 * np.pi * 6 * tt) + rng.uniform(-0.03, 0.03)
            w = np.sin(2 * np.pi * hz(n) * wob * tt) + 0.15 * np.sin(4 * np.pi * hz(n) * wob * tt)
            if i in (5, 11):  # squeaks
                w += 0.5 * np.sin(2 * np.pi * hz(n + 12) * 1.04 * tt)
            out.append(w * env(len(tt), 0.03, 0.6))
        return norm(np.concatenate(out), 0.45)
    return norm(noise(0.2, 0.05), 0.2)


# ---------------------------------------------------------------- parsing
SPEAKER_RE = re.compile(r"^\*\*(NORA|CAL|BOTH):\*\*\s*(.*)$")
CUE_RE = re.compile(r"`?\[(SFX|MUSIC):\s*([^\]]+)\]`?")
NUMWORDS = {"2": "two", "7": "seven", "6": "six"}


def clean(text):
    text = re.sub(r"`?\[CLIP(?: ENDS)?\]`?", "", text)
    text = re.sub(r"\*\(([^)]*)\)\*", "", text)          # *(stage direction)*
    text = text.replace("**", "").replace("*", "")
    text = text.replace("£90,000", "ninety thousand pounds").replace("£200", "two hundred pounds")
    text = re.sub(r"(\d)'(\d+)\"", lambda m: f"{NUMWORDS.get(m[1], m[1])} foot {m[2]}", text)
    text = re.sub(r"(\d+)\s?p\.m\.", r"\1 P M", text)
    text = re.sub(r"(\d+):(\d\d)", r"\1 \2", text)
    text = text.replace("…", "...").replace("—", ", ").replace("–", " to ")
    text = text.replace("U.S.", "U S").replace("Mrs ", "Missus ").replace("St Helena", "Saint Helena")
    text = text.replace("St James's", "Saint James's").replace("St Vitus", "Saint Vitus")
    text = re.sub(r"\s+", " ", text).strip()
    return text


ACRONYMS = {"SOS", "U.S.", "MGM", "MI6"}
SMALL_WORDS = {"a", "an", "and", "the", "in", "of", "on", "to", "for", "at"}


def title_case(s):
    words = []
    for i, w in enumerate(s.split()):
        lw = w.lower()
        if w in ACRONYMS:
            words.append(w)
        elif i > 0 and lw in SMALL_WORDS and not words[-1].endswith(":"):
            words.append(lw)
        else:
            words.append(lw[:1].upper() + lw[1:])
    return " ".join(words)


def chapter_name(h):
    h = re.sub(r"\s*`?\[CLIP\]`?", "", h).strip()
    m = re.match(r'THE B-SIDE: ACT (\w+), "(.+)"', h)
    if m:
        return title_case(f"Act {m[1]}: {m[2]}")
    m = re.match(r'([^:]+): "(.+)"', h)
    if m:
        return title_case(f"{m[1]}: {m[2]}")
    return title_case(h.split(":")[0].strip())


def parse(md):
    body = md.split("## COLD OPEN", 1)[1]
    body = "## COLD OPEN" + body.split("### Show notes", 1)[0]
    events = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line == "---":
            continue
        if line.startswith("## "):
            events.append(("chapter", chapter_name(line[3:].strip())))
            continue
        if "[AD BREAK]" in line:
            events.append(("music", "dramatic sting"))
            continue
        if line.strip("`").lower() == "[pause]":
            events.append(("pause", 1.5))
            continue
        m = SPEAKER_RE.match(line)
        if m:
            spk, rest = m.groups()
            pos = 0
            for c in CUE_RE.finditer(rest):
                seg = clean(rest[pos:c.start()])
                if seg:
                    events.append(("line", spk, seg))
                events.append((c[1].lower(), c[2]))
                pos = c.end()
            seg = clean(rest[pos:])
            if seg:
                events.append(("line", spk, seg))
            continue
        c = CUE_RE.search(line)
        if c:
            events.append((c[1].lower(), c[2]))
    return events


# ---------------------------------------------------------------- render
def render(events, kokoro):
    out, chapters, prev = [], [], None
    pos = lambda: sum(len(x) for x in out) / SR

    def say(spk, text):
        h = HOSTS[spk]
        a, sr = kokoro.create(text, voice=h["voice"], speed=h["speed"], lang="en-us")
        assert sr == SR
        return a.astype(np.float64)

    for i, ev in enumerate(events):
        kind = ev[0]
        if kind == "chapter":
            chapters.append((round(pos(), 2), ev[1]))
            continue
        if kind == "line":
            _, spk, text = ev
            if spk == "BOTH":
                a = mix(say("NORA", text) * 0.75, say("CAL", text) * 0.75)
            else:
                a = say(spk, text)
            # Tight gaps for interruptions ("...") and quick back-and-forth.
            gap = 0.12 if (prev and prev[0] == "line" and prev[2].endswith("...")) else \
                  (0.22 if prev and prev[0] == "line" and prev[1] == spk else 0.32)
            out.append(np.zeros(int(SR * gap)))
            out.append(a)
        elif kind == "sfx":
            out.append(np.zeros(int(SR * 0.15)))
            out.append(sfx_for(ev[1]))
        elif kind == "music":
            out.append(np.zeros(int(SR * 0.3)))
            out.append(sting_for(ev[1]))
            out.append(np.zeros(int(SR * 0.2)))
        elif kind == "pause":
            out.append(np.zeros(int(SR * ev[1])))
        prev = ev
        print(f"  {i + 1}/{len(events)} {pos():7.1f}s", end="\r", file=sys.stderr)
    out.append(np.zeros(SR))
    return np.concatenate(out), chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("out")
    ap.add_argument("--model", required=True); ap.add_argument("--voices", required=True)
    ap.add_argument("--title", default=""); ap.add_argument("--cover", default="")
    ap.add_argument("--track", default="")
    a = ap.parse_args()

    from kokoro_onnx import Kokoro
    kokoro = Kokoro(a.model, a.voices)
    events = parse(Path(a.script).read_text())
    audio, chapters = render(events, kokoro)
    audio = norm(audio, 0.95)

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "raw.wav"
        sf.write(wav, audio, SR)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav)]
        if a.cover:
            cmd += ["-i", a.cover, "-map", "0:a", "-map", "1:v", "-c:v", "mjpeg",
                    "-disposition:v", "attached_pic", "-metadata:s:v", "title=Cover"]
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100",
                "-c:a", "libmp3lame", "-b:a", "128k", "-ac", "1", "-id3v2_version", "3",
                "-metadata", f"title={a.title}", "-metadata", "artist=Edge of History",
                "-metadata", "album=Edge of History", "-metadata", "genre=Podcast",
                "-metadata", f"track={a.track}", a.out]
        subprocess.run(cmd, check=True)

    Path(a.out).with_suffix(".chapters.json").write_text(json.dumps(
        {"version": "1.2.0", "chapters": [{"startTime": s, "title": n} for s, n in chapters]}, indent=2))
    print(f"\nwrote {a.out}: {len(audio) / SR / 60:.1f} min, {len(chapters)} chapters", file=sys.stderr)


if __name__ == "__main__":
    main()
