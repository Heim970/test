import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon
from area_splitter_grid import split_flyzone_grid

# ----------------------------------
# 예시 polygon (fly_zone)
# 적당히 네 좌표 넣어도 됨
# ----------------------------------

fly = [
    (126.1, 37.1),
    (126.2, 37.1),
    (126.25, 37.15),
    (126.2, 37.2),
    (126.1, 37.2),
    (126.1, 37.1)
]

# 예시 NFZ
nfz1 = [
    (126.15, 37.13),
    (126.18, 37.13),
    (126.18, 37.16),
    (126.15, 37.16),
    (126.15, 37.13)
]

nfzs = [nfz1]

# ----------------------------------
# 분할 실행
# ----------------------------------

zones = split_flyzone_grid(fly, nfzs, drone_count=23)

# ----------------------------------
# 도식화 함수
# ----------------------------------

def plot_poly(poly, color='blue'):
    if poly.is_empty:
        return
    if isinstance(poly, Polygon):
        x, y = poly.exterior.xy
        plt.fill(x, y, alpha=0.4, fc=color, ec='black')
    elif isinstance(poly, MultiPolygon):
        for g in poly.geoms:
            x, y = g.exterior.xy
            plt.fill(x, y, alpha=0.4, fc=color, ec='black')


# ----------------------------------
# 그리기
# ----------------------------------

plt.figure(figsize=(8, 8))
colors = ['red', 'blue', 'green', 'purple', 'orange']

# fly_zone
fly_poly = Polygon(fly)
plot_poly(fly_poly, color='lightgray')

# NFZ
plot_poly(Polygon(nfz1), color='black')

# zones
for idx, z in enumerate(zones):
    plot_poly(z, color=colors[idx % len(colors)])

plt.gca().set_aspect('equal', adjustable='box')
plt.title("Scanline Split Visualization")
plt.show()
