# Production pipeline

`produce.py` turns a Markdown script from `episodes/` into a finished, loudness-normalised MP3 with chapter markers. `build_feed.py` turns `show.json` and the rendered audio into `feed.xml`.

## Voices

The hosts are voiced locally with [Kokoro-82M](https://github.com/hexgrad/kokoro), an open-weight (Apache-2.0) text-to-speech model, run through `kokoro-onnx`. Each host has **one fixed voice**, set in `HOSTS` in `produce.py`:

| Host | Voice | Speed |
|---|---|---|
| Nora Vance | `af_heart` | 1.08 |
| Cal Whitlock | `am_michael` | 0.97 |

Don't change these between episodes. The voices are the characters.

## Sound

All music stings and sound effects (the show theme, the Well-Actually bell, the air horn, the cash register, Morse code, Cal's recorder and so on) are synthesised in code. There are no samples and no licensed music. The recorder gag deliberately plays an original off-key tune, not the song the script names.

## Setup

```bash
pip install kokoro-onnx soundfile numpy
mkdir -p production/models && cd production/models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

`ffmpeg` must also be installed. Rendering runs at about four times real time on a 4-core CPU.

## Script conventions the renderer understands

- `**NORA:**`, `**CAL:**` and `**BOTH:**` are spoken lines. BOTH is both voices at once.
- `[SFX: …]` and `[MUSIC: …]` are cues, either on their own line or inline. The description picks the sound, so "ding", "air horn" and "soft piano" each map to their own synthesised sound.
- `[AD BREAK]` becomes a music bumper, `[pause]` a 1.5-second silence and `## HEADINGS` chapter markers.
- `*(stage directions)*` and `[CLIP]` marks are skipped.
- Everything after `### Show notes` is used for the episode's source list, not spoken.
