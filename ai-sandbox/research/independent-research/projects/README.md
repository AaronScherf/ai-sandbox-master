# Independent research projects

The [3R revision](../notes/00_overview-and-strategy/Ground%20Truth%20-%20PhD%20Research%20Plan%20-%203R%20Revision.md) and its [operational roadmap](research_projects_plan_fall26%20-%203R%20Revision.md) describe the current research scope. The original Ground Truth memo and `research_projects_plan_fall26.md` are historical baselines. Use the [research-wide potential data sources register](../notes/00_overview-and-strategy/Potential%20Data%20Sources%20-%20Research-Wide%20Register.md) for cross-project source intake. The older [data-sources note](../notes/01_compound-shocks-panel/data-sources/Data%20Sources%20-%20Climate%20Displacement%20Cash%20Conflict.md) is a narrative candidate-source list, not a verified data dictionary or license grant. In particular, its Project 03 chatbot description predates the 3R revision.

| Folder | Current role |
| --- | --- |
| `evidence-map/` | Separate Git repository for Project 01's evidence map (reprokit evidence kind; remote is private for now, URL and commit in `repositories.json`). The narrowed scope is set; detailed search and classification rules await design review. |
| `compound-shocks/` | Temporary holding place for Project 02's literature review |
| `transferability/` | Project 03 disaster-to-conflict transferability evidence review |
| `data-fusion-toolkit/` | Project 04 prospective reusable library; review held until library-kind support exists |
| `systems-dynamics/` | Project 05 scoping review; remains notes until its scope is settled |
| `bangladesh-insurance-replication/` | Separate private Git repository (git-ignored here; URL and commit in `repositories.json`). Study-kind replication of Hill et al. (2019); replication CSV stays local and git-ignored |
| `math_thesis/` | Separate thesis work (Project 06 in the roadmap) |
| `compound-shocks-panel/` | Separate Git repository (git-ignored here; URL and commit in `repositories.json`). The live Project 02 code and data panel for Somalia and Sudan |
| `reprokit/` | Separate Git repository (git-ignored here). The reproducibility framework and project template that `compound-shocks-panel` and `bangladesh-insurance-replication` pin by tag |

Start project-specific data intake in the live `compound-shocks-panel/` repository using its source descriptors and manifests. Keep source downloads and credentials out of Git. Record source versions and checksums before transformation. The review-only folders above await settled scope and suitable reprokit kinds.

This directory is part of the monorepo, not a separate Git repository. Changes follow the repository's worktree and landing procedures.
