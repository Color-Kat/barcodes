"""Barcode and product-name normalization.

Every source spells barcodes and names differently. Everything entering the DB
goes through here so that cross-source joins actually line up.
"""
import re

_WEIGHT_RE = re.compile(r"\b\d+[.,]?\d*\s*(?:кг|гр?|мл|л|шт|г|g|ml|l|kg)\b", re.I)
_PCT_RE = re.compile(r"\b\d+[.,]?\d*\s*%")
_PUNCT_RE = re.compile(r"[^\w\s]", re.U)


def norm_name(s):
    """Lowercase, drop weight/volume/percent tokens and punctuation, collapse
    spaces — so "Молоко Домик в деревне 3.2% 930 мл" and "МОЛОКО ДОМИК В
    ДЕРЕВНЕ 930мл" become the same key. Returns "" for empty input."""
    if not s:
        return ""
    s = s.lower().replace("ё", "е")
    s = _PCT_RE.sub(" ", s)      # 3.2% first: % breaks the \b in _WEIGHT_RE
    s = _WEIGHT_RE.sub(" ", s)
    s = _PUNCT_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_barcode(raw):
    """Return a checksum-valid EAN-8/EAN-13 digit string, or None.

    UPC-A (12 digits) is widened to EAN-13 with a leading zero, which is how
    GS1 defines the two to coexist — without it US goods duplicate.
    ITF-14/GTIN-14 shipping codes are reduced to their EAN-13 core when the
    leading packaging digit is 0, otherwise rejected (a case of 12 is not the
    same article as the single unit).
    """
    if not raw:
        return None
    d = re.sub(r"\D", "", str(raw))
    if len(d) == 14 and d[0] == "0":
        d = d[1:]
    if len(d) == 12:
        d = "0" + d
    if len(d) not in (8, 13):
        return None
    if d.strip("0") == "":               # 0000000000000 and friends
        return None
    digits = [int(c) for c in d]
    body = digits[:-1][::-1]
    s = sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(body))
    return d if (10 - s % 10) % 10 == digits[-1] else None


def country_of(barcode):
    """GS1 prefix -> ISO-3166 alpha-2, for the prefixes we care about.
    Returns None when the prefix is not one we map (most of the world).

    Note this is the *issuing* GS1 member organisation, not the country of
    manufacture — a Russian company may carry a 400-440 German prefix.
    """
    if not barcode or len(barcode) != 13:
        return None
    p3 = int(barcode[:3])
    if 460 <= p3 <= 469:
        return "RU"
    if p3 == 470:
        return "KG"
    if p3 == 481:
        return "BY"
    if p3 == 482:
        return "UA"
    if p3 == 484:
        return "MD"
    if p3 == 487:
        return "KZ"
    if p3 == 489:
        return "HK"
    if 400 <= p3 <= 440:
        return "DE"
    if 450 <= p3 <= 459 or 490 <= p3 <= 499:
        return "JP"
    if 500 <= p3 <= 509:
        return "GB"
    if 690 <= p3 <= 699:
        return "CN"
    if p3 <= 139:
        return "US"
    return None


def gs1_prefix(barcode, length=7):
    """Company prefix slice — products from one manufacturer share it, which is
    what makes neighbour-scanning for unknown barcodes possible."""
    if not barcode or len(barcode) < length:
        return None
    return barcode[:length]


if __name__ == "__main__":
    assert norm_name("Молоко 3.2% 930 мл") == "молоко"
    assert norm_name("Сыр Российский 500г") == "сыр российский"
    assert norm_name("") == ""
    assert norm_barcode("4600682000129") == "4600682000129"
    assert norm_barcode("4600682000121") is None          # bad checksum
    assert norm_barcode("012000161155") == "0012000161155"  # UPC-A widened
    assert norm_barcode("04600682000129") == "4600682000129"  # GTIN-14, unit case
    assert norm_barcode("14600682000126") is None          # GTIN-14, multipack
    assert norm_barcode("0000000000000") is None
    assert norm_barcode("abc") is None
    assert country_of("4600682000129") == "RU"
    assert country_of("4820024700016") == "UA"
    assert gs1_prefix("4607084356922") == "4607084"
    print("normalize ok")
