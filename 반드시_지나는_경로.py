import osmnx as ox
import networkx as nx
from shapely.geometry import shape, Point
import folium
from collections import Counter
import openrouteservice

def find_mandatory_paths(lat, lon, api_key, minutes):
    location = [lon, lat]
    client = openrouteservice.Client(key=api_key)

    iso = client.isochrones(locations=[location], profile='foot-walking', range=[minutes * 60])
    poly = shape(iso['features'][0]['geometry'])

    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)

    subgraph_nodes = [n for n in G.nodes if poly.contains(Point(G.nodes[n]['x'], G.nodes[n]['y']))]
    SG = G.subgraph(subgraph_nodes).copy()

    # 작은 컴포넌트 제거
    largest_cc = max(nx.connected_components(SG.to_undirected()), key=len)
    SG = SG.subgraph(largest_cc).copy()

    # 중심성과 관절점 계산
    centrality = nx.betweenness_centrality(SG)
    points = [
        n for n in nx.articulation_points(SG)
        if centrality.get(n, 0) > 0.02
    ]

    m = folium.Map(location=[lat, lon], zoom_start=16)

    for node in points:
        folium.CircleMarker(
            location=(SG.nodes[node]['y'], SG.nodes[node]['x']),
            radius=5,
            fill=True,
            color='blue',
            fill_opacity=0.7
        ).add_to(m)

    folium.Marker(
        location=[lat, lon],
        popup='출발 지점',
        icon=folium.Icon(color='green')
    ).add_to(m)

    return m._repr_html_()
