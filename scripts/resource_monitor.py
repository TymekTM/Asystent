#!/usr/bin/env python3
"""
Resource Monitor for GAJA Server
Monitors CPU, memory, GPU, disk usage and provides alerts
"""

import asyncio
import json
import logging
import os
import psutil
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/data/logs/resource_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Comprehensive resource monitoring for Docker container"""
    
    def __init__(self):
        self.data_dir = Path("/app/data")
        self.metrics_db = self.data_dir / "metrics.db"
        self.alert_thresholds = {
            'cpu_percent': 85.0,
            'memory_percent': 90.0,
            'disk_percent': 95.0,
            'gpu_memory_percent': 95.0,
            'gpu_utilization': 90.0
        }
        self.init_database()
    
    def init_database(self):
        """Initialize metrics database"""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS resource_metrics (
                        timestamp DATETIME PRIMARY KEY,
                        cpu_percent REAL,
                        memory_percent REAL,
                        memory_used_mb REAL,
                        disk_percent REAL,
                        disk_used_gb REAL,
                        gpu_utilization REAL,
                        gpu_memory_percent REAL,
                        gpu_memory_used_mb REAL,
                        network_bytes_sent INTEGER,
                        network_bytes_recv INTEGER,
                        process_count INTEGER,
                        load_average_1m REAL
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        timestamp DATETIME PRIMARY KEY,
                        alert_type TEXT,
                        message TEXT,
                        severity TEXT,
                        value REAL
                    )
                ''')
                conn.commit()
                logger.info("Metrics database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def get_cpu_metrics(self) -> Dict:
        """Get CPU usage metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0.0
            cpu_count = psutil.cpu_count()
            
            return {
                'cpu_percent': cpu_percent,
                'load_average_1m': load_avg,
                'cpu_count': cpu_count
            }
        except Exception as e:
            logger.error(f"Failed to get CPU metrics: {e}")
            return {'cpu_percent': 0.0, 'load_average_1m': 0.0, 'cpu_count': 1}
    
    def get_memory_metrics(self) -> Dict:
        """Get memory usage metrics"""
        try:
            memory = psutil.virtual_memory()
            return {
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / (1024 * 1024),
                'memory_total_mb': memory.total / (1024 * 1024),
                'memory_available_mb': memory.available / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Failed to get memory metrics: {e}")
            return {'memory_percent': 0.0, 'memory_used_mb': 0.0}
    
    def get_disk_metrics(self) -> Dict:
        """Get disk usage metrics"""
        try:
            disk = psutil.disk_usage('/app/data')
            return {
                'disk_percent': (disk.used / disk.total) * 100,
                'disk_used_gb': disk.used / (1024 * 1024 * 1024),
                'disk_total_gb': disk.total / (1024 * 1024 * 1024),
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Failed to get disk metrics: {e}")
            return {'disk_percent': 0.0, 'disk_used_gb': 0.0}
    
    def get_gpu_metrics(self) -> Dict:
        """Get GPU metrics using nvidia-smi"""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpu_data = []
                
                for line in lines:
                    if line.strip():
                        parts = [x.strip() for x in line.split(',')]
                        if len(parts) >= 4:
                            utilization = float(parts[0]) if parts[0] != 'N/A' else 0.0
                            memory_used = float(parts[1]) if parts[1] != 'N/A' else 0.0
                            memory_total = float(parts[2]) if parts[2] != 'N/A' else 1.0
                            temperature = float(parts[3]) if parts[3] != 'N/A' else 0.0
                            
                            memory_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0.0
                            
                            gpu_data.append({
                                'utilization': utilization,
                                'memory_used_mb': memory_used,
                                'memory_total_mb': memory_total,
                                'memory_percent': memory_percent,
                                'temperature': temperature
                            })
                
                if gpu_data:
                    # Return primary GPU metrics
                    primary_gpu = gpu_data[0]
                    return {
                        'gpu_utilization': primary_gpu['utilization'],
                        'gpu_memory_percent': primary_gpu['memory_percent'],
                        'gpu_memory_used_mb': primary_gpu['memory_used_mb'],
                        'gpu_temperature': primary_gpu['temperature'],
                        'gpu_count': len(gpu_data)
                    }
            
            return {'gpu_utilization': 0.0, 'gpu_memory_percent': 0.0, 'gpu_memory_used_mb': 0.0}
            
        except Exception as e:
            logger.debug(f"GPU metrics not available: {e}")
            return {'gpu_utilization': 0.0, 'gpu_memory_percent': 0.0, 'gpu_memory_used_mb': 0.0}
    
    def get_network_metrics(self) -> Dict:
        """Get network usage metrics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv,
                'network_packets_sent': net_io.packets_sent,
                'network_packets_recv': net_io.packets_recv
            }
        except Exception as e:
            logger.error(f"Failed to get network metrics: {e}")
            return {'network_bytes_sent': 0, 'network_bytes_recv': 0}
    
    def get_process_metrics(self) -> Dict:
        """Get process-related metrics"""
        try:
            process_count = len(psutil.pids())
            
            # Find GAJA server process
            gaja_process = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cmdline'] and any('server_main.py' in cmd for cmd in proc.info['cmdline']):
                        gaja_process = proc.info
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            result = {
                'process_count': process_count,
                'gaja_process_found': gaja_process is not None
            }
            
            if gaja_process:
                result.update({
                    'gaja_pid': gaja_process['pid'],
                    'gaja_cpu_percent': gaja_process['cpu_percent'],
                    'gaja_memory_percent': gaja_process['memory_percent']
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get process metrics: {e}")
            return {'process_count': 0, 'gaja_process_found': False}
    
    def check_alerts(self, metrics: Dict):
        """Check for alert conditions and log them"""
        alerts = []
        
        # CPU alert
        if metrics.get('cpu_percent', 0) > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'message': f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                'severity': 'warning',
                'value': metrics['cpu_percent']
            })
        
        # Memory alert
        if metrics.get('memory_percent', 0) > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'message': f"High memory usage: {metrics['memory_percent']:.1f}%",
                'severity': 'critical',
                'value': metrics['memory_percent']
            })
        
        # Disk alert
        if metrics.get('disk_percent', 0) > self.alert_thresholds['disk_percent']:
            alerts.append({
                'type': 'disk_full',
                'message': f"Disk almost full: {metrics['disk_percent']:.1f}%",
                'severity': 'critical',
                'value': metrics['disk_percent']
            })
        
        # GPU alerts
        if metrics.get('gpu_memory_percent', 0) > self.alert_thresholds['gpu_memory_percent']:
            alerts.append({
                'type': 'gpu_memory_high',
                'message': f"High GPU memory usage: {metrics['gpu_memory_percent']:.1f}%",
                'severity': 'warning',
                'value': metrics['gpu_memory_percent']
            })
        
        # Log alerts
        for alert in alerts:
            logger.warning(f"ALERT: {alert['message']}")
            self.save_alert(alert)
    
    def save_alert(self, alert: Dict):
        """Save alert to database"""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                conn.execute('''
                    INSERT INTO alerts (timestamp, alert_type, message, severity, value)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    alert['type'],
                    alert['message'],
                    alert['severity'],
                    alert['value']
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
    
    def save_metrics(self, metrics: Dict):
        """Save metrics to database"""
        try:
            with sqlite3.connect(self.metrics_db) as conn:
                conn.execute('''
                    INSERT INTO resource_metrics (
                        timestamp, cpu_percent, memory_percent, memory_used_mb,
                        disk_percent, disk_used_gb, gpu_utilization, gpu_memory_percent,
                        gpu_memory_used_mb, network_bytes_sent, network_bytes_recv,
                        process_count, load_average_1m
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    metrics.get('cpu_percent', 0),
                    metrics.get('memory_percent', 0),
                    metrics.get('memory_used_mb', 0),
                    metrics.get('disk_percent', 0),
                    metrics.get('disk_used_gb', 0),
                    metrics.get('gpu_utilization', 0),
                    metrics.get('gpu_memory_percent', 0),
                    metrics.get('gpu_memory_used_mb', 0),
                    metrics.get('network_bytes_sent', 0),
                    metrics.get('network_bytes_recv', 0),
                    metrics.get('process_count', 0),
                    metrics.get('load_average_1m', 0)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def cleanup_old_metrics(self):
        """Remove old metrics data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            with sqlite3.connect(self.metrics_db) as conn:
                conn.execute('DELETE FROM resource_metrics WHERE timestamp < ?', (cutoff_date.isoformat(),))
                conn.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_date.isoformat(),))
                conn.commit()
                logger.info("Old metrics cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
    
    async def collect_metrics(self):
        """Collect all metrics"""
        try:
            metrics = {}
            
            # Collect all metrics
            metrics.update(self.get_cpu_metrics())
            metrics.update(self.get_memory_metrics())
            metrics.update(self.get_disk_metrics())
            metrics.update(self.get_gpu_metrics())
            metrics.update(self.get_network_metrics())
            metrics.update(self.get_process_metrics())
            
            # Check for alerts
            self.check_alerts(metrics)
            
            # Save to database
            self.save_metrics(metrics)
            
            # Log summary
            logger.info(f"Metrics: CPU {metrics.get('cpu_percent', 0):.1f}%, "
                       f"RAM {metrics.get('memory_percent', 0):.1f}%, "
                       f"Disk {metrics.get('disk_percent', 0):.1f}%, "
                       f"GPU {metrics.get('gpu_utilization', 0):.1f}%")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}
    
    async def run(self):
        """Main monitoring loop"""
        logger.info("Starting resource monitor")
        cleanup_counter = 0
        
        while True:
            try:
                await self.collect_metrics()
                
                # Cleanup old metrics every hour (720 cycles of 5 seconds)
                cleanup_counter += 1
                if cleanup_counter >= 720:
                    self.cleanup_old_metrics()
                    cleanup_counter = 0
                
                await asyncio.sleep(5)  # Collect metrics every 5 seconds
                
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error


if __name__ == "__main__":
    monitor = ResourceMonitor()
    asyncio.run(monitor.run())
