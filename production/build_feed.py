#!/usr/bin/env python3
"""Build feed.xml (the podcast RSS feed) from production/show.json.

Usage: python3 production/build_feed.py

Writes feed.xml at the repository root. When the repository is served with
GitHub Pages, the feed URL is <base_url>/feed.xml; submit that URL to each
podcast platform. Re-run after adding an episode and push.
"""
import json, re, subprocess, uuid
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
show = json.loads((ROOT / "production/show.json").read_text())
base = show["base_url"].rstrip("/")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    s = int(float(out.stdout.strip()))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def sources(script):
    md = (ROOT / script).read_text()
    if "### Show notes" not in md:
        return []
    block = md.split("### Show notes", 1)[1]
    return [re.sub(r"[*_]", "", l[2:]).strip() for l in block.splitlines() if l.startswith("- ")]


def chapters_html(mp3):
    cj = Path(str(ROOT / mp3)).with_suffix(".chapters.json")
    if not cj.exists():
        return ""
    rows = []
    for c in json.loads(cj.read_text())["chapters"]:
        s = int(c["startTime"])
        rows.append(f"{s // 60:02d}:{s % 60:02d} {escape(c['title'])}")
    return "<p><b>Chapters</b><br>" + "<br>".join(rows) + "</p>"


items = []
for ep in sorted(show["episodes"], key=lambda e: e["number"], reverse=True):
    mp3 = ROOT / ep["file"]
    if not mp3.exists():
        continue
    guid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{base}/{ep['file']}"))
    src = sources(ep["script"])
    notes = (f"<p>{escape(ep['summary'])}</p>" + chapters_html(ep["file"]) +
             ("<p><b>Sources</b></p><ul>" + "".join(f"<li>{escape(s)}</li>" for s in src) + "</ul>" if src else "") +
             "<p>Hosts Nora Vance and Cal Whitlock are fictional characters voiced with AI text-to-speech. "
             "The history is real.</p>")
    date = format_datetime(datetime.fromisoformat(ep["pub_date"].replace("Z", "+00:00")))
    chap = Path(ep["file"]).with_suffix(".chapters.json")
    items.append(f"""    <item>
      <title>{escape(ep['title'])}</title>
      <itunes:title>{escape(ep['title'])}</itunes:title>
      <itunes:episode>{ep['number']}</itunes:episode>
      <itunes:season>1</itunes:season>
      <itunes:episodeType>full</itunes:episodeType>
      <description><![CDATA[{notes}]]></description>
      <itunes:summary>{escape(ep['summary'])}</itunes:summary>
      <enclosure url="{base}/{ep['file']}" length="{mp3.stat().st_size}" type="audio/mpeg"/>
      <podcast:chapters url="{base}/{chap.as_posix()}" type="application/json+chapters"/>
      <guid isPermaLink="false">{guid}</guid>
      <pubDate>{date}</pubDate>
      <itunes:duration>{duration(mp3)}</itunes:duration>
      <itunes:explicit>{str(show['explicit']).lower()}</itunes:explicit>
      <itunes:image href="{base}/art/cover.jpg"/>
    </item>""")

feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0"
     xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{escape(show['title'])}</title>
    <link>{base}/</link>
    <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>{show['language']}</language>
    <description>{escape(show['description'])}</description>
    <itunes:summary>{escape(show['description'])}</itunes:summary>
    <itunes:author>{escape(show['author'])}</itunes:author>
    <itunes:owner>
      <itunes:name>{escape(show['owner_name'])}</itunes:name>
      <itunes:email>{escape(show['owner_email'])}</itunes:email>
    </itunes:owner>
    <itunes:image href="{base}/art/cover.jpg"/>
    <image><url>{base}/art/cover.jpg</url><title>{escape(show['title'])}</title><link>{base}/</link></image>
    <itunes:category text="{escape(show['category'])}"/>
    <itunes:explicit>{str(show['explicit']).lower()}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <podcast:locked>no</podcast:locked>
    <podcast:guid>{uuid.uuid5(uuid.UUID('ead4c236-bf58-58c6-a2c6-a6b28d128cb6'), base.split('://')[-1] + '/feed.xml')}</podcast:guid>
{chr(10).join(items)}
  </channel>
</rss>
"""
(ROOT / "feed.xml").write_text(feed)
print(f"wrote feed.xml with {len(items)} episode(s); feed URL: {base}/feed.xml")
