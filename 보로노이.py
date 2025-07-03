import osmnx as ox
import networkx as nx
import numpy as np
import random
from shapely.geometry import Polygon, Point
from shapely.ops import voronoi_diagram
import folium
from folium.plugins import HeatMap
from collections import Counter
from scipy.spatial import Voronoi
import geopandas as gpd

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
            if isinstance(highway, list):
                highway = highway[0]
            probs.append(weight.get(highway, 1))

        probs = np.array(probs, dtype=float)
        probs /= probs.sum()
        current = random.choices(nbrs, probs)[0]

    return current

def generate_voronoi_map(lat, lon, speed, weight, minutes):
    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)

    # 시뮬레이션
    nodes = [simulate_once(G, start_node, speed, weight, minutes) for _ in range(500)]
    freq = Counter(nodes)

    # 생성점 좌표 추출
    points = np.array([[G.nodes[n]['x'], G.nodes[n]['y']] for n in freq.keys()])

    # 보로노이 다이어그램 계산
    vor = Voronoi(points)
    m = folium.Map(location=[lat, lon], zoom_start=16)

    # 히트맵 추가
    heat_data = [(G.nodes[n]['y'], G.nodes[n]['x'], c) for n, c in freq.items()]
    HeatMap(heat_data, radius=20).add_to(m)

    # 생성점 마커
    for x, y in points:
        folium.CircleMarker(location=(y, x), radius=3, color='blue', fill=True, fill_opacity=1).add_to(m)

    # 보로노이 경계선 시각화
    for region in vor.regions:
        if not region or -1 in region: continue
        try:
            polygon = [vor.vertices[i] for i in region]
            poly = Polygon(polygon)
            if poly.is_valid:
                coords = [(y, x) for x, y in poly.exterior.coords]
                folium.PolyLine(coords, color='orange', weight=2, opacity=0.6).add_to(m)
        except: continue

    # 출발 지점 마커
    folium.Marker([lat, lon], popup='출발 지점', icon=folium.Icon(color='green')).add_to(m)

    return m._repr_html_()
