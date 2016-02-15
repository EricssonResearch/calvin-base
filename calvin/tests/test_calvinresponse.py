
from calvin.utilities.calvinresponse import RESPONSE_CODES, CalvinResponse


def test_boolean_value():
    success_list = range(200, 207)
    for code in RESPONSE_CODES:
        response = CalvinResponse(code)
        if code in success_list:
            assert response
        else:
            assert not response


def test_comparisons():
    first = CalvinResponse(100)
    second = CalvinResponse(200)
    third = CalvinResponse(200)

    assert first < second
    assert second > first
    assert second == third
    assert first != second
    assert second <= third
    assert third <= second


def test_set_status():
    response = CalvinResponse(100)
    assert response.status == 100
    response.set_status(400)
    assert response.status == 400
    response.set_status(True)
    assert response.status == 200
    response.set_status(False)
    assert response.status == 500
