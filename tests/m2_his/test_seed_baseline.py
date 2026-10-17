"""Sample patients CSV, frozen before v1.1 B4.

The hash was taken from the pre-B4 file. The B4 generator must
never rewrite the patients unless asked with --patients.
"""

import hashlib

from aarogya.platform import paths

FROZEN_SHA256 = (
    "dbd86eb1c7b28ba85b2f291cb4d0cc89b746f676be5843e978662561ae174ac3"
)


def test_patients_sample_unchanged():
    raw = paths.SEED_CSV.read_bytes()
    # Normalise line endings across checkouts
    digest = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    assert digest == FROZEN_SHA256
