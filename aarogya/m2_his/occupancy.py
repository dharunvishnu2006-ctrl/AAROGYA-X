"""M2 HIS: occupancy per hospital from open stays, never from city."""

import sqlite3
from typing import Any, Dict, List, Optional

from aarogya.m2_his.hospitals import get_hospitals
from aarogya.m2_his.stays import count_open_stays_by_hospital


def hospital_occupancy(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns open stays / total beds for every hospital.

    Above 100% is reported as is and flagged over_capacity.
    With 0 beds the rate is undefined, so occupancy_pct is None.
    """
    open_counts = count_open_stays_by_hospital(conn)
    rows = []
    for hospital in get_hospitals(conn):
        open_stays = open_counts.get(hospital.hospital_id, 0)
        pct: Optional[float] = (
            None
            if hospital.total_beds == 0
            else hospital.occupancy_rate(open_stays)
        )
        rows.append(
            {
                "hospital_id": hospital.hospital_id,
                "name": hospital.name,
                "city": hospital.city,
                "total_beds": hospital.total_beds,
                "open_stays": open_stays,
                "occupancy_pct": pct,
                "over_capacity": hospital.is_over_capacity(open_stays),
            }
        )
    return rows
