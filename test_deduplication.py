#!/usr/bin/env python3
"""
Test script for event deduplication.

This script sends the same event multiple times to the API endpoint
and verifies that only the latest event is stored in the database.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
APP_ID = "my-app-123"  # Change to your app ID
API_ENDPOINT = f"{BASE_URL}/api/logs/{APP_ID}"

# Test event (same payload, sent multiple times)
TEST_EVENT = {
    "eventName": "user_login",
    "user_id": 12345,
    "timestamp": datetime.now().isoformat(),
    "device_type": "mobile"
}

def send_event(event_data, label=""):
    """Send a single event to the API."""
    try:
        print(f"\n[{label}] Sending event...")
        response = requests.post(
            API_ENDPOINT,
            json=event_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"[{label}] Status: {response.status_code}")
        print(f"[{label}] Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"[{label}] ERROR: {e}")
        return False

def fetch_logs():
    """Fetch all logs for the app from the dashboard API."""
    try:
        response = requests.get(
            f"{BASE_URL}/app/{APP_ID}/logs?limit=100&page=1",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('logs', [])
        else:
            print(f"Error fetching logs: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return []

def main():
    print("=" * 60)
    print("EVENT DEDUPLICATION TEST")
    print("=" * 60)
    
    # Step 1: Send the same event 3 times (with slight delay)
    print("\n[STEP 1] Sending the SAME event 3 times...")
    for i in range(1, 4):
        send_event(TEST_EVENT, f"Event {i}")
        time.sleep(0.5)  # Small delay between sends
    
    # Step 2: Wait a moment for processing
    print("\n[STEP 2] Waiting for processing...")
    time.sleep(2)
    
    # Step 3: Fetch logs and check
    print("\n[STEP 3] Fetching logs from database...")
    logs = fetch_logs()
    
    print(f"\n[STEP 3] Total logs fetched: {len(logs)}")
    
    # Count how many of our test events are in the database
    user_login_count = sum(1 for log in logs if log.get('event_name') == 'user_login')
    print(f"[STEP 3] 'user_login' events in database: {user_login_count}")
    
    # Check for deduplication success
    if user_login_count == 1:
        print("\n✅ SUCCESS: Deduplication worked! Only 1 event stored despite sending 3.")
    elif user_login_count == 3:
        print("\n❌ FAILURE: All 3 events stored. Deduplication did NOT work.")
    else:
        print(f"\n⚠️  UNEXPECTED: Found {user_login_count} events (expected 1 or 3).")
    
    # Display the stored event(s)
    print("\n[STEP 4] Stored event details:")
    for log in logs:
        if log.get('event_name') == 'user_login':
            print(f"  - ID: {log.get('id')}")
            print(f"    Event: {log.get('event_name')}")
            print(f"    Status: {log.get('validation_status')}")
            print(f"    Created: {log.get('created_at')}")
            print(f"    Payload: {json.dumps(log.get('payload'), indent=6)}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
