import os
import sys
import subprocess
import argparse
import configparser
from datetime import datetime
import time
import json
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
    matlab_script = os.path.join(src_dir, "first_preprocess.m")
    python_script = os.path.join(src_dir, "first_detect.py")

    target_path = os.path.abspath(args.target)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.skip_preprocess:
        # SWEEP MODE: Execute directly inside the provided target directory
        if not os.path.isdir(target_path):
            print(f"[!] Error: When using --skip-preprocess, target must be a directory containing CSVs.")
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
        with open(log_filename, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")

    log_and_print(f"--- FiRST Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    log_and_print(f"Target Dataset : {target_path}")
    log_and_print(f"Run Output Dir : {run_out_dir}")

    # Initialize benchmark trackers
    prep_time = 0.0
    det_time = 0.0
    plot_time = 0.0

    # ---------------------------------------------------------
    # 4. Load System Configuration (config.ini)
    # ---------------------------------------------------------
    config_file = os.path.join(base_dir, "config.ini")
    config = configparser.ConfigParser()

    if os.path.exists(config_file):
        config.read(config_file)
        mtex_path = config.get("ENVIRONMENT", "MTEX_PATH", fallback="").strip()
        ld_preload = config.get("ENVIRONMENT", "LD_PRELOAD", fallback="").strip()

        if mtex_path:
            os.environ["MTEX_PATH"] = mtex_path
        if ld_preload:
            os.environ["LD_PRELOAD"] = ld_preload
    else:
        log_and_print("[!] Notice: config.ini not found. Using system defaults.")

    # Pass dataset path to MATLAB via OS environment variable
    os.environ["ANG_FILE_PATH"] = target_path

    # ---------------------------------------------------------
    # 5. Execute MATLAB Pre-processing (Physical File Bypass)
    # ---------------------------------------------------------
    if not args.skip_preprocess:
        log_and_print("\n--- STARTING PRE-PROCESSING ---")
        os.environ["ANG_FILE_PATH"] = target_path
        # Keep working directory in run_out_dir while adding src/ to MATLAB's search path
        src_dir_escaped = src_dir.replace("\\", "/")
        matlab_cmd = f"addpath('{src_dir_escaped}'); first_preprocess; quit force;"
        matlab_raw_log = os.path.join(run_out_dir, "matlab_raw_output.txt")
        
        # Route output directly to a file to prevent Python memory pipe deadlocks
        with open(matlab_raw_log, "w", encoding="utf-8") as out_file:
            matlab_process = subprocess.Popen(
                ["matlab", "-nodisplay", "-nosplash", "-nodesktop", "-batch", matlab_cmd],
                stdout=out_file,
                stderr=subprocess.STDOUT
            )
            t0 = time.time()
            matlab_process.wait()
            prep_time = time.time() - t0
        
        # Flush completed MATLAB logs to the primary pipeline log
        if os.path.exists(matlab_raw_log):
            with open(matlab_raw_log, "r", encoding="utf-8") as f:
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
    # 6. Execute Python ISRO Detection (Real-Time Stream)
    # ---------------------------------------------------------
    log_and_print("\n--- STARTING DETECTION ---")

    detect_process = subprocess.Popen(
        [sys.executable, python_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    t0 = time.time()
    for line in detect_process.stdout:
        log_and_print(line.strip())

    detect_process.wait()
    det_time = time.time() - t0

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
            with open(plot_log, "w", encoding="utf-8") as out_file:
                plot_process = subprocess.Popen(
                    ["matlab", "-nodisplay", "-nosplash", "-nodesktop", "-batch", plot_cmd],
                    stdout=out_file,
                    stderr=subprocess.STDOUT
                )
                t0 = time.time()
                plot_process.wait()
                plot_time = time.time() - t0
                        
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

    peak_ram_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0

    log_and_print("\n==================================================")
    log_and_print("              PERFORMANCE BENCHMARKS              ")
    log_and_print("==================================================")
    log_and_print(f" Phase 1 (Pre-processing) : {prep_time:>8.2f} sec")
    log_and_print(f" Phase 2 (Detection)      : {det_time:>8.2f} sec")
    if os.path.exists("ffrs_clusters.csv"):
        log_and_print(f" Phase 3 (Plotting)       : {plot_time:>8.2f} sec")
    else:
        log_and_print(f" Phase 3 (Plotting)       :  Skipped (No ISRO)")
    log_and_print("--------------------------------------------------")
    log_and_print(f" Total Active Compute     : {total_time:>8.2f} sec")
    log_and_print(f" Peak RAM Utilization           : {peak_ram_mb:>8.2f} MB")
    log_and_print("==================================================")

    metrics = {
        "Prep_Time_s": round(prep_time, 2),
        "Det_Time_s": round(det_time, 2),
        "Plot_Time_s": round(plot_time, 2),
        "Total_Time_s": round(total_time, 2),
        "Peak_RAM_MB": round(peak_ram_mb, 2)
    }
    with open(os.path.join(run_out_dir, "pipeline_metrics.json"), "w") as f:
        json.dump(metrics, f)
    
    log_and_print("\nPipeline execution finished successfully.")
    log_and_print(f"Log saved to: {os.path.join(run_out_dir, log_filename)}")

if __name__ == "__main__":
    main()
