from unittest.mock import patch

from sdcli.retry_session import RetrySession


def test_retry_session_passthrough(requests_mock):
    """Checks if a RetrySession makes requests."""
    requests_mock.get("https://example.com", text="some html")

    with RetrySession() as session:
        resp = session.get("https://example.com")
        assert resp.text == "some html"


def test_retry_session_retry(requests_mock):
    """
    Checks if a RetrySession automatically retries after the specified time when the
    response includes a retry header.
    """
    requests_mock.get(
        "https://example.com",
        [{"headers": {"Retry-After": "42"}}, {"text": "some html"}],
    )

    with patch("time.sleep") as mock:
        with RetrySession() as session:
            resp = session.get("https://example.com")

            mock.assert_called_once_with(42)
            assert resp.text == "some html"
