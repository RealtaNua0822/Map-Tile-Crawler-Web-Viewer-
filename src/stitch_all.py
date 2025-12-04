#!/usr/bin/env python3
"""
stitch_all.py

对一组 zoom（或 zoom 范围）为指定 bbox 生成拼接图（PNG），
每个 zoom 生成一张大图，命名为 `{minLon}_{minLat}_{maxLon}_{maxLat}_z{z}.png`。

示例：
python -m src.stitch_all --bbox 115.4,39.4,117.5,41.1 --min-zoom 7 --max-zoom 9 --input-dir out --output-dir map
"""
from pathlib import Path
import argparse
from src.stitch_tiles import bbox_to_tile_range, stitch


def fmt_bbox_name(min_lon, min_lat, max_lon, max_lat):
    return f"{min_lon:.4f}_{min_lat:.4f}_{max_lon:.4f}_{max_lat:.4f}"


def main():
    p = argparse.ArgumentParser(description='为每个 zoom 生成 PNG 地图并保存到 output-dir')
    p.add_argument('--bbox', required=True, help='min_lon,min_lat,max_lon,max_lat')
    p.add_argument('--min-zoom', type=int, required=True)
    p.add_argument('--max-zoom', type=int, required=True)
    p.add_argument('--input-dir', default='out', help='切片根目录')
    p.add_argument('--output-dir', default='map', help='保存大图的目录')
    p.add_argument('--tile-size', type=int, default=256)
    p.add_argument('--format', default='PNG', help='输出格式（默认 PNG）')

    args = p.parse_args()

    parts = args.bbox.split(',')
    if len(parts) != 4:
        p.error('--bbox 需要四个逗号分隔的数字')
    min_lon, min_lat, max_lon, max_lat = map(float, parts)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    name_prefix = fmt_bbox_name(min_lon, min_lat, max_lon, max_lat)

    results = []
    for z in range(args.min_zoom, args.max_zoom + 1):
        x_min, x_max, y_min, y_max = bbox_to_tile_range(min_lon, min_lat, max_lon, max_lat, z)
        out_name = f"{name_prefix}_z{z}.png"
        out_path = output_dir / out_name
        print(f"处理 zoom {z}: X {x_min}..{x_max}, Y {y_min}..{y_max} -> {out_path}")
        res = stitch(z, x_min, x_max, y_min, y_max, input_dir, out_path, tile_size=args.tile_size, output_format=args.format)
        results.append(res)

    print('\n全部完成：')
    for r in results:
        print(f" - z={r['z']}: tiles {r['total']} missing {r['missing']} -> {r['output']}")


if __name__ == '__main__':
    main()
