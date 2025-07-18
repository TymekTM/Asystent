"""
Production Deployment Manager
Handles deployment preparation and execution for GAJA Assistant
"""
import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import zipfile
import tempfile

logger = logging.getLogger(__name__)

class ProductionDeploymentManager:
    """Manages production deployment process"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.deployment_log = []
        self.deployment_success = False
        
    def log_step(self, step: str, success: bool, details: str = ""):
        """Log deployment step"""
        status = "✅" if success else "❌"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            "timestamp": timestamp,
            "step": step,
            "success": success,
            "details": details
        }
        
        self.deployment_log.append(log_entry)
        print(f"{status} [{timestamp}] {step}")
        if details:
            print(f"    {details}")
    
    def prepare_server_deployment(self) -> bool:
        """Prepare server for production deployment"""
        try:
            print("🚀 Preparing Server for Production Deployment")
            print("=" * 50)
            
            # Create deployment directory
            deploy_dir = self.project_root / "deploy" / "server"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy server files
            server_files = [
                "server_main.py",
                "server_config.json", 
                "requirements.txt",
                "secure_config.py",
                "security_integration.py"
            ]
            
            for file_name in server_files:
                source_path = self.project_root / file_name
                if source_path.exists():
                    shutil.copy2(source_path, deploy_dir / file_name)
                    self.log_step(f"Copy {file_name}", True)
                else:
                    self.log_step(f"Copy {file_name}", False, f"File not found: {source_path}")
                    return False
            
            # Copy server directory
            server_source = self.project_root / "server"
            server_dest = deploy_dir / "server"
            if server_source.exists():
                if server_dest.exists():
                    shutil.rmtree(server_dest)
                shutil.copytree(server_source, server_dest)
                self.log_step("Copy server directory", True)
            else:
                self.log_step("Copy server directory", False, "Server directory not found")
                return False
            
            # Copy SSL certificates
            ssl_source = self.project_root / "ssl"
            ssl_dest = deploy_dir / "ssl"
            if ssl_source.exists():
                if ssl_dest.exists():
                    shutil.rmtree(ssl_dest)
                shutil.copytree(ssl_source, ssl_dest)
                self.log_step("Copy SSL certificates", True)
            else:
                self.log_step("Copy SSL certificates", False, "SSL directory not found")
                return False
            
            # Copy essential directories
            essential_dirs = ["databases", "logs", "config"]
            for dir_name in essential_dirs:
                source_dir = self.project_root / dir_name
                dest_dir = deploy_dir / dir_name
                
                if source_dir.exists():
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(source_dir, dest_dir)
                    self.log_step(f"Copy {dir_name} directory", True)
                else:
                    # Create empty directory if it doesn't exist
                    dest_dir.mkdir(exist_ok=True)
                    self.log_step(f"Create {dir_name} directory", True, "Created empty directory")
            
            # Create production startup script
            self.create_server_startup_script(deploy_dir)
            
            # Create Docker configuration
            self.create_docker_config(deploy_dir)
            
            # Create environment template
            self.create_env_template(deploy_dir)
            
            self.log_step("Server deployment preparation", True, "All server files prepared")
            return True
            
        except Exception as e:
            self.log_step("Server deployment preparation", False, f"Error: {e}")
            return False
    
    def prepare_client_deployment(self) -> bool:
        """Prepare client for production deployment"""
        try:
            print("\n💻 Preparing Client for Production Deployment")
            print("=" * 50)
            
            # Create deployment directory
            deploy_dir = self.project_root / "deploy" / "client"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy client directory
            client_source = self.project_root / "client"
            if not client_source.exists():
                self.log_step("Client deployment preparation", False, "Client directory not found")
                return False
            
            # Copy all client files
            for item in client_source.rglob("*"):
                if item.is_file():
                    # Calculate relative path
                    rel_path = item.relative_to(client_source)
                    dest_path = deploy_dir / rel_path
                    
                    # Create parent directories
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, dest_path)
            
            self.log_step("Copy client files", True, f"Copied client directory to deployment")
            
            # Copy client requirements
            client_req_source = client_source / "requirements_client.txt"
            if client_req_source.exists():
                shutil.copy2(client_req_source, deploy_dir / "requirements.txt")
                self.log_step("Copy client requirements", True)
            else:
                # Create basic requirements file
                basic_requirements = [
                    "requests>=2.31.0",
                    "pystray>=0.19.4",
                    "Pillow>=10.0.0",
                    "pycryptodome>=3.19.0"
                ]
                with open(deploy_dir / "requirements.txt", 'w') as f:
                    f.write('\n'.join(basic_requirements))
                self.log_step("Create client requirements", True, "Created basic requirements.txt")
            
            # Create client startup script
            self.create_client_startup_script(deploy_dir)
            
            # Create client installer
            self.create_client_installer(deploy_dir)
            
            self.log_step("Client deployment preparation", True, "All client files prepared")
            return True
            
        except Exception as e:
            self.log_step("Client deployment preparation", False, f"Error: {e}")
            return False
    
    def create_server_startup_script(self, deploy_dir: Path):
        """Create production server startup script"""
        # Linux/Unix startup script
        startup_script_unix = '''#!/bin/bash
set -e

echo "🚀 Starting GAJA Assistant Server"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ Warning: OPENAI_API_KEY not set"
fi

if [ -z "$JWT_SECRET_KEY" ]; then
    echo "⚠️ Warning: JWT_SECRET_KEY not set"
fi

# Start server
echo "Starting server on port 8443 with SSL..."
python server_main.py

echo "Server started successfully!"
'''
        
        # Windows startup script
        startup_script_windows = '''@echo off
echo 🚀 Starting GAJA Assistant Server

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Check environment variables
if "%OPENAI_API_KEY%"=="" (
    echo ⚠️ Warning: OPENAI_API_KEY not set
)

if "%JWT_SECRET_KEY%"=="" (
    echo ⚠️ Warning: JWT_SECRET_KEY not set
)

REM Start server
echo Starting server on port 8443 with SSL...
python server_main.py

echo Server started successfully!
pause
'''
        
        # Save scripts
        with open(deploy_dir / "start_server.sh", 'w', newline='\n') as f:
            f.write(startup_script_unix)
        
        with open(deploy_dir / "start_server.bat", 'w', newline='\r\n') as f:
            f.write(startup_script_windows)
        
        # Make Unix script executable (if on Unix-like system)
        try:
            import stat
            script_path = deploy_dir / "start_server.sh"
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        except:
            pass
        
        self.log_step("Create server startup scripts", True)
    
    def create_client_startup_script(self, deploy_dir: Path):
        """Create production client startup script"""
        # Windows startup script
        startup_script_windows = '''@echo off
echo 💻 Starting GAJA Assistant Client

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Start client
echo Starting GAJA Assistant Client...
python client_main.py

pause
'''
        
        # Linux startup script
        startup_script_unix = '''#!/bin/bash
set -e

echo "💻 Starting GAJA Assistant Client"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Start client
echo "Starting GAJA Assistant Client..."
python client_main.py
'''
        
        # Save scripts
        with open(deploy_dir / "start_client.bat", 'w', newline='\r\n') as f:
            f.write(startup_script_windows)
        
        with open(deploy_dir / "start_client.sh", 'w', newline='\n') as f:
            f.write(startup_script_unix)
        
        # Make Unix script executable
        try:
            import stat
            script_path = deploy_dir / "start_client.sh"
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
        except:
            pass
        
        self.log_step("Create client startup scripts", True)
    
    def create_docker_config(self, deploy_dir: Path):
        """Create Docker configuration for server"""
        dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p logs databases ssl

# Expose port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f -k https://localhost:8443/health || exit 1

# Start server
CMD ["python", "server_main.py"]
'''
        
        docker_compose_content = '''version: '3.8'

services:
  gaja-server:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8443:8443"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    volumes:
      - ./databases:/app/databases
      - ./logs:/app/logs
      - ./ssl:/app/ssl
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "-k", "https://localhost:8443/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
'''
        
        # Save Docker files
        with open(deploy_dir / "Dockerfile", 'w') as f:
            f.write(dockerfile_content)
        
        with open(deploy_dir / "docker-compose.yml", 'w') as f:
            f.write(docker_compose_content)
        
        self.log_step("Create Docker configuration", True)
    
    def create_env_template(self, deploy_dir: Path):
        """Create environment variables template"""
        env_template = '''# GAJA Assistant Production Environment Variables
# Copy this file to .env and fill in your actual values

# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here

# Security Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-minimum-32-characters-long
ENCRYPTION_KEY=your-32-character-encryption-key-here

# Optional: Additional AI Providers
# ANTHROPIC_API_KEY=your-anthropic-api-key-here
# DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8443
SSL_ENABLED=true

# Database Configuration
DATABASE_URL=sqlite:///databases/server_data.db

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/gaja_server.log

# Production Settings
PRODUCTION=true
DEBUG=false
'''
        
        with open(deploy_dir / ".env.template", 'w') as f:
            f.write(env_template)
        
        self.log_step("Create environment template", True)
    
    def create_client_installer(self, deploy_dir: Path):
        """Create client installer script"""
        installer_script = '''@echo off
echo 🛠️ GAJA Assistant Client Installer

echo Creating installation directory...
if not exist "%USERPROFILE%\\GAJA" mkdir "%USERPROFILE%\\GAJA"

echo Copying files...
xcopy /E /I /H /Y . "%USERPROFILE%\\GAJA"

echo Creating desktop shortcut...
set SCRIPT="%TEMP%\\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = "%USERPROFILE%\\Desktop\\GAJA Assistant.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "%USERPROFILE%\\GAJA\\start_client.bat" >> %SCRIPT%
echo oLink.WorkingDirectory = "%USERPROFILE%\\GAJA" >> %SCRIPT%
echo oLink.Description = "GAJA Assistant Client" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT%

echo Creating start menu entry...
if not exist "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\GAJA" mkdir "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\GAJA"
copy "%USERPROFILE%\\Desktop\\GAJA Assistant.lnk" "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\GAJA\\"

echo Installation complete!
echo GAJA Assistant has been installed to: %USERPROFILE%\\GAJA
echo You can start it from the desktop shortcut or start menu.

pause
'''
        
        with open(deploy_dir / "install.bat", 'w', newline='\r\n') as f:
            f.write(installer_script)
        
        self.log_step("Create client installer", True)
    
    def create_deployment_packages(self) -> bool:
        """Create deployment packages"""
        try:
            print("\n📦 Creating Deployment Packages")
            print("=" * 40)
            
            deploy_root = self.project_root / "deploy"
            packages_dir = self.project_root / "packages"
            packages_dir.mkdir(exist_ok=True)
            
            # Create server package
            server_dir = deploy_root / "server"
            if server_dir.exists():
                server_package = packages_dir / f"gaja_server_v{time.strftime('%Y%m%d_%H%M%S')}.zip"
                with zipfile.ZipFile(server_package, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in server_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(server_dir)
                            zipf.write(file_path, arcname)
                
                self.log_step("Create server package", True, f"Created: {server_package.name}")
            else:
                self.log_step("Create server package", False, "Server deployment directory not found")
            
            # Create client package
            client_dir = deploy_root / "client"
            if client_dir.exists():
                client_package = packages_dir / f"gaja_client_v{time.strftime('%Y%m%d_%H%M%S')}.zip"
                with zipfile.ZipFile(client_package, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in client_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(client_dir)
                            zipf.write(file_path, arcname)
                
                self.log_step("Create client package", True, f"Created: {client_package.name}")
            else:
                self.log_step("Create client package", False, "Client deployment directory not found")
            
            return True
            
        except Exception as e:
            self.log_step("Create deployment packages", False, f"Error: {e}")
            return False
    
    def create_deployment_guide(self) -> bool:
        """Create deployment guide"""
        try:
            guide_content = '''# GAJA Assistant Production Deployment Guide

## 🚀 Server Deployment

### Prerequisites
- Python 3.11 or higher
- SSL certificate (replace self-signed certificates in ssl/ directory)
- Environment variables configured

### Quick Start
1. Extract server package to deployment location
2. Copy `.env.template` to `.env` and configure
3. Run `start_server.sh` (Linux) or `start_server.bat` (Windows)

### Docker Deployment
1. Ensure Docker and Docker Compose are installed
2. Configure environment variables in `.env` file
3. Run: `docker-compose up -d`

### Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key
- `JWT_SECRET_KEY`: Secret key for JWT tokens (32+ characters)
- `ENCRYPTION_KEY`: Encryption key for database (32 characters)

### Security Checklist
- [ ] Replace self-signed SSL certificates with valid certificates
- [ ] Configure firewall to allow port 8443
- [ ] Set strong environment variables
- [ ] Enable log monitoring
- [ ] Configure backup for databases/ directory

## 💻 Client Deployment

### Windows Installation
1. Extract client package
2. Run `install.bat` as administrator
3. Client will be installed to user profile
4. Desktop and start menu shortcuts created

### Manual Installation
1. Extract client package to desired location
2. Install Python requirements: `pip install -r requirements.txt`
3. Configure server URL in `client_config.json`
4. Run `start_client.bat` or `start_client.sh`

### Client Configuration
Edit `client_config.json`:
```json
{
    "server_url": "https://your-server:8443",
    "auto_connect": true,
    "ui_theme": "dark"
}
```

## 🔧 Maintenance

### Server Maintenance
- Monitor logs in `logs/` directory
- Backup `databases/` directory regularly
- Update SSL certificates before expiration
- Monitor CPU and memory usage

### Client Updates
- Replace client files with new version
- Restart client application
- Check configuration compatibility

## 🆘 Troubleshooting

### Server Issues
- Check logs in `logs/gaja_server.log`
- Verify SSL certificates are valid
- Ensure environment variables are set
- Check port 8443 is not blocked

### Client Issues
- Verify server URL is correct
- Check network connectivity
- Ensure client has internet access
- Review client logs

### Common Problems
1. **SSL Certificate Error**: Replace self-signed certificates
2. **Environment Variables**: Ensure all required variables are set
3. **Port Access**: Configure firewall for port 8443
4. **Database Issues**: Check file permissions on databases/ directory

## 📊 Monitoring

### Health Checks
- Server health endpoint: `https://your-server:8443/health`
- Monitor server logs for errors
- Check database connectivity

### Performance Monitoring
- Monitor CPU and memory usage
- Track API response times
- Monitor SSL certificate expiration

## 🔐 Security Recommendations

### Production Security
- Use valid SSL certificates from trusted CA
- Configure proper firewall rules
- Enable log monitoring and alerting
- Regular security updates
- Backup encryption keys securely

### Access Control
- Use strong passwords for admin access
- Implement IP restrictions if possible
- Regular access review
- Monitor for suspicious activity

---

For support, check the logs first, then refer to the troubleshooting section.
'''
            
            guide_path = self.project_root / "DEPLOYMENT_GUIDE.md"
            with open(guide_path, 'w', encoding='utf-8') as f:
                f.write(guide_content)
            
            self.log_step("Create deployment guide", True, f"Guide saved to: {guide_path}")
            return True
            
        except Exception as e:
            self.log_step("Create deployment guide", False, f"Error: {e}")
            return False
    
    def run_full_deployment_preparation(self) -> bool:
        """Run complete deployment preparation"""
        print("🏗️ GAJA Assistant Production Deployment Preparation")
        print("=" * 60)
        
        success = True
        
        # Prepare server deployment
        success &= self.prepare_server_deployment()
        
        # Prepare client deployment
        success &= self.prepare_client_deployment()
        
        # Create deployment packages
        success &= self.create_deployment_packages()
        
        # Create deployment guide
        success &= self.create_deployment_guide()
        
        # Save deployment log
        self.save_deployment_log()
        
        # Final status
        if success:
            print("\n✅ DEPLOYMENT PREPARATION COMPLETE")
            print("📦 Packages created in packages/ directory")
            print("📋 See DEPLOYMENT_GUIDE.md for instructions")
            self.deployment_success = True
        else:
            print("\n❌ DEPLOYMENT PREPARATION FAILED")
            print("⚠️ Check deployment log for details")
        
        return success
    
    def save_deployment_log(self):
        """Save deployment log to file"""
        log_path = self.project_root / "deployment_log.json"
        log_data = {
            "timestamp": time.time(),
            "success": self.deployment_success,
            "steps": self.deployment_log
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Deployment log saved to: {log_path}")

def main():
    """Main deployment function"""
    deployment_manager = ProductionDeploymentManager()
    success = deployment_manager.run_full_deployment_preparation()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
