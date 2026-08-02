# V9 ten-run Git-safe evidence archive

This directory archives the ten original per-run `results.json` files and all small textual evidence found under the completed Validation output root. Each `results.json` was verified against the SHA-256 registered in the authoritative ten-run summary before copying.

`local_output_file_manifest.tsv` records SHA-256 and byte size for every local output file, including excluded binary artifacts. Checkpoint binaries, optimizer states, generated spectra, caches and raw arrays are intentionally not committed.

This archive contains Validation evidence only and does not contain simulated-Test predictions or metrics.
