import os
from flask import Flask, jsonify, render_template_string, send_from_directory
import requests
import random
from datetime import datetime

app = Flask(__name__)

def fetch_parking_data():
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = """[out:json][timeout:30];
    (
      nwr["amenity"="parking"](41.1500,69.1000,41.4500,69.4500);
      nwr["amenity"~"cafe|bank|pharmacy|restaurant|fast_food|clinic|hospital"](41.1500,69.1000,41.4500,69.4500);
      nwr["shop"~"supermarket|convenience|clothes|mall"](41.1500,69.1000,41.4500,69.4500);
    );
    out center;
    """
    try:
        response = requests.post(overpass_url, data={'data': overpass_query}, timeout=20)
        data = response.json()
        points = []
        current_hour = datetime.now().hour
        for element in data.get('elements', []):
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lng = element.get('lon') or element.get('center', {}).get('lon')
            if not lat or not lng: continue
            tags = element.get('tags', {})
            is_lot = tags.get('amenity') == 'parking'
            name = tags.get('name')
            if not name:
                if is_lot: name = "Avtoturargoh"
                elif 'shop' in tags: name = "Do'kon oldi (Yo'l yuzi)"
                elif 'amenity' in tags:
                    am_type = tags['amenity']
                    if am_type == 'cafe': name = "Kafe oldi (Yo'l yuzi)"
                    elif am_type == 'bank': name = "Bank oldi (Yo'l yuzi)"
                    elif am_type == 'pharmacy': name = "Dorixona oldi (Yo'l yuzi)"
                    elif am_type == 'restaurant': name = "Restoran oldi (Yo'l yuzi)"
                    elif am_type == 'fast_food': name = "Fast-food oldi (Yo'l yuzi)"
                    elif am_type in ['clinic', 'hospital']: name = "Shifoxona oldi (Yo'l yuzi)"
                    else: name = "Bino oldi (Yo'l yuzi)"
                else:
                    name = "Yo'l yuzi parkovkasi"
            
            if 9 <= current_hour <= 18:
                prob = random.randint(10, 45)
            else:
                prob = random.randint(60, 95)
            
            points.append({
                "name": name,
                "lat": lat,
                "lng": lng,
                "type": "parking_lot" if is_lot else "street_parking",
                "price": "10,000 so'm/soat" if is_lot else "Bepul (Ko'cha yuzi)",
                "probability": f"{prob}%"
            })
        return points[:10000]
    except Exception as e:
        print("Xatolik:", e)
        return []

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <title>Aqlli Avtoturargoh | NVBS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1e3799">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.css" />
    <style>
        :root { --primary: #2563eb; --street: #10b981; --bg: #f8fafc; }
        body { margin: 0; display: flex; height: 100vh; font-family: 'Inter', system-ui, sans-serif; background: var(--bg); }
        
        #sidebar { width: 380px; background: white; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; z-index: 1000; box-shadow: 4px 0 10px rgba(0,0,0,0.05); }
        .header { padding: 20px; border-bottom: 1px solid #f1f5f9; background: #fff; }
        
        .search-box { width: 100%; padding: 12px 15px; border-radius: 8px; border: 1px solid #cbd5e1; background: #f8fafc; margin-top: 15px; font-size: 14px; outline: none; transition: 0.2s; box-sizing: border-box; }
        .search-box:focus { border-color: var(--primary); background: #fff; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        
        #list-container { flex: 1; overflow-y: auto; padding: 15px; }
        #map { flex: 1; }

        .card { background: white; border: 1px solid #f1f5f9; border-radius: 12px; padding: 15px; margin-bottom: 12px; cursor: pointer; transition: 0.2s; border-left: 6px solid #cbd5e1; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: var(--primary); }
        .card.lot { border-left-color: var(--primary); }
        .card.street { border-left-color: var(--street); }

        .type-badge { font-size: 10px; font-weight: 800; padding: 4px 8px; border-radius: 6px; text-transform: uppercase; margin-bottom: 8px; display: inline-block; }
        .lot-badge { background: #dbeafe; color: #1e40af; }
        .street-badge { background: #d1fae5; color: #065f46; }

        .prob-bar-bg { width: 100%; height: 6px; background: #f1f5f9; border-radius: 3px; margin-top: 10px; overflow: hidden; }
        .prob-bar-fill { height: 100%; transition: 0.3s; }

        .info-row { display: flex; justify-content: space-between; font-size: 13px; margin-top: 8px; color: #64748b; }
        .price-tag { color: #334155; font-weight: 600; }
        .radius-info { font-size: 12px; color: #ef4444; font-weight: 600; margin-top: 5px; display: none; }
        
        @media (max-width: 768px) {
            body { flex-direction: column-reverse; }
            #sidebar { width: 100%; height: 45%; border-right: none; border-top: 1px solid #e2e8f0; }
            #map { height: 55%; }
        }
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="header">
            <h2 style="margin:0; font-size:22px; color:#1e293b;">Aqlli Avtoturargoh</h2>
            <p style="margin:5px 0 0; font-size:14px; color:#64748b;">Toshkent Navigatsiya Tizimi</p>
            
            <input type="text" id="searchInput" class="search-box" placeholder="Manzilni qidiring (Masalan: Tatu)...">
            <div id="radiusInfo" class="radius-info">Faqat 600 metr radiusdagi joylar ko'rsatilmoqda</div>
        </div>
        <div id="list-container">
            <p id="status" style="color: #64748b; font-weight: 500;">Butun Toshkent bo'ylab joylar izlanmoqda (Biroz kuting)...</p>
        </div>
    </div>
    <div id="map"></div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet-routing-machine/dist/leaflet-routing-machine.js"></script>
    <script>
        var map = L.map('map', {zoomControl: false}).setView([41.3111, 69.2797], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

        var userMarker = L.marker([41.3111, 69.2797], {draggable: true}).addTo(map)
            .bindPopup("<b>Sizning joylashuvingiz</b>").openPopup();

        var routingControl = null;
        var markerGroup = L.layerGroup().addTo(map); 
        var searchCircle = null; 
        var allParkingData = []; 

        function drawRoute(lat, lng) {
            if (routingControl) map.removeControl(routingControl);
            routingControl = L.Routing.control({
                waypoints: [L.latLng(userMarker.getLatLng()), L.latLng(lat, lng)],
                lineOptions: { styles: [{color: '#2563eb', weight: 6, opacity: 0.8}] },
                addWaypoints: false,
                draggableWaypoints: false,
                show: false 
            }).addTo(map);
        }

        map.on('click', (e) => drawRoute(e.latlng.lat, e.latlng.lng));

        fetch('/api/data')
            .then(res => res.json())
            .then(data => {
                allParkingData = data;
                renderData(allParkingData); 
            })
            .catch(err => {
                document.getElementById('status').innerText = "Ma'lumotlarni yuklashda xatolik yuz berdi.";
            });

        function renderData(dataToRender) {
            const list = document.getElementById('list-container');
            list.innerHTML = '';
            markerGroup.clearLayers(); 
            
            if(dataToRender.length === 0) {
                list.innerHTML = '<p style="color: #ef4444; font-weight: 500;">Bu atrofda turargoh topilmadi.</p>';
                return;
            }

            dataToRender.forEach(p => {
                const isLot = p.type === 'parking_lot';
                const color = isLot ? '#2563eb' : '#10b981';
                
                var marker = L.circleMarker([p.lat, p.lng], {
                    radius: 8, fillColor: color, color: '#fff', weight: 2, fillOpacity: 0.9
                }).addTo(markerGroup);

                marker.bindPopup(`<b>${p.name}</b><br>Bo'sh joy: ${p.probability}`);
                marker.on('click', () => drawRoute(p.lat, p.lng));

                const card = document.createElement('div');
                card.className = `card ${isLot ? 'lot' : 'street'}`;
                const probVal = parseInt(p.probability);
                const probColor = probVal > 70 ? '#10b981' : (probVal > 30 ? '#f59e0b' : '#ef4444');

                card.innerHTML = `
                    <span class="type-badge ${isLot ? 'lot-badge' : 'street-badge'}">${isLot ? 'Maxsus turargoh' : "Yo'l yuzi"}</span>
                    <div style="font-weight:700; color:#1e293b; font-size:16px;">${p.name}</div>
                    <div class="info-row">
                        <span class="price-tag">${p.price}</span>
                        <span>Bo'sh joy: <b style="color:${probColor}">${p.probability}</b></span>
                    </div>
                    <div class="prob-bar-bg">
                        <div class="prob-bar-fill" style="width:${p.probability}; background:${probColor}"></div>
                    </div>
                `;
                card.onclick = () => {
                    map.flyTo([p.lat, p.lng], 16);
                    drawRoute(p.lat, p.lng);
                };
                list.appendChild(card);
            });
        }

        const searchInput = document.getElementById('searchInput');
        const radiusInfo = document.getElementById('radiusInfo');

        searchInput.addEventListener('input', (e) => {
            if (e.target.value.trim() === '') {
                if (searchCircle) map.removeLayer(searchCircle);
                radiusInfo.style.display = 'none';
                renderData(allParkingData);
                map.flyTo([41.3111, 69.2797], 13); 
            }
        });

        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = searchInput.value.trim();
                if (query === '') return;

                document.getElementById('list-container').innerHTML = '<p style="color: #64748b;">Manzil qidirilmoqda...</p>';

                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ', Toshkent')}`)
                    .then(res => res.json())
                    .then(results => {
                        if (results.length > 0) {
                            const targetLat = parseFloat(results[0].lat);
                            const targetLng = parseFloat(results[0].lon);
                            const targetCenter = L.latLng(targetLat, targetLng);

                            map.flyTo(targetCenter, 15);

                            if (searchCircle) map.removeLayer(searchCircle);
                            searchCircle = L.circle(targetCenter, {
                                radius: 600,
                                color: '#ef4444',
                                fillColor: '#ef4444',
                                fillOpacity: 0.1,
                                weight: 2
                            }).addTo(map);

                            const filteredPlaces = allParkingData.filter(p => {
                                const parkingLatLng = L.latLng(p.lat, p.lng);
                                return targetCenter.distanceTo(parkingLatLng) <= 600;
                            });

                            radiusInfo.style.display = 'block';
                            renderData(filteredPlaces);
                        } else {
                            document.getElementById('list-container').innerHTML = '<p style="color: #ef4444; font-weight: 500;">Manzil topilmadi. Yana urinib ko\\'ring.</p>';
                        }
                    })
                    .catch(err => {
                        document.getElementById('list-container').innerHTML = '<p style="color: #ef4444;">Xatolik yuz berdi.</p>';
                    });
            }
        });

        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('data:text/javascript;base64,c2VsZi5hZGRFdmVudExpc3RlbmVyKCdmZXRjaCcsIGZ1bmN0aW9uKGV2ZW50KSB7fSk7');
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    return jsonify(fetch_parking_data())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
