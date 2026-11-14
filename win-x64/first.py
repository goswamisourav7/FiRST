# win-x64 version

import os
import sys
import shutil
import subprocess
import argparse
import configparser
from datetime import datetime
import time
import json

# Cross-platform Peak RAM tracking (Windows x64 Win32 API vs. Unix resource)
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    def get_process_peak_ram_mb(proc):
        """Queries Windows x64 kernel for a child process's PeakWorkingSetSize in MB."""
        try:
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = wintypes.HANDLE(int(proc._handle))
            success = ctypes.windll.kernel32.K32GetProcessMemoryInfo(
                handle, ctypes.byref(pmc), pmc.cb
            )
            if not success:
                success = ctypes.windll.psapi.GetProcessMemoryInfo(
                    handle, ctypes.byref(pmc), pmc.cb
                )
            if success:
                return pmc.PeakWorkingSetSize / (1024.0 * 1024.0)
        except Exception:
            pass
        return 0.0
else:
    import resource


def main():
    # ---------------------------------------------------------
    # 1. Command-Line Argument Parsing
    # ---------------------------------------------------------
    parser = argparse.ArgumentParser(description="Five-fold Rotational Symmetry Detection Tool (FiRST)")
    parser.add_argument("target", help="Path to the .ang file OR the data directory (if skipping preprocess)")
    parser.add_argument("--skip-preprocess", action="store_true", help="Bypass MTEX .ang processing")
    parser.add_argument("--skip-plot", action="store_true", help="Bypass MTEX plotting")
    args = parser.parse_args()

    # ---------------------------------------------------------
    # 2. Directory Architecture & Path Resolution
    # ---------------------------------------------------------
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, "src")
    # Forward slashes ensure MATLAB addpath() works cleanly on Windows without escape issues
    src_dir_escaped = src_dir.replace("\\", "/")
    python_script = os.path.join(src_dir, "first_detect.py")

    target_path = os.path.abspath(args.target)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.skip_preprocess:
        # SWEEP MODE: Execute directly inside the provided target directory
        if not os.path.isdir(target_path):
            print("[!] Error: When using --skip-preprocess, target must be a directory containing CSVs.")
            sys.exit(1)
        run_out_dir = target_path
    else:
        # STANDARD MODE: Create a timestamped results folder
        if not os.path.isfile(target_path):
            print(f"[!] Error: Dataset file not found at {target_path}")
            sys.exit(1)
        dataset_name = os.path.splitext(os.path.basename(target_path))[0]
        run_out_dir = os.path.join(base_dir, "results", f"{dataset_name}_{timestamp}")
        os.makedirs(run_out_dir, exist_ok=True)

    os.chdir(run_out_dir)

    # ---------------------------------------------------------
    # 3. Setup Logging
    # ---------------------------------------------------------
    log_filename = f"FiRST_{timestamp}.log"

    def log_and_print(message=""):
        print(message)
        with open(log_filename, "a", encoding="utf-8", errors="replace") as log_file:
            log_file.write(message + "\n")

    log_and_print(f"--- FiRST Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    log_and_print(f"Target Dataset : {target_path}")
    log_and_print(f"Run Output Dir : {run_out_dir}")

    # Initialize benchmark trackers
    prep_time = 0.0
    det_time = 0.0
    plot_time = 0.0
    peak_ram_mb = 0.0

    # ---------------------------------------------------------
    # 4. Load System Configuration (config.ini)
    # ---------------------------------------------------------
    config_file = os.path.join(base_dir, "config.ini")
    config = configparser.ConfigParser()
    matlab_exe = "matlab"

    if os.path.exists(config_file):
        config.read(config_file, encoding="utf-8")
        mtex_path = config.get("ENVIRONMENT", "MTEX_PATH", fallback="").strip()
        cfg_matlab = config.get("ENVIRONMENT", "MATLAB_EXE", fallback="").strip()
        ld_preload = config.get("ENVIRONMENT", "LD_PRELOAD", fallback="").strip()

        if mtex_path:
            os.environ["MTEX_PATH"] = mtex_path
        if cfg_matlab:
            matlab_exe = cfg_matlab
        if ld_preload and os.name != "nt":
            os.environ["LD_PRELOAD"] = ld_preload
    else:
        log_and_print("[!] Notice: config.ini not found. Using system defaults.")

    # Ensure UTF-8 I/O across child processes on Windows
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["ANG_FILE_PATH"] = target_path

    # Build OS-appropriate headless MATLAB command prefix (-nodisplay is invalid on Windows)
    if os.name == "nt":
        matlab_base_cmd = [matlab_exe, "-nosplash", "-nodesktop", "-batch"]
    else:
        matlab_base_cmd = [matlab_exe, "-nodisplay", "-nosplash", "-nodesktop", "-batch"]

    # ---------------------------------------------------------
    # 5. Execute MATLAB Pre-processing (Physical File Bypass)
    # ---------------------------------------------------------
    if not args.skip_preprocess:
        log_and_print("\n--- STARTING PRE-PROCESSING ---")
        if not shutil.which(matlab_exe) and not os.path.isfile(matlab_exe):
            log_and_print(f"[!] Error: MATLAB executable '{matlab_exe}' not found on PATH or in config.ini.")
            sys.exit(1)

        matlab_cmd = f"addpath('{src_dir_escaped}'); first_preprocess; quit force;"
        matlab_raw_log = os.path.join(run_out_dir, "matlab_raw_output.txt")
        
        with open(matlab_raw_log, "w", encoding="utf-8", errors="replace") as out_file:
            matlab_process = subprocess.Popen(
                matlab_base_cmd + [matlab_cmd],
                stdout=out_file,
                stderr=subprocess.STDOUT
            )
            t0 = time.time()
            matlab_process.wait()
            prep_time = time.time() - t0
            if os.name == "nt":
                peak_ram_mb = max(peak_ram_mb, get_process_peak_ram_mb(matlab_process))
        
        if os.path.exists(matlab_raw_log):
            with open(matlab_raw_log, "r", encoding="utf-8", errors="replace") as f:
                matlab_output = f.read().strip()
                if matlab_output:
                    log_and_print(matlab_output)
        
        if matlab_process.returncode != 0:
            log_and_print(f"\n[!] MATLAB encountered an error (Exit code: {matlab_process.returncode}).")
            sys.exit(matlab_process.returncode)
        
        log_and_print("\nPre-processing complete. CSVs generated.")
    else:
        log_and_print("\n--- SKIPPING PRE-PROCESSING (CSV Bypass) ---")

    # ---------------------------------------------------------
    # 6. Execute Python FFRS Detection (Real-Time Stream)
    # ---------------------------------------------------------
    log_and_print("\n--- STARTING DETECTION ---")

    detect_process = subprocess.Popen(
        [sys.executable, python_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    t0 = time.time()
    for line in detect_process.stdout:
        log_and_print(line.strip())

    detect_process.wait()
    det_time = time.time() - t0
    if os.name == "nt":
        peak_ram_mb = max(peak_ram_mb, get_process_peak_ram_mb(detect_process))

    if detect_process.returncode != 0:
        log_and_print(f"\n[!] Python detection script encountered an error (Exit code: {detect_process.returncode}).")
        sys.exit(detect_process.returncode)

    # ---------------------------------------------------------
    # 7. Execute MATLAB Plotting
    # ---------------------------------------------------------
    if not args.skip_plot:
        if os.path.exists("ffrs_clusters.csv"):
            log_and_print("\n--- GENERATING FFRS VISUALIZATIONS ---")
            plot_cmd = f"addpath('{src_dir_escaped}'); first_plot; quit force;"
            plot_log = os.path.join(run_out_dir, "matlab_plot_output.txt")    
            with open(plot_log, "w", encoding="utf-8", errors="replace") as out_file:
                plot_process = subprocess.Popen(
                    matlab_base_cmd + [plot_cmd],
                    stdout=out_file,
                    stderr=subprocess.STDOUT
                )
                t0 = time.time()
                plot_process.wait()
                plot_time = time.time() - t0
                if os.name == "nt":
                    peak_ram_mb = max(peak_ram_mb, get_process_peak_ram_mb(plot_process))

            if os.path.exists(plot_log):
                with open(plot_log, "r", encoding="utf-8", errors="replace") as f:
                    plot_output = f.read().strip()
                    if plot_output:
                        log_and_print(plot_output)

            if plot_process.returncode != 0:
                log_and_print(f"\n[!] MATLAB plotting encountered an error (Exit code: {plot_process.returncode}).")
                sys.exit(plot_process.returncode)

            log_and_print("Figures exported successfully to the results directory.")
    else:
        log_and_print("\n--- SKIPPING FFRS VISUALIZATIONS ---")

    # ---------------------------------------------------------
    # 8. Cleanup Temporary Files
    # ---------------------------------------------------------
    workspace_file = "mtex_workspace.mat"
    if os.path.exists(workspace_file):
        os.remove(workspace_file)
        log_and_print(f"\nCleanup: Deleted {workspace_file} to free disk space.")

    # ---------------------------------------------------------
    # 9. Performance Summary
    # ---------------------------------------------------------
    total_time = prep_time + det_time + plot_time

    if os.name != "nt":
        peak_ram_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0

    log_and_print("\n==================================================")
    log_and_print("              PERFORMANCE BENCHMARKS              ")
    log_and_print("==================================================")
    log_and_print(f" Phase 1 (Pre-processing) : {prep_time:>8.2f} sec")
    log_and_print(f" Phase 2 (Detection)      : {det_time:>8.2f} sec")
    if os.path.exists("ffrs_clusters.csv") and not args.skip_plot:
        log_and_print(f" Phase 3 (Plotting)       : {plot_time:>8.2f} sec")
    else:
        log_and_print(f" Phase 3 (Plotting)       :  Skipped (No FFRS)")
    log_and_print("--------------------------------------------------")
    log_and_print(f" Total Active Compute     : {total_time:>8.2f} sec")
    log_and_print(f" Peak RAM Utilization     : {peak_ram_mb:>8.2f} MB")
    log_and_print("==================================================")

    metrics = {
        "Prep_Time_s": round(prep_time, 2),
        "Det_Time_s": round(det_time, 2),
        "Plot_Time_s": round(plot_time, 2),
        "Total_Time_s": round(total_time, 2),
        "Peak_RAM_MB": round(peak_ram_mb, 2)
    }
    with open(os.path.join(run_out_dir, "pipeline_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
    
    log_and_print("\nPipeline execution finished successfully.")
    log_and_print(f"Log saved to: {os.path.join(run_out_dir, log_filename)}")

if __name__ == "__main__":
    main()
