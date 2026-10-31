# Controlled vocabularies

One YAML file per vocabulary, named `<vocabulary>.yaml`. The ISO country list and gap analysis subregion table live in
`../reference_data/`, outside the vocabulary loader's search directory.

```yaml
vocabulary: intervention        # lower_snake name; file is intervention.yaml
version: 1
provenance: 3ie                 # 3ie | provisional | local
source: "3ie Evidence Gap Map codebook, <document title, date>"
terms:
  - id: intervention.cash_transfer     # must start with "<vocabulary>."
    label: Cash transfer
    parent: intervention.social_protection   # optional, must exist
    definition: "..."
    aliases: [cash transfers, unconditional cash transfer]
    source: local                      # optional; set only for terms added after the file was loaded
```

## Provenance

- `3ie`: taken from the 3ie codebook the owner supplied (literature taxonomy stage 2, Task 10).
- `provisional`: written by us as a placeholder, to be replaced or reconciled.
- `local`: terms accepted from agent proposals (`proposals accept`); each carries `source: local`.

Bump `version` whenever a file changes; every extracted record stores the vocabulary versions it used.

## Licensing

If 3ie's terms forbid committing a machine-readable copy of its lists, keep the real files in an ignored
directory and point the CLI at it with `--vocab-dir`. Do not commit them.

## Reference data

`../reference_data/README.md` describes the country list, subregion table, and country-list generator. Every `*.yaml`
file in this directory is loaded as a vocabulary.
