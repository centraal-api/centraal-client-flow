"""Test unitario."""

from centraal_client_flow.rules.integration.strategy import (
    OAuthTokenPass,
)


def test_oauth_token_pass_issued_at_string():
    """
    Test if the issued_at value is correctly converted from string to int.
    """
    token_data = {
        "access_token": "dummy_access_token",
        "instance_url": "https://example.salesforce.com",
        "id": "user_id",
        "token_type": "Bearer",
        "issued_at": "1694600000",
        "signature": "dummy_signature",
    }

    token = OAuthTokenPass(**token_data)

    assert isinstance(token.issued_at, int), "issued_at should be an integer"
    assert token.issued_at == 1694600000, "issued_at value was not correctly converted"


def test_oauth_token_pass_issued_at_int():
    """
    Test that issued_at remains an integer when passed as an integer.
    """
    token_data = {
        "access_token": "dummy_access_token",
        "instance_url": "https://example.salesforce.com",
        "id": "user_id",
        "token_type": "Bearer",
        "issued_at": 1694600000,  # issued_at is already an int
        "signature": "dummy_signature",
    }

    token = OAuthTokenPass(**token_data)

    assert isinstance(token.issued_at, int), "issued_at should be an integer"
    assert token.issued_at == 1694600000, "issued_at value is incorrect"


def test_oauth_token_pass_expires_in_default():
    """
    Test that the expires_in field has the correct default value of 1800.
    """
    token_data = {
        "access_token": "dummy_access_token",
        "instance_url": "https://example.salesforce.com",
        "id": "user_id",
        "token_type": "Bearer",
        "issued_at": 1694600000,  # issued_at is an int
        "signature": "dummy_signature",
    }

    token = OAuthTokenPass(**token_data)

    assert token.expires_in == 1800, "expires_in should default to 1800 seconds"
