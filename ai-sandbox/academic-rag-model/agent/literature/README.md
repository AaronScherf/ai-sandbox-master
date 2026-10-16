# agent/literature

Stage 2 of the literature taxonomy: extract one structured, quote-verified study record per converted journal paper.
Records are written to `research/.index/study_records/` (gitignored; they hold verbatim quotes).

```powershell
python -m agent.literature collect --run-id r1            # write cards (no API calls); --double adds a second pass
python -m agent.literature bootstrap r1                   # the contract to give the agent
python -m agent.literature submit r1                      # validate filled cards, write records
python -m agent.literature status
```

Full usage, the record format and the evaluation commands are documented in Task 11 of the plan.
