import os
import io
import time
import datetime
import threading
import unittest
from core.config import logger

# Test runner state
test_status = {
    'running': False,
    'result': None,
    'log': '',
    'summary': '',
    'ai_summary': ''
}
test_status_lock = threading.Lock()

bench_status = {'running': False, 'result': {}, 'log': '', 'summary': ''}
bench_status_lock = threading.Lock()

# Test history and scheduling
test_history = []
max_history_entries = 20
scheduled_interval = None  # in minutes
scheduled_timer = None
scheduler_lock = threading.Lock()

def run_unit_tests():
    """Run unit tests incrementally and update test_status for real-time UI."""
    global test_status
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(os.path.dirname(__file__), '..', '..', 'tests_unit'), pattern='test_*.py')
    stream = io.StringIO()
    # Initialize status
    with test_status_lock:
        test_status.update({
            'running': True,
            'result': None,
            'log': '',
            'summary': '',
            'ai_summary': '',
            'tests': [],
            'last_run': datetime.datetime.now().isoformat()
        })
    # Custom TestResult for streaming
    class StreamingResult(unittest.TextTestResult):
        def __init__(self, *args, **kwargs):
            # Accept all args including 'durations' and 'tb_locals'
            super().__init__(*args, **kwargs)
        def addSuccess(self, test):
            super().addSuccess(test)
            with test_status_lock:
                test_status['tests'].append({'name': test._testMethodName, 'class': test.__class__.__name__, 'status': 'ok', 'details': ''})
                test_status['log'] = stream.getvalue()
        def addFailure(self, test, err):
            super().addFailure(test, err)
            details = self.failures[-1][1]
            with test_status_lock:
                test_status['tests'].append({'name': test._testMethodName, 'class': test.__class__.__name__, 'status': 'FAIL', 'details': details})
                test_status['log'] = stream.getvalue()
        def addError(self, test, err):
            super().addError(test, err)
            details = self.errors[-1][1]
            with test_status_lock:
                test_status['tests'].append({'name': test._testMethodName, 'class': test.__class__.__name__, 'status': 'ERROR', 'details': details})
                test_status['log'] = stream.getvalue()
    runner = unittest.TextTestRunner(stream=stream, verbosity=1, resultclass=StreamingResult)
    result_obj = runner.run(suite)
    output = stream.getvalue()
    with test_status_lock:
        test_status['running'] = False
        test_status['result'] = 'passed' if result_obj.wasSuccessful() else 'failed'
        test_status['summary'] = parse_test_summary(output)
        test_status['ai_summary'] = generate_ai_summary(output)
        test_status['log'] = output
        # Append to history
        entry = {
            'timestamp': test_status.get('last_run'),
            'result': test_status['result'],
            'summary': test_status['summary']
        }
        test_history.append(entry)
        if len(test_history) > max_history_entries:
            test_history.pop(0)

def parse_test_summary(output):
    """Extracts a simple summary from unittest output."""
    import re
    match = re.search(r'Ran (\d+) tests? in ([\d\.]+)s', output)
    if match:
        total = match.group(1)
        time = match.group(2)
        failed = 'FAILED' in output or 'ERROR' in output
        return f"Wykonano {total} testów w {time}s. {'Błędy!' if failed else 'Wszystkie zaliczone.'}"
    return 'Brak podsumowania.'

def generate_ai_summary(output):
    """Placeholder for AI-generated summary. Można podpiąć model AI tutaj."""
    if 'FAILED' in output or 'ERROR' in output:
        return 'Niektóre testy nie przeszły. Sprawdź szczegóły poniżej.'
    if 'OK' in output:
        return 'Wszystkie testy zaliczone pomyślnie.'
    return 'Brak szczegółowego podsumowania.'

def run_benchmarks():
    """Run system benchmarks."""
    with bench_status_lock:
        bench_status['running'] = True
        bench_status['result'] = {}
        bench_status['log'] = ''
        bench_status['summary'] = ''
    log_lines = []
    try:
        import psutil, time
        # System info
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
        total_gb = psutil.virtual_memory().total / (1024**3)
        log_lines.append(f"CPU cores: {cpu_count}")
        log_lines.append(f"Total RAM: {total_gb:.2f} GB")
        # CPU benchmark
        start = time.time()
        sum(range(10_000_000))
        cpu_time = time.time() - start
        log_lines.append(f"Sum(range(10_000_000)): {cpu_time:.3f}s")
        # Memory benchmark
        proc = psutil.Process()
        mem_before = proc.memory_info().rss / (1024**2)
        lst = [0] * 10_000_000
        mem_after = proc.memory_info().rss / (1024**2)
        mem_delta = mem_after - mem_before
        log_lines.append(f"Alloc list(10M ints): +{mem_delta:.2f} MB")
        # Disk I/O benchmark: write and read 10MB file
        import tempfile
        # Prepare 10MB file in temp location
        fd, tmp_path = tempfile.mkstemp(prefix="bench_io_", suffix=".tmp")
        os.close(fd)
        data = b'\0' * (1 * 1024 * 1024)
        num_chunks = 10
        start_io = time.time()
        with open(tmp_path, "wb") as f:
            for _ in range(num_chunks):
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        write_time = time.time() - start_io
        log_lines.append(f"Write 10MB file: {write_time:.3f}s")
        # Read back the file
        start_io = time.time()
        with open(tmp_path, "rb") as f:
            while f.read(1024 * 1024):
                pass
        read_time = time.time() - start_io
        log_lines.append(f"Read 10MB file: {read_time:.3f}s")
        # Cleanup
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        # Prepare initial results including CPU and memory
        result = {
            'cpu_cores': cpu_count,
            'total_memory_gb': round(total_gb, 2),
            'cpu_benchmark_sec': round(cpu_time, 3),
            'memory_alloc_mb': round(mem_delta, 2)
        }
        # Add disk I/O results
        result['disk_write_sec'] = round(write_time, 3)
        result['disk_read_sec'] = round(read_time, 3)
        # Prepare summary string
        summary = (
            f"{cpu_count} cores, {total_gb:.1f}GB RAM; "
            f"CPU: {cpu_time:.3f}s; Mem: {mem_delta:.2f}MB; "
            f"Write: {result['disk_write_sec']:.3f}s; Read: {result['disk_read_sec']:.3f}s"
        )
        log = "\n".join(log_lines)
        with bench_status_lock:
            bench_status['running'] = False
            bench_status['result'] = result
            bench_status['log'] = log
            bench_status['summary'] = summary
    except Exception as e:
        err = str(e)
        with bench_status_lock:
            bench_status['running'] = False
            bench_status['summary'] = f"Error: {err}"
            bench_status['log'] = "\n".join(log_lines) + f"\nError: {err}"
            bench_status['result'] = {}
