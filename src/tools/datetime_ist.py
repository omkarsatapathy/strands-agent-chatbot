"""Tool to get current date and time in IST."""
from datetime import datetime
import pytz
from strands import tool

@tool
def get_current_datetime_ist() -> str:
    """
    Strands tool: Get the current date and time in IST (Indian Standard Time).

    Returns:
        String with the current date and time in IST timezone formatted as 'YYYY-MM-DD HH:MM:SS IST'
    """
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist)
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S IST')
    print(f'\n\n fetched date and time as {formatted_time}')
    return formatted_time
