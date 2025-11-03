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
        
        for row in csv_reader:
            try:
                # Normalize field names
                event_name = row.get('eventName', '').strip().lower()
                field_name = row.get('eventPayload', '').strip().lower()
                data_type = row.get('dataType', '').strip().lower()
                required = row.get('required', '').lower() == 'true'
                
                # Parse condition as JSON if present
                condition_str = row.get('condition', '{}').strip()
                try:
                    condition = json.loads(condition_str) if condition_str else {}
                except json.JSONDecodeError:
                    condition = {}
                
                # Skip rows without event name or field name
                if not event_name or not field_name:
                    continue
                
                rules.append({
                    'event_name': event_name,
                    'field_name': field_name,
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
