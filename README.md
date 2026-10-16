# NovaTV Greek Artwork EPG (unofficial)

Unofficial XMLTV for Greek terrestrial TV. EPG schedules come from Digea and the official ERT sites; programme artwork is matched from **Alpha, ANT1, MEGA, Star, SKAI, OPEN, ERT1, ERT2, ERT3, ERT Cosmos and Digea**. Programme-level `<icon src="..."/>` values refer to images actually published on those broadcasters' pages. No IPTV streams, credentials, Xtream providers or NovaTV application code are changed.

The generated feed URL, **only after the first successful workflow run**:

`https://raw.githubusercontent.com/Ozigto/novatv-greek-artwork-epg/main/epg/digea-artwork.xml`

Compressed version: `https://raw.githubusercontent.com/Ozigto/novatv-greek-artwork-epg/main/epg/digea-artwork.xml.gz`

The scheduled GitHub Action refreshes approximately three times daily. It loads five days of programme schedules and current official artwork. Use **Actions → Refresh Greek Digea artwork XMLTV → Run workflow** to perform the first generation. Inspect `epg/status.json` for the actual programme and image counts. If the upstream website is unavailable, no new feed will be committed.

## Important limitations

- This unofficial feed is not endorsed by Digea or any broadcaster. It does **not** cover pay-TV channels such as Nova, COSMOTE or Magenta.
- Digea's published terrestrial guide is combined with original ERT public-service programme listings. Artwork comes from official broadcaster programme/show pages, scoped to the matching channel. Many local programmes still have no image.
- The app must support XMLTV **programme-level** `<icon>`. Xtream `tvg-id`s may not equal `digea-ID` / `ert-ert1` etc., so the player may need matching via XMLTV `<display-name>`.
- Linking to images is not permission for commercial redistribution. Verify rights before distributing NovaTV.

Run status: [epg/status.json](epg/status.json), including live picture totals per source.\n\nThis public repo contains only code and publicly published programme data and artwork URLs for personal testing.
