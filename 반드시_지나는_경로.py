import osmnx as ox
import networkx as nx
from shapely.geometry import shape, Point
import folium
from collections import Counter
import openrouteservice

def find_mandatory_paths(lat, lon, api_key, minutes):
    location = [lon, lat]
    client = openrouteservice.Client(key=api_key)

    # 1. 이소크론 영역 가져오기
    iso = client.isochrones(locations=[location], profile='foot-walking', range=[minutes * 60])
    poly = shape(iso['features'][0]['geometry'])

    # 2. 그래프 생성
    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)

    # 3. 다각형 안의 노드 선택
    reachable_nodes = [n for n in G.nodes if poly.contains(Point(G.nodes[n]['x'], G.nodes[n]['y']))]

    # 4. 최단경로 계산
    paths = []
    for node in reachable_nodes:
        try:
            path = nx.shortest_path(G, start_node, node)
            paths.append(path)
        except: continue

    # 5. 각 노드가 얼마나 많이 등장했는지 계산
    counter = Counter()
    for path in paths:
        counter.update(path)

    # 6. 지도에 시각화
    m = folium.Map(location=[lat, lon], zoom_start=16)
    for node, count in counter.items():
        folium.CircleMarker(
            location=(G.nodes[node]['y'], G.nodes[node]['x']),
            radius=3,
            fill=True,
            fill_color='red',
            fill_opacity=min(0.1 + count / max(counter.values()), 1.0)
        ).add_to(m)

    folium.Marker(
        location=[lat, lon],
        popup='출발 지점',
        icon=folium.Icon(color='green')
    ).add_to(m)

    return m._repr_html_()
