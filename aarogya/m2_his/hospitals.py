"""M2 HIS: the single Hospital class and the hospital network."""


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


HOSPITAL_NETWORK = [
    Hospital("H001", "Apollo Hospital", "Chennai", 500),
    Hospital("H002", "Fortis Hospital", "Bangalore", 400),
    Hospital("H003", "Manipal Hospital", "Delhi", 450),
]
