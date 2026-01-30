import requests
import re
import time
 
BASE_URL = "https://sql-interface.dev.industryapps.net/ASWN/sqlite-interface/get"
TIMEOUT = 60
 
TABLES = [
 "ASWNDUBAI_erpConsolidateData","ASWNDUBAI_mpsEventTracker","ASWNDUBAI_mpsJobTimeline","ASWNDUBAI_mpsSalesOrderDateChangeLog"

]
 
 
def delete_all_tables_data(tables):
    """
    Deletes all rows from the given list of tables.
    """
    for table in tables:
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            raise ValueError(f"Invalid table name: {table}")
 
        query = f"DELETE FROM {table};"
        response = requests.get(
            BASE_URL,
            params={"query": query},
            timeout=TIMEOUT
        )
 
        if response.status_code != 200:
            raise Exception(
                f"Failed to delete data from {table}\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )
 
        print(f"✅ Deleted all data from {table}")
        time.sleep(0.5)  # small delay to avoid gateway overload
 
 
# Example usage
if __name__ == "__main__":
    delete_all_tables_data(TABLES)
 