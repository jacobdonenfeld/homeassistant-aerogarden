import pytest

from custom_components.aerogarden import cleanPassword


def test_clean_password() -> None:
    """Test function to clean passwords"""

    password = ""
    testText = ["", "small", "okayokay"]

    for text in testText:
        assert cleanPassword(text, password) == text

    password = "pass"

    testText = ["", "pass-in-front", "in-back-pass", "hellogoodbye", "pass"]
    expectedText = [
        "",
        "<password>-in-front",
        "in-back-<password>",
        "hellogoodbye",
        "<password>",
    ]

    for i in range(len(testText)):
        assert cleanPassword(testText[i], password) == expectedText[i]
