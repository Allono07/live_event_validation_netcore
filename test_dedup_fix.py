#!/usr/bin/env python3
"""
Test script to verify deduplication is working correctly.

This script sends the same event multiple times and verifies that:
1. Only the latest event is stored
2. Older duplicates are deleted
3. Pagination counts are correct
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:5000"
APP_ID = "aj12"  # Replace with your actual app_id

# Test event payload (card_click1 with identical business logic)
TEST_EVENT_PAYLOAD = {
    "td": 0,
    "lat": None,
    "lng": None,
    "retry": 0,
    "eventId": 0,
    "payload": {
        "items": [
            {"price": 10.1, "prname": "Apples"},
            {"price": 5, "prname": "Bananas"}
        ],
        "card_name": 2,
        "card_name1": "alle",
        "payment_type": "alle"
    },
    "identity": "",
    "timeZone": "GMT+05:30",
    "eventName": "card_click1",
    "eventTime": str(int(time.time() * 1000)),  # Current timestamp in ms
    "sessionId": "1762186931007",
    "attrParams": {},
    "networkMode": "Unknown",
    "screenOrientation": "portrait"
}

def send_event(app_id: str, event_data: dict, trigger_number: int):
    """Send an event to the API."""
    # Update timestamp to be slightly different each time
    event_data["eventTime"] = str(int(time.time() * 1000))
    
    url = f"{API_BASE_URL}/api/log"
    payload = {
        "app_id": app_id,
        **event_data
    }
    
    print(f"\n[Trigger {trigger_number}] Sending event...")
    print(f"  EventTime: {event_data['eventTime']}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"  ✅ Event sent successfully (ID: {result.get('id', 'N/A')})")
        return True
    except Exception as e:
        print(f"  ❌ Error sending event: {e}")
        return False

def get_app_logs(app_id: str, page: int = 1, limit: int = 50):
    """Fetch paginated logs for the app."""
    url = f"{API_BASE_URL}/app/{app_id}/logs"
    params = {"page": page, "limit": limit}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return None

def count_event_occurrences(app_id: str, event_name: str) -> int:
    """Count how many times an event appears in the logs."""
    data = get_app_logs(app_id, page=1, limit=100)
    if not data or not data.get('logs'):
        return 0
    
    logs = data['logs']
    count = sum(1 for log in logs if log.get('event_name') == event_name)
    return count

def main():
    """Run the deduplication test."""
    print("=" * 80)
    print("DEDUPLICATION TEST - Order of Operations Fix")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  API Base URL: {API_BASE_URL}")
    print(f"  App ID: {APP_ID}")
    print(f"  Event Name: card_click1")
    print(f"  Test Strategy: Send same event 3 times, verify only latest is kept")
    
    # Test 1: Send event first time
    print("\n" + "-" * 80)
    print("TEST 1: First trigger (baseline)")
    print("-" * 80)
    send_event(APP_ID, TEST_EVENT_PAYLOAD.copy(), 1)
    time.sleep(1)
    
    count = count_event_occurrences(APP_ID, "card_click1")
    print(f"\nResult: {count} card_click1 event(s) in database")
    print(f"Expected: 1")
    print(f"Status: {'✅ PASS' if count == 1 else '❌ FAIL'}")
    
    # Test 2: Send same event second time
    print("\n" + "-" * 80)
    print("TEST 2: Second trigger (deduplication should delete first)")
    print("-" * 80)
    send_event(APP_ID, TEST_EVENT_PAYLOAD.copy(), 2)
    time.sleep(1)
    
    count = count_event_occurrences(APP_ID, "card_click1")
    print(f"\nResult: {count} card_click1 event(s) in database")
    print(f"Expected: 1 (first one should be deleted, only latest kept)")
    print(f"Status: {'✅ PASS' if count == 1 else '❌ FAIL - Deduplication not working!'}")
    
    # Test 3: Send same event third time
    print("\n" + "-" * 80)
    print("TEST 3: Third trigger (should still be only 1, not 2 or 3)")
    print("-" * 80)
    send_event(APP_ID, TEST_EVENT_PAYLOAD.copy(), 3)
    time.sleep(1)
    
    count = count_event_occurrences(APP_ID, "card_click1")
    print(f"\nResult: {count} card_click1 event(s) in database")
    print(f"Expected: 1 (only the latest event should be stored)")
    print(f"Status: {'✅ PASS' if count == 1 else '❌ FAIL - Multiple duplicates in DB!'}")
    
    # Final verification
    print("\n" + "=" * 80)
    print("FINAL VERIFICATION")
    print("=" * 80)
    
    logs_data = get_app_logs(APP_ID, page=1, limit=10)
    if logs_data:
        print(f"\nTotal events in database: {logs_data.get('total', 'N/A')}")
        print(f"\nLatest card_click1 events:")
        
        card_events = [log for log in logs_data.get('logs', []) if log.get('event_name') == 'card_click1']
        if card_events:
            for i, event in enumerate(card_events[:3], 1):  # Show first 3
                print(f"  {i}. ID: {event.get('id')}, Created: {event.get('created_at')}")
            
            if len(card_events) == 1:
                print("\n✅ SUCCESS! Only 1 card_click1 event stored (latest one)")
                print("   Deduplication is working correctly!")
            else:
                print(f"\n❌ FAILURE! Found {len(card_events)} card_click1 events")
                print("   Expected only 1 (the latest)")
        else:
            print("❌ No card_click1 events found in logs")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
