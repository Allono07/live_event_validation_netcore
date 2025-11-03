"""Event validator - ported from beta2.py validation logic."""
import re
import json
from typing import Dict, Any, List, Tuple, Optional


# Configuration for float validation
ACCEPT_INT_AS_FLOAT = False


class EventValidator:
    """Validates event payloads against defined rules.
    
    Single Responsibility: Only handles validation logic.
    """
    
    @staticmethod
    def get_value_type(value: Any) -> str:
        """Determine the actual type of a value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            # Try to determine if it's a date
            try:
                if re.match(r"\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$", value):
                    return "date"
            except:
                pass
            return "text"
        elif isinstance(value, (list, tuple)):
            return "array"
        elif isinstance(value, dict):
            return "object"
        return "unknown"
    
    @staticmethod
    def validate_text(value: Any) -> bool:
        """Validate text type."""
        return isinstance(value, str) and value.strip() != ""
    
    @staticmethod
    def validate_date(value: Any, event_name: str = None) -> bool:
        """Validate date type."""
        if event_name == "user_profile_push":
            date_pattern = r"\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD format
        else:
            date_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"  # YYYY-MM-DD HH:MM:SS
        return isinstance(value, str) and bool(re.fullmatch(date_pattern, value))
    
    @staticmethod
    def validate_integer(value: Any) -> bool:
        """Validate integer type."""
        return isinstance(value, int) and not isinstance(value, bool)
    
    @staticmethod
    def validate_float(value: Any) -> bool:
        """Validate float type."""
        if ACCEPT_INT_AS_FLOAT:
            return isinstance(value, (float, int)) and not isinstance(value, bool)
        else:
            return isinstance(value, float)
    
    @staticmethod
    def validate_boolean(value: Any) -> bool:
        """Validate boolean type."""
        return isinstance(value, bool)
    
    @staticmethod
    def validate_value(value: Any, expected_type: str, event_name: str = None) -> str:
        """Validate a value against expected type.
        
        Returns:
            - "Valid" if validation passes
            - "Null value" if value is null/empty
            - "Invalid/Wrong datatype/value" if validation fails
        """
        if value is None or value == "" or value == "":
            return "Null value"
        
        if expected_type == "text":
            is_valid = EventValidator.validate_text(value)
        elif expected_type == "date":
            is_valid = EventValidator.validate_date(value, event_name)
        elif expected_type == "integer":
            is_valid = EventValidator.validate_integer(value)
        elif expected_type == "float":
            is_valid = EventValidator.validate_float(value)
        elif expected_type == "boolean":
            is_valid = EventValidator.validate_boolean(value)
        else:
            return "Invalid/Wrong datatype/value"
        
        return "Valid" if is_valid else "Invalid/Wrong datatype/value"
    
    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalize key by converting to lowercase and replacing spaces with underscores."""
        return key.replace(" ", "_").lower() if key else None
    
    def validate_event(self, event_name: str, payload: Dict[str, Any], 
                      validation_rules: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """Validate an event payload against validation rules.
        
        Args:
            event_name: Name of the event
            payload: Event payload data
            validation_rules: List of validation rules for this event
            
        Returns:
            Tuple of (overall_status, detailed_results)
            - overall_status: 'valid', 'invalid', or 'error'
            - detailed_results: List of validation results for each field
        """
        results = []
        normalized_payload = {self.normalize_key(k): v for k, v in payload.items()}
        
        # Get expected field names
        expected_fields = set(self.normalize_key(rule['field_name']) for rule in validation_rules)
        actual_fields = set(normalized_payload.keys())
        
        # Check required fields and validate each rule
        for rule in validation_rules:
            field_name = rule['field_name']
            normalized_field = self.normalize_key(field_name)
            expected_type = rule['data_type']
            is_required = rule.get('is_required', False)
            
            value = normalized_payload.get(normalized_field)
            
            if normalized_field not in normalized_payload:
                if is_required:
                    results.append({
                        'eventName': event_name,
                        'key': field_name,
                        'value': None,
                        'expectedType': expected_type,
                        'receivedType': 'not present',
                        'validationStatus': 'Payload not present in the log'
                    })
            else:
                validation_status = self.validate_value(value, expected_type, event_name)
                results.append({
                    'eventName': event_name,
                    'key': field_name,
                    'value': value,
                    'expectedType': expected_type,
                    'receivedType': self.get_value_type(value),
                    'validationStatus': validation_status
                })
        
        # Check for extra fields
        extra_fields = actual_fields - expected_fields
        for extra_field in extra_fields:
            # Find original key (case-sensitive)
            original_key = next((k for k in payload.keys() if self.normalize_key(k) == extra_field), extra_field)
            value = payload[original_key]
            results.append({
                'eventName': event_name,
                'key': original_key,
                'value': value,
                'expectedType': 'EXTRA',
                'receivedType': self.get_value_type(value),
                'validationStatus': 'Extra key present in the log'
            })
        
        # Determine overall status
        has_errors = any(r['validationStatus'] not in ['Valid', 'Extra key present in the log'] for r in results)
        overall_status = 'invalid' if has_errors else 'valid'
        
        return overall_status, results
