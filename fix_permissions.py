"""Security Permissions Fixer Fixes file permissions for production security."""
import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger(__name__)


class PermissionsFixer:
    """Fixes file permissions for security."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

    def fix_database_permissions(self) -> bool:
        """Fix database file permissions to 600 (owner read/write only)"""
        success = True
        db_patterns = ["*.db", "*.sqlite", "*.sqlite3"]

        for pattern in db_patterns:
            for db_file in self.base_path.rglob(pattern):
                try:
                    # Set permissions to 600 (owner read/write only)
                    os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR)
                    logger.info(f"Fixed database permissions: {db_file}")
                except Exception as e:
                    logger.error(f"Failed to fix permissions for {db_file}: {e}")
                    success = False

        return success

    def fix_config_permissions(self) -> bool:
        """Fix configuration file permissions."""
        success = True
        config_files = [
            ".env",
            "*.json",
            "*.yml",
            "*.yaml",
            "*.toml",
            "auth_config.json",
            "server_config.json",
        ]

        for pattern in config_files:
            for config_file in self.base_path.rglob(pattern):
                # Skip certain directories
                if any(
                    skip in str(config_file)
                    for skip in ["node_modules", ".git", "__pycache__"]
                ):
                    continue

                try:
                    # Set permissions to 600 for sensitive configs
                    if any(
                        sensitive in config_file.name.lower()
                        for sensitive in [".env", "auth", "secret", "key"]
                    ):
                        os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR)
                        logger.info(
                            f"Fixed sensitive config permissions: {config_file}"
                        )
                    else:
                        # Regular config files: 644 (owner read/write, others read)
                        os.chmod(
                            config_file,
                            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
                        )
                        logger.info(f"Fixed config permissions: {config_file}")
                except Exception as e:
                    logger.error(f"Failed to fix permissions for {config_file}: {e}")
                    success = False

        return success

    def fix_script_permissions(self) -> bool:
        """Fix script file permissions."""
        success = True
        script_patterns = ["*.py", "*.sh", "*.bat", "*.ps1"]

        for pattern in script_patterns:
            for script_file in self.base_path.rglob(pattern):
                # Skip certain directories
                if any(
                    skip in str(script_file)
                    for skip in ["node_modules", ".git", "__pycache__"]
                ):
                    continue

                try:
                    # Set permissions to 755 (owner read/write/execute, others read/execute)
                    os.chmod(
                        script_file,
                        stat.S_IRWXU
                        | stat.S_IRGRP
                        | stat.S_IXGRP
                        | stat.S_IROTH
                        | stat.S_IXOTH,
                    )
                    logger.info(f"Fixed script permissions: {script_file}")
                except Exception as e:
                    logger.error(f"Failed to fix permissions for {script_file}: {e}")
                    success = False

        return success

    def fix_log_permissions(self) -> bool:
        """Fix log file permissions."""
        success = True
        log_patterns = ["*.log", "*.txt"]

        for pattern in log_patterns:
            for log_file in self.base_path.rglob(pattern):
                # Only process files in logs directories
                if "log" not in str(log_file).lower():
                    continue

                try:
                    # Set permissions to 640 (owner read/write, group read)
                    os.chmod(log_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
                    logger.info(f"Fixed log permissions: {log_file}")
                except Exception as e:
                    logger.error(f"Failed to fix permissions for {log_file}: {e}")
                    success = False

        return success

    def create_secure_directories(self) -> bool:
        """Create secure directories with proper permissions."""
        success = True
        secure_dirs = [
            "data",
            "logs",
            "user_data",
            "databases",
            ".cache",
            "dependencies",
        ]

        for dir_name in secure_dirs:
            dir_path = self.base_path / dir_name
            try:
                dir_path.mkdir(exist_ok=True)
                # Set permissions to 750 (owner read/write/execute, group read/execute)
                os.chmod(dir_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
                logger.info(f"Created/secured directory: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to create/secure directory {dir_path}: {e}")
                success = False

        return success

    def audit_permissions(self) -> dict[str, list[str]]:
        """Audit current file permissions and return issues."""
        issues = {"critical": [], "warning": [], "info": []}

        # Check database files
        for db_file in self.base_path.rglob("*.db"):
            mode = oct(os.stat(db_file).st_mode)[-3:]
            if mode != "600":
                issues["critical"].append(
                    f"Database {db_file} has permissions {mode}, should be 600"
                )

        # Check .env files
        for env_file in self.base_path.rglob(".env*"):
            mode = oct(os.stat(env_file).st_mode)[-3:]
            if mode != "600":
                issues["critical"].append(
                    f"Environment file {env_file} has permissions {mode}, should be 600"
                )

        # Check config files with sensitive data
        sensitive_configs = ["auth_config.json", "*secret*", "*key*", "*password*"]
        for pattern in sensitive_configs:
            for config_file in self.base_path.rglob(pattern):
                if config_file.is_file():
                    mode = oct(os.stat(config_file).st_mode)[-3:]
                    if mode not in ["600", "640"]:
                        issues["warning"].append(
                            f"Sensitive config {config_file} has permissions {mode}"
                        )

        return issues

    def fix_all_permissions(self) -> bool:
        """Fix all file permissions."""
        logger.info("Starting comprehensive permissions fix...")

        success = True
        success &= self.create_secure_directories()
        success &= self.fix_database_permissions()
        success &= self.fix_config_permissions()
        success &= self.fix_script_permissions()
        success &= self.fix_log_permissions()

        if success:
            logger.info("✅ All permissions fixed successfully")
        else:
            logger.error("❌ Some permission fixes failed")

        return success


def main():
    """Main function to fix permissions."""
    logging.basicConfig(level=logging.INFO)

    fixer = PermissionsFixer()

    # Audit current permissions
    print("🔍 Auditing current permissions...")
    issues = fixer.audit_permissions()

    total_issues = sum(len(issue_list) for issue_list in issues.values())
    print(f"Found {total_issues} permission issues")

    if total_issues > 0:
        print("🔧 Fixing permissions...")
        success = fixer.fix_all_permissions()

        if success:
            print("✅ Permissions fixed successfully")
        else:
            print("❌ Some issues remain")
    else:
        print("✅ No permission issues found")


if __name__ == "__main__":
    main()
