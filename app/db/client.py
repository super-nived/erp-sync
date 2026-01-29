import httpx

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


class PocketBaseClient:
    def __init__(self):
        self.base_url = settings.pocketbase_url.rstrip("/")
        self.token: str | None = None
        self.timeout = 15

    def auth_admin(self) -> None:
        """
        Authenticate with PocketBase as admin.

        Raises:
            Exception: If authentication fails
        """
        if not settings.pb_admin_email:
            raise ValueError(
                "PocketBase admin credentials not configured. "
                "Set PB_ADMIN_EMAIL and PB_ADMIN_PASSWORD in .env"
            )

        try:
            response = httpx.post(
                f"{self.base_url}/api/collections/_superusers/auth-with-password",
                json={
                    "identity": settings.pb_admin_email,
                    "password": settings.pb_admin_password,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.token = response.json()["token"]
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"Cannot connect to PocketBase at {self.base_url}. "
                f"Is PocketBase running? Error: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            raise ValueError(
                f"PocketBase authentication failed: {e.response.status_code} - "
                f"{e.response.text}"
            )
        except Exception as e:
            raise Exception(f"Unexpected error during PocketBase authentication: {str(e)}")

    def auth_user(self, collection: str, identity: str, password: str) -> dict:
        response = httpx.post(
            f"{self.base_url}/api/collections/{collection}/auth-with-password",
            json={"identity": identity, "password": password},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        auth_required: bool = True,
    ) -> dict:
        headers = {}

        if auth_required and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        url = f"{self.base_url}/api/{path.lstrip('/')}"

        # Build query string for logging
        query_string = ""
        if params:
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                query_parts = [f"{k}={v}" for k, v in filtered_params.items()]
                query_string = "?" + "&".join(query_parts)

        logger.info(f"PocketBase API call: {method} {url}{query_string}")

        response = httpx.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
            timeout=self.timeout,
        )

        response.raise_for_status()
        logger.info(f"PocketBase API response: status={response.status_code}")
        return response.json()

    def get_full_list(
        self,
        collection: str,
        *,
        filter: str | None = None,
        expand: str | None = None,
        sort: str | None = None,
        per_page: int = 200,
    ) -> list[dict]:
        page = 1
        items: list[dict] = []

        while True:
            params = {
                "page": page,
                "perPage": per_page,
                "filter": filter,
                "expand": expand,
                "sort": sort,
            }

            response = self.request(
                "GET",
                f"collections/{collection}/records",
                params={k: v for k, v in params.items() if v},
            )

            items.extend(response.get("items", []))

            if page >= response.get("totalPages", 1):
                break

            page += 1

        logger.info(
            f"PocketBase collection '{collection}': retrieved {len(items)} records"
        )
        return items


pb = PocketBaseClient()
