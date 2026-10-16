# NovaTV Greek Artwork EPG (unofficial)

Greek XMLTV guide for **terrestrial** Greek TV from the public Digea website, with programme-level `<icon src="..."/>` metadata where an actual programme promo image matches the guide title. No channel streams, credentials, Xtream providers or NovaTV code are changed.

The generated feed URL, **only after the first successful workflow run**:

`https://raw.githubusercontent.com/Ozigto/novatv-greek-artwork-epg/main/epg/digea-artwork.xml`

Compressed version: `https://raw.githubusercontent.com/Ozigto/novatv-greek-artwork-epg/main/epg/digea-artwork.xml.gz`

The scheduled GitHub Action refreshes approximately three times daily. Use **Actions → Refresh Greek Digea artwork XMLTV → Run workflow** to perform the first generation. Inspect `epg/status.json` for the actual programme and image counts. If the upstream website is unavailable, no new feed will be committed.

## Important limitations

- This feed is not endorsed by Digea and does **not** cover pay-TV channels like Nova and COSMOTE.
- EPG metadata is tied to Digea's published terrestrial channel schedule; a programme image is included **only when a verified Digea promotional image can be associated with a title**. Expect many programmes without artwork.
- The app must support XMLTV programme-level `<icon>` and may need a channel-name matching rule because its existing provider `tvg-id`s may not equal `digea-ID`.
- Linking to images is not permission for commercial redistribution. Verify rights before distributing NovaTV.

This public repo contains only code and publicly published programme data and artwork URLs for personal testing.
