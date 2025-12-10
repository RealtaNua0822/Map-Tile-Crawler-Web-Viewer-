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
from pathlib import Path
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


def validate_tile_request(template, z, x, y, headers=None, tokens=None, timeout=10, proxies=None):
    """Quickly request a single tile URL to validate headers/tokens.
    Returns (ok: bool, message: str).
    """
    try:
        import requests as _req
    except Exception:
        return False, 'requests 未安装'

    fmt_kwargs = {'z': z, 'x': x, 'y': y}
    if tokens:
        fmt_kwargs.update(tokens)
    try:
        url = template.format(**fmt_kwargs)
    except Exception:
        url = tile_url(template, z, x, y)

    sess = _req.Session()
    if proxies:
        try:
            sess.proxies.update(proxies)
        except Exception:
            pass

    try:
        resp = sess.get(url, headers=headers, timeout=timeout, stream=True)
    except Exception as e:
        return False, f'请求异常: {e}'

    if resp.status_code != 200:
        return False, f'HTTP {resp.status_code}'

    ct = resp.headers.get('content-type', '')
    if 'image' not in ct:
        return False, f'非图片响应，content-type={ct}'

    # try to read small amount to ensure body present
    try:
        chunk = next(resp.iter_content(chunk_size=64), b'')
        if not chunk:
            return False, '响应体为空'
    except Exception as e:
        return False, f'读取响应失败: {e}'

    return True, '验证通过'


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


def download_tile_range(template, z, x_range, y_range, outdir='out', concurrency=32, rate=0.0, headers=None, skip_existing=True, timeout=15, retries=2, tokens=None, convert_webp_to_png=False, proxies=None):
    xmin, xmax = x_range
    ymin, ymax = y_range
    tasks = []
    for x in range(xmin, xmax + 1):
        for y in range(ymin, ymax + 1):
            tasks.append((x, y))

    total = len(tasks)
    session = requests.Session()
    if proxies:
        try:
            session.proxies.update(proxies)
        except Exception:
            pass

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
            # ⚡️ 关键提速：移除了 time.sleep(rate)

        for fut in tqdm(as_completed(futures), total=total):
            res = fut.result()
            x, y, url, out_base = futures[fut]
            if res:
                successes += 1
                final_path = res if isinstance(res, str) else None
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
    parser.add_argument('--concurrency', type=int, default=32, help='并发下载线程数')  # ⬅️ 默认提高到 32
    parser.add_argument('--rate', type=float, default=0.0, help='请求间隔（秒），用于限速（现已禁用，由并发控制）')
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
    parser.add_argument('--config', type=str, help='JSON 配置文件路径，优先读取 headers、tokens、proxies 等')
    args = parser.parse_args()

    # default essential headers (can be overridden by config.json and/or --headers)
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

    # load optional JSON config
    config = {}
    candidates = []
    if args.config:
        candidates.append(args.config)
    candidates.append(str(Path(__file__).resolve().parent / 'config.json'))
    try:
        repo_root = Path(__file__).resolve().parents[2]
        candidates.append(str(repo_root / 'config.json'))
    except Exception:
        pass
    candidates.append(str(Path.cwd() / 'config.json'))

    for p in candidates:
        try:
            if p and Path(p).exists():
                with open(p, 'r', encoding='utf-8') as fh:
                    config = json.load(fh) or {}
                print(f'Loaded config from: {p}')
                break
        except Exception:
            continue

    # build headers
    hdrs = essential_headers.copy()
    try:
        cfg_hdrs = config.get('headers') if isinstance(config, dict) else None
        if isinstance(cfg_hdrs, dict):
            hdrs.update(cfg_hdrs)
    except Exception:
        pass

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

    # tokens priority: CLI args override config tokens
    cfg_tokens = config.get('tokens') if isinstance(config, dict) else {}
    tokens = {
        'secretId': args.secretId or cfg_tokens.get('secretId', ''),
        'clientId': args.clientId or cfg_tokens.get('clientId', ''),
        'expireTime': args.expireTime or cfg_tokens.get('expireTime', ''),
        'sign': args.sign or cfg_tokens.get('sign', ''),
    }

    # proxies
    proxies = None
    try:
        if isinstance(config, dict) and config.get('proxies'):
            proxies = config.get('proxies')
    except Exception:
        proxies = None

    if args.single_url:
        url = args.single_url
        os.makedirs(args.outdir, exist_ok=True)
        name = os.path.basename(url.split('?')[0]) or 'tile'
        out_path = os.path.join(args.outdir, name)
        print(f'下载单个 URL -> {out_path}')
        res = download_tile(requests.Session(), url, out_path, timeout=args.timeout, retries=args.retries, headers=hdrs, skip_existing=args.skip_existing)
        if res:
            print('完成，保存为：', res)
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

    # 批量任务模式（从 config.json jobs 读取）
    if not args.bbox and not args.geojson:
        jobs = config.get('jobs') if isinstance(config, dict) else None
        if jobs and isinstance(jobs, list) and len(jobs) > 0:
            print(f"发现 {len(jobs)} 个任务，开始依次执行...")
            for job in jobs:
                try:
                    name = job.get('name') or f"job-{jobs.index(job)}"
                    print(f"\n=== 开始任务: {name} ===")
                    template = job.get('template') or args.template
                    outdir = job.get('outdir') or args.outdir or 'out'
                    concurrency = int(job.get('concurrency') or args.concurrency or 32)
                    rate = float(job.get('rate') if job.get('rate') is not None else args.rate)
                    skip_existing = bool(job.get('skip_existing') if job.get('skip_existing') is not None else args.skip_existing)
                    timeout = int(job.get('timeout') or args.timeout)
                    retries = int(job.get('retries') or args.retries)
                    convert_webp = bool(job.get('convert_webp_to_png') if job.get('convert_webp_to_png') is not None else args.convert_webp_to_png)

                    if job.get('geojson'):
                        min_lon, min_lat, max_lon, max_lat = geojson_bbox(job.get('geojson'))
                    elif job.get('bbox'):
                        min_lon, min_lat, max_lon, max_lat = parse_bbox_arg(job.get('bbox'))
                    else:
                        print(f"任务 {name} 缺少 bbox 或 geojson，跳过")
                        continue

                    if not job.get('zoom'):
                        print(f"任务 {name} 未指定 zoom，跳过")
                        continue
                    z = int(job.get('zoom'))
                    x_range, y_range = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z)
                    total_tiles = (x_range[1] - x_range[0] + 1) * (y_range[1] - y_range[0] + 1)
                    print(f"任务 {name}: zoom={z} X={x_range} Y={y_range} 总瓦片={total_tiles}")

                    # 验证 token/header 是否有效
                    try:
                        center_lon = (min_lon + max_lon) / 2.0
                        center_lat = (min_lat + max_lat) / 2.0
                        cx, cy = latlon_to_tile_xy(center_lat, center_lon, z)
                        ok, msg = validate_tile_request(template, z, cx, cy, headers=hdrs, tokens=tokens, timeout=timeout, proxies=proxies)
                        if not ok:
                            print(f"任务 {name} 验证失败，跳过：{msg}")
                            continue
                        else:
                            print(f"任务 {name} 验证通过：{msg}")
                    except Exception as e:
                        print(f"任务 {name} 验证时发生异常，跳过：{e}")
                        continue

                    res = download_tile_range(template, z, x_range, y_range, outdir=outdir, concurrency=concurrency, rate=rate, headers=hdrs, skip_existing=skip_existing, timeout=timeout, retries=retries, tokens=tokens, convert_webp_to_png=convert_webp, proxies=proxies)
                    print(f"任务 {name} 下载结果：", res)
                except Exception as e:
                    print(f"任务 {name} 执行失败: {e}")
            print('\n所有任务执行完成')
            return
        else:
            parser.error('必须指定 --bbox 或 --geojson 其一，或在配置文件中添加 jobs')

    # 单次运行模式
    if args.geojson:
        min_lon, min_lat, max_lon, max_lat = geojson_bbox(args.geojson)
    else:
        min_lon, min_lat, max_lon, max_lat = parse_bbox_arg(args.bbox)

    if not args.zoom:
        parser.error('批量抓取需要指定 --zoom')
    x_range, y_range = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, args.zoom)

    total_tiles = (x_range[1] - x_range[0] + 1) * (y_range[1] - y_range[0] + 1)
    print(f'Zoom {args.zoom} X range: {x_range} Y range: {y_range} total tiles: {total_tiles}')

    res = download_tile_range(args.template, args.zoom, x_range, y_range, outdir=args.outdir, concurrency=args.concurrency, rate=args.rate, headers=hdrs, skip_existing=args.skip_existing, timeout=args.timeout, retries=args.retries, tokens=tokens, convert_webp_to_png=args.convert_webp_to_png, proxies=proxies)
    print('下载结果：', res)


if __name__ == '__main__':
    main()