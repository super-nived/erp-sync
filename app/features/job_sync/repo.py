"""
Job Sync Repository

Data access layer for ERP API, PocketBase, and SQLite.
Following spec.md: No business logic, talks to external systems only.
"""

from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.settings import settings
from app.db.client import pb
from app.features.job_sync import db_helpers

logger = get_logger(__name__)


def fetch_erp_data(from_date: str) -> list[dict[str, Any]]:
    """
    Fetch data from ERP API.

    Args:
        from_date: Date string in YYYY-MM-DD format

    Returns:
        List of ERP records

    Raises:
        httpx.HTTPError: On API request failure
    """
    try:
        url = settings.erp_api_url
        params = {"txnType": settings.erp_txn_type, "fromDate": from_date}

        logger.info(f"Fetching ERP data from {url} with params {params}")

        response = httpx.get(url, params=params, timeout=600.0, verify=False)
        response.raise_for_status()

        data = response.json()
        logger.info(f"Fetched {len(data)} records from ERP API")
        return data

    except httpx.TimeoutException as e:
        logger.error(f"ERP API timeout: {str(e)}")
        raise
    except httpx.HTTPError as e:
        logger.error(f"ERP API request failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching ERP data: {str(e)}")
        raise


def get_collection_name() -> str:
    """
    Get the PocketBase collection name.

    Returns:
        Collection name string
    """
    return f"{settings.plant_code}_erpConsolidateData"


def create_record(record_data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a single record in PocketBase.

    Args:
        record_data: Record data to insert

    Returns:
        Created record with PocketBase metadata

    Raises:
        httpx.HTTPError: On API request failure
    """
    try:
        collection = get_collection_name()
        result = pb.request(
            "POST",
            f"collections/{collection}/records",
            json=record_data,
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Failed to create record: "
            f"{e.response.status_code} - {e.response.text}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating record: {str(e)}")
        raise


def update_record(
    record_id: str, record_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Update an existing record in PocketBase.

    Args:
        record_id: PocketBase record ID
        record_data: Updated record data

    Returns:
        Updated record with PocketBase metadata

    Raises:
        httpx.HTTPError: On API request failure
    """
    try:
        collection = get_collection_name()
        result = pb.request(
            "PATCH",
            f"collections/{collection}/records/{record_id}",
            json=record_data,
        )
        return result

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Failed to update record {record_id}: "
            f"{e.response.status_code} - {e.response.text}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating record {record_id}: {str(e)}")
        raise


def find_existing_record(
    base_id: str, sub_id: str
) -> dict[str, Any] | None:
    """
    Find existing record by unique identifiers.

    Args:
        base_id: BOM_WORKORDER_BASE_ID value
        sub_id: BOM_WORKORDER_SUB_ID value

    Returns:
        Record dict if found, None otherwise

    Raises:
        httpx.HTTPError: On API request failure
    """
    try:
        collection = get_collection_name()
        filter_query = (
            f'BOM_WORKORDER_BASE_ID="{base_id}" && '
            f'BOM_WORKORDER_SUB_ID="{sub_id}"'
        )

        response = pb.request(
            "GET",
            f"collections/{collection}/records",
            params={"filter": filter_query, "perPage": 1},
        )

        items = response.get("items", [])
        return items[0] if items else None

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Failed to find record: "
            f"{e.response.status_code} - {e.response.text}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error finding record: {str(e)}")
        raise


def store_erp_record_in_sqlite(
    record: dict[str, Any]
) -> tuple[int, bool] | tuple[None, bool]:
    """
    Store ERP record in SQLite database.

    Args:
        record: ERP record to store

    Returns:
        Tuple of (record_id, is_updated)
    """
    try:
        erp_id = generate_erp_id(record)
        return db_helpers.insert_raw_erp_data(erp_id, record)

    except Exception as e:
        logger.error(f"Error storing ERP record: {str(e)}")
        return None, False


def generate_erp_id(record: dict[str, Any]) -> str:
    """
    Generate unique ERP ID.

    Args:
        record: ERP record

    Returns:
        Unique identifier string
    """
    base_id = record.get("BOM_WORKORDER_BASE_ID", "")
    sub_id = record.get("BOM_WORKORDER_SUB_ID", "")
    return f"{base_id}-{sub_id}"
