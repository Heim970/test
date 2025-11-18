# ============================================================
# area_splitter_scanline.py
#
# 안정적인 Fly-zone 분할용 Scanline Splitter
# - UTM에서 NFZ subtract 후
# - fly_zone을 가로 방향 horizontal band 로 드론 수만큼 분할
# - 각 band ∩ fly_zone = zone_i
# - smoothing / cleaning 불필요
# - MultiPolygon 안전
# - boundary-only inverse transform
# ============================================================

from shapely.geometry import Polygon, MultiPolygon, box
from shapely.ops import unary_union
from pyproj import CRS, Transformer


# -----------------------------
# 좌표 변환
# -----------------------------

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


def get_transformers(poly_ll: Polygon):
    cx, cy = poly_ll.centroid.x, poly_ll.centroid.y
    utm = latlon_to_utm_crs(cx, cy)

    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    to_ll  = Transformer.from_crs(utm, "EPSG:4326", always_xy=True)

    return (
        lambda lon, lat: to_utm.transform(lon, lat),
        lambda x, y: to_ll.transform(x, y),
    )


def poly_to_utm(poly_ll: Polygon, fwd):
    coords = [(fwd(x, y)[0], fwd(x, y)[1]) for x, y in poly_ll.exterior.coords]
    return Polygon(coords)


# -----------------------------
# NFZ subtract
# -----------------------------

def subtract_nfz(fly_poly, nfz_polys):
    if not nfz_polys:
        return fly_poly

    union_nfz = unary_union(nfz_polys)
    out = fly_poly.difference(union_nfz)
    if out.is_empty:
        return None
    return out


# -----------------------------
# UTM → LL 변환 (boundary-only, MultiPolygon-safe)
# -----------------------------

def utm_to_ll_polygon(poly, inv):
    if poly.is_empty:
        return poly

    # 단일 Polygon
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


# -----------------------------
# Main Scanline Split Logic
# -----------------------------

def split_flyzone_scanline(fly_coords, nfz_list, drone_count):
    """
    fly_coords : [[lon, lat], ...]
    nfz_list   : [ [[lon,lat], ...], ... ]
    drone_count: number of zones

    Return: [Polygon or MultiPolygon (LL), ...]
    """

    # 1) LL polygon
    fly_ll = Polygon(fly_coords)
    nfz_ll = [Polygon(n) for n in nfz_list]

    # 2) Transformers
    fwd, inv = get_transformers(fly_ll)

    # 3) LL → UTM
    fly_utm = poly_to_utm(fly_ll, fwd)
    nfz_utm = [poly_to_utm(n, fwd) for n in nfz_ll]

    # 4) NFZ subtract
    real_poly = subtract_nfz(fly_utm, nfz_utm)
    if real_poly is None:
        return []

    # 5) fly_zone bounds
    minx, miny, maxx, maxy = real_poly.bounds
    total_h = maxy - miny
    slice_h = total_h / drone_count

    zones_utm = []

    # 6) Slice fly_zone horizontally into N bands
    for i in range(drone_count):
        y0 = miny + i * slice_h
        y1 = y0 + slice_h

        band = box(minx, y0, maxx, y1)
        inter = real_poly.intersection(band)

        if inter.is_empty:
            zones_utm.append(Polygon())
        else:
            zones_utm.append(inter)

    # 7) Convert each zone back to LL
    zones_ll = []
    for poly in zones_utm:
        if poly.geom_type == "Polygon":
            zones_ll.append(utm_to_ll_polygon(poly, inv))

        elif poly.geom_type == "MultiPolygon":
            merged = []
            for sub in poly.geoms:
                merged.append(utm_to_ll_polygon(sub, inv))
            zones_ll.append(unary_union(merged))

        else:
            zones_ll.append(Polygon())

    return zones_ll
