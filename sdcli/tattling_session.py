import requests


class TattlingSession(requests.Session):
    """
    Identical to a requests Session in every way, except that it raises an error if the
    response is not valid (HTTP 400-600).
    """

    def request(self, method, url, **kwargs):
        resp = super().request(method, url, **kwargs)
        resp.raise_for_status()
        return resp
