"""
PocketBase Collection Name Helper

Centralized configuration for ALL collection base names and dynamic naming with PLANT_CODE prefix.
This enables:
1. Single source of truth for collection names
2. Multi-tenant/multi-plant support with isolated data

**IMPORTANT**: To change any collection name, update COLLECTION_BASE_NAMES below.
All code uses these constants, so changes propagate automatically.

Usage:
    from app.db.collections import CollectionNames

    # Use centralized collection names
    pb.get_full_list(CollectionNames.PROJECTS)  # Returns: "ASWNDUBAI_projects"
    pb.get_full_list(CollectionNames.ERP_SOURCE)  # Returns: "ASWNDUBAI_erpConsolidateData"
"""

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)


# ============================================================================
# CENTRALIZED COLLECTION BASE NAMES
# ============================================================================
# **CHANGE COLLECTION NAMES HERE** - Updates automatically everywhere
# ============================================================================

class COLLECTION_BASE_NAMES:
    """
    Central configuration for all PocketBase collection base names.

    **TO CHANGE A COLLECTION NAME**: Update the value here, and it will
    automatically update throughout the entire application.

    Example:
        ERP_SOURCE = "erpConsolidateData"  # Change to "erpData" if needed
    """

    # ERP Source Data Collections
    ERP_SOURCE = "erpConsolidateData"  # Main ERP data source

    # Sync Management Collections
    SYNC_LOG = "syncLog"  # Sync execution logs
    SYNC_CONFIG = "syncConfig"  # Sync configuration
    SYNC_ERROR = "syncError"  # Sync error tracking

    # System Collections
    REPORTS = "reports"
    LOGS = "logs"


# ============================================================================
# Helper Function
# ============================================================================

def get_collection(base_name: str) -> str:
    """
    Get full collection name with PLANT_CODE prefix.

    Args:
        base_name: Base collection name (e.g., "projects", "machines")

    Returns:
        Full collection name with plant prefix (e.g., "ASWNDUBAI_projects")

    Examples:
        >>> get_collection("projects")
        'ASWNDUBAI_projects'

        >>> get_collection("machines")
        'ASWNDUBAI_machines'
    """
    plant_code = settings.plant_code

    # If plant code is DEFAULT or empty, return base name without prefix
    if not plant_code or plant_code == "DEFAULT":
        return base_name

    # Return prefixed collection name
    full_name = f"{plant_code}_{base_name}"
    logger.debug(f"Collection name: {base_name} → {full_name}")
    return full_name


# ============================================================================
# Collection Name Constants (Ready-to-use with plant prefix)
# ============================================================================

class CollectionNames:
    """
    Ready-to-use collection names with PLANT_CODE prefix applied.

    **RECOMMENDED USAGE**: Import and use these constants everywhere.

    Usage:
        from app.db.collections import CollectionNames

        # In your code
        pb.get_full_list(CollectionNames.ERP_SOURCE)
        pb.get_full_list(CollectionNames.SYNC_LOG)

    Benefits:
    - IDE autocomplete support
    - Type safety
    - Single source of truth
    - Automatic plant prefix
    """

    # ERP Source Data Collections
    ERP_SOURCE = property(lambda self: get_collection(COLLECTION_BASE_NAMES.ERP_SOURCE))

    # Sync Management Collections
    SYNC_LOG = property(lambda self: get_collection(COLLECTION_BASE_NAMES.SYNC_LOG))
    SYNC_CONFIG = property(lambda self: get_collection(COLLECTION_BASE_NAMES.SYNC_CONFIG))
    SYNC_ERROR = property(lambda self: get_collection(COLLECTION_BASE_NAMES.SYNC_ERROR))

    # System Collections
    REPORTS = property(lambda self: get_collection(COLLECTION_BASE_NAMES.REPORTS))
    LOGS = property(lambda self: get_collection(COLLECTION_BASE_NAMES.LOGS))


# Singleton instance for easy access
collections = CollectionNames()
