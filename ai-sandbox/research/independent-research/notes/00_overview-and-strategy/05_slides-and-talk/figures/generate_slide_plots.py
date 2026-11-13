"""
Generate scholarly visual plots for presentation_slides.marp.md:
1. slide08_3ie_evidence_heatmap.png
2. slide10_feedback_convergence.png
3. slide11_covariate_shift.png
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set global aesthetic
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#64748b'
plt.rcParams['axes.linewidth'] = 1.0

output_dir = r"c:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\notes\00_overview-and-strategy\figures"
os.makedirs(output_dir, exist_ok=True)

# ==========================================
# 1. Slide 8: 3ie Evidence Coverage Heatmap
# ==========================================
fig, ax = plt.subplots(figsize=(9, 6.8), dpi=300)

interventions = [
    "Unconditional Cash",
    "Mobile Cash / Digital",
    "Food Vouchers",
    "Parametric Insurance",
    "Cash-for-Work"
]

outcomes = [
    "Food\nConsumption",
    "Child\nNutrition",
    "Asset\nPreservation",
    "Distress\nDisplacement",
    "Local Market\nPrices"
]

# Simulated matrix of study counts (reflecting literature density vs. deserts in Horn of Africa / FCAS)
data = np.array([
    [16, 9, 7, 2, 4],   # Cash
    [8,  4, 5, 1, 3],   # Mobile cash
    [11, 8, 3, 0, 5],   # Food vouchers
    [4,  1, 6, 0, 1],   # Parametric insurance
    [7,  3, 4, 1, 2]    # Public works
])

cmap = plt.cm.Blues
im = ax.imshow(data, cmap=cmap, vmin=0, vmax=18, aspect='auto')

# Labels
ax.set_xticks(np.arange(len(outcomes)))
ax.set_yticks(np.arange(len(interventions)))
ax.set_xticklabels(outcomes, fontsize=12, fontweight='bold', color='#0f172a')
ax.set_yticklabels(interventions, fontsize=12, fontweight='bold', color='#0f172a')

# Rotate x labels
plt.setp(ax.get_xticklabels(), rotation=0, ha="center")

# Annotate values inside cells
for i in range(len(interventions)):
    for j in range(len(outcomes)):
        val = data[i, j]
        color = "white" if val > 8 else "#0f172a"
        weight = "bold"
        text = str(val) if val > 0 else "0"
        ax.text(j, i, text, ha="center", va="center", color=color, fontsize=15, fontweight=weight)

# Highlight "Evidence Desert" cells with red dashed rectangles
desert_coords = [(2, 3), (3, 3)]  # Vouchers x Displacement, Insurance x Displacement
for i, j in desert_coords:
    rect = patches.Rectangle((j - 0.48, i - 0.48), 0.96, 0.96, linewidth=2.5, edgecolor='#e11d48',
                             facecolor='none', linestyle='--')
    ax.add_patch(rect)

# Annotation for Evidence Desert
ax.annotate('Evidence Desert:\nDisplacement unstudied\nin conflict insurance',
            xy=(3, 3), xytext=(2.0, 4.35),
            arrowprops=dict(facecolor='#e11d48', shrink=0.08, width=2, headwidth=7),
            fontsize=10.5, color='#be123c', fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.35", fc="#ffe4e6", ec="#f43f5e", lw=1.5))

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label('Identified Evaluations & Reports (Horn of Africa / FCAS)', fontsize=10.5, fontweight='bold', color='#334155')
cbar.ax.tick_params(labelsize=10)

ax.set_title("3ie Literature Taxonomy: Evidence Coverage & Gap Matrix", fontsize=14, fontweight='bold', color='#0f172a', pad=14)

# Disclaimer at bottom
plt.figtext(0.5, 0.015, "* Note: Illustrative synthetic evidence matrix for pipeline demonstration; not live field data.",
           ha="center", fontsize=9.5, fontstyle="italic", color="#64748b")

plt.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(os.path.join(output_dir, "slide08_3ie_evidence_heatmap.png"), dpi=300)
plt.close(fig)
print("Saved slide08_3ie_evidence_heatmap.png")


# ==========================================
# 2. Slide 10: Outlier Detection Forest Plot
# ==========================================
fig, ax = plt.subplots(figsize=(9, 6.8), dpi=300)

trials = [
    "Trial 01: Niger (World Bank 2023)",
    "Trial 02: Kenya (GiveDirectly 2020)",
    "Trial 03: Bangladesh (Hill et al. 2019)",
    "Trial 04: Yemen Cash vs Food (IFPRI 2020)",
    "Trial 05: Somalia IDP (Save the Children 2021)",
    "Trial 06: Mali Conflict Cash (Tranchant 2019)",
    "Trial 07: Ethiopia Post-War (AEARCTR 2025)",
    "Trial 08: DR Congo IDP Vouchers (IPA 2024)",
    "Trial 09: Nepal Flood FBF (World Bank 2024)",
    "Trial 10: Urban Siege Outlier (Distorted Market)"
]

# Effect sizes and 95% CIs (in SD units)
effects = np.array([0.32, 0.40, 0.28, 0.25, 0.35, 0.22, 0.30, 0.27, 0.38, -0.15])
ci_lower = effects - np.array([0.09, 0.08, 0.10, 0.12, 0.11, 0.13, 0.14, 0.12, 0.09, 0.12])
ci_upper = effects + np.array([0.09, 0.08, 0.10, 0.12, 0.11, 0.13, 0.14, 0.12, 0.09, 0.12])

y_pos = np.arange(len(trials))[::-1]

# Zero effect line
ax.axvline(0, color='#94a3b8', linestyle='--', linewidth=1.5, label="Null Effect")

# Pooled prior band (for the 9 consistent trials)
pooled_mean = np.mean(effects[:-1])
pooled_ci = 0.05
ax.axvspan(pooled_mean - pooled_ci, pooled_mean + pooled_ci, color='#e0e7ff', alpha=0.6,
          label="Context-Weighted Prior Band")

# Plot standard trials
for i in range(len(trials) - 1):
    y = y_pos[i]
    ax.errorbar(effects[i], y, xerr=[[effects[i] - ci_lower[i]], [ci_upper[i] - effects[i]]],
                fmt='o', color='#1e3a8a', ecolor='#2563eb', elinewidth=2.2, capsize=4, markersize=7)

# Plot outlier trial (Trial 10) in red
y_out = y_pos[-1]
ax.errorbar(effects[-1], y_out, xerr=[[effects[-1] - ci_lower[-1]], [ci_upper[-1] - effects[-1]]],
            fmt='s', color='#b91c1c', ecolor='#ef4444', elinewidth=2.8, capsize=5, markersize=8,
            label="Context-Controlled Outlier")

# Annotate outlier
ax.annotate('Outlier Detected:\nUnmeasured armed extortion\n& market supply collapse',
            xy=(effects[-1], y_out), xytext=(effects[-1] + 0.16, y_out + 0.65),
            arrowprops=dict(facecolor='#b91c1c', shrink=0.08, width=2, headwidth=7),
            fontsize=10.5, color='#991b1b', fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.35", fc="#fee2e2", ec="#f87171", lw=1.5))

ax.set_yticks(y_pos)
ax.set_yticklabels(trials, fontsize=11, fontweight='bold', color='#1e293b')
ax.set_xlabel("Standardized Treatment Effect Size (SD Units, 95% CI)", fontsize=11.5, fontweight='bold', color='#0f172a')
ax.set_title("Relative Trial Validity: Forest Plot & Outlier Detection", fontsize=14, fontweight='bold', color='#0f172a', pad=14)
ax.legend(loc='upper right', fontsize=10, framealpha=0.95)
ax.set_xlim(-0.4, 0.65)

# Disclaimer at bottom
plt.figtext(0.5, 0.015, "* Note: Illustrative synthetic trial data for outlier detection demonstration; not live field data.",
           ha="center", fontsize=9.5, fontstyle="italic", color="#64748b")

plt.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(os.path.join(output_dir, "slide10_feedback_convergence.png"), dpi=300)
plt.close(fig)
print("Saved slide10_feedback_convergence.png")


# ==========================================
# 3. Slide 11: Covariate Shift Density Plot
# ==========================================
fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)

x = np.linspace(-0.25, 0.85, 600)

# Source trial distribution (tight, high internal validity)
mu_source = 0.40
sigma_source = 0.075
pdf_source = (1 / (sigma_source * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu_source) / sigma_source)**2)

# Target predicted distribution under covariate shift (moderated effect, wider uncertainty)
mu_target = 0.20
sigma_target = 0.17
pdf_target = (1 / (sigma_target * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu_target) / sigma_target)**2)

# Plot curves
ax.plot(x, pdf_source, color='#1e3a8a', linewidth=2.8, label="Source Trial Effect (Internal Validity, Context A)")
ax.fill_between(x, pdf_source, color='#3b82f6', alpha=0.22)

ax.plot(x, pdf_target, color='#d97706', linewidth=2.8, linestyle='--', label="Predicted Target Effect (Satisficing, Crisis Context B)")
ax.fill_between(x, pdf_target, color='#f59e0b', alpha=0.22)

# Null effect reference line
ax.axvline(0, color='#64748b', linestyle=':', linewidth=1.5)
ax.text(-0.015, 5.2, "Null Effect", rotation=90, color='#475569', fontsize=10, fontweight='bold', ha='right')

# Context Shift Vector Arrow at clean height
arrow_y = 4.2
ax.annotate('', xy=(mu_target, arrow_y), xytext=(mu_source, arrow_y),
            arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", color='#0f172a', lw=2.5))
ax.text((mu_source + mu_target)/2, arrow_y + 0.35, r"Covariate Shift ($\Delta X$)", ha='center',
        fontsize=12, fontweight='bold', color='#0f172a')

# Explanatory text with clear background box so it never clashes with lines
ax.text((mu_source + mu_target)/2, arrow_y - 0.55, "Higher conflict friction, lower market access",
        ha='center', fontsize=9.5, fontweight='bold', color='#0f172a',
        bbox=dict(boxstyle="round,pad=0.3", fc="#ffffff", ec="#94a3b8", lw=1.2, alpha=0.95))

# Annotation for Source Curve (Known Trial)
ax.annotate('Known Trial Setting:\nTight bounds, high precision',
            xy=(mu_source, 5.1), xytext=(mu_source + 0.14, 5.4),
            arrowprops=dict(facecolor='#1e3a8a', shrink=0.08, width=1.8, headwidth=6),
            fontsize=10, color='#1e3a8a', fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.35", fc="#eff6ff", ec="#bfdbfe", lw=1.5))

# Annotation for Target Curve (Novel Crisis Context) - positioned cleanly at lower left
ax.annotate('Novel Crisis Context:\nSatisficing under data scarcity\n(Wider bounds = honest uncertainty)',
            xy=(mu_target, 1.8), xytext=(-0.16, 2.7),
            arrowprops=dict(facecolor='#d97706', shrink=0.08, width=1.8, headwidth=6),
            fontsize=10, color='#92400e', fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.35", fc="#fef3c7", ec="#fde68a", lw=1.5))

ax.set_title("Causal Transportability: Satisficing Under Covariate Shift", fontsize=14, fontweight='bold', color='#0f172a', pad=14)
ax.set_xlabel("Estimated Treatment Effect Size (SD Units)", fontsize=11.5, fontweight='bold', color='#0f172a')
ax.set_ylabel("Probability Density", fontsize=11.5, fontweight='bold', color='#0f172a')

# Legend placed in upper left, well clear of distributions
ax.legend(loc='upper left', fontsize=9.5, framealpha=0.95, edgecolor='#cbd5e1')
ax.set_xlim(-0.22, 0.8)
ax.set_ylim(0, 7.2)

# Disclaimer at bottom
plt.figtext(0.5, 0.015, "* Note: Illustrative synthetic distributions for causal transportability demonstration; not live field data.",
           ha="center", fontsize=9.5, fontstyle="italic", color="#64748b")

plt.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(os.path.join(output_dir, "slide11_covariate_shift.png"), dpi=300)
plt.close(fig)
print("Saved slide11_covariate_shift.png")
