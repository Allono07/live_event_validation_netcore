#!/usr/bin/env python3
"""
Test script for Option A deduplication (eventName + payload only).

Demonstrates that logout_event payloads with different identity values
are now deduplicated correctly.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
APP_ID = "aj12"  # Your app ID from logs
API_ENDPOINT = f"{BASE_URL}/api/logs/{APP_ID}"

# Test events based on your actual logs
# Both logout_event with same payload but different identity
LOGOUT_EVENT_1 = {
    "networkMode": "Unknown",
    "eventId": 0,
    "attrParams": {},
    "lng": None,
    "timeZone": "GMT+05:30",
    "sessionId": "1762184685475",
    "td": 0,
    "screenOrientation": "portrait",
    "payload": {
        "payment_type": "alle",
        "card_name1": "alle",
        "card_name": 2,
        "items": [
            {"prname": "Apples", "price": 10.1},
            {"prname": "Bananas", "price": 5}
        ]
    },
    "identity": "8129445706",  # ← Different identity
    "eventTime": "1762184984976",
    "eventName": "logout_event",
    "lat": None,
    "retry": 0
}

LOGOUT_EVENT_2 = {
    "networkMode": "Unknown",
    "eventId": 0,
    "attrParams": {},
    "lng": None,
    "timeZone": "GMT+05:30",
    "sessionId": "1762184685475",
    "td": 0,
    "screenOrientation": "portrait",
    "payload": {
        "payment_type": "alle",
        "card_name1": "alle",
        "card_name": 2,
        "items": [
            {"prname": "Apples", "price": 10.1},
            {"prname": "Bananas", "price": 5}
        ]
    },
    "identity": "",  # ← Different identity (empty)
    "eventTime": "1762184992456",
    "eventName": "logout_event",
    "lat": None,
    "retry": 0
}

NEW_EVENT_1 = {
    "networkMode": "Unknown",
    "eventId": 0,
    "attrParams": {},
    "lng": None,
    "timeZone": "GMT+05:30",
    "sessionId": "1762184685475",
    "td": 0,
    "screenOrientation": "portrait",
    "payload": {
        "payment_type": "alle",
        "card_name1": "alle",
        "card_name": 2,
        "items": [
            {"prname": "Apples", "price": 10.1},
            {"prname": "Bananas", "price": 5}
        ]
    },
    "identity": "8129445706",
    "eventTime": "1762184984978",
    "eventName": "new_event",
    "lat": None,
    "retry": 0
}

NEW_EVENT_2 = {
    "networkMode": "Unknown",
    "eventId": 0,
    "attrParams": {},
    "lng": None,
    "timeZone": "GMT+05:30",
    "sessionId": "1762184685475",
    "td": 0,
    "screenOrientation": "portrait",
    "payload": {
        "payment_type": "alle",
        "card_name1": "alle",
        "card_name": 2,
        "items": [
            {"prname": "Apples", "price": 10.1},
            {"prname": "Bananas", "price": 5}
        ]
    },
    "identity": "",
    "eventTime": "1762184992457",
    "eventName": "new_event",
    "lat": None,
    "retry": 0
}

def send_event(event_data, label=""):
    """Send a single event to the API."""
    try:
        print(f"\n[{label}] Sending {event_data.get('eventName')} event...")
        print(f"  Identity: '{event_data.get('identity')}'")
        response = requests.post(
            API_ENDPOINT,
            json=event_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"[{label}] Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"[{label}] ✓ Stored with ID: {result.get('id', 'N/A')}")
        else:
            print(f"[{label}] Error: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"[{label}] ERROR: {e}")
        return False

def fetch_logs_for_event(event_name):
    """Fetch and count logs for a specific event name."""
    try:
        response = requests.get(
            f"{BASE_URL}/app/{APP_ID}/logs?limit=100&page=1",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            matching = [log for log in logs if log.get('event_name') == event_name]
            return len(matching), matching
        else:
            return 0, []
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return 0, []

def main():
    print("=" * 70)
    print("OPTION A DEDUPLICATION TEST: eventName + payload only")
    print("=" * 70)
    
    print("\n[TEST CASE 1] logout_event with DIFFERENT identity values")
    print("-" * 70)
    print("Expected: Both should deduplicate (same eventName + payload)")
    print("Result: Only 1 'logout_event' stored\n")
    
    # Send logout event 1
    send_event(LOGOUT_EVENT_1, "Event 1")
    time.sleep(1)
    
    # Send logout event 2 (different identity, should be deduplicated)
    send_event(LOGOUT_EVENT_2, "Event 2")
    time.sleep(1)
    
    # Check how many logout_event entries exist
    count, logs = fetch_logs_for_event('logout_event')
    print(f"\n[RESULT] Total 'logout_event' entries: {count}")
    if count == 1:
        print("✅ SUCCESS: Both logged out deduplicated despite different identity!")
    else:
        print(f"❌ FAILURE: Found {count} entries (expected 1)")
    
    print("\n" + "=" * 70)
    print("[TEST CASE 2] new_event with DIFFERENT identity values")
    print("-" * 70)
    print("Expected: Both should deduplicate (same eventName + payload)")
    print("Result: Only 1 'new_event' stored\n")
    
    # Send new event 1
    send_event(NEW_EVENT_1, "Event 3")
    time.sleep(1)
    
    # Send new event 2 (different identity, should be deduplicated)
    send_event(NEW_EVENT_2, "Event 4")
    time.sleep(1)
    
    # Check how many new_event entries exist
    count, logs = fetch_logs_for_event('new_event')
    print(f"\n[RESULT] Total 'new_event' entries: {count}")
    if count == 1:
        print("✅ SUCCESS: Both new_event deduplicated despite different identity!")
    else:
        print(f"❌ FAILURE: Found {count} entries (expected 1)")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
With Option A deduplication (eventName + payload):
  ✓ Same event type + same business payload = DEDUPLICATED
  ✓ Different identity/user context = IGNORED
  ✓ Different eventTime/sessionId = IGNORED
  ✓ Only the LATEST version is stored
  
This means your app won't show duplicate logout_events just because
they were triggered by different users or at different times.
""")

if __name__ == '__main__':
    main()
