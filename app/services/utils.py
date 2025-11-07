import datetime
import decimal

def make_json_safe(obj):
        """Recursively convert Decimals and dates to JSON-serializable types."""
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        elif isinstance(obj, list):
            return [make_json_safe(x) for x in obj]
        elif isinstance(obj, dict):
            return {k: make_json_safe(v) for k, v in obj.items()}
        else:
            return obj