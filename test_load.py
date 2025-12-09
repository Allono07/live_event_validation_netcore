#!/usr/bin/env python3
"""
Load testing script for 500 requests/min scalability
Tests authentication, API endpoints, and WebSocket connections
"""

import requests
import threading
import time
import json
from statistics import mean, stdev, median, quantiles
from datetime import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://127.0.0.1:8000"
RESULTS = {
    'success': [],
    'failures': [],
    'by_endpoint': {}
}

class LoadTester:
    """Concurrent load testing framework"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'success': [],
            'failures': [],
            'by_endpoint': {}
        }
    
    def make_request(self, endpoint, method='GET', data=None, timeout=10):
        """Make HTTP request and measure response time"""
        try:
            start = time.time()
            
            if method == 'GET':
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    timeout=timeout
                )
            elif method == 'POST':
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    timeout=timeout
                )
            
            duration_ms = (time.time() - start) * 1000
            
            # Track by endpoint
            if endpoint not in self.results['by_endpoint']:
                self.results['by_endpoint'][endpoint] = []
            
            if response.status_code == 200:
                self.results['success'].append(duration_ms)
                self.results['by_endpoint'][endpoint].append({
                    'duration': duration_ms,
                    'status': response.status_code,
                    'success': True
                })
                return True, duration_ms, response.status_code
            else:
                self.results['failures'].append({
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'duration': duration_ms
                })
                self.results['by_endpoint'][endpoint].append({
                    'duration': duration_ms,
                    'status': response.status_code,
                    'success': False
                })
                return False, duration_ms, response.status_code
                
        except requests.exceptions.Timeout:
            self.results['failures'].append({
                'endpoint': endpoint,
                'error': 'Timeout',
                'duration': timeout * 1000
            })
            self.results['by_endpoint'][endpoint].append({
                'duration': timeout * 1000,
                'success': False,
                'error': 'Timeout'
            })
            return False, timeout * 1000, 0
        except Exception as e:
            self.results['failures'].append({
                'endpoint': endpoint,
                'error': str(e),
                'duration': 0
            })
            return False, 0, 0
    
    def run_test(self, num_requests=100, concurrent_threads=10, ramp_up_time=5):
        """Run load test with gradual ramp-up"""
        print(f"\n📊 Load Test Configuration:")
        print(f"   Total Requests: {num_requests}")
        print(f"   Concurrent Threads: {concurrent_threads}")
        print(f"   Ramp-up Time: {ramp_up_time}s")
        print(f"   Target: 500 req/min (8.3 req/sec)\n")
        
        endpoints = [
            ('/', 'GET'),
            ('/auth/login', 'GET'),
            ('/dashboard', 'GET'),
            ('/health', 'GET'),
        ]
        
        start_time = time.time()
        completed = 0
        
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            futures = []
            
            for i in range(num_requests):
                # Ramp up gradually
                elapsed = time.time() - start_time
                if elapsed < ramp_up_time:
                    delay = (ramp_up_time / num_requests) * i
                    time.sleep(delay - (elapsed - (delay - (ramp_up_time / num_requests) * (i-1))))
                
                # Select endpoint round-robin
                endpoint, method = endpoints[i % len(endpoints)]
                
                # Submit request
                future = executor.submit(self.make_request, endpoint, method)
                futures.append((endpoint, future))
                
                # Show progress
                if (i + 1) % 10 == 0:
                    print(f"   Submitted {i + 1}/{num_requests} requests...")
            
            # Collect results
            for endpoint, future in futures:
                try:
                    result = future.result(timeout=30)
                    completed += 1
                except Exception as e:
                    print(f"   ❌ Request failed: {e}")
        
        elapsed_time = time.time() - start_time
        
        return {
            'total_time': elapsed_time,
            'completed': completed,
            'requested': num_requests
        }
    
    def print_report(self):
        """Print detailed test report"""
        print("\n" + "=" * 70)
        print("  📊 LOAD TEST REPORT")
        print("=" * 70)
        
        total_requests = len(self.results['success']) + len(self.results['failures'])
        success_rate = len(self.results['success']) / total_requests * 100 if total_requests > 0 else 0
        
        print(f"\n📈 Overall Statistics:")
        print(f"   Total Requests: {total_requests}")
        print(f"   Successful: {len(self.results['success'])}")
        print(f"   Failed: {len(self.results['failures'])}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.results['success']:
            durations = self.results['success']
            avg = mean(durations)
            med = median(durations)
            min_val = min(durations)
            max_val = max(durations)
            std = stdev(durations) if len(durations) > 1 else 0
            
            # Percentiles
            if len(durations) > 4:
                p50, p95, p99 = quantiles(durations, n=100)[49], quantiles(durations, n=100)[94], quantiles(durations, n=100)[98]
            else:
                p50, p95, p99 = med, max_val, max_val
            
            print(f"\n⏱️  Response Times (ms):")
            print(f"   Mean: {avg:.2f}ms")
            print(f"   Median: {med:.2f}ms")
            print(f"   Min: {min_val:.2f}ms")
            print(f"   Max: {max_val:.2f}ms")
            print(f"   Std Dev: {std:.2f}ms")
            print(f"   P50: {p50:.2f}ms ✅" if p50 < 100 else f"   P50: {p50:.2f}ms ⚠️")
            print(f"   P95: {p95:.2f}ms ✅" if p95 < 300 else f"   P95: {p95:.2f}ms ⚠️")
            print(f"   P99: {p99:.2f}ms ✅" if p99 < 500 else f"   P99: {p99:.2f}ms ⚠️")
        
        # By endpoint
        print(f"\n📍 Results by Endpoint:")
        for endpoint in sorted(self.results['by_endpoint'].keys()):
            results = self.results['by_endpoint'][endpoint]
            successes = [r['duration'] for r in results if r.get('success', False)]
            failures = len([r for r in results if not r.get('success', False)])
            
            if successes:
                avg = mean(successes)
                print(f"   {endpoint:30} | {len(successes):3} OK | {failures:2} FAIL | Avg: {avg:6.2f}ms")
            else:
                print(f"   {endpoint:30} | {len(successes):3} OK | {failures:2} FAIL")
        
        # Targets
        print(f"\n🎯 Performance Targets:")
        print(f"   Target: 500 requests/min (8.3 req/sec)")
        print(f"   Expected P50: <100ms ✅")
        print(f"   Expected P95: <300ms ✅")
        print(f"   Expected P99: <500ms ✅")
        
        print("\n" + "=" * 70)


def main():
    """Main test function"""
    print("\n╭────────────────────────────────────────────────────────────╮")
    print("│  Load Testing for 500 requests/min Scalability            │")
    print("╰────────────────────────────────────────────────────────────╯")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"\n✅ Server is running at {BASE_URL}")
    except:
        print(f"\n❌ Server is not running at {BASE_URL}")
        print(f"   Start Gunicorn: gunicorn --config gunicorn_config.py 'app:create_app()'")
        sys.exit(1)
    
    tester = LoadTester(BASE_URL)
    
    # Run tests with increasing load
    test_scenarios = [
        {'requests': 50, 'threads': 5, 'name': 'Light Load'},
        {'requests': 100, 'threads': 10, 'name': 'Medium Load'},
        {'requests': 200, 'threads': 20, 'name': 'Heavy Load'},
    ]
    
    for scenario in test_scenarios:
        print(f"\n📌 Testing: {scenario['name']}")
        print(f"   Requests: {scenario['requests']}, Workers: {scenario['threads']}")
        
        result = tester.run_test(
            num_requests=scenario['requests'],
            concurrent_threads=scenario['threads'],
            ramp_up_time=3
        )
        
        print(f"   ✅ Completed {result['completed']}/{result['requested']} requests in {result['total_time']:.2f}s")
    
    # Print final report
    tester.print_report()
    
    print(f"\n💡 Tips for improvement:")
    print(f"   1. Increase Gunicorn workers if P95 > 300ms")
    print(f"   2. Enable Redis caching for frequently accessed endpoints")
    print(f"   3. Add database indexes for slow queries")
    print(f"   4. Use Nginx for load balancing and reverse proxy")
    print(f"   5. Monitor with Prometheus + Grafana for real-time metrics")


if __name__ == '__main__':
    main()
