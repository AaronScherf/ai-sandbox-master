"""
Generate 12 scholarly SVG diagrams for presentation_slides.marp.md:
Slide 01: Dilemma Split Graphic (Twin Realities)
Slide 02: Planner vs Academic Decision Contrast (Planner on Left)
Slide 03: 2x2 Positioning Matrix (Research Pipeline)
Slide 04: reprokit Architecture
Slide 05: 2x2 System Architecture
Slide 06: Literature Ingest Pipeline
Slide 07: Multi-Modal Data Fusion Stack
Slide 09: Trial Extraction & Geolocation Gate
Slide 12: Causal DAG with Conflict Break (No black fill, no overlap, clear break)
Slide 13: Methodological Toolkit (Light bottom box, dark text)
Slide 14: Simulation Response Dashboard Mockup (Somalia Admin-1 Map, No Arcs)
Slide 15: Research Roadmap & Milestone Flow (Spring 2027, Summer 2027, Fall 2027)
"""

import os

output_dir = r"c:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\notes\00_overview-and-strategy\figures"
os.makedirs(output_dir, exist_ok=True)

# Common SVG defs for arrows and drop shadows
COMMON_DEFS = """
  <defs>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.10" />
    </filter>
    <filter id="glow-red" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#ef4444" flood-opacity="0.35" />
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
# Slide 01: Dilemma Graphic (Twin Operational Realities Faced by Planner)
# ==============================================================================
svg_01 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  
  <!-- Header Banner -->
  <text x="420" y="44" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">The Humanitarian Planning Problem</text>
  <text x="420" y="72" font-family="Segoe UI, sans-serif" font-size="16" fill="#475569" text-anchor="middle">Dual Realities Confronted Simultaneously in Crisis Response</text>

  <!-- Left Column: Operational Reality -->
  <g transform="translate(35, 95)" filter="url(#shadow)">
    <rect width="360" height="435" fill="#ffffff" stroke="#fca5a5" stroke-width="2.5" rx="10" />
    <rect width="360" height="52" fill="#fee2e2" rx="10" />
    <rect width="360" height="10" y="42" fill="#fee2e2" />
    <text x="25" y="34" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold" fill="#991b1b">&#x23F1; Operational Reality (The Planner)</text>
    
    <!-- Badges -->
    <rect x="25" y="68" width="310" height="46" fill="#fff1f2" stroke="#fda4af" rx="6" />
    <text x="40" y="97" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#be123c">Response Window: 2 &ndash; 3 Weeks</text>
    
    <!-- Bullets -->
    <g transform="translate(25, 138)" font-family="Segoe UI, sans-serif" font-size="14.5" fill="#334155">
      <circle cx="8" cy="12" r="5" fill="#ef4444" />
      <text x="24" y="17" font-weight="bold" fill="#0f172a">Immediate Resource Allocation</text>
      <text x="24" y="36" font-size="13" fill="#64748b">Must deploy aid packages before famine peaks.</text>
      
      <circle cx="8" cy="68" r="5" fill="#ef4444" />
      <text x="24" y="73" font-weight="bold" fill="#0f172a">Hard Budget Constraints</text>
      <text x="24" y="92" font-size="13" fill="#64748b">Fixed funds; must pick optimal intervention mix.</text>
      
      <circle cx="8" cy="124" r="5" fill="#ef4444" />
      <text x="24" y="129" font-weight="bold" fill="#0f172a">Zero Fieldwork Feasibility</text>
      <text x="24" y="148" font-size="13" fill="#64748b">Cannot run 6-month survey or pilot RCT in war.</text>

      <circle cx="8" cy="180" r="5" fill="#ef4444" />
      <text x="24" y="185" font-weight="bold" fill="#0f172a">Current Fallback</text>
      <text x="24" y="204" font-size="13" fill="#b91c1c" font-weight="bold">Subjective heuristics &amp; qualitative tabletop guessing.</text>
    </g>
  </g>

  <!-- Right Column: Evidence Landscape -->
  <g transform="translate(445, 95)" filter="url(#shadow)">
    <rect width="360" height="435" fill="#ffffff" stroke="#93c5fd" stroke-width="2.5" rx="10" />
    <rect width="360" height="52" fill="#dbeafe" rx="10" />
    <rect width="360" height="10" y="42" fill="#dbeafe" />
    <text x="25" y="34" font-family="Segoe UI, sans-serif" font-size="18" font-weight="bold" fill="#1e3a8a">&#x1F4DA; Evidence Friction (The Literature)</text>
    
    <!-- Badges -->
    <rect x="25" y="68" width="310" height="46" fill="#eff6ff" stroke="#bfdbfe" rx="6" />
    <text x="40" y="97" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#1d4ed8">10,000+ Available Evaluations</text>
    
    <!-- Bullets -->
    <g transform="translate(25, 138)" font-family="Segoe UI, sans-serif" font-size="14.5" fill="#334155">
      <circle cx="8" cy="12" r="5" fill="#3b82f6" />
      <text x="24" y="17" font-weight="bold" fill="#0f172a">Prohibitive Search Costs</text>
      <text x="24" y="36" font-size="13" fill="#64748b">Buried across 3ie, J-PAL, World Bank, and paywalls.</text>
      
      <circle cx="8" cy="68" r="5" fill="#3b82f6" />
      <text x="24" y="73" font-weight="bold" fill="#0f172a">Complex Econometric Jargon</text>
      <text x="24" y="92" font-size="13" fill="#64748b">Written for methodologists, not field directors.</text>
      
      <circle cx="8" cy="124" r="5" fill="#3b82f6" />
      <text x="24" y="129" font-weight="bold" fill="#0f172a">Single-Program Isolation</text>
      <text x="24" y="148" font-size="13" fill="#64748b">Isolates one program; ignores opportunity costs.</text>

      <circle cx="8" cy="180" r="5" fill="#3b82f6" />
      <text x="24" y="185" font-weight="bold" fill="#0f172a">Uncertain Local Relevance</text>
      <text x="24" y="204" font-size="13" fill="#1e3a8a" font-weight="bold">Does peacetime cash evidence hold in blockaded crises?</text>
    </g>
  </g>

  <!-- Unifying Center Connector (Not VS, but Dual Contexts) -->
  <g transform="translate(390, 280)">
    <circle cx="30" cy="0" r="26" fill="#0f172a" stroke="#ffffff" stroke-width="3" />
    <text x="30" y="8" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#ffffff" text-anchor="middle">+</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 02: Decision Contrast (Humanitarian Planner on LEFT, Academic on RIGHT)
# ==============================================================================
svg_02 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  <text x="420" y="44" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Divergence in Mandate: Planner vs. Researcher</text>
  <text x="420" y="72" font-family="Segoe UI, sans-serif" font-size="16" fill="#475569" text-anchor="middle">Real-World Portfolio Optimization vs. Internal Causal Identification</text>

  <!-- LEFT Card: Humanitarian Planner (Green) -->
  <g transform="translate(35, 95)" filter="url(#shadow)">
    <rect width="360" height="445" fill="#ffffff" stroke="#059669" stroke-width="2.5" rx="10" />
    <path d="M 0 10 Q 0 0 10 0 L 350 0 Q 360 0 360 10 L 360 48 L 0 48 Z" fill="#047857" />
    <text x="180" y="32" font-family="Segoe UI, sans-serif" font-size="17" font-weight="bold" fill="#ffffff" text-anchor="middle">The Humanitarian Planner Mandate</text>
    
    <g transform="translate(24, 70)" font-family="Segoe UI, sans-serif" font-size="14.5" fill="#334155">
      <text y="16" font-weight="bold" fill="#0f172a">Core Objective:</text>
      <text y="38" fill="#475569">Maximize lives saved under hard budget caps.</text>
      
      <text y="82" font-weight="bold" fill="#0f172a">Primary Question:</text>
      <rect y="96" width="312" height="58" fill="#ecfdf5" stroke="#a7f3d0" rx="6" />
      <text x="12" y="120" font-style="italic" font-weight="bold" fill="#065f46">"Given $5M and 3 weeks in District Z,</text>
      <text x="12" y="142" font-style="italic" font-weight="bold" fill="#065f46">what mix of A, B, or C minimizes loss?"</text>
      
      <text y="184" font-weight="bold" fill="#0f172a">Intervention Framing:</text>
      <text y="206" fill="#475569">Open portfolio choice &amp; program layering.</text>
      
      <text y="250" font-weight="bold" fill="#0f172a">Time Horizon:</text>
      <text y="272" fill="#475569">Days or weeks before emergency peak.</text>

      <text y="316" font-weight="bold" fill="#0f172a">Tolerance for Uncertainty:</text>
      <text y="338" fill="#047857" font-weight="bold">Satisficing: Needs honest probabilistic bounds.</text>
      
      <rect y="360" width="312" height="36" fill="#ecfdf5" stroke="#6ee7b7" rx="6" />
      <text x="156" y="384" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Goal: Simulation Response Exercise</text>
    </g>
  </g>

  <!-- RIGHT Card: Academic Researcher (Blue) -->
  <g transform="translate(445, 95)" filter="url(#shadow)">
    <rect width="360" height="445" fill="#ffffff" stroke="#3b82f6" stroke-width="2" rx="10" />
    <path d="M 0 10 Q 0 0 10 0 L 350 0 Q 360 0 360 10 L 360 48 L 0 48 Z" fill="#1e3a8a" />
    <text x="180" y="32" font-family="Segoe UI, sans-serif" font-size="17" font-weight="bold" fill="#ffffff" text-anchor="middle">The Academic Research Mandate</text>
    
    <g transform="translate(24, 70)" font-family="Segoe UI, sans-serif" font-size="14.5" fill="#334155">
      <text y="16" font-weight="bold" fill="#0f172a">Core Objective:</text>
      <text y="38" fill="#475569">Isolate single causal parameter (internal validity).</text>
      
      <text y="82" font-weight="bold" fill="#0f172a">Primary Question:</text>
      <rect y="96" width="312" height="58" fill="#eff6ff" stroke="#bfdbfe" rx="6" />
      <text x="12" y="125" font-style="italic" font-weight="bold" fill="#1e40af">"Does Intervention X cause Outcome Y?"</text>
      <text x="12" y="145" font-size="12" fill="#64748b">(Holding all other contextual factors constant)</text>
      
      <text y="184" font-weight="bold" fill="#0f172a">Intervention Framing:</text>
      <text y="206" fill="#475569">Single intervention evaluated in isolation.</text>
      
      <text y="250" font-weight="bold" fill="#0f172a">Time Horizon:</text>
      <text y="272" fill="#475569">3 to 5 years (design, survey, peer review).</text>

      <text y="316" font-weight="bold" fill="#0f172a">Tolerance for Uncertainty:</text>
      <text y="338" fill="#475569">Low: Prefers no estimate over an unverified proxy.</text>
      
      <rect y="360" width="312" height="36" fill="#f1f5f9" stroke="#cbd5e1" rx="6" />
      <text x="156" y="384" font-weight="bold" fill="#334155" text-anchor="middle">&#x2713; Gold Standard: Clustered RCT</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 03: 2x2 Positioning Matrix (Research Pipeline)
# ==============================================================================
svg_03 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  <text x="420" y="42" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Crisis Evidence Landscape: 2x2 Positioning</text>
  <text x="420" y="70" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Situating This Research Pipeline Against Existing Frameworks</text>

  <!-- Axes -->
  <line x1="100" y1="300" x2="750" y2="300" stroke="#94a3b8" stroke-width="2.5" marker-end="url(#arrow)" />
  <line x1="420" y1="510" x2="420" y2="105" stroke="#94a3b8" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Axis Labels -->
  <text x="760" y="306" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#0f172a">Causal &amp; Predictive &rarr;</text>
  <text x="90" y="306" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#64748b" text-anchor="end">&larr; Static &amp; Descriptive</text>
  
  <text x="420" y="94" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#0f172a" text-anchor="middle">&uarr; Rapid &amp; Operational</text>
  <text x="420" y="535" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#64748b" text-anchor="middle">&darr; Retrospective / Academic Only</text>

  <!-- Quadrant 1: 3ie Maps (Bottom Left) -->
  <g transform="translate(140, 335)" filter="url(#shadow)">
    <rect width="240" height="145" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="18" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#0f172a">3ie Evidence Maps</text>
    <text x="18" y="55" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Static manual curation</text>
    <text x="18" y="78" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Descriptive bibliography</text>
    <text x="18" y="101" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; No reusable estimators</text>
    <text x="18" y="125" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#e11d48">&#x2717; No spatial context</text>
  </g>

  <!-- Quadrant 2: World Bank Portals (Top Left) -->
  <g transform="translate(140, 130)" filter="url(#shadow)">
    <rect width="240" height="145" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="18" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#0f172a">World Bank / HDX Portals</text>
    <text x="18" y="55" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Real-time situational feeds</text>
    <text x="18" y="78" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Rich GIS map dashboards</text>
    <text x="18" y="101" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Passive visualizers</text>
    <text x="18" y="125" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#e11d48">&#x2717; No counterfactual engine</text>
  </g>

  <!-- Quadrant 3: Academic Hierarchical Models (Bottom Right) -->
  <g transform="translate(460, 335)" filter="url(#shadow)">
    <rect width="250" height="145" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <text x="18" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#0f172a">Academic Meta-Analysis</text>
    <text x="18" y="48" font-family="Segoe UI, sans-serif" font-size="12" fill="#1e40af">Meager (2019), Vivalt (2020)</text>
    <text x="18" y="74" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Bayesian hierarchical pooling</text>
    <text x="18" y="97" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#64748b">&bull; Rigorous causal variance</text>
    <text x="18" y="123" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#e11d48">&#x2717; Requires survey microdata</text>
  </g>

  <!-- Quadrant 4: RESEARCH PIPELINE (Top Right - Highlighted) -->
  <g transform="translate(460, 115)" filter="url(#shadow)">
    <rect width="260" height="165" fill="#eff6ff" stroke="#2563eb" stroke-width="3" rx="10" />
    <rect x="0" y="0" width="260" height="38" fill="#2563eb" rx="10" />
    <rect x="0" y="26" width="260" height="12" fill="#2563eb" />
    <text x="130" y="26" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x2605; Research Pipeline</text>
    
    <text x="16" y="62" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#1e3a8a">&bull; Automated OpenAlex Ingestion</text>
    <text x="16" y="84" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#1e3a8a">&bull; Subnational Spatial Panel Fusion</text>
    <text x="16" y="106" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#1e3a8a">&bull; Causal Transportability Engine</text>
    <text x="16" y="128" font-family="Segoe UI, sans-serif" font-size="13.5" font-weight="bold" fill="#047857">&bull; Simulation Response Exercise</text>
    <rect x="15" y="136" width="230" height="22" fill="#dbeafe" rx="4" />
    <text x="130" y="152" font-family="Segoe UI, sans-serif" font-size="11.5" font-weight="bold" fill="#1e40af" text-anchor="middle">Operational Decision Support</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 04: reprokit Architecture
# ==============================================================================
svg_04 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  <text x="420" y="44" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">reprokit Architecture: Standardizing Open Science</text>
  <text x="420" y="72" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Reproducible by Anyone &bull; Legible to Humans &bull; Scalable by AI Agents</text>

  <!-- Block 1: Copier Template -->
  <g transform="translate(35, 105)" filter="url(#shadow)">
    <rect width="230" height="200" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="230" height="40" fill="#1e293b" rx="8" />
    <rect width="230" height="10" y="30" fill="#1e293b" />
    <text x="115" y="26" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">1. Project Templates</text>
    <g transform="translate(18, 60)" font-family="Segoe UI, sans-serif" font-size="14" fill="#334155">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; study:</text>
      <text x="60" y="16" fill="#64748b">Empirical panels</text>
      <text y="44" font-weight="bold" fill="#0f172a">&bull; evidence:</text>
      <text x="75" y="44" fill="#64748b">Taxonomy maps</text>
      <text y="72" font-weight="bold" fill="#0f172a">&bull; library:</text>
      <text x="60" y="72" fill="#64748b">Analytics tools</text>
      <rect y="92" width="194" height="32" fill="#f1f5f9" rx="4" />
      <text x="97" y="113" font-family="monospace" font-size="12.5" font-weight="bold" fill="#047857" text-anchor="middle">copier copy template</text>
    </g>
  </g>

  <!-- Arrow 1 -> 2 -->
  <line x1="265" y1="205" x2="305" y2="205" stroke="#64748b" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Block 2: Dual Interface -->
  <g transform="translate(305, 105)" filter="url(#shadow)">
    <rect width="230" height="200" fill="#ffffff" stroke="#3b82f6" stroke-width="2.5" rx="8" />
    <rect width="230" height="40" fill="#2563eb" rx="8" />
    <rect width="230" height="10" y="30" fill="#2563eb" />
    <text x="115" y="26" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Dual Interface</text>
    <g transform="translate(18, 60)" font-family="Segoe UI, sans-serif" font-size="14" fill="#334155">
      <text y="16" font-weight="bold" fill="#1e40af">&#x1F464; For Humans:</text>
      <text y="36" font-size="12.5" fill="#64748b">Clear README &amp; protocol.md</text>
      
      <text y="70" font-weight="bold" fill="#059669">&#x1F916; For AI Agents:</text>
      <text y="90" font-size="12.5" fill="#64748b">AGENTS.md + project.yaml</text>
      
      <rect y="104" width="194" height="28" fill="#eff6ff" rx="4" />
      <text x="97" y="123" font-size="12" font-weight="bold" fill="#2563eb" text-anchor="middle">Audit at machine scale</text>
    </g>
  </g>

  <!-- Arrow 2 -> 3 -->
  <line x1="535" y1="205" x2="575" y2="205" stroke="#64748b" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Block 3: Verification Engine -->
  <g transform="translate(575, 105)" filter="url(#shadow)">
    <rect width="230" height="200" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="230" height="40" fill="#0f172a" rx="8" />
    <rect width="230" height="10" y="30" fill="#0f172a" />
    <text x="115" y="26" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">3. Verification Engine</text>
    <g transform="translate(18, 60)" font-family="Segoe UI, sans-serif" font-size="14" fill="#334155">
      <text y="16" font-weight="bold" fill="#0f172a">&bull; SHA-256 Hashes:</text>
      <text y="36" font-size="12" fill="#64748b">Pinned raw inputs &amp; outputs</text>
      <text y="64" font-weight="bold" fill="#0f172a">&bull; CI Test Harness:</text>
      <text y="84" font-size="12" fill="#64748b">Automated pytest suite</text>
      <rect y="100" width="194" height="30" fill="#ecfdf5" rx="4" />
      <text x="97" y="120" font-size="12.5" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Green on Linux &amp; Windows</text>
    </g>
  </g>

  <!-- Bottom Banner: Portability across crises -->
  <g transform="translate(35, 335)" filter="url(#shadow)">
    <rect width="770" height="215" fill="#ffffff" stroke="#e2e8f0" rx="10" />
    <text x="385" y="34" font-family="Segoe UI, sans-serif" font-size="17" font-weight="bold" fill="#0f172a" text-anchor="middle">Why It Matters: Instant Portability Across Geographies</text>
    
    <g transform="translate(25, 60)" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#334155">
      <rect width="225" height="135" fill="#f8fafc" stroke="#cbd5e1" rx="8" />
      <text x="112" y="28" font-size="15" font-weight="bold" fill="#1e3a8a" text-anchor="middle">Somalia Baseline</text>
      <text x="18" y="58" fill="#64748b">&bull; Drought + ACLED + WFP</text>
      <text x="18" y="82" fill="#64748b">&bull; 100% hash verified on CI</text>
      <text x="18" y="110" font-weight="bold" fill="#059669">&#x2713; Completed pipeline</text>

      <rect x="245" y="0" width="225" height="135" fill="#f8fafc" stroke="#cbd5e1" rx="8" />
      <text x="357" y="28" font-size="15" font-weight="bold" fill="#1e3a8a" text-anchor="middle">Sudan Portability</text>
      <text x="263" y="58" fill="#64748b">&bull; Swapped boundary rasters</text>
      <text x="263" y="82" fill="#64748b">&bull; Identical code runs cleanly</text>
      <text x="263" y="110" font-weight="bold" fill="#059669">&#x2713; Portability confirmed</text>

      <rect x="490" y="0" width="230" height="135" fill="#eff6ff" stroke="#3b82f6" stroke-width="2" rx="8" />
      <text x="605" y="28" font-size="15" font-weight="bold" fill="#2563eb" text-anchor="middle">Next Crisis Setting</text>
      <text x="508" y="58" fill="#1e40af">&bull; Ukraine / Armenia / Sahel</text>
      <text x="508" y="82" fill="#1e40af">&bull; Zero pipeline re-engineering</text>
      <text x="508" y="110" font-weight="bold" fill="#2563eb">&rarr; Ready to ingest</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 05: 2x2 System Architecture (Full-Width Visual)
# ==============================================================================
svg_05 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 620" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="960" height="620" fill="#f8fafc" rx="12" />
  <text x="480" y="42" font-family="Segoe UI, sans-serif" font-size="26" font-weight="bold" fill="#0f172a" text-anchor="middle">The 2x2 System Architecture</text>
  <text x="480" y="72" font-family="Segoe UI, sans-serif" font-size="16" fill="#475569" text-anchor="middle">Integrating Context Ingestion, Evidence Synthesis, and Causal Transportability</text>

  <!-- 2x2 Grid Layout -->
  <!-- Top Left: 1.1 Literature Discovery -->
  <g transform="translate(60, 95)" filter="url(#shadow)">
    <rect width="390" height="205" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <rect width="390" height="42" fill="#1e293b" rx="10" />
    <rect width="390" height="10" y="32" fill="#1e293b" />
    <text x="20" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#ffffff">1.1 Literature Search &amp; Synthesis</text>
    <g transform="translate(20, 58)" font-family="Segoe UI, sans-serif" font-size="14" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Automated OpenAlex harvester &amp; web crawlers</text>
      <text y="42">&bull; Snowball citation graph &amp; embedding matching</text>
      <text y="66">&bull; Grey literature: ALNAP, ReliefWeb, World Bank OKR</text>
      <rect y="84" width="350" height="32" fill="#f1f5f9" stroke="#cbd5e1" rx="6" />
      <text x="175" y="105" font-size="13" font-weight="bold" fill="#0f172a" text-anchor="middle">Standalone Synthesis Review Deliverable</text>
    </g>
  </g>

  <!-- Top Right: 2.1 3ie Taxonomy -->
  <g transform="translate(510, 95)" filter="url(#shadow)">
    <rect width="390" height="205" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <rect width="390" height="42" fill="#1e3a8a" rx="10" />
    <rect width="390" height="10" y="32" fill="#1e3a8a" />
    <text x="20" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#ffffff">2.1 3ie Taxonomy &amp; Gap Analysis</text>
    <g transform="translate(20, 58)" font-family="Segoe UI, sans-serif" font-size="14" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Multi-dimensional matrix classification</text>
      <text y="42">&bull; Interventions &times; Outcomes &times; Country Geographies</text>
      <text y="66">&bull; Pinpoints acute "evidence deserts" in conflict</text>
      <rect y="84" width="350" height="32" fill="#eff6ff" stroke="#bfdbfe" rx="6" />
      <text x="175" y="105" font-size="13" font-weight="bold" fill="#1e40af" text-anchor="middle">Quantified Evidence Coverage Heatmaps</text>
    </g>
  </g>

  <!-- Bottom Left: 1.2 Context Data Fusion -->
  <g transform="translate(60, 325)" filter="url(#shadow)">
    <rect width="390" height="205" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <rect width="390" height="42" fill="#0f766e" rx="10" />
    <rect width="390" height="10" y="32" fill="#0f766e" />
    <text x="20" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#ffffff">1.2 Context Data Fusion Panel</text>
    <g transform="translate(20, 58)" font-family="Segoe UI, sans-serif" font-size="14" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Multi-modal spatial data fusion library</text>
      <text y="42">&bull; CHIRPS rain, ACLED conflict, WFP commodity prices</text>
      <text y="66">&bull; Admin-2 district-month spatiotemporal harmonization</text>
      <rect y="84" width="350" height="32" fill="#f0fdfa" stroke="#99f6e4" rx="6" />
      <text x="175" y="105" font-size="13" font-weight="bold" fill="#0f766e" text-anchor="middle">Harmonized Subnational Panel Table Asset</text>
    </g>
  </g>

  <!-- Bottom Right: 2.2 Reproducible Trials -->
  <g transform="translate(510, 325)" filter="url(#shadow)">
    <rect width="390" height="205" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <rect width="390" height="42" fill="#4338ca" rx="10" />
    <rect width="390" height="10" y="32" fill="#4338ca" />
    <text x="20" y="28" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#ffffff">2.2 Reproducible Trials Repository</text>
    <g transform="translate(20, 58)" font-family="Segoe UI, sans-serif" font-size="14" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Curates open crisis RCT microdata</text>
      <text y="42">&bull; AEA, World Bank DIME, Harvard &amp; J-PAL Dataverse</text>
      <text y="66">&bull; Village GPS coordinate audit (The Geolocation Gate)</text>
      <rect y="84" width="350" height="32" fill="#eef2ff" stroke="#c7d2fe" rx="6" />
      <text x="175" y="105" font-size="13" font-weight="bold" fill="#4338ca" text-anchor="middle">Causally Valid Treatment Estimators</text>
    </g>
  </g>

  <!-- Connecting arrows for feedback loops -->
  <path d="M 450 185 L 510 185" stroke="#2563eb" stroke-width="2.5" marker-end="url(#arrow-blue)" />
  <path d="M 255 300 L 255 325" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />
  <path d="M 705 300 L 705 325" stroke="#4338ca" stroke-width="2.5" marker-end="url(#arrow)" />
  <path d="M 450 425 L 510 425" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />

  <!-- Bottom Convergence Banner -->
  <g transform="translate(60, 545)" filter="url(#shadow)">
    <rect width="840" height="60" fill="#0f172a" rx="8" />
    <text x="420" y="26" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff" text-anchor="middle">&darr; CONVERGENCE: Causal Transportability &amp; Simulation Engine &darr;</text>
    <text x="420" y="46" font-family="Segoe UI, sans-serif" font-size="13" fill="#94a3b8" text-anchor="middle">Anchoring Trial Estimators to Context Grids &bull; Predicting Impact in Novel Crises</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 06: Literature Ingest Pipeline
# ==============================================================================
svg_06 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 560" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="560" fill="#f8fafc" rx="12" />
  <text x="420" y="44" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Component 1.1: Automated Literature Discovery Pipeline</text>
  <text x="420" y="72" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Collapsing Literature Search Costs from Months to Minutes</text>

  <!-- Step 1: Harvester -->
  <g transform="translate(35, 105)" filter="url(#shadow)">
    <rect width="170" height="280" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="170" height="38" fill="#1e293b" rx="8" />
    <rect width="170" height="10" y="28" fill="#1e293b" />
    <text x="85" y="25" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">1. API Harvester</text>
    <g transform="translate(14, 55)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; OpenAlex API</text>
      <text y="36">Academic corpus</text>
      <text y="68" font-weight="bold" fill="#0f172a">&bull; Grey Literature:</text>
      <text y="88">ALNAP reports</text>
      <text y="106">ReliefWeb</text>
      <text y="124">World Bank OKR</text>
      <rect y="150" width="142" height="55" fill="#f1f5f9" rx="6" />
      <text x="71" y="174" font-size="11.5" fill="#475569" text-anchor="middle">Automated keyword</text>
      <text x="71" y="192" font-size="11.5" fill="#475569" text-anchor="middle">&amp; taxonomy triggers</text>
    </g>
  </g>

  <line x1="205" y1="245" x2="235" y2="245" stroke="#64748b" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Step 2: Semantic Filter -->
  <g transform="translate(235, 105)" filter="url(#shadow)">
    <rect width="170" height="280" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="170" height="38" fill="#1e3a8a" rx="8" />
    <rect width="170" height="10" y="28" fill="#1e3a8a" />
    <text x="85" y="25" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Filter Engine</text>
    <g transform="translate(14, 55)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Geographic Tag</text>
      <text y="36">Somalia, Sudan...</text>
      <text y="68" font-weight="bold" fill="#0f172a">&bull; Hazard Vector</text>
      <text y="88">Drought, flood, war</text>
      <text y="118" font-weight="bold" fill="#0f172a">&bull; Program Type</text>
      <text y="136">Cash, food, insurance</text>
      <rect y="155" width="142" height="50" fill="#eff6ff" rx="6" />
      <text x="71" y="176" font-size="11.5" font-weight="bold" fill="#1e40af" text-anchor="middle">Embedding similarity</text>
      <text x="71" y="194" font-size="11.5" fill="#1e40af" text-anchor="middle">relevance score</text>
    </g>
  </g>

  <line x1="405" y1="245" x2="435" y2="245" stroke="#64748b" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Step 3: Citation Snowball -->
  <g transform="translate(435, 105)" filter="url(#shadow)">
    <rect width="170" height="280" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="170" height="38" fill="#0f766e" rx="8" />
    <rect width="170" height="10" y="28" fill="#0f766e" />
    <text x="85" y="25" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">3. Snowball Graph</text>
    <g transform="translate(14, 55)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Backward Trace</text>
      <text y="36">Ingests cited trials</text>
      <text y="68" font-weight="bold" fill="#0f172a">&bull; Forward Trace</text>
      <text y="88">Captures replications</text>
      <text y="118" font-weight="bold" fill="#0f172a">&bull; Co-authorship</text>
      <text y="136">Traces research hubs</text>
      <rect y="155" width="142" height="50" fill="#f0fdfa" rx="6" />
      <text x="71" y="176" font-size="11.5" font-weight="bold" fill="#0f766e" text-anchor="middle">Discovers unindexed</text>
      <text x="71" y="194" font-size="11.5" fill="#0f766e" text-anchor="middle">evaluations</text>
    </g>
  </g>

  <line x1="605" y1="245" x2="635" y2="245" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />

  <!-- Step 4: Standalone Usable Outputs -->
  <g transform="translate(635, 105)" filter="url(#shadow)">
    <rect width="170" height="280" fill="#ecfdf5" stroke="#059669" stroke-width="2.5" rx="8" />
    <rect width="170" height="38" fill="#059669" rx="8" />
    <rect width="170" height="10" y="28" fill="#059669" />
    <text x="85" y="25" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">4. Usable Outputs</text>
    <g transform="translate(14, 55)" font-family="Segoe UI, sans-serif" font-size="13" fill="#065f46">
      <text y="18" font-weight="bold">&bull; Literature Review</text>
      <text y="36">Formatted Markdown</text>
      <text y="54">ready to publish</text>
      <text y="88" font-weight="bold">&bull; Search Manifest</text>
      <text y="106">Machine-readable</text>
      <text y="124">references.yaml</text>
      <rect y="150" width="142" height="55" fill="#ffffff" stroke="#a7f3d0" rx="6" />
      <text x="71" y="174" font-size="11.5" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Immediate utility</text>
      <text x="71" y="192" font-size="11.5" fill="#047857" text-anchor="middle">for practitioners</text>
    </g>
  </g>

  <!-- Bottom Card -->
  <g transform="translate(35, 410)" filter="url(#shadow)">
    <rect width="770" height="125" fill="#ffffff" stroke="#e2e8f0" rx="8" />
    <text x="385" y="30" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#0f172a" text-anchor="middle">Direct Value to Humanitarian Planning</text>
    <text x="385" y="58" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#475569" text-anchor="middle">Instead of spending 6 months in library searches, a response team generates a verified, structured literature digest in minutes,</text>
    <text x="385" y="80" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#475569" text-anchor="middle">instantly identifying what has been tried in similar contexts and what risks were reported.</text>
    <rect x="260" y="94" width="250" height="24" fill="#ecfdf5" rx="4" />
    <text x="385" y="110" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#047857" text-anchor="middle">Feeds directly into 3ie Taxonomy &amp; Gap Analysis</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 07: Multi-Modal Data Fusion Stack (Fixed Overlaps)
# ==============================================================================
svg_07 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  <text x="420" y="42" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Component 1.2: Multi-Modal Context Data Fusion Stack</text>
  <text x="420" y="70" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Converting High-Dimensional Raster Geodata into Structured Subnational Context</text>

  <!-- 4 Stacked Layers with Title shifted up-left, Badges down-right -->
  <!-- Layer 1: Satellite Rasters -->
  <g transform="translate(60, 95)" filter="url(#shadow)">
    <polygon points="120,0 680,0 560,65 0,65" fill="#e0f2fe" stroke="#38bdf8" stroke-width="2" />
    <text x="140" y="28" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#0369a1">Layer 1: Earth Observation Rasters (CHIRPS Rain, VIIRS Lights, NDVI)</text>
    <rect x="520" y="32" width="115" height="22" fill="#ffffff" stroke="#38bdf8" rx="4" />
    <text x="577" y="47" font-family="monospace" font-size="11.5" font-weight="bold" fill="#0284c7" text-anchor="middle">GeoTIFF 5km</text>
  </g>

  <!-- Layer 2: Conflict Points -->
  <g transform="translate(60, 155)" filter="url(#shadow)">
    <polygon points="120,0 680,0 560,65 0,65" fill="#fee2e2" stroke="#f87171" stroke-width="2" />
    <text x="140" y="28" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#b91c1c">Layer 2: Conflict Point Processes (ACLED Battles, UCDP Fatalities)</text>
    <rect x="520" y="32" width="115" height="22" fill="#ffffff" stroke="#f87171" rx="4" />
    <text x="577" y="47" font-family="monospace" font-size="11.5" font-weight="bold" fill="#dc2626" text-anchor="middle">Point GeoJSON</text>
  </g>

  <!-- Layer 3: Market Prices -->
  <g transform="translate(60, 215)" filter="url(#shadow)">
    <polygon points="120,0 680,0 560,65 0,65" fill="#fef3c7" stroke="#fbbf24" stroke-width="2" />
    <text x="140" y="28" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#b45309">Layer 3: Market Commodity Prices (WFP / FSNAU Maize, Sorghum, Wheat)</text>
    <rect x="520" y="32" width="115" height="22" fill="#ffffff" stroke="#fbbf24" rx="4" />
    <text x="577" y="47" font-family="monospace" font-size="11.5" font-weight="bold" fill="#d97706" text-anchor="middle">Tabular CSV</text>
  </g>

  <!-- Layer 4: Human Mobility -->
  <g transform="translate(60, 275)" filter="url(#shadow)">
    <polygon points="120,0 680,0 560,65 0,65" fill="#ede9fe" stroke="#a78bfa" stroke-width="2" />
    <text x="140" y="28" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#6d28d9">Layer 4: Forced Displacement Vectors (UNHCR PRMN / IOM DTM Flows)</text>
    <rect x="520" y="32" width="115" height="22" fill="#ffffff" stroke="#a78bfa" rx="4" />
    <text x="577" y="47" font-family="monospace" font-size="11.5" font-weight="bold" fill="#7c3aed" text-anchor="middle">Origin-Dest API</text>
  </g>

  <!-- Downward Arrow & Fusion Library Box (Wider, no text overflow) -->
  <line x1="420" y1="355" x2="420" y2="395" stroke="#059669" stroke-width="3" marker-end="url(#arrow-emerald)" />
  <rect x="150" y="365" width="540" height="30" fill="#ecfdf5" stroke="#059669" stroke-width="1.8" rx="6" />
  <text x="420" y="385" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#047857" text-anchor="middle">Automated Open-Source Fusion Library (Standardized Spatial Joins &amp; Missingness Audits)</text>

  <!-- Resulting Table Box -->
  <g transform="translate(60, 410)" filter="url(#shadow)">
    <rect width="720" height="150" fill="#ffffff" stroke="#047857" stroke-width="2.5" rx="10" />
    <rect width="720" height="34" fill="#047857" rx="10" />
    <rect width="720" height="10" y="24" fill="#047857" />
    <text x="360" y="23" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">Output: Harmonized Subnational Panel Table (District-Month / Admin-2)</text>
    
    <!-- Mini Table Layout -->
    <g transform="translate(25, 46)" font-family="monospace" font-size="12" fill="#334155">
      <rect width="670" height="24" fill="#f1f5f9" />
      <text x="10" y="17" font-weight="bold" fill="#0f172a">district_id</text>
      <text x="110" y="17" font-weight="bold" fill="#0f172a">month</text>
      <text x="190" y="17" font-weight="bold" fill="#0f172a">rain_zscore</text>
      <text x="310" y="17" font-weight="bold" fill="#0f172a">conflict_events</text>
      <text x="460" y="17" font-weight="bold" fill="#0f172a">sorghum_price</text>
      <text x="580" y="17" font-weight="bold" fill="#0f172a">idp_arrivals</text>
      
      <text x="10" y="42">SO-BAIDOA</text>
      <text x="110" y="42">2022-04</text>
      <text x="190" y="42" font-weight="bold" fill="#dc2626">-2.41 (Drought)</text>
      <text x="310" y="42" font-weight="bold" fill="#dc2626">14 battles</text>
      <text x="460" y="42">+45% YoY</text>
      <text x="580" y="42">3,420</text>
      
      <text x="10" y="64">SO-MOGAD</text>
      <text x="110" y="64">2022-04</text>
      <text x="190" y="64">-1.12</text>
      <text x="310" y="64">8 events</text>
      <text x="460" y="64">+22% YoY</text>
      <text x="580" y="64">11,200</text>
    </g>
    <text x="360" y="138" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#059669" text-anchor="middle">&#x2713; CI Hash-Verified for Somalia &amp; Sudan &bull; Standalone Reusable Research Asset</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 09: Trial Extraction & Geolocation Gate (No Text Spills)
# ==============================================================================
svg_09 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  <text x="420" y="42" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Component 2.2: Trial Extraction &amp; The Geolocation Gate</text>
  <text x="420" y="70" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Curating Whole Evaluation Databases &bull; Overcoming the GPS Privacy Hurdle</text>

  <!-- Step 1: Global Repositories -->
  <g transform="translate(35, 105)" filter="url(#shadow)">
    <rect width="210" height="255" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="210" height="38" fill="#1e293b" rx="8" />
    <rect width="210" height="10" y="28" fill="#1e293b" />
    <text x="105" y="25" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">1. Full Repositories</text>
    <g transform="translate(16, 56)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; AEA Data &amp; Code</text>
      <text y="36">4,000 village Niger trial</text>
      <text y="68" font-weight="bold" fill="#0f172a">&bull; World Bank DIME</text>
      <text y="86">Bangladesh flood cash</text>
      <text y="118" font-weight="bold" fill="#0f172a">&bull; Harvard Dataverse</text>
      <text y="136">&bull; J-PAL Dataverse</text>
      <rect y="156" width="178" height="32" fill="#eff6ff" rx="4" />
      <text x="89" y="177" font-size="12" font-weight="bold" fill="#1e40af" text-anchor="middle">Screen for crisis RCTs</text>
    </g>
  </g>

  <line x1="245" y1="230" x2="285" y2="230" stroke="#64748b" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Step 2: Estimator Audit -->
  <g transform="translate(285, 105)" filter="url(#shadow)">
    <rect width="220" height="255" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="220" height="38" fill="#1e3a8a" rx="8" />
    <rect width="220" height="10" y="28" fill="#1e3a8a" />
    <text x="110" y="25" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Estimator Audit</text>
    <g transform="translate(16, 56)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Open Microdata:</text>
      <text y="36">Confirm replication package</text>
      <text y="68" font-weight="bold" fill="#0f172a">&bull; Causal Identification:</text>
      <text y="86">Cluster RCT or clean quasi</text>
      <text y="118" font-weight="bold" fill="#0f172a">&bull; Treatment Estimator:</text>
      <text y="136">ITT / LATE on welfare</text>
      <rect y="156" width="188" height="32" fill="#f1f5f9" rx="4" />
      <text x="94" y="177" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">Standardized effect size</text>
    </g>
  </g>

  <line x1="505" y1="230" x2="545" y2="230" stroke="#b91c1c" stroke-width="2.5" marker-end="url(#arrow-red)" />

  <!-- Step 3: THE GEOLOCATION GATE -->
  <g transform="translate(545, 95)" filter="url(#shadow)">
    <rect width="260" height="275" fill="#fff1f2" stroke="#e11d48" stroke-width="2.5" rx="8" />
    <rect width="260" height="44" fill="#e11d48" rx="8" />
    <rect width="260" height="10" y="34" fill="#e11d48" />
    <text x="130" y="28" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x1F6A8; THE GEOLOCATION GATE</text>
    <g transform="translate(16, 62)" font-family="Segoe UI, sans-serif" font-size="13" fill="#334155">
      <text y="18" font-weight="bold" fill="#9f1239">&bull; The Bottleneck:</text>
      <text y="36" font-size="12" fill="#64748b">GPS coordinates masked</text>
      <text y="54" font-size="12" fill="#64748b">for participant safety.</text>
      <text y="82" font-weight="bold" fill="#9f1239">&bull; Masked Coordinates:</text>
      <text y="100" font-size="12" font-weight="bold" fill="#b91c1c">&#x2717; Cannot link to satellite data!</text>
      <text y="128" font-weight="bold" fill="#9f1239">&bull; The Solution Paths:</text>
      <text y="146" font-size="12" fill="#059669">1. Public spatial packages</text>
      <text y="164" font-size="12" fill="#059669">2. Formal author linkages</text>
      <rect y="176" width="228" height="28" fill="#ffffff" stroke="#f43f5e" rx="4" />
      <text x="114" y="195" font-size="11.5" font-weight="bold" fill="#e11d48" text-anchor="middle">Current Decisive Hurdle</text>
    </g>
  </g>

  <!-- Downward Join to Context Grid (Full Width Card, no text overflow) -->
  <g transform="translate(35, 390)" filter="url(#shadow)">
    <rect width="770" height="155" fill="#ffffff" stroke="#059669" stroke-width="2.5" rx="8" />
    <text x="385" y="32" font-family="Segoe UI, sans-serif" font-size="17" font-weight="bold" fill="#065f46" text-anchor="middle">&darr; Spatial Join: Anchoring Treatment Estimators into Context Grids &darr;</text>
    
    <g transform="translate(30, 56)" font-family="Segoe UI, sans-serif" font-size="14" fill="#334155">
      <text y="18">&bull; With unmasked cluster coordinates, each trial site joins with local <tspan font-weight="bold" fill="#0f172a">CHIRPS rainfall, ACLED conflict, and WFP prices</tspan>.</text>
      <text y="44">&bull; Evaluates how local context modifies experimental impact across multiple trials.</text>
      <rect y="60" width="710" height="30" fill="#ecfdf5" stroke="#a7f3d0" rx="4" />
      <text x="355" y="80" font-weight="bold" fill="#047857" text-anchor="middle">Pre-requisite for Causal Transportability Modeling &amp; Context-Informed Extrapolation</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 12: Causal DAG with Conflict Break (No black fill, no overlap, clear break)
# ==============================================================================
svg_12 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 590" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="590" fill="#f8fafc" rx="12" />
  <text x="420" y="42" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Structural Breaks: Causal Transmission in Peace vs. War</text>
  <text x="420" y="70" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Why Standard Covariate Reweighting Fails When Conflict Collapses Transmission Mechanisms</text>

  <!-- TOP PANEL: Peaceful Setting (Mechanism Holds) -->
  <g transform="translate(45, 95)" filter="url(#shadow)">
    <rect width="750" height="190" fill="#ffffff" stroke="#86efac" stroke-width="2" rx="8" />
    <rect width="750" height="34" fill="#ecfdf5" rx="8" />
    <rect width="750" height="10" y="24" fill="#ecfdf5" />
    <text x="25" y="24" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#065f46">&#x2713; Peaceful Disaster Setting (Unstated Security Assumptions Hold)</text>
    
    <!-- DAG Nodes -->
    <g transform="translate(30, 65)">
      <!-- Node 1 -->
      <rect width="115" height="60" fill="#f8fafc" stroke="#64748b" rx="6" />
      <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a" text-anchor="middle">Drought</text>
      <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a" text-anchor="middle">Shock</text>
      
      <line x1="115" y1="30" x2="150" y2="30" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 2 -->
      <g transform="translate(155, 0)">
        <rect width="115" height="60" fill="#ecfdf5" stroke="#059669" stroke-width="2" rx="6" />
        <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46" text-anchor="middle">Emergency</text>
        <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46" text-anchor="middle">Cash Transfer</text>
      </g>
      
      <line x1="270" y1="30" x2="305" y2="30" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 3 -->
      <g transform="translate(310, 0)">
        <rect width="115" height="60" fill="#ecfdf5" stroke="#059669" rx="6" />
        <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46" text-anchor="middle">Household</text>
        <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46" text-anchor="middle">Liquidity</text>
      </g>
      
      <line x1="425" y1="30" x2="460" y2="30" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 4 -->
      <g transform="translate(465, 0)">
        <rect width="115" height="60" fill="#ecfdf5" stroke="#059669" rx="6" />
        <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46" text-anchor="middle">Market Food</text>
        <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#065f46" text-anchor="middle">Purchase</text>
      </g>
      
      <line x1="580" y1="30" x2="615" y2="30" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />
      
      <!-- Node 5 -->
      <g transform="translate(620, 0)">
        <rect width="70" height="60" fill="#ecfdf5" stroke="#059669" stroke-width="2" rx="6" />
        <text x="35" y="26" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#065f46" text-anchor="middle">Welfare</text>
        <text x="35" y="44" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#047857" text-anchor="middle">&#x2713; Survives</text>
      </g>
    </g>
    <text x="375" y="160" font-family="Segoe UI, sans-serif" font-size="13" fill="#047857" text-anchor="middle">Assumption holds: Open trade routes, competitive merchants &rarr; Elastic food supply smoothly absorbs cash.</text>
  </g>

  <!-- BOTTOM PANEL: Conflict Setting (Structural Break) -->
  <g transform="translate(45, 305)" filter="url(#shadow)">
    <rect width="750" height="260" fill="#ffffff" stroke="#fca5a5" stroke-width="2.5" rx="8" />
    <rect width="750" height="34" fill="#fee2e2" rx="8" />
    <rect width="750" height="10" y="24" fill="#fee2e2" />
    <text x="25" y="24" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#991b1b">&#x26A0; Armed Conflict Setting: The Structural Mechanism Break</text>
    
    <!-- DAG Nodes with Break (Positioned down so obstacle box doesn't touch title) -->
    <g transform="translate(30, 85)">
      <!-- Node 1 -->
      <rect width="115" height="60" fill="#f8fafc" stroke="#64748b" rx="6" />
      <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a" text-anchor="middle">Drought +</text>
      <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f172a" text-anchor="middle">Insurgency</text>
      
      <line x1="115" y1="30" x2="150" y2="30" stroke="#b91c1c" stroke-width="2.5" marker-end="url(#arrow-red)" />
      
      <!-- Node 2 -->
      <g transform="translate(155, 0)">
        <rect width="115" height="60" fill="#eff6ff" stroke="#3b82f6" rx="6" />
        <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#1e40af" text-anchor="middle">Emergency</text>
        <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#1e40af" text-anchor="middle">Cash Transfer</text>
      </g>
      
      <line x1="270" y1="30" x2="305" y2="30" stroke="#b91c1c" stroke-width="2.5" marker-end="url(#arrow-red)" />
      
      <!-- Node 3 -->
      <g transform="translate(310, 0)">
        <rect width="115" height="60" fill="#eff6ff" stroke="#3b82f6" rx="6" />
        <text x="57" y="26" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#1e40af" text-anchor="middle">Household</text>
        <text x="57" y="44" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#1e40af" text-anchor="middle">Liquidity</text>
      </g>
      
      <!-- Obstacle Box positioned cleanly above break, well below title -->
      <g transform="translate(370, -42)" filter="url(#glow-red)">
        <rect width="210" height="34" fill="#fee2e2" stroke="#ef4444" stroke-width="1.8" rx="6" />
        <text x="105" y="22" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#b91c1c" text-anchor="middle">&#x26D4; Checkpoint Blockade / Extortion</text>
      </g>
      <line x1="475" y1="-8" x2="475" y2="10" stroke="#dc2626" stroke-width="2" stroke-dasharray="3,3" />

      <!-- CLEAR BREAK BADGE (Replaced ambiguous blue X) -->
      <g transform="translate(435, 8)">
        <rect width="80" height="44" fill="#dc2626" stroke="#ffffff" stroke-width="2" rx="6" filter="url(#glow-red)" />
        <text x="40" y="20" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#ffffff" text-anchor="middle">BREAK IN</text>
        <text x="40" y="34" font-family="Segoe UI, sans-serif" font-size="10.5" font-weight="bold" fill="#ffffff" text-anchor="middle">MECHANISM</text>
      </g>
      
      <!-- Severed Node 4 -->
      <g transform="translate(525, 0)">
        <rect width="105" height="60" fill="#f8fafc" stroke="#cbd5e1" stroke-dasharray="4,4" rx="6" />
        <text x="52" y="26" font-family="Segoe UI, sans-serif" font-size="12" fill="#94a3b8" text-anchor="middle">Market Food</text>
        <text x="52" y="44" font-family="Segoe UI, sans-serif" font-size="12" fill="#94a3b8" text-anchor="middle">Purchase</text>
      </g>
      
      <!-- Failure Outflow Path (Added fill="none" to eliminate black artifact!) -->
      <path d="M 367 60 Q 367 85 450 85 L 635 85" stroke="#dc2626" stroke-width="2.5" marker-end="url(#arrow-red)" fill="none" />
      
      <!-- Bad Outcome Node -->
      <g transform="translate(640, 58)">
        <rect width="85" height="52" fill="#fee2e2" stroke="#ef4444" stroke-width="2" rx="6" />
        <text x="42" y="22" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#b91c1c" text-anchor="middle">Hyper-Local</text>
        <text x="42" y="38" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#b91c1c" text-anchor="middle">Price Spike</text>
      </g>
    </g>
    
    <text x="375" y="220" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#b91c1c" text-anchor="middle">The Operational Takeaway: When the DAG signals market supply breakdown, cash transfers fail.</text>
    <text x="375" y="240" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#475569" text-anchor="middle">The planner must route around the break by delivering physical food aid or opening humanitarian corridors first.</text>
  </g>
</svg>
"""

# ==============================================================================
# Slide 13: Methodological Toolkit (Light bottom box, dark text)
# ==============================================================================
svg_13 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 580" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="580" fill="#f8fafc" rx="12" />
  <text x="420" y="42" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">The Methodological Toolkit: Estimating Impact in Novel Sites</text>
  <text x="420" y="70" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">A Modular Set of Complementary Econometric &amp; Machine Learning Engines</text>

  <!-- 3 Engine Columns -->
  <!-- Engine 1: Bayesian Hierarchical -->
  <g transform="translate(35, 100)" filter="url(#shadow)">
    <rect width="235" height="260" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="235" height="38" fill="#1e3a8a" rx="8" />
    <rect width="235" height="10" y="28" fill="#1e3a8a" />
    <text x="117" y="25" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">1. Bayesian Hierarchical</text>
    
    <g transform="translate(16, 56)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Prior Construction:</text>
      <text y="36">Empirical treatment effects</text>
      <text y="54">from historical trials (Meager '19)</text>
      
      <text y="88" font-weight="bold" fill="#0f172a">&bull; Context Updating:</text>
      <text y="106">Shifts prior distribution via</text>
      <text y="124">observed target features (&Delta;X)</text>
      
      <rect y="146" width="202" height="48" fill="#eff6ff" rx="4" />
      <text x="101" y="168" font-size="11.5" font-weight="bold" fill="#1e40af" text-anchor="middle">Full Posterior Distribution</text>
      <text x="101" y="186" font-size="11" fill="#1e40af" text-anchor="middle">Generates intuitive credible bands</text>
    </g>
  </g>

  <!-- Engine 2: Synthetic Controls -->
  <g transform="translate(302, 100)" filter="url(#shadow)">
    <rect width="235" height="260" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="235" height="38" fill="#065f46" rx="8" />
    <rect width="235" height="10" y="28" fill="#065f46" />
    <text x="117" y="25" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">2. Synthetic Donor Pools</text>
    
    <g transform="translate(16, 56)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Multi-Trial Weighting:</text>
      <text y="36">Treats related trials as</text>
      <text y="54">synthetic donor pool</text>
      
      <text y="88" font-weight="bold" fill="#0f172a">&bull; Similarity Distance:</text>
      <text y="106">Weights assigned by spatial</text>
      <text y="124">&amp; institutional proximity</text>
      
      <rect y="146" width="202" height="48" fill="#ecfdf5" rx="4" />
      <text x="101" y="168" font-size="11.5" font-weight="bold" fill="#047857" text-anchor="middle">Synthetic Counterfactual</text>
      <text x="101" y="186" font-size="11" fill="#047857" text-anchor="middle">Constructs target comparison site</text>
    </g>
  </g>

  <!-- Engine 3: Causal Neural Networks -->
  <g transform="translate(570, 100)" filter="url(#shadow)">
    <rect width="235" height="260" fill="#ffffff" stroke="#cbd5e1" rx="8" />
    <rect width="235" height="38" fill="#4338ca" rx="8" />
    <rect width="235" height="10" y="28" fill="#4338ca" />
    <text x="117" y="25" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff" text-anchor="middle">3. Causal Neural Nets</text>
    
    <g transform="translate(16, 56)" font-family="Segoe UI, sans-serif" font-size="13" fill="#475569">
      <text y="18" font-weight="bold" fill="#0f172a">&bull; Neural DAG Models:</text>
      <text y="36">Learns representations under</text>
      <text y="54">graph structural constraints</text>
      
      <text y="88" font-weight="bold" fill="#0f172a">&bull; High-Dimensional Data:</text>
      <text y="106">Ingests non-linear satellite</text>
      <text y="124">&amp; conflict interactions (DML)</text>
      
      <rect y="146" width="202" height="48" fill="#eef2ff" rx="4" />
      <text x="101" y="168" font-size="11.5" font-weight="bold" fill="#4338ca" text-anchor="middle">Non-Linear Representation</text>
      <text x="101" y="186" font-size="11" fill="#4338ca" text-anchor="middle">Resolves multi-modal complexity</text>
    </g>
  </g>

  <!-- Convergence Arrows -->
  <line x1="150" y1="365" x2="310" y2="410" stroke="#1e3a8a" stroke-width="2.5" marker-end="url(#arrow-blue)" />
  <line x1="420" y1="365" x2="420" y2="405" stroke="#059669" stroke-width="2.5" marker-end="url(#arrow-emerald)" />
  <line x1="690" y1="365" x2="530" y2="410" stroke="#4338ca" stroke-width="2.5" marker-end="url(#arrow)" />

  <!-- Bottom Result Box (LIGHT BACKGROUND, DARK TEXT) -->
  <g transform="translate(35, 415)" filter="url(#shadow)">
    <rect width="770" height="145" fill="#f8fafc" stroke="#2563eb" stroke-width="2.5" rx="10" />
    <rect width="770" height="36" fill="#dbeafe" rx="10" />
    <rect width="770" height="10" y="26" fill="#dbeafe" />
    <text x="385" y="25" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#1e3a8a" text-anchor="middle">&#x2699; Unified Deliverable: Probabilistic Impact Profiles</text>
    <g transform="translate(25, 54)" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#1e293b">
      <text y="18">&bull; Rather than forcing a single brittle point estimator, the toolkit outputs an <tspan fill="#0f172a" font-weight="bold">empirical distribution of predicted impact</tspan>.</text>
      <text y="42">&bull; Provides the emergency planner with realistic median estimates accompanied by honest credible bounds.</text>
      <rect y="56" width="720" height="26" fill="#eff6ff" stroke="#bfdbfe" rx="4" />
      <text x="360" y="74" font-weight="bold" fill="#1d4ed8" text-anchor="middle">Empowering the Simulation Response Exercise with Honest Uncertainty Quantification</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 14: Simulation Response Dashboard Mockup (With Somalia Admin-1 Map, No Arcs)
# ==============================================================================
svg_14 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 590" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="860" height="590" fill="#0f172a" rx="12" />
  
  <!-- Dashboard Top Bar -->
  <rect x="0" y="0" width="860" height="48" fill="#1e293b" rx="12" />
  <rect x="0" y="38" width="860" height="10" fill="#1e293b" />
  <text x="25" y="30" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#38bdf8">&#x1F6E1; Crisis Response Simulator &bull; Decision Support Tool</text>
  <rect x="680" y="12" width="155" height="26" fill="#059669" rx="12" />
  <text x="757" y="29" font-family="Segoe UI, sans-serif" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x25CF; LIVE CONTEXT FEED</text>

  <!-- Left Column: Location & Somalia Admin-1 Mockup Map -->
  <g transform="translate(25, 65)">
    <rect width="330" height="495" fill="#1e293b" rx="8" />
    <text x="18" y="28" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff">1. Target Location &amp; Spatial Risk Map</text>
    
    <rect x="18" y="42" width="294" height="34" fill="#0f172a" stroke="#334155" rx="4" />
    <text x="30" y="65" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#38bdf8">&#x1F4CD; Somalia &ndash; Baidoa District (Bay)</text>

    <!-- Stylized Somalia Admin-1 Boundaries Map -->
    <g transform="translate(18, 88)">
      <rect width="294" height="185" fill="#090d16" stroke="#334155" rx="6" />
      <text x="12" y="20" font-family="Segoe UI, sans-serif" font-size="11" font-weight="bold" fill="#94a3b8">Admin-1 Need Classification Map</text>
      
      <!-- Vector polygons representing Somali regions -->
      <!-- Somaliland / Northwest -->
      <polygon points="40,40 120,35 150,55 110,75 50,70" fill="#1e293b" stroke="#475569" stroke-width="1.2" />
      <text x="75" y="55" font-family="Segoe UI, sans-serif" font-size="9" fill="#94a3b8">W. Galbeed</text>

      <!-- Puntland / Northeast -->
      <polygon points="120,35 220,40 250,70 190,90 150,55" fill="#1e293b" stroke="#475569" stroke-width="1.2" />
      <text x="180" y="65" font-family="Segoe UI, sans-serif" font-size="9" fill="#94a3b8">Bari / Nugaal</text>

      <!-- Central: Mudug / Galguduud -->
      <polygon points="110,75 190,90 170,120 120,105" fill="#451a03" stroke="#f59e0b" stroke-width="1.2" />
      <text x="140" y="105" font-family="Segoe UI, sans-serif" font-size="9" fill="#fde68a">Mudug</text>

      <!-- South-Central: Hiran / Bakool -->
      <polygon points="120,105 170,120 150,145 95,125" fill="#78350f" stroke="#f59e0b" stroke-width="1.2" />
      <text x="120" y="130" font-family="Segoe UI, sans-serif" font-size="9" fill="#fde68a">Bakool</text>

      <!-- Target Region: BAY (Baidoa) - Highlighted in Red IPC 4 -->
      <polygon points="95,125 150,145 130,175 75,150" fill="#7f1d1d" stroke="#ef4444" stroke-width="2.5" />
      <!-- Target Marker -->
      <circle cx="112" cy="150" r="6" fill="#ef4444" stroke="#ffffff" stroke-width="2" />
      <rect x="125" y="140" width="130" height="24" fill="#0f172a" stroke="#ef4444" rx="4" />
      <text x="130" y="156" font-family="Segoe UI, sans-serif" font-size="10" font-weight="bold" fill="#fca5a5">&#x26A0; Baidoa (IPC 4 Drought)</text>

      <!-- Lower Shabelle & Banadir -->
      <polygon points="150,145 190,135 170,165 130,175" fill="#78350f" stroke="#f59e0b" stroke-width="1.2" />
      <text x="155" y="160" font-family="Segoe UI, sans-serif" font-size="8" fill="#fde68a">L. Shabelle</text>

      <!-- Juba regions -->
      <polygon points="75,150 130,175 110,182 50,165" fill="#1e293b" stroke="#475569" stroke-width="1.2" />

      <!-- Map Legend -->
      <g transform="translate(12, 168)" font-family="Segoe UI, sans-serif" font-size="8.5" fill="#cbd5e1">
        <rect width="10" height="8" fill="#1e293b" /> <text x="14" y="8">Stress</text>
        <rect x="60" width="10" height="8" fill="#78350f" /> <text x="74" y="8">Crisis</text>
        <rect x="120" width="10" height="8" fill="#7f1d1d" /> <text x="134" y="8">Emergency (Target)</text>
      </g>
    </g>
    
    <text x="18" y="295" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#94a3b8">Active Shocks (Fused):</text>
    <g transform="translate(18, 308)" font-family="Segoe UI, sans-serif" font-size="12" fill="#cbd5e1">
      <rect width="294" height="24" fill="#450a0a" rx="4" />
      <text x="10" y="17" fill="#fca5a5">&#x26A0; Rainfall: -2.4&sigma; (Extreme Drought)</text>
      
      <rect y="30" width="294" height="24" fill="#450a0a" rx="4" />
      <text x="10" y="47" fill="#fca5a5">&#x26A0; Conflict: High (Al-Shabaab Blockade)</text>
      
      <rect y="60" width="294" height="24" fill="#78350f" rx="4" />
      <text x="10" y="77" fill="#fde68a">&#x26A0; Market: Grain Price +45% YoY</text>
    </g>

    <line x1="18" y1="405" x2="312" y2="405" stroke="#334155" />
    
    <g transform="translate(18, 418)">
      <text y="14" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff">Budget Constraint:</text>
      <text x="150" y="14" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#34d399">$5,000,000 USD</text>
    </g>
    
    <rect x="18" y="445" width="294" height="38" fill="#2563eb" rx="6" />
    <text x="165" y="469" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#ffffff" text-anchor="middle">RUN SIMULATION &rarr;</text>
  </g>

  <!-- Right Column: Simulation Comparison Options (No Arc Lines) -->
  <g transform="translate(375, 65)">
    <rect width="460" height="495" fill="#1e293b" rx="8" />
    <text x="24" y="28" font-family="Segoe UI, sans-serif" font-size="15" font-weight="bold" fill="#ffffff">2. Simulated Intervention Options (Predicted Impact &amp; Variance)</text>
    
    <!-- Option A: Pure Cash -->
    <g transform="translate(20, 45)">
      <rect width="420" height="125" fill="#0f172a" stroke="#334155" rx="8" />
      <text x="16" y="26" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff">Option A: Unconditional Mobile Cash ($5M)</text>
      <text x="16" y="50" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#94a3b8">Predicted Welfare Gain: <tspan fill="#f59e0b" font-weight="bold">+0.18 SD</tspan> &bull; Beneficiary reach: 110,000</text>
      <text x="16" y="74" font-family="Segoe UI, sans-serif" font-size="12" fill="#fca5a5">&bull; High risk: local merchant food stocks depleted under siege.</text>
      <text x="16" y="94" font-family="Segoe UI, sans-serif" font-size="12" fill="#fca5a5">&bull; Inelastic supply triggers rapid localized food price inflation.</text>
      <rect x="310" y="14" width="95" height="26" fill="#7f1d1d" rx="4" />
      <text x="357" y="31" font-family="Segoe UI, sans-serif" font-size="11.5" font-weight="bold" fill="#fca5a5" text-anchor="middle">HIGH RISK</text>
    </g>

    <!-- Option B: In-Kind Food Aid -->
    <g transform="translate(20, 185)">
      <rect width="420" height="125" fill="#0f172a" stroke="#334155" rx="8" />
      <text x="16" y="26" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff">Option B: Physical In-Kind Food Convoys ($5M)</text>
      <text x="16" y="50" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#94a3b8">Predicted Welfare Gain: <tspan fill="#38bdf8" font-weight="bold">+0.26 SD</tspan> &bull; Beneficiary reach: 64,000</text>
      <text x="16" y="74" font-family="Segoe UI, sans-serif" font-size="12" fill="#93c5fd">&bull; Immune to local market inflation; supplies physical grain.</text>
      <text x="16" y="94" font-family="Segoe UI, sans-serif" font-size="12" fill="#93c5fd">&bull; Severe logistics friction; 30% overhead and armed convoy escort risks.</text>
      <rect x="310" y="14" width="95" height="26" fill="#1e3a8a" rx="4" />
      <text x="357" y="31" font-family="Segoe UI, sans-serif" font-size="11.5" font-weight="bold" fill="#93c5fd" text-anchor="middle">MODERATE</text>
    </g>

    <!-- Option C: Layered Portfolio (Recommended) -->
    <g transform="translate(20, 325)">
      <rect width="420" height="150" fill="#064e3b" stroke="#059669" stroke-width="2.5" rx="8" />
      <text x="16" y="26" font-family="Segoe UI, sans-serif" font-size="14.5" font-weight="bold" fill="#ffffff">&#x2605; Option C: Layered Mix (60% Food Aid + 40% Targeted Cash)</text>
      <text x="16" y="52" font-family="Segoe UI, sans-serif" font-size="13" fill="#a7f3d0">Predicted Welfare Gain: <tspan fill="#34d399" font-weight="bold">+0.38 SD [95% CI: 0.28, 0.46]</tspan></text>
      <text x="16" y="76" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#d1fae5">&bull; Food convoys break market supply inelasticity and anchor local prices.</text>
      <text x="16" y="96" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#d1fae5">&bull; Targeted cash allows families to buy non-grain essentials and medical care.</text>
      <text x="16" y="116" font-family="Segoe UI, sans-serif" font-size="12.5" fill="#d1fae5">&bull; Maximizes survival rates while sustaining local market merchants.</text>
      <rect x="290" y="12" width="115" height="26" fill="#059669" rx="4" />
      <text x="347" y="29" font-family="Segoe UI, sans-serif" font-size="11.5" font-weight="bold" fill="#ffffff" text-anchor="middle">&#x2713; RECOMMENDED</text>
    </g>
  </g>
</svg>
"""

# ==============================================================================
# Slide 15: Research Roadmap & Milestone Flow (Spring 2027, Summer 2027, Fall 2027)
# ==============================================================================
svg_15 = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 840 560" width="100%" height="100%">
{COMMON_DEFS}
  <rect width="840" height="560" fill="#f8fafc" rx="12" />
  <text x="420" y="44" font-family="Segoe UI, sans-serif" font-size="24" font-weight="bold" fill="#0f172a" text-anchor="middle">Research Frontiers &amp; Year 1 Milestone Roadmap</text>
  <text x="420" y="72" font-family="Segoe UI, sans-serif" font-size="15" fill="#475569" text-anchor="middle">Advancing from Technical Proof-of-Concept to Working Paper &amp; Seminar Presentation</text>

  <!-- Horizontal Timeline Bar -->
  <line x1="70" y1="170" x2="770" y2="170" stroke="#cbd5e1" stroke-width="4" />
  
  <!-- Milestone 1: Nov 2026 (Now) -->
  <g transform="translate(90, 125)">
    <circle cx="20" cy="45" r="18" fill="#2563eb" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="51" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">1</text>
    <text x="20" y="12" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#2563eb" text-anchor="middle">Nov 2026 (Now)</text>
    
    <rect x="-60" y="80" width="160" height="125" fill="#ffffff" stroke="#93c5fd" stroke-width="1.8" rx="8" filter="url(#shadow)" />
    <text x="20" y="104" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#1e3a8a" text-anchor="middle">Foundations</text>
    <text x="-48" y="126" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; Case study replication</text>
    <text x="-48" y="146" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; reprokit v0.4.0 live</text>
    <text x="-48" y="166" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; SusDev Brownbag</text>
    <text x="-48" y="186" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; Geolocation data audit</text>
  </g>

  <!-- Milestone 2: Spring 2027 -->
  <g transform="translate(290, 125)">
    <circle cx="20" cy="45" r="18" fill="#0f766e" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="51" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">2</text>
    <text x="20" y="12" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#0f766e" text-anchor="middle">Spring 2027</text>
    
    <rect x="-60" y="80" width="160" height="125" fill="#ffffff" stroke="#99f6e4" stroke-width="1.8" rx="8" filter="url(#shadow)" />
    <text x="20" y="104" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#0f766e" text-anchor="middle">Evidence Scaling</text>
    <text x="-48" y="126" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; 2x2 matrix synthesis</text>
    <text x="-48" y="146" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; OpenAlex API sweep</text>
    <text x="-48" y="166" font-family="Segoe UI, sans-serif" font-size="12" fill="#065f46" font-weight="bold">&bull; SusDev Seminar Talk</text>
    <text x="-48" y="186" font-family="Segoe UI, sans-serif" font-size="12" fill="#065f46" font-weight="bold">&bull; Working Paper 1</text>
  </g>

  <!-- Milestone 3: Summer 2027 -->
  <g transform="translate(490, 125)">
    <circle cx="20" cy="45" r="18" fill="#4338ca" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="51" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">3</text>
    <text x="20" y="12" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#4338ca" text-anchor="middle">Summer 2027</text>
    
    <rect x="-60" y="80" width="160" height="125" fill="#ffffff" stroke="#c7d2fe" stroke-width="1.8" rx="8" filter="url(#shadow)" />
    <text x="20" y="104" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#4338ca" text-anchor="middle">Transport Models</text>
    <text x="-48" y="126" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; Formal transport model</text>
    <text x="-48" y="146" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; Covariate shift checks</text>
    <text x="-48" y="166" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; DAG break formalization</text>
    <text x="-48" y="186" font-family="Segoe UI, sans-serif" font-size="12" fill="#475569">&bull; Multi-trial weighting</text>
  </g>

  <!-- Milestone 4: Fall 2027 -->
  <g transform="translate(690, 125)">
    <circle cx="20" cy="45" r="18" fill="#047857" stroke="#ffffff" stroke-width="3" />
    <text x="20" y="51" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">4</text>
    <text x="20" y="12" font-family="Segoe UI, sans-serif" font-size="14" font-weight="bold" fill="#047857" text-anchor="middle">Fall 2027</text>
    
    <rect x="-60" y="80" width="160" height="125" fill="#ecfdf5" stroke="#047857" stroke-width="2.5" rx="8" filter="url(#shadow)" />
    <text x="20" y="104" font-family="Segoe UI, sans-serif" font-size="13" font-weight="bold" fill="#047857" text-anchor="middle">Applied Testbed</text>
    <text x="-48" y="126" font-family="Segoe UI, sans-serif" font-size="12" fill="#065f46">&bull; Simulation exercise</text>
    <text x="-48" y="146" font-family="Segoe UI, sans-serif" font-size="12" fill="#065f46">&bull; Field crisis evaluation</text>
    <text x="-48" y="166" font-family="Segoe UI, sans-serif" font-size="12" fill="#065f46">&bull; Public open source</text>
    <text x="-48" y="186" font-family="Segoe UI, sans-serif" font-size="12" fill="#065f46">&bull; Decision tool release</text>
  </g>

  <!-- Bottom Core Frontiers Card -->
  <g transform="translate(45, 345)" filter="url(#shadow)">
    <rect width="750" height="190" fill="#ffffff" stroke="#cbd5e1" rx="10" />
    <text x="375" y="32" font-family="Segoe UI, sans-serif" font-size="16" font-weight="bold" fill="#0f172a" text-anchor="middle">Core Theoretical &amp; Empirical Frontiers Ahead</text>
    
    <g transform="translate(30, 54)" font-family="Segoe UI, sans-serif" font-size="13.5" fill="#334155">
      <circle cx="6" cy="12" r="5" fill="#2563eb" />
      <text x="24" y="17" font-weight="bold" fill="#0f172a">Intervention Combining &amp; Layering:</text>
      <text x="24" y="36" fill="#64748b">Modeling positive complementarities when multiple interventions (cash + food + insurance) are deployed together.</text>

      <circle cx="6" cy="62" r="5" fill="#0f766e" />
      <text x="24" y="67" font-weight="bold" fill="#0f172a">Displacement &amp; Human Mobility Dynamics:</text>
      <text x="24" y="86" fill="#64748b">Treating forced migration not as an error term, but as an endogenous outcome (evacuation vs. entrapment under siege).</text>

      <circle cx="6" cy="112" r="5" fill="#4338ca" />
      <text x="24" y="117" font-weight="bold" fill="#0f172a">Subnational Spatial Resolution Limits:</text>
      <text x="24" y="136" fill="#64748b">Testing how finely conflict point events and displacement vectors can be resolved below Admin-2 to match trial clusters.</text>
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
