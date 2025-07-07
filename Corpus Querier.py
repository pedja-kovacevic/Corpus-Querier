import requests
import json
import pandas as pd
import time

API_KEY = "ADD-API-KEY"
API_URL = "https://api.sketchengine.eu/bonito/run.cgi/view"
CORPUS = "preloaded/srwac12"
INPUT_FILE = "INPUT-FILE-LOCATION"
OUTPUT_FILE = "OUTPUT-FILE-LOCATION"

MAX_REQUESTS_PER_MINUTE = 100
MAX_REQUESTS_PER_HOUR = 900
MAX_REQUESTS_PER_DAY = 2000

request_counts = {"minute": 0, "hour": 0, "day": 0}
start_time_minute = time.time()
start_time_hour = time.time()
start_time_day = time.time()
last_request_time = 0

def fup_delay():
    global request_counts, start_time_minute, start_time_hour, start_time_day, last_request_time
    current_time = time.time()

    if current_time - start_time_minute >= 60:
        request_counts["minute"] = 0
        start_time_minute = current_time
    if current_time - start_time_hour >= 3600:
        request_counts["hour"] = 0
        start_time_hour = current_time
    if current_time - start_time_day >= 86400:
        request_counts["day"] = 0
        start_time_day = current_time

    request_counts["minute"] += 1
    request_counts["hour"] += 1
    request_counts["day"] += 1

    elapsed_since_last = current_time - last_request_time
    if request_counts["minute"] > MAX_REQUESTS_PER_MINUTE and request_counts["hour"] <= MAX_REQUESTS_PER_HOUR:
        wait_time = 4 - elapsed_since_last
        if wait_time > 0:
            time.sleep(wait_time)
    elif request_counts["hour"] > MAX_REQUESTS_PER_HOUR:
        wait_time = 45 - elapsed_since_last
        if wait_time > 0:
            time.sleep(wait_time)
    elif request_counts["day"] > MAX_REQUESTS_PER_DAY:
        raise RuntimeError("Daily API request limit reached. Please wait before continuing.")

    last_request_time = time.time()

def get_hits_for_query(query):
    cql_query = f"q{query.strip()}"
    json_query = {
        "corpname": CORPUS,
        "q": [cql_query, "r1"]
    }
    json_str = json.dumps(json_query)

    params = {
        "corpname": CORPUS,
        "json": json_str,
        "api_key": API_KEY,
        "format": "json"
    }

    fup_delay()

    response = requests.get(API_URL, params=params)

    if response.status_code == 429:
        print("Too many requests: backing off for 60 seconds.")
        time.sleep(60)
        return get_hits_for_query(query)

    if response.status_code == 200:
        data = response.json()
        total_hits = 0
        if "Desc" in data:
            for desc in data["Desc"]:
                if "size" in desc:
                    total_hits = desc["size"]
                    break
        return total_hits
    else:
        print(f"API call failed for query '{query}'. Status code: {response.status_code}")
        return None

def main():
    try:
        df = pd.read_excel(INPUT_FILE)
    except Exception as e:
        print(f"Failed to load input file: {e}")
        return

    columns_input = input("Enter column names to scan, separated by commas (e.g. A,B,C): ").strip()
    columns_to_scan = [col.strip() for col in columns_input.split(",") if col.strip()]
    if not columns_to_scan:
        print("No valid columns specified.")
        return

    start_row = input("Enter starting row number (1-based index): ").strip()
    end_row = input("Enter ending row number (1-based index): ").strip()
    try:
        start_row = int(start_row)
        end_row = int(end_row)
        if start_row < 1 or end_row < start_row:
            print("Invalid row range.")
            return
    except ValueError:
        print("Invalid row input.")
        return

    for col in columns_to_scan:
        if col not in df.columns:
            print(f"Column '{col}' not found in the spreadsheet.")
            return

    # Calculate total queries to process
    total_queries = 0
    for idx in range(start_row - 1, min(end_row, len(df))):
        for col in columns_to_scan:
            query = df.at[idx, col]
            if pd.isna(query) or not isinstance(query, str) or not query.strip():
                continue
            total_queries += 1

    completed_queries = 0
    for idx in range(start_row - 1, min(end_row, len(df))):
        for col in columns_to_scan:
            query = df.at[idx, col]
            if pd.isna(query) or not isinstance(query, str) or not query.strip():
                continue

            hits = get_hits_for_query(query.strip())
            df.at[idx, col] = hits

            completed_queries += 1
            print(f"Processed {completed_queries} out of {total_queries} queries.")

    try:
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"Results saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Failed to save output file: {e}")

if __name__ == "__main__":
    main()
