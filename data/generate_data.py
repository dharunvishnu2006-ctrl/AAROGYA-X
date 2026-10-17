"""Generates synthetic seed CSVs with a fixed seed.

Default: writes hospitals_sample.csv and stays_sample.csv, built from
the existing patients_sample.csv. The patients file is rewritten only
with --patients (that path needs faker).
Usage: python data/generate_data.py [--patients]
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Import aarogya when run as script
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aarogya.m2_his.hospitals import HOSPITAL_NETWORK  # noqa: E402

SEED = 42
DATA_DIR = ROOT / "data"
PATIENTS_CSV = DATA_DIR / "patients_sample.csv"
HOSPITALS_CSV = DATA_DIR / "hospitals_sample.csv"
STAYS_CSV = DATA_DIR / "stays_sample.csv"

STAY_SHARE = 0.6
DISCHARGED_SHARE = 0.3
WARDS = ["General", "ICU", "Surgical", "Maternity"]
STAY_START = datetime(2026, 9, 1, tzinfo=timezone.utc)
ADMIT_SPREAD_HOURS = 30 * 24
STAY_HOURS = (12, 240)
STAY_COLUMNS = (
    "patient_id",
    "hospital_id",
    "ward",
    "bed",
    "admitted_at",
    "discharged_at",
)

cities = ['Chennai','Mumbai','Delhi','Bangalore','Hyderabad','Kolkata','Pune','Ahmedabad','Jaipur','Lucknow']
genders = ['Male','Female']


def generate_patients(seed=SEED):
    """Builds 50 synthetic patients; same seed, same rows."""
    from faker import Faker

    rng = random.Random(seed)
    fake = Faker('en_IN')
    fake.seed_instance(seed)
    rows = []
    for i in range(1, 51):
        gender = rng.choice(genders)
        age = rng.randint(18, 75)
        bmi = round(rng.uniform(17.0, 40.0), 1)
        rows.append({
            'patient_id': f'P{i:03d}',
            'name': fake.name_male() if gender == 'Male' else fake.name_female(),
            'age': age,
            'gender': gender,
            'bmi': bmi,
            'bp_systolic': rng.randint(100, 190),
            'bp_diastolic': rng.randint(60, 110),
            'sugar_fasting': rng.randint(70, 250),
            'city': rng.choice(cities),
        })
    return pd.DataFrame(rows)


def generate_hospitals():
    """Writes the one hospital network as rows."""
    return pd.DataFrame(
        [
            {
                "hospital_id": h.hospital_id,
                "name": h.name,
                "city": h.city,
                "total_beds": h.total_beds,
            }
            for h in HOSPITAL_NETWORK
        ]
    )


def generate_stays(patient_ids, seed=SEED):
    """Gives some patients one stay; beds never shared."""
    rng = random.Random(seed)
    next_bed = {}
    rows = []
    for patient_id in sorted(patient_ids):
        if rng.random() >= STAY_SHARE:
            continue
        hospital_id = rng.choice(HOSPITAL_NETWORK).hospital_id
        ward = rng.choice(WARDS)
        # Number beds per hospital and ward
        number = next_bed.get((hospital_id, ward), 0) + 1
        next_bed[(hospital_id, ward)] = number
        admitted = STAY_START + timedelta(
            hours=rng.randint(0, ADMIT_SPREAD_HOURS)
        )
        discharged = ""
        if rng.random() < DISCHARGED_SHARE:
            stay_for = timedelta(hours=rng.randint(*STAY_HOURS))
            discharged = (admitted + stay_for).isoformat()
        rows.append(
            {
                "patient_id": patient_id,
                "hospital_id": hospital_id,
                "ward": ward,
                "bed": f"B{number:02d}",
                "admitted_at": admitted.isoformat(),
                "discharged_at": discharged,
            }
        )
    rows.sort(key=lambda row: (row["admitted_at"], row["patient_id"]))
    return pd.DataFrame(rows, columns=list(STAY_COLUMNS))


def main(argv=None, data_dir=DATA_DIR):
    argv = sys.argv[1:] if argv is None else argv
    data_dir = Path(data_dir)
    patients_csv = data_dir / PATIENTS_CSV.name
    if "--patients" in argv:
        patients = generate_patients()
        patients.to_csv(patients_csv, index=False)
        print(f"Generated {len(patients)} patients")
    patient_ids = pd.read_csv(patients_csv, dtype=str)["patient_id"]
    hospitals = generate_hospitals()
    hospitals.to_csv(data_dir / HOSPITALS_CSV.name, index=False)
    stays = generate_stays(patient_ids.str.strip().tolist())
    stays.to_csv(data_dir / STAYS_CSV.name, index=False)
    open_count = int((stays["discharged_at"] == "").sum())
    print(
        f"Generated {len(hospitals)} hospitals, {len(stays)} stays "
        f"({open_count} open)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
