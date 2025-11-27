import json
import matplotlib.pyplot as plt
from shapely.geometry import shape

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
            ax.plot(x, y, color="orange", linewidth=2, label="polygon")

        elif gtype == "LineString":
            x, y = geom.xy
            ax.plot(x, y, color="blue", linewidth=2, label="route")

        elif gtype == "Point":
            ax.scatter(geom.x, geom.y, s=50, color="black", label="point")

        else:
            print(f"Unsupported geometry: {gtype}")

    ax.set_aspect("equal", "box")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    plt.title("GeoJSON Visualization")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.show()


if __name__ == "__main__":
    plot_geojson("vrp_test.geojson")  # 여기에 너 파일 이름 넣으면 됨
