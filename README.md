# 地理栅格瓦片爬虫与发布系统

# 项目总览（已合并）

此仓库为“地图瓦片爬虫与发布系统”。我已将源代码复制到统一目录 `src_all/`（见下文），并把文档合并为本文件的精简版本。原始文档已备份到 `docs_backup/`。

目的：
- 将所有源码放在一个易查找的位置，便于维护与发布。
- 把散落的说明合并为单一 `README.md`，便于快速上手。

重要：迁移为“复制”，原始文件仍保留在原路径。若需要我可以执行移除或重命名原始文件。

**统一源码位置**
- `src_all/python/` — Python 源文件（`tile_crawler.py`, `stitch_tiles.py`, `stitch_all.py`, `server.py`, `test_tiles.py`）
- `src_all/node_backend/` — Node 后端（`server.js`, `package.json`, `database.js`）
- `src_all/www/` — 静态前端页面（`index.html` 占位）

快速说明：
- Python 服务仍依赖 `requirements.txt`（根目录），可按原方式安装。
- Node 后端在 `src_all/node_backend/`，可用 `npm install` 之后 `npm start` 启动（如需要）。

快速开始（Python）：

```powershell
cd .\ex_1
pip install -r requirements.txt
# 运行服务器（使用迁移后的副本）
python src_all\python\server.py
# 或使用原始位置的 server.py：python server.py
```

下载瓦片示例（迁移后的爬虫副本）：

```powershell
python src_all\python\tile_crawler.py --bbox 115.4,39.4,117.5,41.1 --zoom 8 --template "https://tile.openstreetmap.org/{z}/{x}/{y}.png" --outdir out
```

文件结构（当前）:

```
ex_1/
├── src_all/
│   ├── python/
│   │   ├── tile_crawler.py
   │   ├── stitch_tiles.py
   │   ├── stitch_all.py
   │   ├── server.py
   │   └── test_tiles.py
   ├── node_backend/
   │   ├── server.js
   │   ├── package.json
   │   └── database.js
   └── www/
       └── index.html
├── src/            # 原始 Python 源（仍保留）
├── website0721/    # 原始网站项目（仍保留）
├── out/
├── map/
├── requirements.txt
├── quickstart.ps1
├── quickstart.bat
└── README.md       # (本文件，已合并文档)
```

备注与建议：
- 我只做了“复制与归档”，没有自动修改脚本中的相对导入或路径引用（例如 `from src.stitch_tiles import ...` 仍指向原位置）。如果你希望把工程切换为以 `src_all/` 为主目录，我可以：
  - 更新 Python 导入路径（或添加 `src_all/python` 到 `PYTHONPATH`），
  - 更新 `quickstart` 脚本中的启动路径，
  - 或把原始文件移动（重命名为 `.bak`）并保证所有引用一致。

- 如果要将 Node 后端完全迁移，请告诉我是否需要我在 `src_all/node_backend/` 里运行 `npm install` 并修改 `server.js` 的静态路径。

下一步（可选）:
- 我可以把原始源码从它们旧位置移动到 `src_all/`（删除或重命名原始文件），并调整启动脚本与导入以保持一致。
- 或者我可以只做文档合并并保留原始位置不变（当前状态）。

如果你想继续，我可以：
1. 按你的偏好把文件“移动”（替换为单一源目录）并更新导入与脚本；
2. 运行 `pytest` 或 `python test_tiles.py` 检查基础运行情况；
3. 提交变更为一个 Git 分支（需你确认）。

请选择下一步或让我直接执行完整迁移（会修改/重命名原始文件）。
