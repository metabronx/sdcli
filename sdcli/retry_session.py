# mypy: disable-error-code="override"

import time
from typing import Any, Union

from requests import Response, Session


class RetrySession(Session):
    """
    Identical to a requests Session in every way, except that it automatically retries
    requests that respond with a "Retry-After" header and raises an error if the
    response is not valid (HTTP 400-600).
    """

    def request(
        self, method: Union[str, bytes], url: Union[str, bytes], **kwargs: Any
    ) -> Response:
        resp: Response = super().request(method, url, **kwargs)

        # GitHub et al may rate limit us, in which case we need to wait
        # the amount of time they tell us before retrying
        retry: float = float(resp.headers.get("Retry-After", 0))
        if retry:
            time.sleep(retry)
            return self.request(method, url, **kwargs)

        resp.raise_for_status()
        return resp
