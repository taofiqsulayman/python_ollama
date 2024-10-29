import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)

def create_virtual_env():
    if not os.path.exists('venv'):
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
        print("Created virtual environment")
    else:
        print("Virtual environment already exists")

def install_requirements():
    if os.name == 'nt':  # Windows
        pip_path = 'venv\\Scripts\\pip'
    else:  # Unix/Linux/MacOS
        pip_path = 'venv/bin/pip'
    
    subprocess.run([pip_path, 'install', '-r', 'requirements.txt'])
    print("Installed requirements")

def setup_env_file():
    if not os.path.exists('.env'):
        template_path = Path('.env.template')
        if template_path.exists():
            template_path.rename('.env')
            print("Created .env file from template")
        else:
            print("Warning: .env.template not found")
    else:
        print(".env file already exists")

def main():
    print("Setting up development environment...")
    check_python_version()
    create_virtual_env()
    install_requirements()
    setup_env_file()
    print("\nSetup complete! Next steps:")
    print("1. Configure your .env file with appropriate values")
    print("2. Activate virtual environment:")
    print("   - Windows: .\\venv\\Scripts\\activate")
    print("   - Unix/Linux/MacOS: source venv/bin/activate")
    print("3. Run the application: streamlit run app.py")

if __name__ == "__main__":
    main()