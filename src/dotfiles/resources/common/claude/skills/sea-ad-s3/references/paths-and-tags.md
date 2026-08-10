# SEA-AD S3 Paths and Tags

## Prefix schemas

### prod

```
[access-group/]                 # highly sensitive buckets only; omit for standard
data-modality/
  raw/ | processed/ | released/
    brain-region/
      files
  metadata/ | manifest
inventory-or-manifest
README
```

### wg

```
[access-group/]                 # highly sensitive buckets only; omit for standard
shared_wg_analysis/
  project/
    analysis/
      version-or-date/
        files
  manifest
individual_analysis/
  allen-username/               # dots replaced with underscores
    project/
      personal-substructure/
02_shared_references/
  organization-or-creator/
    reference-type/
      version-or-identifier/
        files
```

Notes:
- `01_template` is reserved for directory templates; do not use as a data destination.
- Legacy folders are archival — do not route new data there.
- Working-group storage is mutable and must not be treated as authoritative or release-ready.
- Production storage is for frozen/completed outputs, not active analysis.

### site-data

```
site-code/
  data-type/
    YYMMDD/
      files
  donorfile.csv
```

**Known site codes:** `uwa`, `uci`, `stanford`, `uwi`, `wfu`, `nbb`, `kpwhri-act`

## Naming rules

- Prefer lowercase names.
- Avoid spaces and periods; prefer underscores.
- Prefix higher-level dated folders with `YYMMDD_`.
- Fully timestamped names may use `YYMMDD_HHmmss_` or `YYYY-MM-DD_HH-mm-ss`.
- Use descriptive project names and established acronyms.
- Replace periods in Allen usernames with underscores for personal directories
  (e.g. `jane.doe` → `jane_doe`).

## Tag guidance *(WIP — conventions are not fully settled)*

| Context | Required keys | Optional keys |
|---|---|---|
| prod | `manuscript`, `datatype`, `releasestate`, `owner`, `modality` | — |
| wg | `uploader` | `releasestate`, `manuscript` |
| site-data | `source`, `uploader` | — |

General rules:
- Use lowercase keys and values.
- Separate multiple values with `/`.
- Update `manuscript` DOI values when preprints become published manuscripts.

### ⚠️ Known inconsistencies (do not silently resolve)

| Issue | Observed variants | Guidance |
|---|---|---|
| Tag key spelling | Declared as `datatype`; one example uses `data_type` | Preserve the form already in use on existing objects, or ask the user to confirm |
| Naming guidance vs. examples | Guidance says avoid spaces; some conceptual examples contain names like `raw data` | Follow explicit guidance: use underscores |
| `owner` vs. `uploader` | Some examples use `owner=` where the declared key is `uploader` | Ask the user which key their existing objects use before tagging |

When you encounter one of these, do not silently pick a variant. Preserve any
observed convention already in use, or ask the user to verify.
