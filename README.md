# Edge of History

*A history comedy podcast. The famous story is never the whole story.*

**Nora Vance** is a former tabloid reporter who always asks "who profited?" **Cal Whitlock** is a former history teacher in a cardigan who always asks "what's the source?" Together they take the most famous, and most infamous, events in history and tell the side of the story almost nobody has heard. They bicker, make a bet every episode (Cal always loses), and then, when it matters, they drop the banter and tell you about the person history forgot.

**Listen:** https://julien-weinstein.github.io/edge-of-history/
**RSS feed:** https://julien-weinstein.github.io/edge-of-history/feed.xml

> Nora and Cal are fictional characters voiced with AI text-to-speech. The history is real, and every episode lists its sources.

## Episodes

| # | Title | Runtime | Script | Audio |
|---|---|---|---|---|
| 1 | The Mona Lisa Was a Nobody Until a Handyman Stole It | 21:55 | [script](episodes/ep01-mona-lisa.md) | [mp3](audio/ep01-mona-lisa.mp3) |
| 2 | The Titanic Sank Because of a Group Chat | 21:25 | [script](episodes/ep02-titanic.md) | [mp3](audio/ep02-titanic.mp3) |
| 3 | Napoleon Was Tall. A British Cartoonist Ruined His Life. | 19:44 | [script](episodes/ep03-napoleon.md) | [mp3](audio/ep03-napoleon.mp3) |

Episodes 4 to 10 are outlined in [`season-1.md`](season-1.md).

## Repository layout

| Path | What it is |
|---|---|
| [`show-bible.md`](show-bible.md) | The hosts, their voices, the episode structure, running gags and accuracy rules. Every script follows it. |
| [`audience-strategy.md`](audience-strategy.md) | How topics are chosen, title and thumbnail formulas, the launch plan and engagement mechanics |
| [`season-1.md`](season-1.md) | The 10-episode Season 1 guide and Season 2 ideas |
| [`episodes/`](episodes/) | Full episode scripts |
| [`audio/`](audio/) | Finished MP3s and chapter files (Podcasting 2.0 JSON) |
| [`art/`](art/) | Cover art (3000×3000) and the HTML it's rendered from |
| [`production/`](production/) | The voice and sound pipeline (`produce.py`), feed builder (`build_feed.py`) and show metadata (`show.json`) |
| [`feed.xml`](feed.xml) | The podcast RSS feed every platform reads |
| [`index.html`](index.html) | The show website, served by GitHub Pages |
| [`PUBLISHING.md`](PUBLISHING.md) | How to go live on Apple, Spotify, YouTube, Amazon and the rest, and how to release new episodes |

## Continuity tracker

Update this after every episode so the hosts stay consistent.

| Ep | Bet winner | Forfeit | Dings | Tally | Callbacks introduced |
|---|---|---|---|---|---|
| 1 | Nora | Cal reads a fake 1-star review as Shakespeare | 1 | 0 | "Respect to the handyman," the bell, Aunt Deb, Nora's lawsuit, George Clooney |
| 2 | Nora | Cal plays "My Heart Will Go On" on the recorder | 0 | 0 | The recorder, the air horn, "there's always a Mabel" |
| 3 | Nora | Cal wears a child-size foam bicorne | 1 | 0 | The hat (comes back in the finale), Cal's mother, "don't wash" |
