"""Pure banking helpers: Turkish IBANs, T.C. identity numbers, name masking. No I/O here."""

import hashlib
import hmac
import re
import secrets

# Fictitious bank code for this demo bank; real codes are assigned by the Central Bank.
BANK_CODE = "99999"

_IBAN_RE = re.compile(r"^TR[0-9]{24}$")


def normalize_iban(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def _mod97(numeric: str) -> int:
    remainder = 0
    for start in range(0, len(numeric), 9):
        remainder = int(str(remainder) + numeric[start : start + 9]) % 97
    return remainder


def _to_numeric(text: str) -> str:
    return "".join(str(int(ch, 36)) for ch in text)


def is_valid_tr_iban(value: str) -> bool:
    """TR + 2 check digits + 5-digit bank code + reserve '0' + 16-digit account no (ISO 13616)."""
    iban = normalize_iban(value)
    if not _IBAN_RE.match(iban) or iban[9] != "0":
        return False
    return _mod97(_to_numeric(iban[4:] + iban[:4])) == 1


def make_tr_iban(account_number: str, bank_code: str = BANK_CODE) -> str:
    if not (account_number.isascii() and account_number.isdigit() and len(account_number) == 16):
        raise ValueError("account_number must be 16 digits")
    bban = f"{bank_code}0{account_number}"
    check = 98 - _mod97(_to_numeric(bban + "TR00"))
    return f"TR{check:02d}{bban}"


def random_iban() -> str:
    return make_tr_iban(f"{secrets.randbelow(10**16):016d}")


def format_iban(value: str) -> str:
    iban = normalize_iban(value)
    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


def is_valid_national_id(value: str) -> bool:
    """T.C. kimlik no: 11 digits, no leading zero, two check digits."""
    # isascii(): str.isdigit() also accepts e.g. full-width digits, which would hash differently.
    if not (len(value) == 11 and value.isascii() and value.isdigit() and value[0] != "0"):
        return False
    d = [int(c) for c in value]
    tenth = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
    eleventh = sum(d[:10]) % 10
    return d[9] == tenth and d[10] == eleventh


def national_id_digest(national_id: str, pepper: str) -> str:
    """Keyed hash: lets us enforce one registration per person without storing the number."""
    return hmac.new(pepper.encode(), national_id.encode(), hashlib.sha256).hexdigest()


MASKED_NAME_WORDS = 4


def mask_iban(iban: str) -> str:
    """Country code, check digits and the last 4 digits: TR12******************0003."""
    return iban[:4] + "*" * (len(iban) - 8) + iban[-4:]


def mask_name(full_name: str) -> str:
    """'Deniz Yılmaz' -> 'De*** Yı***': enough to confirm a recipient, not to identify them.

    Short words show only their first letter, so 'Al' doesn't appear in full. At most
    MASKED_NAME_WORDS words are kept, which also keeps the result well inside the 120-character
    transactions.counterparty column.
    """
    words = full_name.split()[:MASKED_NAME_WORDS]
    return " ".join(f"{word[: 2 if len(word) > 2 else 1]}***" for word in words)
