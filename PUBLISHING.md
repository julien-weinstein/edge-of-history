# Publishing Edge of History

The show is distributed the standard way. The MP3s and an RSS feed are hosted here with GitHub Pages, and each platform is given the **feed URL** once. After that, every platform pulls new episodes automatically whenever `feed.xml` changes.

**Feed URL:** `https://julien-weinstein.github.io/edge-of-history/feed.xml`

## 1. Turn on GitHub Pages (once)

1. Go to the repository's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to *Deploy from a branch*, choose **Branch** `main` and folder `/ (root)`, then press **Save**.
3. After a minute or two, these should open in a browser:
   - https://julien-weinstein.github.io/edge-of-history/ (the show website)
   - https://julien-weinstein.github.io/edge-of-history/feed.xml (the feed)
4. Optionally, paste the feed URL into a validator such as https://podba.se/validate/ or https://castfeedvalidator.com before submitting it anywhere.

## 2. Submit the feed to each platform (once each)

Each platform needs your own account, and some send a verification code to the feed's contact email (`julienw@umich.edu`). These menus change from time to time, so if a step doesn't match what you see, look for "add a show with an RSS feed."

| Platform | Where | Steps | Also reaches |
|---|---|---|---|
| **Apple Podcasts** | podcastsconnect.apple.com | Click **+**, choose **New Show**, choose **Add a show with an RSS feed**, paste the URL and submit for review (usually a few days) | Overcast, Castro and most indie apps, which read Apple's directory |
| **Spotify** | creators.spotify.com | Choose **Get started**, then **Find an existing show**, paste the URL, and enter the code emailed to the feed address | |
| **YouTube / YouTube Music** | studio.youtube.com | Choose **Create**, then **New podcast**, then **Submit RSS feed**, paste the URL and confirm ownership | Audio-only episodes on YouTube and YouTube Music |
| **Amazon Music / Audible** | podcasters.amazon.com | Choose **Add or claim your podcast**, paste the URL and verify by email | |
| **Podcast Index** | podcastindex.org/add | Paste the URL. No account is needed. | Pocket Casts, Fountain, Podverse, Castamatic and other open apps |
| **iHeartRadio** | iheart.com/content/submit-your-podcast | Fill in the form with the feed URL | |
| **Pocket Casts** | pocketcasts.com/submit | Paste the URL (if it hasn't already appeared through Podcast Index) | |

## 3. Releasing a new episode

```bash
# 1. Write the script in episodes/, following show-bible.md.
# 2. Render it (models are not in git; see production/README.md):
python3 production/produce.py episodes/ep04-salem.md audio/ep04-salem.mp3 \
  --model production/models/kokoro-v1.0.onnx --voices production/models/voices-v1.0.bin
# 3. Add the episode (title, summary, pub_date) to production/show.json.
# 4. Rebuild the feed, then commit and push:
python3 production/build_feed.py
git add audio episodes production feed.xml && git commit -m "Episode 4" && git push
```

Every platform picks up the new episode from the feed within a few hours.

## Things to know

- **AI disclosure.** Nora and Cal are fictional and voiced with AI text-to-speech. The show description and every episode's notes say so. Keep that wording, because platforms increasingly require AI-generated content to be disclosed.
- **Hosting limits.** GitHub Pages has a soft bandwidth limit of about 100 GB a month, which is roughly 5,000 episode downloads. If the show outgrows that, move the MP3s to a podcast host or object storage, change `base_url` in `production/show.json`, rebuild the feed, and the platforms will follow automatically. Never change the feed URL itself without setting up a redirect, because that's how listeners get lost.
- **Never change an episode's audio file path after it's published.** The episode's GUID is derived from that path, so changing it makes apps treat the episode as new.
