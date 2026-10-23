# Working on this repository

Build with `python3 scripts/build.py`. Verify changes with:

```sh
python3 -m unittest discover -s tests -v
node --test tests/*.test.cjs
```

- `data/events.json` is authoritative. Read `docs/DESIGN.md` before changing its schema.
- Use official organizer or institutional pages for event dates and deadlines. Record verification limitations; do not infer registration status from missing or expired dates.
- Preserve event IDs and retain past editions. Keep related programmes and short meetings distinct.
- This repository contains public-facing material only. Do not add personal attendance plans, rankings or private scan notes, even to unpublished records.
- Keep build logic on the Python standard library; IANA data comes from the host database or the `tzdata` fallback in `requirements.txt`. Do not fetch dependencies during the build. Keep the generated page usable without JavaScript and use relative asset paths for GitHub Pages under `/conferences/`.
- Do not commit `dist/`, local preview configuration, caches or temporary research files.
- Publication is opt-in through `PUBLISH_PAGES=true` and Pages settings. Preserve that gate unless a user explicitly asks to change it.
- The existing conference-watch automation is outside this repository; do not modify it as part of routine site development.
