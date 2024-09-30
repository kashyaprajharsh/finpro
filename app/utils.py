import re
import calendar

def extract_year_month_from_metadata(metadata):
    years_months = []
    for entry in metadata:
        match = re.search(r'(\w{3})(\d{2})', entry["source"])
        if match:
            month_abbreviation = match.group(1)
            year_short = match.group(2)

            month_mapping = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }

            month_numeric = month_mapping.get(month_abbreviation.lower())

            if month_numeric:
                year = '20' + year_short
                years_months.append((year, month_numeric))

    return years_months

def extract_year_from_path(path):
    match = re.search(r'(\d{2,4})', path)
    if match:
        return match.group(1)
    else:
        print(f"No year found in path: {path}")
        return None