# 🧪 Comprehensive 60-Minute Multi-User Stress Test Suite

## Overview

This comprehensive stress testing suite tests the Gaja system under realistic production conditions for 60 minutes with multiple concurrent users. It verifies system stability, performance, memory management, user isolation, and all critical functionality.

## 🎯 Test Objectives

The test suite validates:

- **System Stability**: No crashes during 60-minute operation
- **Session Isolation**: Each user gets their own data and responses
- **Memory Functionality**: Short, mid, and long-term memory work correctly
- **Performance**: Response times stay within acceptable limits
- **Rate Limiting**: Free vs premium user limits work correctly
- **Plugin System**: All plugins function under load
- **Fallback Mechanisms**: LLM fallback works when plugins fail
- **Resource Usage**: CPU/RAM usage stays within acceptable limits

## 🏗️ Architecture

### Components

1. **`test_multi_user_stress_60min.py`** - Main stress test orchestrator
2. **`system_resource_monitor.py`** - System resource monitoring
3. **`run_comprehensive_stress_test.py`** - Combined test runner
4. **`server_manager.py`** - Server management utilities

### Test Phases

#### Phase 1 (0-15 min): Basic Interaction

- Plugin testing (weather, time, notes, reminders, calculator)
- Different languages (PL/EN)
- Long and short queries
- LLM fallback testing

#### Phase 2 (15-30 min): Memory Testing

- Store personal information
- Test memory recall after delays
- Context persistence verification

#### Phase 3 (30-45 min): Limits and Priority

- Rate limiting for free users
- Priority handling for premium users
- Concurrent request handling

#### Phase 4 (45-60 min): Long Sessions & Edge Cases

- Dialog simulations
- Edge case handling
- Error recovery testing

## 🚀 Running the Tests

### Prerequisites

1. **Server Running**: Gaja server must be running on `localhost:8001`
2. **Dependencies**: Install required packages:
   ```bash
   pip install aiohttp psutil pytest
   ```

### Quick Start

```bash
# Check if server is running and start if needed
python tests_pytest/server_manager.py --auto-start

# Run the comprehensive stress test
python tests_pytest/run_comprehensive_stress_test.py
```

### Advanced Usage

```bash
# Run with custom server URL
python tests_pytest/run_comprehensive_stress_test.py --server-url http://your-server:8001

# Run quick 5-minute test (for development)
python tests_pytest/run_comprehensive_stress_test.py --quick-test

# Run monitoring only
python tests_pytest/system_resource_monitor.py

# Run stress test only (via pytest)
pytest tests_pytest/test_multi_user_stress_60min.py::test_60_minute_multi_user_stress -v
```

## 📊 Test Configuration

### User Profiles

The test creates multiple user profiles with different characteristics:

- **User Types**: Free vs Premium
- **Languages**: Polish (PL) vs English (EN)
- **Platforms**: Windows, Linux, Mac simulation

### Performance Targets

- **Success Rate**: ≥ 90%
- **Average Response Time**: ≤ 1.5 seconds
- **Max Response Time**: ≤ 2.5 seconds
- **CPU Usage**: ≤ 80% average
- **Memory Usage**: ≤ 80% average

### Test Queries

The test uses realistic queries including:

- Plugin-specific queries (weather, time, notes, etc.)
- Memory test phrases with personal information
- Long queries to test LLM capabilities
- Edge cases (empty queries, special characters, etc.)

## 📋 Monitoring

### System Resources

The monitoring system tracks:

- **CPU Usage**: Average, peak, time over 80%
- **Memory Usage**: Average, peak, total GB used
- **Disk Usage**: Space utilization
- **Network Activity**: Bytes sent/received
- **Process Count**: System load indicator
- **Docker Stats**: Container resource usage (if applicable)

### Application Logs

Monitors log files for:

- Error messages
- Warning messages
- Critical failures
- Performance issues

## 📄 Reports

### Test Reports

After completion, the test generates:

1. **Comprehensive Report** (`comprehensive_stress_test_report_YYYYMMDD_HHMMSS.json`)

   - Complete test results
   - Performance metrics
   - User statistics
   - Error analysis
   - Combined analysis and recommendations

2. **Resource Monitoring Report** (`resource_monitor_report_YYYYMMDD_HHMMSS.json`)

   - Detailed resource usage over time
   - System statistics
   - Performance snapshots

3. **Test Logs** (`comprehensive_stress_test_YYYYMMDD_HHMMSS.log`)
   - Detailed execution logs
   - Error messages
   - Performance warnings

### Report Structure

```json
{
  "test_metadata": {
    "test_type": "comprehensive_60_minute_stress_test",
    "duration_minutes": 60.0,
    "start_time": "2025-01-24T10:00:00",
    "server_url": "http://localhost:8001"
  },
  "stress_test_results": {
    "test_summary": {
      "total_users": 3,
      "total_requests": 450,
      "success_rate_percent": 95.2,
      "rate_limit_hits": 12
    },
    "performance_metrics": {
      "average_response_time_seconds": 1.234,
      "max_response_time_seconds": 2.456
    }
  },
  "monitoring_results": {
    "resource_usage": {
      "cpu_usage": { "average": 45.2, "maximum": 78.5 },
      "memory_usage": { "average": 52.1, "maximum": 71.3 }
    }
  },
  "combined_analysis": {
    "overall_status": "passed",
    "critical_issues": [],
    "warnings": [],
    "recommendations": ["System is ready for production"]
  }
}
```

## ✅ Success Criteria

### Test Passes If:

- ✅ **No Crashes**: System runs for full 60 minutes without major failures
- ✅ **High Success Rate**: ≥ 90% of requests succeed
- ✅ **Good Performance**: Average response time ≤ 1.5s
- ✅ **User Isolation**: No data mixing between users
- ✅ **Memory Works**: Memory recall success rate ≥ 70%
- ✅ **Plugins Work**: All plugin types tested successfully
- ✅ **Resource Usage**: CPU/RAM usage stays reasonable (≤ 80% average)
- ✅ **Rate Limiting**: Free users hit limits, premium users don't

### Test Fails If:

- ❌ **System Crashes**: Server becomes unavailable
- ❌ **Poor Performance**: Response times consistently > 2.5s
- ❌ **Low Success Rate**: < 90% request success rate
- ❌ **Resource Exhaustion**: CPU/RAM consistently > 90%
- ❌ **Data Corruption**: Users see each other's data
- ❌ **Memory Failure**: Memory recall success rate < 70%

## 🔧 Troubleshooting

### Common Issues

1. **Server Not Running**

   ```bash
   python tests_pytest/server_manager.py --auto-start
   ```

2. **High Memory Usage**

   - Check for memory leaks in logs
   - Monitor garbage collection
   - Review database connection pooling

3. **Slow Response Times**

   - Check CPU usage during test
   - Monitor database query performance
   - Review network latency

4. **Test Failures**
   - Check server logs for errors
   - Review resource usage graphs
   - Verify server configuration

### Debug Mode

Enable debug logging:

```bash
export GAJA_LOG_LEVEL=DEBUG
python tests_pytest/run_comprehensive_stress_test.py
```

## 🔍 Compliance

This stress test is fully compliant with:

- **AGENTS.md** coding standards

  - ✅ Uses async/await throughout
  - ✅ Includes comprehensive test coverage
  - ✅ Proper error handling and logging
  - ✅ No blocking operations

- **Finishing Touches Guidelines**
  - ✅ Tests all main flow components
  - ✅ Validates memory system
  - ✅ Tests plugin system
  - ✅ Verifies multi-user support
  - ✅ Confirms system stability

## 📈 Performance Benchmarks

### Typical Results (Production Ready System)

- **Users**: 3-5 concurrent
- **Requests**: 400-600 total
- **Success Rate**: 95-99%
- **Average Response Time**: 0.8-1.2 seconds
- **Peak CPU**: 60-75%
- **Peak Memory**: 50-70%
- **Memory Tests**: 85-95% success
- **Rate Limit Hits**: 5-20 (expected for free users)

### Performance Optimization Tips

1. **Database Optimization**

   - Use connection pooling
   - Optimize memory queries
   - Index frequently accessed columns

2. **Memory Management**

   - Implement proper cleanup
   - Monitor memory usage patterns
   - Use efficient data structures

3. **Caching**
   - Cache frequent plugin responses
   - Implement session caching
   - Use response compression

## 🚀 Production Deployment

After passing the stress test:

1. **Review Reports**: Check for any warnings or recommendations
2. **Performance Tuning**: Implement suggested optimizations
3. **Monitoring Setup**: Configure production monitoring
4. **Load Balancing**: Consider horizontal scaling if needed
5. **Backup Strategy**: Ensure data backup procedures are in place

## 📞 Support

For issues with the stress test suite:

1. Check the generated log files
2. Review the troubleshooting section
3. Verify server configuration matches test requirements
4. Check system resources and dependencies

---

_This stress test suite ensures your Gaja system is ready for production deployment with confidence in its stability, performance, and reliability under real-world conditions._
