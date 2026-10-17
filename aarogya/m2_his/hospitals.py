"""M2 HIS: the single Hospital class and the hospital network."""

import sqlite3
from typing import List, Optional

HOSPITAL_FIELDS = ("hospital_id", "name", "city", "total_beds")


class Hospital:
    def __init__(
        self, hospital_id: str, name: str, city: str, total_beds: int
    ):
        self.hospital_id = hospital_id
        self.name = name
        self.city = city
        self.total_beds = total_beds

    def occupancy_rate(self, active_patients: int) -> float:
        if self.total_beds <= 0:
            return 0.0
        return round((active_patients / self.total_beds) * 100, 1)

    def is_over_capacity(self, open_stays: int) -> bool:
        """True when open stays exceed beds; never clamped."""
        return open_stays > self.total_beds


HOSPITAL_NETWORK = [
    Hospital("H001", "Apollo Hospital", "Chennai", 500),
    Hospital("H002", "Fortis Hospital", "Bangalore", 400),
    Hospital("H003", "Manipal Hospital", "Delhi", 450),
]


def _from_row(row: sqlite3.Row) -> Hospital:
    return Hospital(
        row["hospital_id"], row["name"], row["city"], row["total_beds"]
    )


def insert_hospital(conn: sqlite3.Connection, hospital: Hospital) -> None:
    """Stores one hospital; a duplicate id raises IntegrityError."""
    with conn:
        conn.execute(
            """
            INSERT INTO hospitals (hospital_id, name, city, total_beds)
            VALUES (?, ?, ?, ?)
            """,
            (
                hospital.hospital_id,
                hospital.name,
                hospital.city,
                hospital.total_beds,
            ),
        )


def get_hospital(
    conn: sqlite3.Connection, hospital_id: str
) -> Optional[Hospital]:
    """Returns one stored hospital, or None."""
    row = conn.execute(
        "SELECT * FROM hospitals WHERE hospital_id = ?", (hospital_id,)
    ).fetchone()
    return _from_row(row) if row else None


def get_hospitals(conn: sqlite3.Connection) -> List[Hospital]:
    """Returns every stored hospital sorted by hospital_id."""
    rows = conn.execute(
        "SELECT * FROM hospitals ORDER BY hospital_id ASC"
    ).fetchall()
    return [_from_row(row) for row in rows]


def count_hospitals(conn: sqlite3.Connection) -> int:
    """Returns the number of stored hospitals."""
    return int(conn.execute("SELECT COUNT(*) FROM hospitals").fetchone()[0])
