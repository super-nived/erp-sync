"""
Job Sync Schema Definitions

Pydantic models for ERP data and API contracts.
Following spec.md: Only data shapes, no logic, no DB calls.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ERPRecord(BaseModel):
    """ERP API response record schema."""

    TXN_TYPE: Optional[str] = None
    CUST_ORDER_ID: Optional[str] = None
    CUST_ORDER_LINE_NO: Optional[int] = None
    CUST_ORDER_DATE: Optional[datetime] = None
    CUST_ORDER_WANT_DATE: Optional[datetime] = None
    CUST_ORDER_LINE_WANT_DATE: Optional[datetime] = None
    CUST_ORDER_STATUS: Optional[str] = None
    WO_ASSMB_PART_ID: Optional[str] = None
    WO_ASSMB_QTY: Optional[float] = None
    WO_CREATE_DATE: Optional[datetime] = None
    WO_RLS_DATE: Optional[datetime] = None
    WO_WANT_DATE: Optional[datetime] = None
    WO_CLOSE_DATE: Optional[datetime] = None
    WO_STATUS: Optional[str] = None
    WO_PRODUCT_CODE: Optional[str] = None
    WO_ASW_STATUS: Optional[str] = None
    BOM_WORKORDER_TYPE: Optional[str] = None
    BOM_WORKORDER_BASE_ID: str
    BOM_WORKORDER_LOT_ID: Optional[str] = None
    BOM_WORKORDER_SPLIT_ID: Optional[str] = None
    BOM_WORKORDER_SUB_ID: str
    BOM_OPERATION_SEQ_NO: Optional[int] = None
    BOM_PIECE_NO: Optional[int] = None
    BOM_PART_ID: Optional[str] = None
    BOM_QTY: Optional[float] = None
    PART_IS_MANUFACTURE: Optional[str] = None
    PART_CATEGORY: Optional[str] = None
    PART_QTY_ON_HAND_WHOLE: Optional[float] = None
    PART_QTY_ON_ORDER_WHOLE: Optional[float] = None
    PART_QTY_IN_DEMAND_WHOLE: Optional[float] = None
    PART_LEADTIME_DAYS: Optional[float] = None
    PURC_REQ_ID: Optional[str] = None
    PURC_REQ_LINE_NO: Optional[int] = None
    PURC_REQ_PART_ID: Optional[str] = None
    PURC_REQ_QTY: Optional[float] = None
    PURC_REQ_DATE: Optional[datetime] = None
    PURC_REQ_WANT_DATE: Optional[datetime] = None
    PURC_ORDER_ID: Optional[str] = None
    PO_LINE_NO: Optional[int] = None
    PO_QTY: Optional[float] = None
    PURC_ORDER_DATE: Optional[datetime] = None
    PURC_ORDER_STATUS: Optional[str] = None
    PO_WANT_DATE: Optional[datetime] = None
    PO_ETD: Optional[datetime] = None
    PO_ETA: Optional[datetime] = None
    GRN_ID: Optional[str] = None
    GRN_LINE_NO: Optional[int] = None
    GRN_QTY: Optional[float] = None
    GRN_INSPECT_QTY: Optional[float] = None
    GRN_REJECTED_QTY: Optional[float] = None
    GRN_DATE: Optional[datetime] = None
    GRN_CREATE_DATE: Optional[datetime] = None
    GRN_INSPECTION_DATE: Optional[datetime] = None
    INV_TRANS_ID: Optional[int] = None
    INV_TRANS_PART_ID: Optional[str] = None
    INV_TRANS_TYPE: Optional[str] = None
    INV_TRANS_CLASS: Optional[str] = None
    INV_TRANS_QTY: Optional[float] = None
    INV_TRANS_DATE: Optional[datetime] = None
    INV_TRANS_CREATE_DATE: Optional[datetime] = None


class SyncJobStatus(BaseModel):
    """Sync job status response."""

    job_id: str
    status: str
    records_processed: int
    records_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SyncTriggerRequest(BaseModel):
    """Manual sync trigger request."""

    from_date: Optional[str] = Field(
        None, description="Date in YYYY-MM-DD format"
    )
