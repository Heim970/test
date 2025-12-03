# lf_core.py
"""
Line Following core:
- binary mask -> skeleton -> pixel graph
- longest path = trunk
- DFS-based branch extraction
- route simplification
- route splitting for N drones
- drone-route GeoJSON builder
"""

import numpy as np
import cv2
import networkx as nx
from shapely.geometry import LineString


# ---------------- Skeleton & Graph ----------------

def skeletonize_mask(mask: np.ndarray) -> np.ndarray:
    """
    mask: 2D array, non-zero = road region
    return: 0/1 skeleton
    """
    # ensure uint8 0/255
    bin_img = (mask > 0).astype(np.uint8) * 255
    skel = cv2.ximgproc.thinning(bin_img, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    return (skel > 0).astype(np.uint8)


def skeleton_to_graph(skel: np.ndarray, connectivity: int = 8) -> nx.Graph:
    """
    skeleton에서 픽셀 그래프 생성.
    node = (row, col)
    """
    h, w = skel.shape
    G = nx.Graph()

    if connectivity == 4:
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    else:
        dirs = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1),
        ]

    # add nodes
    ys, xs = np.where(skel > 0)
    for y, x in zip(ys, xs):
        G.add_node((y, x))

    # add edges
    for y, x in zip(ys, xs):
        for dy, dx in dirs:
            ny, nx_ = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx_ < w and skel[ny, nx_] > 0:
                G.add_edge((y, x), (ny, nx_))

    return G


# ---------------- Trunk & Branch ----------------

def _dist(a, b):
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2) ** 0.5


def _bridge_endpoints(G: nx.Graph, max_dist: float = 2.5):
    """
    서로 가까운 endpoint끼리 bridge edge 추가해서
    skeleton의 작은 단절을 메꾼다.
    """
    endpoints = [n for n in G.nodes if G.degree(n) == 1]
    n = len(endpoints)
    for i in range(n):
        a = endpoints[i]
        for j in range(i + 1, n):
            b = endpoints[j]
            if _dist(a, b) <= max_dist and not G.has_edge(a, b):
                G.add_edge(a, b)


def find_trunk_longest_path(G: nx.Graph):
    """
    endpoint 간 최장 path를 trunk로 사용.
    """
    G = G.copy()
    _bridge_endpoints(G, max_dist=2.5)

    endpoints = [n for n in G.nodes if G.degree(n) == 1]
    if not endpoints:
        # fallback: 임의 노드 기준 최장 path
        nodes = list(G.nodes)
        if not nodes:
            return []
        s = nodes[0]
        lengths = nx.single_source_shortest_path_length(G, s)
        t = max(lengths, key=lambda k: lengths[k])
        return nx.shortest_path(G, s, t)

    best_path = None
    best_len = -1

    for s in endpoints:
        lengths = nx.single_source_shortest_path_length(G, s)
        t = max(lengths, key=lambda k: lengths[k])
        path = nx.shortest_path(G, s, t)
        if len(path) > best_len:
            best_len = len(path)
            best_path = path

    return best_path or []


def _branch_paths_from_root(G, root, trunk_set, visited_edges):
    paths = []
    stack = [(root, None, [root])]

    while stack:
        node, parent, path = stack.pop()

        neighbors = [
            nb for nb in G.neighbors(node)
            if nb != parent and nb not in trunk_set
        ]

        if not neighbors:
            paths.append(path)
            continue

        for nb in neighbors:
            e = tuple(sorted((node, nb)))
            if e in visited_edges:
                continue
            visited_edges.add(e)
            stack.append((nb, node, path + [nb]))

    return paths


def extract_branches(G: nx.Graph, trunk, min_len: int = 15):
    """
    trunk: list of nodes
    return: list of branch paths (각각 node list)
    """
    trunk_set = set(trunk)
    branches = []
    visited_edges = set()

    for v in trunk:
        for nb in G.neighbors(v):
            if nb in trunk_set:
                continue

            e0 = tuple(sorted((v, nb)))
            if e0 in visited_edges:
                continue
            visited_edges.add(e0)

            sub_paths = _branch_paths_from_root(G, nb, trunk_set, visited_edges)
            for p in sub_paths:
                full = [v] + p
                if len(full) >= min_len:
                    branches.append(full)

    return branches


# ---------------- Simplify & Split ----------------

def simplify_route(coords, tol: float):
    """
    coords: [(y, x) 또는 (lon, lat), ...]
    tol: shapely LineString.simplify tolerance
    """
    if len(coords) < 3:
        return coords
    line = LineString(coords)
    simp = line.simplify(tol, preserve_topology=False)
    if simp.is_empty or len(simp.coords) < 2:
        return coords
    return list(simp.coords)


def split_routes_for_agents(routes, n_agents: int):
    """
    routes: [coords, coords, ...]  # trunk + branches (이미 world 좌표)
    n_agents: agent/drone 수

    길이 기반 greedy 로드밸런싱.
    return: [[route_a1, route_a2, ...], [route_b1, ...], ...]
    """
    if not routes or n_agents <= 0:
        return []

    m = min(n_agents, len(routes))
    lengths = [
        LineString(r).length if len(r) >= 2 else 0.0
        for r in routes
    ]

    order = sorted(range(len(routes)), key=lambda i: lengths[i], reverse=True)

    buckets = [[] for _ in range(m)]
    bucket_len = [0.0] * m

    for idx in order:
        k = min(range(m), key=lambda j: bucket_len[j])
        buckets[k].append(routes[idx])
        bucket_len[k] += lengths[idx]

    return buckets


def join_routes_for_agent(route_list):
    """
    여러 route를 하나의 LineString 궤적으로 이어붙이기.
    route_list: [coords1, coords2, ...]
    """
    coords = []
    for seg in route_list:
        if not seg or len(seg) < 2:
            continue
        if not coords:
            coords.extend(seg)
            continue
        last = coords[-1]
        first = seg[0]
        if last != first:
            coords.append(first)
        coords.extend(seg[1:])
    return coords


# ---------------- GeoJSON helpers ----------------

def build_drone_routes_geojson(drone_routes):
    """
    drone_routes: [
        [coords1, coords2, ...],   # drone_id = 1
        [coordsX, ...],            # drone_id = 2
        ...
    ]
    각 드론은 LineString 하나로 묶어서 내보낸다.
    """
    features = []

    for idx, segs in enumerate(drone_routes, start=1):
        coords = join_routes_for_agent(segs)
        if len(coords) < 2:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "type": "drone_route",
                    "drone_id": idx,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }
