"""
Final Production Readiness Test
Complete system validation for production deployment
"""
import sys
import json
import logging
from pathlib import Path

# Dodaj ścieżkę projektu
sys.path.insert(0, str(Path(__file__).parent))

from security_integration import get_security_integration, initialize_security
from fix_permissions import PermissionsFixer

logger = logging.getLogger(__name__)

class ProductionReadinessTest:
    """Test gotowości systemu na produkcję"""
    
    def __init__(self):
        self.passed_tests = 0
        self.total_tests = 0
        self.issues = []
    
    def test_security_integration(self) -> bool:
        """Test integracji systemów bezpieczeństwa"""
        self.total_tests += 1
        print("🔒 Testing security integration...")
        
        try:
            # Initialize security
            success = initialize_security()
            if not success:
                self.issues.append("Security system initialization failed")
                return False
            
            # Get security status
            security = get_security_integration()
            status = security.get_security_status()
            
            # Check all components are initialized
            components = status.get('components', {})
            if not all(components.values()):
                self.issues.append("Some security components not initialized")
                return False
            
            # Check API keys are secured
            if not status.get('api_keys_secured', False):
                self.issues.append("API keys not properly secured")
                return False
            
            print("  ✅ Security integration working")
            self.passed_tests += 1
            return True
            
        except Exception as e:
            self.issues.append(f"Security integration error: {e}")
            return False
    
    def test_file_permissions(self) -> bool:
        """Test uprawnień plików"""
        self.total_tests += 1
        print("📁 Testing file permissions...")
        
        try:
            fixer = PermissionsFixer()
            issues = fixer.audit_permissions()
            
            critical_issues = len(issues.get('critical', []))
            if critical_issues > 0:
                self.issues.append(f"Critical file permission issues: {critical_issues}")
                return False
            
            print("  ✅ File permissions secure")
            self.passed_tests += 1
            return True
            
        except Exception as e:
            self.issues.append(f"File permissions test error: {e}")
            return False
    
    def test_configuration_security(self) -> bool:
        """Test bezpieczeństwa konfiguracji"""
        self.total_tests += 1
        print("⚙️ Testing configuration security...")
        
        try:
            # Check config.json doesn't contain API keys
            config_path = Path("config.json")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_text = f.read()
                
                # Check for exposed API keys
                if "sk-" in config_text and not "${" in config_text:
                    self.issues.append("API keys still exposed in config.json")
                    return False
            
            # Check .env file permissions
            env_path = Path(".env")
            if env_path.exists():
                import stat
                mode = oct(env_path.stat().st_mode)[-3:]
                if mode != "600":
                    self.issues.append(f".env file has insecure permissions: {mode}")
                    return False
            
            print("  ✅ Configuration security OK")
            self.passed_tests += 1
            return True
            
        except Exception as e:
            self.issues.append(f"Configuration security test error: {e}")
            return False
    
    def test_ssl_setup(self) -> bool:
        """Test konfiguracji SSL"""
        self.total_tests += 1
        print("🔐 Testing SSL setup...")
        
        try:
            ssl_dir = Path("ssl")
            cert_path = ssl_dir / "certificate.pem"
            key_path = ssl_dir / "private_key.pem"
            
            if not ssl_dir.exists():
                self.issues.append("SSL directory not found")
                return False
            
            if not cert_path.exists() or not key_path.exists():
                self.issues.append("SSL certificates not found")
                return False
            
            # Check key file permissions
            import stat
            key_mode = oct(key_path.stat().st_mode)[-3:]
            if key_mode != "600":
                self.issues.append(f"SSL private key has insecure permissions: {key_mode}")
                return False
            
            print("  ✅ SSL setup complete")
            self.passed_tests += 1
            return True
            
        except Exception as e:
            self.issues.append(f"SSL setup test error: {e}")
            return False
    
    def test_production_files(self) -> bool:
        """Test plików produkcyjnych"""
        self.total_tests += 1
        print("📋 Testing production files...")
        
        try:
            required_files = [
                "PRODUCTION_SECURITY_CHECKLIST.md",
                "Dockerfile.production",
                "secure_config.py",
                "security_integration.py",
                "production_security_setup.py"
            ]
            
            missing_files = []
            for file_path in required_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                self.issues.append(f"Missing production files: {', '.join(missing_files)}")
                return False
            
            print("  ✅ Production files present")
            self.passed_tests += 1
            return True
            
        except Exception as e:
            self.issues.append(f"Production files test error: {e}")
            return False
    
    def run_complete_test(self) -> bool:
        """Uruchom kompletny test gotowości"""
        print("🚀 GAJA Assistant Production Readiness Test")
        print("=" * 50)
        
        # Run all tests
        tests = [
            self.test_security_integration,
            self.test_file_permissions,
            self.test_configuration_security,
            self.test_ssl_setup,
            self.test_production_files
        ]
        
        for test in tests:
            test()
        
        # Generate report
        print("\n📊 TEST RESULTS")
        print(f"Passed: {self.passed_tests}/{self.total_tests}")
        print(f"Success rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        if self.issues:
            print("\n🚨 ISSUES FOUND:")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        else:
            print("\n✅ NO ISSUES FOUND!")
        
        # Overall status
        if self.passed_tests == self.total_tests:
            print("\n🎉 SYSTEM READY FOR PRODUCTION!")
            return True
        else:
            print("\n⚠️ SYSTEM NOT READY - FIX ISSUES FIRST")
            return False

def main():
    """Main function"""
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    test = ProductionReadinessTest()
    success = test.run_complete_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
