# Forge File Ownership Policy

- schema: `helm.iconforge.file_ownership_policy.v1`
- status: `pass`
- tracked files classified: `14010`
- unknown tracked files: `0`
- untracked handoff files: `0`

## Classes

| Class | Count | Disposition |
| --- | ---: | --- |
| `generated_tracked` | 9302 | tracked with reproducible/provenance evidence |
| `reference_evidence_tracked` | 4252 | tracked reference-only evidence |
| `review_only_output` | 18 | ignored or archived outside the handoff |
| `source_contract` | 438 | tracked source |

## Rules

- Every Forge worker must claim intended write paths before modifying tracked generated or source-contract files.
- Review-only outputs under pipeline/iconforge/out/ are ignored by Git; summarize them in board evidence or promote them through an explicit generator if they must be tracked.
- Generated tracked artifacts must be reproducible from a named forge module or carry provenance in an adjacent JSON/Markdown report.
- Reference-source assets are comparison/provenance evidence only and must not become canonical Helm artwork without a clean-IP task.
- A handoff must not contain untracked files under Forge-controlled roots; stage intentional files, ignore scratch outputs, or delete them before complete_claim.
