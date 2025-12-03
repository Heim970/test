import numpy as np
from lf_core import (
    skeletonize_mask, skeleton_to_graph,
    find_trunk_longest_path, extract_branches,
    simplify_route, split_routes_for_agents,
    build_drone_routes_geojson,
)

# 1) mask 준비 (0/1 or 0/255)
mask = np.load("some_binary_mask.npy")

# 2) skeleton & graph
skel = skeletonize_mask(mask)
G = skeleton_to_graph(skel)

# 3) trunk & branches (pixel 좌표)
trunk = find_trunk_longest_path(G)
branches = extract_branches(G, trunk)

# 4) TODO: world 좌표 변환
def px_to_world(node_list):
    # ex: (row, col) -> (lon, lat) or (x, y)
    ...
    return coords

trunk_w = px_to_world(trunk)
branches_w = [px_to_world(b) for b in branches]

# 5) 스무딩
trunk_s = simplify_route(trunk_w, tol=2e-5)
branches_s = [simplify_route(b, tol=2e-5) for b in branches_w]

routes = [trunk_s] + branches_s

# 6) N 드론으로 분배
drone_no = 3
drone_routes = split_routes_for_agents(routes, drone_no)

# 7) GeoJSON
geojson = build_drone_routes_geojson(drone_routes)
