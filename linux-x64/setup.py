import os
import sys
import subprocess
import configparser

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
    print("\n[2/3] Installing dependencies from offline wheels...")
    
    if os.name == 'nt':
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")

    if not os.path.exists(req_file) or not os.path.exists(dep_dir):
        print(f"      [!] Error: 'requirements.txt' or 'dependencies/' folder missing.")
        sys.exit(1)

    try:
        subprocess.run([
            venv_python, "-m", "pip", "install",
            "--no-index", f"--find-links={dep_dir}",
            "-r", req_file
        ], cwd=base_dir, check=True)
        print("      -> Dependencies installed successfully.")
    except subprocess.CalledProcessError:
        print("      [!] Error installing dependencies. Exiting.")
        sys.exit(1)

    # ---------------------------------------------------------
    # 3. Create config.ini (With Defensive Sanitization)
    # ---------------------------------------------------------
    print("\n[3/3] System Configuration Setup")
    print("      Leave any field blank and press Enter if not required on your system.\n")
    
    # Process MTEX Path
    mtex_input = input("      Enter the absolute path to your MTEX installation:\n      > ").strip()
    mtex_path = mtex_input.rstrip("/\\") if mtex_input else ""
    
    if mtex_path and not os.path.exists(mtex_path):
        print(f"      [!] Warning: The directory '{mtex_path}' does not appear to exist.")

    # Process GCC Path
    print("\n      [Note: MATLAB and MTEX often clash over the C++ standard library on Linux clusters.]")
    gcc_input = input("      Enter the DIRECTORY containing a modern libstdc++.so.6 (for LD_PRELOAD):\n      > ").strip()
    
    gcc_path = ""
    if gcc_input:
        # Strip trailing slashes just in case they added one
        gcc_input = gcc_input.rstrip("/\\")
        
        # Check if they accidentally included the filename anyway
        if gcc_input.endswith("libstdc++.so.6"):
            gcc_path = gcc_input
        else:
            gcc_path = os.path.join(gcc_input, "libstdc++.so.6")
            
        if not os.path.exists(gcc_path):
            print(f"      [!] Warning: Could not locate '{gcc_path}' on this system.")

    # Write Configuration
    config = configparser.ConfigParser()
    config['ENVIRONMENT'] = {
        'MTEX_PATH': mtex_path,
        'LD_PRELOAD': gcc_path
    }

    config_file = os.path.join(base_dir, "config.ini")
    with open(config_file, 'w') as configfile:
        config.write(configfile)
        
    print(f"\n      -> Configuration saved to {config_file}")

    # ---------------------------------------------------------
    # Final Instructions
    # ---------------------------------------------------------
    print("\n==================================================")
    print(" [+] Setup Complete! You are ready to run.")
    print("==================================================")
    print(" To execute the pipeline, activate your new environment and run the wrapper:")
    if os.name == 'nt':
        print("    > venv\\Scripts\\activate")
    else:
        print("    > source venv/bin/activate")
    print("    > python first.py tests/Test1.ang")
    print("==================================================")

if __name__ == "__main__":
    main()