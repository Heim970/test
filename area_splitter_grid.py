# ============================================================
# area_splitter_grid.py
#
# Fly-zone을 row × col 2D grid로 균등 분할한 뒤
# 각 cell ∩ (fly_zone - NFZ) 를 zone으로 사용하는 방식.
#
# - geometry 안정성 최고 (difference + intersection만 사용)
# - multi-polygon safe
# - smoothing/cleaning 없음
# - runner에서 바로 사용 가능
# ============================================================

from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from pyproj import CRS, Transformer
import math


# ------------------------------------------------------------
# 좌표 변환
# ------------------------------------------------------------

def latlon_to_utm_crs(lon, lat):
    zone = int((lon + 180) // 6) + 1
    south = lat < 0
    return CRS.from_dict({
        "proj": "utm",
        "zone": zone,
        "south": south,
        "ellps": "WGS84",
        "units": "m",
    })


def get_transformers(poly_ll):
    cx, cy = poly_ll.centroid.x, poly_ll.centroid.y
    utm = latlon_to_utm_crs(cx, cy)
    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    to_ll  = Transformer.from_crs(utm, "EPSG:4326", always_xy=True)

    return (
        lambda lon, lat: to_utm.transform(lon, lat),
        lambda x, y: to_ll.transform(x, y),
    )


def poly_to_utm(poly_ll, fwd):
    coords = [(fwd(x, y)[0], fwd(x, y)[1]) for x, y in poly_ll.exterior.coords]
    return Polygon(coords)


# ------------------------------------------------------------
# NFZ difference
# ------------------------------------------------------------

def subtract_nfz(fly_poly, nfz_polys):
    if not nfz_polys:
        return fly_poly

    merged = unary_union(nfz_polys)
    out = fly_poly.difference(merged)
    return out if not out.is_empty else None


# ------------------------------------------------------------
# LL 변환 (boundary-only)
# ------------------------------------------------------------

def utm_to_ll_polygon(poly, inv):
    if poly.is_empty:
        return poly

    # 단일 polygon
    if poly.geom_type == "Polygon":
        ext = [(inv(x, y)[0], inv(x, y)[1]) for x, y in poly.exterior.coords]
        return Polygon(ext)

    # MultiPolygon
    if poly.geom_type == "MultiPolygon":
        parts = []
        for g in poly.geoms:
            if g.is_empty:
                continue
            ext = [(inv(x, y)[0], inv(x, y)[1]) for x, y in g.exterior.coords]
            parts.append(Polygon(ext))
        return MultiPolygon(parts)

    return Polygon()


# ------------------------------------------------------------
# row × col grid splitter (혜민용)
# ------------------------------------------------------------

def auto_grid_shape(n):
    """
    n개의 zone을 생성하기 위한 row, col 자동 계산.
    - 가능한 한 정사각형 형태에 가깝게
    - 예: 4→2×2, 5→2×3, 6→2×3, 7→3×3, 8→3×3, 9→3×3
    """
    r = int(math.sqrt(n))
    c = math.ceil(n / r)
    return r, c


def split_flyzone_grid(fly_coords, nfz_list, drone_count):
    """
    fly_coords = [(lon, lat), ...]
    nfz_list = [ [(lon, lat), ...], ... ]
    """

    # 1) LL polygon
    fly_ll = Polygon(fly_coords)
    nfz_ll = [Polygon(n) for n in nfz_list]

    # 2) transformers
    fwd, inv = get_transformers(fly_ll)

    # 3) LL → UTM
    fly_utm = poly_to_utm(fly_ll, fwd)
    nfz_utm = [poly_to_utm(n, fwd) for n in nfz_ll]

    # 4) NFZ subtract
    real_poly = subtract_nfz(fly_utm, nfz_utm)
    if real_poly is None:
        return []

    # 5) grid shape 결정
    rows, cols = auto_grid_shape(drone_count)

    minx, miny, maxx, maxy = real_poly.bounds
    dx = (maxx - minx) / cols
    dy = (maxy - miny) / rows

    zones_utm = []

    # 6) 각 cell ∩ real_poly
    for r in range(rows):
        for c in range(cols):
            x0 = minx + c * dx
            x1 = x0 + dx
            y0 = miny + r * dy
            y1 = y0 + dy
            cell = box(x0, y0, x1, y1)

            inter = real_poly.intersection(cell)
            zones_utm.append(inter)
    
    total_cells = len(zones_utm)

    if total_cells > drone_count:
        base = zones_utm[:drone_count]       # 필요한 만큼만 남기고
        extra = zones_utm[drone_count:]      # 초과된 cell들

        # 마지막 zone에 merge
        merged_last = base[-1]
        for e in extra:
            merged_last = merged_last.union(e)

        base[-1] = merged_last
        zones_utm = base

    # 7) UTM → LL 변환
    final_ll = []
    for poly in zones_utm:
        if poly.is_empty:
            final_ll.append(Polygon())
            continue

        if poly.geom_type == "Polygon":
            final_ll.append(utm_to_ll_polygon(poly, inv))

        else:
            merged = []
            for sub in poly.geoms:
                merged.append(utm_to_ll_polygon(sub, inv))
            final_ll.append(unary_union(merged))

    return final_ll
