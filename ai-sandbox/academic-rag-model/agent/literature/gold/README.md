# Gold set

`gold_set.yaml` lists about ten papers whose key facts the owner has checked by hand. It holds expected values only
(vocabulary ids, labels, ISO country codes), never quotes or paper text, so it is safe to commit.

```yaml
version: 1
papers:
  - file_id: 0123456789abcdef          # the index card's file_id
    expect:
      countries: [SO]
      study_design: [study_design.panel]        # vocab ids
      data_sources: ["FSNAU", "ACLED"]          # vocab ids, or labels/values (case- and space-insensitive)
      intervention: []
      outcome: []
    notes: ""
```

Score the current records with `python -m agent.literature eval [--gold PATH]`. It prints aggregates as JSON:
micro-averaged facet precision and recall, proposals per record, the card bounce rate, and double-pass agreement.
The file is created in Task 10, once the real vocabularies are loaded and the papers are chosen.
