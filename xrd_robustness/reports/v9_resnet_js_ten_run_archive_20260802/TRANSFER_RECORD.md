# V9 ten-run evidence transfer record

Date: 2026-08-02

The Git-safe evidence archive was transferred from the migrated Tencent Cloud Shanghai instance and independently verified before this repository update.

## Outer archive verification

- Archive: `v9_ten_run_git_safe_archive_20260802.tar.gz`
- Expected SHA-256: `5a276a9091c2c70c3e6a7a2689479731c35b47be03169c1c8eeec78af5798b10`
- Observed SHA-256: `5a276a9091c2c70c3e6a7a2689479731c35b47be03169c1c8eeec78af5798b10`
- Result: PASS

## Archive safety and integrity

- Tar members: 178
- Regular files: 155
- Directories: 23
- Unsafe absolute paths, `..` traversal paths, symlinks, hard links, devices or FIFOs: 0
- Uncompressed file bytes: 7,976,469
- Internal `archive_files.sha256` entries checked: 154
- Internal hash mismatches or missing files: 0
- Archive status: `verified_complete_results_archive`
- Registered runs: 10
- Simulated Test accessed by this archive: false

## Registered result hashes

| Run | Best epoch | Global step | `results.json` SHA-256 |
|---|---:|---:|---|
| `seed_20260711_dynamic_erm` | 80 | 49280 | `0A33CEC8F9B5040B78BF134BA298FFC6C0F9ABC2CA5E4C2148ADBABBF95B0E43` |
| `seed_20260711_js_lambda_60` | 40 | 24640 | `BA15033E27674233335044D2918E380BBAA54FE5594F126114E7C388BB7C1C20` |
| `seed_20260712_dynamic_erm` | 90 | 55440 | `10303967F4D59CEBEBA6D851024B05759A0A3204011AE3B23DA3493E436917BF` |
| `seed_20260712_js_lambda_60` | 80 | 49280 | `4A9EC2ECF7CC17141E37E3E6B1F7240B4E0452D08BB0F75D1DF5DDF9055290E9` |
| `seed_20260713_dynamic_erm` | 100 | 61600 | `0A2B0762A13CB1AE643BF3BDDCFA510560D5E3BEEAD859FB9C1281BD98B531B5` |
| `seed_20260713_js_lambda_60` | 80 | 49280 | `CDD564C707B343BD9CF734C48FD59C832D1E2D83687C95AEAC1A33E1E42067E9` |
| `seed_20260714_dynamic_erm` | 90 | 55440 | `0727115988B83A791912CE08A4EF88437FB02C86E20FA11B782BCD531F7B26DA` |
| `seed_20260714_js_lambda_60` | 30 | 18480 | `5D8CB731D39DDC6DE43B72D51553BA93799B6A918EFB13E1C4FA45FE9D2196E9` |
| `seed_20260715_dynamic_erm` | 80 | 49280 | `EB730CDCABF46FDE3DF3CDB3762DB36C8420FB0C917B5A5B5DB5464A27F31EB0` |
| `seed_20260715_js_lambda_60` | 60 | 36960 | `CF6D155A78C2B4BCDD040EEA0C8A3ABE6AC71A9699AA2C1AF0BF771D9B34D327` |

The repository directory also contains the archive README, verification index and run registry. Checkpoint binaries, optimizer states, raw prediction arrays, generated spectra and caches remain excluded under the existing binary policy; their local paths, sizes and SHA-256 values are recorded by the verified archive manifest.
