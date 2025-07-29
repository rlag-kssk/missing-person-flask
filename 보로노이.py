import osmnx as ox
import networkx as nx
import numpy as np
import random
from shapely.geometry import Polygon
from scipy.spatial import Voronoi
from sklearn.cluster import KMeans
import folium
from folium.plugins import HeatMap
from collections import Counter

# 무한한 보로노이 영역 자르는 함수
def voronoi_finite_polygons_2d(vor, radius=1000):
    new_regions = []
    new_vertices = vor.vertices.tolist()
    center = vor.points.mean(axis=0)
    all_ridges = {}

    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]
        if -1 not in vertices:
            new_regions.append(vertices)
            continue

        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v != -1]
        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0 and v2 >= 0:
                continue
            t = vor.points[p2] - vor.points[p1]
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius
            new_vertices.append(far_point.tolist())
            new_region.append(len(new_vertices) - 1)
        new_regions.append(new_region)

    return new_regions, np.array(new_vertices)


# 시뮬레이션 1회
def simulate_once(G, start_node, speed, weight, total_time_min, step_time=30):
    adjusted_time = total_time_min * (speed / 1.0)
    total_steps = int((adjusted_time * 60) // step_time)
    current = start_node
    for _ in range(total_steps):
        nbrs = list(G.neighbors(current))
        if not nbrs: break
        if random.random() < 0.5: continue
        probs = []
        for v in nbrs:
            data = list(G.get_edge_data(current, v).values())[0]
            highway = data.get('highway', 'residential')
            if isinstance(highway, list): highway = highway[0]
            probs.append(weight.get(highway, 1))
        probs = np.array(probs, dtype=float)
        probs /= probs.sum()
        current = random.choices(nbrs, probs)[0]
    return current


# 골든타임 추정 함수
def estimate_golden_time(G, start_node, speed, weight, capacity_threshold, max_minutes=180, step=10):
    for minutes in range(step, max_minutes + 1, step):
        reached = set()
        for _ in range(300):
            node = simulate_once(G, start_node, speed, weight, minutes)
            reached.add(node)
        if len(reached) > capacity_threshold:
            return minutes
    return None


# 메인 지도 생성 함수
def generate_voronoi_map(lat, lon, speed, weight, minutes, searcher_count=3, capacity_per_searcher=30):
    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)

    # 골든타임 추정
    K = searcher_count * capacity_per_searcher
    golden_time = estimate_golden_time(G, start_node, speed, weight, K) or minutes

    # 시뮬레이션
    results = [simulate_once(G, start_node, speed, weight, golden_time) for _ in range(500)]
    counter = Counter(results)

    m = folium.Map(location=[lat, lon], zoom_start=16)

    # 히트맵
    heat_data = [(G.nodes[n]['y'], G.nodes[n]['x'], c) for n, c in counter.items()]
    HeatMap(heat_data, radius=20).add_to(m)

    # 최빈 위치 표시
    if counter:
        most_common_node = counter.most_common(1)[0][0]
        folium.Marker(
            location=[G.nodes[most_common_node]['y'], G.nodes[most_common_node]['x']],
            popup="예상 최빈 위치",
            icon=folium.Icon(color="red")
        ).add_to(m)

    # 골든타임 정보 추가
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=f"""<div style="font-size: 14px; color: black; font-weight: bold">
                        골든타임 추정: {golden_time}분
                     </div>"""
        )
    ).add_to(m)

    # KMeans 클러스터링 + 보로노이
    pos = np.array([[G.nodes[n]['x'], G.nodes[n]['y']] for n in counter])
    pos = np.unique(pos, axis=0)
    k = min(5, len(pos))

    if k >= 3:
        kmeans = KMeans(n_clusters=k, random_state=0).fit(pos)
        centers = kmeans.cluster_centers_
        vor = Voronoi(centers)
        regions, vertices = voronoi_finite_polygons_2d(vor)

        for region in regions:
            polygon = vertices[region]
            poly = Polygon(polygon)
            if poly.is_valid:
                coords = [(y, x) for x, y in poly.exterior.coords]
                folium.PolyLine(coords, color="orange", weight=2, opacity=0.6).add_to(m)

        for point in centers:
            folium.CircleMarker(
                location=(point[1], point[0]), radius=4, color="blue", fill=True
            ).add_to(m)

    # 출발 지점
    folium.Marker([lat, lon], popup="출발 지점", icon=folium.Icon(color="green")).add_to(m)

    return m._repr_html_()
