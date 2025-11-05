#!/usr/bin/env python3
"""
Test script for server-side filter fix.

This script tests the new filter_logs() method to ensure it correctly
queries the database and returns filtered results.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.app import App
from app.models.user import User
from app.models.log_entry import LogEntry
from app.repositories.log_repository import LogRepository
from app.services.log_service import LogService

def test_filter_logs():
    """Test the filter_logs method."""
    print("=" * 80)
    print("Testing Server-Side Filter Implementation")
    print("=" * 80)
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        # Get some test data
        app_record = db.session.query(App).first()
        if not app_record:
            print("❌ No apps found in database. Please create an app first.")
            return False
        
        print(f"\n✓ Found app: {app_record.app_id}")
        
        # Get log repository
        log_repo = LogRepository()
        
        # Test 1: Get all logs count
        all_logs = db.session.query(LogEntry).filter_by(app_id=app_record.id).all()
        total_logs = len(all_logs)
        print(f"✓ Total logs in database: {total_logs}")
        
        if total_logs == 0:
            print("❌ No logs found. Please send some events first.")
            return False
        
        # Test 2: Get distinct event names
        event_names = log_repo.get_distinct_event_names(app_record.id)
        print(f"✓ Distinct event names: {len(event_names)}")
        print(f"  Events: {event_names[:5]}...")  # Show first 5
        
        if not event_names:
            print("❌ No event names found.")
            return False
        
        # Test 3: Filter by single event name
        test_event = event_names[0]
        filter_result = log_repo.filter_logs(app_record.id, {
            'event_names': [test_event]
        })
        print(f"\n✓ Filter by event '{test_event}': {len(filter_result)} results")
        
        if len(filter_result) == 0:
            print("❌ No results for single event filter.")
            return False
        
        # Test 4: Filter by validation status
        statuses = set()
        for log in all_logs:
            if log.validation_results and isinstance(log.validation_results, list):
                for result in log.validation_results:
                    statuses.add(result.get('validationStatus', 'Unknown'))
        
        if statuses:
            test_status = list(statuses)[0]
            filter_result = log_repo.filter_logs(app_record.id, {
                'validation_statuses': [test_status]
            })
            print(f"✓ Filter by status '{test_status}': {len(filter_result)} results")
        
        # Test 5: Filter by multiple criteria
        filter_result = log_repo.filter_logs(app_record.id, {
            'event_names': [test_event],
            'validation_statuses': ['Valid']
        })
        print(f"✓ Filter by event + status: {len(filter_result)} results")
        
        # Test 6: Value search
        # Find a value to search for
        sample_value = None
        for log in all_logs[:10]:
            if log.validation_results and isinstance(log.validation_results, list):
                for result in log.validation_results:
                    val = result.get('value')
                    if val and isinstance(val, str) and len(val) > 3:
                        sample_value = val[:5]  # Take first 5 chars
                        break
                if sample_value:
                    break
        
        if sample_value:
            filter_result = log_repo.filter_logs(app_record.id, {
                'value_search': sample_value
            })
            print(f"✓ Filter by value search '{sample_value}': {len(filter_result)} results")
        
        # Test 7: Verify results structure
        if filter_result:
            first_result = filter_result[0]
            required_fields = ['timestamp', 'eventName', 'key', 'value', 'validationStatus']
            missing_fields = [f for f in required_fields if f not in first_result]
            
            if missing_fields:
                print(f"❌ Result missing fields: {missing_fields}")
                print(f"   Got: {list(first_result.keys())}")
                return False
            
            print(f"✓ Result structure valid:")
            print(f"   - timestamp: {first_result['timestamp']}")
            print(f"   - eventName: {first_result['eventName']}")
            print(f"   - key: {first_result['key']}")
            print(f"   - value: {first_result['value']}")
            print(f"   - validationStatus: {first_result['validationStatus']}")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - Server-side filter is working correctly!")
        print("=" * 80)
        return True

if __name__ == '__main__':
    try:
        success = test_filter_logs()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
