import csv
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon

def load_polygon_from_csv(path):
    coords = []
    with open(path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            # 빈 줄 / 잘못된 줄 스킵
            if not row or len(row) < 2:
                continue

            # 공백 제거 + float 변환
            try:
                lon = float(row[0].strip())
                lat = float(row[1].strip())
                coords.append((lon, lat))
            except ValueError:
                # 헤더나 이상한 줄 무시
                continue

    # 첫 좌표와 마지막 좌표가 다르면 polygon 자동 close
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    return Polygon(coords)


def plot_poly(poly, color='blue'):
    if poly.is_empty:
        return

    if isinstance(poly, Polygon):
        x, y = poly.exterior.xy
        plt.plot(x, y, color=color)
        plt.fill(x, y, alpha=0.3, color=color)

    elif isinstance(poly, MultiPolygon):
        for g in poly.geoms:
            x, y = g.exterior.xy
            plt.plot(x, y, color=color)
            plt.fill(x, y, alpha=0.3, color=color)


if __name__ == "__main__":
    path = "fly_zone.csv"   # ← 네 CSV 경로
    poly = load_polygon_from_csv(path)

    plt.figure(figsize=(8, 8))
    plot_poly(poly, color="red")

    plt.gca().set_aspect('equal', adjustable='box')
    plt.title("Polygon Visualization From CSV")
    plt.show()
