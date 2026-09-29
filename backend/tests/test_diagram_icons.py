"""Tests for n8n icon lookup (services.diagram_builder).

`fetch_icon_from_n8n` is mocked out in every other diagram test, so nothing
covered how a catalogue entry is chosen. Two defects lived there:

  * a miss fell back to `data[0]` -- the catalogue's first entry, observed to
    be `Auto-Scaling-group`. SNS and KMS both rendered as an Auto Scaling icon
    with no log line. A wrong icon is harder to notice than a grey box.
  * the first substring hit won, so `S3` matched `S3 on Outposts` instead of
    `Simple Storage Service`.

The fixtures below use the real catalogue's shape and names (315 AWS entries,
`icon_name` + `svg_content`).
"""

import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import

from hypothesis import given
from hypothesis import strategies as st

from services.diagram_builder import (
    _icon_match_score,
    _normalise_icon_name,
    _select_icon_entry,
    fetch_icon_from_n8n,
)

# Names taken verbatim from the live catalogue.
CATALOGUE = [
    {"icon_name": "Auto-Scaling-group.svg", "svg_content": "<svg>asg</svg>"},
    {"icon_name": "AWS Lambda", "svg_content": "<svg>lambda</svg>"},
    {"icon_name": "S3 on Outposts", "svg_content": "<svg>outposts</svg>"},
    {"icon_name": "Simple Storage Service", "svg_content": "<svg>s3</svg>"},
    {"icon_name": "Simple Storage Service Glacier", "svg_content": "<svg>glacier</svg>"},
    {"icon_name": "Simple Notification Service", "svg_content": "<svg>sns</svg>"},
    {"icon_name": "AWS Key Management Service", "svg_content": "<svg>kms</svg>"},
    {"icon_name": "CloudWatch", "svg_content": "<svg>cw</svg>"},
    {"icon_name": "CloudWatch Logs", "svg_content": "<svg>cwlogs</svg>"},
    {"icon_name": "AWS WAF", "svg_content": "<svg>waf</svg>"},
]


def _name_of(entry):
    return entry["icon_name"] if entry else None


class Normalisation(unittest.TestCase):
    def test_strips_svg_suffix_and_vendor_prefix(self):
        self.assertEqual(_normalise_icon_name("Auto-Scaling-group.svg"), "auto scaling group")
        self.assertEqual(_normalise_icon_name("AWS Lambda"), "lambda")
        self.assertEqual(_normalise_icon_name("Amazon CloudWatch"), "cloudwatch")

    def test_is_punctuation_and_case_insensitive(self):
        self.assertEqual(_normalise_icon_name("API-Gateway"), _normalise_icon_name("api gateway"))


class Selection(unittest.TestCase):
    def test_expands_abbreviations_the_catalogue_does_not_use(self):
        """The catalogue has no entry containing "SNS" or "KMS" at all."""
        self.assertEqual(
            _name_of(_select_icon_entry(CATALOGUE, "SNS")), "Simple Notification Service"
        )
        self.assertEqual(
            _name_of(_select_icon_entry(CATALOGUE, "KMS")), "AWS Key Management Service"
        )

    def test_exact_match_beats_substring_hit(self):
        """`S3` is a substring of `S3 on Outposts`; the wanted entry is not."""
        self.assertEqual(
            _name_of(_select_icon_entry(CATALOGUE, "S3")), "Simple Storage Service"
        )

    def test_prefers_the_shorter_name_on_a_tie(self):
        self.assertEqual(_name_of(_select_icon_entry(CATALOGUE, "CloudWatch")), "CloudWatch")

    def test_vendor_prefix_does_not_prevent_an_exact_match(self):
        self.assertEqual(_name_of(_select_icon_entry(CATALOGUE, "Lambda")), "AWS Lambda")
        self.assertEqual(_name_of(_select_icon_entry(CATALOGUE, "WAF")), "AWS WAF")

    def test_a_miss_returns_none_rather_than_the_first_entry(self):
        """The regression: this used to hand back `Auto-Scaling-group`."""
        self.assertIsNone(_select_icon_entry(CATALOGUE, "Cloud Spanner"))
        self.assertIsNone(_select_icon_entry(CATALOGUE, "BigQuery"))

    def test_a_catalogue_name_buried_in_the_service_name_is_not_a_match(self):
        """Observed against the live catalogue, which holds only AWS icons.

        `Q` is a real entry there, and `"q"` is a substring of `"bigquery"`.
        `AWS-Cloud` normalises to `cloud`, a substring of `cloud spanner`.
        Both produced a confident, wrong icon for a non-AWS service.
        """
        catalogue = CATALOGUE + [
            {"icon_name": "Q", "svg_content": "<svg>q</svg>"},
            {"icon_name": "AWS-Cloud.svg", "svg_content": "<svg>cloud</svg>"},
        ]
        self.assertIsNone(_select_icon_entry(catalogue, "BigQuery"))
        self.assertIsNone(_select_icon_entry(catalogue, "Cloud Spanner"))
        # The same entries must still be reachable when actually asked for.
        self.assertEqual(_name_of(_select_icon_entry(catalogue, "Q")), "Q")

    def test_ignores_non_dict_entries(self):
        self.assertIsNone(_select_icon_entry(["nonsense", 42], "Lambda"))

    @given(st.text(min_size=1, max_size=30))
    def test_never_returns_an_unmatched_entry(self, service_name):
        """Whatever is asked for, the answer is either a real match or None."""
        entry = _select_icon_entry(CATALOGUE, service_name)
        if entry is not None:
            self.assertGreater(_icon_match_score(service_name, entry["icon_name"]), 0)


class WordBoundary(unittest.TestCase):
    def test_word_boundary_scores_above_bare_substring(self):
        boundary = _icon_match_score("gateway", "API Gateway")
        buried = _icon_match_score("ecs", "Secsomething")
        self.assertGreater(boundary, buried)


def _response(status_code=200, payload=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json = MagicMock(return_value=payload)
    return response


def _client_returning(response):
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class FetchFallsBackLoudly(unittest.IsolatedAsyncioTestCase):
    """Every degraded path must say so; a grey icon must never be silent."""

    async def _fetch(self, response, service="Lambda"):
        with patch.dict("os.environ", {"N8N_WEBHOOK_URL": "https://n8n.example/webhook"}):
            with patch("httpx.AsyncClient", return_value=_client_returning(response)):
                with self.assertLogs("services.diagram_builder", level="WARNING") as logs:
                    svg = await fetch_icon_from_n8n(service)
        return svg, "\n".join(logs.output)

    async def test_non_200_is_logged(self):
        svg, logged = await self._fetch(_response(status_code=503))
        self.assertIn("#cccccc", svg)
        self.assertIn("503", logged)

    async def test_catalogue_miss_is_logged(self):
        svg, logged = await self._fetch(_response(payload=CATALOGUE), service="Cloud Spanner")
        self.assertIn("#cccccc", svg)
        self.assertIn("Cloud Spanner", logged)

    async def test_matched_entry_without_svg_is_logged(self):
        payload = [{"icon_name": "AWS Lambda"}]
        svg, logged = await self._fetch(_response(payload=payload))
        self.assertIn("#cccccc", svg)
        self.assertIn("SVG", logged)


class FetchSucceeds(unittest.IsolatedAsyncioTestCase):
    async def _fetch(self, response, service):
        with patch.dict("os.environ", {"N8N_WEBHOOK_URL": "https://n8n.example/webhook"}):
            with patch("httpx.AsyncClient", return_value=_client_returning(response)):
                return await fetch_icon_from_n8n(service)

    async def test_returns_the_matched_svg(self):
        svg = await self._fetch(_response(payload=CATALOGUE), "SNS")
        self.assertEqual(svg, "<svg>sns</svg>")

    async def test_accepts_a_raw_svg_body(self):
        svg = await self._fetch(_response(text="<svg>direct</svg>"), "Lambda")
        self.assertEqual(svg, "<svg>direct</svg>")

    async def test_accepts_a_dict_payload(self):
        svg = await self._fetch(_response(payload={"svg_content": "<svg>d</svg>"}), "Lambda")
        self.assertEqual(svg, "<svg>d</svg>")

    async def test_accepts_a_nested_dict_payload(self):
        svg = await self._fetch(_response(payload={"data": {"svg": "<svg>n</svg>"}}), "Lambda")
        self.assertEqual(svg, "<svg>n</svg>")

    async def test_unset_webhook_url_returns_the_placeholder(self):
        with patch.dict("os.environ", {"N8N_WEBHOOK_URL": ""}):
            svg = await fetch_icon_from_n8n("Lambda")
        self.assertIn("#cccccc", svg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
