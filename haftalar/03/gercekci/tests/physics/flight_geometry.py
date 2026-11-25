"""Independent geometry used to distinguish alternating eights from circles."""
import math

def winding(points, centre):
    angles = [math.atan2(p[1]-centre[1], p[0]-centre[0]) for p in points]
    return sum(math.atan2(math.sin(b-a), math.cos(b-a)) for a, b in zip(angles, angles[1:])) / (2*math.pi)

def lobes(points, split=0., deadband=15.):
    sequence = []
    for point in points:
        side = -1 if point[1] < split-deadband else 1 if point[1] > split+deadband else 0
        if side and (not sequence or sequence[-1] != side): sequence.append(side)
    return sequence
