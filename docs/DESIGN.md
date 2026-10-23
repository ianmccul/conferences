# Conference directory design

## Purpose and scope

Make a useful, easily maintained public calendar for tensor-network researchers, starting with the existing conference scan. Direct tensor-network events are tagged explicitly; selected related meetings in entanglement, quantum information, quantum matter, dynamics and numerical methods provide context. Programmes, schools and short meetings have separate type labels.

The first version contains 29 meetings, including separate records for the NQS2027 programme, school and conference, checked on 23 October 2026. Dates and deadlines link to organizer or institutional pages. An indexed official listing sometimes supplies dates when the page cannot be opened; those limitations are recorded explicitly. Discovery lists are leads, not authority for a participation deadline.

This repository is a standalone GitHub Pages project. It needs neither a root `ianmccul.github.io` site nor changes to the existing teaching site. A future homepage can link to `/conferences/`.

## Implementation

`data/events.json` is the source of truth. A Python standard-library script validates it, escapes all rendered text, then emits HTML, CSS, a small JavaScript file, a favicon and a public JSON export into `dist/`. No source pages are fetched during the build. The directory (`index.html`) and standalone About page (`about.html`) share `site/layout.template.html` for navigation, theme controls and the footer. Relative HTML links work under `/conferences/` and in an extracted download; filtering initializes only on the directory page.

The complete public list is rendered at build time. JavaScript adds combined search, region, topic and meeting-type filters; upcoming/ongoing, past and all-date views; counts; URL state; and permalink handling. It reads embedded JSON rather than making network requests. Every event remains readable when JavaScript is unavailable, and the downloaded site can be opened locally.

Dates use ISO `YYYY-MM-DD` strings. Meeting date ranges are inclusive and local to their venue. The browser uses the current UTC calendar date when deciding which date view contains an entry, so classification can differ from venue time near midnight. No current availability or registration-open status is inferred. Deadline times are displayed only when a source supplies both the time and its timezone. `AoE` means Anywhere on Earth, a fixed UTC−12 offset.

Explicitly timed deadlines remain pending through their recorded cutoff instant. Python converts the source time using the IANA timezone database (including daylight-saving rules), or the fixed AoE offset. The embedded browser JSON adds a derived `cutoff_utc` field to each deadline; it is `null` for date-only entries. The source and downloadable JSON retain the schema below. Python and JavaScript compare the same UTC instants; the browser refreshes summaries on return and once a minute while visible. Date-only deadlines retain UTC calendar-date comparison without inventing a precise cutoff. Summaries order timed deadlines by their cutoff and date-only entries by date at UTC midnight. Ambiguous or nonexistent local times around daylight-saving changes fail validation until the source cutoff is clarified.

The page uses system fonts, native form controls and native `<details>` disclosures, with keyboard focus styles, a skip link, live result counts and a narrow-screen layout. It has no analytics or external asset dependencies. Light and dark colour palettes follow the system by default; the header selector can override that preference and stores the choice locally in the browser. A small script applies saved choices before the stylesheet loads to avoid a flash of the wrong theme. Without JavaScript, CSS still follows the system preference. Print output always uses the light palette.

## Event schema

The top-level object has exactly `schema_version: 2`, `updated` (ISO date) and `events` (a nonempty array). Version 2 replaces the single `format` string with a `formats` array. Each event has the following required fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable lowercase hyphenated slug, including edition/year; template IDs, `event-data`, and the `month-` and `title-` prefixes are reserved |
| `title` | Public event title |
| `start_date`, `end_date` | Inclusive ISO date range |
| `location` | Object with `city`, `country`, `region`, `venue` |
| `formats` | Nonempty list of distinct meeting types: `Conference`, `Workshop`, `School`, `Programme` |
| `topics` | Nonempty list of allowed subject tags |
| `summary` | Short factual description of the meeting's scope |
| `official_url` | Organizer or institutional event page |
| `deadlines` | Array of the deadline objects described below; empty if none is recorded |
| `notes` | Public practical context, or an empty string |
| `last_checked` | Date of the entry's most recent source check |
| `verification_note` | Scope/limitations of that check, or an empty string |
| `published` | Boolean controlling inclusion in generated output |
| `related_event_ids` | IDs connecting a programme and its short meetings, or an empty array |

Meeting types can overlap. A combined school and conference uses `"formats": ["School", "Conference"]` and appears when either type is selected. The filter offers individual types only, while the entry displays all its types. Each event is listed and counted once. The `format` URL parameter still represents the single type selected in the filter. A long programme and a separately dated school or conference continue to have distinct records connected through `related_event_ids`.

Allowed regions are `Asia`, `Europe`, `North America`, `South America`, `Oceania`, `Africa`, `Online`. For the initial physical meetings, `country` is a geographic display label that may include a territory.

Allowed topics are `Tensor networks`, `Entanglement`, `Quantum information`, `Quantum matter`, `Dynamics & open systems`, `Numerical methods`, `Gauge theories`. These constants live in `scripts/build.py` and can be extended deliberately.

Each deadline object has exactly these fields:

```json
{
  "kind": "Registration",
  "date": "2027-01-15",
  "time": null,
  "timezone": null,
  "note": "",
  "source_url": "https://example.org/meeting/registration"
}
```

`kind` distinguishes registration, abstracts, funding priority, applications and other participation steps. `time` is `HH:MM` when explicitly supplied; `timezone` is an IANA identifier or `AoE`. They must either both be strings or both be `null`. Never turn a funding deadline into a registration deadline or assume a timezone from the venue. An expired abstract deadline does not establish that registration has closed.

Unknown fields are rejected. Personal travel preferences, attendance plans, rankings and private research notes belong outside this repository, including for unpublished entries. Excluding a record from generated output is an editorial control, not a confidentiality mechanism.

## Update workflow

Start with manual or agent-assisted pull requests. A scan produces proposed event additions or changes, with official source links and an explicit verification date. Review those changes as a diff in the canonical JSON; run the tests and build; merge when the content is ready. Once Pages is enabled, a merge to `main` publishes the approved data.

Use these rules for any later automatic updater:

- Preserve IDs across edits and make a new ID for a new edition.
- Keep old meetings for the archive; do not silently remove them after they finish.
- Preserve distinctions between a long programme and a related short conference.
- Recheck the official source before changing a deadline. If a check fails, do not claim fresh verification of that detail; record what was and was not confirmed.
- Include source URLs and meaningful changes in the pull-request description.
- Use the existing validator and tests before proposing a commit.
- Do not automatically merge uncertain changes or claim completeness of the directory.

No scheduled update integration is enabled in this version. The existing conference-watch process can later be adapted to create pull requests. A Drive or Sheets workflow is also possible, but an importer should generate this same schema and pass the same review gate. Introducing a second authoritative store now would add synchronization work without improving the first version.

## Deployment and review

Pull requests and pushes to `main` run validation, Python tests, JavaScript tests and a static build. Each successful run saves a downloadable artifact for review. Deployment additionally requires `main`, a non-PR event and `PUBLISH_PAGES=true`. Pages settings must also use GitHub Actions.

Keep publishing disabled during private development. Repository visibility and website visibility are separate decisions. The workflow never changes either repository privacy or Pages settings. There is no deployment from pull-request branches.

## Deliberately deferred

A calendar subscription feed, deadline reminder emails, map, submission form, scheduled scraper, root personal website and custom domain can be added later. The current data model and static output leave those options open without requiring them for a useful directory. Choose a code/content license before inviting public reuse.
