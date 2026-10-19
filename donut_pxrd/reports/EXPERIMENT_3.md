# Experiment 3: DONUT-PXRD

**Status:** COMPLETE

## `experiment_3_width`

| Metric | Mean over seeds | Seed SD |
|---|---:|---:|
| du_abs_error | 0.18091749 | 0.0039478875 |
| dv_abs_error | 0.73310043 | 0.11588094 |
| q_mae | 0.45700896 | 0.058122983 |
| a_abs_error_angstrom | 0.005708332 | 0.0018341093 |
| c_abs_error_angstrom | 0.025843931 | 0.0026433708 |
| zero_shift_abs_error_deg | 0.051286541 | 0.0048779399 |
| fwhm_abs_error_deg | 0.020930484 | 0.0034539897 |
| background_abs_error | 0 | 0 |
| physics_profile_rmse | 0.10362441 | 0.010792289 |
| encoder_p50_seconds | 0.0032456667 | 0.00020599835 |
| encoder_p95_seconds | 0.004780105 | 5.4087588e-05 |

Prediction failure fraction: `0`; `n=231` sample-seed rows.

## `experiment_3_background`

| Metric | Mean over seeds | Seed SD |
|---|---:|---:|
| du_abs_error | 0.098514031 | 0.056105098 |
| dv_abs_error | 0.18099085 | 0.21659507 |
| q_mae | 0.13975244 | 0.13635007 |
| a_abs_error_angstrom | 0.0041194063 | 0.0023290164 |
| c_abs_error_angstrom | 0.0071412854 | 0.0073154856 |
| zero_shift_abs_error_deg | 0.034380174 | 0.0026309785 |
| fwhm_abs_error_deg | 0.012956179 | 0.0079190519 |
| background_abs_error | 0.0014949125 | 0.0011779968 |
| physics_profile_rmse | 0.051417121 | 0.033737451 |
| encoder_p50_seconds | 0.0036187 | 0.00082547811 |
| encoder_p95_seconds | 0.01205158 | 0.0029078664 |

Prediction failure fraction: `0`; `n=231` sample-seed rows.

## `experiment_3_noise`

| Metric | Mean over seeds | Seed SD |
|---|---:|---:|
| du_abs_error | 0.15664719 | 0.16188317 |
| dv_abs_error | 0.29942641 | 0.40319446 |
| q_mae | 0.2280368 | 0.28253849 |
| a_abs_error_angstrom | 0.0043623338 | 0.0028241108 |
| c_abs_error_angstrom | 0.013153435 | 0.017682595 |
| zero_shift_abs_error_deg | 0.040371282 | 0.01539353 |
| fwhm_abs_error_deg | 0.021194762 | 0.0063718378 |
| background_abs_error | 0.0020094856 | 0.0012718152 |
| physics_profile_rmse | 0.058923205 | 0.038261399 |
| encoder_p50_seconds | 0.010073733 | 0.0033147582 |
| encoder_p95_seconds | 0.014921203 | 0.00043998337 |

Prediction failure fraction: `0`; `n=231` sample-seed rows.

## Audits

```json
{
  "texture_OOD_stress": {
    "by_seed": {
      "20261061": {
        "n": 77,
        "du_abs_error": 0.11252964418381456,
        "dv_abs_error": 0.1926902821069801,
        "q_mae": 0.15260996314539732,
        "a_abs_error_angstrom": 0.005993962917428551,
        "c_abs_error_angstrom": 0.005059274137451115,
        "zero_shift_abs_error_deg": 0.03319611192623916,
        "fwhm_abs_error_deg": 0.017196508076595462,
        "background_abs_error": 0.0007146173356815766,
        "physics_profile_rmse": 0.06871942783911507,
        "decoder_profile_rmse": 0.08836641743198617,
        "encoder_p50_seconds": 0.011460649984655902,
        "encoder_p95_seconds": 0.015073535000556153
      },
      "20261062": {
        "n": 77,
        "du_abs_error": 0.37799168763222635,
        "dv_abs_error": 0.7408765053594267,
        "q_mae": 0.5594340964958264,
        "a_abs_error_angstrom": 0.0088662822056749,
        "c_abs_error_angstrom": 0.03417265425384396,
        "zero_shift_abs_error_deg": 0.058020335534650934,
        "fwhm_abs_error_deg": 0.020326168933979514,
        "background_abs_error": 0.0034429415240330003,
        "physics_profile_rmse": 0.09368525000361654,
        "decoder_profile_rmse": 0.21047440703426087,
        "encoder_p50_seconds": 0.012499700009357184,
        "encoder_p95_seconds": 0.015755010000430045
      },
      "20261063": {
        "n": 77,
        "du_abs_error": 0.09006886074392055,
        "dv_abs_error": 0.23645201488458487,
        "q_mae": 0.16326043781425273,
        "a_abs_error_angstrom": 0.005506117641312922,
        "c_abs_error_angstrom": 0.005865592810740349,
        "zero_shift_abs_error_deg": 0.03223420612560411,
        "fwhm_abs_error_deg": 0.02767322444696968,
        "background_abs_error": 0.0010734127594238204,
        "physics_profile_rmse": 0.07035879737564496,
        "decoder_profile_rmse": 0.0942473394143117,
        "encoder_p50_seconds": 0.013970700034406036,
        "encoder_p95_seconds": 0.015415400027995936
      }
    },
    "aggregate": {
      "du_abs_error": {
        "mean": 0.19353006418665383,
        "sample_sd": 0.16014271632302107,
        "by_seed": {
          "20261061": 0.11252964418381456,
          "20261062": 0.37799168763222635,
          "20261063": 0.09006886074392055
        }
      },
      "dv_abs_error": {
        "mean": 0.39000626745033057,
        "sample_sd": 0.30464933153006246,
        "by_seed": {
          "20261061": 0.1926902821069801,
          "20261062": 0.7408765053594267,
          "20261063": 0.23645201488458487
        }
      },
      "q_mae": {
        "mean": 0.29176816581849213,
        "sample_sd": 0.23186665561630593,
        "by_seed": {
          "20261061": 0.15260996314539732,
          "20261062": 0.5594340964958264,
          "20261063": 0.16326043781425273
        }
      },
      "a_abs_error_angstrom": {
        "mean": 0.006788787588138791,
        "sample_sd": 0.0018156228043775262,
        "by_seed": {
          "20261061": 0.005993962917428551,
          "20261062": 0.0088662822056749,
          "20261063": 0.005506117641312922
        }
      },
      "c_abs_error_angstrom": {
        "mean": 0.015032507067345144,
        "sample_sd": 0.01658075580880898,
        "by_seed": {
          "20261061": 0.005059274137451115,
          "20261062": 0.03417265425384396,
          "20261063": 0.005865592810740349
        }
      },
      "zero_shift_abs_error_deg": {
        "mean": 0.04115021786216474,
        "sample_sd": 0.014617864700597423,
        "by_seed": {
          "20261061": 0.03319611192623916,
          "20261062": 0.058020335534650934,
          "20261063": 0.03223420612560411
        }
      },
      "fwhm_abs_error_deg": {
        "mean": 0.021731967152514884,
        "sample_sd": 0.005377973405451601,
        "by_seed": {
          "20261061": 0.017196508076595462,
          "20261062": 0.020326168933979514,
          "20261063": 0.02767322444696968
        }
      },
      "background_abs_error": {
        "mean": 0.0017436572063794658,
        "sample_sd": 0.00148251776825508,
        "by_seed": {
          "20261061": 0.0007146173356815766,
          "20261062": 0.0034429415240330003,
          "20261063": 0.0010734127594238204
        }
      },
      "physics_profile_rmse": {
        "mean": 0.07758782507279219,
        "sample_sd": 0.01396485589513796,
        "by_seed": {
          "20261061": 0.06871942783911507,
          "20261062": 0.09368525000361654,
          "20261063": 0.07035879737564496
        }
      },
      "decoder_profile_rmse": {
        "mean": 0.13102938796018623,
        "sample_sd": 0.0688642113336137,
        "by_seed": {
          "20261061": 0.08836641743198617,
          "20261062": 0.21047440703426087,
          "20261063": 0.0942473394143117
        }
      },
      "encoder_p50_seconds": {
        "mean": 0.012643683342806375,
        "sample_sd": 0.0012612042710425694,
        "by_seed": {
          "20261061": 0.011460649984655902,
          "20261062": 0.012499700009357184,
          "20261063": 0.013970700034406036
        }
      },
      "encoder_p95_seconds": {
        "mean": 0.015414648342994044,
        "sample_sd": 0.0003407381217827508,
        "by_seed": {
          "20261061": 0.015073535000556153,
          "20261062": 0.015755010000430045,
          "20261063": 0.015415400027995936
        }
      }
    },
    "failure_rate": 0.0,
    "prediction_count": 231
  },
  "texture_manifest": {
    "schema": "donut_pxrd_texture_stress_v1",
    "dataset_npz_sha256": "9ce287eea67c3968d5d7133d10853acdfde0b6ee10d0d1e2d1aad580f8a03a7a",
    "test_indices_sha256": "12c5fd101e7b5f6aa0003626b7754028bf5fd0dc112b8a2c808a634ea945911f",
    "generator_records": [
      {
        "global_index": 339,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.168357378117374,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.970451710807818,
        "c_angstrom": 3.9811748969125667
      },
      {
        "global_index": 78,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.0686694218002541,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.014622870657478,
        "c_angstrom": 4.059318092897552
      },
      {
        "global_index": 61,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1369026360708558,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.006769710020665,
        "c_angstrom": 4.025801362121412
      },
      {
        "global_index": 355,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.4541935939217778,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9619277487119042,
        "c_angstrom": 3.9827017084836234
      },
      {
        "global_index": 304,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1368490085015663,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9624914322101517,
        "c_angstrom": 4.03110019782166
      },
      {
        "global_index": 421,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6511094634136364,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9992710400290106,
        "c_angstrom": 4.0189288239414
      },
      {
        "global_index": 153,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.2277094832389637,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.006239990109278,
        "c_angstrom": 4.040300411237109
      },
      {
        "global_index": 322,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6682549360006955,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.991301518997474,
        "c_angstrom": 4.055851261767046
      },
      {
        "global_index": 181,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3664794731238874,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9954366483665953,
        "c_angstrom": 4.014265450434311
      },
      {
        "global_index": 510,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.7866749281276599,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.010149532682909,
        "c_angstrom": 4.053425240262085
      },
      {
        "global_index": 387,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.4165450267733914,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.957893046858776,
        "c_angstrom": 3.996669349878467
      },
      {
        "global_index": 370,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6137122071869978,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9893084825082465,
        "c_angstrom": 4.051662580140298
      },
      {
        "global_index": 489,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8389356644388984,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.010420963553649,
        "c_angstrom": 4.038177399831707
      },
      {
        "global_index": 344,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.259486782225438,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.977461009183198,
        "c_angstrom": 4.032040191190724
      },
      {
        "global_index": 331,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.090562303277216,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.974180102088556,
        "c_angstrom": 3.9929953432805374
      },
      {
        "global_index": 9,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5721144713821391,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.013446863731147,
        "c_angstrom": 4.037636602415687
      },
      {
        "global_index": 148,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6341781028576655,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9585333166176953,
        "c_angstrom": 4.0284691652459825
      },
      {
        "global_index": 74,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8179384210865136,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.982427512084892,
        "c_angstrom": 4.039905776204876
      },
      {
        "global_index": 189,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8677825374037135,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.003293934437204,
        "c_angstrom": 4.031153888745563
      },
      {
        "global_index": 265,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.39820682361871,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.0189389925497405,
        "c_angstrom": 4.0272502403928385
      },
      {
        "global_index": 409,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5725489770351915,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.011700516965374,
        "c_angstrom": 4.029381331500188
      },
      {
        "global_index": 281,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8421077406398955,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.00963616164935,
        "c_angstrom": 4.0351292206576
      },
      {
        "global_index": 229,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1429116519294302,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9985330450536813,
        "c_angstrom": 4.022304810302796
      },
      {
        "global_index": 87,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6064593576116403,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9890805442824493,
        "c_angstrom": 4.004678123242969
      },
      {
        "global_index": 405,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.617961338266537,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.996098463446725,
        "c_angstrom": 4.009608488381551
      },
      {
        "global_index": 440,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.4781214350228649,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.974548191627464,
        "c_angstrom": 4.0440527714410575
      },
      {
        "global_index": 216,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.7334120539925656,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.980701645460518,
        "c_angstrom": 4.0267717566204615
      },
      {
        "global_index": 248,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.7424009589197151,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9776063667035553,
        "c_angstrom": 4.042768195873278
      },
      {
        "global_index": 435,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.7900616690272586,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9637473122876896,
        "c_angstrom": 3.9887166934569636
      },
      {
        "global_index": 429,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.9821115912759824,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.0000706407457995,
        "c_angstrom": 4.026840866771086
      },
      {
        "global_index": 194,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.0674248268644182,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.993984677849685,
        "c_angstrom": 4.050988828020317
      },
      {
        "global_index": 417,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6631674214869848,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.013095799405632,
        "c_angstrom": 4.051928323775536
      },
      {
        "global_index": 118,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8569156190628631,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.002456397457255,
        "c_angstrom": 4.062292863693529
      },
      {
        "global_index": 247,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.2629379436579842,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.989677085501892,
        "c_angstrom": 3.9980924298945193
      },
      {
        "global_index": 408,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.461206643108273,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.982267381464135,
        "c_angstrom": 4.024742174655711
      },
      {
        "global_index": 163,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1363494550911977,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9596690095975284,
        "c_angstrom": 3.9837971298293184
      },
      {
        "global_index": 456,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.094324245269774,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9759294966250636,
        "c_angstrom": 4.0232706631561586
      },
      {
        "global_index": 196,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3874066910009182,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.956383256030686,
        "c_angstrom": 4.0231704583089565
      },
      {
        "global_index": 375,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.849208075411434,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9875370220527495,
        "c_angstrom": 4.004435444664813
      },
      {
        "global_index": 291,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5868750447104869,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.957294322092382,
        "c_angstrom": 3.989867592109498
      },
      {
        "global_index": 326,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5877635484705027,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.998894563064487,
        "c_angstrom": 4.052187791792023
      },
      {
        "global_index": 12,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3436556135010629,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9545829841568687,
        "c_angstrom": 4.009250695489702
      },
      {
        "global_index": 498,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1312621010812318,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.991178527943587,
        "c_angstrom": 4.04621645964462
      },
      {
        "global_index": 430,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3867401668853812,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.011752671788407,
        "c_angstrom": 4.060020266134998
      },
      {
        "global_index": 479,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.9852471090352376,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9784165712606367,
        "c_angstrom": 4.008555301891095
      },
      {
        "global_index": 188,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3453354780996865,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9483764743198733,
        "c_angstrom": 4.012084362101263
      },
      {
        "global_index": 145,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1093856998658773,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.02546409036275,
        "c_angstrom": 4.034460027049493
      },
      {
        "global_index": 346,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.4885714100939,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.987483643749227,
        "c_angstrom": 4.043709318969004
      },
      {
        "global_index": 186,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5975858861473761,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9841220922824503,
        "c_angstrom": 4.043957494569802
      },
      {
        "global_index": 474,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.2014362012928257,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.989357998673994,
        "c_angstrom": 4.038334326547499
      },
      {
        "global_index": 4,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.2784339229415493,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.956736753245793,
        "c_angstrom": 4.020402418194909
      },
      {
        "global_index": 286,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1955870308702927,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.007444986410203,
        "c_angstrom": 4.064939635803994
      },
      {
        "global_index": 471,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.340784079059568,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9856393682825106,
        "c_angstrom": 4.008743704618182
      },
      {
        "global_index": 347,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.638343407259313,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.965096825355544,
        "c_angstrom": 4.000666711537115
      },
      {
        "global_index": 249,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.0368340023569913,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.0071035976445035,
        "c_angstrom": 4.034023999000709
      },
      {
        "global_index": 314,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3045034223146006,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.981337417486815,
        "c_angstrom": 4.048694847172813
      },
      {
        "global_index": 39,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8550171829822372,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9836931454276407,
        "c_angstrom": 4.021325637919863
      },
      {
        "global_index": 161,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.4409695561964733,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.018580273206583,
        "c_angstrom": 4.0415611161176495
      },
      {
        "global_index": 505,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.9800278759961042,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.012561530928722,
        "c_angstrom": 4.023164756017297
      },
      {
        "global_index": 279,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5689672171624721,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.990753177308949,
        "c_angstrom": 4.002443065063724
      },
      {
        "global_index": 397,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.7226243991273044,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.003040104457288,
        "c_angstrom": 4.024701867500852
      },
      {
        "global_index": 5,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.9821585466696229,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.992411476482105,
        "c_angstrom": 4.028640988399659
      },
      {
        "global_index": 262,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.2421956768375697,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9941997022611115,
        "c_angstrom": 4.0597060017385775
      },
      {
        "global_index": 258,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.6262478568702144,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.994687779625529,
        "c_angstrom": 4.046994461946173
      },
      {
        "global_index": 141,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.2303886247140907,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9972110345071186,
        "c_angstrom": 4.035241250644259
      },
      {
        "global_index": 311,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5435395132489153,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.979097459293044,
        "c_angstrom": 4.015868233057212
      },
      {
        "global_index": 334,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8789843765873079,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.009702966508003,
        "c_angstrom": 4.070315610840751
      },
      {
        "global_index": 180,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8148125528502315,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9670156751329473,
        "c_angstrom": 4.007844945406111
      },
      {
        "global_index": 342,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.1922416062443804,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9984008454513043,
        "c_angstrom": 4.0671182603722364
      },
      {
        "global_index": 242,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.5983527089039986,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.986161066098513,
        "c_angstrom": 4.057096795457184
      },
      {
        "global_index": 285,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8472462545336842,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.010138404479473,
        "c_angstrom": 4.022446508990474
      },
      {
        "global_index": 122,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.4163253347872957,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.981592971640956,
        "c_angstrom": 4.053104398576935
      },
      {
        "global_index": 335,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.7589242881584645,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9713959800919523,
        "c_angstrom": 4.011044637131053
      },
      {
        "global_index": 236,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.0469491513038922,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.95194076820663,
        "c_angstrom": 4.020695323143613
      },
      {
        "global_index": 460,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 0.8387236519616106,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9526204963027958,
        "c_angstrom": 4.010665430237352
      },
      {
        "global_index": 276,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.059479759209402,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 3.9612032658222454,
        "c_angstrom": 4.0236217585166925
      },
      {
        "global_index": 17,
        "preferred_hkl": [
          0,
          0,
          1
        ],
        "march_parameter": 0.8,
        "electronic_noise_std_counts": 1.3635150720809213,
        "intensity_factor_min": 0.7155417527999327,
        "intensity_factor_max": 1.9531249999999993,
        "a_angstrom": 4.01821582468084,
        "c_angstrom": 4.050629241878986
      }
    ],
    "march_parameter_r": 0.8,
    "preferred_hkl": [
      0,
      0,
      1
    ],
    "evaluation_only": true,
    "renderer": "xrd_robustness.simulator.simulate_from_peak_table + apply_preferred_orientation"
  }
}
```
