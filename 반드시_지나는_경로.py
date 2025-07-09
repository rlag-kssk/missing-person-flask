import osmnx as ox
import networkx as nx
from shapely.geometry import shape, Point
import folium
import openrouteservice

def find_mandatory_paths(lat, lon, api_key, minutes):
    location = [lon, lat]
    client = openrouteservice.Client(key=api_key)

    iso = client.isochrones(locations=[location], profile='foot-walking', range=[minutes * 60])
    poly = shape(iso['features'][0]['geometry'])

    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)

    # 범위 내 노드 필터링
    sub_nodes = [n for n in G.nodes if poly.contains(Point(G.nodes[n]['x'], G.nodes[n]['y']))]
    SG = G.subgraph(sub_nodes).copy()

    # 가장 큰 연결 요소만 사용
    largest_cc = max(nx.connected_components(SG.to_undirected()), key=len)
    SG = SG.subgraph(largest_cc).copy()

    # 중심성 계산
    centrality = nx.betweenness_centrality(SG)

    # 관절점 필터링 (무방향 그래프 변환)
    UG = SG.to_undirected()
    important_nodes = [
        n for n in nx.articulation_points(UG)
        if centrality.get(n, 0) > 0.02
    ]

    # 지도 시각화
    m = folium.Map(location=[lat, lon], zoom_start=16)

    for node in important_nodes:
        folium.CircleMarker(
            location=(SG.nodes[node]['y'], SG.nodes[node]['x']),
            radius=5,
            color='blue',
            fill=True,
            fill_opacity=0.7
        ).add_to(m)

    folium.Marker(
        location=[lat, lon],
        popup='출발 지점',
        icon=folium.Icon(color='green')
    ).add_to(m)

    return m._repr_html_()
