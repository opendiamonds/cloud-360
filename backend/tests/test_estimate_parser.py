"""Tests for estimate_parser (FR2 / NFR3 / NFR4)."""

from __future__ import annotations

import io
import unittest

from hypothesis import given, settings, strategies as st

from cost.estimate_parser import parse
from cost.estimate_readers import MAX_PAYLOAD_BYTES


def _aws_csv(rows: list[tuple[str, str, str, str, str, str]]) -> bytes:
    header = "Description,Service,Region,Quantity,Monthly cost,Currency\n"
    body = "".join(
        f"{d},{s},{r},{q},{m},{c}\n" for d, s, r, q, m, c in rows
    )
    return (header + body).encode("utf-8")


def _minimal_xlsx(headers: list[str], rows: list[list[str]]) -> bytes:
    """Build a tiny xlsx via openpyxl."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestEstimateParser(unittest.TestCase):
    def test_aws_csv_resolves_and_parses(self):
        raw = _aws_csv(
            [
                ("EC2 box", "Amazon EC2", "us-east-1", "2", "10.00", "USD"),
                ("Total", "", "", "", "10.00", "USD"),
            ]
        )
        result = parse(raw, "estimate.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "aws")
        self.assertEqual(result["sourceFormat"], "csv")
        self.assertGreaterEqual(len(result["lines"]), 1)
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(result["lines"][0]["quantity"], 2.0)
        self.assertEqual(result["lines"][0]["amount"], 10.0)
        self.assertEqual(result["lines"][0]["itemName"], "EC2 box")

    def test_aws_modern_calculator_csv_resolves(self):
        """Current AWS Pricing Calculator: Monthly + Service, Description often blank."""
        raw = (
            "Estimate summary\n"
            "Upfront cost,Monthly cost,Total 12 months cost,Currency\n"
            "0,116.42,1397.04,USD\n"
            "\n"
            "Detailed Estimate\n"
            "Group hierarchy,Region,Description,Service,Upfront,Monthly,"
            "First 12 months total,Currency,Status,Configuration summary\n"
            "My Estimate,Asia Pacific (Jakarta),,Amazon API Gateway,0,90.3,1083.60,USD,,HTTP API\n"
            "My Estimate,Asia Pacific (Jakarta),,Amazon EventBridge,0,3.5,42.00,USD,,Events\n"
            "My Estimate,Asia Pacific (Jakarta),,AWS Data Transfer,0,20.48,245.76,USD,,DT\n"
        ).encode("utf-8")
        result = parse(raw, "AWS.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "aws")
        names = [ln["itemName"] for ln in result["lines"]]
        self.assertEqual(
            names,
            ["Amazon API Gateway", "Amazon EventBridge", "AWS Data Transfer"],
        )
        self.assertEqual(result["lines"][0]["quantity"], 1.0)
        self.assertEqual(result["lines"][0]["amount"], 90.3)
        self.assertEqual(result["totals"]["statedTotal"], 114.28)
        self.assertEqual(result["totals"]["currency"], "USD")

    def test_blank_amount_or_service_rows_are_dropped(self):
        """Only rows with a service name and a numeric amount are kept."""
        raw = _minimal_xlsx(
            [
                "Service name",
                "Region",
                "Quantity",
                "Estimated monthly cost",
                "Currency",
            ],
            [
                ["Virtual Machines", "eastus", "1", "12.5", "USD"],
                ["", "eastus", "", "", "USD"],  # blank service + amount
                ["Storage Accounts", "eastus", "", "", "USD"],  # blank amount
                ["", "eastus", "1", "3.0", "USD"],  # blank service
                ["App Service", "eastus", "", "8.0", "USD"],  # blank qty OK
                ["Total", "", "", "20.5", "USD"],
            ],
        )
        result = parse(raw, "estimate.xlsx")
        self.assertEqual(result["detection"]["status"], "resolved")
        names = [ln["itemName"] for ln in result["lines"]]
        self.assertEqual(names, ["Virtual Machines", "App Service"])
        self.assertEqual(result["lines"][1]["quantity"], 1.0)
        self.assertEqual(result["lines"][1]["amount"], 8.0)
        self.assertEqual([ln["ordinal"] for ln in result["lines"]], [0, 1])
        self.assertEqual(result["totals"]["statedTotal"], 20.5)
        self.assertEqual(result["totals"]["currency"], "USD")

    def test_stated_total_falls_back_to_line_sum(self):
        raw = _aws_csv(
            [
                ("EC2", "Amazon EC2", "us-east-1", "1", "10.00", "USD"),
                ("S3", "Amazon S3", "us-east-1", "1", "2.50", "USD"),
            ]
        )
        result = parse(raw, "estimate.csv")
        self.assertEqual(result["totals"]["statedTotal"], 12.5)
        self.assertEqual(result["totals"]["currency"], "USD")

    def test_unidentifiable_amount_row_is_dropped(self):
        """Rows whose amount cannot be parsed are not stored or shown."""
        raw = _aws_csv(
            [
                ("Broken", "Amazon EC2", "us-east-1", "N/A", "oops", "USD"),
                ("Ok", "Amazon S3", "us-east-1", "1", "1.50", "USD"),
            ]
        )
        result = parse(raw, "estimate.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(len(result["lines"]), 1)
        self.assertEqual(result["lines"][0]["itemName"], "Ok")
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")

    def test_oversized_csv_returns_ambiguous(self):
        # Craft payload whose UTF-8 length exceeds 32 MiB without 50k+ rows.
        huge = b"Description,Service,Region,Quantity,Monthly cost,Currency\n"
        pad = b"x" * (MAX_PAYLOAD_BYTES + 10)
        # Keep as one oversized "cell" line — reader rejects by byte length
        raw = huge + pad + b",Amazon EC2,us-east-1,1,1,USD\n"
        result = parse(raw, "big.csv")
        self.assertEqual(result["detection"]["status"], "ambiguous")
        self.assertEqual(result["lines"], [])

    def test_azure_xlsx_resolves(self):
        raw = _minimal_xlsx(
            [
                "Service name",
                "Region",
                "Quantity",
                "Estimated monthly cost",
                "Currency",
            ],
            [["Virtual Machines", "eastus", "1", "12.5", "USD"]],
        )
        result = parse(raw, "estimate.xlsx")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "azure")
        self.assertEqual(result["sourceFormat"], "xlsx")
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")

    def test_azure_xlsx_without_quantity_defaults_to_one(self):
        """Official Azure exports often omit Quantity and put headers after a title."""
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["Azure Pricing Calculator"])
        ws.append(["Exported on", "2026-09-20"])
        ws.append([])
        ws.append(
            [
                "Service Category",
                "Service Type",
                "Service Name",
                "Region",
                "Currency",
                "Estimated Monthly Cost",
                "Estimated Upfront Cost",
            ]
        )
        ws.append(
            [
                "Compute",
                "Virtual Machines",
                "Virtual Machines",
                "East US",
                "USD",
                "73.00",
                "0",
            ]
        )
        buf = io.BytesIO()
        wb.save(buf)
        result = parse(buf.getvalue(), "azure-export.xlsx")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "azure")
        self.assertEqual(len(result["lines"]), 1)
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(result["lines"][0]["quantity"], 1.0)
        self.assertEqual(result["lines"][0]["amount"], 73.0)
        self.assertEqual(result["lines"][0]["itemName"], "Virtual Machines")

    def test_forced_cloud_parses_lines_when_detection_ambiguous(self):
        raw = _minimal_xlsx(
            ["Service Name", "Estimated Monthly Cost", "Currency"],
            [["Blob Storage", "9.5", "USD"]],
        )
        forced = parse(raw, "mystery.xlsx", forced_cloud="azure")
        self.assertEqual(forced["detection"]["status"], "resolved")
        self.assertEqual(forced["detection"]["cloud"], "azure")
        self.assertEqual(len(forced["lines"]), 1)
        self.assertEqual(forced["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(forced["lines"][0]["quantity"], 1.0)
        self.assertEqual(forced["lines"][0]["amount"], 9.5)

    def test_error_message_has_no_abspath(self):
        # Non-bytes raises ValueError without path
        with self.assertRaises(ValueError) as ctx:
            parse("not-bytes")  # type: ignore[arg-type]
        self.assertNotIn("/", str(ctx.exception))
        self.assertNotIn("\\", str(ctx.exception))

    def test_row_cap_returns_ambiguous(self):
        header = "Description,Service,Region,Quantity,Monthly cost,Currency\n"
        # 50_001 data rows stay well under 32 MiB
        row = "EC2,Amazon EC2,us-east-1,1,1.00,USD\n"
        raw = (header + row * 50_001).encode("utf-8")
        result = parse(raw, "many.csv")
        self.assertEqual(result["detection"]["status"], "ambiguous")
        self.assertEqual(result["lines"], [])
        self.assertIn("50000", result["detection"].get("reason", ""))

    def test_corrupt_xlsx_reason_has_no_path(self):
        # Valid ZIP magic but corrupt interior → caught path; reason must not leak paths
        raw = b"PK\x03\x04" + b"\x00" * 200
        result = parse(raw, "broken.xlsx")
        self.assertEqual(result["detection"]["status"], "ambiguous")
        self.assertEqual(result["lines"], [])
        reason = result["detection"].get("reason", "")
        self.assertNotIn("/", reason)
        self.assertNotIn("\\", reason)

    def test_gcp_csv_resolves(self):
        raw = (
            "SKU description,SKU ID,Quantity,Unit,Cost,Currency\n"
            "Compute Engine,SKU-1,2,hour,3.50,USD\n"
        ).encode("utf-8")
        result = parse(raw, "estimate.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "gcp")
        self.assertEqual(result["sourceFormat"], "csv")
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(result["lines"][0]["quantity"], 2.0)
        self.assertEqual(result["lines"][0]["amount"], 3.5)

    def test_gcp_modern_calculator_csv_resolves(self):
        """Current GCP Pricing Calculator export uses service_display_name / total_price."""
        raw = (
            "service_display_name,name,quantity,region,service_id,sku,"
            '"total_price, USD",notes\n'
            "Imagen Models,Imagen output,0.0,global,SID,SKU1,0,\n"
            "Instances (Compute Engine),N4 Core,1460.0,us-central1,SID2,SKU2,45.54,\n"
            "Cloud Storage,Standard Storage,100.0,us-central1,SID3,SKU3,2.00,\n"
        ).encode("utf-8")
        result = parse(raw, "gcp-modern.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "gcp")
        names = [ln["itemName"] for ln in result["lines"]]
        self.assertEqual(names, ["N4 Core", "Standard Storage"])
        self.assertEqual(result["lines"][0]["amount"], 45.54)
        self.assertEqual(result["lines"][0]["currency"], "USD")
        self.assertEqual(result["lines"][0]["spec"], "SKU2")
        self.assertEqual(result["lines"][0].get("serviceId"), "SID2")
        self.assertEqual(result["totals"]["statedTotal"], 47.54)
        self.assertEqual(result["totals"]["currency"], "USD")

    def test_aws_csv_title_row_and_no_quantity(self):
        raw = (
            "AWS Pricing Calculator Estimate\n"
            "Description,Service,Region,Monthly cost,Currency\n"
            "EC2 box,Amazon EC2,us-east-1,10.00,USD\n"
        ).encode("utf-8")
        result = parse(raw, "aws-estimate.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "aws")
        self.assertEqual(len(result["lines"]), 1)
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(result["lines"][0]["quantity"], 1.0)
        self.assertEqual(result["lines"][0]["amount"], 10.0)

    def test_gcp_csv_title_row_and_usage_as_quantity(self):
        raw = (
            "Google Cloud Pricing Calculator\n"
            "Service description,SKU description,SKU ID,Usage,Unit,Cost,Currency\n"
            "Compute Engine,N1 Core,SKU1,730,hour,24.82,USD\n"
        ).encode("utf-8")
        result = parse(raw, "gcp-estimate.csv")
        self.assertEqual(result["detection"]["status"], "resolved")
        self.assertEqual(result["detection"]["cloud"], "gcp")
        self.assertEqual(result["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(result["lines"][0]["quantity"], 730.0)
        self.assertEqual(result["lines"][0]["amount"], 24.82)
        self.assertEqual(result["lines"][0]["itemName"], "N1 Core")

    def test_aws_xlsx_is_ambiguous_not_azure(self):
        """BR1.1: AWS-shaped headers in xlsx must not resolve as Azure."""
        raw = _minimal_xlsx(
            [
                "Description",
                "Service",
                "Region",
                "Quantity",
                "Monthly cost",
                "Currency",
            ],
            [["EC2", "Amazon EC2", "us-east-1", "1", "10", "USD"]],
        )
        result = parse(raw, "aws.xlsx")
        self.assertEqual(result["detection"]["status"], "ambiguous")
        self.assertNotEqual(result["detection"].get("cloud"), "azure")
        # Override path can still extract lines as AWS
        forced = parse(raw, "aws.xlsx", forced_cloud="aws")
        self.assertEqual(forced["detection"]["cloud"], "aws")
        self.assertEqual(forced["lines"][0]["parseStatus"], "parsed")
        self.assertEqual(forced["lines"][0]["amount"], 10.0)

    def test_gcp_xlsx_is_ambiguous_until_override(self):
        raw = _minimal_xlsx(
            [
                "SKU description",
                "SKU ID",
                "Quantity",
                "Unit",
                "Cost",
                "Currency",
            ],
            [["Compute", "SKU1", "2", "hour", "3.50", "USD"]],
        )
        result = parse(raw, "gcp.xlsx")
        self.assertEqual(result["detection"]["status"], "ambiguous")
        forced = parse(raw, "gcp.xlsx", forced_cloud="gcp")
        self.assertEqual(forced["detection"]["cloud"], "gcp")
        self.assertEqual(forced["lines"][0]["quantity"], 2.0)
        self.assertEqual(forced["lines"][0]["amount"], 3.5)


class TestEstimateParserProperties(unittest.TestCase):
    @given(st.binary(min_size=0, max_size=64))
    @settings(max_examples=40, deadline=None)
    def test_parse_never_raises_on_bytes(self, blob: bytes):
        result = parse(blob, "fuzz.bin")
        self.assertIn(result["detection"]["status"], ("resolved", "ambiguous"))
        self.assertIsInstance(result["lines"], list)

    @given(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=12),
                st.sampled_from(["Amazon EC2", "Amazon S3"]),
                st.sampled_from(["us-east-1", "eu-west-1"]),
                st.decimals(
                    min_value=0, max_value=100, places=2, allow_nan=False, allow_infinity=False
                ),
                st.decimals(
                    min_value=0, max_value=1000, places=2, allow_nan=False, allow_infinity=False
                ),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=25, deadline=None)
    def test_same_input_same_output(self, rows):
        encoded = _aws_csv(
            [
                (d, s, r, str(q), str(a), "USD")
                for d, s, r, q, a in rows
            ]
        )
        a = parse(encoded, "estimate.csv")
        b = parse(encoded, "estimate.csv")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
