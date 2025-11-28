import json
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import shape
from shapely.ops import transform


def compute_centroid(features):
    """전체 geometry에서 centroid 계산."""
    xs = []
    ys = []
    for feat in features:
        geom = shape(feat["geometry"])
        gtype = geom.geom_type

        if gtype == "Point":
            xs.append(geom.x)
            ys.append(geom.y)

        elif gtype == "LineString":
            x, y = geom.xy
            xs.extend(x)
            ys.extend(y)

        elif gtype == "Polygon":
            x, y = geom.exterior.xy
            xs.extend(x)
            ys.extend(y)

    return np.mean(xs), np.mean(ys)


def normalize_geometry(geom, cx, cy):
    """좌표를 centroid 기준으로 shift."""
    return transform(lambda x, y, z=None: (x - cx, y - cy), geom)


def normalize_geojson(path):
    # Load geojson
    with open(path, "r") as f:
        data = json.load(f)

    features = data["features"]
    
    # 전체 centroid 계산
    cx, cy = compute_centroid(features)
    print(f"Applied centroid shift: ({cx}, {cy})")

    fig, ax = plt.subplots(figsize=(10, 8))

    # 정규화 후 바로 plot
    for feat in features:
        geom = shape(feat["geometry"])
        geom = normalize_geometry(geom, cx, cy)  # shift 적용

        gtype = geom.geom_type

        if gtype == "Polygon":
            x, y = geom.exterior.xy
            ax.plot(x, y, color="orange", linewidth=2)

        elif gtype == "LineString":
            x, y = geom.xy
            ax.plot(x, y, color="blue", linewidth=2)

        elif gtype == "Point":
            ax.scatter(geom.x, geom.y, s=50, color="black")

    ax.set_aspect("equal", "box")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    plt.title("Normalized GeoJSON Visualization (Centered at 0,0)")
    plt.xlabel("X (shifted)")
    plt.ylabel("Y (shifted)")
    plt.show()      



if __name__ == "__main__":
    normalize_geojson("vrp_test.geojson")  # 여기에 너 파일 이름 넣으면 됨