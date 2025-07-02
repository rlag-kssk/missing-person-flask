from flask import Flask, render_template, request
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import HeatMap
from shapely.geometry import shape, Point
from collections import Counter
import random
import numpy as np
import openrouteservice

app = Flask(__name__)

def get_speed(gender, age):
    speed = 1.0
    if gender == '남': speed += 0.2
    if age == '청소년': speed += 0.2
    elif age == '어린이': speed -= 0.2
    elif age == '노인': speed -= 0.3
    return speed

def get_weight(preference):
    if preference == '도로 선호':
        return {'residential': 5, 'footway': 3, 'path': 1, 'service': 2}
    else:
        return {'residential': 2, 'footway': 3, 'path': 5, 'service': 2}

def simulate_once(G, start_node, speed, weight, total_time_min, step_time=30):
    adjusted_time = total_time_min * (speed / 1.0)
    total_steps = int((adjusted_time * 60) // step_time)
    current = start_node
    for _ in range(total_steps):
        nbrs = list(G.neighbors(current))
        if not nbrs: break
        if random.random() < 0.5: continue
        probs = [weight.get(list(G.get_edge_data(current, v).values())[0].get('highway', 'residential'), 1) for v in nbrs]
        probs = np.array(probs, dtype=float)
        probs /= probs.sum()
        current = random.choices(nbrs, probs)[0]
    return current

def run_simulation(lat, lon, speed, weight, minutes):
    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    start_node = ox.distance.nearest_nodes(G, X=lon, Y=lat)
    nodes = [simulate_once(G, start_node, speed, weight, minutes) for _ in range(500)]
    freq = Counter(nodes)
    m = folium.Map(location=[lat, lon], zoom_start=16)
    heat_data = [(G.nodes[n]['y'], G.nodes[n]['x'], c) for n, c in freq.items()]
    HeatMap(heat_data, radius=20).add_to(m)
    folium.Marker([lat, lon], popup='출발 지점', icon=folium.Icon(color='green')).add_to(m)
    if freq:
        most_common = freq.most_common(1)[0][0]
        folium.Marker([G.nodes[most_common]['y'], G.nodes[most_common]['x']], popup='예상 위치', icon=folium.Icon(color='red')).add_to(m)
    return m._repr_html_()

def find_mandatory_path(lat, lon, api_key, minutes):
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
        folium.CircleMarker(location=(G.nodes[node]['y'], G.nodes[node]['x']), radius=3, fill=True, fill_color='red', fill_opacity=min(0.1 + count / max(counter.values()), 1.0)).add_to(m)
    folium.Marker(location=[lat, lon], popup='출발 지점', icon=folium.Icon(color='green')).add_to(m)
    return m._repr_html_()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def result():
    gender = request.form['gender']
    age = request.form['age']
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    time = int(request.form['time'])
    preference = request.form['preference']
    action = request.form['action']
    api_key = request.form.get('api_key')

    speed = get_speed(gender, age)
    weight = get_weight(preference)

    if action == 'simulate':
        map_html = run_simulation(lat, lon, speed, weight, time)
    elif action == 'mandatory' and api_key:
        map_html = find_mandatory_path(lat, lon, api_key, time)
    else:
        return 'API 키가 필요합니다.', 400

    return render_template('result.html', map_html=map_html)

if __name__ == '__main__':
    app.run(debug=True)
