
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
    reachable_nodes = [n for n in G.nodes if poly.contains(Point(G.nodes[n]['x'], G.nodes[n]['y']))]
    paths = []
    for node in reachable_nodes:
        try:
            path = nx.shortest_path(G, start_node, node)
            paths.append(path)
        except: continue
    counter = Counter()
    for path in paths:
        counter.update(path)
    m = folium.Map(location=[lat, lon], zoom_start=16)
    for node, count in counter.items():
        folium.CircleMarker(
            location=(G.nodes[node]['y'], G.nodes[node]['x']),
            radius=3,
            fill=True,
            fill_color='red',
            fill_opacity=min(0.1 + count / max(counter.values()), 1.0)
        ).add_to(m)
    folium.Marker(location=[lat, lon], popup='출발 지점', icon=folium.Icon(color='green')).add_to(m)
    return m._repr_html_()
