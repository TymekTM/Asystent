"""
Quick Performance Test for GAJA Assistant
=========================================

Simplified version for quick performance checks
Focuses on system stability and basic metrics
"""

import asyncio
import time
import psutil
import aiohttp
import json
import os
from typing import Optional

class QuickPerfTest:
    """Quick performance test for system validation."""
    
    def __init__(self):
        # Load API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key = config.get("API_KEYS", {}).get("OPENAI_API_KEY")
            except Exception:
                pass
    
    async def quick_test(self, users: int = 50) -> dict:
        """Run a quick test with specified number of users."""
        if not self.api_key:
            return {"error": "No API key found"}
        
        print(f"🚀 Quick test: {users} concurrent users")
        
        # Monitor system before test
        cpu_before = psutil.cpu_percent()
        memory_before = psutil.virtual_memory().percent
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        ) as session:
            
            tasks = []
            for i in range(users):
                task = self._make_request(session, i)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Monitor system after test
        cpu_after = psutil.cpu_percent()
        memory_after = psutil.virtual_memory().percent
        
        # Analyze results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        
        return {
            "users": users,
            "duration": duration,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(results)) * 100,
            "rps": successful / duration,
            "cpu_usage": cpu_after,
            "memory_usage": memory_after,            "cpu_delta": cpu_after - cpu_before,
            "memory_delta": memory_after - memory_before
        }
    
    async def _make_request(self, session: aiohttp.ClientSession, user_id: int) -> dict:
        """Make a single API request."""
        try:
            payload = {
                "model": "gpt-4.1-nano",  # Cheapest and fastest model
                "messages": [{"role": "user", "content": f"Test {user_id}"}],
                "max_tokens": 10
            }
            
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    return {"success": True, "user_id": user_id}
                else:
                    return {"success": False, "user_id": user_id, "status": response.status}
                    
        except Exception as e:
            return {"success": False, "user_id": user_id, "error": str(e)}

async def main():
    """Run quick performance tests."""
    print("⚡ GAJA Assistant Quick Performance Test")
    print("=" * 50)
    
    tester = QuickPerfTest()
    
    # Test scenarios
    test_users = [10, 25, 50, 100]
    
    for users in test_users:
        try:
            result = await tester.quick_test(users)
            
            if "error" in result:
                print(f"❌ {users} users: {result['error']}")
                continue
            
            print(f"\n📊 {users} users:")
            print(f"   Success: {result['successful']}/{users} ({result['success_rate']:.1f}%)")
            print(f"   Duration: {result['duration']:.2f}s")
            print(f"   RPS: {result['rps']:.1f}")
            print(f"   CPU: {result['cpu_usage']:.1f}% (+{result['cpu_delta']:.1f}%)")
            print(f"   Memory: {result['memory_usage']:.1f}% (+{result['memory_delta']:.1f}%)")
            
            if result['success_rate'] >= 95:
                print("   ✅ Excellent")
            elif result['success_rate'] >= 80:
                print("   ⚠️ Good")
            else:
                print("   ❌ Poor - check API limits")
                
            # Small delay between tests
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Test failed for {users} users: {e}")
    
    print(f"\n🎉 Quick performance test completed!")

if __name__ == "__main__":
    asyncio.run(main())
