# Independent research projects

The [3R revision](../notes/00_overview-and-strategy/Ground%20Truth%20-%20PhD%20Research%20Plan%20-%203R%20Revision.md) and its [operational roadmap](research_projects_plan_fall26%20-%203R%20Revision.md) describe the current research scope. The original Ground Truth memo and `research_projects_plan_fall26.md` are historical baselines. Use the [research-wide potential data sources register](../notes/00_overview-and-strategy/Potential%20Data%20Sources%20-%20Research-Wide%20Register.md) for cross-project source intake. The older [data-sources note](../notes/01_compound-shocks-panel/data-sources/Data%20Sources%20-%20Climate%20Displacement%20Cash%20Conflict.md) is a narrative candidate-source list, not a verified data dictionary or license grant. In particular, its Project 03 chatbot description predates the 3R revision.

| Folder | Current role |
| --- | --- |
| `01_evidence_map/` | Evaluation evidence map for anticipatory action, cash, and conflict |
| `02_compound_shocks/` | Somalia exploratory study and prospective fused panel; later Ukraine work remains a separate phase |
| `03_transferability/` | Disaster-to-conflict transferability paper; replaces the chatbot pilot |
| `04_data_fusion_toolkit/` | Prospective reusable data-processing package, developed from validated Project 02 needs |
| `05_systems_dynamics/` | Internal systems-dynamics scoping note |
| `math_thesis/` | Separate thesis work (Project 06 in the roadmap) |
| `compound-shocks-panel/` | Separate Git repository (git-ignored here; URL and commit in `repositories.json`). The live Project 02 code and data panel for Somalia and Sudan. It supersedes the placeholder files in `02_compound_shocks/` |
| `reprokit/` | Separate Git repository (git-ignored here). The reproducibility framework and project template that `compound-shocks-panel` pins by tag |

Start data intake in [`02_compound_shocks/`](02_compound_shocks/README.md). Keep source downloads and credentials out of Git. Record source versions and checksums before transformation. Projects 01, 03, 04, and 05 retain their existing literature reviews; their methods and publication structure should be set when their individual scope is settled.

This directory is part of the monorepo, not a separate Git repository. Changes follow the repository's worktree and landing procedures.
