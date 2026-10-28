"""Class number -> problem type.

The order must be the same as in ml/data/classes.yaml (the file used for training),
because the model only outputs a class NUMBER.
"""
from app.enums import ProblemType

CLASS_INDEX = {
    0: ProblemType.POTHOLE,
    1: ProblemType.ROAD_DAMAGE,
    2: ProblemType.GARBAGE,
    3: ProblemType.WATERLOGGING,
    4: ProblemType.DAMAGED_ROAD_SIGN,
    5: ProblemType.OPEN_DRAIN,
}
