#!/usr/bin/env python3
"""Server Configuration and Logging Optimization.

This script addresses the verbose logging issues mentioned in the server logs:
1. Migrates from deprecated @app.on_event to lifespan handlers
2. Optimizes logging configuration for production
3. Implements proper log filtering after initialization
"""

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger


class ServerOptimizer:
    """Handles server configuration optimization."""

    def __init__(self):
        self.optimizations_applied = []

    def check_current_server_config(self) -> dict[str, Any]:
        """Analyze current server configuration."""
        server_file = Path("server/server_main.py")

        issues = {
            "deprecated_on_event": False,
            "verbose_health_logging": False,
            "missing_log_filtering": False,
            "no_structured_logging": False,
        }

        if server_file.exists():
            content = server_file.read_text(encoding="utf-8")

            # Check for deprecated patterns
            if "@app.on_event" in content:
                issues["deprecated_on_event"] = True

            if "INFO:     127.0.0.1:" in content:
                issues["verbose_health_logging"] = True

            if "logging.getLogger" not in content:
                issues["missing_log_filtering"] = True

            if "structured" not in content.lower():
                issues["no_structured_logging"] = True

        return issues

    def generate_optimized_lifespan(self) -> str:
        """Generate optimized lifespan handler code."""
        return '''
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with optimized logging."""
    # Startup
    global server_app

    # Configure logging for production
    setup_production_logging()

    logger.info("Starting GAJA Assistant Server...")
    server_app = ServerApp()
    await server_app.initialize()
    set_server_app(server_app)
    logger.success("Server initialization completed")

    yield

    # Shutdown
    logger.info("Shutting down GAJA Assistant Server...")
    if server_app:
        await server_app.cleanup()
    logger.info("Server shutdown complete")


def setup_production_logging():
    """Configure optimized logging for production."""
    # Remove default logger
    logger.remove()

    # Add structured logging with filtering
    logger.add(
        "logs/server_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        filter=lambda record: not is_health_check_spam(record)
    )

    # Console logging with reduced verbosity
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
        filter=lambda record: not is_health_check_spam(record) and record["level"].no >= 20
    )

    # Suppress external library noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("websockets.server").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


def is_health_check_spam(record) -> bool:
    """Filter out repetitive health check logs."""
    message = record.get("message", "")

    # Filter health check access logs
    if "GET /health HTTP/1.1" in message and "200 OK" in message:
        return True

    # Filter repetitive startup messages after initial load
    spam_patterns = [
        "Waiting for application startup",
        "Application startup complete",
        "Uvicorn running on"
    ]

    return any(pattern in message for pattern in spam_patterns)


# Create FastAPI app with lifespan
app = FastAPI(
    title="GAJA Assistant Server",
    description="AI Assistant with Function Calling",
    version="2.0.0",
    lifespan=lifespan  # Use new lifespan instead of @app.on_event
)
'''

    def generate_health_endpoint_optimization(self) -> str:
        """Generate optimized health endpoint with minimal logging."""
        return '''
@app.get("/health")
async def health_check():
    """Optimized health check with minimal logging."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "function_calling": "enabled" if server_app and hasattr(server_app, 'function_calling_system') else "disabled"
    }

@app.get("/healthz")
async def kubernetes_health_check():
    """Kubernetes-style health check (silent)."""
    return {"status": "ok"}

@app.get("/api/v1/healthz")
async def api_health_check():
    """API health check with function calling status."""
    if not server_app:
        raise HTTPException(status_code=503, detail="Server not initialized")

    return {
        "status": "healthy",
        "services": {
            "ai_module": "ok" if hasattr(server_app, 'ai_module') else "unavailable",
            "function_calling": "ok" if hasattr(server_app, 'function_calling_system') else "unavailable",
            "database": "ok" if hasattr(server_app, 'database_manager') else "unavailable",
            "plugins": "ok" if hasattr(server_app, 'plugin_manager') else "unavailable"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
'''

    def create_logging_config(self) -> str:
        """Create optimized logging configuration."""
        return '''
"""
Optimized Logging Configuration for GAJA Assistant Server

This configuration reduces verbose logging while maintaining essential information.
"""

import sys
from datetime import datetime
from loguru import logger


class ProductionLoggingConfig:
    """Production-ready logging configuration."""

    @staticmethod
    def setup():
        """Setup optimized logging for production use."""
        # Remove all default handlers
        logger.remove()

        # File logging with rotation
        logger.add(
            "logs/gaja_server_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
            filter=ProductionLoggingConfig.filter_spam,
            compression="zip"
        )

        # Console logging - errors and important info only
        logger.add(
            sys.stderr,
            level="WARNING",  # Only warnings and errors to console
            format="<red>{time:HH:mm:ss}</red> | <level>{level: <8}</level> | <level>{message}</level>",
            filter=ProductionLoggingConfig.filter_console
        )

        # Startup/shutdown events - separate file
        logger.add(
            "logs/gaja_lifecycle.log",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
            filter=lambda record: ProductionLoggingConfig.is_lifecycle_event(record),
            rotation="10 MB"
        )

        # Suppress external libraries
        ProductionLoggingConfig.suppress_external_noise()

    @staticmethod
    def filter_spam(record) -> bool:
        """Filter out repetitive/spam logs."""
        message = record.get("message", "")

        # Health check spam
        if "GET /health HTTP/1.1" in message:
            return False

        # Uvicorn access logs for health checks
        if "127.0.0.1" in message and "200 OK" in message:
            return False

        return True

    @staticmethod
    def filter_console(record) -> bool:
        """Filter console output to essential messages only."""
        message = record.get("message", "")
        level = record.get("level", {}).get("name", "")

        # Allow errors and warnings
        if level in ["ERROR", "WARNING", "CRITICAL"]:
            return True

        # Allow important startup/shutdown messages
        important_keywords = [
            "Starting GAJA",
            "Server initialization completed",
            "Function calling system initialized",
            "Server startup complete",
            "Server shutdown complete",
            "Plugin",
            "AI module initialized"
        ]

        return any(keyword in message for keyword in important_keywords)

    @staticmethod
    def is_lifecycle_event(record) -> bool:
        """Check if record is a lifecycle event."""
        message = record.get("message", "")
        lifecycle_keywords = [
            "Starting GAJA",
            "initialization",
            "startup",
            "shutdown",
            "Plugin loaded",
            "Plugin unloaded"
        ]
        return any(keyword in message for keyword in lifecycle_keywords)

    @staticmethod
    def suppress_external_noise():
        """Suppress noisy external library logs."""
        noisy_loggers = [
            "uvicorn.access",
            "uvicorn.error",
            "websockets.server",
            "websockets.protocol",
            "aiohttp.access",
            "aiofiles",
            "multipart.multipart"
        ]

        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
'''

    async def generate_optimization_report(self) -> dict[str, Any]:
        """Generate optimization recommendations."""
        issues = self.check_current_server_config()

        report = {
            "current_issues": issues,
            "optimizations": {
                "lifespan_migration": {
                    "required": issues["deprecated_on_event"],
                    "description": "Migrate from @app.on_event to lifespan handlers",
                    "impact": "Removes deprecation warnings",
                },
                "health_check_optimization": {
                    "required": issues["verbose_health_logging"],
                    "description": "Reduce health check logging frequency",
                    "impact": "Significantly reduces log volume",
                },
                "log_filtering": {
                    "required": issues["missing_log_filtering"],
                    "description": "Implement smart log filtering",
                    "impact": "Removes repetitive logs while keeping essentials",
                },
                "structured_logging": {
                    "required": issues["no_structured_logging"],
                    "description": "Add structured logging format",
                    "impact": "Better log analysis and monitoring",
                },
            },
            "recommendations": [
                "Use /healthz endpoint for monitoring instead of /health to reduce logs",
                "Implement log rotation with compression",
                "Add separate lifecycle event logging",
                "Filter external library noise",
                "Use WARNING level for console in production",
            ],
        }

        return report

    async def create_optimized_files(self):
        """Create optimized configuration files."""
        logger.info("📝 Creating optimized server configuration files...")

        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Generate optimized logging config
        logging_config = self.create_logging_config()
        config_file = Path("server_logging_config.py")
        config_file.write_text(logging_config, encoding="utf-8")
        logger.info(f"✅ Created: {config_file}")

        # Generate example optimized server
        optimized_server = f"""
# Example of optimized server configuration
from datetime import datetime
from contextlib import asynccontextmanager
import sys
import logging
from fastapi import FastAPI, HTTPException
from loguru import logger

{self.generate_optimized_lifespan()}

{self.generate_health_endpoint_optimization()}
"""

        example_file = Path("server_optimized_example.py")
        example_file.write_text(optimized_server, encoding="utf-8")
        logger.info(f"✅ Created: {example_file}")

        self.optimizations_applied.extend(
            [
                "Created optimized logging configuration",
                "Generated lifespan handler example",
                "Created health endpoint optimization",
                "Setup log filtering and rotation",
            ]
        )


async def main():
    """Main optimization execution."""
    logger.info("🔧 GAJA Server Optimization Utility")
    logger.info("=" * 50)

    optimizer = ServerOptimizer()

    # Generate optimization report
    report = await optimizer.generate_optimization_report()

    logger.info("📊 Current Server Analysis:")
    for issue, present in report["current_issues"].items():
        status = "❌ NEEDS FIX" if present else "✅ OK"
        logger.info(f"   {issue}: {status}")

    logger.info("\n🛠  Recommended Optimizations:")
    for opt_name, opt_data in report["optimizations"].items():
        required = "🔴 REQUIRED" if opt_data["required"] else "🟢 OPTIONAL"
        logger.info(f"   {opt_name}: {required}")
        logger.info(f"      {opt_data['description']}")
        logger.info(f"      Impact: {opt_data['impact']}")

    # Create optimized files
    await optimizer.create_optimized_files()

    logger.info("\n📋 Optimization Summary:")
    for optimization in optimizer.optimizations_applied:
        logger.info(f"   ✅ {optimization}")

    logger.info("\n🎯 Next Steps:")
    logger.info("   1. Review generated server_optimized_example.py")
    logger.info("   2. Apply lifespan handler migration to server_main.py")
    logger.info("   3. Import and use ProductionLoggingConfig.setup()")
    logger.info("   4. Test with reduced logging verbosity")
    logger.info("   5. Monitor function calling system performance")

    # Save report
    import json

    report_file = Path("server_optimization_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"📁 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())
