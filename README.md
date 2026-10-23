# Tensor-network conferences & workshops

**[Browse the calendar](https://ianmccul.github.io/conferences/)** · **[Suggest a meeting or correction](https://github.com/ianmccul/conferences/issues/new/choose)**

A curated directory of conferences, workshops, schools and research programmes on tensor networks and related areas of entanglement, quantum information and many-body physics. Coverage is worldwide, with a broader selection of related meetings in Asia.

The calendar includes event dates, locations, organizer links and recorded participation deadlines. Search by topic or location, filter by meeting type, or browse past editions. Combined schools and conferences appear under both types.

## Suggest a meeting or correction

Open an [issue](https://github.com/ianmccul/conferences/issues/new/choose) with a link to the event. Add any notes you think are useful—for example, a newly announced meeting, a changed date or an extended deadline. A link is enough to get started; you do not need to fill out a data record or edit JSON.

The AI conference monitor checks open suggestions as part of its regular daily scan. It verifies the public event information and prepares a pull request for review. Suggestions and corrections submitted as ordinary issues are welcome too.

## How updates are published

1. A suggestion arrives through an issue, or the monitor finds a new meeting or a material change on the web.
2. The monitor checks organizer or institutional sources and proposes the changes in a pull request, linking the relevant issues and sources.
3. The maintainer receives the PR link with a short summary of what changed, reviews the proposal and merges it when ready.
4. GitHub Actions validates the data, runs the tests and publishes the approved changes to the [website](https://ianmccul.github.io/conferences/).

The monitor updates an existing open proposal when appropriate, avoids duplicate submissions and does not merge its own changes. Events remain in the archive after they finish. Source access limitations are recorded with the affected entries.

## Data and contributions

[`data/events.json`](data/events.json) is the source of truth. Direct pull requests are also welcome; the [development guide](docs/DEVELOPMENT.md) explains how to edit, validate and preview the site.

| Resource | Purpose |
| --- | --- |
| [About the directory](https://ianmccul.github.io/conferences/about.html) | Scope and source information |
| [Event data](data/events.json) | Conference records and deadlines |
| [Discovery sources](data/sources.json) | Starting points for finding meetings |
| [Development guide](docs/DEVELOPMENT.md) | Local preview, checks and publishing |
| [Monitor workflow](docs/MONITORING.md) | Issue intake, verification and PR review |
| [Design and schema](docs/DESIGN.md) | Data fields and implementation choices |

Maintained by [Ian McCulloch](https://github.com/ianmccul).
