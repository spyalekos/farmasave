from dataclasses import dataclass

@dataclass
class Medication:
    id: int
    name: str
    type: str
    pieces_per_box: int
    current_boxes: int
    current_pieces: int

    @property
    def total_pieces(self):
        return self.current_pieces + (self.current_boxes * self.pieces_per_box)

@dataclass
class Dosage:
    med_id: int
    dosage_per_day: int
