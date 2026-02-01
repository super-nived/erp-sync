import requests

url = "http://127.0.0.1:8080/data"
params = {
    "txnType": "BOM",
    "fromDate": "2025-01-27"
}

response = requests.get(url, params=params)
data = response.json()

# 1. Total records (with duplicates)
total_records = len(data)

# 2. Unique (BASE_ID + SUB_ID)
unique_base_sub = set()

# 3. Unique BASE_ID only
unique_base = set()

# 4. Unique (CUST_ORDER_ID + LINE_NO + BOM_PART_ID)
unique_project_bom = set()

for item in data:
    base_id = item.get("BOM_WORKORDER_BASE_ID")
    sub_id = item.get("BOM_WORKORDER_SUB_ID")

    cust_id = item.get("CUST_ORDER_ID")
    line_no = item.get("CUST_ORDER_LINE_NO")
    part_id = item.get("BOM_PART_ID")

    # 2
    unique_base_sub.add((base_id, sub_id))

    # 3
    unique_base.add(base_id)

    # 4
    unique_project_bom.add((cust_id, line_no, part_id))


print("Total Records:", total_records)
print("Unique (Base + Sub):", len(unique_base_sub))
print("Unique (Base Only):", len(unique_base))
print("Unique (Order + Line + Part):", len(unique_project_bom))
