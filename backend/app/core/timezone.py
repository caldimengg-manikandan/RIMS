from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Returns current time in Indian Standard Time (IST) as a naive datetime object for DB storage."""
    return datetime.now(IST).replace(tzinfo=None)
