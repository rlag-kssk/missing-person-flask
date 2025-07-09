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

def generate_voronoi_map(lat, lon, speed, weight, minutes):
    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)
    results = [simulate_once(G, start_node, speed, weight, minutes) for _ in range(500)]
    counter = Counter(results)

    m = folium.Map(location=[lat, lon], zoom_start=16)

    # 히트맵
    heat_data = [(G.nodes[n]['y'], G.nodes[n]['x'], c) for n, c in counter.items()]
    HeatMap(heat_data, radius=20).add_to(m)

    # 최빈 노드 표시
    if counter:
        most_common_node = counter.most_common(1)[0][0]
        folium.Marker(
            location=[G.nodes[most_common_node]['y'], G.nodes[most_common_node]['x']],
            popup="예상 최빈 위치",
            icon=folium.Icon(color="red", icon="glyphicon-map-marker")
        ).add_to(m)

    # KMeans로 대표 생성점 추출
    pos = np.array([[G.nodes[n]['x'], G.nodes[n]['y']] for n in counter])
    kmeans = KMeans(n_clusters=5, random_state=0).fit(pos)
    centers = kmeans.cluster_centers_

    # 보로노이 다이어그램
    vor = Voronoi(centers)
    for point in centers:
        folium.CircleMarker(
            location=(point[1], point[0]), radius=4, color="blue", fill=True
        ).add_to(m)

    for region in vor.regions:
        if not region or -1 in region: continue
        try:
            polygon = [vor.vertices[i] for i in region]
            poly = Polygon(polygon)
            if poly.is_valid:
                coords = [(y, x) for x, y in poly.exterior.coords]
                folium.PolyLine(coords, color="orange", weight=2, opacity=0.5).add_to(m)
        except: continue

    # 시작 지점 마커
    folium.Marker([lat, lon], popup="출발 지점", icon=folium.Icon(color="green")).add_to(m)

    return m._repr_html_()
