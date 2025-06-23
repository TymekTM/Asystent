#!/usr/bin/env python3
"""
GAJA Overlay Comprehensive Debug Tool
Diagnozuje wszystkie aspekty overlay: procesy, porty, API, okna, logi, komunikację

Following AGENTS.md guidelines:
- Async-first architecture
- Comprehensive test coverage
- Clear logging and error handling
- Modular design
"""

import asyncio
import ctypes
import ctypes.wintypes as wintypes
import json
import logging
import socket
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiohttp
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CLIENT_PORT = 5001
DEFAULT_SERVER_PORT = 5000
OVERLAY_PROCESS_NAMES = ["gaja-overlay.exe", "gaja-overlay", "tauri"]
CLIENT_PROCESS_NAMES = ["python.exe", "python", "client_main.py"]
SERVER_PROCESS_NAMES = ["python.exe", "python", "server_main.py"]
EXPECTED_ENDPOINTS = [
    "/api/status",
    "/api/overlay/show",
    "/api/overlay/hide",
    "/api/overlay/status",
    "/api/test/wakeword",
]


class OverlayComprehensiveDebugger:
    """Comprehensive debugger for GAJA overlay system.

    Tests all components: processes, networking, API, windows, communication.
    """

    def __init__(self):
        """Initialize the comprehensive debugger."""
        self.client_port = DEFAULT_CLIENT_PORT
        self.server_port = DEFAULT_SERVER_PORT
        self.session: Optional[aiohttp.ClientSession] = None
        self.debug_results: dict[str, Any] = {}

    async def run_full_diagnostic(self) -> dict[str, Any]:
        """Run complete diagnostic of overlay system.

        Returns comprehensive results dictionary.
        """
        print("🔍 GAJA Overlay Comprehensive Diagnostic Starting...")
        print("=" * 60)

        # Initialize results structure
        self.debug_results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {},
            "processes": {},
            "networking": {},
            "api_tests": {},
            "window_analysis": {},
            "file_system": {},
            "communication": {},
            "recommendations": [],
        }

        try:
            # Step 1: System information
            await self._analyze_system_info()

            # Step 2: Process analysis
            await self._analyze_processes()

            # Step 3: Network connectivity
            await self._analyze_networking()

            # Step 4: API endpoint testing
            await self._test_api_endpoints()

            # Step 5: Window system analysis
            await self._analyze_windows()

            # Step 6: File system analysis
            await self._analyze_file_system()

            # Step 7: Communication flow testing
            await self._test_communication_flow()

            # Step 8: Generate recommendations
            self._generate_recommendations()

        except Exception as e:
            logger.error(f"Diagnostic error: {e}")
            self.debug_results["critical_error"] = str(e)

        finally:
            if self.session:
                await self.session.close()

        # Print results
        self._print_results()

        return self.debug_results

    async def _analyze_system_info(self) -> None:
        """Analyze system information."""
        print("\n1️⃣ System Information Analysis")
        print("-" * 40)

        system_info = {
            "platform": sys.platform,
            "python_version": sys.version,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage(".").percent,
            "boot_time": psutil.boot_time(),
        }

        self.debug_results["system_info"] = system_info
        print(f"✅ Platform: {system_info['platform']}")
        print(f"✅ Python: {system_info['python_version'].split()[0]}")
        print(f"✅ CPU cores: {system_info['cpu_count']}")
        print(
            f"✅ Memory: {system_info['memory_available'] / (1024**3):.1f}GB available"
        )

    async def _analyze_processes(self) -> None:
        """Analyze all relevant processes."""
        print("\n2️⃣ Process Analysis")
        print("-" * 40)

        processes = {"overlay": [], "client": [], "server": [], "all_python": []}

        # Find all processes
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "status", "cpu_percent", "memory_info"]
        ):
            try:
                proc_info = proc.info
                proc_name = proc_info["name"].lower()
                cmdline = " ".join(proc_info["cmdline"]) if proc_info["cmdline"] else ""

                # Categorize processes
                if any(name in proc_name for name in ["gaja-overlay", "tauri"]):
                    processes["overlay"].append(proc_info)

                if "python" in proc_name and (
                    "client_main" in cmdline or "gaja" in cmdline.lower()
                ):
                    processes["client"].append(proc_info)

                if "python" in proc_name and (
                    "server_main" in cmdline or "manage.py" in cmdline
                ):
                    processes["server"].append(proc_info)

                if "python" in proc_name:
                    processes["all_python"].append(
                        {
                            "pid": proc_info["pid"],
                            "cmdline": cmdline[:100] + "..."
                            if len(cmdline) > 100
                            else cmdline,
                        }
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.debug_results["processes"] = processes

        # Print findings
        print(f"🔍 Overlay processes: {len(processes['overlay'])}")
        for proc in processes["overlay"]:
            print(f"   PID {proc['pid']}: {proc['name']} - {proc['status']}")

        print(f"🔍 Client processes: {len(processes['client'])}")
        for proc in processes["client"]:
            print(f"   PID {proc['pid']}: {proc['cmdline'][:50]}...")

        print(f"🔍 Server processes: {len(processes['server'])}")
        for proc in processes["server"]:
            print(f"   PID {proc['pid']}: {proc['cmdline'][:50]}...")

        print(f"🔍 Total Python processes: {len(processes['all_python'])}")

    async def _analyze_networking(self) -> None:
        """Analyze network connectivity and port usage."""
        print("\n3️⃣ Network Analysis")
        print("-" * 40)

        networking = {"port_status": {}, "connections": [], "listening_ports": []}

        # Check specific ports
        for port_name, port in [
            ("client", self.client_port),
            ("server", self.server_port),
        ]:
            is_open = self._check_port(port)
            networking["port_status"][f"{port_name}_port_{port}"] = is_open
            print(f"🔌 Port {port} ({port_name}): {'OPEN' if is_open else 'CLOSED'}")

        # Get all listening ports
        try:
            connections = psutil.net_connections(kind="inet")
            for conn in connections:
                if conn.status == "LISTEN":
                    networking["listening_ports"].append(
                        {
                            "port": conn.laddr.port,
                            "address": conn.laddr.ip,
                            "pid": conn.pid,
                        }
                    )

            # Filter for relevant ports
            relevant_ports = [
                p
                for p in networking["listening_ports"]
                if p["port"] in [self.client_port, self.server_port, 3000, 8000, 8080]
            ]

            print("🔍 Relevant listening ports:")
            for port_info in relevant_ports:
                print(f"   Port {port_info['port']}: PID {port_info['pid']}")

        except Exception as e:
            print(f"❌ Error getting network connections: {e}")

        self.debug_results["networking"] = networking

    def _check_port(self, port: int) -> bool:
        """Check if port is open and listening."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False

    async def _test_api_endpoints(self) -> None:
        """Test all API endpoints thoroughly."""
        print("\n4️⃣ API Endpoint Testing")
        print("-" * 40)

        api_results = {
            "client_api": {},
            "server_api": {},
            "response_times": {},
            "errors": [],
        }

        # Test client API (port 5001)
        print("🔍 Testing Client API (port 5001)...")
        await self._test_port_endpoints(self.client_port, "client_api", api_results)

        # Test server API (port 5000)
        print("🔍 Testing Server API (port 5000)...")
        await self._test_port_endpoints(self.server_port, "server_api", api_results)

        self.debug_results["api_tests"] = api_results

    async def _test_port_endpoints(
        self, port: int, api_key: str, results: dict
    ) -> None:
        """Test endpoints on specific port."""
        base_url = f"http://localhost:{port}"

        if not self.session:
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            self.session = aiohttp.ClientSession(timeout=timeout)

        results[api_key] = {}

        for endpoint in EXPECTED_ENDPOINTS:
            try:
                start_time = time.time()
                async with self.session.get(f"{base_url}{endpoint}") as response:
                    response_time = time.time() - start_time

                    result = {
                        "status": response.status,
                        "response_time": response_time,
                        "headers": dict(response.headers),
                        "accessible": True,
                    }

                    if response.status == 200:
                        try:
                            data = await response.json()
                            result["data"] = data
                            print(
                                f"   ✅ {endpoint}: {response.status} ({response_time:.2f}s)"
                            )
                        except Exception:
                            result["data"] = await response.text()
                            print(f"   ✅ {endpoint}: {response.status} (text response)")
                    else:
                        print(f"   ❌ {endpoint}: {response.status}")

                    results[api_key][endpoint] = result

            except asyncio.TimeoutError:
                print(f"   ⏱️ {endpoint}: TIMEOUT")
                results[api_key][endpoint] = {"accessible": False, "error": "timeout"}

            except Exception as e:
                print(f"   ❌ {endpoint}: ERROR - {e}")
                results[api_key][endpoint] = {"accessible": False, "error": str(e)}

    async def _analyze_windows(self) -> None:
        """Analyze overlay windows using Windows API."""
        print("\n5️⃣ Window System Analysis")
        print("-" * 40)

        window_analysis = {
            "overlay_windows": [],
            "all_gaja_windows": [],
            "window_properties": {},
        }

        try:
            # Find all windows
            def enum_windows_callback(hwnd, lParam):
                window_text = ctypes.create_unicode_buffer(512)
                ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
                window_title = window_text.value

                if window_title and (
                    "gaja" in window_title.lower() or "overlay" in window_title.lower()
                ):
                    window_info = self._get_detailed_window_info(hwnd, window_title)
                    window_analysis["all_gaja_windows"].append(window_info)

                    if "overlay" in window_title.lower():
                        window_analysis["overlay_windows"].append(window_info)

                return True

            enum_windows_proc = ctypes.WINFUNCTYPE(
                ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
            )
            ctypes.windll.user32.EnumWindows(
                enum_windows_proc(enum_windows_callback), 0
            )

            print(f"🔍 Found {len(window_analysis['overlay_windows'])} overlay windows")
            print(
                f"🔍 Found {len(window_analysis['all_gaja_windows'])} total GAJA windows"
            )

            for window in window_analysis["overlay_windows"]:
                print(f"   📋 {window['title']} (HWND: {window['hwnd']})")
                print(f"      Visible: {window['visible']}, Alpha: {window['alpha']}")
                print(f"      Position: ({window['x']}, {window['y']})")
                print(f"      Size: {window['width']}x{window['height']}")

        except Exception as e:
            print(f"❌ Window analysis error: {e}")
            window_analysis["error"] = str(e)

        self.debug_results["window_analysis"] = window_analysis

    def _get_detailed_window_info(self, hwnd: int, title: str) -> dict[str, Any]:
        """Get detailed information about a window."""
        try:
            # Get window rect
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))

            # Get window styles
            style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -16)  # GWL_STYLE
            ex_style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, -20)  # GWL_EXSTYLE

            # Check visibility and states
            is_visible = bool(ctypes.windll.user32.IsWindowVisible(hwnd))
            is_iconic = bool(ctypes.windll.user32.IsIconic(hwnd))
            is_zoomed = bool(ctypes.windll.user32.IsZoomed(hwnd))

            # Get opacity
            alpha = ctypes.c_ubyte()
            layered = ctypes.windll.user32.GetLayeredWindowAttributes(
                hwnd, None, ctypes.byref(alpha), None
            )

            return {
                "hwnd": hwnd,
                "title": title,
                "x": rect.left,
                "y": rect.top,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
                "visible": is_visible,
                "minimized": is_iconic,
                "maximized": is_zoomed,
                "style": hex(style),
                "ex_style": hex(ex_style),
                "layered": bool(layered),
                "alpha": alpha.value if layered else None,
            }

        except Exception as e:
            return {"hwnd": hwnd, "title": title, "error": str(e)}

    async def _analyze_file_system(self) -> None:
        """Analyze relevant files and directories."""
        print("\n6️⃣ File System Analysis")
        print("-" * 40)

        file_analysis = {
            "project_structure": {},
            "config_files": {},
            "log_files": {},
            "executables": {},
        }

        # Check project structure
        project_root = Path(".")
        important_paths = [
            "overlay/",
            "client/",
            "server/",
            "gaja_client/",
            "gaja_server/",
            "logs/",
            "client_main.py",
            "server_main.py",
            "manage.py",
        ]

        for path_str in important_paths:
            path = project_root / path_str
            file_analysis["project_structure"][path_str] = {
                "exists": path.exists(),
                "is_file": path.is_file() if path.exists() else None,
                "is_dir": path.is_dir() if path.exists() else None,
                "size": path.stat().st_size
                if path.exists() and path.is_file()
                else None,
            }

            status = "✅" if path.exists() else "❌"
            print(f"   {status} {path_str}")

        # Check for executables
        exe_patterns = ["*.exe", "gaja-overlay*", "tauri*"]
        for pattern in exe_patterns:
            exes = list(project_root.rglob(pattern))
            if exes:
                file_analysis["executables"][pattern] = [str(exe) for exe in exes]
                print(f"   🔍 Found {len(exes)} files matching {pattern}")
                for exe in exes[:3]:  # Show first 3
                    print(f"      {exe}")

        # Check recent log files
        log_dirs = ["logs/", "client/logs/", "gaja_client/logs/", "."]
        for log_dir in log_dirs:
            log_path = project_root / log_dir
            if log_path.exists():
                log_files = list(log_path.glob("*.log"))
                recent_logs = sorted(
                    log_files, key=lambda x: x.stat().st_mtime, reverse=True
                )[:3]
                if recent_logs:
                    file_analysis["log_files"][log_dir] = [
                        str(log) for log in recent_logs
                    ]
                    print(f"   📋 Recent logs in {log_dir}: {len(recent_logs)}")

        self.debug_results["file_system"] = file_analysis

    async def _test_communication_flow(self) -> None:
        """Test end-to-end communication flow."""
        print("\n7️⃣ Communication Flow Testing")
        print("-" * 40)

        comm_results = {
            "client_to_overlay": False,
            "server_to_client": False,
            "full_chain": False,
            "detailed_tests": [],
        }

        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            self.session = aiohttp.ClientSession(timeout=timeout)

        # Test 1: Basic client connection
        try:
            async with self.session.get(
                f"http://localhost:{self.client_port}/api/status"
            ) as response:
                if response.status == 200:
                    comm_results["client_to_overlay"] = True
                    print("   ✅ Client API responding")
                else:
                    print(f"   ❌ Client API error: {response.status}")
        except Exception as e:
            print(f"   ❌ Client connection failed: {e}")

        # Test 2: Overlay show command
        try:
            async with self.session.get(
                f"http://localhost:{self.client_port}/api/overlay/show"
            ) as response:
                result = {
                    "test": "overlay_show",
                    "status": response.status,
                    "success": response.status == 200,
                }
                if response.status == 200:
                    print("   ✅ Overlay show command accepted")
                else:
                    print(f"   ❌ Overlay show failed: {response.status}")
                comm_results["detailed_tests"].append(result)
        except Exception as e:
            print(f"   ❌ Overlay show error: {e}")
            comm_results["detailed_tests"].append(
                {"test": "overlay_show", "error": str(e), "success": False}
            )

        # Test 3: Test wakeword with custom message
        try:
            test_message = "🔍 DIAGNOSTIC TEST - IF YOU SEE THIS, OVERLAY IS WORKING"
            url = f"http://localhost:{self.client_port}/api/test/wakeword?query={test_message}"
            async with self.session.get(url) as response:
                result = {
                    "test": "wakeword_test",
                    "status": response.status,
                    "success": response.status == 200,
                    "message": test_message,
                }
                if response.status == 200:
                    print("   ✅ Test wakeword sent successfully")
                    print(f"   📤 Message: {test_message}")
                else:
                    print(f"   ❌ Test wakeword failed: {response.status}")
                comm_results["detailed_tests"].append(result)
        except Exception as e:
            print(f"   ❌ Test wakeword error: {e}")

        self.debug_results["communication"] = comm_results

    def _generate_recommendations(self) -> None:
        """Generate diagnostic recommendations based on findings."""
        recommendations = []

        # Check processes
        if not self.debug_results["processes"]["overlay"]:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": "No overlay process found",
                    "solution": "Start the overlay process: check if gaja-overlay.exe is built and start the client",
                }
            )

        if not self.debug_results["processes"]["client"]:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": "No client process found",
                    "solution": "Start the client: python client_main.py or python manage.py",
                }
            )

        # Check networking
        client_port_open = self.debug_results["networking"]["port_status"].get(
            f"client_port_{self.client_port}", False
        )
        if not client_port_open:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": f"Client port {self.client_port} not accessible",
                    "solution": "Check if client is running and listening on the correct port",
                }
            )

        # Check API responses
        client_api = self.debug_results["api_tests"].get("client_api", {})
        if not any(result.get("accessible", False) for result in client_api.values()):
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": "No client API endpoints responding",
                    "solution": "Client may be crashed or not properly initialized. Check client logs.",
                }
            )

        # Check windows
        overlay_windows = self.debug_results["window_analysis"].get(
            "overlay_windows", []
        )
        if overlay_windows:
            invisible_windows = [
                w
                for w in overlay_windows
                if not w.get("visible", False) or w.get("alpha", 255) == 0
            ]
            if invisible_windows:
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "issue": "Overlay windows exist but are invisible",
                        "solution": "Run window_diagnostic.py to fix transparency issues",
                    }
                )

        # Communication flow issues
        comm_results = self.debug_results["communication"]
        if not comm_results.get("client_to_overlay", False):
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": "Client-to-overlay communication broken",
                    "solution": "Check client logs, restart client, verify overlay process is responding",
                }
            )

        self.debug_results["recommendations"] = recommendations

    def _print_results(self) -> None:
        """Print comprehensive diagnostic results."""
        print("\n" + "=" * 60)
        print("🎯 DIAGNOSTIC SUMMARY")
        print("=" * 60)

        # Critical issues
        recommendations = self.debug_results.get("recommendations", [])
        high_priority = [r for r in recommendations if r["priority"] == "HIGH"]

        if high_priority:
            print("🚨 CRITICAL ISSUES FOUND:")
            for i, rec in enumerate(high_priority, 1):
                print(f"{i}. {rec['issue']}")
                print(f"   💡 Solution: {rec['solution']}")
                print()
        else:
            print("✅ No critical issues detected")

        # System status summary
        processes = self.debug_results["processes"]
        print("📊 SYSTEM STATUS:")
        print(f"   Overlay processes: {len(processes.get('overlay', []))}")
        print(f"   Client processes: {len(processes.get('client', []))}")
        print(f"   Server processes: {len(processes.get('server', []))}")

        networking = self.debug_results["networking"]
        client_port_status = networking["port_status"].get(
            f"client_port_{self.client_port}", False
        )
        print(
            f"   Client port {self.client_port}: {'OPEN' if client_port_status else 'CLOSED'}"
        )

        windows = self.debug_results["window_analysis"]
        overlay_count = len(windows.get("overlay_windows", []))
        print(f"   Overlay windows: {overlay_count}")

        print("\n📋 Full diagnostic data saved to debug results")
        print(f"   Timestamp: {self.debug_results['timestamp']}")


async def main():
    """Main diagnostic entry point."""
    debugger = OverlayComprehensiveDebugger()

    try:
        results = await debugger.run_full_diagnostic()

        # Save results to file
        results_file = Path("overlay_debug_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n💾 Results saved to: {results_file}")

        return results

    except KeyboardInterrupt:
        print("\n⏹️ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        logger.exception("Diagnostic error")


if __name__ == "__main__":
    asyncio.run(main())
