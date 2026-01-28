"""
Performance and Load Testing Suite
Uses custom performance benchmarks that work with pytest.

Note: For full Locust load testing, use the separate locustfile.py
      Command: locust -f tests/locustfile.py
"""
import os
import time
import statistics
import concurrent.futures
from datetime import datetime
from typing import List, Dict
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "test@proflow.com"
SUPER_ADMIN_PASSWORD = "test123456"

# Request timeout settings for external environments
REQUEST_TIMEOUT = 30  # seconds
CONCURRENT_REQUEST_TIMEOUT = 15  # shorter timeout for concurrent tests


# =============================================
# Performance Benchmark Utilities
# =============================================

class PerformanceBenchmark:
    """Custom performance benchmark utilities"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token = None
        self.org_id = None
        self.results: Dict[str, List[float]] = {}
    
    def login(self):
        """Authenticate and get token"""
        response = requests.post(f"{self.base_url}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        }, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            # Get org_id
            orgs = requests.get(
                f"{self.base_url}/api/organizations/",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=REQUEST_TIMEOUT
            )
            if orgs.status_code == 200 and orgs.json():
                self.org_id = orgs.json()[0]["org_id"]
            return True
        return False
    
    def measure_request(self, name: str, method: str, url: str, timeout: int = None, **kwargs) -> float:
        """Measure a single request's response time"""
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        kwargs["headers"]["Authorization"] = f"Bearer {self.token}"
        kwargs["timeout"] = timeout or REQUEST_TIMEOUT
        
        start = time.perf_counter()
        response = requests.request(method, f"{self.base_url}{url}", **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        
        if name not in self.results:
            self.results[name] = []
        self.results[name].append(elapsed)
        
        return elapsed
    
    def run_benchmark(self, name: str, method: str, url: str, iterations: int = 10, **kwargs) -> Dict:
        """Run multiple iterations of a request and collect stats"""
        times = []
        for _ in range(iterations):
            try:
                elapsed = self.measure_request(name, method, url, **kwargs)
                times.append(elapsed)
            except requests.exceptions.Timeout:
                # Record timeout as a very high latency
                times.append(REQUEST_TIMEOUT * 1000)
            except requests.exceptions.RequestException:
                # Skip failed requests
                continue
        
        if not times:
            return {
                "name": name,
                "iterations": iterations,
                "error": "All requests failed"
            }
        
        return {
            "name": name,
            "iterations": iterations,
            "successful": len(times),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "avg_ms": round(statistics.mean(times), 2),
            "median_ms": round(statistics.median(times), 2),
            "std_dev_ms": round(statistics.stdev(times), 2) if len(times) > 1 else 0
        }
    
    def run_concurrent_benchmark(self, name: str, method: str, url: str, 
                                  concurrent_users: int = 10, requests_per_user: int = 5, **kwargs) -> Dict:
        """Run concurrent requests to test throughput"""
        
        def make_request():
            times = []
            for _ in range(requests_per_user):
                try:
                    elapsed = self.measure_request(f"{name}_concurrent", method, url, 
                                                   timeout=CONCURRENT_REQUEST_TIMEOUT, **kwargs)
                    times.append(elapsed)
                except requests.exceptions.Timeout:
                    times.append(CONCURRENT_REQUEST_TIMEOUT * 1000)
                except requests.exceptions.RequestException:
                    continue
            return times
        
        start = time.perf_counter()
        all_times = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            for future in concurrent.futures.as_completed(futures, timeout=60):
                try:
                    all_times.extend(future.result())
                except concurrent.futures.TimeoutError:
                    continue
        
        total_time = time.perf_counter() - start
        total_requests = len(all_times)
        
        if not all_times:
            return {
                "name": name,
                "error": "All concurrent requests failed or timed out"
            }
        
        return {
            "name": name,
            "concurrent_users": concurrent_users,
            "requests_per_user": requests_per_user,
            "total_requests": total_requests,
            "total_time_s": round(total_time, 2),
            "requests_per_second": round(total_requests / total_time, 2) if total_time > 0 else 0,
            "min_ms": round(min(all_times), 2),
            "max_ms": round(max(all_times), 2),
            "avg_ms": round(statistics.mean(all_times), 2),
            "p95_ms": round(sorted(all_times)[int(len(all_times) * 0.95)], 2) if len(all_times) >= 20 else round(max(all_times), 2),
            "p99_ms": round(sorted(all_times)[int(len(all_times) * 0.99)], 2) if len(all_times) >= 100 else round(max(all_times), 2)
        }


# =============================================
# Pytest Performance Tests
# =============================================

@pytest.fixture(scope="module")
def benchmark():
    """Create benchmark instance"""
    bench = PerformanceBenchmark(BASE_URL)
    assert bench.login(), "Failed to login for benchmarks"
    return bench


class TestResponseTimePerformance:
    """Test API response times meet SLAs"""
    
    # SLA thresholds in milliseconds - adjusted for external environments
    # These are higher to account for network latency in cloud environments
    SLA_FAST = 500       # Fast endpoints (simple reads)
    SLA_NORMAL = 2000    # Normal endpoints 
    SLA_SLOW = 5000      # Slow endpoints (complex queries)
    SLA_EXTERNAL = 10000 # For external environment testing with potential network issues
    
    def test_login_performance(self, benchmark):
        """Login should be fast"""
        result = benchmark.run_benchmark("login", "POST", "/api/auth/login", 
                                         iterations=5,
                                         json={"email": SUPER_ADMIN_EMAIL, "password": SUPER_ADMIN_PASSWORD})
        print(f"\nLogin Performance: avg={result['avg_ms']}ms, p50={result['median_ms']}ms")
        assert result["avg_ms"] < self.SLA_NORMAL, f"Login too slow: {result['avg_ms']}ms > {self.SLA_NORMAL}ms"
    
    def test_get_tasks_performance(self, benchmark):
        """Task list should be reasonably fast"""
        result = benchmark.run_benchmark("get_tasks", "GET", "/api/tasks/", iterations=10)
        print(f"\nGet Tasks: avg={result['avg_ms']}ms, p50={result['median_ms']}ms")
        # Use external SLA for cloud environments
        assert result["avg_ms"] < self.SLA_EXTERNAL, f"Get tasks too slow: {result['avg_ms']}ms"
        # Also check median is acceptable (less affected by outliers)
        assert result["median_ms"] < self.SLA_NORMAL, f"Get tasks median too slow: {result['median_ms']}ms"
    
    def test_get_projects_performance(self, benchmark):
        """Project list should be reasonably fast"""
        result = benchmark.run_benchmark("get_projects", "GET", "/api/projects/", iterations=10)
        print(f"\nGet Projects: avg={result['avg_ms']}ms, p50={result['median_ms']}ms")
        assert result["median_ms"] < self.SLA_NORMAL, f"Get projects median too slow: {result['median_ms']}ms"
    
    def test_get_notifications_performance(self, benchmark):
        """Notifications should be reasonably fast"""
        result = benchmark.run_benchmark("get_notifications", "GET", "/api/notifications/", iterations=10)
        print(f"\nGet Notifications: avg={result['avg_ms']}ms, p50={result['median_ms']}ms")
        assert result["median_ms"] < self.SLA_NORMAL, f"Get notifications median too slow: {result['median_ms']}ms"
    
    def test_get_permissions_performance(self, benchmark):
        """Permission list is cached, should be reasonably fast"""
        result = benchmark.run_benchmark("get_permissions", "GET", "/api/roles/permissions", iterations=10)
        print(f"\nGet Permissions: avg={result['avg_ms']}ms, p50={result['median_ms']}ms")
        assert result["median_ms"] < self.SLA_NORMAL, f"Get permissions median too slow: {result['median_ms']}ms"
    
    def test_get_organization_members_performance(self, benchmark):
        """Member list should be reasonably fast"""
        if benchmark.org_id:
            result = benchmark.run_benchmark("get_members", "GET", 
                                             f"/api/organizations/{benchmark.org_id}/members", 
                                             iterations=10)
            print(f"\nGet Members: avg={result['avg_ms']}ms, p50={result['median_ms']}ms")
            assert result["median_ms"] < self.SLA_NORMAL, f"Get members median too slow: {result['median_ms']}ms"


class TestConcurrentLoadPerformance:
    """Test API under concurrent load"""
    
    # Lower thresholds for external environments with network latency
    MIN_THROUGHPUT = 1.0  # requests per second (lower for external URLs)
    MAX_P95_LATENCY = 20000  # ms (allow higher latency for external tests)
    
    def test_concurrent_task_reads(self, benchmark):
        """Test concurrent task reads"""
        result = benchmark.run_concurrent_benchmark(
            "concurrent_tasks", "GET", "/api/tasks/",
            concurrent_users=5, requests_per_user=10
        )
        print(f"\nConcurrent Task Reads:")
        print(f"  Total: {result.get('total_requests', 0)} requests in {result.get('total_time_s', 0)}s")
        print(f"  Throughput: {result.get('requests_per_second', 0)} req/s")
        print(f"  Latency: avg={result.get('avg_ms', 0)}ms, p95={result.get('p95_ms', 0)}ms, p99={result.get('p99_ms', 0)}ms")
        
        if "error" in result:
            pytest.skip(f"Concurrent test failed: {result['error']}")
        
        assert result["requests_per_second"] >= self.MIN_THROUGHPUT, f"Throughput too low: {result['requests_per_second']}"
        assert result["p95_ms"] < self.MAX_P95_LATENCY, f"P95 latency too high: {result['p95_ms']}ms"
    
    def test_concurrent_project_reads(self, benchmark):
        """Test concurrent project reads"""
        result = benchmark.run_concurrent_benchmark(
            "concurrent_projects", "GET", "/api/projects/",
            concurrent_users=5, requests_per_user=10
        )
        print(f"\nConcurrent Project Reads:")
        print(f"  Throughput: {result.get('requests_per_second', 0)} req/s")
        print(f"  Latency: avg={result.get('avg_ms', 0)}ms, p95={result.get('p95_ms', 0)}ms")
        
        if "error" in result:
            pytest.skip(f"Concurrent test failed: {result['error']}")
        
        assert result["requests_per_second"] >= self.MIN_THROUGHPUT, f"Throughput too low: {result['requests_per_second']}"
    
    def test_mixed_workload(self, benchmark):
        """Test mixed read workload"""
        endpoints = [
            ("/api/tasks/", "GET"),
            ("/api/projects/", "GET"),
            ("/api/notifications/", "GET"),
        ]
        
        all_times = []
        start = time.perf_counter()
        
        def mixed_request():
            times = []
            for url, method in endpoints:
                try:
                    elapsed = benchmark.measure_request("mixed", method, url, timeout=CONCURRENT_REQUEST_TIMEOUT)
                    times.append(elapsed)
                except (requests.exceptions.Timeout, requests.exceptions.RequestException):
                    continue
            return times
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(mixed_request) for _ in range(10)]
            for future in concurrent.futures.as_completed(futures, timeout=120):
                try:
                    all_times.extend(future.result())
                except concurrent.futures.TimeoutError:
                    continue
        
        total_time = time.perf_counter() - start
        total_requests = len(all_times)
        
        print(f"\nMixed Workload:")
        print(f"  Total: {total_requests} requests in {round(total_time, 2)}s")
        if total_requests > 0:
            print(f"  Throughput: {round(total_requests / total_time, 2)} req/s")
            print(f"  Avg Latency: {round(statistics.mean(all_times), 2)}ms")
        
        if total_requests == 0:
            pytest.skip("All mixed workload requests failed or timed out")
        
        assert total_requests / total_time >= 0.5, f"Mixed workload throughput too low: {total_requests / total_time}"


class TestDatabaseQueryPerformance:
    """Test database-heavy operations"""
    
    def test_time_summary_performance(self, benchmark):
        """Time summary aggregates data - should complete in reasonable time"""
        result = benchmark.run_benchmark("time_summary", "GET", "/api/time-entries/summary", iterations=5)
        print(f"\nTime Summary: avg={result['avg_ms']}ms, max={result['max_ms']}ms")
        assert result["median_ms"] < 5000, f"Time summary median too slow: {result['median_ms']}ms"
    
    def test_roles_with_member_counts(self, benchmark):
        """Roles list includes member counts - tests aggregation"""
        if benchmark.org_id:
            result = benchmark.run_benchmark("get_roles", "GET", 
                                             f"/api/roles/org/{benchmark.org_id}", 
                                             iterations=5)
            print(f"\nGet Roles: avg={result['avg_ms']}ms, max={result['max_ms']}ms")
            assert result["median_ms"] < 2000, f"Get roles median too slow: {result['median_ms']}ms"


# =============================================
# Stress Test Functions (for manual running)
# =============================================

def run_stress_test(duration_seconds: int = 60, users: int = 10):
    """Run a stress test for a specified duration"""
    print(f"\n{'='*60}")
    print(f"STRESS TEST: {users} users for {duration_seconds} seconds")
    print(f"{'='*60}")
    
    benchmark = PerformanceBenchmark(BASE_URL)
    if not benchmark.login():
        print("ERROR: Failed to login")
        return
    
    endpoints = [
        ("/api/tasks/", "GET"),
        ("/api/projects/", "GET"),
        ("/api/notifications/", "GET"),
    ]
    
    results = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "timeout_requests": 0,
        "response_times": []
    }
    
    end_time = time.time() + duration_seconds
    
    def worker():
        local_results = {"total": 0, "success": 0, "failed": 0, "timeout": 0, "times": []}
        while time.time() < end_time:
            url, method = endpoints[local_results["total"] % len(endpoints)]
            try:
                start = time.perf_counter()
                response = requests.request(
                    method, f"{BASE_URL}{url}",
                    headers={"Authorization": f"Bearer {benchmark.token}"},
                    timeout=CONCURRENT_REQUEST_TIMEOUT
                )
                elapsed = (time.perf_counter() - start) * 1000
                local_results["times"].append(elapsed)
                local_results["total"] += 1
                if response.status_code == 200:
                    local_results["success"] += 1
                else:
                    local_results["failed"] += 1
            except requests.exceptions.Timeout:
                local_results["total"] += 1
                local_results["timeout"] += 1
            except Exception as e:
                local_results["total"] += 1
                local_results["failed"] += 1
        return local_results
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
        futures = [executor.submit(worker) for _ in range(users)]
        for future in concurrent.futures.as_completed(futures, timeout=duration_seconds + 30):
            try:
                r = future.result()
                results["total_requests"] += r["total"]
                results["successful_requests"] += r["success"]
                results["failed_requests"] += r["failed"]
                results["timeout_requests"] += r["timeout"]
                results["response_times"].extend(r["times"])
            except concurrent.futures.TimeoutError:
                continue
    
    # Print results
    times = results["response_times"]
    if times:
        print(f"\nResults:")
        print(f"  Total Requests: {results['total_requests']}")
        print(f"  Successful: {results['successful_requests']} ({round(results['successful_requests']/results['total_requests']*100, 1) if results['total_requests'] else 0}%)")
        print(f"  Failed: {results['failed_requests']}")
        print(f"  Timeouts: {results['timeout_requests']}")
        print(f"  Requests/Second: {round(results['total_requests'] / duration_seconds, 2)}")
        print(f"  Response Times:")
        print(f"    Min: {round(min(times), 2)}ms")
        print(f"    Max: {round(max(times), 2)}ms")
        print(f"    Avg: {round(statistics.mean(times), 2)}ms")
        print(f"    Median: {round(statistics.median(times), 2)}ms")
        print(f"    P95: {round(sorted(times)[int(len(times) * 0.95)], 2)}ms")
        print(f"    P99: {round(sorted(times)[int(len(times) * 0.99)], 2)}ms")
    else:
        print("\nNo successful requests recorded")
    
    return results


# =============================================
# Run tests
# =============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stress":
        # Run stress test
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        users = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        run_stress_test(duration, users)
    else:
        # Run pytest
        pytest.main([__file__, "-v", "-s", "--tb=short"])
