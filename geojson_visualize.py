import json
import matplotlib.pyplot as plt
from shapely.geometry import shape
import random

def plot_geojson(path):
    # Load geojson
    with open(path, "r") as f:
        data = json.load(f)

    fig, ax = plt.subplots(figsize=(10, 8))

    for feat in data["features"]:
        geom = shape(feat["geometry"])
        gtype = geom.geom_type

        if gtype == "Polygon":
            # 외곽선 추출
            x, y = geom.exterior.xy
            ax.plot(x, y, color="orange", linewidth=2, label="Polygon")

        elif gtype == "LineString":
            x, y = geom.xy
            # 💡 랜덤 색상 생성 (R, G, B)
            rand_color = (random.random(), random.random(), random.random())
            
            # 💡 무조건 실선(solid)으로 그리기
            ax.plot(x, y, color=rand_color, linewidth=2, linestyle='-', label="LineString")

        elif gtype == "Point":
            ax.scatter(geom.x, geom.y, s=50, color="black", label="Point")

        else:
            print(f"Unsupported geometry: {gtype}")

    ax.set_aspect("equal", "box")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    
    # 범례 중복 제거
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys())

    plt.title("GeoJSON Visualization (Random Colors)")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.show()


if __name__ == "__main__":
    plot_geojson("lf_test.geojson")