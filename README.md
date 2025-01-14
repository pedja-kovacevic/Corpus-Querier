# Corpus Querier

**Corpus Querier** is a Python script designed to automate corpus querying tasks using APIs like Sketch Engine. It ensures efficient and fair querying of large datasets while strictly adhering to rate limits and fair use principles. This tool is ideal for linguists, researchers, and data analysts working with corpus data.

---

## Features

- **Automated Querying**: Processes large datasets without manual intervention.
- **Rate Limit Compliance**: Pauses for minute, hourly, and daily query limits, ensuring fair use and compliance with API policies.
- **Resumable Execution**: Tracks progress in a JSON file, allowing the script to resume seamlessly after interruptions.
- **Query Flexibility**: Handles both Corpus Query Language (CQL) and plain text queries (word or lemma-based).
- **Daily Output**: Automatically saves results after reaching daily limits.

---

## Prerequisites

Before using Corpus Querier, ensure the following are installed:

1. **Python 3.7+**
2. Required Python libraries:
   ```bash
   pip install pandas requests openpyxl

Here’s the revised README.md and modifications to the code, ensuring it aligns strictly with fair use principles and removes references to "limitless" or VPN-based functionality. This version emphasizes adherence to rate limits and ethical practices.


# Corpus Querier

**Corpus Querier** is a Python script designed to automate corpus querying tasks using APIs like Sketch Engine. It ensures efficient and fair querying of large datasets while strictly adhering to rate limits and fair use principles. This tool is ideal for linguists, researchers, and data analysts working with corpus data.

---

## Features

- **Automated Querying**: Processes large datasets without manual intervention.
- **Rate Limit Compliance**: Pauses for minute, hourly, and daily query limits, ensuring fair use and compliance with API policies.
- **Resumable Execution**: Tracks progress in a JSON file, allowing the script to resume seamlessly after interruptions.
- **Query Flexibility**: Handles both Corpus Query Language (CQL) and plain text queries (word or lemma-based).
- **Daily Output**: Automatically saves results after reaching daily limits.

---

## Prerequisites

Before using Corpus Querier, ensure the following are installed:

1. **Python 3.7+**
2. Required Python libraries:
   ```bash
   pip install pandas requests openpyxl
Usage
1. Configure the Script
Update the following file paths and query limits in the script if necessary:

INPUT_FILE: Path to the Excel file containing queries.
OUTPUT_BASE: Directory for saving outputs.
MAX_QUERIES_PER_MINUTE, MAX_QUERIES_PER_HOUR, MAX_QUERIES_PER_DAY: Set API rate limits.
2. Run the Script
Run the script from the terminal:
python corpus_querier.py

3. Follow the Prompts
Choose whether to treat plain text queries as word or lemma queries.
Provide the start and end rows for processing.
Specify the columns to scan for queries (default: D, E, F, G, H, I, J).

4. Results
Results are saved in the output directory after processing each row.
When daily limits are reached, results are saved, and the script pauses for 24 hours before resuming.

Here’s the revised README.md and modifications to the code, ensuring it aligns strictly with fair use principles and removes references to "limitless" or VPN-based functionality. This version emphasizes adherence to rate limits and ethical practices.

Revised README.md

# Corpus Querier

**Corpus Querier** is a Python script designed to automate corpus querying tasks using APIs like Sketch Engine. It ensures efficient and fair querying of large datasets while strictly adhering to rate limits and fair use principles. This tool is ideal for linguists, researchers, and data analysts working with corpus data.

---

## Features

- **Automated Querying**: Processes large datasets without manual intervention.
- **Rate Limit Compliance**: Pauses for minute, hourly, and daily query limits, ensuring fair use and compliance with API policies.
- **Resumable Execution**: Tracks progress in a JSON file, allowing the script to resume seamlessly after interruptions.
- **Query Flexibility**: Handles both Corpus Query Language (CQL) and plain text queries (word or lemma-based).
- **Daily Output**: Automatically saves results after reaching daily limits.

---

## Prerequisites

Before using Corpus Querier, ensure the following are installed:

1. **Python 3.7+**
2. Required Python libraries:
   ```bash
   pip install pandas requests openpyxl
Usage
1. Configure the Script
Update the following file paths and query limits in the script if necessary:

INPUT_FILE: Path to the Excel file containing queries.
OUTPUT_BASE: Directory for saving outputs.
MAX_QUERIES_PER_MINUTE, MAX_QUERIES_PER_HOUR, MAX_QUERIES_PER_DAY: Set API rate limits.
2. Run the Script
Run the script from the terminal:

bash
python corpus_querier.py

3. Follow the Prompts
Choose whether to treat plain text queries as word or lemma queries.
Provide the start and end rows for processing.
Specify the columns to scan for queries (default: D, E, F, G, H, I, J).

4. Results
Results are saved in the output directory after processing each row.
When daily limits are reached, results are saved, and the script pauses for 24 hours before resuming.

Input File Format
The input file should be an Excel sheet where:

Each row represents a query set.
Columns specified in the prompt contain queries in either plain text or CQL.

Here’s the revised README.md and modifications to the code, ensuring it aligns strictly with fair use principles and removes references to "limitless" or VPN-based functionality. This version emphasizes adherence to rate limits and ethical practices.

Revised README.md

# Corpus Querier

**Corpus Querier** is a Python script designed to automate corpus querying tasks using APIs like Sketch Engine. It ensures efficient and fair querying of large datasets while strictly adhering to rate limits and fair use principles. This tool is ideal for linguists, researchers, and data analysts working with corpus data.

---

## Features

- **Automated Querying**: Processes large datasets without manual intervention.
- **Rate Limit Compliance**: Pauses for minute, hourly, and daily query limits, ensuring fair use and compliance with API policies.
- **Resumable Execution**: Tracks progress in a JSON file, allowing the script to resume seamlessly after interruptions.
- **Query Flexibility**: Handles both Corpus Query Language (CQL) and plain text queries (word or lemma-based).
- **Daily Output**: Automatically saves results after reaching daily limits.

---

## Prerequisites

Before using Corpus Querier, ensure the following are installed:

1. **Python 3.7+**
2. Required Python libraries:
   ```bash
   pip install pandas requests openpyxl
Usage
1. Configure the Script
Update the following file paths and query limits in the script if necessary:

INPUT_FILE: Path to the Excel file containing queries.
OUTPUT_BASE: Directory for saving outputs.
MAX_QUERIES_PER_MINUTE, MAX_QUERIES_PER_HOUR, MAX_QUERIES_PER_DAY: Set API rate limits.
2. Run the Script
Run the script from the terminal:

bash
python corpus_querier.py

3. Follow the Prompts
Choose whether to treat plain text queries as word or lemma queries.
Provide the start and end rows for processing.
Specify the columns to scan for queries (default: D, E, F, G, H, I, J).
4. Results
Results are saved in the output directory after processing each row.
When daily limits are reached, results are saved, and the script pauses for 24 hours before resuming.
Input File Format
The input file should be an Excel sheet where:

Each row represents a query set.
Columns specified in the prompt contain queries in either plain text or CQL.
Example:

D	E	F
example	[lemma="run"]	test
Output
The script generates an Excel file for each processing day:

Example output file: corpus_query_results_YYYYMMDD.xlsx.
Fair Use Commitment
Corpus Querier is designed to promote ethical usage of corpus APIs:

Rate Limits: Fully complies with API-imposed rate limits to prevent excessive server load.
Sustainability: Includes automated pausing mechanisms to align with fair use principles.
Transparency: Outputs progress and ensures all operations are consistent with service terms.

License
This project is licensed under the MIT License. Users are free to use the script for their own research purposes with proper attribution. Users must comply with the terms of service of any API or platform accessed using this script.

Cite as

Kovačević, P. (2025). Corpus Querier: A Python script for automated corpus querying with fair use compliance (Version 1.0) [Computer software]. GitHub. https://github.com/pedja-kovacevic/Corpus-Querier
