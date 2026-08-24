# SEA-AD S3 Buckets and Routing

## Bucket table

| Class | Bucket | Intended use |
|---|---|---|
| Standard prod | `s3://sea-ad-prod-802451596237-us-west-2/` | Frozen/completed non-sensitive datasets and release-ready outputs |
| Standard wg | `s3://sea-ad-wg-802451596237-us-west-2/` | Mutable analyses, scripts, benchmarks, and experimental outputs |
| Sensitive prod | `s3://sea-ad-prod-highly-sensitive-711387118892-us-west-2/` | Production data requiring highly sensitive storage |
| Sensitive wg | `s3://sea-ad-wg-highly-sensitive-711387118892-us-west-2/` | Active analyses requiring highly sensitive storage |
| Sensitive site-data | `s3://sea-ad-site-data-highly-sensitive-711387118892-us-west-2/` | External-site deposits, source data, forms, and imaging |

All buckets are in `us-west-2`.

## Sensitivity rules

- PII must use highly sensitive storage.
- Data and derivatives governed by a DUA requiring highly sensitive storage
  must remain highly sensitive, even if a derivative contains no PII.
- All ADKP data and all ADKP-derived datasets must remain highly sensitive.
- Site deposits currently have only a highly sensitive bucket.
- Never infer that de-identification permits moving data to standard storage.
- If sensitivity or DUA status is unclear, **stop and ask** rather than guessing.

## Routing decision tree

```
Sensitivity or DUA status unclear?
  → Stop and ask.

Governed by a DUA requiring highly sensitive storage?
  Yes → highly sensitive bucket
  No → Is it PII?
    Yes → highly sensitive bucket
    No → Is it ADKP data or an ADKP-derived dataset?
      Yes → highly sensitive bucket
      No → standard bucket

Standard or highly sensitive chosen. Now:
  Frozen/completed output? → prod
  Active analysis?         → wg
  External-site deposit?   → site-data (highly sensitive only)
```

## Legacy buckets (do not recommend as new destinations)

| Bucket | Status |
|---|---|
| `sea-ad-streamlit-802451596237-us-west-2` | In stasis |
| `sea-ad-highly-sensitive-711387118892-us-west-2` | Mixed content; being migrated to the newer prod/wg buckets |

## Examples

### 1 — Non-sensitive completed dataset → standard prod

Dataset: finalized snRNA-seq count matrix; no PII, not ADKP, no DUA restrictions.

Proposed URI (not verified):
```
s3://sea-ad-prod-802451596237-us-west-2/snrna_seq/released/DLPFC/counts_matrix.h5ad
```

Verify with:
```bash
aws s3 ls s3://sea-ad-prod-802451596237-us-west-2/snrna_seq/released/DLPFC/
```

---

### 2 — Active ADKP analysis → sensitive wg

Dataset: intermediate files derived from ADKP data; actively being worked on.

Bucket: `s3://sea-ad-wg-highly-sensitive-711387118892-us-west-2/`  
Highly sensitive buckets require an access-group prefix.

Proposed URI (not verified):
```
s3://sea-ad-wg-highly-sensitive-711387118892-us-west-2/adkp_access/shared_wg_analysis/adkp_benchmarking/clustering/250810/results.h5ad
```

---

### 3 — Personal wg prefix with dotted username

Allen username `jane.doe` → directory component `jane_doe` (dots → underscores).

Proposed URI (not verified):
```
s3://sea-ad-wg-802451596237-us-west-2/individual_analysis/jane_doe/my_project/notebooks/
```

---

### 4 — Unknown DUA status → refuse and ask

Question: "Can I copy this dataset to the standard wg bucket?"

Response: "I can't determine the correct bucket without knowing the DUA status
and whether any ADKP-derived material is present. Please confirm:
(a) Does a DUA govern this data?
(b) Is any ADKP data or ADKP derivative included?
I'll route it once those are clear."

---

### 5 — Read-only listing (credentials required)

All SEA-AD buckets are private; AWS credentials must already be configured in
the user's shell environment (via `aws configure`, `AWS_PROFILE`, an IAM role,
or equivalent). Never suggest `--no-sign-request` for these buckets.

Suggest the command text without embedding credentials, profile names, or tokens:

```bash
aws s3 ls s3://sea-ad-prod-802451596237-us-west-2/snrna_seq/
```

If the command returns an access-denied error, tell the user to verify their
AWS credentials; do not ask them to paste credentials into the conversation.
Never include `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, session tokens,
or `--profile <name>` in a suggested command.
