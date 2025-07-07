# Sketch Engine API Query Script

This Python script queries the Sketch Engine API to retrieve total hit counts for CQL (Corpus Query Language) queries stored in an Excel spreadsheet. The results replace the original queries in the spreadsheet with their corresponding frequency counts and save the output as a new Excel file.

---

## Features

- Reads queries from specified columns and rows in an Excel file.
- Sends queries to the Sketch Engine API while respecting their Fair Use Policy (FUP) limits.
- Automatically handles rate limiting with delays based on the number of requests per minute, hour, and day.
- Supports complex CQL queries.
- Outputs a new Excel file with frequencies replacing the original queries.
- Prints progress in the terminal during execution.

---

## How It Works

### Constants and Configuration

- `API_KEY`: Your Sketch Engine API key.
- `API_URL`: Sketch Engine endpoint (`view` method).
- `CORPUS`: Name of the corpus to query (e.g., `"preloaded/srwac12"`).
- `INPUT_FILE` and `OUTPUT_FILE`: Paths to the input and output Excel files.
- `MAX_REQUESTS_PER_MINUTE`, `MAX_REQUESTS_PER_HOUR`, `MAX_REQUESTS_PER_DAY`: Limits based on Sketch Engine Fair Use Policy.

### Rate Limiting (`fup_delay` function)

- Tracks the number of requests made per minute, hour, and day.
- Resets counters after time intervals (60 seconds, 3600 seconds, 86400 seconds).
- If request thresholds are exceeded, the function imposes delays:
  - Between 100 and 900 requests per hour: 4-second delay between requests.
  - Above 900 requests per hour: 45-second delay.
  - Above 2000 requests per day: stops execution with an error.
- This avoids 429 "Too Many Requests" errors.

### Querying Sketch Engine (`get_hits_for_query` function)

- Takes a CQL query string as input.
- Wraps it in the format Sketch Engine expects (`q[query]`) and requests a random sample (`"r1"`) to get the total hit count.
- Sends a GET request to the API endpoint with proper parameters.
- If rate limit error 429 is returned, waits 60 seconds and retries.
- Parses the JSON response to extract the total number of hits (`size` field in `Desc`).
- Returns the total hit count or `None` if the API call fails.

### Main Script Logic (`main` function)

- Loads the input Excel file into a pandas DataFrame.
- Prompts the user to specify:
  - Columns to scan for queries (e.g., `A,B,C`).
  - Start and end row numbers (1-based index).
- Validates the column names and row ranges.
- Calculates the total number of queries to process.
- Iterates over the specified rows and columns:
  - Skips empty or invalid cells.
  - Calls `get_hits_for_query` for each query.
  - Replaces the query string in the DataFrame with the corresponding hit count.
  - Prints progress updates showing how many queries have been processed.
- Saves the updated DataFrame to the output Excel file.
- Handles exceptions during file loading and saving, printing relevant error messages.

---

## Usage

1. Set your API key, input/output file paths, and corpus name in the script.
2. Run the script.
3. Follow prompts to enter:
   - Columns to scan (e.g., `A,B,C`)
   - Start and end rows to process.
4. The script will process the queries and save the results in the specified output file.

---

## Example Terminal Output
Enter column names to scan, separated by commas (e.g. A,B,C): A,B
Enter starting row number (1-based index): 1
Enter ending row number (1-based index): 100
Processed 1 out of 50 queries.
Processed 2 out of 50 queries.
...
Processed 50 out of 50 queries.
Results saved to "location you provided"


---

## Notes

- This script respects Sketch Engine's Fair Use Policy by implementing rate limiting and automatic retry on hitting limits.
- Input queries can be simple or complex CQL expressions.
- The script replaces queries in place with their counts, so keep a backup of your original data.
- Error handling provides user feedback but can be extended for robustness.

---



