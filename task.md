ERP Flow Architecture (ERP -> Local SQL -> Processing -> Push)
This document describes the end-to-end flow, state model, and crash recovery for an ERP data pipeline that:

Pulls data from ERP
Stores it in a local SQL database
Processes and pushes it to a target system
Tracks every step for retry and recovery
The goal is to make the flow resilient to crashes and safe for reprocessing.

High-Level Flow
Fetch from ERP API on a schedule or trigger.
Store raw ERP records in SQL (idempotent).
Queue job rows to process each ERP record.
Worker processes queued jobs and pushes to target.
Record result and update job status.
Retry on failure with backoff.
Core Tables (Minimal Schema)
erp_raw_data
Stores raw ERP records safely and idempotently.

id (PK)
erp_id (unique ERP record ID)
payload_json (raw ERP JSON)
fetched_at
job_queue
Tracks processing state and retry logic.

id (PK)
payload_ref (FK -> erp_raw_data.id)
status (queued, processing, done, failed)
retry_count
last_error
last_attempt_at
next_attempt_at
created_at
updated_at
push_log
Stores target response for audit/debug.

id (PK)
job_id (FK -> job_queue.id)
response_code
response_body
sent_at
Detailed Process Step-by-Step
1) ERP Fetch
Trigger: Scheduler or cron job (for example, every N minutes or at shift end).

Logic:

Call ERP API.
For each ERP record:
Insert into erp_raw_data with erp_id unique constraint.
If insert fails due to duplicate erp_id, skip (already fetched).
Why: This creates a durable, idempotent landing zone.

2) Queue Job Creation
Trigger: Same fetch step or a separate reconciliation job.

Logic:

For each newly inserted erp_raw_data row:
Insert a job_queue row with status = 'queued'.
Why: Separates data ingestion from processing, so crashes during processing do not lose the data.

3) Worker Picks Jobs
Trigger: Continuous worker loop or scheduled worker.

Logic:

Select jobs where:
status = 'queued'
next_attempt_at <= now
Atomically update the job to:
status = 'processing'
last_attempt_at = now
Why: Prevents multiple workers from processing the same job.

4) Process and Push
Logic:

Read the ERP payload from erp_raw_data.
Build a target payload.
Send to target system.
Record response in push_log.
Outcome:

On success:
job_queue.status = 'done'
On failure:
job_queue.status = 'failed'
retry_count += 1
next_attempt_at = now + backoff
last_error set to failure reason
Crash and Recovery Scenarios
Scenario A: Crash During Fetch
What happens:

Partial ERP response may be ingested.
Already inserted erp_raw_data rows are safe.
Recovery:

Next fetch continues, duplicates are ignored by erp_id unique constraint.
Scenario B: Crash After Raw Insert, Before Job Creation
What happens:

Data exists in erp_raw_data, but no job_queue row.
Recovery:

A reconciliation job scans for erp_raw_data rows with no matching job_queue and inserts missing jobs.
Scenario C: Crash While Job Is processing
What happens:

Job is stuck in processing.
Recovery:

A reaper job finds processing jobs older than N minutes and resets them to queued (or failed with a retry increment).
Scenario D: Crash After Push Success, Before Status Update
What happens:

Target received the data, but job still marked processing or failed.
Recovery options:

Use idempotent push IDs so re-sends are safe.
Or check push_log / target API to detect success before re-sending.
Scenario E: Crash During Retry Backoff
What happens:

Job is in failed with next_attempt_at in the future.
Recovery:

Worker will retry automatically once next_attempt_at <= now.
Recommended State Machine
queued -> processing -> done
             |
             v
          failed -> queued (via retry/backoff)
Scheduling Options
Time-based: Run fetch every N minutes.
Simple and reliable.
Shift-based: Fetch at shift end (like your current scheduler).
Matches operational cycles.
Event-based: If ERP supports webhooks (rare), trigger on event.



erp url ,https://aswanservice.aswan.com:8088/api/inprocessjobsBOMmaterialsDetails?txnType=BOM&fromDate=2025-12-01
responce formate [
{
"TXN_TYPE": "BOM",
"CUST_ORDER_ID": "SO-122573",
"CUST_ORDER_LINE_NO": 2,
"CUST_ORDER_DATE": "2025-07-11T00:00:00",
"CUST_ORDER_WANT_DATE": "2025-07-31T00:00:00",
"CUST_ORDER_LINE_WANT_DATE": "2025-07-31T00:00:00",
"CUST_ORDER_STATUS": "R",
"WO_ASSMB_PART_ID": "",
"WO_ASSMB_QTY": 1,
"WO_CREATE_DATE": "2025-12-08T09:39:14.893",
"WO_RLS_DATE": "2025-12-08T09:39:14.893",
"WO_WANT_DATE": "2025-07-31T00:00:00",
"WO_CLOSE_DATE": null,
"WO_STATUS": "F",
"WO_PRODUCT_CODE": "_P-ANNULR-BOP-R",
"WO_ASW_STATUS": "",
"BOM_WORKORDER_TYPE": "W",
"BOM_WORKORDER_BASE_ID": "AW-122573.1",
"BOM_WORKORDER_LOT_ID": "1",
"BOM_WORKORDER_SPLIT_ID": "0",
"BOM_WORKORDER_SUB_ID": "1",
"BOM_OPERATION_SEQ_NO": 120,
"BOM_PIECE_NO": 10,
"BOM_PART_ID": "DP0036",
"BOM_QTY": 10,
"PART_IS_MANUFACTURE": "N",
"PART_CATEGORY": "RM",
"PART_QTY_ON_HAND_WHOLE": 279,
"PART_QTY_ON_ORDER_WHOLE": 0,
"PART_QTY_IN_DEMAND_WHOLE": 273,
"PART_LEADTIME_DAYS": 0,
"PURC_REQ_ID": "",
"PURC_REQ_LINE_NO": 0,
"PURC_REQ_PART_ID": "",
"PURC_REQ_QTY": 0,
"PURC_REQ_DATE": null,
"PURC_REQ_WANT_DATE": null,
"PURC_ORDER_ID": "",
"PO_LINE_NO": 0,
"PO_QTY": 0,
"PURC_ORDER_DATE": null,
"PURC_ORDER_STATUS": "",
"PO_WANT_DATE": null,
"PO_ETD": null,
"PO_ETA": null,
"GRN_ID": "",
"GRN_LINE_NO": 0,
"GRN_QTY": 0,
"GRN_INSPECT_QTY": 0,
"GRN_REJECTED_QTY": 0,
"GRN_DATE": null,
"GRN_CREATE_DATE": null,
"GRN_INSPECTION_DATE": null,
"INV_TRANS_ID": 0,
"INV_TRANS_PART_ID": "",
"INV_TRANS_TYPE": "",
"INV_TRANS_CLASS": "",
"INV_TRANS_QTY": 0,
"INV_TRANS_DATE": null,
"INV_TRANS_CREATE_DATE": null
}]


inervall 1 hour, if one sync take above 1 only start next shcedule after this one complate okay 

table schema to apply this one


[
    {
        "id": "xil63txo81b8yd7",
        "name": "ASWNDUBAI_erpConsolidateData",
        "type": "base",
        "system": false,
        "schema": [
            {
                "system": false,
                "id": "re2jzp2n",
                "name": "TXN_TYPE",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "ukfdrl6z",
                "name": "CUST_ORDER_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "cminpcrb",
                "name": "CUST_ORDER_LINE_NO",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "gfclfcdx",
                "name": "CUST_ORDER_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "secnfw0x",
                "name": "CUST_ORDER_WANT_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "5yyywdus",
                "name": "CUST_ORDER_LINE_WANT_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "lcz822yw",
                "name": "CUST_ORDER_STATUS",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "osy4w8s4",
                "name": "WO_ASSMB_PART_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "ey85013o",
                "name": "WO_ASSMB_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "mrua4ujk",
                "name": "WO_CREATE_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "kvkzu1pk",
                "name": "WO_RLS_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "7irwiyuw",
                "name": "WO_WANT_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "yhb24unc",
                "name": "WO_STATUS",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "jfsq4luf",
                "name": "WO_PRODUCT_CODE",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "iccisdid",
                "name": "WO_ASW_STATUS",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "czk60q0z",
                "name": "BOM_WORKORDER_TYPE",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "sfjsuuo6",
                "name": "BOM_WORKORDER_BASE_ID",
                "type": "text",
                "required": true,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "vslzcdqi",
                "name": "BOM_WORKORDER_LOT_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "szvh4xqa",
                "name": "BOM_WORKORDER_SPLIT_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "8fs7pcua",
                "name": "BOM_WORKORDER_SUB_ID",
                "type": "text",
                "required": true,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "cuwgys1q",
                "name": "BOM_OPERATION_SEQ_NO",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "gr2jfbcg",
                "name": "BOM_PIECE_NO",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "8o8cjluk",
                "name": "BOM_PART_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "mmzdk4oc",
                "name": "BOM_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "ksqfgccn",
                "name": "PART_IS_MANUFACTURE",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "suhe3khw",
                "name": "PART_CATEGORY",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "zlxbpb4o",
                "name": "PURC_REQ_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "9y27dszo",
                "name": "PURC_REQ_LINE_NO",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "a6h23nnr",
                "name": "PURC_REQ_PART_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "j3nrlrcf",
                "name": "PURC_REQ_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "uk7i2s3m",
                "name": "PURC_REQ_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "qhbzh4zh",
                "name": "PURC_REQ_WANT_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "ek9swmfk",
                "name": "PURC_ORDER_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "wygfaz1q",
                "name": "PO_LINE_NO",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "f5ferxb9",
                "name": "PO_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "vshwtt1s",
                "name": "PURC_ORDER_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "p1cwvwpp",
                "name": "PURC_ORDER_STATUS",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "l8kumq9b",
                "name": "PO_WANT_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "tnuohohb",
                "name": "PO_ETD",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "1tqaevuv",
                "name": "PO_ETA",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "eucmqugu",
                "name": "GRN_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "lsesykts",
                "name": "GRN_LINE_NO",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "bzjxhlb3",
                "name": "GRN_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "xrvzryu8",
                "name": "GRN_INSPECT_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "sqwg2ddu",
                "name": "GRN_REJECTED_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "dprce0ri",
                "name": "GRN_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "gl7k1mnu",
                "name": "GRN_CREATE_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "ygnouhmi",
                "name": "INV_TRANS_ID",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "sddffa8y",
                "name": "INV_TRANS_PART_ID",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "nm9woxhe",
                "name": "INV_TRANS_TYPE",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "6aoersii",
                "name": "INV_TRANS_CLASS",
                "type": "text",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "pattern": ""
                }
            },
            {
                "system": false,
                "id": "7jroiymm",
                "name": "INV_TRANS_QTY",
                "type": "number",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": null,
                    "max": null,
                    "noDecimal": false
                }
            },
            {
                "system": false,
                "id": "jft2hvt5",
                "name": "INV_TRANS_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            },
            {
                "system": false,
                "id": "og1hl5iw",
                "name": "INV_TRANS_CREATE_DATE",
                "type": "date",
                "required": false,
                "presentable": false,
                "unique": false,
                "options": {
                    "min": "",
                    "max": ""
                }
            }
        ],
        "indexes": [],
        "listRule": "",
        "viewRule": "",
        "createRule": "",
        "updateRule": "",
        "deleteRule": "",
        "options": {}
    }
]