import requests
import pandas as pd
import time
import json
from datetime import datetime

API_URL = "https://www.clarin.si/noske/run.cgi/first"
IP_CHECK_URL = "https://api64.ipify.org?format=json"  # To check current IP address

# File paths
INPUT_FILE = "C://Users//Korisnik//Downloads//test.xlsx"
OUTPUT_BASE = "C://Users//Korisnik//Downloads//frequencies_day_"
PROGRESS_FILE = "progress.json"  # File to track progress

# Query limits
MAX_QUERIES_PER_MINUTE = 95
MAX_QUERIES_PER_HOUR = 850
MAX_QUERIES_PER_DAY = 1950

# Global setting for handling plain text
plain_text_treatment = "word"  # Default; will be updated based on user input

def query_concordance(query, corpus="srwac"):
    """
    Query concordance to fetch absolute frequency using a provided query.
    Automatically handles both plain text and CQL queries.
    """
    global plain_text_treatment

    # If the query is plain text, convert it based on the user-defined treatment
    if not query.strip().startswith("[") or not query.strip().endswith("]"):
        if plain_text_treatment == "word":
            cql_query = f'[word="{query.strip()}"]'
        elif plain_text_treatment == "lemma":
            cql_query = f'[lemma="{query.strip()}"]'
        else:
            print("Invalid plain text treatment setting.")
            return 0
    else:
        # Assume the query is already in CQL format
        cql_query = query.strip()

    params = {
        "corpname": corpus,
        "queryselector": "cqlrow",
        "cql": cql_query,
        "default_attr": "word",
        "pagesize": 1,
        "format": "json"
    }

    try:
        response = requests.get(API_URL, params=params)
        data = response.json()
        absolute_frequency = data.get("concsize", 0)
        return absolute_frequency
    except Exception as e:
        print(f"Exception occurred while querying '{query}': {e}")
        return 0

def save_progress(last_row):
    """Save progress to the progress file."""
    with open(PROGRESS_FILE, "w") as file:
        json.dump({"last_row": last_row, "day": datetime.now().strftime("%Y-%m-%d")}, file)

def process_spreadsheet(start_row, end_row, columns_to_scan):
    """Process the spreadsheet starting from the specified row to the ending row."""
    df = pd.read_excel(INPUT_FILE)
    for col in columns_to_scan:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in the input file.")

    query_count_minute = 0
    query_count_hour = 0
    query_count_day = 0
    start_time = time.time()

    # Load progress if exists
    try:
        with open(PROGRESS_FILE, "r") as file:
            progress = json.load(file)
        start_row = max(start_row, progress.get("last_row", start_row))
        print(f"Resuming from row {start_row}.")
    except FileNotFoundError:
        print("No progress file found. Starting fresh.")

    for index in range(start_row - 1, end_row):  # Convert to 0-based index
        for col in columns_to_scan:
            cql_query = df.at[index, col]
            if pd.isna(cql_query) or not isinstance(cql_query, str):
                print(f"Skipping invalid query in row {index + 1}, column {col}.")
                continue

            abs_freq = query_concordance(cql_query)
            df.at[index, col] = abs_freq
            query_count_minute += 1
            query_count_hour += 1
            query_count_day += 1

            # Enforce minute limit
            if query_count_minute >= MAX_QUERIES_PER_MINUTE:
                elapsed = time.time() - start_time
                if elapsed < 60:
                    print(f"Minute limit reached. Pausing for {60 - elapsed:.2f} seconds.")
                    time.sleep(60 - elapsed)
                query_count_minute = 0
                start_time = time.time()

            # Enforce hourly limit
            if query_count_hour >= MAX_QUERIES_PER_HOUR:
                print("Hourly limit reached. Pausing for 1 hour.")
                time.sleep(3600)
                query_count_hour = 0

            # Enforce daily limit
            if query_count_day >= MAX_QUERIES_PER_DAY:
                day_output = OUTPUT_BASE + f"{datetime.now().strftime('%Y%m%d')}.xlsx"
                df.to_excel(day_output, index=False)
                save_progress(index + 1)
                print(f"Daily limit reached. Results saved to {day_output}. Pausing for 24 hours.")
                time.sleep(86400)  # Sleep for 24 hours
                query_count_day = 0

        save_progress(index + 1)

    day_output = OUTPUT_BASE + f"{datetime.now().strftime('%Y%m%d')}.xlsx"
    df.to_excel(day_output, index=False)
    print(f"Processing complete. Results saved to {day_output}.")

def main():
    """Main function."""
    global plain_text_treatment

    print("CORPUS QUERIER")
    print("Do you want to treat plain text queries as:")
    print("1. Word queries (e.g., [word=\"example\"])")
    print("2. Lemma queries (e.g., [lemma=\"example\"])")
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice == "1":
            plain_text_treatment = "word"
            break
        elif choice == "2":
            plain_text_treatment = "lemma"
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    try:
        start_row = int(input("Enter the starting row (1-based index): ").strip())
        end_row = int(input("Enter the ending row (1-based index): ").strip())
        if start_row < 1 or end_row < start_row:
            print("Error: Invalid row range.")
            return

        columns_input = input(
            "Enter the column names to scan, separated by commas (default: D,E,F,G,H,I,J): "
        ).strip()
        columns_to_scan = (
            [col.strip() for col in columns_input.split(",")]
            if columns_input
            else ["D", "E", "F", "G", "H", "I", "J"]
        )

        print(f"Columns to scan: {columns_to_scan}")
        process_spreadsheet(start_row, end_row, columns_to_scan)
    except ValueError:
        print("Invalid input. Please enter valid numbers for the starting and ending rows.")

if __name__ == "__main__":
    main()
