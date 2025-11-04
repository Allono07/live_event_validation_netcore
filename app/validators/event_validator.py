"""Event validator - ported from beta2.py validation logic."""
import re
import json
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict


# Configuration for float validation
ACCEPT_INT_AS_FLOAT = False


class EventValidator:
    """Validates event payloads against defined rules.
    
    Single Responsibility: Only handles validation logic.
    Includes comprehensive validation from beta2.py:
    - Type validation (text, date, integer, float, boolean)
    - Required field checking
    - Extra field detection
    - Array/object validation
    - Conditional validation
    - Null/empty value handling
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
    def validate_value(value: Any, expected_type: str, event_name: str = None) -> Any:
        """Validate a value against expected type.
        
        Returns:
            - True if validation passes
            - "Null value" if value is null/empty
            - False if validation fails
            - Special message for int-as-float case
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
            result = EventValidator.validate_float(value)
            # Add special handling for int values that might have been floats
            if result and isinstance(value, int) and ACCEPT_INT_AS_FLOAT:
                return "Valid (JSON serialization converted float to integer)"
            return result
        elif expected_type == "boolean":
            is_valid = EventValidator.validate_boolean(value)
        else:
            return False
        
        return is_valid
    
    @staticmethod
    def get_formatted_value(value: Any, expected_type: str) -> Any:
        """Format value based on its expected type."""
        if expected_type == "float" and isinstance(value, float):
            # Convert to string maintaining decimal places
            str_val = str(value)
            if '.' not in str_val:
                str_val += '.00'
            elif len(str_val.split('.')[1]) == 1:
                str_val += '0'
            return str_val
        return value
    
    @staticmethod
    def normalize_key(key: str) -> str:
        """Normalize key by converting to lowercase and replacing spaces with underscores."""
        return key.replace(" ", "_").lower() if key else None
    
    @staticmethod
    def get_array_field_name(key: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract array field and subfield from pattern like 'items[].field_name'."""
        match = re.match(r"(.+)\[\]\.(.+)", key)
        if match:
            return match.group(1), match.group(2)
        return None, None

    @staticmethod
    def _find_key_case_insensitive(d: Dict[str, Any], target: str) -> Optional[str]:
        """Find the actual key in dict `d` that matches `target` case-insensitively.

        Returns the original key name if found, otherwise None.
        """
        if not isinstance(d, dict):
            return None
        target_n = EventValidator.normalize_key(target)
        for k in d.keys():
            if EventValidator.normalize_key(k) == target_n:
                return k
        return None

    @staticmethod
    def get_value_by_path(payload: Dict[str, Any], field_name: str) -> Any:
        """Resolve nested field names like 'payload.card_name' or 'items[].id'.

        Returns the value if present, otherwise None.
        """
        if not field_name:
            return None

        # Support dot notation and array brackets
        parts = field_name.split('.')
        current = payload
        for part in parts:
            if current is None:
                return None

            # array pattern like items[]
            if part.endswith('[]'):
                arr_key = part[:-2]
                real_key = EventValidator._find_key_case_insensitive(current, arr_key)
                if real_key is None:
                    return None
                arr = current.get(real_key)
                if not isinstance(arr, list):
                    return None
                # return the array itself; caller may decide how to validate
                return arr

            # normal key: case-insensitive lookup
            real_key = EventValidator._find_key_case_insensitive(current, part)
            if real_key is None:
                return None

            current = current.get(real_key)

        return current
    
    @staticmethod
    def validate_conditional_fields(payload: Dict, validation: Dict) -> Tuple[bool, str]:
        """Validate fields based on conditional rules."""
        if 'condition' not in validation or not validation['condition']:
            return True, ""
        
        condition = validation['condition']
        if_field = condition.get('if_field')
        if_value = condition.get('if_value')
        then_field = condition.get('then_field')
        then_type = condition.get('then_type')
        
        if if_field in payload and payload[if_field] == if_value:
            if then_field not in payload:
                return False, f"Required field '{then_field}' is missing when '{if_field}' is '{if_value}'"
            if not EventValidator.validate_value(payload[then_field], then_type):
                return False, f"Field '{then_field}' has invalid type when '{if_field}' is '{if_value}'"
        
        return True, ""
    
    @staticmethod
    def validate_required_fields(payload: Dict, validations: List[Dict], event_name: str) -> List[Dict]:
        """Check for required fields and add validation results."""
        results = []
        required_fields = [EventValidator.normalize_key(v['field_name']) 
                          for v in validations if v.get('is_required', False)]
        
        normalized_payload = {EventValidator.normalize_key(k): k for k in payload.keys()}
        
        for validation in validations:
            if not validation.get('is_required', False):
                continue
                
            field_name = validation['field_name']
            normalized_field = EventValidator.normalize_key(field_name)
            
            if normalized_field not in normalized_payload:
                results.append({
                    'eventName': event_name,
                    'key': field_name,
                    'value': None,
                    'expectedType': validation['data_type'],
                    'receivedType': 'not present',
                    'validationStatus': 'Payload not present in the log',
                    'comment': 'Required field is missing in the payload'
                })
        
        return results
    
    def validate_event(self, event_name: str, payload: Dict[str, Any], 
                      validation_rules: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """Validate an event payload against validation rules.
        
        Comprehensive validation including:
        - Required field validation
        - Type validation for each field
        - Extra field detection
        - Null/empty value handling
        - Conditional validation
        - Array/object validation
        
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

        # We only validate the inner 'payload' object (per user request).
        # If the incoming payload contains a key 'payload' that is a dict, use that; otherwise
        # use an empty dict so fields are reported as missing.
        inner_payload = {}
        if isinstance(payload, dict) and 'payload' in payload and isinstance(payload.get('payload'), dict):
            inner_payload = payload.get('payload')

        # Preprocess validation rules: strip leading 'payload.' if present so rules can refer
        # to nested keys either as 'payload.card_name' or just 'card_name'.
        processed_rules = []
        for vr in validation_rules:
            fn = vr.get('field_name') or ''
            if isinstance(fn, str) and fn.startswith('payload.'):
                fn = fn[len('payload.'):]  # remove leading prefix
            # keep other keys unchanged
            new_vr = dict(vr)
            new_vr['field_name'] = fn
            processed_rules.append(new_vr)

        # Check required fields first against inner_payload
        required_results = self.validate_required_fields(inner_payload, processed_rules, event_name)
        results.extend(required_results)

        # Check conditional validations against inner_payload
        for validation in processed_rules:
            is_valid, error_msg = self.validate_conditional_fields(inner_payload, validation)
            if not is_valid:
                results.append({
                    'eventName': event_name,
                    'key': validation['field_name'],
                    'value': None,
                    'expectedType': validation['data_type'],
                    'receivedType': 'invalid',
                    'validationStatus': error_msg,
                    'comment': error_msg
                })

        # Normalize inner_payload for case-insensitive comparison
        normalized_payload = {self.normalize_key(k): v for k, v in inner_payload.items()}

        # Get expected field names (normalized) from processed rules
        expected_fields = set(self.normalize_key(rule['field_name']) for rule in processed_rules)
        # Also detect any array root keys expected (rules like 'items[].price' imply 'items' is expected)
        expected_array_roots = set()
        for rule in processed_rules:
            arr, sub = self.get_array_field_name(rule['field_name'] or '')
            if arr:
                expected_array_roots.add(self.normalize_key(arr))

        actual_fields = set(normalized_payload.keys())

        # Check for extra fields inside inner_payload (not in validation rules)
        # Exclude array root keys if there are array rules for them
        extra_fields = set()
        for f in actual_fields:
            if f in expected_fields:
                continue
            if f in expected_array_roots:
                continue
            extra_fields.add(f)
        for extra_field in extra_fields:
            # Find original key (case-sensitive)
            original_key = next((k for k in inner_payload.keys() if self.normalize_key(k) == extra_field), extra_field)
            value = inner_payload[original_key]
            results.append({
                'eventName': event_name,
                'key': original_key,
                'value': value,
                'expectedType': 'EXTRA',
                'receivedType': self.get_value_type(value),
                'validationStatus': 'Extra key present in the log',
                'comment': 'This is an EXTRA payload or there is a spelling mistake with the required payload'
            })
        
        # Validate each processed rule (against inner_payload only)
        for validation in processed_rules:
            field_name = validation['field_name']
            normalized_field = self.normalize_key(field_name)
            expected_type = validation['data_type']
            
            if not field_name or not expected_type:
                results.append({
                    'eventName': event_name,
                    'key': field_name,
                    'value': None,
                    'expectedType': expected_type,
                    'receivedType': 'unknown',
                    'validationStatus': 'Invalid CSV row',
                    'comment': 'Invalid validation rule configuration'
                })
                continue
            
            # Handle array-of-objects pattern like 'items[].price'
            arr_name, sub_field = self.get_array_field_name(field_name)
            if arr_name and sub_field:
                # Find actual key in payload (case-insensitive)
                real_arr_key = self._find_key_case_insensitive(inner_payload, arr_name)
                if real_arr_key is None:
                    # Array not present
                    results.append({
                        'eventName': event_name,
                        'key': field_name,
                        'value': None,
                        'expectedType': expected_type,
                        'receivedType': 'not present',
                        'validationStatus': 'Payload not present in the log',
                        'comment': f"Array '{arr_name}' is missing in payload"
                    })
                    continue

                arr_val = inner_payload.get(real_arr_key)
                if not isinstance(arr_val, list):
                    results.append({
                        'eventName': event_name,
                        'key': real_arr_key,
                        'value': arr_val,
                        'expectedType': 'array',
                        'receivedType': self.get_value_type(arr_val),
                        'validationStatus': 'Invalid/Wrong datatype/value',
                        'comment': f"Expected array for '{real_arr_key}'"
                    })
                    continue

                # If array is empty, report accordingly
                if len(arr_val) == 0:
                    results.append({
                        'eventName': event_name,
                        'key': real_arr_key,
                        'value': arr_val,
                        'expectedType': 'array',
                        'receivedType': 'array',
                        'validationStatus': 'Payload value is Empty',
                        'comment': 'Array is empty'
                    })
                    continue

                # Validate each object element's sub_field
                for idx, elem in enumerate(arr_val):
                    if not isinstance(elem, dict):
                        results.append({
                            'eventName': event_name,
                            'key': f"{real_arr_key}[{idx}]",
                            'value': elem,
                            'expectedType': 'object',
                            'receivedType': self.get_value_type(elem),
                            'validationStatus': 'Invalid/Wrong datatype/value',
                            'comment': 'Array element is not an object'
                        })
                        continue

                    real_sub_key = self._find_key_case_insensitive(elem, sub_field)
                    if real_sub_key is None:
                        results.append({
                            'eventName': event_name,
                            'key': f"{real_arr_key}[{idx}].{sub_field}",
                            'value': None,
                            'expectedType': expected_type,
                            'receivedType': 'not present',
                            'validationStatus': 'Payload not present in the log',
                            'comment': f"Field '{sub_field}' missing in array element {idx}"
                        })
                        continue

                    val = elem.get(real_sub_key)
                    validation_result = self.validate_value(val, expected_type, event_name)
                    if validation_result == "Null value":
                        status = 'Payload value is Empty'
                        comment = 'Field value is empty or null'
                    elif validation_result is True or (isinstance(validation_result, str) and "Valid" in validation_result):
                        status = 'Valid'
                        comment = 'Field validation passed'
                    else:
                        status = 'Invalid/Wrong datatype/value'
                        comment = f"Expected type: {expected_type}, Received type: {self.get_value_type(val)}"

                    formatted_value = self.get_formatted_value(val, expected_type)
                    results.append({
                        'eventName': event_name,
                        'key': f"{real_arr_key}[{idx}].{real_sub_key}",
                        'value': formatted_value,
                        'expectedType': expected_type,
                        'receivedType': self.get_value_type(val),
                        'validationStatus': status,
                        'comment': comment
                    })
                # finished array handling for this rule
                continue

            # Resolve value from inner_payload: try top-level inner keys first, then nested path
            value = normalized_payload.get(normalized_field)
            if value is None:
                nested_val = self.get_value_by_path(inner_payload, field_name)
                if nested_val is not None:
                    value = nested_val

            # If still not found, report as missing (unless required already reported)
            if value is None:
                # Only add if not already reported as required field missing
                already_reported = any(
                    r['key'] == field_name and r['validationStatus'] == 'Payload not present in the log'
                    for r in results
                )
                if not already_reported and not validation.get('is_required', False):
                    results.append({
                        'eventName': event_name,
                        'key': field_name,
                        'value': None,
                        'expectedType': expected_type,
                        'receivedType': 'not present',
                        'validationStatus': 'Payload not present in the log',
                        'comment': 'Field is missing in the payload'
                    })
                continue
            
            # Validate the value
            validation_result = self.validate_value(value, expected_type, event_name)
            
            # Determine status
            if validation_result == "Null value":
                status = 'Payload value is Empty'
                comment = 'Field value is empty or null'
            elif validation_result is True or isinstance(validation_result, str) and "Valid" in validation_result:
                status = 'Valid'
                comment = 'Field validation passed'
            else:
                status = 'Invalid/Wrong datatype/value'
                comment = f"Expected type: {expected_type}, Received type: {self.get_value_type(value)}"
            
            # Format value for display
            formatted_value = self.get_formatted_value(value, expected_type)
            
            results.append({
                'eventName': event_name,
                'key': field_name,
                'value': formatted_value,
                'expectedType': expected_type,
                'receivedType': self.get_value_type(value),
                'validationStatus': status,
                'comment': comment
            })
        
        # Determine overall status
        has_errors = any(
            r['validationStatus'] not in ['Valid', 'Extra key present in the log'] 
            for r in results
        )
        overall_status = 'invalid' if has_errors else 'valid'
        
        return overall_status, results

    def validate_unknown_event(self, event_name: str, payload: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """Fallback validation for events that have no rules defined.

        Behavior: validate only inner 'payload' object keys using simple heuristics:
        - expectedType is inferred from the value
        - non-null/non-empty values marked as 'Valid (no rule)'
        - null/empty values marked as 'Payload value is Empty'
        This mirrors a permissive fallback so unknown events still produce per-field results.
        """
        results = []
        inner_payload = {}
        if isinstance(payload, dict) and 'payload' in payload and isinstance(payload.get('payload'), dict):
            inner_payload = payload.get('payload')

        # Mark this entire event as an EXTRA event (not present in the validation sheet).
        # For UI clarity, mark only the first reported field with the explicit 'Extra event' label
        # and show remaining fields as payload from the extra event.
        first = True
        for k, v in inner_payload.items():
            value_type = self.get_value_type(v)
            if v is None or (isinstance(v, str) and v.strip() == ""):
                status = 'Payload value is Empty'
                comment = 'Field value is empty or null (extra event)'
            else:
                if first:
                    status = 'Extra event (not in sheet)'
                    comment = 'Event not present in validation sheet; showing payload from extra event'
                else:
                    status = 'Payload from extra event'
                    comment = 'Showing payload value from extra event'

            results.append({
                'eventName': event_name,
                'key': k,
                'value': v,
                'expectedType': 'EXTRA',
                'receivedType': value_type,
                'validationStatus': status,
                'comment': comment
            })
            first = False

        # Determine overall status: invalid if any empty values exist
        has_errors = any(r['validationStatus'] == 'Payload value is Empty' for r in results)
        overall_status = 'invalid' if has_errors else 'valid'
        return overall_status, results
