import csv
import re

INPUT_FILE = "mymovies.csv"
OUTPUT_FILE = "cleaned_mymovies.csv"

def clean_actor_field(actor_field: str) -> str:
    """
    Cleans actor field that may contain newline-separated entries
    like 'Name ... Character' and converts to comma-separated names.
    """
    if "\n" not in actor_field:
        # Already a comma-separated list → nothing to fix
        return actor_field.strip()

    # Split on newlines
    lines = actor_field.splitlines()

    cleaned_names = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove " ... role" if present
        name = re.sub(r"\s*\.\.\..*$", "", line).strip()

        cleaned_names.append(name)

    # Join as comma-space list
    return ", ".join(cleaned_names)


# --- Process CSV ---
with open(INPUT_FILE, newline='', encoding="latin-1") as f_in, \
     open(OUTPUT_FILE, "w", newline='', encoding="utf-8") as f_out:

    reader = csv.reader(f_in, delimiter=';', quotechar='"')
    writer = csv.writer(f_out, delimiter=';', quotechar='"')

    for row in reader:
        if len(row) < 5:
            writer.writerow(row)
            continue

        # Actors is column index 4 based on your example
        row[4] = clean_actor_field(row[4])

        writer.writerow(row)

print("Done! Cleaned file written to:", OUTPUT_FILE)
