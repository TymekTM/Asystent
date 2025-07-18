#!/usr/bin/env python3
"""
GAJA Assistant - Security Audit and Remediation System
Kompleksowy system audytu bezpieczeństwa i naprawy wykrytych problemów.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from loguru import logger


class SecurityAuditor:
    """Główny audytor bezpieczeństwa systemu."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.audit_results = {}
        self.critical_issues = []
        self.high_issues = []
        self.medium_issues = []
        self.low_issues = []

    async def run_full_audit(self) -> dict[str, Any]:
        """Przeprowadza pełny audyt bezpieczeństwa."""
        logger.info("🔍 Starting comprehensive security audit...")

        audit_tasks = [
            self.audit_authentication(),
            self.audit_input_validation(),
            self.audit_api_security(),
            self.audit_database_security(),
            self.audit_configuration_security(),
            self.audit_dependency_security(),
            self.audit_file_permissions(),
            self.audit_logging_security(),
            self.audit_network_security(),
            self.audit_code_quality(),
        ]

        results = await asyncio.gather(*audit_tasks, return_exceptions=True)

        # Kompiluj wyniki
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Audit task {i} failed: {result}")
            else:
                self.audit_results.update(result)

        # Klasyfikuj problemy
        self._classify_issues()

        # Generuj raport
        return self._generate_audit_report()

    async def audit_authentication(self) -> dict[str, Any]:
        """Audyt systemu autentyfikacji."""
        logger.info("🔐 Auditing authentication system...")

        issues = []
        recommendations = []

        # Sprawdź mock users w kodzie
        routes_file = self.project_root / "server" / "api" / "routes.py"
        if routes_file.exists():
            content = routes_file.read_text(encoding="utf-8")

            if "MOCK_USERS" in content:
                issues.append(
                    {
                        "severity": "critical",
                        "type": "hardcoded_credentials",
                        "description": "Mock users with hardcoded credentials found in production code",
                        "file": str(routes_file),
                        "remediation": "Replace mock authentication with secure JWT-based system",
                    }
                )

            if '"password"' in content and '"admin123"' in content:
                issues.append(
                    {
                        "severity": "critical",
                        "type": "weak_default_password",
                        "description": "Weak default password found in code",
                        "file": str(routes_file),
                        "remediation": "Remove hardcoded passwords and implement secure password policies",
                    }
                )

        # Sprawdź konfigurację haseł
        auth_config = self.project_root / "client" / "configs" / "auth_config.json"
        if auth_config.exists():
            try:
                config_data = json.loads(auth_config.read_text())
                for user in config_data.get("users", []):
                    if "password_hash" in user:
                        recommendations.append(
                            "Password hashes found - ensure they use strong hashing algorithm"
                        )
                    if user.get("role") == "super_admin":
                        issues.append(
                            {
                                "severity": "medium",
                                "type": "privileged_account",
                                "description": "Super admin account detected",
                                "file": str(auth_config),
                                "remediation": "Review super admin permissions and implement least privilege principle",
                            }
                        )
            except json.JSONDecodeError:
                issues.append(
                    {
                        "severity": "low",
                        "type": "config_parse_error",
                        "description": "Failed to parse auth configuration",
                        "file": str(auth_config),
                    }
                )

        # Sprawdź JWT implementation
        if not self._check_jwt_security():
            issues.append(
                {
                    "severity": "high",
                    "type": "insecure_jwt",
                    "description": "JWT implementation lacks proper security",
                    "remediation": "Implement secure JWT with proper secret key management and expiration",
                }
            )

        return {
            "authentication_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_input_validation(self) -> dict[str, Any]:
        """Audyt walidacji danych wejściowych."""
        logger.info("🛡️ Auditing input validation...")

        issues = []
        recommendations = []

        # Sprawdź czy istnieje system walidacji
        validator_file = (
            self.project_root / "server" / "security" / "input_validator.py"
        )
        if not validator_file.exists():
            issues.append(
                {
                    "severity": "high",
                    "type": "missing_input_validation",
                    "description": "No comprehensive input validation system found",
                    "remediation": "Implement input validation and sanitization system",
                }
            )

        # Sprawdź API endpoints pod kątem walidacji
        api_files = list(self.project_root.glob("server/api/*.py"))
        for api_file in api_files:
            content = api_file.read_text(encoding="utf-8")

            # Szukaj potencjalnych problemów
            if "request.json" in content and "validate" not in content:
                issues.append(
                    {
                        "severity": "medium",
                        "type": "unvalidated_json_input",
                        "description": f"Unvalidated JSON input in {api_file.name}",
                        "file": str(api_file),
                        "remediation": "Add JSON input validation using Pydantic models",
                    }
                )

            if "sql" in content.lower() and "sanitize" not in content.lower():
                issues.append(
                    {
                        "severity": "high",
                        "type": "potential_sql_injection",
                        "description": f"Potential SQL injection vulnerability in {api_file.name}",
                        "file": str(api_file),
                        "remediation": "Use parameterized queries and input sanitization",
                    }
                )

        return {
            "input_validation_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_api_security(self) -> dict[str, Any]:
        """Audyt bezpieczeństwa API."""
        logger.info("🌐 Auditing API security...")

        issues = []
        recommendations = []

        # Sprawdź konfigurację CORS
        server_config = self.project_root / "server_config.json"
        if server_config.exists():
            try:
                config_data = json.loads(server_config.read_text())

                # Sprawdź host binding
                host = config_data.get("server", {}).get("host")
                if host == "0.0.0.0":
                    issues.append(
                        {
                            "severity": "high",
                            "type": "insecure_host_binding",
                            "description": "Server configured to bind to all interfaces (0.0.0.0)",
                            "file": str(server_config),
                            "remediation": "Change host to 127.0.0.1 for local access or specific IP for production",
                        }
                    )

                # Sprawdź CORS
                cors_origins = config_data.get("security", {}).get("cors_origins", [])
                if "*" in cors_origins:
                    issues.append(
                        {
                            "severity": "critical",
                            "type": "permissive_cors",
                            "description": "CORS configured to allow all origins (*)",
                            "file": str(server_config),
                            "remediation": "Restrict CORS to specific trusted domains",
                        }
                    )

                # Sprawdź SSL
                ssl_config = config_data.get("security", {}).get("ssl", {})
                if not ssl_config.get("enabled", False):
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "ssl_not_enabled",
                            "description": "SSL/TLS not enabled",
                            "file": str(server_config),
                            "remediation": "Enable SSL/TLS for production deployment",
                        }
                    )

            except json.JSONDecodeError:
                issues.append(
                    {
                        "severity": "medium",
                        "type": "config_parse_error",
                        "description": "Failed to parse server configuration",
                        "file": str(server_config),
                    }
                )

        # Sprawdź rate limiting
        if not self._check_rate_limiting():
            issues.append(
                {
                    "severity": "medium",
                    "type": "missing_rate_limiting",
                    "description": "No rate limiting mechanism detected",
                    "remediation": "Implement rate limiting to prevent abuse",
                }
            )

        return {
            "api_security_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_database_security(self) -> dict[str, Any]:
        """Audyt bezpieczeństwa bazy danych."""
        logger.info("🗃️ Auditing database security...")

        issues = []
        recommendations = []

        # Sprawdź czy istnieje szyfrowanie bazy danych
        secure_db_file = (
            self.project_root / "server" / "database" / "secure_database.py"
        )
        if not secure_db_file.exists():
            issues.append(
                {
                    "severity": "high",
                    "type": "no_database_encryption",
                    "description": "No database encryption system found",
                    "remediation": "Implement database encryption for sensitive data",
                }
            )

        # Sprawdź pliki bazy danych
        db_files = list(self.project_root.glob("**/*.db")) + list(
            self.project_root.glob("**/*.sqlite")
        )
        for db_file in db_files:
            # Sprawdź uprawnienia
            stat_info = os.stat(db_file)
            permissions = oct(stat_info.st_mode)[-3:]

            if permissions not in ["600", "640"]:
                issues.append(
                    {
                        "severity": "medium",
                        "type": "insecure_db_permissions",
                        "description": f"Database file {db_file.name} has permissions {permissions}",
                        "file": str(db_file),
                        "remediation": "Set database file permissions to 600 (owner read/write only)",
                    }
                )

        # Sprawdź konfigurację bazy danych
        db_managers = list(self.project_root.glob("**/database_manager.py"))
        for db_manager in db_managers:
            content = db_manager.read_text(encoding="utf-8")

            if "execute(" in content and "?" not in content:
                issues.append(
                    {
                        "severity": "high",
                        "type": "sql_injection_risk",
                        "description": f"Potential SQL injection in {db_manager.name}",
                        "file": str(db_manager),
                        "remediation": "Use parameterized queries with ? placeholders",
                    }
                )

        return {
            "database_security_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_configuration_security(self) -> dict[str, Any]:
        """Audyt bezpieczeństwa konfiguracji."""
        logger.info("⚙️ Auditing configuration security...")

        issues = []
        recommendations = []

        # Sprawdź pliki konfiguracyjne z kluczami API
        config_files = list(self.project_root.glob("**/*config*.json"))
        for config_file in config_files:
            try:
                content = config_file.read_text(encoding="utf-8")

                # Sprawdź klucze API w plaintext
                if "YOUR_" in content and "API_KEY" in content:
                    recommendations.append(
                        f"Template API keys found in {config_file.name} - replace with environment variables"
                    )

                if re.search(r'"[a-zA-Z0-9_-]{20,}"', content):
                    potential_keys = re.findall(r'"([a-zA-Z0-9_-]{20,})"', content)
                    for key in potential_keys:
                        if not key.startswith("YOUR_") and "sk-" in key:
                            issues.append(
                                {
                                    "severity": "critical",
                                    "type": "exposed_api_key",
                                    "description": f"Potential API key exposed in {config_file.name}",
                                    "file": str(config_file),
                                    "remediation": "Move API keys to environment variables",
                                }
                            )

            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Sprawdź .env files
        env_files = list(self.project_root.glob("**/.env*"))
        for env_file in env_files:
            if env_file.name == ".env":
                # Sprawdź uprawnienia .env
                stat_info = os.stat(env_file)
                permissions = oct(stat_info.st_mode)[-3:]

                if permissions != "600":
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "insecure_env_permissions",
                            "description": f".env file has permissions {permissions}",
                            "file": str(env_file),
                            "remediation": "Set .env file permissions to 600",
                        }
                    )

        return {
            "configuration_security_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_dependency_security(self) -> dict[str, Any]:
        """Audyt bezpieczeństwa zależności."""
        logger.info("📦 Auditing dependency security...")

        issues = []
        recommendations = []

        # Sprawdź czy safety jest zainstalowane
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "safety"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                recommendations.append(
                    "Install 'safety' package for dependency vulnerability scanning"
                )
            else:
                # Uruchom safety check
                safety_result = subprocess.run(
                    [sys.executable, "-m", "safety", "check", "--json"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if safety_result.returncode == 0:
                    try:
                        vulnerabilities = json.loads(safety_result.stdout)
                        for vuln in vulnerabilities:
                            issues.append(
                                {
                                    "severity": "high",
                                    "type": "vulnerable_dependency",
                                    "description": f"Vulnerable package: {vuln.get('package_name')} {vuln.get('installed_version')}",
                                    "remediation": f"Update to version {vuln.get('fixed_in', 'latest')}",
                                }
                            )
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logger.warning(f"Failed to run dependency security check: {e}")

        # Sprawdź requirements.txt
        req_files = list(self.project_root.glob("**/requirements*.txt"))
        for req_file in req_files:
            content = req_file.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]

            # Sprawdź pinned versions
            unpinned = [
                line for line in lines if "==" not in line and not line.startswith("#")
            ]
            if unpinned:
                recommendations.append(
                    f"Pin dependency versions in {req_file.name}: {', '.join(unpinned[:3])}"
                )

        return {
            "dependency_security_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_file_permissions(self) -> dict[str, Any]:
        """Audyt uprawnień plików."""
        logger.info("📁 Auditing file permissions...")

        issues = []

        # Sprawdź wrażliwe pliki
        sensitive_patterns = [
            "**/*key*",
            "**/*secret*",
            "**/*password*",
            "**/*credential*",
            "**/.env*",
            "**/*config*.json",
        ]

        for pattern in sensitive_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    stat_info = os.stat(file_path)
                    permissions = oct(stat_info.st_mode)[-3:]

                    # Pliki wrażliwe powinny mieć restrykcyjne uprawnienia
                    if permissions not in ["600", "640"]:
                        issues.append(
                            {
                                "severity": "medium",
                                "type": "insecure_file_permissions",
                                "description": f"Sensitive file {file_path.name} has permissions {permissions}",
                                "file": str(file_path),
                                "remediation": "Set file permissions to 600 (owner read/write only)",
                            }
                        )

        return {
            "file_permissions_audit": {
                "issues": issues,
                "status": "warning" if issues else "ok",
            }
        }

    async def audit_logging_security(self) -> dict[str, Any]:
        """Audyt bezpieczeństwa logowania."""
        logger.info("📋 Auditing logging security...")

        issues = []
        recommendations = []

        # Sprawdź konfigurację logowania
        log_configs = list(self.project_root.glob("**/logging*.py")) + list(
            self.project_root.glob("**/log*.py")
        )

        for log_file in log_configs:
            content = log_file.read_text(encoding="utf-8")

            # Sprawdź czy loguje się wrażliwe dane
            sensitive_patterns = ["password", "api_key", "secret", "token"]
            for pattern in sensitive_patterns:
                if pattern in content.lower():
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "sensitive_data_logging",
                            "description": f"Potential sensitive data logging in {log_file.name}",
                            "file": str(log_file),
                            "remediation": "Implement log sanitization to mask sensitive data",
                        }
                    )

        return {
            "logging_security_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "warning" if issues else "ok",
            }
        }

    async def audit_network_security(self) -> dict[str, Any]:
        """Audyt bezpieczeństwa sieciowego."""
        logger.info("🌐 Auditing network security...")

        issues = []
        recommendations = []

        # Sprawdź konfigurację serwera
        main_files = list(self.project_root.glob("**/server_main*.py"))
        for main_file in main_files:
            content = main_file.read_text(encoding="utf-8")

            if 'host="0.0.0.0"' in content:
                issues.append(
                    {
                        "severity": "high",
                        "type": "insecure_host_binding",
                        "description": f"Server binding to all interfaces in {main_file.name}",
                        "file": str(main_file),
                        "remediation": "Bind to specific interface or localhost",
                    }
                )

            if "debug=True" in content:
                issues.append(
                    {
                        "severity": "medium",
                        "type": "debug_mode_enabled",
                        "description": f"Debug mode enabled in {main_file.name}",
                        "file": str(main_file),
                        "remediation": "Disable debug mode in production",
                    }
                )

        return {
            "network_security_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "critical"
                if any(i["severity"] == "critical" for i in issues)
                else "warning",
            }
        }

    async def audit_code_quality(self) -> dict[str, Any]:
        """Audyt jakości kodu pod kątem bezpieczeństwa."""
        logger.info("🔍 Auditing code quality...")

        issues = []
        recommendations = []

        # Sprawdź Python files pod kątem podstawowych problemów
        py_files = list(self.project_root.glob("**/*.py"))

        for py_file in py_files[:50]:  # Ogranicz do 50 plików żeby nie było zbyt długo
            try:
                content = py_file.read_text(encoding="utf-8")

                # Sprawdź eval/exec
                if "eval(" in content or "exec(" in content:
                    issues.append(
                        {
                            "severity": "high",
                            "type": "dangerous_function_usage",
                            "description": f"Use of eval/exec in {py_file.name}",
                            "file": str(py_file),
                            "remediation": "Avoid using eval/exec functions",
                        }
                    )

                # Sprawdź subprocess bez shell=False
                if "subprocess" in content and "shell=True" in content:
                    issues.append(
                        {
                            "severity": "medium",
                            "type": "shell_injection_risk",
                            "description": f"subprocess with shell=True in {py_file.name}",
                            "file": str(py_file),
                            "remediation": "Use subprocess with shell=False and proper argument passing",
                        }
                    )

            except UnicodeDecodeError:
                pass

        return {
            "code_quality_audit": {
                "issues": issues,
                "recommendations": recommendations,
                "status": "warning" if issues else "ok",
            }
        }

    def _check_jwt_security(self) -> bool:
        """Sprawdza implementację JWT."""
        # Sprawdź czy istnieje bezpieczna implementacja JWT
        security_files = list(self.project_root.glob("**/security*.py"))

        for security_file in security_files:
            content = security_file.read_text(encoding="utf-8")
            if "jwt" in content.lower() and "secret" in content.lower():
                return True

        return False

    def _check_rate_limiting(self) -> bool:
        """Sprawdza czy istnieje rate limiting."""
        rate_limit_files = list(self.project_root.glob("**/rate_limit*.py"))
        return len(rate_limit_files) > 0

    def _classify_issues(self) -> None:
        """Klasyfikuje problemy według ważności."""
        for audit_name, audit_data in self.audit_results.items():
            issues = audit_data.get("issues", [])

            for issue in issues:
                severity = issue.get("severity", "low")

                if severity == "critical":
                    self.critical_issues.append(issue)
                elif severity == "high":
                    self.high_issues.append(issue)
                elif severity == "medium":
                    self.medium_issues.append(issue)
                else:
                    self.low_issues.append(issue)

    def _generate_audit_report(self) -> dict[str, Any]:
        """Generuje raport z audytu."""
        total_issues = (
            len(self.critical_issues)
            + len(self.high_issues)
            + len(self.medium_issues)
            + len(self.low_issues)
        )

        # Oblicz ogólny wynik bezpieczeństwa
        security_score = max(
            0,
            100
            - (
                len(self.critical_issues) * 25
                + len(self.high_issues) * 10
                + len(self.medium_issues) * 5
                + len(self.low_issues) * 1
            ),
        )

        return {
            "audit_summary": {
                "total_issues": total_issues,
                "critical_issues": len(self.critical_issues),
                "high_issues": len(self.high_issues),
                "medium_issues": len(self.medium_issues),
                "low_issues": len(self.low_issues),
                "security_score": security_score,
                "overall_status": self._get_overall_status(),
                "audit_timestamp": datetime.now().isoformat(),
            },
            "detailed_results": self.audit_results,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "remediation_priority": self._get_remediation_priority(),
        }

    def _get_overall_status(self) -> str:
        """Określa ogólny status bezpieczeństwa."""
        if self.critical_issues:
            return "CRITICAL - Immediate action required"
        elif self.high_issues:
            return "HIGH RISK - Action required within 24 hours"
        elif self.medium_issues:
            return "MEDIUM RISK - Action required within 1 week"
        elif self.low_issues:
            return "LOW RISK - Address when convenient"
        else:
            return "SECURE - No major issues found"

    def _get_remediation_priority(self) -> list[dict[str, Any]]:
        """Zwraca priorytety naprawy."""
        priority_list = []

        # Krytyczne problemy mają najwyższy priorytet
        for issue in self.critical_issues:
            priority_list.append(
                {
                    "priority": 1,
                    "severity": "critical",
                    "description": issue["description"],
                    "remediation": issue.get(
                        "remediation", "Review and fix immediately"
                    ),
                    "file": issue.get("file", "Unknown"),
                }
            )

        # Wysokie problemy
        for issue in self.high_issues:
            priority_list.append(
                {
                    "priority": 2,
                    "severity": "high",
                    "description": issue["description"],
                    "remediation": issue.get("remediation", "Address within 24 hours"),
                    "file": issue.get("file", "Unknown"),
                }
            )

        return priority_list[:10]  # Top 10 najważniejszych


async def main():
    """Główna funkcja audytu."""
    print("🛡️ GAJA Assistant Security Audit System")
    print("=" * 50)

    try:
        auditor = SecurityAuditor(".")
        audit_report = await auditor.run_full_audit()

        # Zapisz raport
        report_file = Path("security_audit_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, indent=2, ensure_ascii=False)

        # Wyświetl podsumowanie
        summary = audit_report["audit_summary"]
        print("\n📊 AUDIT SUMMARY")
        print(f"Security Score: {summary['security_score']}/100")
        print(f"Overall Status: {summary['overall_status']}")
        print(f"Total Issues: {summary['total_issues']}")
        print(f"  🔴 Critical: {summary['critical_issues']}")
        print(f"  🟠 High: {summary['high_issues']}")
        print(f"  🟡 Medium: {summary['medium_issues']}")
        print(f"  🟢 Low: {summary['low_issues']}")

        # Wyświetl top priorytetowe problemy
        if audit_report.get("remediation_priority"):
            print("\n🎯 TOP PRIORITY ISSUES:")
            for i, issue in enumerate(audit_report["remediation_priority"][:5], 1):
                print(f"  {i}. [{issue['severity'].upper()}] {issue['description']}")
                print(f"     💡 {issue['remediation']}")
                if issue["file"] != "Unknown":
                    print(f"     📁 {issue['file']}")
                print()

        print(f"\n📄 Full report saved to: {report_file}")

        # Zwróć kod wyjścia na podstawie wyników
        if summary["critical_issues"] > 0:
            sys.exit(1)
        elif summary["high_issues"] > 0:
            sys.exit(2)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Audit failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    import re
    from datetime import datetime

    asyncio.run(main())
