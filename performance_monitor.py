\
import time
import json
import os
import logging
from functools import wraps
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)
STATS_FILE = 'performance_stats.jsonl'  # Use JSON Lines for easier appending
stats_lock = threading.Lock()

# In-memory aggregation for averages to avoid reading the file constantly
aggregated_stats = defaultdict(lambda: {'total_time': 0.0, 'count': 0})
aggregation_lock = threading.Lock()

def measure_performance(func):
    """Decorator to measure execution time of a function and log it."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            func_name = func.__name__
            module_name = func.__module__
            full_name = f"{module_name}.{func_name}"

            # Log to file
            log_entry = {
                'timestamp': time.time(),
                'function': full_name,
                'duration_ms': duration * 1000, # Store in milliseconds
            }
            try:
                with stats_lock:
                    with open(STATS_FILE, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(log_entry) + '\n')
            except IOError as e:
                logger.error(f"Error writing performance stats to {STATS_FILE}: {e}")

            # Update in-memory aggregation
            with aggregation_lock:
                aggregated_stats[full_name]['total_time'] += duration
                aggregated_stats[full_name]['count'] += 1

            # Optional: Log to console logger as well
            # logger.debug(f"PERF: {full_name} took {duration:.4f}s")

    return wrapper

def load_and_aggregate_stats():
    """Loads all stats from the file and aggregates them."""
    global aggregated_stats
    temp_aggregated_stats = defaultdict(lambda: {'total_time': 0.0, 'count': 0})
    try:
        with stats_lock: # Ensure file isn't being written to while reading
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            func_name = entry.get('function')
                            duration_ms = entry.get('duration_ms')
                            if func_name and duration_ms is not None:
                                # Convert duration back to seconds for aggregation consistency
                                duration_sec = duration_ms / 1000.0
                                temp_aggregated_stats[func_name]['total_time'] += duration_sec
                                temp_aggregated_stats[func_name]['count'] += 1
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid line in {STATS_FILE}: {line.strip()}")
    except IOError as e:
        logger.error(f"Error reading performance stats file {STATS_FILE}: {e}")
        # Return current in-memory stats if file reading fails
        with aggregation_lock:
            return aggregated_stats.copy() # Return a copy

    # Update the global in-memory stats with the freshly loaded data
    with aggregation_lock:
        aggregated_stats = temp_aggregated_stats
        return aggregated_stats.copy() # Return a copy

def get_average_times():
    """Calculates and returns average execution time for each function."""
    averages = {}
    # Load latest aggregates from file first
    current_aggregates = load_and_aggregate_stats()

    for func_name, data in current_aggregates.items():
        if data['count'] > 0:
            avg_time_sec = data['total_time'] / data['count']
            averages[func_name] = {
                'average_ms': avg_time_sec * 1000,
                'count': data['count']
            }
    # Sort by average time descending
    sorted_averages = dict(sorted(averages.items(), key=lambda item: item[1]['average_ms'], reverse=True))
    return sorted_averages

def clear_performance_stats():
    """Clears the performance statistics file."""
    global aggregated_stats
    try:
        with stats_lock:
            if os.path.exists(STATS_FILE):
                os.remove(STATS_FILE)
        with aggregation_lock:
             aggregated_stats = defaultdict(lambda: {'total_time': 0.0, 'count': 0})
        logger.info(f"Performance stats file {STATS_FILE} cleared.")
        return True
    except OSError as e:
        logger.error(f"Error clearing performance stats file {STATS_FILE}: {e}")
        return False

# Load existing stats on module import
load_and_aggregate_stats()

# Example usage (can be removed later)
# @measure_performance
# def example_function(duration):
#     time.sleep(duration)

# if __name__ == "__main__":
#     print("Running example...")
#     example_function(0.1)
#     example_function(0.2)
#     print("Current Stats:", _stats_data)
#     print("Averages:", get_average_times())
#     # save_stats() # atexit handles this
