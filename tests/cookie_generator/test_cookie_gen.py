import pytest
from spotbot.cookie_generator.cookie_gen import GenerateFootprint


def test_initialization():
    global test_instance
    test_instance = GenerateFootprint(2, "l.wiederhold@gmx.net")
    assert test_instance.driver is not None
    assert test_instance
    assert test_instance.amount_of_cookies_to_gen
    assert test_instance.email


def test_generate_footprint():
    generated_cookies = test_instance.generate_footprint()
    assert generated_cookies is None
