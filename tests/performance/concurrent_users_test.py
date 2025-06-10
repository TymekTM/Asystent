"""
GAJA Assistant Concurrent Users Performance Test
================================================

Test wydajnościowy dla 100, 200, 1000 i 10000 concurrent users
- Używa OpenAI API (500 RPM limit)
- Bez TTS - tylko transfer danych
- Monitoring CPU i pamięci RAM
- Analiza wydajności i bottlenecks
"""

import asyncio
import time
import logging
import psutil
import aiohttp
import json
import statistics
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
import os
from datetime import datetime
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Wynik pojedynczego testu."""
    user_id: int
    start_time: float
    end_time: float
    response_time: float
    success: bool
    error: Optional[str] = None
    response_size: int = 0
    status_code: Optional[int] = None

@dataclass
class SystemMetrics:
    """Metryki systemowe."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int

@dataclass
class ConcurrencyTestSummary:
    """Podsumowanie testu concurrency."""
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    max_response_time: float
    min_response_time: float
    requests_per_second: float
    total_duration: float
    max_cpu_usage: float
    max_memory_usage: float
    max_memory_mb: float
    data_transferred_mb: float
    errors: Dict[str, int]

class PerformanceMonitor:
    """Monitor wydajności systemowej."""
    
    def __init__(self):
        self.metrics: List[SystemMetrics] = []
        self.monitoring = False
        self.monitor_task = None
        self.initial_network = psutil.net_io_counters()
    
    async def start_monitoring(self, interval: float = 0.5):
        """Rozpoczyna monitoring systemu."""
        self.monitoring = True
        self.metrics.clear()
        self.initial_network = psutil.net_io_counters()
        
        async def monitor():
            while self.monitoring:
                try:
                    # CPU i pamięć
                    cpu_percent = psutil.cpu_percent(interval=None)
                    memory = psutil.virtual_memory()
                    
                    # Sieć
                    network = psutil.net_io_counters()
                    network_sent_mb = (network.bytes_sent - self.initial_network.bytes_sent) / 1024 / 1024
                    network_recv_mb = (network.bytes_recv - self.initial_network.bytes_recv) / 1024 / 1024
                    
                    # Połączenia sieciowe
                    try:
                        connections = len(psutil.net_connections())
                    except (psutil.AccessDenied, OSError):
                        connections = 0
                    
                    metric = SystemMetrics(
                        timestamp=time.time(),
                        cpu_percent=cpu_percent,
                        memory_percent=memory.percent,
                        memory_mb=memory.used / 1024 / 1024,
                        network_sent_mb=network_sent_mb,
                        network_recv_mb=network_recv_mb,
                        active_connections=connections
                    )
                    
                    self.metrics.append(metric)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring: {e}")
                
                await asyncio.sleep(interval)
        
        self.monitor_task = asyncio.create_task(monitor())
    
    async def stop_monitoring(self):
        """Zatrzymuje monitoring systemu."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    def get_peak_metrics(self) -> Dict[str, float]:
        """Zwraca szczytowe wartości metryk."""
        if not self.metrics:
            return {}
        
        return {
            "max_cpu_percent": max(m.cpu_percent for m in self.metrics),
            "max_memory_percent": max(m.memory_percent for m in self.metrics),
            "max_memory_mb": max(m.memory_mb for m in self.metrics),
            "max_network_sent_mb": max(m.network_sent_mb for m in self.metrics),
            "max_network_recv_mb": max(m.network_recv_mb for m in self.metrics),
            "max_connections": max(m.active_connections for m in self.metrics)
        }

class OpenAILoadTester:
    """Tester obciążenia dla OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # If not in environment, try to load from config.json
        if not self.api_key:
            try:
                import json
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key = config.get("API_KEYS", {}).get("OPENAI_API_KEY")
            except Exception as e:
                logger.error(f"Failed to load API key from config.json: {e}")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required - set OPENAI_API_KEY or add to config.json")
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: List[TestResult] = []
        self.monitor = PerformanceMonitor()
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(
            limit=None,  # No limit on total connections
            limit_per_host=1000,  # High limit per host
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def simulate_user_request(self, user_id: int) -> TestResult:
        """Symuluje żądanie pojedynczego użytkownika."""
        start_time = time.time()
          # Realistic user query for testing
        test_prompt = f"Użytkownik {user_id}: Proszę o krótką odpowiedź na pytanie o pogodę."
        
        payload = {
            "model": "gpt-4.1-nano",  # Cheapest model, sufficient for testing
            "messages": [
                {"role": "user", "content": test_prompt}
            ],
            "max_tokens": 100,  # Krótkie odpowiedzi dla wydajności
            "temperature": 0.7
        }
        
        try:
            async with self.session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload
            ) as response:
                end_time = time.time()
                
                if response.status == 200:
                    response_data = await response.json()
                    response_size = len(json.dumps(response_data))
                    
                    return TestResult(
                        user_id=user_id,
                        start_time=start_time,
                        end_time=end_time,
                        response_time=end_time - start_time,
                        success=True,
                        response_size=response_size,
                        status_code=response.status
                    )
                else:
                    error_text = await response.text()
                    return TestResult(
                        user_id=user_id,
                        start_time=start_time,
                        end_time=end_time,
                        response_time=end_time - start_time,
                        success=False,
                        error=f"HTTP {response.status}: {error_text}",
                        status_code=response.status
                    )
                    
        except Exception as e:
            end_time = time.time()
            return TestResult(
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                response_time=end_time - start_time,
                success=False,
                error=str(e)
            )
    
    async def run_concurrent_test(self, concurrent_users: int, requests_per_user: int = 1) -> ConcurrencyTestSummary:
        """Uruchamia test z określoną liczbą concurrent users."""
        logger.info(f"🚀 Starting test with {concurrent_users} concurrent users")
        logger.info(f"📊 Each user will make {requests_per_user} request(s)")
        
        # Start monitoring
        await self.monitor.start_monitoring()
        
        # Reset results
        self.results.clear()
        
        # Test start time
        test_start = time.time()
        
        # Create tasks for concurrent users
        tasks = []
        for user_id in range(concurrent_users):
            for request_num in range(requests_per_user):
                task_user_id = user_id * requests_per_user + request_num
                task = asyncio.create_task(self.simulate_user_request(task_user_id))
                tasks.append(task)
        
        # Execute all tasks concurrently
        logger.info(f"⏳ Executing {len(tasks)} concurrent requests...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, TestResult):
                self.results.append(result)
            else:
                logger.error(f"Task failed with exception: {result}")
        
        test_end = time.time()
        total_duration = test_end - test_start
        
        # Stop monitoring
        await self.monitor.stop_monitoring()
        
        # Calculate statistics
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        if successful_results:
            response_times = [r.response_time for r in successful_results]
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            
            # Percentiles
            sorted_times = sorted(response_times)
            p95_idx = int(0.95 * len(sorted_times))
            p99_idx = int(0.99 * len(sorted_times))
            
            p95_response_time = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
            p99_response_time = sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1]
            
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = median_response_time = 0
            p95_response_time = p99_response_time = 0
            max_response_time = min_response_time = 0
        
        # Error analysis
        error_counts = {}
        for result in failed_results:
            error = result.error or "Unknown error"
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # System metrics
        peak_metrics = self.monitor.get_peak_metrics()
        
        # Data transfer calculation
        total_data_mb = sum(r.response_size for r in self.results) / 1024 / 1024
        
        # Calculate requests per second
        rps = len(self.results) / total_duration if total_duration > 0 else 0
        
        summary = ConcurrencyTestSummary(
            concurrent_users=concurrent_users,
            total_requests=len(self.results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            success_rate=len(successful_results) / len(self.results) * 100 if self.results else 0,
            average_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            requests_per_second=rps,
            total_duration=total_duration,
            max_cpu_usage=peak_metrics.get("max_cpu_percent", 0),
            max_memory_usage=peak_metrics.get("max_memory_percent", 0),
            max_memory_mb=peak_metrics.get("max_memory_mb", 0),
            data_transferred_mb=total_data_mb,
            errors=error_counts
        )
        
        return summary

def print_test_summary(summary: ConcurrencyTestSummary):
    """Wyświetla podsumowanie testu."""
    print(f"\n{'='*60}")
    print(f"🎯 CONCURRENT USERS TEST RESULTS: {summary.concurrent_users} users")
    print(f"{'='*60}")
    
    # Request statistics
    print(f"📊 REQUEST STATISTICS:")
    print(f"   Total requests: {summary.total_requests}")
    print(f"   Successful: {summary.successful_requests}")
    print(f"   Failed: {summary.failed_requests}")
    print(f"   Success rate: {summary.success_rate:.2f}%")
    print(f"   Requests/sec: {summary.requests_per_second:.2f}")
    print(f"   Total duration: {summary.total_duration:.2f}s")
    
    # Response time statistics
    print(f"\n⏱️ RESPONSE TIME STATISTICS:")
    print(f"   Average: {summary.average_response_time:.3f}s")
    print(f"   Median: {summary.median_response_time:.3f}s")
    print(f"   95th percentile: {summary.p95_response_time:.3f}s")
    print(f"   99th percentile: {summary.p99_response_time:.3f}s")
    print(f"   Min: {summary.min_response_time:.3f}s")
    print(f"   Max: {summary.max_response_time:.3f}s")
    
    # System metrics
    print(f"\n💻 SYSTEM METRICS:")
    print(f"   Peak CPU usage: {summary.max_cpu_usage:.1f}%")
    print(f"   Peak memory usage: {summary.max_memory_usage:.1f}%")
    print(f"   Peak memory: {summary.max_memory_mb:.1f} MB")
    print(f"   Data transferred: {summary.data_transferred_mb:.2f} MB")
    
    # Errors
    if summary.errors:
        print(f"\n❌ ERRORS:")
        for error, count in summary.errors.items():
            print(f"   {error}: {count} occurrences")
    
    # Performance assessment
    print(f"\n🎯 PERFORMANCE ASSESSMENT:")
    if summary.success_rate >= 95:
        print("   ✅ Excellent success rate")
    elif summary.success_rate >= 90:
        print("   ⚠️ Good success rate")
    else:
        print("   ❌ Poor success rate - investigate failures")
    
    if summary.average_response_time <= 2.0:
        print("   ✅ Excellent response times")
    elif summary.average_response_time <= 5.0:
        print("   ⚠️ Acceptable response times")
    else:
        print("   ❌ Slow response times - performance issues")
    
    if summary.max_cpu_usage <= 80:
        print("   ✅ Good CPU utilization")
    else:
        print("   ⚠️ High CPU usage - monitor for bottlenecks")

async def main():
    """Main test function."""
    print("🚀 GAJA Assistant Concurrent Users Performance Test")
    print("=" * 60)
    print("📋 Testing OpenAI API with concurrent users")
    print("🚫 No TTS - only data transfer and system monitoring")
    print()
      # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("API_KEYS", {}).get("OPENAI_API_KEY")
        except Exception as e:
            logger.error(f"Failed to load API key from config.json: {e}")
    
    if not api_key:
        print("❌ OpenAI API key not found!")
        print("   Set OPENAI_API_KEY environment variable or add to config.json")
        return
    
    print("✅ OpenAI API key found")
    print(f"⚠️ OpenAI API limit: 500 requests per minute")
    print()
    
    # Test scenarios
    test_scenarios = [100, 200, 1000, 10000]
    
    # Store all results for comparison
    all_results = []
    
    try:
        async with OpenAILoadTester(api_key) as tester:
            for concurrent_users in test_scenarios:
                print(f"\n🎯 TESTING {concurrent_users} CONCURRENT USERS")
                print("-" * 50)
                
                # Adjust requests per user based on API limits
                # 500 RPM = ~8.3 requests per second
                # Spread requests to avoid hitting rate limits
                requests_per_user = 1
                
                if concurrent_users > 500:
                    print(f"⚠️ {concurrent_users} users exceeds OpenAI rate limit (500 RPM)")
                    print("   Test will likely encounter rate limiting")
                
                try:
                    summary = await tester.run_concurrent_test(
                        concurrent_users=concurrent_users,
                        requests_per_user=requests_per_user
                    )
                    
                    print_test_summary(summary)
                    all_results.append(summary)
                    
                    # Wait between tests to respect rate limits
                    if concurrent_users < max(test_scenarios):
                        wait_time = 10 if concurrent_users <= 500 else 60
                        print(f"\n⏳ Waiting {wait_time}s before next test...")
                        await asyncio.sleep(wait_time)
                        
                except Exception as e:
                    print(f"❌ Test failed for {concurrent_users} users: {e}")
                    logger.exception("Test failed")
    
        # Final comparison
        if len(all_results) > 1:
            print(f"\n{'='*80}")
            print("📊 COMPARATIVE ANALYSIS")
            print(f"{'='*80}")
            
            print(f"{'Users':<8} {'Success%':<10} {'Avg Time':<12} {'RPS':<8} {'CPU%':<8} {'Memory%':<10}")
            print("-" * 80)
            
            for result in all_results:
                print(f"{result.concurrent_users:<8} "
                      f"{result.success_rate:<10.1f} "
                      f"{result.average_response_time:<12.3f} "
                      f"{result.requests_per_second:<8.1f} "
                      f"{result.max_cpu_usage:<8.1f} "
                      f"{result.max_memory_usage:<10.1f}")
        
        print(f"\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        logger.exception("Test suite failed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
