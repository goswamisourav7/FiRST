# FiRST: Five-fold Rotational Symmetry Detection Tool

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![MATLAB](https://img.shields.io/badge/MATLAB-R2021a%2B-orange.svg)](https://www.mathworks.com/products/matlab.html)
[![MTEX](https://img.shields.io/badge/MTEX-6.0%2B-green.svg)](https://mtex-toolbox.github.io/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20HPC%20%7C%20Windows%20x64-lightgrey.svg)]()
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![DOI](https://zenodo.org/badge/1457735093.svg)](https://doi.org/10.5281/zenodo.24367800)

**FiRST** (*Five-fold Rotational Symmetry Detection Tool*) is an automated, high-throughput crystallographic analysis pipeline designed to detect, verify, and visualize five-fold $\Sigma3$ twin clusters—often associated with icosahedral short-range order (ISRO)-mediated nucleation or growth accidents—in Face-Centered Cubic (FCC) microstructures from Electron Backscatter Diffraction (EBSD) datasets.

FiRST combines the crystallographic grain-reconstruction capabilities of **MATLAB/MTEX** with a fast **Python** graph-theoretic and quaternion-algebraic detection engine. It is engineered to run headlessly on High-Performance Computing (HPC) Linux clusters as well as local Windows x64 workstations.

---

## Table of Contents

1. [Repository Architecture](#1-repository-architecture)
2. [System Requirements & Prerequisites](#2-system-requirements--prerequisites)
3. [Downloading & Installation](#3-downloading--installation)
   - [3.1 Cloning the Repository](#31-cloning-the-repository)
   - [3.2 Automated Setup Wizard (`setup.py`)](#32-automated-setup-wizard-setuppy)
   - [3.3 Manual Configuration (`config.ini`)](#33-manual-configuration-configini)
4. [Running the Pipeline](#4-running-the-pipeline)
   - [4.1 Standard Execution (End-to-End `.ang` Analysis)](#41-standard-execution-end-to-end-ang-analysis)
   - [4.2 Command-Line Arguments & Bypass Modes](#42-command-line-arguments--bypass-modes)
5. [Output Files & Data Dictionary](#5-output-files--data-dictionary)
6. [Modifying, Extending, & Reusing the Tool](#6-modifying-extending--reusing-the-tool)
   - [6.1 Adjusting Crystallographic Tolerances](#61-adjusting-crystallographic-tolerances)
   - [6.2 Reusing `first_detect.py` with External Software (Dream.3D / OIM / Aztec)](#62-reusing-first_detectpy-with-external-software-dream3d--oim--aztec)
   - [6.3 Customizing MTEX Plots](#63-customizing-mtex-plots)
7. [Troubleshooting & HPC Notes](#7-troubleshooting--hpc-notes)
8. [Citing FiRST](#8-citing-first)
9. [License & Terms of Reuse](#9-license--terms-of-reuse)

---

## 1. Repository Architecture

```text
FiRST/
├── os(linux-x64 or win-x64)/
│   ├── dependencies/                 # (Optional) Offline Python wheel (.whl) archives
│   ├── examples/                     # Sample .ang datasets for verification
│   ├── src/
│   │   ├── first_preprocess.m        # Phase 1: MTEX EBSD import, grain segmentation & pole extraction
│   │   ├── first_detect.py           # Phase 2: Hierarchical pole clustering & quaternion DFS engine
│   │   ├── first_plot.m              # Phase 3: Automated MTEX locator, IPF & Pole Figure plotting
│   ├── first.py                      # Primary CLI orchestrator
│   ├── requirements.txt              # Pinned Python package dependencies
│   ├── setup.py                      # One-time setup wizard (venv, dependencies, config.ini)
│   └── results/                      # (After execution) Auto-generated timestamped output directories

```

---

## 2. System Requirements & Prerequisites

* **Operating System**:
  * **Windows**: Windows 10 / 11 (x64) or Windows Server (x64).
  * **Linux**: Ubuntu, RHEL, Rocky Linux, CentOS, or OpenHPC clusters (x86_64).
* **MATLAB**: MATLAB R2021a or newer (requires the `-batch` non-interactive execution mode).
* **MTEX Toolbox**: [MTEX](https://mtex-toolbox.github.io/) version **6.0.0 or newer** (tested extensively on MTEX 6.1.0).
* **Python**: Python **3.9 – 3.13** (64-bit).
* **Python Libraries** (automatically installed via `setup.py`):
  * `numpy` ($\ge 2.0$)
  * `scipy` ($\ge 1.14$)
  * `pandas` ($\ge 2.2$)
  * `networkx` ($\ge 3.3$)
  * `matplotlib` ($\ge 3.9$)

---

## 3. Downloading & Installation

### 3.1 Cloning the Repository

Download the latest release archive from GitHub or clone the repository via Git:

```bash
git clone https://github.com/goswamisourav7/FiRST.git
cd linux-x64 (or cd win-x64)
```

### 3.2 Automated Setup Wizard (`setup.py`)

FiRST includes an interactive, cross-platform setup wizard that creates an isolated Python virtual environment (`venv`), installs all required dependencies (either from the local `dependencies/` offline cache or via PyPI), and configures your `config.ini` file.

Run the setup script using your system Python:

```bash
python setup.py
```

During the wizard prompts:
1. **MTEX Installation Path**: Provide the absolute path to your MTEX folder (e.g., `C:\Users\username\Documents\MATLAB\mtex-6.1.0` on Windows or `/home/username/mtex-6.1.0` on Linux).
2. **MATLAB Executable Path** *(prompted if `matlab` is not already on your system `PATH`)*: Provide the full path to `matlab.exe` (e.g., `C:\Program Files\MATLAB\R2024b\bin\matlab.exe`) or its `bin` directory.
3. **Linux GCC Standard Library Path** *(Linux only)*: On Linux HPC clusters where MATLAB's bundled `libstdc++.so.6` conflicts with newer system compilers or MTEX MEX binaries, provide the directory containing your system or module `libstdc++.so.6` (e.g., `/opt/ohpc/pub/compiler/gcc/12.3.0/lib64`). Leave blank if not required.

### 3.3 Manual Configuration (`config.ini`)

If you prefer to configure your environment manually without running `setup.py`, create a file named `config.ini` in the appropriate os directory of the repository:

**Windows x64 Example (`config.ini`):**
```ini
[ENVIRONMENT]
MTEX_PATH = C:\Users\Researcher\Documents\MATLAB\mtex-6.1.0
MATLAB_EXE = C:\Program Files\MATLAB\R2024b\bin\matlab.exe
LD_PRELOAD = 
```

**Linux HPC Example (`config.ini`):**
```ini
[ENVIRONMENT]
MTEX_PATH = /home/researcher/software/mtex-6.1.0
MATLAB_EXE = matlab
LD_PRELOAD = /opt/ohpc/pub/compiler/gcc/12.3.0/lib64/libstdc++.so.6
```

---

## 4. Running the Pipeline

Before running FiRST, activate the Python virtual environment created during setup:

* **Windows (Command Prompt)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
* **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### 4.1 Standard Execution (End-to-End `.ang` Analysis)

Pass the path of any `.ang` EBSD dataset to `first.py`:

```bash
python first.py examples/Sample_data.ang
```

This creates a timestamped folder inside `results/<DatasetName>_<YYYYMMDD_HHMMSS>/`, executes all three phases (MTEX pre-processing $\rightarrow$ Python detection $\rightarrow$ MTEX plotting), cleans up temporary `.mat` cache files, and outputs a full performance and statistical summary.

### 4.2 Command-Line Arguments & Bypass Modes

`first.py` supports modular flags for rapid parameter sweeps and re-analysis:

```text
usage: first.py [-h] [--skip-preprocess] [--skip-plot] target

Five-fold Rotational Symmetry Detection Tool (FiRST)

positional arguments:
  target             Path to the .ang file OR the data directory (if skipping preprocess)

options:
  -h, --help         Show this help message and exit
  --skip-preprocess  Bypass MTEX .ang processing (target must be a directory with pre-computed CSVs)
  --skip-plot        Bypass MTEX plotting (runs pre-processing and/or Python detection only)
```

**Common Workflows:**
* **Fast Screening (No Cluster Plots)**: Run pre-processing and detection to get counts, CSVs, and the $\langle 110 \rangle$ pole coincidence histogram without spending time rendering individual MTEX cluster figures:
  ```bash
  python first.py path/to/dataset.ang --skip-plot
  ```
* **Re-running Detection on Pre-processed CSVs**: If you already have a directory containing `grain_pairs.csv`, `grain_attributes.csv`, `dataset_stats.csv`, and `twin_boundary_lengths.csv` (for instance, from a previous run or a synthetic generator):
  ```bash
  python first.py results/Test1_20261116_120000 --skip-preprocess --skip-plot
  ```

---

## 5. Output Files & Data Dictionary

Every run creates a self-contained directory inside `results/` containing the following artifacts:

### A. Primary Detection & Statistical Outputs
| Filename | Generated By | Description |
| :--- | :--- | :--- |
| `ffrs_clusters.csv` | `first_detect.py` | **Master Detection Table.** Lists each unique five-fold cluster (`ClusterID`), the 5 ordered MTEX grain IDs (`G1`–`G5`), and the topological classification (`Closed` vs. `Open`). |
| `pole_frequencies.csv` | `first_detect.py` | Tabulates the number of twinned grain pairs sharing a coincident $\langle 110 \rangle$ pole versus frequency across the entire dataset. |
| `pole_frequency_histogram.png` | `first_detect.py` | Log-scale bar chart of $\langle 110 \rangle$ pole coincidence multiplicity. |
| `FiRST_<timestamp>.log` | `first.py` | Complete execution transcript, including per-cluster pole centroids, maximum angular spread (in degrees), open-chain $\Sigma3$ deviation angles, global dataset statistics, and runtime/RAM benchmarks. |
| `pipeline_metrics.json` | `first.py` | Machine-readable JSON summary of execution times (`Prep_Time_s`, `Det_Time_s`, `Plot_Time_s`, `Total_Time_s`) and peak memory usage (`Peak_RAM_MB`). |

### B. Crystallographic Visualizations (Generated when `--skip-plot` is omitted)
| Filename | Description |
| :--- | :--- |
| `Dataset_Master_Locator_Map.png` | Full-dataset IPF map with black HAGBs ($> 15^\circ$), white LAGBs ($2^\circ\text{–}15^\circ$), and labeled bounding boxes pinpointing every detected five-fold cluster. |
| `IPF_Color_Key_<Phase>.png` | Inverse Pole Figure color key legend for each detected crystal phase (projected parallel to the specimen $Z$-axis). |
| `Cluster_<X>_Fig1_Cluster_IPF.png` | High-magnification IPF map of the 5 constituent grains in `Cluster <X>`, with $\Sigma3$ twin boundaries highlighted in **red**, $\Sigma9$ boundaries in **green**, LAGBs in **white**, and general HAGBs in **black**. |
| `Cluster_<X>_Fig2_Cluster_110_PF.png` | $\langle 110 \rangle$ Pole Figure of the 5 cluster grains (color-matched to their IPF colors) overlaid with dashed red great circles representing the inter-grain misorientation planes intersecting at the shared $\langle 110 \rangle$ pole. |
| `Cluster_<X>_Fig3_Cluster_111_PF.png` | $\langle 111 \rangle$ Pole Figure of the 5 cluster grains showing the distribution of twinning planes around the common axis. |

### C. Intermediate Crystallographic Tables
| Filename | Schema / Columns | Description |
| :--- | :--- | :--- |
| `dataset_stats.csv` | `TotalGrains, TotalBoundaryLength, TotalTwinLength` | Global scalar metrics for the entire EBSD map. |
| `grain_attributes.csv` | `grainID, q0, q1, q2, q3, hasSigma3, nSigma3Nbrs` | Unit quaternion components ($q_0$ scalar, $q_1, q_2, q_3$ vector) and $\Sigma3$ neighbor counts for every segmented FCC grain. |
| `grains.csv` | `GrainID, PoleID, X, Y, Z` | Specimen-frame Cartesian coordinates of the 6 symmetrically unique $\langle 110 \rangle$ poles for all twinned grains. |
| `grain_pairs.csv` | `Grain1, Grain2, PoleID, p1x, p1y, p1z, p2x, p2y, p2z` | Coincident $\langle 110 \rangle$ unit vectors shared between adjacent $\Sigma3$-twinned grain pairs ($\le 5.0^\circ$ misalignment). |
| `twin_boundary_lengths.csv` | `Grain1, Grain2, BoundaryLength` | Physical boundary trace length for every unique $\Sigma3$ grain pair. |

---

## 6. Modifying, Extending, & Reusing the Tool

FiRST is designed with a decoupled, file-based interface between the crystallographic pre-processor and the graph-theoretic detector, making it straightforward to customize or integrate into external workflows.

### 6.1 Adjusting Crystallographic Tolerances

1. **Pole Coincidence & Brandon Tolerances (`src/first_detect.py`)**:
   Open `src/first_detect.py` and modify the constants at the top of the file:
   ```python
   ANGLE_TOL_DEG = 5.0   # Maximum angular spread (deg) for shared <110> poles in a cluster
   SIGMA3_TOL_DEG = 8.66 # Brandon criterion tolerance (deg) for open-chain Sigma-3 verification
   ```
   *(Note: If you increase `ANGLE_TOL_DEG` above $5.0^\circ$, also update `tolPole = 5 * degree;` on line 140 of `src/first_preprocess.m` to match).*

2. **Grain Reconstruction Thresholds (`src/first_preprocess.m`)**:
   To adjust the minimum grain size or misorientation threshold used during MTEX grain segmentation, edit line 44 of `src/first_preprocess.m`:
   ```matlab
   [grains_all, ebsd.grainId] = calcGrains(ebsd, 'angle', 2*degree, 'minPixel', 5);
   ```

### 6.2 Reusing `first_detect.py` with External Software (Dream.3D / OIM / Aztec)

Because `src/first_detect.py` operates strictly on standard CSV files, you can use FiRST's Python detection engine **without MATLAB or MTEX** by exporting the four required CSV files (`grain_pairs.csv`, `grain_attributes.csv`, `dataset_stats.csv`, and `twin_boundary_lengths.csv`) from any third-party crystallographic software (such as Dream.3D, EDAX OIM Analysis, Oxford Instruments AZtecCrystal, or `orix`) and running:

```bash
python first.py /path/to/exported_csv_directory --skip-preprocess --skip-plot
```

### 6.3 Customizing MTEX Plots

All visual styling—including boundary line widths, colors, bounding-box margins, and specimen coordinate conventions—is centralized in `src/first_plot.m`:
* **Coordinate Frame**: Controlled via `setMTEXpref('xAxisDirection', 'east')`, `setMTEXpref('yAxisDirection', 'south')`, and `ebsd.plottingConvention = plottingConvention(-zvector, xvector);`.
* **Image Resolution**: All figures are exported at $300\text{ DPI}$ via `exportgraphics(..., 'Resolution', 300)`. Increase this value to `600` for print-ready journal submissions.

---

## 7. Troubleshooting & HPC Notes

* **`MATLAB executable 'matlab' not found`**:
  On Windows systems, MATLAB is frequently not added to the system `PATH` environment variable. Re-run `python setup.py` and enter the full path to `matlab.exe` (e.g., `C:\Program Files\MATLAB\R2024b\bin\matlab.exe`), or set `MATLAB_EXE` directly inside `config.ini`.
* **`Invalid file or directory '...-nodisplay'` on Windows**:
  Windows MATLAB does not accept the X11 `-nodisplay` flag. Ensure you are running the cross-platform `first.py`, which automatically omits `-nodisplay` when `os.name == 'nt'`.
* **`libstdc++.so.6: version 'GLIBCXX_3.4.xx' not found` (Linux HPC)**:
  MATLAB ships with an internal copy of `libstdc++.so.6` that may be older than your cluster's GCC compiler or Python virtual environment extensions. Load a modern GCC module (`module load gcc/12.3.0`), locate its `libstdc++.so.6`, and add the full path to `LD_PRELOAD` in `config.ini`.
* **`Unrecognized function or variable 'nfftmex' / 'nfsftmex'` (Linux HPC)**:
  Occurs during ODF/Pole Figure density estimation if MTEX's pre-compiled `.mexa64` binaries cannot locate `libfftw3.so` on your cluster node. Preload both libraries in `config.ini` (separated by a space or colon):
  ```ini
  LD_PRELOAD = /opt/ohpc/pub/compiler/gcc/12.3.0/lib64/libstdc++.so.6:/opt/ohpc/pub/libs/fftw3/lib/libfftw3.so
  ```

---

## 8. Citing FiRST

If you use **FiRST** in your research, please cite the software repository (see `CITATION.cff` for full metadata) and the accompanying manuscript:

* **Software:** Goswami, S., Mishra, S. K., and Karagadde, S. (2026). *FiRST: Five-fold Rotational Symmetry Detection Tool* (Version 1.0.0) [Computer software]. GitHub. https://github.com/goswamisourav7/FiRST
* **Manuscript:** Goswami, S., Mishra, S. K., and Karagadde, S. (2026). *Automated detection of five-fold rotational symmetry in polycrystalline materials*. Manuscript submitted for publication.



```bibtex
@software{goswami_2026_first,
  author  = {Goswami, Sourav and Mishra, Sushil Kumar and Karagadde, Shyamprasad},
  title   = {{FiRST: Five-fold Rotational Symmetry Detection Tool}},
  version = {1.0.0},
  year    = {2026},
  url     = {https://github.com/goswamisourav7/FiRST},
  doi     = {https://doi.org/10.5281/zenodo.24367801}
}
```

Please also cite the [MTEX Toolbox](https://mtex-toolbox.github.io/publications) when using the MATLAB pre-processing and plotting modules:
* Bachmann, F., Hielscher, R., & Schaeben, H. (2010). *Texture Analysis with MTEX – Free and Open Source Software Toolbox*. Solid State Phenomena, 160, 63–68.

---

## 9. License & Terms of Reuse

This project is distributed under the **GNU General Public License v3.0**. Refer to the license file for further details.

* **Bug Reports & Feature Requests**: Please open an issue on the GitHub Issues tracker with your `FiRST_<timestamp>.log` file attached.
* **Pull Requests**: Contributions extending FiRST to other twinning systems or direct `.h5oina` / `.oh5` readers are welcome.