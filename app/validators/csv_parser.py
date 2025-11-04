"""CSV parser for validation rules."""
import csv
import json
from io import StringIO
from typing import List, Dict, Any


class CSVParser:
    """Parses CSV files containing validation rules.
    
    Single Responsibility: Only handles CSV parsing.
    """
    
    @staticmethod
    def parse_csv_content(csv_content: str) -> List[Dict[str, Any]]:
        """Parse CSV content into validation rules.
        
        Args:
            csv_content: String content of CSV file
            
        Returns:
            List of validation rule dictionaries
        """
        rules = []
        csv_reader = csv.DictReader(StringIO(csv_content))

        last_event_raw = ''
        for row in csv_reader:
            try:
                # Support merged rows where eventName may be empty for subsequent lines
                raw_event = (row.get('eventName') or '').strip()
                if raw_event:
                    last_event_raw = raw_event

                # Use the last seen event name when current row has it blank
                if not last_event_raw:
                    # No event context yet; skip this row
                    continue

                # Store event_name normalized for matching, but preserve original case for UI if needed
                event_name = last_event_raw.strip().lower()

                # Preserve field name casing as provided in CSV (e.g., eventId)
                field_name_raw = (row.get('eventPayload') or '').strip()
                data_type = (row.get('dataType') or '').strip().lower()

                required = (row.get('required') or '').lower() == 'true'

                # Parse condition as JSON if present
                condition_str = (row.get('condition') or '{}').strip()
                try:
                    condition = json.loads(condition_str) if condition_str else {}
                except json.JSONDecodeError:
                    condition = {}

                # Skip rows without field name
                if not field_name_raw:
                    continue

                rules.append({
                    'event_name': event_name,
                    # Keep original field name casing for display
                    'field_name': field_name_raw,
                    'data_type': data_type,
                    'is_required': required,
                    'condition': condition
                })
            except Exception as e:
                # Skip malformed rows
                print(f"Skipping malformed CSV row: {e}")
                continue

        return rules
    
    @staticmethod
    def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV file into validation rules.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of validation rule dictionaries
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return CSVParser.parse_csv_content(content)
    
    @staticmethod
    def group_rules_by_event(rules: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group validation rules by event name.
        
        Args:
            rules: List of validation rules
            
        Returns:
            Dictionary mapping event names to their validation rules
        """
        grouped = {}
        for rule in rules:
            event_name = rule['event_name']
            if event_name not in grouped:
                grouped[event_name] = []
            grouped[event_name].append(rule)
        return grouped
