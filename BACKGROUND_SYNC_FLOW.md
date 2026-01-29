# ERP to PocketBase Background Sync - Complete Flow Documentation

## Overview
This document explains how the background synchronization process works, including unique identifiers, change detection, and job processing.

---

## 1. Unique Record Identifier

### Primary Key Combination
Each ERP record is uniquely identified by **TWO fields combined**:

```
UNIQUE_ID = BOM_WORKORDER_BASE_ID + BOM_WORKORDER_SUB_ID
```

**Example:**
```json
{
  "BOM_WORKORDER_BASE_ID": "AW-123573.1",
  "BOM_WORKORDER_SUB_ID": "0",
  // ... other 60+ fields
}
```

**Unique ID:** `AW-123573.1-0`

This combination ensures:
- ✅ Same record from different syncs is identified as the same
- ✅ Updates go to the correct existing record
- ✅ No duplicate records in PocketBase

---

## 2. Three-Stage Storage Architecture

### Stage 1: SQLite Database (Local State)
**Purpose:** Durable storage, change detection, crash recovery

**Table: `erp_raw_data`**
```sql
CREATE TABLE erp_raw_data (
    id INTEGER PRIMARY KEY,           -- Auto-increment ID
    erp_id TEXT UNIQUE,               -- "AW-123573.1-0"
    payload_json TEXT,                -- Full record JSON
    payload_hash TEXT,                -- MD5 hash for change detection
    fetched_at TEXT                   -- Timestamp
)
```

**Table: `job_queue`**
```sql
CREATE TABLE job_queue (
    id INTEGER PRIMARY KEY,
    payload_ref INTEGER,              -- FK to erp_raw_data.id
    status TEXT,                      -- 'queued', 'processing', 'done', 'failed'
    retry_count INTEGER,
    last_error TEXT,
    next_attempt_at TEXT,
    created_at TEXT,
    updated_at TEXT
)
```

**Table: `push_log`**
```sql
CREATE TABLE push_log (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,                   -- FK to job_queue.id
    response_code INTEGER,            -- HTTP status (200, 500, etc)
    response_body TEXT,               -- Error details
    sent_at TEXT
)
```

### Stage 2: Job Queue (Processing Control)
**Purpose:** Track which records need processing, retry failed jobs

**Job States:**
- `queued` → Ready to process
- `processing` → Currently being processed
- `done` → Successfully synced to PocketBase
- `failed` → Max retries exceeded

### Stage 3: PocketBase (Final Destination)
**Purpose:** Store data for frontend/API consumption

**Collection:** `{PLANT_CODE}_erpConsolidateData`

**Unique Constraint:**
```
BOM_WORKORDER_BASE_ID + BOM_WORKORDER_SUB_ID
```

---

## 3. Complete Sync Flow (Step by Step)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ERP API (External System)                     │
│  https://aswanservice.aswan.com:8088/api/...                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP GET (Every 60 min)
                         │ Timeout: 600 seconds
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: FETCH from ERP                                          │
│  ────────────────────────────────────────────────────────────   │
│  • Fetches records from last 367 days                           │
│  • Returns JSON array (could be 7000+ records)                  │
│  • Example: [{BOM_WORKORDER_BASE_ID: "AW-123.1", ...}, ...]     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: STORE in SQLite (Idempotent)                           │
│  ────────────────────────────────────────────────────────────   │
│  For each record:                                                │
│    1. Generate unique ID: "AW-123.1-0"                          │
│    2. Calculate hash: md5(entire_json_payload)                  │
│    3. Check if record exists in erp_raw_data                    │
│                                                                  │
│    IF NEW:                                                       │
│      → Insert into erp_raw_data                                 │
│      → is_updated = False                                       │
│                                                                  │
│    IF EXISTS + SAME HASH:                                       │
│      → Skip (no changes)                                        │
│      → is_updated = False                                       │
│                                                                  │
│    IF EXISTS + DIFFERENT HASH:                                  │
│      → Update payload_json and payload_hash                     │
│      → is_updated = True                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: CREATE/REQUEUE Job                                     │
│  ────────────────────────────────────────────────────────────   │
│  IF NEW RECORD:                                                  │
│    → Create job with status='queued'                            │
│                                                                  │
│  IF is_updated = True:                                          │
│    → Find existing job                                          │
│    → IF job.status = 'done':                                    │
│        → Reset to 'queued' (force requeue)                      │
│        → Reset retry_count = 0                                  │
│                                                                  │
│  IF is_updated = False:                                         │
│    → Job stays as 'done' (no reprocessing)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: WORKER Picks Job (Every 5 seconds)                     │
│  ────────────────────────────────────────────────────────────   │
│  SELECT * FROM job_queue                                         │
│  WHERE status = 'queued'                                         │
│    AND next_attempt_at <= NOW()                                 │
│  ORDER BY created_at ASC                                         │
│  LIMIT 1;                                                        │
│                                                                  │
│  → Update job.status = 'processing'                             │
│  → Update job.last_attempt_at = NOW()                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: PROCESS Job                                            │
│  ────────────────────────────────────────────────────────────   │
│  1. Load payload from erp_raw_data                              │
│  2. Validate with Pydantic (ERPRecord schema)                   │
│  3. Transform to PocketBase format                              │
│  4. Check if record exists in PocketBase                        │
│     → Search by: BOM_WORKORDER_BASE_ID + BOM_WORKORDER_SUB_ID   │
│                                                                  │
│  IF EXISTS in PocketBase:                                       │
│    → UPDATE existing record (PATCH request)                     │
│                                                                  │
│  IF NOT EXISTS in PocketBase:                                   │
│    → CREATE new record (POST request)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: HANDLE Result                                          │
│  ────────────────────────────────────────────────────────────   │
│  SUCCESS (HTTP 200):                                             │
│    → job.status = 'done'                                        │
│    → Log to push_log (response_code=200)                        │
│                                                                  │
│  FAILURE (Exception/HTTP Error):                                │
│    → job.status = 'failed' (if retry_count >= 5)                │
│    → job.status = 'queued' (if retry_count < 5)                 │
│    → job.retry_count += 1                                       │
│    → job.next_attempt_at = NOW() + exponential_backoff          │
│    → job.last_error = error_message                             │
│    → Log to push_log (response_code=500)                        │
│                                                                  │
│  Retry Backoff Schedule:                                         │
│    - Retry 1: Wait 5 minutes                                    │
│    - Retry 2: Wait 10 minutes                                   │
│    - Retry 3: Wait 15 minutes                                   │
│    - Retry 4: Wait 20 minutes                                   │
│    - Retry 5: Wait 25 minutes                                   │
│    - After 5 retries: status='failed' (permanent)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Change Detection Logic (Hash-Based)

### How Hash Works

**Step 1: Calculate Hash**
```python
# Full record with 60+ fields
record = {
    "BOM_WORKORDER_BASE_ID": "AW-123.1",
    "BOM_WORKORDER_SUB_ID": "0",
    "BOM_QTY": 100,
    "PART_QTY_ON_HAND_WHOLE": 500.5,
    "WO_STATUS": "R",
    # ... 55+ more fields
}

# Sort keys to ensure consistent hash
import json, hashlib
sorted_json = json.dumps(record, sort_keys=True)
hash = hashlib.md5(sorted_json.encode()).hexdigest()
# Result: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

**Step 2: Compare Hash**
```python
old_hash = "a1b2c3d4..."  # From database
new_hash = "x9y8z7w6..."  # Just calculated

if old_hash != new_hash:
    # ANY field changed!
    update_record()
    requeue_job()
```

### Example Scenarios

#### Scenario A: Single Field Changes
```json
// Day 1
{"BOM_QTY": 100, "PART_ID": "ABC", ...}
Hash: "abc123..."

// Day 2 - Only BOM_QTY changed
{"BOM_QTY": 99, "PART_ID": "ABC", ...}
Hash: "xyz789..."  ← DIFFERENT!

Result: ✅ Record updated, job requeued
```

#### Scenario B: No Changes
```json
// Day 1
{"BOM_QTY": 100, "PART_ID": "ABC", ...}
Hash: "abc123..."

// Day 2 - Same data
{"BOM_QTY": 100, "PART_ID": "ABC", ...}
Hash: "abc123..."  ← SAME!

Result: ✅ No update, job stays done, no PocketBase call
```

#### Scenario C: Multiple Fields Change
```json
// Day 1
{"BOM_QTY": 100, "WO_STATUS": "R", "PART_QTY": 500, ...}
Hash: "abc123..."

// Day 2 - Three fields changed
{"BOM_QTY": 99, "WO_STATUS": "F", "PART_QTY": 450, ...}
Hash: "xyz789..."  ← DIFFERENT!

Result: ✅ Record updated, job requeued, entire record synced
```

---

## 5. Background Workers (3 Concurrent Loops)

### Worker 1: Fetch Loop
**Interval:** Every 60 minutes (configurable via `ERP_SYNC_INTERVAL_MINUTES`)

```python
while True:
    from_date = calculate_from_date()  # Last 367 days
    records = fetch_from_erp(from_date)

    for record in records:
        record_id, is_updated = store_in_sqlite(record)
        create_or_requeue_job(record_id, is_updated)

    sleep(60 * 60)  # Wait 1 hour
```

### Worker 2: Process Loop
**Interval:** Every 5 seconds

```python
while True:
    job = get_next_queued_job()

    if job:
        try:
            process_job(job)
            mark_as_done(job)
        except Exception as e:
            mark_as_failed(job, e)

    sleep(5)  # Check every 5 seconds
```

### Worker 3: Reaper Loop
**Interval:** Every 5 minutes

**Purpose:** Recover stuck jobs (crash recovery)

```python
while True:
    # Find jobs stuck in 'processing' for > 10 minutes
    stuck_jobs = find_stuck_processing_jobs(timeout=10)

    for job in stuck_jobs:
        reset_to_queued(job)  # Give them another chance

    sleep(300)  # Check every 5 minutes
```

---

## 6. Crash Recovery Scenarios

### Scenario A: App Crashes During ERP Fetch
**What Happens:**
- Partial data may be fetched
- Already inserted records are safe in SQLite

**Recovery:**
- Next fetch continues from same date
- Duplicates ignored by unique constraint on `erp_id`

### Scenario B: App Crashes During Job Processing
**What Happens:**
- Job stuck in `status='processing'`

**Recovery:**
- Reaper loop (every 5 min) finds jobs in `processing` for > 10 min
- Resets them to `queued`
- Worker picks them up again

### Scenario C: PocketBase Down
**What Happens:**
- Jobs fail with network error

**Recovery:**
- Job marked as `failed`
- Retry with exponential backoff
- Max 5 retries over ~75 minutes
- After 5 failures → permanent `failed` status

### Scenario D: Database Corruption
**What Happens:**
- SQLite file corrupted

**Recovery:**
- Delete `data/job_sync.db`
- Restart app
- All tables recreated
- Next sync fetches all data again

---

## 7. Configuration Options

### Environment Variables (.env)

```bash
# ERP API
ERP_API_URL=https://aswanservice.aswan.com:8088/api/...
ERP_TXN_TYPE=BOM

# Sync Timing
ERP_SYNC_INTERVAL_MINUTES=60        # How often to fetch
ERP_SYNC_DAYS_BACK=367              # How far back to fetch
ERP_SYNC_FROM_DATE=2025-01-01       # Override days_back (optional)

# PocketBase
POCKETBASE_URL=http://localhost:8090
PB_ADMIN_EMAIL=admin@example.com
PB_ADMIN_PASSWORD=your_password
PLANT_CODE=ASWNDUBAI               # Collection prefix
```

---

## 8. Monitoring & Logs

### Key Log Messages

**Successful Fetch:**
```
Fetching ERP data from 2025-01-27
Fetched 7741 records from ERP API
Stored 1791, queued 1791 records
```

**Change Detection:**
```
Updated record AW-123.1-0 (hash changed)
Requeued job 42 for updated data
```

**Successful Processing:**
```
Processing job 42
Updated AW-123.1-0
Job 42 completed
```

**Retry After Failure:**
```
Job processing error: Network timeout
Retry attempt 2/5 (next attempt in 10 minutes)
```

### Database Queries for Monitoring

```sql
-- Total records
SELECT COUNT(*) FROM erp_raw_data;

-- Job status breakdown
SELECT status, COUNT(*) FROM job_queue GROUP BY status;

-- Failed jobs with errors
SELECT id, last_error, retry_count
FROM job_queue
WHERE status='failed';

-- Recent successes
SELECT job_id, response_code, sent_at
FROM push_log
WHERE response_code=200
ORDER BY sent_at DESC
LIMIT 10;

-- Processing time
SELECT AVG(julianday(sent_at) - julianday(created_at)) * 24 * 60 as avg_minutes
FROM push_log p
JOIN job_queue j ON p.job_id = j.id
WHERE response_code=200;
```

---

## 9. API Endpoints

### POST /job-sync/trigger
Manually trigger a sync

**Request:**
```json
{
  "from_date": "2025-01-01"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "stored": 7741,
    "queued": 1234
  },
  "message": "Fetched and queued 1234 records"
}
```

### GET /job-sync/status
Check worker status

**Response:**
```json
{
  "success": true,
  "data": {
    "scheduler_running": true,
    "sync_in_progress": false
  },
  "message": "Sync status retrieved"
}
```

### POST /job-sync/stop
Stop the background worker

**Response:**
```json
{
  "success": true,
  "data": {
    "scheduler_running": false
  },
  "message": "Scheduler stopped successfully"
}
```

---

## 10. Performance Characteristics

### Throughput
- **Fetch:** ~7000 records in ~5 minutes (depends on ERP API)
- **Processing:** ~100 records/minute to PocketBase
- **Hash Comparison:** ~10,000 records/second (instant)

### Storage
- **SQLite DB Size:** ~5MB per 1000 records
- **Memory Usage:** ~50MB base + 10MB per 1000 queued jobs

### Network
- **ERP Fetch:** 1 request per hour (large payload)
- **PocketBase Sync:** 1 request per record (upsert)
- **Timeout:** 10 minutes for ERP, 15 seconds for PocketBase

---

## 11. Troubleshooting

### "Processed: 0 success, 0 failed" continuously
**Meaning:** No jobs in queue (all done)
**Action:** Normal! Means all records synced successfully

### Jobs stuck in "processing"
**Cause:** App crashed during processing
**Fix:** Wait 5-10 minutes for reaper to reset them

### "Transform error: validation error"
**Cause:** ERP data doesn't match schema (e.g., float vs int)
**Fix:** Update schema.py to accept correct types

### ERP fetch timeout
**Cause:** API taking > 10 minutes
**Fix:** Increase timeout in repo.py or reduce date range

### All jobs failing
**Cause:** PocketBase connection issue
**Fix:** Check PocketBase URL, credentials, collection exists

---

## Summary

**Unique Identifier:** `BOM_WORKORDER_BASE_ID + BOM_WORKORDER_SUB_ID`

**Change Detection:** MD5 hash of entire record

**Update Trigger:** Any single field change → hash changes → requeue

**Processing:** 3 concurrent workers (fetch, process, reaper)

**Reliability:** Crash recovery, retry logic, audit logs

**Efficiency:** Hash-based comparison, idempotent operations
