"""
Generate 12 scholarly SVG diagrams for presentation_slides.marp.md:
Slide 01: Dilemma Split Graphic
Slide 02: Academic vs Planner Decision Contrast
Slide 03: 2x2 Positioning Matrix
Slide 04: reprokit Architecture
Slide 05: 2x2 System Architecture
Slide 06: Literature Ingest Pipeline
Slide 07: Multi-Modal Data Fusion Stack
Slide 09: Trial Extraction & Geolocation Gate
Slide 12: Causal DAG with Conflict Break
Slide 13: Methodological Toolkit
Slide 14: Simulation Response Dashboard Mockup
Slide 15: Research Roadmap & Milestone Flow
"""

import os

output_dir = r"c:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\notes\00_overview-and-strategy\figures"
os.makedirs(output_dir, exist_ok=True)

# Common SVG defs for arrows and drop shadows
COMMON_DEFS = """
  <defs>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.08" />
    </filter>
    <filter id="glow-red" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#ef4444" flood-opacity="0.3" />
    </filter>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#475569" />
    </marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#2563eb" />
    </marker>
    <marker id="arrow-red" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#dc2626" />
    </marker>
    <marker id="arrow-emerald" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#059669" />
    </marker>
  </defs>
"""

# ==============================================================================
# Slide 01: Dilemma Split Graphic
# ==============================================================================
svg_01 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  
  <!-- Header Banner -->
  <text x="400" y="42" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">The Operational Mismatch in Crisis Response</text>
  <text x="400" y="68" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Life-or-Death Emergency Decisions vs. High Evidence Search &amp; Consumption Costs</text>

  <!-- Left Column: Operational Urgency -->
  <g transform="translate(30, 95)" filter="url(#shadow)">
    <rect width="350" height="440" fill="#ffffff" stroke="#fca5a5" stroke-width="2" rx="10" />
    <rect width="350" height="48" fill="#fee2e2" rx="10" />
    <rect width="350" height="10" y="38" fill="#fee2e2" />
    <text x="25" y="30" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#991b1b">&#x23F1; Operational Reality (The Planner)</text>
    
    <!-- Badges -->
    <rect x="25" y="65" width="300" height="50" fill="#fff1f2" stroke="#fda4af" rx="6" />
    <text x="40" y="95" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#be123c">Response Window: 2 &ndash; 3 Weeks</text>
    
    <!-- Bullets -->
    <g transform="translate(25, 135)" font-family="Segoe UI, sans-serif" font-size="13" fill="#334155">
      <circle cx="8" cy="12" r="4" fill="#ef4444" />
      <text x="22" y="16" font-weight="bold" fill="#0f172a">Immediate Resource Allocation</text>
      <text x="22" y="34" font-size="11.5" fill="#64748b">Must deploy aid packages before famine peaks.</text>
      
      <circle cx="8" cy="62" r="4" fill="#ef4444" />
      <text x="22" y="66" font-weight="bold" fill="#0f172a">Hard Budget Constraints</text>
      <text x="22" y="84" font-size="11.5" fill="#64748b">Fixed funds; must pick optimal intervention mix.</text>
      
      <circle cx="8" cy="112" r="4" fill="#ef4444" />
      <text x="22" y="116" font-weight="bold" fill="#0f172a">Zero Fieldwork Feasibility</text>
      <text x="22" y="134" font-size="11.5" fill="#64748b">Cannot run 6-month survey or pilot RCT in war.</text>

      <circle cx="8" cy="162" r="4" fill="#ef4444" />
      <text x="22" y="166" font-weight="bold" fill="#0f172a">Current Fallback</text>
      <text x="22" y="184" font-size="11.5" fill="#b91c1c" font-weight="bold">Subjective heuristics &amp; qualitative tabletop guessing.</text>
    </g>
  </g>

  <!-- Right Column: Academic Evidence Reality -->
  <g transform="translate(420, 95)" filter="url(#shadow)">
    <rect width="350" height="440" fill="#ffffff" stroke="#93c5fd" stroke-width="2" rx="10" />
    <rect width="350" height="48" fill="#dbeafe" rx="10" />
    <rect width="350" height="10" y="38" fill="#dbeafe" />
    <text x="25" y="30" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#1e3a8a">&#x1F4DA; Evidence Reality (The Literature)</text>
    
    <!-- Badges -->
    <rect x="25" y="65" width="300" height="50" fill="#eff6ff" stroke="#bfdbfe" rx="6" />
    <text x="40" y="95" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#1d4ed8">10,000+ Available Evaluations</text>
    
    <!-- Bullets -->
    <g transform="translate(25, 135)" font-family="Segoe UI, sans-serif" font-size="13" fill="#334155">
      <circle cx="8" cy="12" r="4" fill="#3b82f6" />
      <text x="22" y="16" font-weight="bold" fill="#0f172a">Prohibitive Search Costs</text>
      <text x="22" y="34" font-size="11.5" fill="#64748b">Buried across 3ie, J-PAL, World Bank, and paywalls.</text>
      
      <circle cx="8" cy="62" r="4" fill="#3b82f6" />
      <text x="22" y="66" font-weight="bold" fill="#0f172a">Complex Econometric Jargon</text>
      <text x="22" y="84" font-size="11.5" fill="#64748b">Written for methodologists, not field directors.</text>
      
      <circle cx="8" cy="112" r="4" fill="#3b82f6" />
      <text x="22" y="116" font-weight="bold" fill="#0f172a">Single-Program Isolation</text>
      <text x="22" y="134" font-size="11.5" fill="#64748b">Isolates one program; ignores opportunity costs.</text>

      <circle cx="8" cy="162" r="4" fill="#3b82f6" />
      <text x="22" y="166" font-weight="bold" fill="#0f172a">Uncertain Local Relevance</text>
      <text x="22" y="184" font-size="11.5" fill="#475569">Does Kenya peacetime cash work in blockaded Somalia?</text>
    </g>
  </g>

  <!-- Center Tension Connector -->
  <g transform="translate(365, 300)">
    <circle cx="35" cy="0" r="28" fill="#0f172a" />
    <text x="35" y="7" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold" fill="#ffffff" text-anchor="middle">VS</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 02: Academic vs Planner Decision Contrast
# ==============================================================================
svg_02 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="42" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Divergence in Mandate: Researcher vs. Planner</text>
  <text x="400" y="68" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Internal Causal Identification vs. Real-World Portfolio Optimization</text>

  <!-- Left Card: Academic Researcher -->
  <g transform="translate(40, 95)" filter="url(#shadow)">
    <rect width="340" height="445" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <path d="M 0 10 Q 0 0 10 0 L 330 0 Q 340 0 340 10 L 340 45 L 0 45 Z" fill="#1e3a8a" />
    <text x="170" y="28" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">The Academic Mandate</text>
    
    <g transform="translate(20, 65)" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#334155">
      <text y="15" font-weight="bold" fill="#0f172a">Core Objective:</text>
      <text y="35" fill="#475569">Isolate single causal parameter (internal validity).</text>
      
      <text y="75" font-weight="bold" fill="#0f172a">Primary Question:</text>
      <rect y="88" width="300" height="42" fill="#eff6ff" stroke="#bfdbfe" rx="4" />
      <text x="10" y="114" font-style="italic" fill="#1e40af">"Does Intervention X cause Outcome Y?"</text>
      
      <text y="160" font-weight="bold" fill="#0f172a">Intervention Framing:</text>
      <text y="180" fill="#475569">Single intervention evaluated in isolation.</text>
      
      <text y="220" font-weight="bold" fill="#0f172a">Time Horizon:</text>
      <text y="240" fill="#475569">3 to 5 years (design, survey, peer review).</text>

      <text y="280" font-weight="bold" fill="#0f172a">Tolerance for Uncertainty:</text>
      <text y="300" fill="#475569">Low: Prefers no estimate over an unverified proxy.</text>
      
      <rect y="335" width="300" height="32" fill="#f1f5f9" rx="4" />
      <text x="150" y="356" font-weight="bold" fill="#475569" text-anchor="middle">&#x2713; Gold Standard: Clustered RCT</text>
    </g>
  </g>

  <!-- Right Card: Humanitarian Planner -->
  <g transform="translate(420, 95)" filter="url(#shadow)">
    <rect width="340" height="445" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <path d="M 0 10 Q 0 0 10 0 L 330 0 Q 340 0 340 10 L 340 45 L 0 45 Z" fill="#047857" />
    <text x="170" y="28" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">The Humanitarian Planner Mandate</text>
    
    <g transform="translate(20, 65)" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#334155">
      <text y="15" font-weight="bold" fill="#0f172a">Core Objective:</text>
      <text y="35" fill="#475569">Maximize lives saved under hard budget caps.</text>
      
      <text y="75" font-weight="bold" fill="#0f172a">Primary Question:</text>
      <rect y="88" width="300" height="52" fill="#ecfdf5" stroke="#a7f3d0" rx="4" />
      <text x="10" y="108" font-style="italic" fill="#065f46">"Given $5M and 3 weeks in District Z,</text>
      <text x="10" y="126" font-style="italic" fill="#065f46">what mix of A, B, or C minimizes loss?"</text>
      
      <text y="168" font-weight="bold" fill="#0f172a">Intervention Framing:</text>
      <text y="188" fill="#475569">Open portfolio choice &amp; program layering.</text>
      
      <text y="228" font-weight="bold" fill="#0f172a">Time Horizon:</text>
      <text y="248" fill="#475569">Days or weeks before emergency peak.</text>

      <text y="288" font-weight="bold" fill="#0f172a">Tolerance for Uncertainty:</text>
      <text y="308" fill="#047857" font-weight="bold">Satisficing: Needs honest probabilistic bounds.</text>
      
      <rect y="335" width="300" height="32" fill="#ecfdf5" rx="4" />
      <text x="150" y="356" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Goal: Simulation Response Exercise</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 03: 2x2 Positioning Matrix
# ==============================================================================
svg_03 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="40" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Crisis Evidence Landscape: 2x2 Positioning</text>
  <text x="400" y="64" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Situating Our Pipeline Against Existing Academic and Policy Frameworks</text>

  <!-- Axes -->
  <line x1="120" y1="300" x2="720" y2="300" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)" />
  <line x1="420" y1="500" x2="420" y2="100" stroke="#94a3b8" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Axis Labels -->
  <text x="730" y="305" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#334155">Causal &amp; Predictive &rarr;</text>
  <text x="110" y="305" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#64748b" text-anchor="end">&larr; Static &amp; Descriptive</text>
  
  <text x="420" y="88" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#334155" text-anchor="middle">&uarr; Rapid &amp; Operational</text>
  <text x="420" y="525" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#64748b" text-anchor="middle">&darr; Retrospective / Academic Only</text>

  <!-- Quadrant 1: 3ie Maps (Bottom Left) -->
  <g transform="translate(160, 340)" filter="url(#shadow)">
    <rect width="220" height="130" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="15" y="28" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a">3ie Evidence Maps</text>
    <text x="15" y="52" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Static manual curation</text>
    <text x="15" y="70" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Descriptive bibliography</text>
    <text x="15" y="88" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; No reusable estimators</text>
    <text x="15" y="106" font-family="Segoe UI, sans-serif" font-size="11" fill="#e11d48">No spatial context</text>
  </g>

  <!-- Quadrant 2: World Bank Portals (Top Left) -->
  <g transform="translate(160, 130)" filter="url(#shadow)">
    <rect width="220" height="130" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="15" y="28" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a">World Bank / HDX Portals</text>
    <text x="15" y="52" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Real-time situational feeds</text>
    <text x="15" y="70" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Rich GIS map dashboards</text>
    <text x="15" y="88" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Passive visualizers</text>
    <text x="15" y="106" font-family="Segoe UI, sans-serif" font-size="11" fill="#e11d48">No counterfactual engine</text>
  </g>

  <!-- Quadrant 3: Academic Hierarchical Models (Bottom Right) -->
  <g transform="translate(460, 340)" filter="url(#shadow)">
    <rect width="230" height="130" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="15" y="28" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a">Academic Meta-Analysis</text>
    <text x="15" y="46" font-family="Segoe UI, sans-serif" font-size="10.5" fill="#1e40af">Meager (2019), Vivalt (2020)</text>
    <text x="15" y="68" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Bayesian hierarchical pooling</text>
    <text x="15" y="86" font-family="Segoe UI, sans-serif" font-size="11" fill="#64748b">&bull; Rigorous causal variance</text>
    <text x="15" y="104" font-family="Segoe UI, sans-serif" font-size="11" fill="#e11d48">Requires survey microdata</text>
  </g>

  <!-- Quadrant 4: OUR PIPELINE (Top Right - Highlighted) -->
  <g transform="translate(460, 120)" filter="url(#shadow)">
    <rect width="240" height="150" fill="#eff6ff" stroke="#2563eb" stroke-width="2.5" rx="10" />
    <rect x="0" y="0" width="240" height="34" fill="#2563eb" rx="10" />
    <rect x="0" y="24" width="240" height="10" fill="#2563eb" />
    <text x="120" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x2605; Our Research Pipeline</text>
    
    <text x="15" y="55" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e3a8a">&bull; Automated OpenAlex Ingestion</text>
    <text x="15" y="73" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e3a8a">&bull; Subnational Spatial Panel Fusion</text>
    <text x="15" y="91" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e3a8a">&bull; Causal Transportability Engine</text>
    <text x="15" y="110" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#047857">&bull; Simulation Response Exercise</text>
    <rect x="15" y="120" width="210" height="20" fill="#dbeafe" rx="4" />
    <text x="120" y="134" font-family="Segoe UI, sans-serif" font-size="9.5" font-weight="bold" fill="#1e40af" text-anchor="middle">Operational Decision Support</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 04: reprokit Architecture
# ==============================================================================
svg_04 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="42" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">reprokit Architecture: Standardizing Open Science</text>
  <text x="400" y="68" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Reproducible by Anyone &bull; Legible to Humans &bull; Scalable by AI Agents</text>

  <!-- Block 1: Copier Template -->
  <g transform="translate(40, 110)" filter="url(#shadow)">
    <rect width="210" height="180" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="210" height="36" fill="#1e293b" rx="8" />
    <rect width="210" height="10" y="26" fill="#1e293b" />
    <text x="105" y="23" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">1. Project Templates</text>
    <g transform="translate(15, 52)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#334155">
      <text y="15" font-weight="bold" fill="#0f172a">&bull; study:</text>
      <text x="50" y="15" fill="#64748b">Empirical panels</text>
      <text y="40" font-weight="bold" fill="#0f172a">&bull; evidence:</text>
      <text x="65" y="40" fill="#64748b">Taxonomy maps</text>
      <text y="65" font-weight="bold" fill="#0f172a">&bull; library:</text>
      <text x="50" y="65" fill="#64748b">Analytics tools</text>
      <rect y="82" width="180" height="26" fill="#f1f5f9" rx="4" />
      <text x="90" y="99" font-family="monospace" font-size="10.5" fill="#047857" text-anchor="middle">copier copy template</text>
    </g>
  </g>

  <!-- Arrow 1 -> 2 -->
  <line x1="250" y1="200" x2="285" y2="200" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Block 2: Dual Interface -->
  <g transform="translate(295, 110)" filter="url(#shadow)">
    <rect width="210" height="180" fill="#ffffff" stroke="#3b82f6" stroke-width="2" rx="8" />
    <rect width="210" height="36" fill="#2563eb" rx="8" />
    <rect width="210" height="10" y="26" fill="#2563eb" />
    <text x="105" y="23" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Dual Interface</text>
    <g transform="translate(15, 52)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#334155">
      <text y="15" font-weight="bold" fill="#1e40af">&#x1F464; For Humans:</text>
      <text y="32" font-size="10.5" fill="#64748b">Clear README &amp; protocol.md</text>
      
      <text y="60" font-weight="bold" fill="#059669">&#x1F916; For AI Agents:</text>
      <text y="77" font-size="10.5" fill="#64748b">AGENTS.md + project.yaml</text>
      
      <rect y="92" width="180" height="24" fill="#eff6ff" rx="4" />
      <text x="90" y="108" font-size="10" font-weight="bold" fill="#2563eb" text-anchor="middle">Audit at machine scale</text>
    </g>
  </g>

  <!-- Arrow 2 -> 3 -->
  <line x1="505" y1="200" x2="540" y2="200" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Block 3: Verification Engine -->
  <g transform="translate(550, 110)" filter="url(#shadow)">
    <rect width="210" height="180" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="210" height="36" fill="#0f172a" rx="8" />
    <rect width="210" height="10" y="26" fill="#0f172a" />
    <text x="105" y="23" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">3. Verification Engine</text>
    <g transform="translate(15, 52)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#334155">
      <text y="15" font-weight="bold" fill="#0f172a">&bull; SHA-256 Hashes:</text>
      <text y="32" font-size="10" fill="#64748b">Pinned raw inputs &amp; outputs</text>
      <text y="55" font-weight="bold" fill="#0f172a">&bull; CI Test Harness:</text>
      <text y="72" font-size="10" fill="#64748b">Automated pytest suite</text>
      <rect y="86" width="180" height="26" fill="#ecfdf5" rx="4" />
      <text x="90" y="103" font-size="10.5" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Green on Linux &amp; Windows</text>
    </g>
  </g>

  <!-- Bottom Banner: Portability across crises -->
  <g transform="translate(40, 325)" filter="url(#shadow)">
    <rect width="720" height="215" fill="#ffffff" stroke="#e2e8f0" rx="8" />
    <text x="360" y="32" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#0f172a" text-anchor="middle">Why It Matters: Instant Portability Across Geographies</text>
    
    <g transform="translate(30, 60)" font-family="Segoe UI, sans-serif" font-size="12" fill="#334155">
      <rect width="200" height="120" fill="#f8fafc" stroke="#cbd5e1" rx="6" />
      <text x="100" y="25" font-weight="bold" fill="#1e3a8a" text-anchor="middle">Somalia Pilot</text>
      <text x="15" y="52" fill="#64748b">&bull; Drought + ACLED + WFP</text>
      <text x="15" y="74" fill="#64748b">&bull; 100% hash verified on CI</text>
      <text x="15" y="98" font-weight="bold" fill="#059669">&#x2713; Completed baseline</text>

      <rect x="230" y="0" width="200" height="120" fill="#f8fafc" stroke="#cbd5e1" rx="6" />
      <text x="330" y="25" font-weight="bold" fill="#1e3a8a" text-anchor="middle">Sudan Portability</text>
      <text x="245" y="52" fill="#64748b">&bull; Swapped boundary rasters</text>
      <text x="245" y="74" fill="#64748b">&bull; Same code runs cleanly</text>
      <text x="245" y="98" font-weight="bold" fill="#059669">&#x2713; Portability check passed</text>

      <rect x="460" y="0" width="200" height="120" fill="#eff6ff" stroke="#3b82f6" rx="6" />
      <text x="560" y="25" font-weight="bold" fill="#2563eb" text-anchor="middle">Next Crisis Setting</text>
      <text x="475" y="52" fill="#1e40af">&bull; Ukraine / Armenia / Sahel</text>
      <text x="475" y="74" fill="#1e40af">&bull; Zero pipeline re-engineering</text>
      <text x="475" y="98" font-weight="bold" fill="#2563eb">&rarr; Ready to ingest</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 05: 2x2 System Architecture
# ==============================================================================
svg_05 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="38" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">The 2x2 System Architecture</text>
  <text x="400" y="62" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Continuous Ingestion &bull; Quantitative Evidence &bull; Reusable Knowledge Corpus</text>

  <!-- 2x2 Box Layout -->
  <!-- Top Left: 1.1 Literature Discovery -->
  <g transform="translate(60, 90)" filter="url(#shadow)">
    <rect width="320" height="175" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="320" height="34" fill="#1e293b" rx="8" />
    <rect width="320" height="10" y="24" fill="#1e293b" />
    <text x="15" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">1.1 Literature Search &amp; Synthesis</text>
    <g transform="translate(15, 48)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Automated OpenAlex harvester</text>
      <text y="34">&bull; Snowball citation graph expansion</text>
      <text y="52">&bull; Grey literature: ALNAP, ReliefWeb, World Bank</text>
      <rect y="68" width="290" height="24" fill="#f1f5f9" rx="4" />
      <text x="145" y="84" font-weight="bold" fill="#0f172a" text-anchor="middle">Standalone Synthesis Review Output</text>
    </g>
  </g>

  <!-- Top Right: 2.1 3ie Taxonomy -->
  <g transform="translate(420, 90)" filter="url(#shadow)">
    <rect width="320" height="175" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="320" height="34" fill="#1e3a8a" rx="8" />
    <rect width="320" height="10" y="24" fill="#1e3a8a" />
    <text x="15" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">2.1 3ie Taxonomy &amp; Gap Analysis</text>
    <g transform="translate(15, 48)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Multi-dimensional matrix classification</text>
      <text y="34">&bull; Interventions &times; Outcomes &times; Countries</text>
      <text y="52">&bull; Pinpoints acute "evidence deserts" in conflict</text>
      <rect y="68" width="290" height="24" fill="#eff6ff" rx="4" />
      <text x="145" y="84" font-weight="bold" fill="#1e40af" text-anchor="middle">Quantified Evidence Coverage Heatmaps</text>
    </g>
  </g>

  <!-- Bottom Left: 1.2 Context Data Fusion -->
  <g transform="translate(60, 290)" filter="url(#shadow)">
    <rect width="320" height="175" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="320" height="34" fill="#0f766e" rx="8" />
    <rect width="320" height="10" y="24" fill="#0f766e" />
    <text x="15" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">1.2 Context Data Fusion Panel</text>
    <g transform="translate(15, 48)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Multi-modal spatial ingestion library</text>
      <text y="34">&bull; CHIRPS rain, ACLED points, WFP prices</text>
      <text y="52">&bull; Admin-2 district-month harmonization</text>
      <rect y="68" width="290" height="24" fill="#f0fdfa" rx="4" />
      <text x="145" y="84" font-weight="bold" fill="#0f766e" text-anchor="middle">Harmonized Subnational Panel Dataset</text>
    </g>
  </g>

  <!-- Bottom Right: 2.2 Reproducible Trials -->
  <g transform="translate(420, 290)" filter="url(#shadow)">
    <rect width="320" height="175" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="320" height="34" fill="#4338ca" rx="8" />
    <rect width="320" height="10" y="24" fill="#4338ca" />
    <text x="15" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">2.2 Reproducible Trials Repository</text>
    <g transform="translate(15, 48)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Curates open crisis RCT microdata</text>
      <text y="34">&bull; AEA, World Bank, Harvard/J-PAL Dataverse</text>
      <text y="52">&bull; Village GPS coordinate audit (the gate)</text>
      <rect y="68" width="290" height="24" fill="#eef2ff" rx="4" />
      <text x="145" y="84" font-weight="bold" fill="#4338ca" text-anchor="middle">Causally Valid Treatment Estimators</text>
    </g>
  </g>

  <!-- Connecting arrows for feedback loops -->
  <path d="M 380 170 L 420 170" stroke="#2563eb" stroke-width="2" marker-end="url(#arrow-blue)" />
  <path d="M 420 190 L 380 190" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />
  <path d="M 220 265 L 220 290" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />
  <path d="M 580 265 L 580 290" stroke="#4338ca" stroke-width="2" marker-end="url(#arrow)" />
  <path d="M 380 375 L 420 375" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />

  <!-- Bottom Convergence Box -->
  <g transform="translate(60, 485)" filter="url(#shadow)">
    <rect width="680" height="70" fill="#0f172a" rx="8" />
    <text x="340" y="28" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">&darr; CONVERGENCE: Causal Transportability &amp; Simulation Engine &darr;</text>
    <text x="340" y="48" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#94a3b8" text-anchor="middle">Anchoring Trial Estimators to Context Grids &bull; Predicting Impact in Novel Crises</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 06: Literature Ingest Pipeline
# ==============================================================================
svg_06 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 550" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="550" fill="#f8fafc" rx="12" />
  <text x="400" y="42" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Component 1.1: Automated Literature Discovery Pipeline</text>
  <text x="400" y="68" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Collapsing Literature Search Costs from Months to Minutes</text>

  <!-- Step 1: OpenAlex & Web Harvester -->
  <g transform="translate(40, 110)" filter="url(#shadow)">
    <rect width="150" height="260" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="150" height="34" fill="#1e293b" rx="8" />
    <rect width="150" height="10" y="24" fill="#1e293b" />
    <text x="75" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">1. API Harvester</text>
    <g transform="translate(12, 50)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; OpenAlex API</text>
      <text y="32">Academic corpus</text>
      <text y="58" font-weight="bold" fill="#0f172a">&bull; Grey Literature:</text>
      <text y="74">ALNAP reports</text>
      <text y="90">ReliefWeb</text>
      <text y="106">World Bank OKR</text>
      <rect y="125" width="126" height="50" fill="#f1f5f9" rx="4" />
      <text x="63" y="145" font-size="9.5" fill="#64748b" text-anchor="middle">Continuous automated</text>
      <text x="63" y="162" font-size="9.5" fill="#64748b" text-anchor="middle">keyword triggers</text>
    </g>
  </g>

  <line x1="190" y1="240" x2="225" y2="240" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Step 2: Semantic Filtering -->
  <g transform="translate(230, 110)" filter="url(#shadow)">
    <rect width="150" height="260" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="150" height="34" fill="#1e3a8a" rx="8" />
    <rect width="150" height="10" y="24" fill="#1e3a8a" />
    <text x="75" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Filter Engine</text>
    <g transform="translate(12, 50)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Geographic Tag</text>
      <text y="32">Somalia, Sudan...</text>
      <text y="58" font-weight="bold" fill="#0f172a">&bull; Hazard Vector</text>
      <text y="74">Drought, flood, war</text>
      <text y="100" font-weight="bold" fill="#0f172a">&bull; Program Type</text>
      <text y="116">Cash, food, insurance</text>
      <rect y="135" width="126" height="40" fill="#eff6ff" rx="4" />
      <text x="63" y="152" font-size="9.5" font-weight="bold" fill="#1e40af" text-anchor="middle">Embedding similarity</text>
      <text x="63" y="168" font-size="9.5" fill="#1e40af" text-anchor="middle">relevance score</text>
    </g>
  </g>

  <line x1="380" y1="240" x2="415" y2="240" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Step 3: Citation Snowball -->
  <g transform="translate(420, 110)" filter="url(#shadow)">
    <rect width="150" height="260" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="150" height="34" fill="#0f766e" rx="8" />
    <rect width="150" height="10" y="24" fill="#0f766e" />
    <text x="75" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">3. Snowball Graph</text>
    <g transform="translate(12, 50)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Backward Tracing</text>
      <text y="32">Ingests cited trials</text>
      <text y="58" font-weight="bold" fill="#0f172a">&bull; Forward Tracing</text>
      <text y="74">Captures replications</text>
      <text y="100" font-weight="bold" fill="#0f172a">&bull; Co-authorship</text>
      <text y="116">Follows research hubs</text>
      <rect y="135" width="126" height="40" fill="#f0fdfa" rx="4" />
      <text x="63" y="152" font-size="9.5" font-weight="bold" fill="#0f766e" text-anchor="middle">Discovers unindexed</text>
      <text x="63" y="168" font-size="9.5" fill="#0f766e" text-anchor="middle">evaluation reports</text>
    </g>
  </g>

  <line x1="570" y1="240" x2="605" y2="240" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />

  <!-- Step 4: Standalone Usable Outputs -->
  <g transform="translate(610, 110)" filter="url(#shadow)">
    <rect width="150" height="260" fill="#ecfdf5" stroke="#059669" stroke-width="2" rx="8" />
    <rect width="150" height="34" fill="#059669" rx="8" />
    <rect width="150" height="10" y="24" fill="#059669" />
    <text x="75" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">4. Usable Outputs</text>
    <g transform="translate(12, 50)" font-family="Segoe UI, sans-serif" font-size="11" fill="#065f46">
      <text y="16" font-weight="bold">&bull; Literature Review</text>
      <text y="32">Formatted Markdown</text>
      <text y="48">ready for publication</text>
      <text y="74" font-weight="bold">&bull; Search Manifest</text>
      <text y="90">Machine-readable</text>
      <text y="106">references.yaml</text>
      <rect y="125" width="126" height="50" fill="#ffffff" stroke="#a7f3d0" rx="4" />
      <text x="63" y="145" font-size="9.5" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Immediate utility</text>
      <text x="63" y="162" font-size="9.5" fill="#047857" text-anchor="middle">for practitioners</text>
    </g>
  </g>

  <!-- Bottom Card -->
  <g transform="translate(40, 395)" filter="url(#shadow)">
    <rect width="720" height="120" fill="#ffffff" stroke="#e2e8f0" rx="8" />
    <text x="360" y="28" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#0f172a" text-anchor="middle">Direct Value to Humanitarian Planning</text>
    <text x="360" y="52" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569" text-anchor="middle">Instead of spending 6 months in library searches, a response team generates a verified, structured literature digest in minutes,</text>
    <text x="360" y="72" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569" text-anchor="middle">instantly identifying what has been tried in similar contexts and what risks were reported.</text>
    <rect x="250" y="85" width="220" height="22" fill="#ecfdf5" rx="4" />
    <text x="360" y="100" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#047857" text-anchor="middle">Feeds directly into 3ie Taxonomy &amp; Gap Analysis</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 07: Multi-Modal Data Fusion Stack
# ==============================================================================
svg_07 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="40" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Component 1.2: Multi-Modal Context Data Fusion Stack</text>
  <text x="400" y="66" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Converting High-Dimensional Raster Geodata into Structured Subnational Context</text>

  <!-- 4 Stacked Layers -->
  <!-- Layer 1: Satellite Rasters -->
  <g transform="translate(80, 100)" filter="url(#shadow)">
    <polygon points="120,0 600,0 480,70 0,70" fill="#e0f2fe" stroke="#38bdf8" stroke-width="2" />
    <text x="300" y="42" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0369a1">Layer 1: Earth Observation Rasters (CHIRPS Rainfall, VIIRS Night Lights, NDVI)</text>
    <rect x="495" y="18" width="90" height="20" fill="#ffffff" rx="4" />
    <text x="540" y="32" font-family="monospace" font-size="10" fill="#0284c7" text-anchor="middle">GeoTIFF 5km</text>
  </g>

  <!-- Layer 2: Conflict Points -->
  <g transform="translate(80, 160)" filter="url(#shadow)">
    <polygon points="120,0 600,0 480,70 0,70" fill="#fee2e2" stroke="#f87171" stroke-width="2" />
    <text x="300" y="42" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#b91c1c">Layer 2: Conflict Point Processes (ACLED Battles, UCDP GED Fatalities)</text>
    <rect x="495" y="18" width="90" height="20" fill="#ffffff" rx="4" />
    <text x="540" y="32" font-family="monospace" font-size="10" fill="#dc2626" text-anchor="middle">Point GeoJSON</text>
  </g>

  <!-- Layer 3: Market Prices -->
  <g transform="translate(80, 220)" filter="url(#shadow)">
    <polygon points="120,0 600,0 480,70 0,70" fill="#fef3c7" stroke="#fbbf24" stroke-width="2" />
    <text x="300" y="42" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#b45309">Layer 3: Market Commodity Prices (WFP / FSNAU Maize, Sorghum, Wheat)</text>
    <rect x="495" y="18" width="90" height="20" fill="#ffffff" rx="4" />
    <text x="540" y="32" font-family="monospace" font-size="10" fill="#d97706" text-anchor="middle">Tabular CSV</text>
  </g>

  <!-- Layer 4: Human Mobility -->
  <g transform="translate(80, 280)" filter="url(#shadow)">
    <polygon points="120,0 600,0 480,70 0,70" fill="#ede9fe" stroke="#a78bfa" stroke-width="2" />
    <text x="300" y="42" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#6d28d9">Layer 4: Forced Displacement Vectors (UNHCR PRMN / IOM DTM Flows)</text>
    <rect x="495" y="18" width="90" height="20" fill="#ffffff" rx="4" />
    <text x="540" y="32" font-family="monospace" font-size="10" fill="#7c3aed" text-anchor="middle">Origin-Dest API</text>
  </g>

  <!-- Downward Arrow: Data Fusion Library -->
  <line x1="400" y1="365" x2="400" y2="405" stroke="#059669" stroke-width="3" marker-end="url(#arrow-emerald)" />
  <rect x="250" y="375" width="300" height="22" fill="#ecfdf5" stroke="#a7f3d0" rx="4" />
  <text x="400" y="390" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#047857" text-anchor="middle">Automated Open-Source Fusion Library (Standardized Spatial Joins)</text>

  <!-- Resulting Table Box -->
  <g transform="translate(80, 420)" filter="url(#shadow)">
    <rect width="640" height="135" fill="#ffffff" stroke="#047857" stroke-width="2" rx="8" />
    <rect width="640" height="30" fill="#047857" rx="8" />
    <rect width="640" height="10" y="20" fill="#047857" />
    <text x="320" y="20" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">Output: Harmonized Subnational Panel Table (District-Month / Admin-2)</text>
    
    <!-- Mini Table Layout -->
    <g transform="translate(20, 42)" font-family="monospace" font-size="11" fill="#334155">
      <rect width="600" height="22" fill="#f1f5f9" />
      <text x="10" y="15" font-weight="bold" fill="#0f172a">district_id</text>
      <text x="100" y="15" font-weight="bold" fill="#0f172a">month</text>
      <text x="170" y="15" font-weight="bold" fill="#0f172a">rain_zscore</text>
      <text x="270" y="15" font-weight="bold" fill="#0f172a">conflict_events</text>
      <text x="400" y="15" font-weight="bold" fill="#0f172a">sorghum_price</text>
      <text x="510" y="15" font-weight="bold" fill="#0f172a">idp_arrivals</text>
      
      <text x="10" y="36">SO-BAIDOA</text>
      <text x="100" y="36">2022-04</text>
      <text x="170" y="36" fill="#dc2626">-2.41 (Drought)</text>
      <text x="270" y="36" fill="#dc2626">14 battles</text>
      <text x="400" y="36">+45% YoY</text>
      <text x="510" y="36">3,420</text>
      
      <text x="10" y="54">SO-MOGAD</text>
      <text x="100" y="54">2022-04</text>
      <text x="170" y="54">-1.12</text>
      <text x="270" y="54">8 events</text>
      <text x="400" y="54">+22% YoY</text>
      <text x="510" y="54">11,200</text>
    </g>
    <text x="320" y="125" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#059669" text-anchor="middle">&#x2713; CI Hash-Verified for Somalia &amp; Sudan &bull; Reusable Data Asset</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 09: Trial Extraction & Geolocation Gate
# ==============================================================================
svg_09 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="40" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Component 2.2: Trial Extraction &amp; The Geolocation Gate</text>
  <text x="400" y="66" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Curating Whole Evaluation Databases &bull; Overcoming the GPS Privacy Hurdle</text>

  <!-- Step 1: Global Repositories -->
  <g transform="translate(50, 105)" filter="url(#shadow)">
    <rect width="180" height="240" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="180" height="34" fill="#1e293b" rx="8" />
    <rect width="180" height="10" y="24" fill="#1e293b" />
    <text x="90" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">1. Full Repositories</text>
    <g transform="translate(15, 50)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; AEA Data &amp; Code</text>
      <text y="32">4,000 village Niger trial</text>
      <text y="60" font-weight="bold" fill="#0f172a">&bull; World Bank DIME</text>
      <text y="76">Bangladesh flood cash</text>
      <text y="104" font-weight="bold" fill="#0f172a">&bull; Harvard Dataverse</text>
      <text y="120">&bull; J-PAL Dataverse</text>
      <rect y="138" width="150" height="32" fill="#eff6ff" rx="4" />
      <text x="75" y="158" font-size="10" font-weight="bold" fill="#1e40af" text-anchor="middle">Screen for crisis RCTs</text>
    </g>
  </g>

  <line x1="230" y1="225" x2="275" y2="225" stroke="#64748b" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Step 2: Estimator Verification -->
  <g transform="translate(285, 105)" filter="url(#shadow)">
    <rect width="190" height="240" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="190" height="34" fill="#1e3a8a" rx="8" />
    <rect width="190" height="10" y="24" fill="#1e3a8a" />
    <text x="95" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Estimator Audit</text>
    <g transform="translate(15, 50)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Open Microdata:</text>
      <text y="32">Confirm replication package</text>
      <text y="58" font-weight="bold" fill="#0f172a">&bull; Causal Identification:</text>
      <text y="74">Cluster RCT or clean quasi</text>
      <text y="100" font-weight="bold" fill="#0f172a">&bull; Treatment Estimator:</text>
      <text y="116">ITT / LATE on welfare</text>
      <rect y="138" width="160" height="32" fill="#f1f5f9" rx="4" />
      <text x="80" y="158" font-size="10" font-weight="bold" fill="#0f172a" text-anchor="middle">Standardized effect size</text>
    </g>
  </g>

  <line x1="475" y1="225" x2="520" y2="225" stroke="#b91c1c" stroke-width="2.5" marker-end="url(#arrow-red)" />

  <!-- Step 3: THE DECISIVE GEOLOCATION GATE -->
  <g transform="translate(530, 95)" filter="url(#shadow)">
    <rect width="220" height="260" fill="#fff1f2" stroke="#e11d48" stroke-width="2.5" rx="8" />
    <rect width="220" height="40" fill="#e11d48" rx="8" />
    <rect width="220" height="10" y="30" fill="#e11d48" />
    <text x="110" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x1F6A8; THE GEOLOCATION GATE</text>
    <g transform="translate(15, 56)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#334155">
      <text y="16" font-weight="bold" fill="#9f1239">&bull; The Bottleneck:</text>
      <text y="34" font-size="10.5" fill="#64748b">GPS coordinates masked</text>
      <text y="50" font-size="10.5" fill="#64748b">for participant safety.</text>
      <text y="74" font-weight="bold" fill="#9f1239">&bull; Masked Coordinates:</text>
      <text y="92" font-size="10.5" fill="#b91c1c">&#x2717; Cannot link to satellite!</text>
      <text y="116" font-weight="bold" fill="#9f1239">&bull; The Solution Paths:</text>
      <text y="134" font-size="10.5" fill="#059669">1. Public spatial packages</text>
      <text y="150" font-size="10.5" fill="#059669">2. Formal author linkages</text>
      <rect y="165" width="190" height="26" fill="#ffffff" stroke="#f43f5e" rx="4" />
      <text x="95" y="182" font-size="10" font-weight="bold" fill="#e11d48" text-anchor="middle">Current Decisive Hurdle</text>
    </g>
  </g>

  <!-- Downward Join to Context Grid -->
  <g transform="translate(150, 390)" filter="url(#shadow)">
    <rect width="500" height="145" fill="#ffffff" stroke="#059669" stroke-width="2" rx="8" />
    <text x="250" y="30" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#065f46" text-anchor="middle">&darr; Spatial Join: Anchoring Treatment into Context Grids &darr;</text>
    
    <g transform="translate(30, 52)" font-family="Segoe UI, sans-serif" font-size="12" fill="#334155">
      <text y="15">&bull; With unmasked coordinates, each trial site joins with local <tspan font-weight="bold" fill="#0f172a">CHIRPS rainfall, ACLED conflict, and WFP prices</tspan>.</text>
      <text y="40">&bull; Evaluates how local context modifies experimental impact across multiple trials.</text>
      <rect y="55" width="440" height="26" fill="#ecfdf5" rx="4" />
      <text x="220" y="72" font-weight="bold" fill="#047857" text-anchor="middle">Pre-requisite for Causal Transportability Modeling</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 12: Causal DAG with Conflict Break
# ==============================================================================
svg_12 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="38" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Structural Breaks: Causal Transmission in Peace vs. War</text>
  <text x="400" y="64" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Why Standard Covariate Reweighting Fails When Conflict Collapses Transmission Mechanisms</text>

  <!-- TOP PANEL: Peaceful Setting (Mechanism Holds) -->
  <g transform="translate(50, 95)" filter="url(#shadow)">
    <rect width="700" height="195" fill="#ffffff" stroke="#86efac" stroke-width="2" rx="8" />
    <rect width="700" height="32" fill="#ecfdf5" rx="8" />
    <rect width="700" height="10" y="22" fill="#ecfdf5" />
    <text x="20" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46">&#x2713; Peaceful Disaster Setting (Unstated Security Assumptions Hold)</text>
    
    <!-- DAG Nodes -->
    <g transform="translate(30, 65)">
      <!-- Node 1 -->
      <rect width="110" height="60" fill="#f8fafc" stroke="#64748b" rx="6" />
      <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">Drought</text>
      <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">Shock</text>
      
      <line x1="110" y1="30" x2="145" y2="30" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 2 -->
      <g transform="translate(150, 0)">
        <rect width="110" height="60" fill="#ecfdf5" stroke="#059669" stroke-width="2" rx="6" />
        <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#065f46" text-anchor="middle">Emergency</text>
        <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#065f46" text-anchor="middle">Cash Transfer</text>
      </g>
      
      <line x1="260" y1="30" x2="295" y2="30" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 3 -->
      <g transform="translate(300, 0)">
        <rect width="110" height="60" fill="#ecfdf5" stroke="#059669" rx="6" />
        <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#065f46" text-anchor="middle">Household</text>
        <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#065f46" text-anchor="middle">Liquidity</text>
      </g>
      
      <line x1="410" y1="30" x2="445" y2="30" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 4 -->
      <g transform="translate(450, 0)">
        <rect width="110" height="60" fill="#ecfdf5" stroke="#059669" rx="6" />
        <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#065f46" text-anchor="middle">Market Food</text>
        <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#065f46" text-anchor="middle">Purchase</text>
      </g>
      
      <line x1="560" y1="30" x2="595" y2="30" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 5 -->
      <g transform="translate(600, 0)">
        <rect width="60" height="60" fill="#ecfdf5" stroke="#059669" stroke-width="2" rx="6" />
        <text x="30" y="26" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#065f46" text-anchor="middle">Welfare</text>
        <text x="30" y="42" font-family="Segoe UI, sans-serif" font-size="10" fill="#047857" text-anchor="middle">&#x2713; Survives</text>
      </g>
    </g>
    <text x="350" y="165" font-family="Segoe UI, sans-serif" font-size="11" fill="#047857" text-anchor="middle">Assumption holds: Open trade routes, competitive merchants &rarr; Elastic food supply smoothly absorbs cash.</text>
  </g>

  <!-- BOTTOM PANEL: Conflict Setting (Structural Break) -->
  <g transform="translate(50, 315)" filter="url(#shadow)">
    <rect width="700" height="230" fill="#ffffff" stroke="#fca5a5" stroke-width="2" rx="8" />
    <rect width="700" height="32" fill="#fee2e2" rx="8" />
    <rect width="700" height="10" y="22" fill="#fee2e2" />
    <text x="20" y="22" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#991b1b">&#x26A0; Armed Conflict Setting: The Structural Mechanism Break</text>
    
    <!-- DAG Nodes with Break -->
    <g transform="translate(30, 65)">
      <!-- Node 1 -->
      <rect width="110" height="60" fill="#f8fafc" stroke="#64748b" rx="6" />
      <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">Drought +</text>
      <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">Insurgency</text>
      
      <line x1="110" y1="30" x2="145" y2="30" stroke="#b91c1c" stroke-width="2" marker-end="url(#arrow-red)" />
      
      <!-- Node 2 -->
      <g transform="translate(150, 0)">
        <rect width="110" height="60" fill="#eff6ff" stroke="#3b82f6" rx="6" />
        <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e40af" text-anchor="middle">Emergency</text>
        <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e40af" text-anchor="middle">Cash Transfer</text>
      </g>
      
      <line x1="260" y1="30" x2="295" y2="30" stroke="#b91c1c" stroke-width="2" marker-end="url(#arrow-red)" />
      
      <!-- Node 3 -->
      <g transform="translate(300, 0)">
        <rect width="110" height="60" fill="#eff6ff" stroke="#3b82f6" rx="6" />
        <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e40af" text-anchor="middle">Household</text>
        <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#1e40af" text-anchor="middle">Liquidity</text>
      </g>
      
      <!-- THE RED BREAK ICON -->
      <g transform="translate(420, 10)">
        <circle cx="15" cy="20" r="18" fill="#ef4444" />
        <text x="15" y="27" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x2717;</text>
      </g>
      
      <!-- Adversarial Obstacle Above Break -->
      <g transform="translate(340, -42)" filter="url(#glow-red)">
        <rect width="180" height="36" fill="#fee2e2" stroke="#ef4444" stroke-width="1.5" rx="4" />
        <text x="90" y="22" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#b91c1c" text-anchor="middle">&#x26D4; Checkpoint Blockade / Extortion</text>
      </g>
      <line x1="430" y1="-5" x2="435" y2="10" stroke="#dc2626" stroke-width="2" stroke-dasharray="3,3" />

      <!-- Slashed Arrow -->
      <line x1="410" y1="30" x2="465" y2="30" stroke="#ef4444" stroke-width="2.5" stroke-dasharray="4,4" />
      
      <!-- Severed Node 4 -->
      <g transform="translate(470, 0)">
        <rect width="110" height="60" fill="#f8fafc" stroke="#cbd5e1" stroke-dasharray="4,4" rx="6" />
        <text x="55" y="26" font-family="Segoe UI, sans-serif" font-size="11" fill="#94a3b8" text-anchor="middle">Market Food</text>
        <text x="55" y="42" font-family="Segoe UI, sans-serif" font-size="11" fill="#94a3b8" text-anchor="middle">Purchase</text>
      </g>
      
      <!-- Failure Outflow -->
      <path d="M 355 60 Q 355 90 420 90 L 590 90" stroke="#dc2626" stroke-width="2" marker-end="url(#arrow-red)" />
      
      <!-- Bad Outcome Node -->
      <g transform="translate(595, 65)">
        <rect width="70" height="50" fill="#fee2e2" stroke="#ef4444" stroke-width="2" rx="6" />
        <text x="35" y="22" font-family="Segoe UI, sans-serif" font-size="9.5" font-weight="bold" fill="#b91c1c" text-anchor="middle">Hyper-Local</text>
        <text x="35" y="38" font-family="Segoe UI, sans-serif" font-size="9.5" font-weight="bold" fill="#b91c1c" text-anchor="middle">Price Spike</text>
      </g>
    </g>
    
    <text x="350" y="195" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#b91c1c" text-anchor="middle">The Operational Takeaway: When the DAG signals market inelasticity, cash transfers fail.</text>
    <text x="350" y="213" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569" text-anchor="middle">The planner must route around the break by delivering physical food or opening supply corridors first.</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 13: Methodological Toolkit
# ==============================================================================
svg_13 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#f8fafc" rx="12" />
  <text x="400" y="40" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">The Methodological Toolkit: Estimating Impact in Novel Sites</text>
  <text x="400" y="66" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">A Modular Set of Complementary Econometric &amp; Machine Learning Engines</text>

  <!-- 3 Engine Columns -->
  <!-- Engine 1: Bayesian Hierarchical -->
  <g transform="translate(40, 100)" filter="url(#shadow)">
    <rect width="220" height="250" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="220" height="34" fill="#1e3a8a" rx="8" />
    <rect width="220" height="10" y="24" fill="#1e3a8a" />
    <text x="110" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">1. Bayesian Hierarchical</text>
    
    <g transform="translate(15, 52)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Prior Construction:</text>
      <text y="32" font-size="10.5">Empirical treatment effects</text>
      <text y="48" font-size="10.5">from historical trials (Meager '19)</text>
      
      <text y="78" font-weight="bold" fill="#0f172a">&bull; Context Updating:</text>
      <text y="94" font-size="10.5">Shifts prior distribution via</text>
      <text y="110" font-size="10.5">observed target features (&Delta;X)</text>
      
      <rect y="132" width="190" height="48" fill="#eff6ff" rx="4" />
      <text x="95" y="152" font-size="9.5" font-weight="bold" fill="#1e40af" text-anchor="middle">Full Posterior Distribution</text>
      <text x="95" y="168" font-size="9" fill="#1e40af" text-anchor="middle">Generates intuitive credible bands</text>
    </g>
  </g>

  <!-- Engine 2: Synthetic Controls -->
  <g transform="translate(290, 100)" filter="url(#shadow)">
    <rect width="220" height="250" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="220" height="34" fill="#065f46" rx="8" />
    <rect width="220" height="10" y="24" fill="#065f46" />
    <text x="110" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Synthetic Donor Pools</text>
    
    <g transform="translate(15, 52)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Multi-Trial Weighting:</text>
      <text y="32" font-size="10.5">Treats related trials as</text>
      <text y="48" font-size="10.5">synthetic donor pool</text>
      
      <text y="78" font-weight="bold" fill="#0f172a">&bull; Similarity Distance:</text>
      <text y="94" font-size="10.5">Weights assigned by spatial</text>
      <text y="110" font-size="10.5">&amp; institutional proximity</text>
      
      <rect y="132" width="190" height="48" fill="#ecfdf5" rx="4" />
      <text x="95" y="152" font-size="9.5" font-weight="bold" fill="#047857" text-anchor="middle">Synthetic Counterfactual</text>
      <text x="95" y="168" font-size="9" fill="#047857" text-anchor="middle">Constructs target comparison site</text>
    </g>
  </g>

  <!-- Engine 3: Causal Neural Networks -->
  <g transform="translate(540, 100)" filter="url(#shadow)">
    <rect width="220" height="250" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="220" height="34" fill="#4338ca" rx="8" />
    <rect width="220" height="10" y="24" fill="#4338ca" />
    <text x="110" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">3. Causal Neural Nets</text>
    
    <g transform="translate(15, 52)" font-family="Segoe UI, sans-serif" font-size="11" fill="#475569">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; Neural DAG Models:</text>
      <text y="32" font-size="10.5">Learns representations under</text>
      <text y="48" font-size="10.5">graph structural constraints</text>
      
      <text y="78" font-weight="bold" fill="#0f172a">&bull; High-Dimensional Rasters:</text>
      <text y="94" font-size="10.5">Ingests non-linear satellite</text>
      <text y="110" font-size="10.5">&amp; conflict interactions (DML)</text>
      
      <rect y="132" width="190" height="48" fill="#eef2ff" rx="4" />
      <text x="95" y="152" font-size="9.5" font-weight="bold" fill="#4338ca" text-anchor="middle">Non-Linear Representation</text>
      <text x="95" y="168" font-size="9" fill="#4338ca" text-anchor="middle">Resolves multi-modal complexity</text>
    </g>
  </g>

  <!-- Convergence Arrows -->
  <line x1="150" y1="355" x2="300" y2="400" stroke="#1e3a8a" stroke-width="2" marker-end="url(#arrow-blue)" />
  <line x1="400" y1="355" x2="400" y2="395" stroke="#059669" stroke-width="2" marker-end="url(#arrow-emerald)" />
  <line x1="650" y1="355" x2="500" y2="400" stroke="#4338ca" stroke-width="2" marker-end="url(#arrow)" />

  <!-- Bottom Result Box -->
  <g transform="translate(40, 410)" filter="url(#shadow)">
    <rect width="720" height="135" fill="#0f172a" rx="8" />
    <text x="360" y="32" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x2699; Unified Deliverable: Probabilistic Impact Profiles</text>
    <g transform="translate(30, 52)" font-family="Segoe UI, sans-serif" font-size="12" fill="#94a3b8">
      <text y="15">&bull; Rather than forcing a single brittle estimator, the toolkit outputs an <tspan fill="#ffffff" font-weight="bold">empirical distribution of predicted impact</tspan>.</text>
      <text y="38">&bull; Gives the emergency planner realistic median estimates accompanied by honest credible bounds.</text>
      <rect y="52" width="660" height="24" fill="#1e293b" rx="4" />
      <text x="330" y="68" font-weight="bold" fill="#38bdf8" text-anchor="middle">Empowering the Simulation Response Exercise with Real Uncertainty Quantification</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 14: Simulation Response Dashboard Mockup
# ==============================================================================
svg_14 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="580" fill="#0f172a" rx="12" />
  
  <!-- Dashboard Top Bar -->
  <rect x="0" y="0" width="800" height="48" fill="#1e293b" rx="12" />
  <rect x="0" y="38" width="800" height="10" fill="#1e293b" />
  <text x="25" y="30" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#38bdf8">&#x1F6E1; Crisis Response Simulator &bull; Decision Support Tool</text>
  <rect x="620" y="12" width="150" height="24" fill="#059669" rx="12" />
  <text x="695" y="28" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x25CF; LIVE CONTEXT FEED</text>

  <!-- Left Column: Context & District Selector -->
  <g transform="translate(25, 65)">
    <rect width="230" height="485" fill="#1e293b" rx="8" />
    <text x="20" y="30" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">1. Target Location</text>
    
    <rect x="20" y="45" width="190" height="32" fill="#0f172a" stroke="#334155" rx="4" />
    <text x="32" y="66" font-family="Segoe UI, sans-serif" font-size="12" fill="#38bdf8">&#x1F4CD; Somalia &ndash; Baidoa</text>
    
    <text x="20" y="105" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#94a3b8">Active Shocks (Fused):</text>
    <g transform="translate(20, 120)" font-family="Segoe UI, sans-serif" font-size="11" fill="#cbd5e1">
      <rect width="190" height="24" fill="#450a0a" rx="4" />
      <text x="10" y="16" fill="#fca5a5">&#x26A0; Rainfall: -2.4&sigma; (Extreme Drought)</text>
      
      <rect y="32" width="190" height="24" fill="#450a0a" rx="4" />
      <text x="10" y="48" fill="#fca5a5">&#x26A0; Conflict: High (Al-Shabaab Siege)</text>
      
      <rect y="64" width="190" height="24" fill="#78350f" rx="4" />
      <text x="10" y="80" fill="#fde68a">&#x26A0; Market: Grain Price +45% YoY</text>
    </g>

    <line x1="20" y1="235" x2="210" y2="235" stroke="#334155" />
    
    <text x="20" y="260" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff">Budget Constraint:</text>
    <rect x="20" y="275" width="190" height="34" fill="#0f172a" rx="4" />
    <text x="30" y="297" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#34d399">$5,000,000 USD</text>
    
    <text x="20" y="335" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff">Time to Peak Famine:</text>
    <rect x="20" y="348" width="190" height="30" fill="#0f172a" rx="4" />
    <text x="30" y="368" font-family="Segoe UI, sans-serif" font-size="12" fill="#fbbf24">&#x23F3; 18 Days</text>
    
    <rect x="20" y="420" width="190" height="42" fill="#2563eb" rx="6" />
    <text x="115" y="446" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">RUN SIMULATION &rarr;</text>
  </g>

  <!-- Center Column: Simulation Comparison -->
  <g transform="translate(275, 65)">
    <rect width="495" height="485" fill="#1e293b" rx="8" />
    <text x="25" y="30" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#ffffff">2. Simulated Intervention Options (Predicted Impact &amp; Variance)</text>
    
    <!-- Option A: Pure Cash -->
    <g transform="translate(25, 50)">
      <rect width="445" height="95" fill="#0f172a" stroke="#334155" rx="6" />
      <text x="15" y="24" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">Option A: Unconditional Mobile Cash ($5M)</text>
      <text x="15" y="44" font-family="Segoe UI, sans-serif" font-size="11" fill="#94a3b8">Predicted Welfare Gain: <tspan fill="#34d399" font-weight="bold">+0.18 SD</tspan> &bull; Cost per beneficiary: $45</text>
      <!-- Simulated Density Curve Line -->
      <path d="M 15 80 Q 80 50 140 80" stroke="#f59e0b" stroke-width="2" fill="none" />
      <text x="15" y="65" font-family="Segoe UI, sans-serif" font-size="9" fill="#f59e0b">Wide variance: high risk of market inflation under siege</text>
      <rect x="340" y="15" width="90" height="26" fill="#7f1d1d" rx="4" />
      <text x="385" y="32" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#fca5a5" text-anchor="middle">HIGH RISK</text>
    </g>

    <!-- Option B: In-Kind Food Aid -->
    <g transform="translate(25, 155)">
      <rect width="445" height="95" fill="#0f172a" stroke="#334155" rx="6" />
      <text x="15" y="24" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">Option B: Physical In-Kind Food Convoys ($5M)</text>
      <text x="15" y="44" font-family="Segoe UI, sans-serif" font-size="11" fill="#94a3b8">Predicted Welfare Gain: <tspan fill="#34d399" font-weight="bold">+0.26 SD</tspan> &bull; Cost per beneficiary: $78</text>
      <!-- Tight curve -->
      <path d="M 15 80 Q 50 55 90 80" stroke="#38bdf8" stroke-width="2" fill="none" />
      <text x="15" y="65" font-family="Segoe UI, sans-serif" font-size="9" fill="#38bdf8">Immune to local inflation, but high logistics friction &amp; convoy risk</text>
      <rect x="340" y="15" width="90" height="26" fill="#14532d" rx="4" />
      <text x="385" y="32" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#86efac" text-anchor="middle">STABLE</text>
    </g>

    <!-- Option C: Layered Portfolio (Recommended) -->
    <g transform="translate(25, 260)">
      <rect width="445" height="110" fill="#064e3b" stroke="#059669" stroke-width="2" rx="6" />
      <text x="15" y="24" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">&#x2605; Option C: Layered Mix (60% Food Aid + 40% Targeted Cash)</text>
      <text x="15" y="44" font-family="Segoe UI, sans-serif" font-size="11" fill="#a7f3d0">Predicted Welfare Gain: <tspan fill="#34d399" font-weight="bold">+0.38 SD [95% CI: 0.28, 0.46]</tspan></text>
      <text x="15" y="64" font-family="Segoe UI, sans-serif" font-size="10.5" fill="#d1fae5">&bull; Food convoys stabilize grain supply &rarr; allows cash to smooth consumption.</text>
      <text x="15" y="82" font-family="Segoe UI, sans-serif" font-size="10.5" fill="#d1fae5">&bull; Minimizes mortality while preserving market trader incentives.</text>
      <rect x="325" y="15" width="105" height="26" fill="#059669" rx="4" />
      <text x="377" y="32" font-family="Segoe UI, sans-serif" font-size="10" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x2713; RECOMMENDED</text>
    </g>

    <!-- Real World Badge: Armenia Foundation Engagement -->
    <g transform="translate(25, 385)">
      <rect width="445" height="80" fill="#0f172a" stroke="#2563eb" rx="6" />
      <text x="15" y="24" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#60a5fa">&#x1F91D; Active Real-World Application: Armenia Foundation Pilot</text>
      <text x="15" y="44" font-family="Segoe UI, sans-serif" font-size="10.5" fill="#cbd5e1">Currently collaborating with a philanthropic foundation in Armenia to apply</text>
      <text x="15" y="60" font-family="Segoe UI, sans-serif" font-size="10.5" fill="#cbd5e1">this structured literature and evidence-mapping engine for local crisis response.</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 15: Research Roadmap & Milestone Flow
# ==============================================================================
svg_15 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 550" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="800" height="550" fill="#f8fafc" rx="12" />
  <text x="400" y="42" font-family="Segoe UI, sans-serif" font-size="20" font-weight="bold" fill="#0f172a" text-anchor="middle">Research Frontiers &amp; Year 1 Milestone Roadmap</text>
  <text x="400" y="68" font-family="Segoe UI, sans-serif" font-size="13" fill="#64748b" text-anchor="middle">Advancing from Technical Proof-of-Concept to Working Paper &amp; Seminar Presentation</text>

  <!-- Horizontal Timeline Bar -->
  <line x1="80" y1="160" x2="720" y2="160" stroke="#cbd5e1" stroke-width="4" />
  
  <!-- Milestone 1: Nov 2026 (Now) -->
  <g transform="translate(100, 120)">
    <circle cx="20" cy="40" r="16" fill="#2563eb" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="45" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">1</text>
    <text x="20" y="10" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#2563eb" text-anchor="middle">Nov 2026 (Current)</text>
    
    <rect x="-40" y="75" width="120" height="110" fill="#ffffff" stroke="#93c5fd" rx="6" filter="url(#shadow)" />
    <text x="20" y="95" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#1e3a8a" text-anchor="middle">Foundations</text>
    <text x="-30" y="115" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; CI hash builds pass</text>
    <text x="-30" y="132" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; reprokit v0.4.0 live</text>
    <text x="-30" y="150" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; SusDev Brownbag</text>
    <text x="-30" y="168" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Geolocation audit</text>
  </g>

  <!-- Milestone 2: Dec 2026 -->
  <g transform="translate(280, 120)">
    <circle cx="20" cy="40" r="16" fill="#0f766e" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="45" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">2</text>
    <text x="20" y="10" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#0f766e" text-anchor="middle">Dec 2026</text>
    
    <rect x="-40" y="75" width="120" height="110" fill="#ffffff" stroke="#99f6e4" rx="6" filter="url(#shadow)" />
    <text x="20" y="95" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#0f766e" text-anchor="middle">Evidence Scaling</text>
    <text x="-30" y="115" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Armenia pilot review</text>
    <text x="-30" y="132" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; 3ie taxonomy scale</text>
    <text x="-30" y="150" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; OpenAlex API sweep</text>
    <text x="-30" y="168" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Author data outreach</text>
  </g>

  <!-- Milestone 3: Jan-Feb 2027 -->
  <g transform="translate(460, 120)">
    <circle cx="20" cy="40" r="16" fill="#4338ca" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="45" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">3</text>
    <text x="20" y="10" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#4338ca" text-anchor="middle">Jan &ndash; Feb 2027</text>
    
    <rect x="-40" y="75" width="120" height="110" fill="#ffffff" stroke="#c7d2fe" rx="6" filter="url(#shadow)" />
    <text x="20" y="95" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#4338ca" text-anchor="middle">Transport Models</text>
    <text x="-30" y="115" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Bayesian updating run</text>
    <text x="-30" y="132" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Synthetic donor pool</text>
    <text x="-30" y="150" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Fusion library v1.0</text>
    <text x="-30" y="168" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#475569">&bull; Layering simulation</text>
  </g>

  <!-- Milestone 4: Spring 2027 -->
  <g transform="translate(640, 120)">
    <circle cx="20" cy="40" r="16" fill="#047857" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="45" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">4</text>
    <text x="20" y="10" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#047857" text-anchor="middle">Spring 2027</text>
    
    <rect x="-40" y="75" width="120" height="110" fill="#ecfdf5" stroke="#047857" stroke-width="2" rx="6" filter="url(#shadow)" />
    <text x="20" y="95" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#047857" text-anchor="middle">Flagship Delivery</text>
    <text x="-30" y="115" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#065f46">&bull; Flagship Working Paper</text>
    <text x="-30" y="132" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#065f46">&bull; SusDev Seminar Talk</text>
    <text x="-30" y="150" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#065f46">&bull; Public Open-Source</text>
    <text x="-30" y="168" font-family="Segoe UI, sans-serif" font-size="9.5" fill="#065f46">&bull; Advisor alignment</text>
  </g>

  <!-- Bottom Core Frontiers Card -->
  <g transform="translate(60, 340)" filter="url(#shadow)">
    <rect width="680" height="180" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="340" y="28" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#0f172a" text-anchor="middle">Core Theoretical &amp; Empirical Frontiers Ahead</text>
    
    <g transform="translate(30, 50)" font-family="Segoe UI, sans-serif" font-size="11.5" fill="#334155">
      <circle cx="5" cy="10" r="4" fill="#2563eb" />
      <text x="20" y="14" font-weight="bold" fill="#0f172a">Intervention Combining &amp; Layering:</text>
      <text x="20" y="30" fill="#64748b">Modeling positive complementarities when multiple interventions (cash + food + insurance) are deployed together.</text>

      <circle cx="5" cy="55" r="4" fill="#0f766e" />
      <text x="20" y="59" font-weight="bold" fill="#0f172a">Displacement &amp; Human Mobility Dynamics:</text>
      <text x="20" y="75" fill="#64748b">Treating forced migration not as an error term, but as an endogenous outcome (evacuation vs. entrapment under siege).</text>

      <circle cx="5" cy="100" r="4" fill="#4338ca" />
      <text x="20" y="104" font-weight="bold" fill="#0f172a">Subnational Spatial Resolution Limits:</text>
      <text x="20" y="120" fill="#64748b">Testing how finely conflict point events and displacement vectors can be resolved below Admin-2 to match trial clusters.</text>
    </g>
  </g>
</svg>
"""

# Dictionary of all SVGs to write
svg_dict = {
    "slide01_dilemma_split.svg": svg_01,
    "slide02_decision_contrast.svg": svg_02,
    "slide03_positioning_matrix.svg": svg_03,
    "slide04_reprokit_architecture.svg": svg_04,
    "slide05_architecture_2x2.svg": svg_05,
    "slide06_lit_search_pipeline.svg": svg_06,
    "slide07_data_fusion_stack.svg": svg_07,
    "slide09_trial_extraction_flow.svg": svg_09,
    "slide12_conflict_dag.svg": svg_12,
    "slide13_methodological_toolkit.svg": svg_13,
    "slide14_simulation_dashboard.svg": svg_14,
    "slide15_roadmap_frontiers.svg": svg_15,
}

for filename, content in svg_dict.items():
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"Generated {filename}")

print(f"Successfully generated all {len(svg_dict)} SVG diagrams in {output_dir}")
