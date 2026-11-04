"""Tekrarlanabilir tarla senaryosu: bölgesel sararma + bitki bazında çeşitlilik.

Bu değerler senaryo tasarımıdır. NDVI, hastalık veya gerçek tarımsal stres
ölçümü değildir. Görüntü işleme kodları bu dosyadaki bilgileri okumaz.
"""
import math
import random

SEED = 2302
STRESS_LEVELS = 12
SHADE_LEVELS = 4

# Sağlıklı koyu yeşil → sararma → kurumuş yaprak.
COLOR_STOPS = (
    (0.00, (0.13, 0.40, 0.075)),
    (0.35, (0.36, 0.53, 0.10)),
    (0.65, (0.72, 0.62, 0.15)),
    (1.00, (0.66, 0.35, 0.10)),
)


def regional_stress(east, north):
    """Komşu bitkilerde ilişkili, geniş ve yumuşak geçişli bölgeler üret."""
    patches = (
        (-17, 49, 10, 11, 0.92),
        (20, 30, 8, 8, 0.78),
        (16, 63, 9, 7, 0.60),
    )
    value = 0.06 + 0.035 * math.sin(east / 8 + north / 13)
    for cx, cy, sx, sy, strength in patches:
        distance = ((east - cx) / sx) ** 2 + ((north - cy) / sy) ** 2
        value += strength * math.exp(-0.5 * distance)
    return min(1.0, max(0.0, value))


def leaf_color(stress):
    for (s0, c0), (s1, c1) in zip(COLOR_STOPS, COLOR_STOPS[1:]):
        if stress <= s1:
            fraction = (stress - s0) / (s1 - s0)
            return tuple(a + fraction * (b - a) for a, b in zip(c0, c1))
    return COLOR_STOPS[-1][1]


def material_name(level, shade, light=False):
    return f'plant_{level:02d}_{shade:02d}' + ('_light' if light else '')


def palette():
    """Bitki başına ayrı draw call yerine ortak renk grupları kullan."""
    colors = {}
    for level in range(STRESS_LEVELS):
        base = leaf_color(level / (STRESS_LEVELS - 1))
        for shade in range(SHADE_LEVELS):
            brightness = 0.88 + 0.08 * shade
            for light in (False, True):
                factor = brightness * (1.12 if light else 1.0)
                colors[material_name(level, shade, light)] = tuple(
                    min(0.95, component * factor) for component in base
                )
    return colors


def plants():
    """Aynı seed aynı 1 575 bitkiyi üretir; satırlar ve tarla boyutu değişmez."""
    rng = random.Random(SEED)
    result = []
    for column in range(45):
        for row in range(35):
            east = -31 + 1.4 * column + rng.uniform(-0.10, 0.10)
            north = 19 + 1.4 * row + rng.uniform(-0.10, 0.10)
            stress = min(1.0, max(0.0, regional_stress(east, north) + rng.uniform(-0.035, 0.035)))
            level = round(stress * (STRESS_LEVELS - 1))
            shade = rng.randrange(SHADE_LEVELS)
            result.append({
                'id': len(result), 'east_m': east, 'north_m': north,
                'scenario_stress': stress,
                'height_m': (1.10 - 0.62 * stress) * rng.uniform(0.83, 1.17),
                'canopy_scale': (1.08 - 0.32 * stress) * rng.uniform(0.85, 1.15),
                'yaw_rad': rng.uniform(-math.pi, math.pi),
                'material': material_name(level, shade),
                'light_material': material_name(level, shade, True),
            })
    return result
