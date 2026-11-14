# win-x64 version

import os
import sys
import shutil
import subprocess
import configparser

def clean_input_path(raw_str):
    """Strips whitespace, surrounding quotes (Windows 'Copy as path'), and trailing slashes."""
    if not raw_str:
        return ""
    cleaned = raw_str.strip().strip('"').strip("'").rstrip("/\\")
    return os.path.normpath(cleaned) if cleaned else ""

def main():
    print("=======================================================================================")
    print("      Five-fold Rotational Symmetry Detection Tool (FiRST): One-Time Setup Wizard      ")
    print("=======================================================================================")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(base_dir, "venv")
    req_file = os.path.join(base_dir, "requirements.txt")
    dep_dir = os.path.join(base_dir, "dependencies")

    # ---------------------------------------------------------
    # 1. Create Virtual Environment
    # ---------------------------------------------------------
    print("\n[1/3] Creating Python virtual environment ('venv')...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=base_dir, check=True)
        print("      -> Virtual environment created successfully.")
    except subprocess.CalledProcessError:
        print("      [!] Error creating virtual environment. Exiting.")
        sys.exit(1)

    # ---------------------------------------------------------
    # 2. Install Dependencies
    # ---------------------------------------------------------
    print("\n[2/3] Installing Python dependencies...")
    
    if os.name == "nt":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(req_file):
        print("      [!] Error: 'requirements.txt' is missing.")
        sys.exit(1)

    installed = False
    if os.path.exists(dep_dir) and os.listdir(dep_dir):
        print("      -> Attempting offline installation from 'dependencies/'...")
        res = subprocess.run([
            venv_python, "-m", "pip", "install",
            "--no-index", f"--find-links={dep_dir}",
            "-r", req_file
        ], cwd=base_dir)
        if res.returncode == 0:
            installed = True
            print("      -> Offline dependencies installed successfully.")
        else:
            print("      [!] Notice: Offline wheels did not match this OS/Python version. Falling back to PyPI...")

    if not installed:
        try:
            subprocess.run([
                venv_python, "-m", "pip", "install", "-r", req_file
            ], cwd=base_dir, check=True)
            print("      -> Dependencies installed successfully from PyPI.")
        except subprocess.CalledProcessError:
            print("      [!] Error installing dependencies. Ensure internet access or place win_amd64 wheels in 'dependencies/'.")
            sys.exit(1)

    # ---------------------------------------------------------
    # 3. Create config.ini (With Defensive Sanitization)
    # ---------------------------------------------------------
    print("\n[3/3] System Configuration Setup")
    print("      Leave any field blank and press Enter if not required on your system.\n")
    
    # Process MTEX Path
    mtex_input = input("      Enter the absolute path to your MTEX installation:\n      > ")
    mtex_path = clean_input_path(mtex_input)
    
    if mtex_path and not os.path.exists(mtex_path):
        print(f"      [!] Warning: The directory '{mtex_path}' does not appear to exist.")

    # Process MATLAB executable path (Especially useful on Windows if not in PATH)
    default_matlab = shutil.which("matlab")
    matlab_exe = "matlab"
    if not default_matlab:
        print("\n      [Notice: 'matlab' was not detected on your system PATH.]")
        matlab_input = input("      Enter the full path to 'matlab.exe' (or its 'bin' folder):\n      > ")
        matlab_clean = clean_input_path(matlab_input)
        if matlab_clean:
            if os.path.isdir(matlab_clean):
                exe_name = "matlab.exe" if os.name == "nt" else "matlab"
                matlab_exe = os.path.join(matlab_clean, exe_name)
            else:
                matlab_exe = matlab_clean
            if not os.path.exists(matlab_exe):
                print(f"      [!] Warning: Could not locate '{matlab_exe}'.")

    # Process GCC Path (Linux Only)
    gcc_path = ""
    if os.name != "nt":
        print("\n      [Note: MATLAB and MTEX often clash over the C++ standard library on Linux clusters.]")
        gcc_input = input("      Enter the DIRECTORY containing a modern libstdc++.so.6 (for LD_PRELOAD):\n      > ")
        gcc_clean = clean_input_path(gcc_input)
        if gcc_clean:
            gcc_path = gcc_clean if gcc_clean.endswith("libstdc++.so.6") else os.path.join(gcc_clean, "libstdc++.so.6")
            if not os.path.exists(gcc_path):
                print(f"      [!] Warning: Could not locate '{gcc_path}' on this system.")

    # Write Configuration
    config = configparser.ConfigParser()
    config["ENVIRONMENT"] = {
        "MTEX_PATH": mtex_path,
        "MATLAB_EXE": matlab_exe,
        "LD_PRELOAD": gcc_path
    }

    config_file = os.path.join(base_dir, "config.ini")
    with open(config_file, "w", encoding="utf-8") as configfile:
        config.write(configfile)
        
    print(f"\n      -> Configuration saved to {config_file}")

    # ---------------------------------------------------------
    # Final Instructions
    # ---------------------------------------------------------
    print("\n==================================================")
    print(" [+] Setup Complete! You are ready to run.")
    print("==================================================")
    print(" To execute the pipeline, activate your new environment and run the wrapper:")
    if os.name == "nt":
        print("    CMD        > venv\\Scripts\\activate.bat")
        print("    PowerShell > .\\venv\\Scripts\\Activate.ps1")
        print("    Run        > python first.py tests\\Test1.ang")
    else:
        print("    > source venv/bin/activate")
        print("    > python first.py tests/Test1.ang")
    print("==================================================")

if __name__ == "__main__":
    main()
