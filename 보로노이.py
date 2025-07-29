def generate_voronoi_map(lat, lon, speed, weight, minutes):
    import osmnx as ox
    import networkx as nx
    import numpy as np
    import folium
    from folium.plugins import HeatMap
    from shapely.geometry import Polygon
    from shapely.ops import transform
    from sklearn.cluster import KMeans
    from scipy.spatial import Voronoi
    from collections import Counter
    from pyproj import Transformer
    import random

    G = ox.graph_from_point((lat, lon), dist=1000, network_type='walk')
    G_proj = ox.project_graph(G)
    node_positions_proj = {n: (d['x'], d['y']) for n, d in G_proj.nodes(data=True)}

    def simulate_once(G, start_node, speed, weight, total_time_min, step_time=30):
        adjusted_time = total_time_min * (speed / 1.0)
        total_steps = int((adjusted_time * 60) // step_time)
        current = start_node
        for _ in range(total_steps):
            neighbors = list(G.neighbors(current))
            if not neighbors or random.random() < 0.5:
                continue
            probs = []
            for v in neighbors:
                data = list(G.get_edge_data(current, v).values())[0]
                hwy = data.get('highway', 'residential')
                if isinstance(hwy, list):
                    hwy = hwy[0]
                probs.append(weight.get(hwy, 1))
            probs = np.array(probs, dtype=float)
            probs /= probs.sum()
            current = np.random.choice(neighbors, p=probs)
        return current

    start_node = ox.distance.nearest_nodes(G, lon, lat)
    sim_nodes = [simulate_once(G_proj, start_node, speed, weight, minutes) for _ in range(500)]
    counter = Counter(sim_nodes)

    coords = np.array([node_positions_proj[n] for n in sim_nodes])
    k = min(5, len(np.unique(coords, axis=0)))
    if k < 3:
        return "<p>데이터가 부족하여 보로노이 영역을 생성할 수 없습니다.</p>"

    kmeans = KMeans(n_clusters=k, random_state=0).fit(coords)
    generator_points = kmeans.cluster_centers_
    vor = Voronoi(generator_points)

    def voronoi_finite_polygons_2d(vor, radius=3000):
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

    regions, vertices = voronoi_finite_polygons_2d(vor)
    transformer = Transformer.from_crs(G_proj.graph['crs'], 'EPSG:4326', always_xy=True)
    m = folium.Map(location=[lat, lon], zoom_start=16)

    heat_data = []
    for node, count in counter.items():
        x, y = node_positions_proj[node]
        lon_, lat_ = transformer.transform(x, y)
        heat_data.append([lat_, lon_, count])
    HeatMap(heat_data, radius=25, blur=18).add_to(m)

    for region in regions:
        polygon = vertices[region]
        if len(polygon) < 3:
            continue
        try:
            poly = Polygon(polygon)
            poly_latlon = transform(transformer.transform, poly)
            coords = [(lat_, lon_) for lon_, lat_ in poly_latlon.exterior.coords]
            folium.Polygon(locations=coords, color='orange', weight=3, fill=False).add_to(m)
        except:
            continue

    for pt in generator_points:
        lon_, lat_ = transformer.transform(*pt)
        folium.CircleMarker(location=[lat_, lon_], radius=5, color='blue', fill=True, fill_opacity=0.8).add_to(m)

    folium.Marker(location=[lat, lon], popup="Start", icon=folium.Icon(color='green')).add_to(m)

    return m._repr_html_()
