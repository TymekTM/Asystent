#!/usr/bin/env python3
"""
security_check.py - Comprehensive security checker for GAJA Assistant

This script performs automated security checks on the GAJA Assistant codebase
and configuration files to identify potential security vulnerabilities.
"""

import os
import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityChecker:
    """Comprehensive security checker for GAJA Assistant."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.info: List[Dict[str, Any]] = []
          # Patterns for sensitive data detection - more specific
        self.sensitive_patterns = [
            (r'sk-[a-zA-Z0-9]{48,}', 'OpenAI API Key'),
            (r'pk-[a-zA-Z0-9]{40,}', 'Anthropic API Key'),
            (r'xoxb-[a-zA-Z0-9]{10,}', 'Slack Bot Token'),
            (r'ya29\.[a-zA-Z0-9_-]{30,}', 'Google OAuth Token'),
            (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
            (r'AIza[0-9A-Za-z_-]{35}', 'Google API Key'),
            (r'password\s*[=:]\s*["\'][^"\']{8,}["\']', 'Hardcoded Password'),
            (r'secret\s*[=:]\s*["\'][^"\']{8,}["\']', 'Hardcoded Secret'),
            (r'token\s*[=:]\s*["\'][^"\']{16,}["\']', 'Hardcoded Token'),
        ]
          # Files and directories to exclude from sensitive data scanning
        self.exclude_files = {
            '.git', '__pycache__', 'node_modules', 'venv', 'env',
            '.env.example', 'requirements.txt', 'package.json',
            'migrate_api_keys.py', 'security_check.py'
        }
        
        # Directories to completely skip during scanning
        self.exclude_directories = {
            '.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv',
            'release', 'dist', 'build', '.pytest_cache', '.tox',
            'dependencies', 'packages', 'site-packages', '.cache',
            'logs', 'temp', 'tmp', 'history_archive', '.vscode',
            'screenshots', 'reports'
        }
        
        # File extensions to exclude from security scanning
        self.exclude_extensions = {
            '.db', '.sqlite', '.sqlite3', '.log', '.tmp', '.cache',
            '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin',
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.mp3', '.wav', '.mp4', '.avi', '.mov', '.pdf'
        }
          # Safe configuration patterns
        self.safe_config_patterns = [
            'YOUR_API_KEY_HERE', 'your_api_key_here', 'placeholder',
            'example', 'template', 'ENTER_YOUR', 'INSERT_YOUR',
            'REPLACE_WITH', 'CHANGE_THIS', 'dummy', 'test',
            '_comment', 'loaded from environment', 'env file'
        ]
        
        # Patterns that look like API keys but are safe
        self.safe_key_patterns = [
            r'sk-.*example.*', r'sk-.*placeholder.*', r'sk-.*dummy.*',
            r'pk-.*example.*', r'pk-.*placeholder.*', r'pk-.*dummy.*',
            r'.*YOUR_.*_KEY.*', r'.*ENTER_YOUR.*', r'.*REPLACE_WITH.*'        ]
    
    def check_sensitive_data_in_files(self) -> None:
        """Check for hardcoded sensitive data in source files."""
        logger.info("Checking for sensitive data in files...")
        
        for root, dirs, files in os.walk('.'):
            # Skip excluded directories completely
            dirs[:] = [d for d in dirs if d not in self.exclude_directories]
            
            # Skip if we're in an excluded directory path
            if any(excl_dir in root for excl_dir in self.exclude_directories):
                continue
            
            for file in files:
                if any(excl in file for excl in self.exclude_files):
                    continue
                
                # Skip files with excluded extensions
                if any(file.endswith(ext) for ext in self.exclude_extensions):
                    continue
                
                if file.endswith(('.py', '.js', '.json', '.yaml', '.yml', '.txt', '.md', '.env')):
                    file_path = Path(root) / file
                    
                    # Additional path-based exclusions
                    if any(excl_dir in str(file_path) for excl_dir in self.exclude_directories):                        continue
                        
                    self._scan_file_for_sensitive_data(file_path)
    
    def _scan_file_for_sensitive_data(self, file_path: Path) -> None:
        """Scan a single file for sensitive data."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for pattern, description in self.sensitive_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    
                    # Check if it's a safe placeholder
                    if any(safe in matched_text.lower() for safe in self.safe_config_patterns):
                        continue
                    
                    # Check against safe key patterns
                    if any(re.match(safe_pattern, matched_text, re.IGNORECASE) 
                           for safe_pattern in self.safe_key_patterns):
                        continue
                    
                    # Skip very short potential keys (likely false positives)
                    if description == 'Potential API Key' and len(matched_text) < 20:
                        continue
                      # Skip if it's in a comment explaining environment variables
                    line_start = max(0, content.rfind('\n', 0, match.start()))
                    line_end = content.find('\n', match.end())
                    if line_end == -1:
                        line_end = len(content)
                    line_content = content[line_start:line_end].lower()
                    
                    if any(comment_indicator in line_content for comment_indicator in 
                           ['_comment', '# ', '//', '/*', 'loaded from environment', 'env file']):
                        continue
                    
                    # Skip dev/test passwords in development contexts
                    if description in ['Hardcoded Password', 'Hardcoded Secret'] and any(
                        dev_indicator in line_content for dev_indicator in 
                        ['dev', 'test', 'default', 'demo', 'example', 'seed_dev']):
                        continue
                    
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    self.issues.append({
                        'type': 'sensitive_data',
                        'severity': 'HIGH',
                        'file': str(file_path),
                        'line': line_num,
                        'description': f'{description} detected',
                        'pattern': pattern,
                        'context': matched_text[:20] + '...' if len(matched_text) > 20 else matched_text
                    })
                    
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
    
    def check_file_permissions(self) -> None:
        """Check file permissions for sensitive files."""
        logger.info("Checking file permissions...")
        
        sensitive_files = [
            '.env', 'admin_credentials.txt', 'config.json',
            'server_config.json', 'client_config.json'
        ]
        
        for file_name in sensitive_files:
            file_path = Path(file_name)
            if file_path.exists():
                try:
                    stat_info = file_path.stat()
                    mode = oct(stat_info.st_mode)[-3:]
                    
                    # Check if file is readable by others (world-readable)
                    if int(mode[2]) >= 4:
                        self.issues.append({
                            'type': 'file_permissions',
                            'severity': 'MEDIUM',
                            'file': str(file_path),
                            'description': f'Sensitive file {file_name} is world-readable (permissions: {mode})',
                            'recommendation': 'Run: chmod 600 ' + str(file_path)
                        })
                    
                except Exception as e:
                    logger.error(f"Error checking permissions for {file_path}: {e}")
    
    def check_configuration_security(self) -> None:
        """Check configuration files for security issues."""
        logger.info("Checking configuration security...")
        
        config_files = [
            'config.json', 'server_config.json', 'client_config.json',
            'server/server_config.json', 'client/client_config.json'
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                self._check_config_file_security(config_path)
    
    def _check_config_file_security(self, config_path: Path) -> None:
        """Check a specific configuration file for security issues."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
              # Check for CORS wildcard
            cors_origins = self._get_nested_value(config, ['security', 'cors_origins']) or \
                          self._get_nested_value(config, ['cors_origins'])
            
            if cors_origins and '*' in cors_origins:
                self.warnings.append({
                    'type': 'cors_security',
                    'severity': 'MEDIUM',
                    'file': str(config_path),
                    'description': 'CORS configured to allow all origins (*)',
                    'recommendation': 'Restrict CORS to specific trusted domains'
                })
              # Check for debug mode in production-like config
            debug_mode = self._get_nested_value(config, ['server', 'debug']) or \
                        self._get_nested_value(config, ['debug'])
            
            if debug_mode and 'production' in str(config_path).lower():
                self.issues.append({
                    'type': 'debug_mode',
                    'severity': 'HIGH',
                    'file': str(config_path),
                    'description': 'Debug mode enabled in production configuration',
                    'recommendation': 'Disable debug mode in production'
                })
              # Check for binding to all interfaces
            host = self._get_nested_value(config, ['server', 'host']) or \
                   self._get_nested_value(config, ['host'])
            
            if host == '0.0.0.0':
                self.warnings.append({
                    'type': 'network_binding',
                    'severity': 'MEDIUM',
                    'file': str(config_path),
                    'description': 'Server configured to bind to all interfaces (0.0.0.0)',
                    'recommendation': 'Consider binding to localhost or specific interface'
                })
              # Check for API keys in config
            api_keys = self._get_nested_value(config, ['api_keys']) or \
                      self._get_nested_value(config, ['API_KEYS'])
            
            if api_keys and isinstance(api_keys, dict):
                for key, value in api_keys.items():
                    if value and isinstance(value, str) and len(value) > 10:
                        if not any(safe in value.lower() for safe in self.safe_config_patterns):
                            self.issues.append({
                                'type': 'api_key_in_config',
                                'severity': 'HIGH',
                                'file': str(config_path),
                                'description': f'API key {key} appears to contain actual credentials',
                                'recommendation': 'Move API key to environment variable'
                            })
                            
        except Exception as e:
            logger.error(f"Error checking config {config_path}: {e}")
    
    def _get_nested_value(self, data: Dict, keys: List[str]) -> Any:
        """Get nested value from dictionary."""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    def check_dependencies_security(self) -> None:
        """Check for known security vulnerabilities in dependencies."""
        logger.info("Checking dependencies for known vulnerabilities...")
        
        # Check if safety is available
        try:
            result = subprocess.run(['safety', 'check', '--json'], 
                                 capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities:
                    self.issues.append({
                        'type': 'dependency_vulnerability',
                        'severity': 'HIGH',
                        'description': f"Vulnerable dependency: {vuln.get('package_name')} {vuln.get('installed_version')}",
                        'vulnerability': vuln.get('vulnerability'),
                        'recommendation': f"Upgrade to version {vuln.get('fixed_versions', 'latest')}"
                    })
            else:
                self.warnings.append({
                    'type': 'dependency_check',
                    'severity': 'INFO',
                    'description': 'Could not run safety check (install with: pip install safety)'
                })
                
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            self.warnings.append({
                'type': 'dependency_check',
                'severity': 'INFO',
                'description': 'Safety dependency checker not available'
            })
    
    def check_python_security(self) -> None:
        """Check Python code for security issues using bandit."""
        logger.info("Checking Python code security...")
        
        try:
            result = subprocess.run(['bandit', '-r', '.', '-f', 'json', '-ll'], 
                                 capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                for issue in bandit_results.get('results', []):
                    self.issues.append({
                        'type': 'code_security',
                        'severity': issue.get('issue_severity', 'MEDIUM'),
                        'file': issue.get('filename'),
                        'line': issue.get('line_number'),
                        'description': issue.get('issue_text'),
                        'test_id': issue.get('test_id'),
                        'recommendation': 'Review code for security best practices'
                    })
                    
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            self.warnings.append({
                'type': 'code_security_check',
                'severity': 'INFO',
                'description': 'Bandit security checker not available (install with: pip install bandit)'
            })
    
    def check_gitignore_security(self) -> None:
        """Check if .gitignore properly excludes sensitive files."""
        logger.info("Checking .gitignore configuration...")
        
        gitignore_path = Path('.gitignore')
        if not gitignore_path.exists():
            self.issues.append({
                'type': 'gitignore',
                'severity': 'HIGH',
                'description': '.gitignore file not found',
                'recommendation': 'Create .gitignore to exclude sensitive files'
            })
            return
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                gitignore_content = f.read()
            
            required_patterns = [
                '.env', '*.db', '*.log', 'admin_credentials.txt',
                '**/config.json', '__pycache__'
            ]
            
            missing_patterns = []
            for pattern in required_patterns:
                if pattern not in gitignore_content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                self.warnings.append({
                    'type': 'gitignore',
                    'severity': 'MEDIUM',
                    'description': f'Missing .gitignore patterns: {", ".join(missing_patterns)}',
                    'recommendation': 'Add missing patterns to .gitignore'
                })
                
        except Exception as e:            logger.error(f"Error checking .gitignore: {e}")
    
    def check_process_security(self) -> None:
        """Check for secure process management practices."""
        logger.info("Checking process security...")
        
        # Look for subprocess calls without proper validation
        python_files = list(Path('.').rglob('*.py'))
        
        for py_file in python_files:
            # Skip files in excluded directories
            if any(excl_dir in str(py_file) for excl_dir in self.exclude_directories):
                continue
                
            # Skip test files and certain types of files
            if any(skip in str(py_file).lower() for skip in ['test_', 'tests/', '_test.py', 'demo_', 'example_']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                  # Check for os.system usage (potentially dangerous)
                if 'os.system(' in content:
                    # Skip if it's just detecting os.system usage (like in this file)
                    if 'security_check.py' in str(py_file) or 'check.*os.system' in content:
                        continue
                        
                    line_num = content[:content.find('os.system(')].count('\n') + 1
                    self.warnings.append({
                        'type': 'process_security',
                        'severity': 'MEDIUM',
                        'file': str(py_file),
                        'line': line_num,
                        'description': 'Use of os.system() detected',
                        'recommendation': 'Consider using subprocess.run() for better security'
                    })
                  # Check for shell=True in subprocess calls
                shell_true_pattern = r'subprocess\.[^(]+\([^)]*shell\s*=\s*True'
                matches = re.finditer(shell_true_pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\\n') + 1
                    self.warnings.append({
                        'type': 'process_security',
                        'severity': 'MEDIUM',
                        'file': str(py_file),
                        'line': line_num,
                        'description': 'subprocess call with shell=True',
                        'recommendation': 'Avoid shell=True unless absolutely necessary'
                    })
                    
            except Exception as e:
                logger.error(f"Error checking {py_file}: {e}")
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all security checks and return results."""
        logger.info("Starting comprehensive security check...")
        
        self.check_sensitive_data_in_files()
        self.check_file_permissions()
        self.check_configuration_security()
        self.check_dependencies_security()
        self.check_python_security()
        self.check_gitignore_security()
        self.check_process_security()
        
        return {
            'issues': self.issues,
            'warnings': self.warnings,
            'info': self.info,
            'summary': {
                'total_issues': len(self.issues),
                'high_severity': len([i for i in self.issues if i.get('severity') == 'HIGH']),
                'medium_severity': len([i for i in self.issues if i.get('severity') == 'MEDIUM']),
                'low_severity': len([i for i in self.issues if i.get('severity') == 'LOW']),
                'warnings': len(self.warnings)
            }
        }
    
    def print_results(self, results: Dict[str, Any]) -> None:
        """Print security check results in a readable format."""
        print("\\n" + "="*80)
        print("GAJA ASSISTANT SECURITY CHECK RESULTS")
        print("="*80)
        
        summary = results['summary']
        print(f"\\nSUMMARY:")
        print(f"  Total Issues: {summary['total_issues']}")
        print(f"  High Severity: {summary['high_severity']}")
        print(f"  Medium Severity: {summary['medium_severity']}")
        print(f"  Low Severity: {summary['low_severity']}")
        print(f"  Warnings: {summary['warnings']}")
        
        # Print high severity issues first
        high_issues = [i for i in results['issues'] if i.get('severity') == 'HIGH']
        if high_issues:
            print(f"\\n🚨 HIGH SEVERITY ISSUES ({len(high_issues)}):")
            for issue in high_issues:
                self._print_issue(issue)
        
        # Print medium severity issues
        medium_issues = [i for i in results['issues'] if i.get('severity') == 'MEDIUM']
        if medium_issues:
            print(f"\\n⚠️  MEDIUM SEVERITY ISSUES ({len(medium_issues)}):")
            for issue in medium_issues:
                self._print_issue(issue)
        
        # Print warnings
        if results['warnings']:
            print(f"\\n💡 WARNINGS ({len(results['warnings'])}):")
            for warning in results['warnings']:
                self._print_issue(warning)
        
        # Security score
        total_points = 100
        high_penalty = len(high_issues) * 15
        medium_penalty = len(medium_issues) * 5
        warning_penalty = len(results['warnings']) * 1
        
        security_score = max(0, total_points - high_penalty - medium_penalty - warning_penalty)
        
        print(f"\\n📊 SECURITY SCORE: {security_score}/100")
        
        if security_score >= 90:
            print("✅ Excellent security posture!")
        elif security_score >= 75:
            print("👍 Good security posture with room for improvement")
        elif security_score >= 50:
            print("⚠️  Moderate security risks present")
        else:
            print("🚨 Significant security risks require immediate attention")
        
        print("\\n" + "="*80)
    
    def _print_issue(self, issue: Dict[str, Any]) -> None:
        """Print a single security issue."""
        severity = issue.get('severity', 'INFO')
        file_path = issue.get('file', 'N/A')
        line = issue.get('line', '')
        description = issue.get('description', 'No description')
        recommendation = issue.get('recommendation', '')
        
        location = f"{file_path}:{line}" if line else file_path
        
        print(f"\\n  [{severity}] {description}")
        if file_path != 'N/A':
            print(f"    Location: {location}")
        if recommendation:
            print(f"    Fix: {recommendation}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GAJA Assistant Security Checker")
    parser.add_argument("--output", help="Output format", choices=['json', 'text'], default='text')
    parser.add_argument("--output-file", help="Output file path")
    parser.add_argument("--fail-on-high", action="store_true", help="Exit with code 1 if high severity issues found")
    
    args = parser.parse_args()
    
    checker = SecurityChecker()
    results = checker.run_all_checks()
    
    if args.output == 'json':
        output = json.dumps(results, indent=2)
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(output)
        else:
            print(output)
    else:
        checker.print_results(results)
        if args.output_file:
            # Redirect stdout to file for text output
            import sys
            with open(args.output_file, 'w') as f:
                sys.stdout = f
                checker.print_results(results)
                sys.stdout = sys.__stdout__
    
    # Exit with error code if high severity issues found and --fail-on-high is set
    if args.fail_on_high and results['summary']['high_severity'] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
