from refresh_velib import _arrondissement, _bike_counts


def test_arrondissement_from_four_and_five_digit_codes():
    assert _arrondissement("1001") == 1
    assert _arrondissement("9008") == 9
    assert _arrondissement("10162") == 10
    assert _arrondissement("16107") == 16
    assert _arrondissement("21001") is None


def test_bike_type_counts():
    status = {"num_bikes_available_types": [{"mechanical": 7}, {"ebike": 3}]}
    assert _bike_counts(status) == (7, 3)
