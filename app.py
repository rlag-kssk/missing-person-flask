from flask import Flask, render_template, request, session, redirect, url_for
import osmnx as ox
import networkx as nx
import folium
from folium.plugins import HeatMap
from shapely.geometry import shape, Point
from collections import Counter
import random
import numpy as np
import openrouteservice

from 보로노이 import generate_voronoi_map
from 반드시_지나는_경로 import find_mandatory_paths

app = Flask(__name__)
app.secret_key = 'missing_secret'

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

@app.route('/')
def base_info():
    return render_template('base_info.html')

@app.route('/submit_info', methods=['POST'])
def submit_info():
    session['gender'] = request.form['gender']
    session['age'] = request.form['age']
    session['lat'] = float(request.form['lat'])
    session['lon'] = float(request.form['lon'])
    session['time'] = int(request.form['time'])
    session['preference'] = request.form['preference']
    return redirect(url_for('choose_function'))

@app.route('/choose_function')
def choose_function():
    return render_template('choose_function.html')

@app.route('/simulate')
def simulate():
    gender = session['gender']
    age = session['age']
    lat = session['lat']
    lon = session['lon']
    minutes = session['time']
    preference = session['preference']
    speed = get_speed(gender, age)
    weight = get_weight(preference)
    map_html = generate_voronoi_map(lat, lon, speed, weight, minutes)
    return render_template('simulate_result.html', map_html=map_html)

@app.route('/mandatory_input')
def mandatory_input():
    return render_template('mandatory_input.html')

@app.route('/mandatory_result', methods=['POST'])
def mandatory_result():
    lat = session['lat']
    lon = session['lon']
    minutes = session['time']
    api_key = request.form['api_key']
    if not api_key:
        return 'API 키가 필요합니다.', 400
    map_html = find_mandatory_paths(lat, lon, api_key, minutes)
    return render_template('mandatory_result.html', map_html=map_html)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
