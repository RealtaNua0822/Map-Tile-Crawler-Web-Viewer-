#!/usr/bin/env python3
"""
server.py

Flask Web 服务器，发布瓦片服务。
- 从与本脚本同目录的 out/ 读取瓦片（结构：out/{z}/{x}/{y}.xxx）
- 提供 /tiles/{z}/{x}/{y}.png 接口（CORS 支持）
- 首页自动估算瓦片覆盖范围并居中显示
"""

from flask import Flask, send_file, render_template_string, jsonify, make_response
from flask_cors import CORS
from pathlib import Path
import os
import logging
import math

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 瓦片目录：与 server.py 同目录下的 out/
TILES_DIR = Path(__file__).resolve().parent / 'out'
MAPS_DIR = Path(__file__).resolve().parent / 'map'  # 保留但未使用

PREFERRED_EXTS = ['png', 'webp', 'jpg', 'jpeg']


def tile_xy_to_latlon(x, y, z):
    """将瓦片坐标 (x, y, z) 转换为经纬度 (lat, lon)"""
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


def estimate_bbox_from_tiles():
    """
    扫描 TILES_DIR，估算已有瓦片的大致地理范围。
    返回 (min_lon, min_lat, max_lon, max_lat, zoom_used) 或 None
    """
    try:
        z_dirs = [d for d in TILES_DIR.iterdir() if d.is_dir() and d.name.isdigit()]
        if not z_dirs:
            return None

        # 选择最高 zoom（通常细节最丰富）
        z_dir = max(z_dirs, key=lambda d: int(d.name))
        z = int(z_dir.name)

        all_x = []
        all_y = []

        for x_dir in z_dir.iterdir():
            if x_dir.is_dir() and x_dir.name.isdigit():
                x = int(x_dir.name)
                all_x.append(x)
                for y_file in x_dir.glob('*.*'):
                    if y_file.stem.isdigit():
                        y = int(y_file.stem)
                        all_y.append(y)

        if not all_x or not all_y:
            return None

        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)

        # 注意：Slippy map 的 y 增加方向是向下，所以：
        # 左上角 = (x_min, y_min) → 对应 (max_lat, min_lon)
        # 右下角 = (x_max, y_max) → 对应 (min_lat, max_lon)
        lat_ne, lon_nw = tile_xy_to_latlon(x_min, y_min, z)   # 左上
        lat_sw, lon_se = tile_xy_to_latlon(x_max, y_max, z)   # 右下

        min_lat = min(lat_sw, lat_ne)
        max_lat = max(lat_sw, lat_ne)
        min_lon = min(lon_nw, lon_se)
        max_lon = max(lon_nw, lon_se)

        return min_lon, min_lat, max_lon, max_lat, z

    except Exception as e:
        logger.warning(f"估算瓦片范围失败: {e}")
        return None


def find_tile_file(z: int, x: int, y: int):
    """查找瓦片文件，优先返回 PNG"""
    tile_dir = TILES_DIR / str(z) / str(x)
    tile_base = tile_dir / str(y)

    # 优先 PNG
    png_path = tile_base.with_suffix('.png')
    if png_path.exists() and png_path.is_file():
        return png_path

    # 再试其他格式
    for ext in ['webp', 'jpg', 'jpeg']:
        tile_path = tile_base.with_suffix('.' + ext)
        if tile_path.exists() and tile_path.is_file():
            return tile_path

    # fallback: 任意扩展名
    if tile_dir.exists():
        for f in tile_dir.glob(f'{y}.*'):
            if f.is_file():
                return f

    return None


@app.route('/')
def index():
    bbox_info = estimate_bbox_from_tiles()

    if bbox_info:
        min_lon, min_lat, max_lon, max_lat, z = bbox_info
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        init_zoom = max(7, min(12, z - 1))  # 初始缩放略小于数据 zoom
        coverage_text = f"Zoom {z} | Lon: {min_lon:.4f}~{max_lon:.4f} | Lat: {min_lat:.4f}~{max_lat:.4f}"
    else:
        # fallback
        center_lat, center_lon, init_zoom = 0.0, 0.0, 2
        coverage_text = "未检测到瓦片（请检查 out/ 目录）"

    html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>瓦片地图服务</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ margin: 0; padding: 0; }}
        body, html, #map {{ width: 100%; height: 100%; font-family: Arial, sans-serif; }}
        #info {{ position: absolute; top: 10px; right: 10px; background: white; padding: 15px;
                border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2); z-index: 400;
                font-size: 13px; }}
        #info h3 {{ margin-bottom: 10px; }}
        .info-row {{ margin: 5px 0; }}
        .label {{ font-weight: bold; color: #333; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="info">
        <h3>瓦片地图服务</h3>
        <div class="info-row">
            <span class="label">缩放级别 (z):</span> <span id="zoom">{init_zoom}</span>
        </div>
        <div class="info-row">
            <span class="label">瓦片坐标:</span> <span id="tile">-</span>
        </div>
        <div class="info-row">
            <span class="label">中心坐标:</span> <span id="center">-</span>
        </div>
        <div class="info-row">
            <span class="label">覆盖范围:</span> {coverage_text}
        </div>
    </div>

    <script>
        const map = L.map('map').setView([{center_lat}, {center_lon}], {init_zoom});

        const tileLayer = L.tileLayer('/tiles/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '本地瓦片服务',
            minZoom: 7,
            maxZoom: 14,
            errorTileUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
        }}).addTo(map);

        map.on('zoomend', function() {{
            document.getElementById('zoom').textContent = map.getZoom();
        }});

        map.on('mousemove', function(e) {{
            const z = map.getZoom();
            const x = Math.floor((e.latlng.lng + 180) / 360 * Math.pow(2, z));
            const y = Math.floor((1 - Math.log(Math.tan(Math.PI * e.latlng.lat / 180) + 1 / Math.cos(Math.PI * e.latlng.lat / 180)) / Math.PI) / 2 * Math.pow(2, z));
            
            document.getElementById('tile').textContent = `(${{x}}, ${{y}}, ${{z}})`;
            document.getElementById('center').textContent = 
                `${{e.latlng.lat.toFixed(4)}}°, ${{e.latlng.lng.toFixed(4)}}°`;
        }});
    </script>
</body>
</html>
    '''
    return render_template_string(html)


@app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
def get_tile(z, x, y):
    tile_path = find_tile_file(z, x, y)

    if tile_path is None:
        logger.debug(f"Tile not found: {z}/{x}/{y}")
        from PIL import Image
        import io
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        resp = make_response(send_file(img_io, mimetype='image/png'))
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp

    try:
        logger.info(f"Serving tile: {z}/{x}/{y} from {tile_path}")

        if tile_path.suffix.lower() == '.png':
            resp = make_response(send_file(str(tile_path), mimetype='image/png'))
            resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp

        from PIL import Image
        import io
        with Image.open(str(tile_path)) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            resp = make_response(send_file(img_io, mimetype='image/png'))
            resp.headers['Cache-Control'] = 'public, max-age=86400'
            return resp

    except Exception as e:
        logger.error(f"Error reading/converting tile {z}/{x}/{y} ({tile_path}): {e}", exc_info=True)
        from PIL import Image
        import io
        img = Image.new('RGBA', (256, 256), (255, 0, 0, 64))
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        resp = make_response(send_file(img_io, mimetype='image/png'))
        resp.headers['Cache-Control'] = 'public, max-age=0'
        return resp


@app.route('/api/tile-stats')
def tile_stats():
    stats = {}
    if TILES_DIR.exists():
        for z_dir in sorted(TILES_DIR.glob('*/')):
            if z_dir.is_dir() and z_dir.name.isdigit():
                count = len(list(z_dir.glob('*/*')))
                stats[z_dir.name] = count
    return jsonify(stats)


if __name__ == '__main__':
    print("=" * 60)
    print("🌍 瓦片地图服务已启动")
    print("=" * 60)
    print(f"📍 瓦片目录: {TILES_DIR.resolve()}")
    print("🌐 访问地址：http://localhost:5000")
    print("🗺️  瓦片接口：/tiles/{z}/{x}/{y}.png")
    print("📊 统计接口：/api/tile-stats")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)