---
name: brisc
description: >-
  High-performance scRNA-seq processing with brisc for large datasets (>400k cells, up to 20M).
  Use when running QC, normalization, HVG selection, PCA, k-NN graph, Harmony batch integration,
  Leiden clustering, UMAP/PaCMAP embedding, label transfer, marker gene detection, or pseudobulk
  differential expression on datasets too large or too slow for Scanpy.
tool_type: python
primary_tool: brisc
---

## Version Compatibility

Reference examples tested with: brisc 0.x+.

Before using code patterns, verify installed versions match. If versions differ:
- Python: `pip show brisc` then `help(brisc.SingleCell.method)` to check signatures
- CLI: `python -c "import brisc; print(brisc.__version__)"`

If code throws AttributeError or TypeError, introspect the installed package and adapt
the example to match the actual API rather than retrying.

# brisc: Large-Scale scRNA-seq Processing

**"Process my large scRNA-seq dataset"** → Use brisc for any dataset that is slow or
memory-constrained in Scanpy. Achieves identical results to Scanpy on single-thread but
scales to 20M cells with ~2× lower peak memory via multi-threaded, BLAS-accelerated
algorithms and Polars DataFrames for metadata.

## Governing Principle

brisc guarantees floating-point identical results regardless of thread count (`match_parallel=True`
on PCA). This is rare and valuable: it means running with `-1` (all cores) does not trade
reproducibility for speed. The exception is `umap(hogwild=True)`, which is faster but loses
reproducibility — prefer `pacmap()` or `localmap()` at scale instead.

obs/var metadata are Polars DataFrames, not pandas. Filter and select with Polars expressions;
convert with `.to_pandas()` only when a downstream tool requires it.

Method calls return `self`, enabling a method-chaining pattern that expresses the full
pipeline as a single expression. Each step is a transformation of the same object, not a
copy — plan memory accordingly.

## Installation

**Conda (recommended)** — auto-configures MKL BLAS, which outperforms OpenBLAS at high
core counts (OpenBLAS caps threading at 64 cores):
```bash
conda install -c conda-forge brisc
```

**Pip** — uses the system BLAS; verify it is MKL on x86 if running >64 cores:
```bash
pip install brisc
```

**Verify BLAS backend** (x86 only; MKL is required for full multi-threading benefit):
```python
import numpy as np
np.__config__.blas_opt_info   # should show MKL, not OpenBLAS
```

**R packages** (only needed for pseudobulk DE or Seurat/.rds I/O):
```r
install.packages('arrow')
BiocManager::install('limma')
install.packages('Seurat')         # for .h5Seurat read/write
BiocManager::install('SingleCellExperiment')
```

## Full Pipeline

```python
from brisc import SingleCell

sc = SingleCell(
    'data.h5ad',
    obs_columns=['sample', 'donor', 'cell_type'],   # load only needed columns — faster at scale
    num_threads=-1                                  # -1 = all available cores
)

sc = (sc
    .qc(max_mito_fraction=0.05, min_genes=100, allow_float=False)
    .hvg(n_top_genes=2000, batch_column='donor')
    .normalize(method='log1pPF', inplace=True)      # inplace avoids a matrix copy
    .pca(n_comps=50, match_parallel=True)
    .neighbors(k=20)
    .shared_neighbors()
    .harmonize(batch_column='donor')               # remove if no batch correction needed
    .cluster(resolution=[0.25, 0.5, 1.0, 1.5, 2.0])
    .pacmap()                                       # faster than umap() at >400k cells
)

markers = sc.find_markers(groupby='leiden_1.0')
sc.save('processed.h5ad', overwrite=True)
```

## Large-Scale Tips (>400k cells)

| Concern | Recommendation |
|---------|----------------|
| I/O speed | Pass `obs_columns` and `var_columns` to skip loading unused metadata |
| Memory peak | `normalize(inplace=True)` modifies X in place; avoids a full matrix copy |
| Embedding speed | Prefer `pacmap()` or `localmap()` over `umap()`; both are faster at scale |
| UMAP when needed | `umap(hogwild=True)` is faster but sacrifices reproducibility |
| Clustering throughput | Pass a list to `cluster(resolution=[...])` — resolutions run in parallel |
| Thread count | Default `-1` (all cores) is correct; override per-step if needed: `pca(num_threads=8)` |
| BLAS at >64 cores | Use conda install to get MKL; OpenBLAS caps at 64 cores silently |
| Seurat format limit | R sparse indices are 32-bit; `.rds`/`.h5Seurat` cannot hold >2,147,483,647 nonzeros — stay with `.h5ad` for very large datasets |
| Metadata-only ops | Pass `X=False` to skip loading the count matrix when only obs/var are needed |

## Per-Method Reference

### `qc()`
```python
sc.qc(
    max_mito_fraction=0.05,   # fraction, not percent
    min_genes=100,
    allow_float=False,        # set True if X is float32 rather than integer counts
    remove_doublets=False,    # cxds co-expression doublet scoring
    subset=False              # False adds Boolean column; True removes cells
)
```
Adds `num_counts`, `num_genes`, `mito_fraction` to `obs`.

### `hvg()`
```python
sc.hvg(
    n_top_genes=2000,
    batch_column='donor'   # batch-aware HVG selection; omit if single batch
)
```

### `normalize()`
```python
sc.normalize(
    method='log1pPF',   # options: 'log1pPF', 'PFlog1pPF', 'logCP10k'
    inplace=True        # strongly preferred at scale to avoid matrix copy
)
```

### `pca()`
```python
sc.pca(
    n_comps=50,
    match_parallel=True,   # ensures identical results at any thread count
    num_threads=-1
)
# Joint PCA across a reference and query dataset:
sc_ref.pca(sc_query)
```

### `neighbors()` and `shared_neighbors()`
```python
sc.neighbors(k=20)        # approximate k-NN graph stored in obsp
sc.shared_neighbors()     # shared nearest neighbor (SNN) graph for Leiden clustering
```

### `harmonize()`
```python
sc.harmonize(batch_column='donor')  # stores result in obsm['harmony']
# Cross-dataset integration:
sc_ref.harmonize(sc_query)
```

### `cluster()`
```python
sc.cluster(resolution=[0.25, 0.5, 1.0, 1.5, 2.0])   # all resolutions run in parallel
# Adds columns e.g. 'leiden_0.25', 'leiden_1.0' to obs
```

### `umap()` / `pacmap()` / `localmap()`
```python
sc.umap()                # reproducible; slow on >400k cells
sc.umap(hogwild=True)    # faster; sacrifices reproducibility
sc.pacmap()              # fast alternative; preferred at scale
sc.localmap()            # another fast alternative
```

### `label_transfer_from()`
```python
sc_query.label_transfer_from(
    sc_ref,
    cell_type_column='cell_type',
    num_neighbors=20,
    next_best=True        # also returns runner-up label and confidence score
)
# Adds 'cell_type_transferred' and 'cell_type_transferred_confidence' to sc_query.obs
```

### `find_markers()`
```python
sc.find_markers(
    groupby='leiden_1.0',
    min_detection_rate=0.25,
    min_fold_change=2,
    pareto=True           # retains Pareto-non-dominated genes (specificity + magnitude)
)
```

## Pseudobulk Differential Expression

Requires R with `limma` and the `ryp` Python-R bridge (installed as brisc dependency).

```python
from brisc import SingleCell, Pseudobulk

pb = sc.pseudobulk(
    sample_column='sample',
    cell_type_column='cell_type'   # sums raw counts per sample × cell type
)

pb = pb.qc(
    condition_column='cytokine',
    min_cells=10,              # minimum cells per sample per cell type
    min_gene_detection=0.8,    # gene must be detected in ≥80% of samples per condition
    max_zero_sd=3              # removes outlier samples >3 SD above mean zero-count genes
)

pb = pb.library_size()         # TMM-normalized library sizes

de = pb.de(
    formula='~ cytokine + donor + log2(num_cells) + log2(library_size)',
    group=True,    # separate mean-variance trend per condition (voomByGroup)
    robust=True    # robust empirical Bayes
)

# de.table: Polars DataFrame with gene, cell_type, logFC, SE, CI, avg expression, P, FDR
print(de.table.head())
de.plot_volcano('CD14 Mono', 'volcano.png')
```

## I/O and Conversion

```python
# Read with partial column loading (faster for large .h5ad or .h5Seurat)
sc = SingleCell('data.h5ad', obs_columns=['sample', 'cell_type'], X=False)   # metadata only
sc = SingleCell('data.h5Seurat', assay='RNA')                                  # Seurat (requires ryp)

# Save
sc.save('out.h5ad', overwrite=True)
sc.save('out.rds')                  # R SingleCellExperiment (requires ryp; 32-bit index limit)

# In-memory conversion
adata = sc.to_scanpy()              # returns AnnData; X is shared, not copied
seurat_obj = sc.to_seurat()        # requires ryp

# Partial reads of a saved file
sc.read_obs()
sc.read_obsm()
```

## Common Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: X must be integer` | Float32 count matrix | Pass `allow_float=True` to `qc()` |
| Threading caps at 64 cores | OpenBLAS installed instead of MKL | Use `conda install -c conda-forge brisc` to get MKL |
| `OverflowError` or index error saving .rds | Matrix has >2,147,483,647 nonzeros (R 32-bit index limit) | Save as `.h5ad` instead; use Seurat format only for smaller datasets |
| `AttributeError` on `sc.harmonize` or `sc.label_transfer_from` | brisc version mismatch | `pip show brisc` and check the changelog at https://github.com/briscverse/brisc |
| Memory spike during normalize | Default makes a copy of X | Pass `inplace=True` to `normalize()` |
| Slow embedding on millions of cells | `umap()` default is single-threaded | Switch to `pacmap()` or `localmap()`; use `umap(hogwild=True)` only if UMAP is required |
| `ryp` import error on DE or Seurat I/O | R packages not configured | Install R `arrow` + `limma`; check `ryp` is installed in the same Python env |
| Volcano or marker result empty | `min_cells` too high in `pb.qc()` | Lower `min_cells` or increase the per-cell-type sample count |

## Related Skills

- bio-single-cell-preprocessing — Scanpy/Seurat QC, ambient removal, normalization (when not using brisc)
- bio-single-cell-batch-integration — Harmony, scVI, and other integration methods
- bio-single-cell-clustering — Leiden clustering, resolution selection, cluster annotation
- bio-single-cell-differential-abundance — compositional analysis across conditions
- bio-single-cell-markers-annotation — marker gene interpretation and cell type assignment

## References

- brisc documentation: https://brisc.run/
- brisc GitHub: https://github.com/briscverse/brisc
- Basic workflow tutorial: https://brisc.run/tutorials/basic_workflow.html
- Integration and label transfer: https://brisc.run/tutorials/integration_and_label_transfer.html
- Differential expression tutorial: https://brisc.run/tutorials/differential_expression.html
- Interoperability: https://brisc.run/tutorials/interoperability.html
