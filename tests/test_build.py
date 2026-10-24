"""Validate publication boundaries and the generated, usable-without-JS page."""

from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.articles = []
        self.scripts = []
        self.assets = []
        self.links = []
        self.script_data = ""
        self.in_data = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "article":
            self.articles.append(attrs)
        if tag == "script":
            self.scripts.append(attrs)
            self.in_data = attrs.get("id") == "event-data"
        if tag in {"script", "img"} and "src" in attrs:
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") != "canonical":
            self.assets.append(attrs["href"])
        if tag == "a":
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_data = False

    def handle_data(self, text):
        if self.in_data:
            self.script_data += text


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((build.ROOT / "data/events.json").read_text(encoding="utf-8"))
        self.event = self.data["events"][0]

    def assert_invalid(self, phrase):
        with self.assertRaisesRegex(build.ValidationError, phrase):
            build.validate(self.data)

    def test_checked_in_data_validates(self):
        build.validate(self.data)

    def test_calendar_date_and_reversed_range_rejected(self):
        self.event["start_date"] = "2027-02-30"
        self.assert_invalid("invalid calendar date")
        self.event["start_date"] = "2027-02-01"
        self.assert_invalid("end_date precedes")

    def test_duplicate_ids_rejected(self):
        self.data["events"].append(deepcopy(self.event))
        self.assert_invalid("duplicate event id")

    def test_event_ids_cannot_collide_with_page_ids(self):
        for key in ["directory", "theme", "event-data", "about-title", "month-2027-02", "title-another-event"]:
            with self.subTest(key=key):
                self.event["id"] = key
                self.assert_invalid("reserved page ID or namespace")

    def test_unknown_fields_rejected(self):
        self.event["personal_notes"] = "Do not publish this field"
        self.assert_invalid("unexpected.*personal_notes")

    def test_unsafe_or_malformed_links_rejected(self):
        for url in ["javascript:alert(1)", "file:///tmp/example", "https://name:password@example.org", "https://[bad"]:
            with self.subTest(url=url):
                self.event["official_url"] = url
                self.assert_invalid("URL")

    def test_url_ports_validated_for_event_and_deadline_sources(self):
        self.event["deadlines"] = [{"kind": "Registration", "date": "2026-12-01",
            "time": None, "timezone": None, "note": "", "source_url": "https://example.org/event"}]
        for record, field in [(self.event, "official_url"), (self.event["deadlines"][0], "source_url")]:
            original = record[field]
            for port in ["notaport", "99999", "-1"]:
                with self.subTest(field=field, port=port):
                    record[field] = f"https://example.org:{port}/event"
                    self.assert_invalid("invalid URL")
            record[field] = "https://example.org:8443/event"
            build.validate(self.data)
            record[field] = original

    def test_invalid_formats_and_topics_rejected(self):
        for value in [[], "School", [None], ["School & conference"], ["School", "School"], ["Unrecognized"]]:
            with self.subTest(formats=value):
                self.event["formats"] = value
                self.assert_invalid("format")
        self.event["formats"] = ["School", "Conference"]
        build.validate(self.data)
        self.event["topics"] = ["unrecognized subject"]
        self.assert_invalid("invalid or duplicate topic")

    def test_multiple_formats_share_one_entry_and_have_individual_filter_options(self):
        self.event["formats"] = ["School", "Conference"]
        self.data["events"] = [self.event]
        with TemporaryDirectory() as temp:
            output = Path(temp)
            self.assertEqual(build.build(self.data, output, "2026-10-23"), 1)
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertEqual(len(Page(html).articles), 1)
            self.assertIn('<span>School / Conference</span>', html)
            self.assertEqual(html.count('<option value="School">School</option>'), 1)
            self.assertEqual(html.count('<option value="Conference">Conference</option>'), 1)
            self.assertNotIn('School &amp; conference', html)
            exported = json.loads((output / "events.json").read_text(encoding="utf-8"))
            self.assertEqual(exported["schema_version"], 2)
            self.assertEqual(exported["events"][0]["formats"], ["School", "Conference"])

    def test_deadline_time_requires_explicit_timezone(self):
        self.event["deadlines"] = [{"kind": "Registration", "date": "2026-10-10",
            "time": "23:59", "timezone": None, "note": "", "source_url": "https://example.org/event"}]
        self.assert_invalid("must be paired")
        self.event["deadlines"][0]["timezone"] = "AoE"
        build.validate(self.data)
        self.event["deadlines"][0]["timezone"] = "Unspecified"
        self.assert_invalid("IANA timezone")

    def test_missing_timezone_data_reports_install_step(self):
        # Keep the diagnostic independent of the live calendar's deadline order.
        self.event["deadlines"] = [{"kind": "Registration", "date": "2026-10-10",
            "time": "23:59", "timezone": "Asia/Tokyo", "note": "",
            "source_url": "https://example.org/event"}]
        self.event["related_event_ids"] = []
        self.data["events"] = [self.event]
        with TemporaryDirectory() as temp:
            fixture = Path(temp) / "events.json"
            fixture.write_text(json.dumps(self.data), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-S", str(build.ROOT / "scripts/build.py"),
                 "--data", str(fixture), "--check"],
                env={**os.environ, "PYTHONTZPATH": "", "PYTHONIOENCODING": "utf-8"},
                capture_output=True, encoding="utf-8",
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot load IANA timezone 'Asia/Tokyo'", result.stderr)
        self.assertIn("python -m pip install -r requirements.txt", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_social_preview_metadata_and_image_are_in_static_output(self):
        with TemporaryDirectory() as temp:
            output = Path(temp)
            build.build(self.data, output, "2026-10-24")
            for name, suffix in [("index.html", ""), ("about.html", "about.html")]:
                html = (output / name).read_text(encoding="utf-8")
                self.assertIn(f'<meta property="og:url" content="https://ianmccul.github.io/conferences/{suffix}">', html)
                self.assertIn('<meta property="og:title" content="', html)
                self.assertIn('<meta property="og:description" content="', html)
                self.assertIn('<meta property="og:image" content="https://ianmccul.github.io/conferences/social-preview.png">', html)
            image = (output / "social-preview.png").read_bytes()
            self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(int.from_bytes(image[16:20], "big"), 1200)
            self.assertEqual(int.from_bytes(image[20:24], "big"), 630)

    def test_build_preserves_utf8_with_locale_encoding(self):
        with TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, "-X", "utf8=0", str(build.ROOT / "scripts/build.py"),
                 "--output", temp, "--today", "2026-10-23"],
                env={**os.environ, "LC_ALL": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONIOENCODING": "utf-8"},
                capture_output=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (Path(temp) / "index.html").read_text(encoding="utf-8")
            for value in ["Topic, city, institute…", "∅", "↺"]:
                self.assertIn(value, html)

    def test_unresolved_related_event_rejected(self):
        self.event["related_event_ids"] = ["missing-edition"]
        self.assert_invalid("unresolved")

    def test_timed_deadlines_use_aoe_and_iana_cutoffs(self):
        for day, clock, zone, expected in [
            ("2026-12-04", "23:59", "AoE", "2026-12-05T11:59:00+00:00"),
            ("2026-11-15", "23:59", "Asia/Tokyo", "2026-11-15T14:59:00+00:00"),
            ("2027-07-01", "15:00", "America/New_York", "2027-07-01T19:00:00+00:00"),
            ("2027-01-01", "15:00", "America/New_York", "2027-01-01T20:00:00+00:00"),
        ]:
            with self.subTest(zone=zone, day=day):
                deadline = {"date": day, "time": clock, "timezone": zone}
                self.assertEqual(build.deadline_cutoff(deadline).isoformat(), expected)
        self.assertIsNone(build.deadline_cutoff({"date": "2026-12-04", "time": None, "timezone": None}))

    def test_ambiguous_and_nonexistent_local_deadline_times_rejected(self):
        for day, clock in [("2027-03-14", "02:30"), ("2027-11-07", "01:30")]:
            with self.subTest(day=day):
                self.event["deadlines"] = [{"kind": "Registration", "date": day,
                    "time": clock, "timezone": "America/New_York", "note": "", "source_url": "https://example.org/event"}]
                self.assert_invalid("ambiguous or nonexistent")

    def test_aoe_deadline_stays_pending_until_cutoff_next_utc_day(self):
        self.event["deadlines"] = [{"date": "2026-12-04", "time": "23:59", "timezone": "AoE", "kind": "Poster"}]
        for now in ["2026-12-05T00:00:00Z", "2026-12-05T11:58:59Z", "2026-12-05T11:59:00Z"]:
            with self.subTest(now=now):
                self.assertEqual(build.deadline_summary(self.event, now), "Poster · 4 Dec 2026 · 23:59 AoE")
        self.assertEqual(build.deadline_summary(self.event, "2026-12-05T11:59:01Z"), "Recorded deadlines have passed")

    def test_reference_time_requires_timezone_and_accepts_reproducible_date(self):
        expected = datetime(2026, 12, 5, tzinfo=timezone.utc)
        self.assertEqual(build.utc_instant("2026-12-05"), expected)
        self.assertEqual(build.utc_instant("2026-12-05T08:00:00+08:00"), expected)
        with self.assertRaisesRegex(build.ValidationError, "timestamp with timezone"):
            build.utc_instant("2026-12-05T12:00:00")

    def test_generated_page_is_complete_and_subpath_portable(self):
        with TemporaryDirectory() as temp:
            output = Path(temp) / "conferences"
            count = build.build(self.data, output, "2026-10-23")
            page = Page((output / "index.html").read_text(encoding="utf-8"))
            exported = json.loads((output / "events.json").read_text(encoding="utf-8"))
            self.assertEqual(count, len(page.articles))
            self.assertEqual(len(page.ids), len(set(page.ids)), "DOM IDs must be unique")
            self.assertTrue(all("hidden" not in attrs for attrs in page.articles))
            embedded = json.loads(page.script_data)
            qip = next(e for e in embedded if e["id"] == "qip-2027")
            poster = next(d for d in qip["deadlines"] if d["kind"] == "Poster")
            self.assertEqual(poster["cutoff_utc"], "2026-12-05T11:59:00Z")
            for event in embedded:
                for deadline in event["deadlines"]:
                    cutoff = deadline.pop("cutoff_utc")
                    self.assertEqual(cutoff is None, deadline["time"] is None)
            self.assertEqual(embedded, exported["events"], "UTC cutoffs are derived only for browser use")
            self.assertEqual({a["id"] for a in page.articles}, {e["id"] for e in exported["events"]})
            pages = {name: Page((output / name).read_text(encoding="utf-8")) for name in ("index.html", "about.html")}
            self.assertNotIn("about", page.ids)
            self.assertIn("./about.html", page.links)
            self.assertIn("about", pages["about.html"].ids)
            self.assertIn("./index.html#directory", pages["about.html"].links)
            self.assertEqual(pages["about.html"].articles, [])
            for name, document in pages.items():
                self.assertEqual(len(document.ids), len(set(document.ids)), name)
                for asset in document.assets:
                    self.assertTrue(asset.startswith("./"), asset)
                    self.assertTrue((output / asset).is_file(), asset)
                for link in document.links:
                    self.assertFalse(link.startswith("/"), link)
                    target = urlsplit(link)
                    if not target.scheme:
                        path = target.path.removeprefix("./") or name
                        self.assertTrue((output / path).is_file(), link)
                        if target.fragment:
                            self.assertIn(target.fragment, pages[path].ids, link)
            self.assertTrue((output / ".nojekyll").is_file())

    def test_unpublished_records_and_references_not_exported(self):
        self.event["id"] = "unpublished-example"
        self.event["title"] = "Unpublished title sentinel"
        self.event["published"] = False
        self.data["events"][1]["related_event_ids"] = [self.event["id"]]
        with TemporaryDirectory() as temp:
            build.build(self.data, Path(temp), "2026-10-23")
            for name in ["index.html", "events.json"]:
                result = (Path(temp) / name).read_text(encoding="utf-8")
                self.assertNotIn("Unpublished title sentinel", result)
                self.assertNotIn("unpublished-example", result)

    def test_event_text_cannot_break_out_of_html_or_embedded_json(self):
        self.event["title"] = '</script><script>alert("example")</script> & a title'
        with TemporaryDirectory() as temp:
            build.build(self.data, Path(temp), "2026-10-23")
            html = (Path(temp) / "index.html").read_text(encoding="utf-8")
            page = Page(html)
            self.assertEqual(len(page.scripts), 3)
            self.assertNotIn(self.event["title"], html)
            self.assertIn("&lt;/script&gt;", html)
            self.assertEqual(json.loads(page.script_data)[0]["title"], self.event["title"])

    def test_cross_month_and_year_dates_are_visible(self):
        self.event.update(start_date="2026-12-29", end_date="2027-01-05")
        html = build.render_event(self.event, "2026-10-23", {})
        self.assertIn('class="date-end">to 5 Jan 2027', html)
        self.assertIn("29 Dec 2026 – 5 Jan 2027", html)

    def test_deadline_summary_never_infers_registration_status(self):
        self.assertEqual(build.deadline_summary(self.event, "2026-10-23"), "Deadlines not recorded")
        self.event["deadlines"] = [{"date": "2026-09-01", "kind": "Registration"}]
        self.assertEqual(build.deadline_summary(self.event, "2026-10-23"), "Recorded deadlines have passed")

    def test_date_only_deadline_remains_pending_through_utc_date(self):
        self.event["deadlines"] = [{"date": "2026-12-04", "time": None, "timezone": None, "kind": "Registration"}]
        self.assertEqual(build.deadline_summary(self.event, "2026-12-04T23:59:59Z"), "Registration · 4 Dec 2026")
        self.assertEqual(build.deadline_summary(self.event, "2026-12-05T00:00:00Z"), "Recorded deadlines have passed")


if __name__ == "__main__":
    unittest.main()
