# win-x64 version

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

# Force non-interactive headless backend before importing pyplot (prevents Windows GUI popups/Tk errors)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

# =====================================
# PARAMETERS
# =====================================
ANGLE_TOL_DEG = 5.0
ANGLE_TOL_RAD = np.deg2rad(ANGLE_TOL_DEG)
COS_TOL = np.cos(ANGLE_TOL_RAD)

SIGMA3_TOL_DEG = 8.66

# =====================================
# HELPER FUNCTIONS: QUATERNIONS
# =====================================
def get_cubic_symmetries():
    s = np.sqrt(2) / 2
    syms = [
        [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1],
        [s, s, 0, 0], [s, -s, 0, 0], [s, 0, s, 0], [s, 0, -s, 0], [s, 0, 0, s], [s, 0, 0, -s],
        [0, s, s, 0], [0, s, -s, 0], [0, s, 0, s], [0, s, 0, -s], [0, 0, s, s], [0, 0, s, -s],
    ]

    for x in [0.5, -0.5]:
        for y in [0.5, -0.5]:
            for z in [0.5, -0.5]:
                syms.append([0.5, x, y, z])
    return np.array(syms)

def quat_mult(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([
        w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2
    ])

def quat_inv(q):
    return np.array([q[0], -q[1], -q[2], -q[3]])

def check_sigma3(qA, qB, tol_deg=SIGMA3_TOL_DEG):
    syms = get_cubic_symmetries()
    q_ideal = np.array([np.sqrt(3)/2, 1/(2*np.sqrt(3)), 1/(2*np.sqrt(3)), 1/(2*np.sqrt(3))])
    q_mis = quat_mult(quat_inv(qA), qB)
    min_dev = np.inf
    
    for S1 in syms:
        for S2 in syms:
            q_eq = quat_mult(S1, quat_mult(q_mis, S2))
            dot = np.clip(np.abs(np.dot(q_eq, q_ideal)), -1.0, 1.0)
            dev_angle = 2 * np.arccos(dot)
            if dev_angle < min_dev: 
                min_dev = dev_angle
            
    min_dev_deg = np.rad2deg(min_dev)
    return min_dev_deg <= tol_deg, min_dev_deg

# =====================================
# LOAD DATA & CALCULATE BASE STATS
# =====================================
try:
    pairs = pd.read_csv("grain_pairs.csv")
    attrs = pd.read_csv("grain_attributes.csv")
    stats = pd.read_csv("dataset_stats.csv")
    total_grains_all = stats['TotalGrains'].iloc[0]
    total_boundary_len = stats['TotalBoundaryLength'].iloc[0]
    total_twin_len = stats['TotalTwinLength'].iloc[0]
    twin_len_df = pd.read_csv("twin_boundary_lengths.csv")
    twin_lengths = {frozenset([int(r['Grain1']), int(r['Grain2'])]): r['BoundaryLength'] for _, r in twin_len_df.iterrows()}
except FileNotFoundError as e:
    print(f"Error loading files: {e}")
    sys.exit(1)

total_fcc_grains = len(attrs)
total_twin_grains = int(attrs['hasSigma3'].sum())

if len(pairs) > 0:
    poles = pairs[["p1x", "p1y", "p1z"]].values
    grain1 = pairs["Grain1"].values
    grain2 = pairs["Grain2"].values
    poles = poles / np.linalg.norm(poles, axis=1)[:, None]
else:
    poles = np.empty((0, 3))
    grain1 = np.array([])
    grain2 = np.array([])

quaternions = {int(row['grainID']): np.array([row['q0'], row['q1'], row['q2'], row['q3']]) for _, row in attrs.iterrows()}

print(f"Total pairs analyzed: {len(poles)}")

# =====================================
# HIERARCHICAL CLUSTERING 
# =====================================
if len(poles) >= 2:
    dot_matrix = np.clip(np.abs(np.dot(poles, poles.T)), -1.0, 1.0)
    dist_matrix = 1.0 - dot_matrix
    np.fill_diagonal(dist_matrix, 0)
    condensed_dist = squareform(dist_matrix)

    Z = linkage(condensed_dist, method='complete')
    threshold_dist = 1.0 - COS_TOL 
    labels = fcluster(Z, threshold_dist, criterion='distance')
    unique_labels, counts = np.unique(labels, return_counts=True)
elif len(poles) == 1:
    labels = np.array([1])
    unique_labels, counts = np.array([1]), np.array([1])
else:
    labels = np.array([])
    unique_labels, counts = np.array([]), np.array([])

# ---------------------------------------------------------
# <110> Pole Frequency Histogram & CSV Export
# ---------------------------------------------------------
if len(counts) > 0:
    max_count = np.max(counts)
    bins = np.arange(1, max(7, max_count + 2)) 
    hist, bin_edges = np.histogram(counts, bins=bins)
    
    freq_df = pd.DataFrame({'Grains_Sharing_Pole': bin_edges[:-1], 'Frequency': hist})
    freq_df.to_csv("pole_frequencies.csv", index=False)
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(bin_edges[:-1], hist, color='#1f77b4', edgecolor='black', zorder=3)
    plt.yscale('log')
    plt.xlabel('Number of Twinned Grains Sharing a <110> Pole')
    plt.ylabel('Frequency (Log Scale)')
    plt.title('Distribution of <110> Pole Coincidence in Twinned Grains')
    plt.xticks(bin_edges[:-1])
    plt.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
    
    for bar in bars:
        yval = bar.get_height()
        if yval > 0:
            plt.text(bar.get_x() + bar.get_width()/2, yval, f'{int(yval)}', 
                     ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig("pole_frequency_histogram.png", dpi=300)
    plt.close()
else:
    print("\n[!] No twinned grain clusters found; skipping histogram generation.")

candidate_labels = unique_labels[counts >= 4]
clusters = [np.where(labels == lbl)[0].tolist() for lbl in candidate_labels]

# =====================================
# FFRS RECONSTRUCTION & DEDUPLICATION
# =====================================
ffrs_found = [] 
total_ffrs_count = 0
unique_ffrs_grains = set()
ffrs_twin_edges = set()
ordered_ffrs_chains = []

for k, cluster in enumerate(clusters):
    cluster_poles = poles[cluster]

    cov = np.zeros((3, 3))
    for p in cluster_poles:
        cov += np.outer(p, p)
    evals, evecs = np.linalg.eigh(cov)
    centroid = evecs[:, np.argmax(evals)] 

    dots = np.clip(np.abs(cluster_poles @ centroid), -1.0, 1.0)
    max_spread = np.rad2deg(np.max(np.arccos(dots)))

    twin_pairs = [(int(grain1[idx]), int(grain2[idx])) for idx in cluster]
    
    chain_G = nx.Graph()
    chain_G.add_edges_from(twin_pairs)

    for start_node in chain_G.nodes():
        stack = [[start_node]]
        
        while stack:
            path = stack.pop()
            
            if len(path) == 5:
                cluster_set = set(path)
                
                is_duplicate = False
                for found_set in ffrs_found:
                    if len(cluster_set.intersection(found_set)) >= 1:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    gA, gB = path[0], path[-1]
                    
                    if chain_G.has_edge(gA, gB):
                        print(f"\n[FFRS Detected in Cluster {k+1}]")
                        print(f"Pole centroid: {np.round(centroid, 6)}")
                        print(f"Max angular spread (deg): {round(max_spread, 4)}")
                        path.append(path[0])
                        ordered_ffrs_chains.append(path[:5] + ["Closed"])
                        print(f"FFRS Chain (Already Closed): {' - '.join(map(str, path))}")
                        
                        ffrs_found.append(cluster_set)
                        total_ffrs_count += 1
                        unique_ffrs_grains.update(cluster_set)
                        for i in range(5):
                            ffrs_twin_edges.add(frozenset([path[i], path[(i+1)%5]]))
                        
                    else:
                        is_twin, dev_angle = check_sigma3(quaternions[gA], quaternions[gB])
                        
                        if is_twin:
                            print(f"\n[FFRS Detected in Cluster {k+1}]")
                            print(f"Pole centroid: {np.round(centroid, 6)}")
                            print(f"Max angular spread (deg): {round(max_spread, 4)}")
                            print(f"FFRS Chain (Open): {' - '.join(map(str, path))}")
                            print(f"-> Verification SUCCESS: Grains {gA} and {gB} share a valid Sigma-3 twin misorientation (Deviation: {dev_angle:.2f} deg).")
                            path.append(path[0])
                            ordered_ffrs_chains.append(path[:5] + ["Open"])
                            print(f"-> Final Closed FFRS Chain: {' - '.join(map(str, path))}")
                            
                            ffrs_found.append(cluster_set)
                            total_ffrs_count += 1
                            unique_ffrs_grains.update(cluster_set)
                            for i in range(5):
                                ffrs_twin_edges.add(frozenset([path[i], path[(i+1)%5]]))
            else:
                last_node = path[-1]
                for neighbor in chain_G.neighbors(last_node):
                    if neighbor not in path: 
                        stack.append(path + [neighbor])

# =====================================
# FINAL STATISTICAL REPORT
# =====================================
ffrs_twin_len_sum = sum(twin_lengths.get(edge, 0.0) for edge in ffrs_twin_edges)
ffrs_len_pct = (ffrs_twin_len_sum / total_twin_len * 100) if total_twin_len > 0 else 0

print(f"\n=====================================")
print(f"DATASET STATISTICS:")
print(f"-------------------------------------")
print(f"Total Grains            :   {total_grains_all}")
print(f"Total Boundary Length:      {total_boundary_len:.2f}")
print(f"Total Twin Boundary Length: {total_twin_len:.2f}")
print(f"-------------------------------------")
print(f"Total FCC Grains:           {total_fcc_grains}")

twin_pct = (total_twin_grains / total_fcc_grains * 100) if total_fcc_grains > 0 else 0
print(f"Twin Grains:                {total_twin_grains} ({twin_pct:.2f}% of FCC grains)")

print(f"Candidate <110> Poles:      {len(clusters)}")
print(f"True FFRS Clusters Found:   {total_ffrs_count}")

ffrs_pct = (len(unique_ffrs_grains) / total_twin_grains * 100) if total_twin_grains > 0 else 0
print(f"FFRS-Mediated Grains:      {len(unique_ffrs_grains)} ({ffrs_pct:.2f}% of twin grains)")
print(f"FFRS Twin Length Fraction:  {ffrs_len_pct:.2f}% of total twin length")
print(f"=====================================")

if ordered_ffrs_chains:
    df_ffrs = pd.DataFrame(ordered_ffrs_chains, columns=["G1", "G2", "G3", "G4", "G5", "Type"])
    df_ffrs.to_csv("ffrs_clusters.csv", index_label="ClusterID")