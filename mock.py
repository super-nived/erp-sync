from fastapi import FastAPI, Query
from contextlib import asynccontextmanager
import random
import datetime

# -----------------------------
# In-memory storage
# -----------------------------
DATASET = []


# -----------------------------
# Utils
# -----------------------------
def random_date(start_year=2023, end_year=2026):
    start = datetime.date(start_year, 1, 1)
    end = datetime.date(end_year, 12, 31)

    delta = end - start
    return str(start + datetime.timedelta(days=random.randint(0, delta.days)))


def init_data(
    total_customers=3000,
    lines_per_customer=5,     # Each customer has 5 projects
    subs_per_line=10          # Each project has 10 sub workorders
):
    """
    Generates clean sequential ERP-style data
    """

    if DATASET:
        return

    record_id = 1

    for cust_no in range(1, total_customers + 1):

        cust_order_id = f"CO-{100000 + cust_no}"

        # Line items: 1,2,3,4...
        for line_no in range(1, lines_per_customer + 1):

            base_id = f"AW{cust_order_id}.{line_no}"

            # Sub IDs: 0,1,2,3...
            for sub_id in range(subs_per_line):

                DATASET.append({

                    # Customer
                    "TXN_TYPE": "SALE",
                    "CUST_ORDER_ID": cust_order_id,
                    "CUST_ORDER_LINE_NO": line_no,
                    "CUST_ORDER_DATE": random_date(),
                    "CUST_ORDER_WANT_DATE": random_date(),
                    "CUST_ORDER_LINE_WANT_DATE": random_date(),
                    "CUST_ORDER_STATUS": "OPEN",

                    # Work Order
                    "WO_ASSMB_PART_ID": f"ASM-{record_id}",
                    "WO_ASSMB_QTY": random.randint(1, 100),
                    "WO_CREATE_DATE": random_date(),
                    "WO_RLS_DATE": random_date(),
                    "WO_WANT_DATE": random_date(),
                    "WO_STATUS": "RELEASED",
                    "WO_PRODUCT_CODE": f"PROD-{record_id}",
                    "WO_ASW_STATUS": "ON_TRACK",

                    # BOM (Main Rule)
                    "BOM_WORKORDER_TYPE": "MFG",
                    "BOM_WORKORDER_BASE_ID": base_id,
                    "BOM_WORKORDER_LOT_ID": f"L{record_id}",
                    "BOM_WORKORDER_SPLIT_ID": "0",

                    # IMPORTANT
                    "BOM_WORKORDER_SUB_ID": str(sub_id),

                    "BOM_OPERATION_SEQ_NO": 10 + sub_id,
                    "BOM_PIECE_NO": 1,
                    "BOM_PART_ID": f"PART-{record_id}",
                    "BOM_QTY": 1,

                    # Part
                    "PART_IS_MANUFACTURE": True,
                    "PART_CATEGORY": "MECHANICAL",

                    # PR
                    "PURC_REQ_ID": f"PR-{record_id}",
                    "PURC_REQ_LINE_NO": 1,
                    "PURC_REQ_PART_ID": f"PART-{record_id}",
                    "PURC_REQ_QTY": 1,
                    "PURC_REQ_DATE": random_date(),
                    "PURC_REQ_WANT_DATE": random_date(),

                    # PO
                    "PURC_ORDER_ID": f"PO-{record_id}",
                    "PO_LINE_NO": 1,
                    "PO_QTY": 1,
                    "PURC_ORDER_DATE": random_date(),
                    "PURC_ORDER_STATUS": "CONFIRMED",
                    "PO_WANT_DATE": random_date(),
                    "PO_ETD": random_date(),
                    "PO_ETA": random_date(),

                    # GRN
                    "GRN_ID": f"GRN-{record_id}",
                    "GRN_LINE_NO": 1,
                    "GRN_QTY": 1,
                    "GRN_INSPECT_QTY": 1,
                    "GRN_REJECTED_QTY": 0,
                    "GRN_DATE": random_date(),
                    "GRN_CREATE_DATE": random_date(),

                    # Inventory
                    "INV_TRANS_ID": f"IT-{record_id}",
                    "INV_TRANS_PART_ID": f"PART-{record_id}",
                    "INV_TRANS_TYPE": "IN",
                    "INV_TRANS_CLASS": "RAW",
                    "INV_TRANS_QTY": 1,
                    "INV_TRANS_DATE": random_date(),
                    "INV_TRANS_CREATE_DATE": random_date(),
                })

                record_id += 1

# -----------------------------
# Lifespan
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    init_data()   # Startup
    yield
    DATASET.clear()  # Shutdown


# -----------------------------
# App
# -----------------------------
app = FastAPI(lifespan=lifespan)


# -----------------------------
# API
# -----------------------------
@app.get("/api/erp-records")
def get_erp_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500)
):
    total = len(DATASET)

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total,
        "total_pages": (total + page_size - 1) // page_size,
        "records": DATASET[start:end],
    }
