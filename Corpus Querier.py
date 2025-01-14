import requests
import pandas as pd
import time
import json
from datetime import datetime

# Constants
API_URL = "https://www.clarin.si/noske/run.cgi/first"
PROGRESS_FILE = "progress.json"  # For progress tracking

# Query limits
MAX_QUERIES_PER_MINUTE = 95
MAX_QUERIES_PER_HOUR = 850
MAX_QUERIES_PER_DAY = 1950

# File paths
INPUT_FILE = "C://Users//Korisnik//Downloads//queries.xlsx"
OUTPUT_BASE = "C://Users//Korisnik//Downloads//frequencies_day_"

# Global settings
plain_text_treatment = "word"  # Default: Treat plain text as word queries

def query_concordance(query, corpus="srwac"):
    """
    Query concordance API for the frequency of a given query.
    Automatically determines whether the query is plain text or CQL.
    """
    global plain_text_treatment

    if query.strip().startswith("[") and query.strip().endswith("]"):
        cql_query = query.strip()  # Assume it's a valid CQL query
        print(f"Detected CQL query: {cql_query}")
    else:
        if plain_text_treatment == "word":
            cql_query = f'[word="{query.strip()}"]'
        elif plain_text_treatment == "lemma":
            cql_query = f'[lemma="{query.strip()}"]'
        else:
            print("Error: Invalid plain text treatment setting.")
            return 0
        print(f"Detected plain text query: {cql_query}")

    params = {
        "corpname": corpus,
        "queryselector": "cqlrow",
        "cql": cql_query,
        "default_attr": "word",
        "pagesize": 1,
        "format": "json",
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("concsize", 0)
    except requests.RequestException as e:
        print(f"Error querying API for '{query}': {e}")
        return 0

def save_progress(last_row):
    """Save the last processed row to a progress file."""
    with open(PROGRESS_FILE, "w") as file:
        json.dump({"last_row": last_row, "day": datetime.now().strftime("%Y-%m-%d")}, file)

def process_spreadsheet(start_row, end_row, columns_to_scan):
    """Process the spreadsheet within the specified range and update frequencies."""
    try:
        df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: File not found at {INPUT_FILE}")
        return

    for col in columns_to_scan:
        if col not in df.columns:
            print(f"Error: Column '{col}' not found in the input file.")
            return

    query_count_minute = query_count_hour = query_count_day = 0
    start_time = time.time()

    for index in range(start_row - 1, end_row):
        for col in columns_to_scan:
            query = df.at[index, col]
            if pd.isna(query) or not isinstance(query, str):
                print(f"Skipping invalid query in row {index + 1}, column {col}.")
                continue

            abs_freq = query_concordance(query)
            df.at[index, col] = abs_freq
            query_count_minute += 1
            query_count_hour += 1
            query_count_day += 1

            elapsed = time.time() - start_time
            if query_count_minute >= MAX_QUERIES_PER_MINUTE and elapsed < 60:
                print(f"Minute limit reached. Pausing for {60 - elapsed:.2f} seconds.")
                time.sleep(60 - elapsed)
                query_count_minute = 0
                start_time = time.time()

            if query_count_hour >= MAX_QUERIES_PER_HOUR:
                print("Hourly limit reached. Pausing for 1 hour.")
                time.sleep(3600)
                query_count_hour = 0

            if query_count_day >= MAX_QUERIES_PER_DAY:
                day_output = OUTPUT_BASE + f"{datetime.now().strftime('%Y%m%d')}.xlsx"
                df.to_excel(day_output, index=False)
                save_progress(index + 1)
                print(f"Daily limit reached. Results saved to {day_output}. Pausing for 24 hours.")
                time.sleep(86400)
                query_count_day = 0

        save_progress(index + 1)

    day_output = OUTPUT_BASE + f"{datetime.now().strftime('%Y%m%d')}.xlsx"
    df.to_excel(day_output, index=False)
    print(f"Processing complete. Results saved to {day_output}.")

def main():
    """Main function to execute the program."""
    global plain_text_treatment

    print("CORPUS QUERIER")
    print("1. Treat plain text as word queries")
    print("2. Treat plain text as lemma queries")
    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in {"1", "2"}:
            plain_text_treatment = "word" if choice == "1" else "lemma"
            break
        print("Invalid choice. Please enter 1 or 2.")

    resume_prompt = input("Do you want to resume from the last saved progress? (yes/no): ").strip().lower()
    if resume_prompt == "yes":
        try:
            with open(PROGRESS_FILE, "r") as file:
                progress = json.load(file)
                start_row = progress.get("last_row", 1)
                print(f"Resuming from row {start_row}.")
        except FileNotFoundError:
            print("No progress file found. Starting fresh.")
            start_row = None
    else:
        print("Starting fresh.")
        start_row = None

    while start_row is None:
        try:
            start_row = int(input("Enter the starting row (1-based index): ").strip())
            if start_row < 1:
                print("Starting row must be 1 or greater. Please try again.")
                start_row = None
        except ValueError:
            print("Invalid input. Please enter a numeric value for the starting row.")

    while True:
        try:
            end_row = int(input("Enter the ending row (1-based index): ").strip())
            if end_row < start_row:
                print("Ending row must be greater than or equal to the starting row. Please try again.")
            else:
                break
        except ValueError:
            print("Invalid input. Please enter a numeric value for the ending row.")

    columns_input = input(
        "Enter column names to scan, separated by commas (default: D,E,F,G,H,I,J): "
    ).strip()
    columns_to_scan = (
        [col.strip() for col in columns_input.split(",")]
        if columns_input
        else ["D", "E", "F", "G", "H", "I", "J"]
    )

    print(f"Columns to scan: {columns_to_scan}")
    process_spreadsheet(start_row, end_row, columns_to_scan)

if __name__ == "__main__":
    main()
