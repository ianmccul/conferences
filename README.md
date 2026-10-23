# Tensor-network conferences & workshops

A curated directory of tensor-network meetings and selected related events in entanglement, quantum information and many-body physics. The initial list covers October 2026–October 2027, with broader regional coverage in Asia.

The intended address is **https://ianmccul.github.io/conferences/**. Publishing is disabled by default. The site is independent of the `teaching` repository and can later be linked from a personal homepage.

## Develop and preview

Python 3.10+ builds the site with its standard library plus IANA timezone data. Linux and macOS usually supply this data through the operating system. On Windows, or a minimal host without that database, install the first-party Python `tzdata` fallback:

```sh
python -m pip install -r requirements.txt
```

No Python packages are needed when the system timezone database is available. The build does not download data automatically. Node 18+ is needed only for the JavaScript tests. No npm packages, framework or database server are required. The commands below use `python3`; on Windows use `python` (or `py -3`) instead.

```sh
python3 scripts/build.py
python3 -m http.server --directory dist 8000
```

Open http://localhost:8000. Alternatively, open `dist/index.html` directly: the event data is embedded, so filtering also works from a downloaded copy. All event entries remain readable without JavaScript. The header’s theme selector offers System, Light and Dark; an explicit choice is remembered in the browser. Without JavaScript, colours follow the system preference. The About link opens `about.html`, with the directory’s scope, contribution links and data download.

```sh
python3 scripts/build.py --check
python3 -m unittest discover -s tests -v
node --test tests/*.test.cjs
```

The build uses the current instant for deadline summaries. `python3 scripts/build.py --now 2026-12-05T11:58:00Z` fixes that instant for reproducible output; `--today 2026-10-23` is shorthand for midnight UTC on that date. Explicitly timed deadlines use their recorded timezone, including AoE. Date-only deadlines remain pending through their UTC calendar date without assuming a precise cutoff. The browser refreshes summaries on return to the page and once a minute while visible. These summaries do not infer registration availability.

## Edit the calendar

| File | Purpose |
| --- | --- |
| `data/events.json` | Authoritative event records, source links and verification dates |
| `data/sources.json` | Discovery sources for finding future meetings |
| `scripts/build.py` | Validation and static HTML generation |
| `site/` | Directory and About templates, shared layout, styles and browser filtering |
| `tests/` | Publication, validation and filtering checks |
| `docs/DESIGN.md` | Data schema, update workflow and design choices |

1. Verify the event and each changed deadline against the organizer or institutional source.
2. Edit `data/events.json`. Keep the event's stable `id`; use a new ID for a new annual edition.
3. Update the entry's `last_checked` and the dataset's `updated` date. Describe any verification limitation in `verification_note`.
4. Run the checks above, review the generated page, and open a pull request.

Keep past meetings: the default view shows upcoming and ongoing events, while the date controls expose the archive. Filters can be shared through URL query parameters, and each entry has a permalink.

Meeting types can overlap: use `"formats": ["School", "Conference"]` for a combined event so either filter finds it. The available types are `School`, `Conference`, `Workshop` and `Programme`. Each event is counted once, regardless of how many types it has. The data uses schema version 2.

The JSON schema is enforced by the build script. Unknown fields, invalid dates, unsafe URL schemes, malformed ports, duplicate or reserved IDs and unresolved related-event links fail the build. `published: false` excludes an event and its references from both the HTML and the downloadable JSON. It does **not** hide it from repository readers or Git history. Store only public-facing information in this repository.

## Review without publishing

GitHub Actions runs the checks and builds on pull requests and pushes to `main`. Separate Linux and Windows jobs install the timezone fallback, disable the system timezone lookup and exercise locale-based text encoding. A successful run provides a `conference-site` artifact: download it, extract the ZIP and open `index.html`. Access to this artifact follows repository access; it is not a deployed website.

## Publish when ready

A private repository does not automatically mean a private GitHub Pages site. Review the generated content before enabling Pages. GitHub Pages availability for private repositories depends on the account plan.

When publication is intended:

1. Merge the reviewed change into `main`.
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source.
3. In **Settings → Secrets and variables → Actions → Variables**, add the repository variable `PUBLISH_PAGES` with the value `true`.
4. Run **Validate and build conference site** from the Actions tab on `main`, or push a new change to `main`.

The workflow grants deployment permissions only to its deployment job, and it deploys only from `main` with that explicit variable set. Assets use relative URLs so the project works under `/conferences/` or on a future custom domain.

Removing the variable stops future deployments; it does not remove an already published site. Unpublish through GitHub Pages settings if required.

See [GitHub's publishing-source instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Future updates

The first version uses reviewed commits. It does not run a scraper or change any existing conference-watch automation. A later updater can propose edits to `data/events.json` in a pull request, using the same validation and review flow. A Google Sheet or Drive export could feed that file later without changing the website.
