"""
SQLite Interface Client - Direct SQL Query Interface

Provides same interface as PocketBaseClient but uses direct SQL queries
via sql-interface API endpoint.

Usage:
    from app.db.sql_client import sql_db

    # Same interface as PocketBase
    records = sql_db.get_full_list(
        collection="ASWNDUBAI_Job",
        filter='workOrderNumber = "AW-123"',
        sort="-created"
    )
"""

import urllib.parse
from typing import List, Dict

import httpx

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


class SQLiteInterfaceClient:
    """
    Direct SQL interface client for SQLite database.

    Mimics PocketBaseClient interface but executes raw SQL queries.
    """

    def __init__(self):
        """Initialize SQL interface client."""
        self.base_url = settings.sql_interface_url.rstrip("/") if settings.sql_interface_url else None
        self.timeout = 30  # SQL queries may take longer
        self.token: str | None = None

        if not self.base_url:
            logger.warning("SQL_INTERFACE_URL not configured")

    def auth_admin(self) -> None:
        """
        Authenticate with SQL interface.

        Currently no authentication required - placeholder for future JWT token support.

        Raises:
            Exception: If authentication fails
        """
        logger.debug("SQL interface auth: no authentication required (placeholder for future JWT)")
        # Future: Extract JWT token from request context and store
        self.token = None

    def execute_raw_sql(self, query: str) -> List[Dict]:
        """
        Execute raw SQL query via API endpoint.

        Args:
            query: SQL query to execute

        Returns:
            List of records as dictionaries

        Raises:
            Exception: If query execution fails
        """
        if not self.base_url:
            raise ValueError("SQL_INTERFACE_URL not configured in settings")

        try:
            # URL encode the query
            encoded_query = urllib.parse.quote(query)

            # Build full URL
            url = f"{self.base_url}/sqlite-interface/get?query={encoded_query}"

            logger.debug(f"SQL Interface: {query[:100]}...")

            # Execute request
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            response = httpx.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )

            response.raise_for_status()
            data = response.json()

            # Handle response format
            if isinstance(data, list):
                logger.info(f"SQL query returned {len(data)} records")
                return data
            else:
                logger.warning(f"Unexpected response format: {type(data)}")
                return []

        except httpx.HTTPStatusError as e:
            logger.error(f"SQL query failed: HTTP {e.response.status_code} - {e.response.text}")
            raise Exception(f"SQL query failed: {e.response.status_code}")

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to SQL interface at {self.base_url}: {e}")
            raise ConnectionError(f"Cannot connect to SQL interface: {str(e)}")

        except Exception as e:
            logger.error(f"SQL query error: {str(e)}")
            raise Exception(f"SQL query execution failed: {str(e)}")

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        auth_required: bool = True,
    ) -> dict:
        """
        Execute database request (for compatibility with PocketBase interface).

        For SQL interface, this converts REST-style requests to SQL queries.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            path: Path like "collections/{collection}/records" or "collections/{collection}/records/{id}"
            params: Query parameters (filter, sort, etc.)
            json: JSON payload for POST/PATCH
            auth_required: Whether authentication is required

        Returns:
            Dict with response data

        Raises:
            NotImplementedError: For POST/PATCH/DELETE (writes not supported yet)
        """
        if method != "GET":
            raise NotImplementedError(
                f"SQL interface only supports GET (reads). "
                f"Method {method} not supported. Use PocketBase client for writes."
            )

        # Parse collection from path
        # Path format: "collections/{collection}/records" or "collections/{collection}/records/{id}"
        parts = path.strip("/").split("/")

        if len(parts) < 3 or parts[0] != "collections":
            raise ValueError(f"Invalid path format: {path}")

        collection = parts[1]

        # Check if getting single record by ID
        if len(parts) >= 4 and parts[2] == "records":
            record_id = parts[3]
            # Get single record
            query = f"SELECT * FROM {collection} WHERE id = '{record_id}' LIMIT 1"
            results = self.execute_raw_sql(query)

            if not results:
                raise Exception(f"Record not found: {record_id}")

            return results[0]

        # Otherwise, get list of records
        return {"items": self.get_full_list(collection, **params) if params else self.get_full_list(collection)}

    def get_full_list(
        self,
        collection: str,
        *,
        filter: str | None = None,
        expand: str | None = None,
        sort: str | None = None,
        per_page: int = 200,
    ) -> List[Dict]:
        """
        Get full list of records from collection with automatic pagination.

        Mimics PocketBase get_full_list() - fetches ALL records across multiple pages.

        Args:
            collection: Table name (e.g., "ASWNDUBAI_Job")
            filter: PocketBase-style filter (e.g., 'status = "active"')
            expand: Relations to expand (not yet supported)
            sort: Sort field (e.g., "-created" for DESC, "name" for ASC)
            per_page: Records per page (default: 200)

        Returns:
            List of ALL records as dictionaries (paginated automatically)

        Raises:
            Exception: If query fails
        """
        try:
            all_items = []
            page = 1

            # Paginate through all results (like PocketBase does)
            while True:
                # Build SQL query with pagination
                query_parts = [f"SELECT * FROM {collection}"]

                # Add WHERE clause if filter provided
                if filter:
                    sql_where = self._convert_filter_to_sql(filter)
                    if sql_where:
                        query_parts.append(f"WHERE {sql_where}")

                # Add ORDER BY clause if sort provided
                if sort:
                    sql_order = self._convert_sort_to_sql(sort)
                    if sql_order:
                        query_parts.append(f"ORDER BY {sql_order}")

                # Add pagination (LIMIT/OFFSET)
                offset = (page - 1) * per_page
                query_parts.append(f"LIMIT {per_page} OFFSET {offset}")

                # Build final query
                query = " ".join(query_parts)

                logger.debug(f"SQL query (page {page}): {query}")

                # Execute query
                results = self.execute_raw_sql(query)

                # Add results to list
                all_items.extend(results)

                # Check if we got fewer results than per_page (last page)
                if len(results) < per_page:
                    break

                page += 1

            logger.info(
                f"SQL collection '{collection}': retrieved {len(all_items)} records "
                f"across {page} page(s)"
            )
            return all_items

        except Exception as e:
            logger.error(f"Failed to get records from '{collection}': {e}")
            raise

    def get_list(
        self,
        collection: str,
        *,
        page: int = 1,
        per_page: int = 200,
        filter: str | None = None,
        sort: str | None = None,
    ) -> Dict:
        """
        Get single page of records from collection.

        Mimics PocketBase get_list() - returns paginated response with metadata.

        Args:
            collection: Table name (e.g., "ASWNDUBAI_Job")
            page: Page number (1-indexed, like PocketBase)
            per_page: Records per page (default: 200)
            filter: PocketBase-style filter
            sort: Sort field

        Returns:
            Dict with pagination metadata:
            {
                "page": 1,
                "perPage": 200,
                "totalItems": 938,
                "totalPages": 5,
                "items": [...]
            }

        Raises:
            Exception: If query fails
        """
        try:
            # Build base query for counting total
            count_query_parts = [f"SELECT COUNT(*) as total FROM {collection}"]

            # Add WHERE clause if filter provided
            if filter:
                sql_where = self._convert_filter_to_sql(filter)
                if sql_where:
                    count_query_parts.append(f"WHERE {sql_where}")

            # Get total count
            count_query = " ".join(count_query_parts)
            count_result = self.execute_raw_sql(count_query)
            total_items = count_result[0]["total"] if count_result else 0
            total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

            # Build data query with pagination
            query_parts = [f"SELECT * FROM {collection}"]

            if filter:
                sql_where = self._convert_filter_to_sql(filter)
                if sql_where:
                    query_parts.append(f"WHERE {sql_where}")

            if sort:
                sql_order = self._convert_sort_to_sql(sort)
                if sql_order:
                    query_parts.append(f"ORDER BY {sql_order}")

            # Add pagination
            offset = (page - 1) * per_page
            query_parts.append(f"LIMIT {per_page} OFFSET {offset}")

            # Execute query
            query = " ".join(query_parts)
            logger.debug(f"SQL paginated query (page {page}): {query}")

            items = self.execute_raw_sql(query)

            logger.info(
                f"SQL collection '{collection}': page {page}/{total_pages}, "
                f"{len(items)} records"
            )

            # Return PocketBase-compatible response
            return {
                "page": page,
                "perPage": per_page,
                "totalItems": total_items,
                "totalPages": total_pages,
                "items": items,
            }

        except Exception as e:
            logger.error(f"Failed to get paginated records from '{collection}': {e}")
            raise

    def get_grouped_list(
        self,
        collection: str,
        *,
        group_by: List[str],
        aggregations: Dict[str, str] | None = None,
        filter: str | None = None,
        sort: str | None = None,
        is_full_list: bool = True,
        page: int = 1,
        per_page: int = 200,
    ) -> List[Dict] | Dict:
        """
        Get grouped and aggregated records from collection.

        Builds SQL GROUP BY query with aggregations.

        Args:
            collection: Table name (e.g., "ASWNDUBAI_mpsEventTracker")
            group_by: Fields to group by (e.g., ["workorder_base_id", "status"])
            aggregations: Dict of {result_field: "AGG(source_field)"}
                Examples:
                {
                    "planned_start_date": "MIN(planned_start_date)",
                    "planned_end_date": "MAX(planned_end_date)",
                    "total_count": "COUNT(*)",
                    "avg_qty": "AVG(qnty)"
                }
            filter: PocketBase-style filter for WHERE clause
            sort: Sort field (applied after grouping)
            is_full_list: If True, returns all records. If False, returns paginated response
            page: Page number (if is_full_list=False)
            per_page: Records per page

        Returns:
            List of dicts (if is_full_list=True) or paginated response dict (if False)

        Raises:
            Exception: If query fails

        Example:
            # Group by work order, get date ranges and status
            results = sql_db.get_grouped_list(
                collection="ASWNDUBAI_mpsEventTracker",
                group_by=["workorder_base_id"],
                aggregations={
                    "planned_start_date": "MIN(planned_start_date)",
                    "planned_end_date": "MAX(planned_end_date)",
                    "status": "CASE WHEN SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) > 0 THEN 'delayed' ELSE 'on_track' END"
                },
                sort="-last_updated_at",
                is_full_list=False,
                page=1,
                per_page=10,
            )
        """
        try:
            if not group_by:
                raise ValueError("group_by parameter is required for grouping")

            # Build SELECT clause
            select_fields = group_by.copy()  # Include GROUP BY fields

            # Add aggregations
            if aggregations:
                for result_field, agg_expression in aggregations.items():
                    select_fields.append(f"{agg_expression} AS {result_field}")

            select_clause = ", ".join(select_fields)

            # Build base query
            query_parts = [f"SELECT {select_clause} FROM {collection}"]

            # Add WHERE clause
            if filter:
                sql_where = self._convert_filter_to_sql(filter)
                if sql_where:
                    query_parts.append(f"WHERE {sql_where}")

            # Add GROUP BY clause
            group_clause = ", ".join(group_by)
            query_parts.append(f"GROUP BY {group_clause}")

            # Add ORDER BY clause (after grouping)
            if sort:
                sql_order = self._convert_sort_to_sql(sort)
                if sql_order:
                    query_parts.append(f"ORDER BY {sql_order}")

            # Handle pagination based on is_full_list flag
            if is_full_list:
                # Get all records (no pagination)
                query = " ".join(query_parts)
                logger.debug(f"SQL grouped query (full list): {query}")

                results = self.execute_raw_sql(query)

                logger.info(
                    f"SQL grouped query on '{collection}': "
                    f"retrieved {len(results)} groups"
                )
                return results

            else:
                # Paginated response

                # First, get total count of groups
                count_query_parts = [f"SELECT COUNT(*) as total FROM ("]
                count_query_parts.append(" ".join(query_parts))
                count_query_parts.append(")")

                count_query = " ".join(count_query_parts)
                count_result = self.execute_raw_sql(count_query)
                total_items = count_result[0]["total"] if count_result else 0
                total_pages = (total_items + per_page - 1) // per_page

                # Add pagination to data query
                offset = (page - 1) * per_page
                query_parts.append(f"LIMIT {per_page} OFFSET {offset}")

                query = " ".join(query_parts)
                logger.debug(f"SQL grouped query (page {page}): {query}")

                items = self.execute_raw_sql(query)

                logger.info(
                    f"SQL grouped query on '{collection}': "
                    f"page {page}/{total_pages}, {len(items)} groups"
                )

                # Return PocketBase-compatible paginated response
                return {
                    "page": page,
                    "perPage": per_page,
                    "totalItems": total_items,
                    "totalPages": total_pages,
                    "items": items,
                }

        except Exception as e:
            logger.error(f"Failed to execute grouped query on '{collection}': {e}")
            raise

    def _convert_filter_to_sql(self, pb_filter: str) -> str:
        """
        Convert PocketBase filter syntax to SQL WHERE clause.

        Args:
            pb_filter: PocketBase filter (e.g., 'status = "active" && priority > 5')

        Returns:
            SQL WHERE clause (e.g., "status = 'active' AND priority > 5")
        """
        if not pb_filter:
            return ""

        try:
            # Simple conversions
            sql_filter = pb_filter

            # Replace PocketBase operators with SQL operators
            sql_filter = sql_filter.replace("&&", "AND")
            sql_filter = sql_filter.replace("||", "OR")
            sql_filter = sql_filter.replace("!=", "<>")

            # Handle relation field syntax: "jobId.workOrderNumber" → "workOrderNumber"
            # This assumes the relation is already expanded or denormalized
            # TODO: Handle complex joins if needed
            if "." in sql_filter:
                logger.debug(f"Filter contains relation syntax (.), may need adjustment: {sql_filter}")

            return sql_filter

        except Exception as e:
            logger.error(f"Error converting filter to SQL: {e}")
            return ""

    def _convert_sort_to_sql(self, pb_sort: str) -> str:
        """
        Convert PocketBase sort syntax to SQL ORDER BY clause.

        Args:
            pb_sort: PocketBase sort (e.g., "-created" for DESC, "name,id" for multiple)

        Returns:
            SQL ORDER BY clause (e.g., "created DESC", "name ASC, id ASC")
        """
        if not pb_sort:
            return ""

        try:
            # Split multiple sort fields
            sort_fields = [s.strip() for s in pb_sort.split(",")]
            sql_parts = []

            for field in sort_fields:
                if field.startswith("-"):
                    # Descending order
                    sql_parts.append(f"{field[1:]} DESC")
                else:
                    # Ascending order (default)
                    sql_parts.append(f"{field} ASC")

            return ", ".join(sql_parts)

        except Exception as e:
            logger.error(f"Error converting sort to SQL: {e}")
            return ""


# Singleton instance
sql_db = SQLiteInterfaceClient()
