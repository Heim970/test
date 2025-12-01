import json
import numpy as np
from shapely.geometry import shape, Polygon
from shapely.ops import transform
from pyproj import Transformer


def geojson_to_polygons(geojson_bytes):
    data = json.loads(geojson_bytes)
    feats = data.get("features", [])

    polys = []
    for f in feats:
        geom = shape(f["geometry"])
        if isinstance(geom, Polygon):
            polys.append(geom)
        else:
            for g in geom.geoms:
                if isinstance(g, Polygon):
                    polys.append(g)
    return polys


def polygons_to_utm(polys):
    """WGS84 → UTM(K) 변환"""
    tf = Transformer.from_crs("EPSG:4326", "EPSG:32652", always_xy=True)

    utm_polys = [transform(tf.transform, p) for p in polys]
    return utm_polys


def rasterize_polygon(polys, resolution=1.0):
    """
    polys: UTM polygon list
    resolution: meter per pixel (ex: 0.5m or 1m)

    return:
       mask: np.ndarray (H, W)
       meta: dict (bounds + resolution)
    """
    # 전체 영역 바운딩 박스
    minx = min(p.bounds[0] for p in polys)
    miny = min(p.bounds[1] for p in polys)
    maxx = max(p.bounds[2] for p in polys)
    maxy = max(p.bounds[3] for p in polys)

    width = int(np.ceil((maxx - minx) / resolution))
    height = int(np.ceil((maxy - miny) / resolution))

    mask = np.zeros((height, width), dtype=np.uint8)

    # raster 좌표 → UTM 좌표 역변환
    # pixel (j, i):
    #   x = minx + j*resolution
    #   y = miny + i*resolution
    for i in range(height):
        y = miny + i * resolution + resolution / 2
        for j in range(width):
            x = minx + j * resolution + resolution / 2

            pt = (x, y)
            # 어느 polygon 안에 포함되는지 검사
            for poly in polys:
                if poly.contains(shape({"type": "Point", "coordinates": pt})):
                    mask[i, j] = 1
                    break

    meta = {
        "utm_min_x": minx,
        "utm_min_y": miny,
        "resolution": resolution,
        "crs": "EPSG:32652",
    }

    return mask, meta


def save_mask(mask, meta, mask_path="sample_mask.npy", meta_path="sample_mask_meta.json"):
    np.save(mask_path, mask)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def geojson_to_mask(geojson_bytes, resolution=1.0):
    polys = geojson_to_polygons(geojson_bytes)
    utm_polys = polygons_to_utm(polys)
    mask, meta = rasterize_polygon(utm_polys, resolution=resolution)
    return mask, meta
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import numpy as np
from shapely.geometry import shape, Polygon
from shapely.ops import transform
from pyproj import Transformer


def load_polygons_from_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    feats = data.get("features", [])
    polys = []

    for f in feats:
        geom = shape(f["geometry"])
        if isinstance(geom, Polygon):
            polys.append(geom)
        else:
            # MultiPolygon 등 해체
            for g in geom.geoms:
                if isinstance(g, Polygon):
                    polys.append(g)

    return polys


def to_utm(polys, epsg="EPSG:32652"):
    """WGS84 → UTM 변환"""
    tf = Transformer.from_crs("EPSG:4326", epsg, always_xy=True)
    return [transform(tf.transform, p) for p in polys]


def rasterize(polys, resolution=1.0):
    """폴리곤 → 바이너리 mask rasterize"""
    minx = min(p.bounds[0] for p in polys)
    miny = min(p.bounds[1] for p in polys)
    maxx = max(p.bounds[2] for p in polys)
    maxy = max(p.bounds[3] for p in polys)

    width = int(np.ceil((maxx - minx) / resolution))
    height = int(np.ceil((maxy - miny) / resolution))

    mask = np.zeros((height, width), dtype=np.uint8)

    for i in range(height):
        y = miny + i * resolution + resolution / 2
        for j in range(width):
            x = minx + j * resolution + resolution / 2

            pt = {"type": "Point", "coordinates": (x, y)}
            for poly in polys:
                if poly.contains(shape(pt)):
                    mask[i, j] = 1
                    break

    meta = {
        "utm_min_x": minx,
        "utm_min_y": miny,
        "resolution": resolution,
        "crs": "EPSG:32652"
    }

    return mask, meta


def main():
    # 필요한 부분만 수정해서 사용 (파일명 / resolution)
    GEOJSON_PATH = "lf/mlf_result.geojson"
    MASK_OUT = "lf/sample_mask.npy"
    META_OUT = "lf/sample_mask_meta.json"
    RESOLUTION = 1.0   # meter per pixel

    print(f"[INFO] Loading polygons from {GEOJSON_PATH}")
    polys = load_polygons_from_geojson(GEOJSON_PATH)

    print("[INFO] Converting to UTM (EPSG:32652)")
    utm_polys = to_utm(polys)

    print("[INFO] Rasterizing polygon → binary mask")
    mask, meta = rasterize(utm_polys, RESOLUTION)

    print(f"[INFO] Saving mask → {MASK_OUT}")
    np.save(MASK_OUT, mask)

    print(f"[INFO] Saving metadata → {META_OUT}")
    with open(META_OUT, "w") as f:
        json.dump(meta, f, indent=2)

    print("[DONE] Complete. Generated:")
    print(f" - {MASK_OUT} (mask shape = {mask.shape})")
    print(f" - {META_OUT}")


if __name__ == "__main__":
    main()
