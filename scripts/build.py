#!/usr/bin/env python3
"""Validate public conference records and build a portable static directory."""

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import shutil
from string import Template
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
FORMATS = {"Conference", "Workshop", "School", "Programme", "School & conference"}
REGIONS = {"Asia", "Europe", "North America", "South America", "Oceania", "Africa", "Online"}
TOPICS = {"Tensor networks", "Entanglement", "Quantum information", "Quantum matter",
          "Dynamics & open systems", "Numerical methods", "Gauge theories"}
EVENT_KEYS = {"id", "title", "start_date", "end_date", "location", "format", "topics",
              "summary", "official_url", "deadlines", "notes", "last_checked",
              "verification_note", "published", "related_event_ids"}
DEADLINE_KEYS = {"kind", "date", "time", "timezone", "note", "source_url"}


class ValidationError(ValueError):
    """The input is unsuitable for publication."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def text(value, context, allow_empty=False):
    require(isinstance(value, str), f"{context}: expected a string")
    require(allow_empty or bool(value.strip()), f"{context}: must not be empty")
    require(not any(ord(char) < 32 and char not in "\n\t" for char in value),
            f"{context}: contains control characters")


def iso_date(value, context):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value),
            f"{context}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{context}: invalid calendar date") from exc


def web_url(value, context):
    text(value, context)
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ValidationError(f"{context}: invalid URL") from exc
    require(parsed.scheme in {"http", "https"} and bool(parsed.hostname)
            and not parsed.username and not parsed.password
            and not any(char.isspace() for char in value), f"{context}: expected a public HTTP(S) URL")


def exact_keys(value, allowed, context):
    require(isinstance(value, dict), f"{context}: expected an object")
    require(set(value) == allowed,
            f"{context}: missing {sorted(allowed - set(value))}; unexpected {sorted(set(value) - allowed)}")


def validate(data):
    exact_keys(data, {"schema_version", "updated", "events"}, "dataset")
    require(type(data["schema_version"]) is int and data["schema_version"] == 1,
            "schema_version must be 1")
    updated = iso_date(data["updated"], "updated")
    require(isinstance(data["events"], list) and data["events"], "events must be a nonempty list")
    ids = set()
    editions = set()
    for number, event in enumerate(data["events"]):
        context = f"event {number + 1}"
        exact_keys(event, EVENT_KEYS, context)
        key = event["id"]
        require(isinstance(key, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key),
                f"{context}: id must be a lowercase slug")
        require(key not in ids, f"duplicate event id: {key}")
        ids.add(key)
        context = key
        for field in ("title", "summary"):
            text(event[field], f"{context}.{field}")
        for field in ("notes", "verification_note"):
            text(event[field], f"{context}.{field}", allow_empty=True)
        start = iso_date(event["start_date"], f"{context}.start_date")
        end = iso_date(event["end_date"], f"{context}.end_date")
        require(start <= end, f"{context}: end_date precedes start_date")
        checked = iso_date(event["last_checked"], f"{context}.last_checked")
        require(checked <= updated, f"{context}: last_checked is after dataset updated")
        location = event["location"]
        exact_keys(location, {"city", "country", "region", "venue"}, f"{context}.location")
        for field, value in location.items():
            text(value, f"{context}.location.{field}")
        require(location["region"] in REGIONS, f"{context}: unknown region")
        require(isinstance(event["format"], str) and event["format"] in FORMATS,
                f"{context}: unknown format")
        topics = event["topics"]
        require(isinstance(topics, list) and topics and all(isinstance(t, str) for t in topics),
                f"{context}: topics must be a nonempty string list")
        require(set(topics) <= TOPICS and len(topics) == len(set(topics)),
                f"{context}: invalid or duplicate topic")
        web_url(event["official_url"], f"{context}.official_url")
        edition = (event["official_url"].rstrip("/"), event["start_date"], event["title"].casefold())
        require(edition not in editions, f"{context}: duplicate event edition")
        editions.add(edition)
        require(type(event["published"]) is bool, f"{context}: published must be a boolean")
        require(isinstance(event["related_event_ids"], list)
                and all(isinstance(x, str) for x in event["related_event_ids"]),
                f"{context}: related_event_ids must be a string list")
        require(isinstance(event["deadlines"], list), f"{context}: deadlines must be a list")
        for deadline in event["deadlines"]:
            exact_keys(deadline, DEADLINE_KEYS, f"{context}.deadline")
            text(deadline["kind"], f"{context}.deadline.kind")
            text(deadline["note"], f"{context}.deadline.note", allow_empty=True)
            iso_date(deadline["date"], f"{context}.deadline.date")
            web_url(deadline["source_url"], f"{context}.deadline.source_url")
            clock, zone = deadline["time"], deadline["timezone"]
            require((clock is None) == (zone is None), f"{context}: deadline time and timezone must be paired")
            if clock is not None:
                require(isinstance(clock, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clock),
                        f"{context}: invalid deadline time")
                require(isinstance(zone, str), f"{context}: invalid deadline timezone")
                if zone != "AoE":
                    try:
                        ZoneInfo(zone)
                    except (ValueError, ZoneInfoNotFoundError) as exc:
                        raise ValidationError(f"{context}: use an IANA timezone or AoE") from exc
    for event in data["events"]:
        require(all(key in ids and key != event["id"] for key in event["related_event_ids"]),
                f"{event['id']}: unresolved or self-referential related event")
    return data


def human_date(value):
    day = date.fromisoformat(value)
    return f"{day.day} {day.strftime('%b %Y')}"


def date_range(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first == last:
        return human_date(start)
    if (first.year, first.month) == (last.year, last.month):
        return f"{first.day}–{last.day} {last.strftime('%b %Y')}"
    if first.year == last.year:
        return f"{first.day} {first.strftime('%b')} – {last.day} {last.strftime('%b %Y')}"
    return f"{human_date(start)} – {human_date(end)}"


def deadline_summary(event, today):
    remaining = sorted((d for d in event["deadlines"] if d["date"] >= today), key=lambda d: d["date"])
    if remaining:
        item = remaining[0]
        return f"{item['kind']} · {human_date(item['date'])}"
    return "Recorded deadline dates have passed" if event["deadlines"] else "Deadlines not recorded"


def render_event(event, today, by_id):
    esc = escape
    start = date.fromisoformat(event["start_date"])
    end = date.fromisoformat(event["end_date"])
    days = str(start.day) if start == end else f"{start.day}–{end.day}" if start.month == end.month and start.year == end.year else str(start.day)
    month = start.strftime("%b").upper()
    range_text = date_range(event["start_date"], event["end_date"])
    end_label = ""
    if (start.year, start.month) != (end.year, end.month):
        end_date = f"{end.day} {end.strftime('%b')}"
        if start.year != end.year:
            end_date += f" {end.year}"
        end_label = f'<span class="date-end">to {end_date}</span>'
    location = event["location"]
    place = ", ".join(dict.fromkeys((location["city"], location["country"])))
    labels = "".join(f'<span class="tag{" tag-core" if tag == "Tensor networks" else ""}">{esc(tag)}</span>' for tag in event["topics"])
    deadline_rows = []
    for item in sorted(event["deadlines"], key=lambda d: (d["date"], d["kind"])):
        clock = f" · {esc(item['time'])} {esc(item['timezone'])}" if item["time"] else ""
        note = f'<p>{esc(item["note"])}</p>' if item["note"] else ""
        deadline_rows.append(f'<li><span>{esc(item["kind"])}</span><div><a href="{esc(item["source_url"], quote=True)}">{human_date(item["date"])}</a>{clock}{note}</div></li>')
    deadlines = '<ul class="deadline-list">' + "".join(deadline_rows) + '</ul>' if deadline_rows else '<p>No deadline is recorded. Check the organizer’s page for participation details.</p>'
    notes = f'<p class="event-note">{esc(event["notes"])}</p>' if event["notes"] else ""
    verification = f'<p class="verification-note">{esc(event["verification_note"])}</p>' if event["verification_note"] else ""
    related = [by_id[key] for key in event["related_event_ids"] if by_id[key]["published"]]
    related_html = '<p class="related">Related: ' + "; ".join(f'<a href="#{item["id"]}" data-event-link="{item["id"]}">{esc(item["title"])}</a>' for item in related) + '</p>' if related else ""
    return f'''<article class="event" id="{event['id']}" data-event-id="{event['id']}" aria-labelledby="title-{event['id']}">
  <div class="event-date" aria-label="{range_text}"><span class="date-month">{month}</span><strong>{days}</strong><span class="date-year">{start.year}</span>{end_label}</div>
  <div class="event-body">
    <div class="event-kicker"><span>{esc(event['format'])}</span><span class="place">{esc(place)}</span></div>
    <h3 id="title-{event['id']}"><a href="{esc(event['official_url'], quote=True)}">{esc(event['title'])}<span class="external-arrow" aria-hidden="true">↗</span></a></h3>
    <p class="event-summary">{esc(event['summary'])}</p>
    <div class="tags">{labels}</div>
    <details><summary><span class="deadline-summary">{esc(deadline_summary(event, today))}</span><span class="details-label">Details <span aria-hidden="true">+</span></span></summary>
      <div class="event-details"><dl class="event-facts"><div><dt>Dates</dt><dd>{range_text}</dd></div><div><dt>Venue</dt><dd>{esc(location['venue'])}</dd></div></dl>
      {notes}<h4>Participation deadlines</h4>{deadlines}
      <p class="date-note">A recorded deadline does not confirm that places are available. Date-only deadlines have no assumed cutoff time.</p>
      {related_html}<div class="source-row"><a href="{esc(event['official_url'], quote=True)}">Organizer’s website ↗</a><span>Last checked {human_date(event['last_checked'])}</span><a href="#{event['id']}" class="permalink" aria-label="Link to {esc(event['title'], quote=True)}">Permalink</a></div>{verification}
      </div>
    </details>
  </div>
</article>'''


def options(values):
    return "".join(f'<option value="{escape(value, quote=True)}">{escape(value)}</option>' for value in sorted(values))


def render_page(content, *, about=False, event_json=None):
    layout = Template((ROOT / "site/layout.template.html").read_text(encoding="utf-8"))
    title = "About | Tensor-network conferences & workshops" if about else "Tensor-network conferences & workshops"
    description = (
        "About this curated calendar of tensor-network meetings, its scope and how to contribute."
        if about else "A curated calendar of tensor-network conferences, workshops and schools, with related meetings in quantum many-body physics."
    )
    return layout.substitute(
        title=escape(title), description=escape(description, quote=True), content=content,
        skip_href="#about" if about else "#directory",
        skip_label="Skip to about this directory" if about else "Skip to conferences",
        directory_href="./index.html#directory" if about else "#directory",
        directory_current="" if about else ' aria-current="page"',
        about_current=' aria-current="page"' if about else "",
        page_data=f'<script type="application/json" id="event-data">{event_json}</script>' if event_json is not None else "",
    )


def build(data, output, today):
    validate(data)
    output.mkdir(parents=True, exist_ok=True)
    by_id = {event["id"]: event for event in data["events"]}
    public = sorted(({
        **event,
        "related_event_ids": [key for key in event["related_event_ids"] if by_id[key]["published"]],
    } for event in data["events"] if event["published"]), key=lambda e: (e["start_date"], e["title"]))
    require(public, "at least one event must be published")
    groups = defaultdict(list)
    for event in public:
        groups[event["start_date"][:7]].append(event)
    cards = []
    for month, events in groups.items():
        label = date.fromisoformat(month + "-01").strftime("%B %Y")
        cards.append(f'<section class="month-group" aria-labelledby="month-{month}"><h2 class="month-heading" id="month-{month}">{label}<span class="month-count">{len(events):02}</span></h2>' + "".join(render_event(e, today, by_id) for e in events) + '</section>')
    serialized = json.dumps(public, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = Template((ROOT / "site/index.template.html").read_text())
    html = template.substitute(
        cards="\n".join(cards), updated=human_date(data["updated"]),
        count=len(public), countries=len({e["location"]["country"] for e in public}),
        years=f"{public[0]['start_date'][:4]}—{max(e['end_date'] for e in public)[:4]}",
        regions=options({e["location"]["region"] for e in public}),
        formats=options({e["format"] for e in public}), topics=options({tag for e in public for tag in e["topics"]}),
        build_date=today,
    )
    (output / "index.html").write_text(render_page(html, event_json=serialized), encoding="utf-8")
    about = (ROOT / "site/about.template.html").read_text(encoding="utf-8")
    (output / "about.html").write_text(render_page(about, about=True), encoding="utf-8")
    for name in ("styles.css", "app.js", "favicon.svg"):
        shutil.copyfile(ROOT / "site" / name, output / name)
    (output / ".nojekyll").write_text("")
    (output / "events.json").write_text(json.dumps({**data, "events": public}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(public)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/events.json")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--today", default=datetime.now(timezone.utc).date().isoformat(), help="UTC calendar date for reproducible builds")
    parser.add_argument("--check", action="store_true", help="Validate data without writing output")
    args = parser.parse_args()
    try:
        iso_date(args.today, "--today")
        data = validate(json.loads(args.data.read_text(encoding="utf-8")))
        if args.check:
            print(f"Validated {len(data['events'])} event records.")
        else:
            count = build(data, args.output, args.today)
            print(f"Built {count} events in {args.output}")
    except (ValidationError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()

