"""🔧 System Resource Monitor for Stress Testing.

Monitors CPU, RAM, disk, and network usage during stress tests.
Compliant with AGENTS.md requirements - uses async monitoring.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

import psutil

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    """Single resource usage snapshot."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    docker_stats: dict | None = None


@dataclass
class ResourceMonitor:
    """Monitors system resources during stress testing."""

    snapshots: list[ResourceSnapshot] = field(default_factory=list)
    monitoring: bool = False
    interval_seconds: float = 5.0

    async def get_docker_stats(self) -> dict | None:
        """Get Docker container stats if available."""
        try:
            # Try to get docker stats for Gaja containers
            process = await asyncio.create_subprocess_exec(
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                lines = stdout.decode().strip().split("\n")
                if len(lines) > 1:  # Skip header
                    stats = {}
                    for line in lines[1:]:
                        parts = line.split("\t")
                        if len(parts) >= 4:
                            container = parts[0]
                            if "gaja" in container.lower():
                                stats[container] = {
                                    "cpu_percent": parts[1],
                                    "memory_usage": parts[2],
                                    "memory_percent": parts[3],
                                }
                    return stats if stats else None

        except Exception as e:
            logger.debug(f"Docker stats not available: {e}")

        return None

    async def take_snapshot(self) -> ResourceSnapshot:
        """Take a single resource snapshot."""
        # CPU and memory
        cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking call
        await asyncio.sleep(1)  # Wait for 1 second for accurate reading
        memory = psutil.virtual_memory()

        # Disk usage for the current directory
        disk = psutil.disk_usage(".")

        # Network stats
        network = psutil.net_io_counters()

        # Process count
        process_count = len(psutil.pids())

        # Docker stats (if available)
        docker_stats = await self.get_docker_stats()

        snapshot = ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024**3),
            memory_total_gb=memory.total / (1024**3),
            disk_percent=disk.percent,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            process_count=process_count,
            docker_stats=docker_stats,
        )

        return snapshot

    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        self.monitoring = True
        logger.info(
            f"🔍 Starting resource monitoring (interval: {self.interval_seconds}s)"
        )

        while self.monitoring:
            try:
                snapshot = await self.take_snapshot()
                self.snapshots.append(snapshot)

                # Log significant resource usage
                if snapshot.cpu_percent > 80:
                    logger.warning(f"⚠️ High CPU usage: {snapshot.cpu_percent:.1f}%")

                if snapshot.memory_percent > 80:
                    logger.warning(
                        f"⚠️ High memory usage: {snapshot.memory_percent:.1f}%"
                    )

                if snapshot.disk_percent > 90:
                    logger.warning(f"⚠️ High disk usage: {snapshot.disk_percent:.1f}%")

                # Log every 10th snapshot (every 50 seconds by default)
                if len(self.snapshots) % 10 == 0:
                    logger.info(
                        f"📊 CPU: {snapshot.cpu_percent:.1f}% | "
                        f"RAM: {snapshot.memory_percent:.1f}% "
                        f"({snapshot.memory_used_gb:.1f}GB/{snapshot.memory_total_gb:.1f}GB) | "
                        f"Processes: {snapshot.process_count}"
                    )

            except Exception as e:
                logger.error(f"❌ Error taking resource snapshot: {e}")

            await asyncio.sleep(self.interval_seconds)

    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self.monitoring = False
        logger.info("🛑 Stopping resource monitoring")

    def get_statistics(self) -> dict:
        """Get resource usage statistics."""
        if not self.snapshots:
            return {}

        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_percent for s in self.snapshots]

        return {
            "monitoring_duration_minutes": (
                (
                    self.snapshots[-1].timestamp - self.snapshots[0].timestamp
                ).total_seconds()
                / 60
            ),
            "total_snapshots": len(self.snapshots),
            "cpu_usage": {
                "average": sum(cpu_values) / len(cpu_values),
                "maximum": max(cpu_values),
                "minimum": min(cpu_values),
                "over_80_percent": sum(1 for v in cpu_values if v > 80),
            },
            "memory_usage": {
                "average": sum(memory_values) / len(memory_values),
                "maximum": max(memory_values),
                "minimum": min(memory_values),
                "over_80_percent": sum(1 for v in memory_values if v > 80),
            },
            "peak_memory_gb": max(s.memory_used_gb for s in self.snapshots),
            "process_count_range": {
                "minimum": min(s.process_count for s in self.snapshots),
                "maximum": max(s.process_count for s in self.snapshots),
            },
        }

    def save_detailed_report(self, filename: str = None) -> str:
        """Save detailed monitoring report."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"resource_monitor_report_{timestamp}.json"

        report = {
            "metadata": {
                "monitoring_start": self.snapshots[0].timestamp.isoformat()
                if self.snapshots
                else None,
                "monitoring_end": self.snapshots[-1].timestamp.isoformat()
                if self.snapshots
                else None,
                "interval_seconds": self.interval_seconds,
                "total_snapshots": len(self.snapshots),
            },
            "statistics": self.get_statistics(),
            "snapshots": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "cpu_percent": s.cpu_percent,
                    "memory_percent": s.memory_percent,
                    "memory_used_gb": round(s.memory_used_gb, 2),
                    "disk_percent": s.disk_percent,
                    "process_count": s.process_count,
                    "docker_stats": s.docker_stats,
                }
                for s in self.snapshots
            ],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"📄 Resource monitoring report saved to: {filename}")
        return filename


class LogMonitor:
    """Monitors application logs for errors and warnings."""

    def __init__(self, log_files: list[str] = None):
        self.log_files = log_files or []
        self.error_count = 0
        self.warning_count = 0
        self.critical_errors = []
        self.monitoring = False

    async def monitor_logs(self) -> None:
        """Monitor log files for errors and warnings."""
        self.monitoring = True
        logger.info(f"📋 Starting log monitoring for {len(self.log_files)} files")

        # This is a simplified version - in production you'd use proper log tailing
        initial_positions = {}

        for log_file in self.log_files:
            try:
                if os.path.exists(log_file):
                    with open(log_file) as f:
                        f.seek(0, 2)  # Go to end of file
                        initial_positions[log_file] = f.tell()
                else:
                    initial_positions[log_file] = 0
            except Exception as e:
                logger.warning(
                    f"⚠️ Could not initialize log monitoring for {log_file}: {e}"
                )

        while self.monitoring:
            try:
                for log_file in self.log_files:
                    await self.check_log_file(
                        log_file, initial_positions.get(log_file, 0)
                    )

            except Exception as e:
                logger.error(f"❌ Error monitoring logs: {e}")

            await asyncio.sleep(5)  # Check every 5 seconds

    async def check_log_file(self, log_file: str, last_position: int) -> None:
        """Check a single log file for new entries."""
        try:
            if not os.path.exists(log_file):
                return

            with open(log_file) as f:
                f.seek(last_position)
                new_lines = f.readlines()

                for line in new_lines:
                    line = line.strip().lower()
                    if "error" in line or "exception" in line:
                        self.error_count += 1
                        if "critical" in line or "fatal" in line:
                            self.critical_errors.append(line[:200])

                    elif "warning" in line or "warn" in line:
                        self.warning_count += 1

                # Update position
                last_position = f.tell()

        except Exception as e:
            logger.debug(f"Could not check log file {log_file}: {e}")

    def stop_monitoring(self) -> None:
        """Stop log monitoring."""
        self.monitoring = False
        logger.info("🛑 Stopping log monitoring")

    def get_summary(self) -> dict:
        """Get log monitoring summary."""
        return {
            "files_monitored": len(self.log_files),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "critical_errors": self.critical_errors,
        }


async def run_monitoring_during_stress_test(
    test_duration_minutes: int = 60,
    resource_interval: float = 5.0,
    log_files: list[str] = None,
) -> dict:
    """Run comprehensive monitoring during stress test.

    Args:
        test_duration_minutes: How long to monitor
        resource_interval: Interval between resource snapshots
        log_files: List of log files to monitor

    Returns:
        Combined monitoring report
    """

    # Default log files to monitor
    if log_files is None:
        log_files = [
            "logs/server.log",
            "logs/gaja_server.log",
            "logs/error.log",
            "/var/log/gaja/server.log",  # Docker/VPS location
        ]

    # Initialize monitors
    resource_monitor = ResourceMonitor(interval_seconds=resource_interval)
    log_monitor = LogMonitor(log_files)

    logger.info(f"🚀 Starting {test_duration_minutes}-minute monitoring session")

    # Start monitoring tasks
    monitoring_tasks = [
        asyncio.create_task(resource_monitor.start_monitoring()),
        asyncio.create_task(log_monitor.monitor_logs()),
    ]

    try:
        # Wait for test duration
        await asyncio.sleep(test_duration_minutes * 60)

    finally:
        # Stop monitoring
        resource_monitor.stop_monitoring()
        log_monitor.stop_monitoring()

        # Cancel tasks
        for task in monitoring_tasks:
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*monitoring_tasks, return_exceptions=True)

    # Generate combined report
    resource_stats = resource_monitor.get_statistics()
    log_summary = log_monitor.get_summary()

    # Save detailed resource report
    resource_report_file = resource_monitor.save_detailed_report()

    combined_report = {
        "monitoring_summary": {
            "duration_minutes": test_duration_minutes,
            "resource_snapshots": len(resource_monitor.snapshots),
            "resource_report_file": resource_report_file,
        },
        "resource_usage": resource_stats,
        "log_monitoring": log_summary,
        "alerts": [],
    }

    # Generate alerts
    if resource_stats.get("cpu_usage", {}).get("maximum", 0) > 90:
        combined_report["alerts"].append("🚨 CPU usage exceeded 90%")

    if resource_stats.get("memory_usage", {}).get("maximum", 0) > 90:
        combined_report["alerts"].append("🚨 Memory usage exceeded 90%")

    if log_summary.get("critical_errors", []):
        combined_report["alerts"].append(
            f"🚨 {len(log_summary['critical_errors'])} critical errors detected"
        )

    if log_summary.get("error_count", 0) > 50:
        combined_report["alerts"].append(
            f"🚨 High error count: {log_summary['error_count']}"
        )

    logger.info("📊 Monitoring completed")
    logger.info(
        f"CPU peak: {resource_stats.get('cpu_usage', {}).get('maximum', 0):.1f}%"
    )
    logger.info(
        f"Memory peak: {resource_stats.get('memory_usage', {}).get('maximum', 0):.1f}%"
    )
    logger.info(
        f"Errors: {log_summary.get('error_count', 0)}, Warnings: {log_summary.get('warning_count', 0)}"
    )

    return combined_report


if __name__ == "__main__":
    """Run monitoring standalone."""

    async def main():
        # Default 5-minute test run
        report = await run_monitoring_during_stress_test(test_duration_minutes=5)

        print("\n" + "=" * 60)
        print("🔍 MONITORING SUMMARY")
        print("=" * 60)

        resource_usage = report.get("resource_usage", {})
        log_monitoring = report.get("log_monitoring", {})

        print(f"Duration: {report['monitoring_summary']['duration_minutes']} minutes")
        print(f"Snapshots: {report['monitoring_summary']['resource_snapshots']}")

        if resource_usage:
            cpu = resource_usage.get("cpu_usage", {})
            memory = resource_usage.get("memory_usage", {})

            print(
                f"CPU - Avg: {cpu.get('average', 0):.1f}%, Peak: {cpu.get('maximum', 0):.1f}%"
            )
            print(
                f"Memory - Avg: {memory.get('average', 0):.1f}%, Peak: {memory.get('maximum', 0):.1f}%"
            )
            print(
                f"Peak Memory Usage: {resource_usage.get('peak_memory_gb', 0):.2f} GB"
            )

        print(f"Log Errors: {log_monitoring.get('error_count', 0)}")
        print(f"Log Warnings: {log_monitoring.get('warning_count', 0)}")

        alerts = report.get("alerts", [])
        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("\n✅ No alerts - system running normally")

    asyncio.run(main())
