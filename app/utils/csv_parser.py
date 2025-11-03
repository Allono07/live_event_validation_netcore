"""CSV parser for validation rules."""
import csv
from io import StringIO


def parse_validation_rules(csv_content):
    """Parse CSV content and return list of validation rules.
    
    Expected CSV format (event name appears only once, then empty for same event):
    eventName,eventPayload,dataType
    user_login,user_id,integer
    ,timestamp,date
    ,device_type,text
    
    Args:
        csv_content: String content of CSV file
        
    Returns:
        List of dictionaries with validation rule data
    """
    rules = []
    
    # Handle both file objects and strings
    if isinstance(csv_content, str):
        content = StringIO(csv_content)
    else:
        content = csv_content
        
    reader = csv.DictReader(content)
    
    current_event_name = None  # Track the current event name
    
    for row in reader:
        # Skip completely empty rows
        if not any(row.values()):
            continue
        
        # Get event name from row, or use previous event name if empty
        event_name = row.get('eventName', '').strip()
        if event_name:
            current_event_name = event_name
        elif current_event_name:
            event_name = current_event_name
        else:
            # Skip rows with no event name at the start
            continue
            
        rule = {
            'event_name': event_name,
            'field_name': row.get('eventPayload', '').strip(),
            'data_type': row.get('dataType', 'text').strip().lower(),
            'is_required': True,  # All fields are required by default
            'expected_pattern': None,
            'expected_value': None,
        }
        
        # Validate required fields
        if not rule['event_name'] or not rule['field_name']:
            continue
            
        # Validate data type
        valid_types = ['text', 'date', 'integer', 'float', 'boolean']
        if rule['data_type'] not in valid_types:
            rule['data_type'] = 'text'
            
        rules.append(rule)
        
    return rules


def validate_csv_format(csv_content):
    """Validate CSV format and return error messages if any.
    
    Args:
        csv_content: String content of CSV file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if isinstance(csv_content, str):
            content = StringIO(csv_content)
        else:
            content = csv_content
            
        reader = csv.DictReader(content)
        
        # Check required headers
        required_headers = ['eventName', 'eventPayload', 'dataType']
        if not all(header in reader.fieldnames for header in required_headers):
            missing = [h for h in required_headers if h not in reader.fieldnames]
            return False, f"Missing required headers: {', '.join(missing)}"
            
        # Try to read at least one row
        try:
            first_row = next(reader)
            if not first_row.get('eventName') or not first_row.get('eventPayload'):
                return False, "First row must have eventName and eventPayload"
        except StopIteration:
            return False, "CSV file is empty"
            
        return True, None
        
    except csv.Error as e:
        return False, f"CSV parsing error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
