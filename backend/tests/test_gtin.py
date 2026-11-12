import pytest

from app.core.gtin import is_valid_gtin


@pytest.mark.parametrize(
    "value",
    ["96385074", "036000291452", "4006381333931", "10012345000017"],
)
def test_known_valid_gtin_lengths(value):
    assert is_valid_gtin(value)


@pytest.mark.parametrize(
    "value",
    ["96385075", "036000291453", "4006381333932", "10012345000018"],
)
def test_invalid_gtin_check_digits(value):
    assert not is_valid_gtin(value)


@pytest.mark.parametrize("value", [None, "", "1234567", "123456789", "１２３４５６７８", 4006381333931])
def test_gtin_rejects_wrong_length_or_non_ascii_string(value):
    assert not is_valid_gtin(value)


def test_gtin_keeps_leading_zero_as_part_of_string():
    value = "036000291452"
    assert is_valid_gtin(value)
    assert value.startswith("0")
