from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


@dataclass(frozen=True)
class NetworkConfig:
    name: str
    default_length: int
    # prefixes can be strings (fixed) or tuples representing inclusive integer ranges
    prefixes: List[Union[str, Tuple[int, int]]]


def _luhn_checksum_digit(number_without_check: str) -> str:
    """Return the Luhn check digit for the provided number body (as string)."""
    digits = [int(ch) for ch in number_without_check]
    # Starting from rightmost, double every second digit
    total = 0
    parity = (len(digits) + 1) % 2  # positions that need doubling
    for idx, d in enumerate(digits):
        if idx % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    check = (10 - (total % 10)) % 10
    return str(check)


def _random_prefix(prefixes: List[Union[str, Tuple[int, int]]]) -> str:
    choice = random.choice(prefixes)
    if isinstance(choice, str):
        return choice
    start, end = choice
    n = random.randint(start, end)
    width = len(str(start))  # preserve width
    return f"{n:0{width}d}"


def _generate_from_prefix(prefix: str, length: int) -> str:
    if not prefix.isdigit():
        raise ValueError("Prefix must be numeric")
    if length < len(prefix) + 1:
        raise ValueError("Length too short for given prefix")
    body_len = length - len(prefix) - 1  # minus check digit
    middle = ''.join(str(random.randint(0, 9)) for _ in range(body_len))
    partial = prefix + middle
    return partial + _luhn_checksum_digit(partial)


class CreditCardService:
    """Generates Luhn-valid card numbers for common networks."""

    NETWORKS = {
        "visa": NetworkConfig(
            name="visa",
            default_length=16,
            prefixes=["4"],
        ),
        "mastercard": NetworkConfig(
            name="mastercard",
            default_length=16,
            prefixes=[(51, 55), (2221, 2720)],
        ),
        "amex": NetworkConfig(
            name="amex",
            default_length=15,
            prefixes=["34", "37"],
        ),
        "discover": NetworkConfig(
            name="discover",
            default_length=16,
            prefixes=["6011", "65", (644, 649), (622126, 622925)],
        ),
        "jcb": NetworkConfig(
            name="jcb",
            default_length=16,
            prefixes=[(3528, 3589)],
        ),
        "diners": NetworkConfig(
            name="diners",
            default_length=14,
            prefixes=[(300, 305),  (36, 36), (38, 38)],
        ),
    }

    def generate_cards(
        self,
        *,
        network: Optional[str] = None,
        bin_prefix: Optional[str] = None,
        length: Optional[int] = None,
        quantity: int = 1,
    ) -> List[str]:
        if quantity < 1 or quantity > 500:
            raise ValueError("quantity must be between 1 and 500")

        selected_config: Optional[NetworkConfig] = None
        if network:
            key = network.strip().lower()
            if key not in self.NETWORKS:
                raise ValueError("Unsupported network. Try visa, mastercard, amex, discover, jcb, diners")
            selected_config = self.NETWORKS[key]

        # If BIN provided, use it as prefix (4-8 digits common). We'll be permissive (2-12).
        prefix_to_use: Optional[str] = None
        if bin_prefix:
            candidate = bin_prefix.strip().replace(" ", "")
            if not candidate.isdigit():
                raise ValueError("bin must be numeric")
            if not (2 <= len(candidate) <= 12):
                raise ValueError("bin length must be between 2 and 12 digits")
            prefix_to_use = candidate

        target_length: int
        if length is not None:
            if length < 12 or length > 19:
                raise ValueError("length must be between 12 and 19")
            target_length = length
        else:
            target_length = selected_config.default_length if selected_config else 16

        results: List[str] = []
        for _ in range(quantity):
            if prefix_to_use is not None:
                prefix = prefix_to_use
            elif selected_config is not None:
                prefix = _random_prefix(selected_config.prefixes)
            else:
                # No network or BIN -> choose a random network with common length 16
                any_config = random.choice([self.NETWORKS["visa"], self.NETWORKS["mastercard"], self.NETWORKS["discover"], self.NETWORKS["jcb"]])
                prefix = _random_prefix(any_config.prefixes)
                if length is None:
                    target_length = any_config.default_length

            results.append(_generate_from_prefix(prefix, target_length))

        return results
