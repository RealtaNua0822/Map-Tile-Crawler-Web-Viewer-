"""Simple map tile crawler

功能：
- 计算经纬度到 Slippy map 瓦片 (x, y, z) 的转换
- 根据 bbox 或 GeoJSON 多边形导出瓦片索引范围
- 并发下载瓦片并保存为 `out/{z}/{x}/{y}.png`

使用说明见仓库 README
"""
import math
import os
import time
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except Exception:
    raise RuntimeError('请先安装依赖：pip install -r requirements.txt')

try:
    from tqdm import tqdm
except Exception:
    # fallback simple progress
    tqdm = lambda x, **k: x


def latlon_to_tile_xy(lat_deg, lon_deg, z):
    """Convert latitude/longitude to slippy map tile x,y at zoom z.

    Returns integers (x, y).
    """
    lat_rad = math.radians(lat_deg)
    n = 2 ** z
    x = math.floor((lon_deg + 180.0) / 360.0 * n)
    y = math.floor((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    x = int(max(0, min(x, n - 1)))
    y = int(max(0, min(y, n - 1)))
    return x, y


def bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z):
    """Given bbox, return inclusive tile range: (xmin,xmax),(ymin,ymax)

    Note: bbox is min_lon, min_lat, max_lon, max_lat
    """
    n = 2 ** z
    # clamp input
    min_lon = max(-180.0, min(180.0, min_lon))
    max_lon = max(-180.0, min(180.0, max_lon))
    min_lat = max(-85.05112878, min(85.05112878, min_lat))
    max_lat = max(-85.05112878, min(85.05112878, max_lat))

    x_min = math.floor((min_lon + 180.0) / 360.0 * n)
    x_max = math.floor((max_lon + 180.0) / 360.0 * n)

    def lat_to_y(lat_deg):
        lat_rad = math.radians(lat_deg)
        return math.floor((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)

    y_min = lat_to_y(max_lat)  # northern edge -> smaller y
    y_max = lat_to_y(min_lat)  # southern edge -> larger y

    x_min = int(max(0, min(x_min, n - 1)))
    x_max = int(max(0, min(x_max, n - 1)))
    y_min = int(max(0, min(y_min, n - 1)))
    y_max = int(max(0, min(y_max, n - 1)))

    if x_max < x_min:
        x_min, x_max = x_max, x_min
    if y_max < y_min:
        y_min, y_max = y_max, y_min

    return (x_min, x_max), (y_min, y_max)


def geojson_bbox(geojson_path):
    """Compute bbox from GeoJSON (FeatureCollection, Feature, or Geometry).

    Returns (min_lon, min_lat, max_lon, max_lat).
    """
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def extract_coords(obj):
        if obj is None:
            return []
        t = obj.get('type')
        if t == 'FeatureCollection':
            coords = []
            for feat in obj.get('features', []) or []:
                coords += extract_coords(feat)
            return coords
        if t == 'Feature':
            return extract_coords(obj.get('geometry'))
        if t in ('Polygon', 'MultiPolygon', 'LineString', 'MultiLineString', 'Point', 'MultiPoint'):
            coords = []
            def recurse(c):
                if isinstance(c[0], (float, int)):
                    coords.append(tuple(c))
                else:
                    for e in c:
                        recurse(e)
            recurse(obj.get('coordinates', []))
            return coords
        if t == 'GeometryCollection':
            coords = []
            for g in obj.get('geometries', []) or []:
                coords += extract_coords(g)
            return coords
        return []

    coords = extract_coords(data)
    if not coords:
        raise ValueError('GeoJSON中没有找到坐标')
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lons), min(lats), max(lons), max(lats))


def tile_url(template, z, x, y):
    return template.format(z=z, x=x, y=y)


def _get_ext_from_url_or_content(url, resp=None):
    # try to get extension from URL
    path = url.split('?')[0]
    if '.' in path:
        ext = os.path.splitext(path)[1]
        if ext:
            return ext
    # try to infer from response headers
    if resp is not None:
        ct = resp.headers.get('content-type', '')
        if 'image/' in ct:
            subtype = ct.split('/')[-1].split(';')[0].strip()
            if subtype == 'jpeg':
                return '.jpg'
            return f'.{subtype}'
    return '.png'


def download_tile(session, url, out_path, timeout=15, retries=2, headers=None, skip_existing=True):
    # write to a temporary file first
    tmp_path = out_path + '.part'
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    # if final exists and skipping enabled
    if skip_existing and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        return True

    for attempt in range(1, retries + 2):
        try:
            resp = session.get(url, timeout=timeout, stream=True, headers=headers)
            if resp.status_code == 200:
                with open(tmp_path, 'wb') as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                # determine extension from response
                ext = _get_ext_from_url_or_content(url, resp) or '.png'
                final_path = out_path
                # if out_path has no extension, append ext
                base, cur_ext = os.path.splitext(out_path)
                if not cur_ext:
                    final_path = base + ext
                # move tmp to final
                try:
                    os.replace(tmp_path, final_path)
                except Exception:
                    os.remove(tmp_path)
                    return False
                return final_path
            else:
                time.sleep(0.5 * attempt)
        except Exception:
            time.sleep(0.5 * attempt)
    # cleanup tmp if exists
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    return False


def download_tile_range(template, z, x_range, y_range, outdir='out', concurrency=8, rate=0.05, headers=None, skip_existing=True, timeout=15, retries=2, tokens=None, convert_webp_to_png=False):
    xmin, xmax = x_range
    ymin, ymax = y_range
    tasks = []
    for x in range(xmin, xmax + 1):
        for y in range(ymin, ymax + 1):
            tasks.append((x, y))

    total = len(tasks)
    session = requests.Session()

    successes = 0
    failures = 0

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {}
        for x, y in tasks:
            # build url with tokens if provided
            fmt_kwargs = {'z': z, 'x': x, 'y': y}
            if tokens:
                fmt_kwargs.update(tokens)
            try:
                url = template.format(**fmt_kwargs)
            except Exception:
                url = tile_url(template, z, x, y)

            # prepare out path without extension (extension decided after response)
            out_base = os.path.join(outdir, str(z), str(x), f"{y}")
            futures[ex.submit(download_tile, session, url, out_base, timeout=timeout, retries=retries, headers=headers, skip_existing=skip_existing)] = (x, y, url, out_base)
            time.sleep(rate)

        for fut in tqdm(as_completed(futures), total=total):
            res = fut.result()
            x, y, url, out_base = futures[fut]
            if res:
                successes += 1
                # res may be the final_path when successful
                final_path = res if isinstance(res, str) else None
                # optional conversion
                if convert_webp_to_png and final_path:
                    try:
                        from PIL import Image
                        base, ext = os.path.splitext(final_path)
                        if ext.lower() in ('.webp',):
                            png_path = base + '.png'
                            img = Image.open(final_path)
                            img.save(png_path)
                    except Exception:
                        pass
            else:
                failures += 1

    return {'total': total, 'successes': successes, 'failures': failures}


def parse_bbox_arg(bbox_str):
    parts = [p.strip() for p in bbox_str.split(',')]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError('bbox 必须为 min_lon,min_lat,max_lon,max_lat')
    return tuple(float(p) for p in parts)


def main():
    parser = argparse.ArgumentParser(description='简单瓦片爬虫')
    parser.add_argument('--bbox', type=str, help='min_lon,min_lat,max_lon,max_lat')
    parser.add_argument('--geojson', type=str, help='GeoJSON 文件路径（可选）')
    parser.add_argument('--zoom', type=int, help='瓦片层级 z')
    parser.add_argument('--template', type=str, default='https://tile.openstreetmap.org/{z}/{x}/{y}.png', help='瓦片 URL 模板，包含 {z} {x} {y}')
    parser.add_argument('--outdir', type=str, default='out', help='输出目录')
    parser.add_argument('--concurrency', type=int, default=8, help='并发下载线程数')
    parser.add_argument('--rate', type=float, default=0.05, help='请求间隔（秒），用于限速')
    parser.add_argument('--skip-existing', action='store_true', help='跳过已存在的文件（默认不启用）')
    parser.add_argument('--referer', type=str, help='设置 HTTP Referer 请求头')
    parser.add_argument('--user-agent', type=str, help='设置 HTTP User-Agent 请求头')
    parser.add_argument('--headers', type=str, help='额外请求头，JSON 字符串，例如 "{\"Authorization\":\"Bearer ...\"}"')
    parser.add_argument('--single-url', type=str, help='下载单个完整 URL 到 outdir，文件名使用 tile_z_x_y.ext 或 tile.ext')
    parser.add_argument('--timeout', type=int, default=15, help='请求超时时间（秒）')
    parser.add_argument('--retries', type=int, default=2, help='重试次数')
    parser.add_argument('--secretId', type=str, help='模板中使用的 secretId')
    parser.add_argument('--clientId', type=str, help='模板中使用的 clientId')
    parser.add_argument('--expireTime', type=str, help='模板中使用的 expireTime')
    parser.add_argument('--sign', type=str, help='模板中使用的 sign')
    parser.add_argument('--convert-webp-to-png', action='store_true', help='将下载到的 webp 图片转换为 PNG')
    parser.add_argument('--dry-run', action='store_true', help='只计算瓦片范围与数量，不进行下载')
    args = parser.parse_args()

    # default essential headers (can be overridden by --headers)
    essential_headers = {
        'Accept': 'image/webp,*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Origin': 'https://online.geovisearth.com',
        'Referer': 'https://online.geovisearth.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Accept-Encoding': 'gzip, deflate, br',
        'Priority': 'u=1, i',
    }

    # build headers from CLI and merge with essentials
    hdrs = essential_headers.copy()
    if args.referer:
        hdrs['Referer'] = args.referer
    if args.user_agent:
        hdrs['User-Agent'] = args.user_agent
    if args.headers:
        try:
            extra = json.loads(args.headers)
            if isinstance(extra, dict):
                hdrs.update(extra)
        except Exception:
            print('警告：无法解析 --headers JSON，忽略')

    # prepare tokens for template
    tokens = {
        'secretId': args.secretId or '',
        'clientId': args.clientId or '',
        'expireTime': args.expireTime or '',
        'sign': args.sign or '',
    }

    if args.single_url:
        url = args.single_url
        os.makedirs(args.outdir, exist_ok=True)
        # pick a filename from url or fallback
        name = os.path.basename(url.split('?')[0]) or 'tile'
        out_path = os.path.join(args.outdir, name)
        print(f'下载单个 URL -> {out_path}')
        res = download_tile(requests.Session(), url, out_path, timeout=args.timeout, retries=args.retries, headers=hdrs, skip_existing=args.skip_existing)
        if res:
            print('完成，保存为：', res)
            # optional conversion
            if args.convert_webp_to_png:
                try:
                    from PIL import Image
                    base, ext = os.path.splitext(res)
                    if ext.lower() in ('.webp',):
                        png_path = base + '.png'
                        img = Image.open(res)
                        img.save(png_path)
                        print('已转换为：', png_path)
                except Exception:
                    print('转换为 PNG 失败（Pillow 未安装或文件受损）')
        else:
            print('失败')
        return

    if not args.bbox and not args.geojson:
        parser.error('必须指定 --bbox 或 --geojson 其一')

    if args.geojson:
        min_lon, min_lat, max_lon, max_lat = geojson_bbox(args.geojson)
    else:
        min_lon, min_lat, max_lon, max_lat = parse_bbox_arg(args.bbox)

    if not args.zoom:
        parser.error('批量抓取需要指定 --zoom')
    x_range, y_range = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, args.zoom)

    total_tiles = (x_range[1] - x_range[0] + 1) * (y_range[1] - y_range[0] + 1)
    print(f'Zoom {args.zoom} X range: {x_range} Y range: {y_range} total tiles: {total_tiles}')

    res = download_tile_range(args.template, args.zoom, x_range, y_range, outdir=args.outdir, concurrency=args.concurrency, rate=args.rate, headers=hdrs, skip_existing=args.skip_existing, timeout=args.timeout, retries=args.retries, tokens=tokens, convert_webp_to_png=args.convert_webp_to_png)
    print('下载结果：', res)


if __name__ == '__main__':
    main()
