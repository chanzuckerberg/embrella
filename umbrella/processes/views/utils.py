"""
Utility functions used across process views.
"""


def msi_session_sort_key(name):
    """
    Custom sorting function for MSI session names in format 'yymmmdda'.
    Returns a tuple for sorting with newer sessions first.
    """
    try:
        # Extract components from the name
        year = int(name[:2])
        month = name[2:5].lower()  # Convert to lowercase for consistent comparison
        day = int(name[5:7])
        seq = name[7] if len(name) > 7 else 'a'  # Default to 'a' if no sequence letter

        # Convert month to number for proper sorting
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        }

        # Check if month is valid
        if month not in month_map:
            return (0, 0, 0, 'z')  # Move invalid months to the end

        month_num = month_map[month]

        # Validate year and day
        if not (0 <= year <= 99) or not (1 <= day <= 31):
            return (0, 0, 0, 'z')  # Move invalid dates to the end

        # Return tuple for sorting (negative year for descending order - newer first)
        return (-year, -month_num, -day, seq)
    except (ValueError, IndexError):
        # If name doesn't match expected format, put it at the end
        return (0, 0, 0, 'z')
