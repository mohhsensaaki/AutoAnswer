# NewAfzzinaAI Deployment Scripts

This directory contains deployment scripts for the NewAfzzinaAI FastAPI application, supporting both Linux/Unix systems and Windows.

## Scripts Overview

### For Linux/Unix Systems
- `deploy.sh` - Main deployment script for Linux/Unix
- `stop.sh` - Stop script for Linux/Unix

### For Windows Systems
- `deploy.ps1` - Main deployment script for Windows (PowerShell)
- `stop.ps1` - Stop script for Windows (PowerShell)

## Usage

### Windows (PowerShell)

#### Deploy and Run Directly
```powershell
.\scripts\deploy.ps1
```

#### Deploy as Windows Service (requires Administrator)
```powershell
.\scripts\deploy.ps1 -AsService
```

#### Stop Application
```powershell
.\scripts\stop.ps1
```

#### Get Help
```powershell
.\scripts\deploy.ps1 -Help
.\scripts\stop.ps1 -Help
```

### Linux/Unix (Bash)

#### Deploy and Run as Service
```bash
./scripts/deploy.sh
```

#### Stop Application
```bash
./scripts/stop.sh
```

## What the Deployment Scripts Do

### 1. **Environment Checks**
- ✅ Verify Python 3.8+ is installed
- ✅ Verify pip is available
- ✅ Check system compatibility

### 2. **Virtual Environment Setup**
- 🔧 Create virtual environment (`env/`)
- 🔧 Activate virtual environment
- 🔧 Upgrade pip to latest version

### 3. **Dependency Installation**
- 📦 Install all requirements from `requirements.txt`
- 📦 Ensure all dependencies are compatible

### 4. **Service Setup**
- 🚀 **Linux**: Create systemd service
- 🚀 **Windows**: Create Windows service (with NSSM)
- 🚀 **Alternative**: Run directly if service setup fails

### 5. **Application Startup**
- ▶️ Start the FastAPI application
- ▶️ Verify application is running
- ▶️ Display useful information and endpoints

## Application Endpoints

Once deployed, your application will be available at:

- **Main Application**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Service Management

### Windows Service Management
```powershell
# Start service
Start-Service -Name NewAfzzinaAI

# Stop service
Stop-Service -Name NewAfzzinaAI

# Restart service
Restart-Service -Name NewAfzzinaAI

# Check status
Get-Service -Name NewAfzzinaAI

# View service details
Get-WmiObject -Class Win32_Service | Where-Object {$_.Name -eq "NewAfzzinaAI"}
```

### Linux Service Management
```bash
# Start service
sudo systemctl start newafzzinaai

# Stop service
sudo systemctl stop newafzzinaai

# Restart service
sudo systemctl restart newafzzinaai

# Check status
sudo systemctl status newafzzinaai

# View logs
sudo journalctl -u newafzzinaai -f
```

## Testing the Deployment

### Windows PowerShell
```powershell
# Test health endpoint
Invoke-RestMethod -Uri http://localhost:8000/health

# Test with detailed output
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object StatusCode, Content
```

### Linux/Unix
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test with detailed output
curl -v http://localhost:8000/health
```

## Troubleshooting

### Common Issues

#### Python Not Found
- **Windows**: Install Python from https://python.org/downloads/
- **Linux**: `sudo apt-get install python3 python3-pip` (Ubuntu/Debian)

#### Permission Denied (Linux)
```bash
# Make scripts executable
chmod +x scripts/deploy.sh scripts/stop.sh
```

#### Service Won't Start
1. Check logs (see Service Management section)
2. Verify all dependencies are installed
3. Check port 8000 is not already in use
4. Ensure virtual environment is properly activated

#### Port Already in Use
```bash
# Find process using port 8000
netstat -an | grep :8000

# Kill process (replace PID with actual process ID)
kill -9 <PID>
```

### Windows-Specific Issues

#### NSSM Not Found
The script will try to install NSSM automatically. If this fails:
1. Download NSSM from https://nssm.cc/
2. Extract to a directory in your PATH
3. Run the deployment script again

#### PowerShell Execution Policy
If you get execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## File Structure After Deployment

```
NewAfzzinaAI/
├── env/                    # Virtual environment
├── scripts/
│   ├── deploy.sh          # Linux deployment script
│   ├── deploy.ps1         # Windows deployment script
│   ├── stop.sh            # Linux stop script
│   ├── stop.ps1           # Windows stop script
│   └── README.md          # This file
├── main.py                # FastAPI application
├── requirements.txt       # Python dependencies
├── run_app.bat           # Windows batch file (created by deploy.ps1)
└── app.log               # Application logs (if running directly)
```

## Environment Variables

The application supports the following environment variables:
- `IS_PRODUCTION`: Set to "yes" for production logging
- `LOG_URL`: Directory for log files (default: current directory)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review the application logs
3. Verify all prerequisites are met
4. Check the FastAPI documentation at http://localhost:8000/docs

---

Happy coding! 🚀 