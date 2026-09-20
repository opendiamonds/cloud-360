"""Pure estimate-table parser — no HTTP/DB/framework imports (FR2.3)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, TypedDict

from cost.estimate_readers import (
    MAX_PAYLOAD_BYTES,
    best_clouds,
    column_map,
    infer_currency_from_headers,
    iter_limited_rows,
    parse_number,
    read_csv_table,
    read_xlsx_table,
    row_get,
    score_cloud,
    sniff_format,
    xlsx_uncompressed_bytes,
)

# Official Azure exports often omit Quantity; treat missing column as 1.
_DEFAULT_QUANTITY = Decimal("1")

CloudId = Literal["aws", "azure", "gcp"]
ParseStatus = Literal["parsed", "unidentifiable"]
SourceFormat = Literal["csv", "xlsx"]


class CloudDetection(TypedDict, total=False):
    status: Literal["resolved", "ambiguous"]
    cloud: CloudId
    candidates: list[CloudId]
    reason: str


class LineItem(TypedDict, total=False):
    ordinal: int
    itemName: str
    spec: str
    quantity: float | None
    amount: float | None
    currency: str | None
    parseStatus: ParseStatus
    rawText: str


class EstimateTotals(TypedDict, total=False):
    statedTotal: float | None
    currency: str | None


class ParseResult(TypedDict):
    detection: CloudDetection
    lines: list[LineItem]
    totals: EstimateTotals
    sourceFormat: SourceFormat


def _ambiguous(
    *,
    source_format: SourceFormat,
    reason: str,
    candidates: list[CloudId] | None = None,
) -> ParseResult:
    detection: CloudDetection = {"status": "ambiguous", "reason": reason}
    if candidates:
        detection["candidates"] = candidates
    return {
        "detection": detection,
        "lines": [],
        "totals": {"statedTotal": None, "currency": None},
        "sourceFormat": source_format,
    }


def _safe_message(exc: BaseException) -> str:
    """NFR3.2: never leak absolute paths or traceback text."""
    name = type(exc).__name__
    return f"parse failed ({name})"


def _decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _normalize_line(
    ordinal: int,
    row: list[str],
    mapping: dict[str, int],
    *,
    default_currency: str | None = None,
) -> LineItem:
    raw_text = ",".join(row)
    amount = parse_number(row_get(row, mapping.get("amount")))
    qty = parse_number(row_get(row, mapping.get("quantity")))
    # Official exports often leave Quantity blank on priced lines — default to 1
    # when amount is present so the row can still be kept.
    if qty is None and amount is not None:
        qty = _DEFAULT_QUANTITY
    currency_raw = row_get(row, mapping.get("currency")).strip() or None
    if not currency_raw:
        currency_raw = default_currency
    item = row_get(row, mapping.get("itemName")).strip() or None
    if not item:
        item = row_get(row, mapping.get("itemNameAlt")).strip() or None
    spec = row_get(row, mapping.get("spec")).strip() or None

    if qty is None or amount is None:
        return {
            "ordinal": ordinal,
            "itemName": item or "",
            "spec": spec or "",
            "quantity": _decimal_to_float(qty),
            "amount": _decimal_to_float(amount),
            "currency": currency_raw,
            "parseStatus": "unidentifiable",
            "rawText": raw_text,
        }
    return {
        "ordinal": ordinal,
        "itemName": item or "",
        "spec": spec or "",
        "quantity": _decimal_to_float(qty),
        "amount": _decimal_to_float(amount),
        "currency": currency_raw,
        "parseStatus": "parsed",
        "rawText": raw_text,
    }


def _is_total_label(text: str) -> bool:
    label = text.strip().lower()
    return bool(label) and (
        "total" in label or "合計" in label or "小計" in label
    )


def _is_kept_line(line: LineItem) -> bool:
    """Keep only rows with a service/component name and a non-zero amount.

    Total / 合計 rows are excluded from line items (surfaced via totals).
    Zero-priced calculator placeholders are dropped.
    """
    name = (line.get("itemName") or "").strip()
    if not name or line.get("amount") is None:
        return False
    if _is_total_label(name):
        return False
    try:
        if float(line["amount"]) == 0.0:
            return False
    except (TypeError, ValueError):
        return False
    return True


def _extract_totals(
    rows: list[list[str]],
    mapping: dict[str, int],
    kept: list[LineItem],
) -> EstimateTotals:
    """Prefer a labeled total row; otherwise sum kept line amounts."""
    amount_idx = mapping.get("amount")
    currency_idx = mapping.get("currency")
    stated = None
    currency = None
    for row in reversed(rows):
        if not any(_is_total_label(cell) for cell in row if cell):
            continue
        if amount_idx is not None:
            stated = parse_number(row_get(row, amount_idx))
        if currency_idx is not None:
            currency = row_get(row, currency_idx).strip() or None
        break

    if stated is None and kept:
        stated = sum(
            (Decimal(str(ln["amount"])) for ln in kept if ln.get("amount") is not None),
            Decimal("0"),
        )
    if currency is None:
        for ln in kept:
            if ln.get("currency"):
                currency = ln["currency"]
                break

    return {
        "statedTotal": _decimal_to_float(stated),
        "currency": currency,
    }


def parse(
    file_bytes: bytes,
    filename: str | None = None,
    *,
    forced_cloud: CloudId | None = None,
) -> ParseResult:
    """Parse an official cloud estimate export into a ParseResult (BR1–BR3).

    ``forced_cloud`` skips auto-detection and maps columns for that cloud
    (used when the caller supplies a cloud override after an ambiguous pass).
    """
    if not isinstance(file_bytes, (bytes, bytearray)):
        raise ValueError("file_bytes must be bytes")
    payload = bytes(file_bytes)

    fmt = sniff_format(payload, filename)
    if fmt is None:
        return _ambiguous(source_format="csv", reason="unrecognized format")

    try:
        if fmt == "csv":
            if len(payload) > MAX_PAYLOAD_BYTES:
                return _ambiguous(source_format="csv", reason="payload exceeds 32 MiB")
            # UTF-8 byte length of decoded text is checked inside reader via encode
            table = read_csv_table(payload)
            if table is None:
                # Distinguish oversize UTF-8 vs corrupt
                try:
                    text = payload.decode("utf-8-sig")
                    if len(text.encode("utf-8")) > MAX_PAYLOAD_BYTES:
                        return _ambiguous(
                            source_format="csv", reason="payload exceeds 32 MiB"
                        )
                except UnicodeDecodeError:
                    pass
                return _ambiguous(source_format="csv", reason="unreadable csv")
        else:
            uncompressed = xlsx_uncompressed_bytes(payload)
            if uncompressed < 0:
                return _ambiguous(source_format="xlsx", reason="unreadable xlsx")
            if uncompressed > MAX_PAYLOAD_BYTES:
                return _ambiguous(
                    source_format="xlsx", reason="payload exceeds 32 MiB"
                )
            table = read_xlsx_table(payload)
            if table is None:
                return _ambiguous(source_format="xlsx", reason="unreadable xlsx")
    except ValueError as exc:
        # openpyxl missing etc. — still no path leak
        return _ambiguous(
            source_format="xlsx" if fmt == "xlsx" else "csv",
            reason=_safe_message(exc),
        )
    except Exception as exc:  # pragma: no cover — defensive
        return _ambiguous(
            source_format="xlsx" if fmt == "xlsx" else "csv",
            reason=_safe_message(exc),
        )

    limited = iter_limited_rows(table.rows)
    if limited is None:
        return _ambiguous(
            source_format=table.source_format,  # type: ignore[arg-type]
            reason="row count exceeds 50000",
        )

    if not table.headers or not any(h.strip() for h in table.headers):
        return _ambiguous(
            source_format=table.source_format,  # type: ignore[arg-type]
            reason="missing headers",
        )

    if forced_cloud is not None:
        cloud: CloudId = forced_cloud
    else:
        scores = score_cloud(table.headers)
        raw_best = best_clouds(scores, minimum=3)
        # BR1.1: drop format-incompatible from already-ranked winners
        # (zeroing scores first let Azure win on AWS-like xlsx headers).
        if table.source_format == "csv":
            compatible = [c for c in raw_best if c != "azure"]
        else:
            compatible = [c for c in raw_best if c not in ("aws", "gcp")]
        if len(compatible) != 1:
            return _ambiguous(
                source_format=table.source_format,  # type: ignore[arg-type]
                reason="cloud detection ambiguous",
                candidates=(raw_best or ["aws", "azure", "gcp"]),  # type: ignore[list-item]
            )
        cloud = compatible[0]  # type: ignore[assignment]

    mapping = column_map(table.headers, cloud)
    # Amount is required; Quantity may be absent (default 1 in _normalize_line).
    if "amount" not in mapping:
        return _ambiguous(
            source_format=table.source_format,  # type: ignore[arg-type]
            reason="cannot map required columns",
        )
    default_currency = infer_currency_from_headers(
        table.headers, mapping.get("amount")
    )

    # Exclude trailing total-looking rows from line items when labeled
    data_rows = list(limited)
    if data_rows:
        if any(_is_total_label(cell) for cell in data_rows[-1] if cell):
            data_rows = data_rows[:-1]

    kept: list[LineItem] = []
    for row in data_rows:
        line = _normalize_line(
            0, row, mapping, default_currency=default_currency
        )
        if not _is_kept_line(line):
            continue
        line["ordinal"] = len(kept)
        kept.append(line)
    totals = _extract_totals(list(limited), mapping, kept)
    if totals.get("currency") is None and default_currency:
        totals["currency"] = default_currency

    return {
        "detection": {"status": "resolved", "cloud": cloud},  # type: ignore[typeddict-item]
        "lines": kept,
        "totals": totals,
        "sourceFormat": table.source_format,  # type: ignore[typeddict-item]
    }
