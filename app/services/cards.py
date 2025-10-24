from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CardSpec:
    brand: str
    lengths: Tuple[int, ...]
    prefixes: Tuple[str, ...]
    cvv_length: int


CARD_SPECS: Dict[str, CardSpec] = {
    # Common sandbox/test brands
    "visa": CardSpec(
        brand="VISA",
        lengths=(16,),
        prefixes=("4",),
        cvv_length=3,
    ),
    "mastercard": CardSpec(
        brand="MASTERCARD",
        lengths=(16,),
        prefixes=(
            # 51-55
            *[str(i) for i in range(51, 56)],
            # 2221-2720 (we keep as strings, handle variable prefix length)
            *[str(i) for i in range(2221, 2721)],
        ),
        cvv_length=3,
    ),
    "amex": CardSpec(
        brand="AMEX",
        lengths=(15,),
        prefixes=("34", "37"),
        cvv_length=4,
    ),
    "discover": CardSpec(
        brand="DISCOVER",
        lengths=(16,),
        prefixes=(
            "6011",
            "65",
            *[str(i) for i in range(644, 650)],
            *[str(i) for i in range(622126, 622926)],
        ),
        cvv_length=3,
    ),
    "jcb": CardSpec(
        brand="JCB",
        lengths=(16,),
        prefixes=tuple(str(i) for i in range(3528, 3590)),
        cvv_length=3,
    ),
    "diners": CardSpec(
        brand="DINERS",
        lengths=(14,),
        prefixes=(
            *[str(i) for i in range(300, 306)],
            "36",
            *[str(i) for i in range(38, 40)],
        ),
        cvv_length=3,
    ),
}


def _luhn_check_digit(number_without_check: str) -> str:
    digits = [int(d) for d in number_without_check]
    # Luhn algorithm: from right, double every second digit
    for i in range(len(digits) - 1, -1, -2):
        doubled = digits[i] * 2
        digits[i] = doubled - 9 if doubled > 9 else doubled
    total = sum(digits)
    return str((10 - (total % 10)) % 10)


def _complete_luhn(prefix: str, total_length: int) -> str:
    # Fill with random digits up to length-1, then compute check digit
    if len(prefix) >= total_length:
        raise ValueError("Prefix must be shorter than total length")
    remaining = total_length - len(prefix) - 1
    body = prefix + "".join(str(random.randint(0, 9)) for _ in range(remaining))
    check = _luhn_check_digit(body)
    return body + check


def _choose_prefix(prefixes: Tuple[str, ...]) -> str:
    return random.choice(prefixes)


def _generate_expiry() -> Tuple[int, int]:
    now = datetime.utcnow()
    month = random.randint(1, 12)
    year = now.year + random.randint(2, 5)
    return month, year


def _generate_cvv(length: int) -> str:
    lower = 10 ** (length - 1)
    upper = (10 ** length) - 1
    return str(random.randint(lower, upper))


def _generate_zip() -> str:
    # US 5-digit ZIP; avoid 00000 while allowing leading zeros
    return str(random.randint(1, 99999)).zfill(5)


def generate_card(brand: Optional[str] = None) -> Dict[str, str | int]:
    """Generate a single sandbox test card.

    If brand is None or unknown, a random supported brand is used.
    """
    key = (brand or "").strip().lower()
    spec = CARD_SPECS.get(key)
    if spec is None:
        key = random.choice(list(CARD_SPECS.keys()))
        spec = CARD_SPECS[key]

    length = random.choice(spec.lengths)
    prefix = _choose_prefix(spec.prefixes)
    number = _complete_luhn(prefix, length)

    exp_month, exp_year = _generate_expiry()
    cvv = _generate_cvv(spec.cvv_length)

    return {
        "brand_key": key,
        "brand": spec.brand,
        "number": number,
        "expiry_month": exp_month,
        "expiry_year": exp_year,
        "cvv": cvv,
        "zip": _generate_zip(),
    }


def generate_cards(count: int = 1, brand: Optional[str] = None) -> List[Dict[str, str | int]]:
    if count < 1:
        count = 1
    if count > 20:
        count = 20
    return [generate_card(brand=brand) for _ in range(count)]
