import pytest

from app.banking import (
    format_iban,
    is_valid_national_id,
    is_valid_tr_iban,
    make_tr_iban,
    mask_name,
    normalize_iban,
    random_iban,
)


@pytest.mark.parametrize("number", ["0000000000000000", "1234567890123456", "9999999999999999"])
def test_roundtrip(number):
    iban = make_tr_iban(number)
    assert len(iban) == 26
    assert is_valid_tr_iban(iban)
    assert normalize_iban(format_iban(iban).lower()) == iban
    assert is_valid_tr_iban(format_iban(iban).lower())
    assert is_valid_tr_iban(random_iban())


@pytest.mark.parametrize("iban", ["TR330006100519786457841326", "TR320010009999901234567890"])
def test_known_iban(iban):
    assert is_valid_tr_iban(iban)


@pytest.mark.parametrize("position", range(2, 26))
def test_corrupted_digit(position):
    iban = "TR330006100519786457841326"
    damaged = iban[:position] + str((int(iban[position]) + 1) % 10) + iban[position + 1 :]
    assert not is_valid_tr_iban(damaged)


@pytest.mark.parametrize(
    "iban", ["", "TR", "TR33000610051978645784132", "TR3300061005197864578413260"]
)
def test_invalid_length(iban):
    assert not is_valid_tr_iban(iban)


@pytest.mark.parametrize(
    ("number", "valid"),
    [
        ("10000000146", True),
        ("00000000146", False),
        ("1000000014", False),
        ("100000001460", False),
        ("10000000147", False),
        ("10000000156", False),
    ],
)
def test_identity(number, valid):
    assert is_valid_national_id(number) is valid


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Deniz Yılmaz", "De*** Yı***"),
        ("  Ömer   Can Bozkurt ", "Öm*** Ca*** Bo***"),
        ("A", "A***"),
        ("Al Ka", "A*** K***"),
        ("Ali Kaya", "Al*** Ka***"),
        # Capped at four words so it always fits the 120-character counterparty column.
        (" ".join(["Abc"] * 60), " ".join(["Ab***"] * 4)),
        ("", ""),
    ],
)
def test_mask(name, expected):
    assert mask_name(name) == expected
