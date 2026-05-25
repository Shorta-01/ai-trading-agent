# Task 183

Slice 28 — V1.1 Mean-Rev + QVM rebuild. The second half of the
predictor-quality rebuild work. The Slice 22 audit flagged
specific issues:

* **Mean-Rev**: target is the 20-day SMA regardless of regime;
  trending assets will get a wrong "reversion that never
  happens" prediction. The Hurst-confidence multiplier dampens
  this only partially.
* **QVM**: minimum universe size of 5 is too small for stable
  cross-sectional z-scores (industry practice ≥ 30); the
  composite is hard-clipped at ±2 rather than soft-mapped; no
  sector-neutralization (a tech stock vs. a utility compared
  on the same value distribution).

Scope:
- **Mean-Rev rebuild** (`mean_reversion_predictor.py`):
  - Hurst-asymmetric target: when ``H > 0.55`` the projected price
    blends toward an extrapolated trend continuation (less
    reversion); when ``H < 0.45`` it stays pulled toward the SMA
    (full reversion). The blend is a linear interpolation
    parameterised on ``H``.
  - Behind a new `mean_reversion_hurst_asymmetric_target` constructor
    knob defaulting to False so V1 behaviour is preserved.
- **QVM rebuild** (`qvm_factor_predictor.py`):
  - Raise the minimum-universe floor from 5 to 30 (still
    configurable). Universe < 30 returns
    ``insufficient_universe``.
  - Sector-neutral z-scoring: subtract the sector mean from each
    factor component before z-scoring against the
    sector-de-meaned distribution. Falls back to global z-score
    when sector data is missing.
  - Soft-tanh mapping of the composite z-score onto [-1, +1]
    instead of the hard ±2 clip; behind a new
    `qvm_soft_clip_composite` knob.
- New settings: `mean_reversion_hurst_asymmetric_target` (default
  False), `qvm_min_universe_size` (default 30, configurable),
  `qvm_sector_neutral_zscore` (default False), `qvm_soft_clip_composite`
  (default False).
- Tests: Hurst-asymmetric target behaviour on trending vs
  mean-reverting series; QVM universe-size floor with the new
  default; sector-neutral z-scoring with synthetic two-sector
  universe; soft-tanh mapping vs hard-clip mapping.

When Slice 28 ships, Slice 29 (real AI explanation provider) is
unblocked.

Manual approval gate stays; safety booleans hard-False on every
persisted record. The defaults preserve V1 behaviour so existing
tests stay green.
