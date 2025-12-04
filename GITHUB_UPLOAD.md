# GitHub 上传指南

本文档说明如何将本项目推送到 GitHub。

## 前置条件

1. **安装 Git**
   - Windows: 从 https://git-scm.com/download/win 下载并安装
   - 安装后在 PowerShell 中应能使用 `git` 命令

2. **GitHub 账户**
   - 已创建 GitHub 账户（https://github.com）

3. **配置 Git 全局用户信息**

   在 PowerShell 中执行：

   ```powershell
   git config --global user.name "你的名字"
   git config --global user.email "你的邮箱@example.com"
   ```

---

## 步骤 1: 在 GitHub 创建仓库

### 网页操作（推荐）

1. 打开 https://github.com/new
2. 填写仓库信息：
   - **Repository name**: `map-tile-crawler`（或自定义名称）
   - **Description**: `Map tile crawler and web viewer - 地图瓦片爬虫与发布系统`
   - **Public/Private**: 选择 Public（公开）或 Private（私有）
   - ✅ 不勾选 "Initialize this repository with"（不创建 README、.gitignore 等，因为我们本地已有）
3. 点击 "Create repository"
4. GitHub 会显示推送命令（保留此页面，待会需要）

---

## 步骤 2: 本地初始化 Git 仓库

在项目根目录（`C:\Users\1\Desktop\ex_1`）的 PowerShell 中执行：

```powershell
cd C:\Users\1\Desktop\ex_1

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 创建首次提交
git commit -m "初始提交: 完整的地图瓦片爬虫与发布系统

- tile_crawler.py: 支持 bbox/geojson/单个 URL 的瓦片下载
- stitch_tiles.py: 瓦片拼接工具
- stitch_all.py: 批量拼接工具  
- server.py: Flask Web 服务与交互式地图浏览
- 详见 README.md 和 USAGE.md"
```

---

## 步骤 3: 添加远程仓库并推送

将 GitHub 上创建的仓库链接添加到本地：

```powershell
# 将 origin 指向 GitHub 仓库（替换 YOUR_USERNAME 和 REPO_NAME）
git remote add origin https://github.com/YOUR_USERNAME/map-tile-crawler.git

# 重命名主分支为 main（如需要）
git branch -M main

# 推送到 GitHub
git push -u origin main
```

**示例**（假设用户名为 `john-doe`，仓库名为 `map-tile-crawler`）：

```powershell
git remote add origin https://github.com/john-doe/map-tile-crawler.git
git branch -M main
git push -u origin main
```

---

## 步骤 4: 验证

打开 GitHub 仓库链接验证：

- 所有文件都已上传
- 查看文件列表：
  - `README.md`
  - `USAGE.md`
  - `requirements.txt`
  - `server.py`
  - `src/tile_crawler.py`
  - `src/stitch_tiles.py`
  - `src/stitch_all.py`

---

## 常见问题

### Q: "fatal: not a git repository"

A: 确保你在项目根目录执行 `git init`：

```powershell
cd C:\Users\1\Desktop\ex_1
git init
```

### Q: "error: src refspec main does not match any branch"

A: 确保已执行 `git commit` 创建了至少一次提交，再执行 `git push`

### Q: 认证失败（403/401）

A: 使用 GitHub token 替代密码：

```powershell
# 用 token 替代密码
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/REPO_NAME.git
```

获取 token：https://github.com/settings/tokens

### Q: 想修改已推送的提交信息

A: 首次推送后，若要修改，可用 `git commit --amend`（仅限本地，推送后应避免修改历史）

---

## 可选：创建 .gitignore

为避免上传临时文件和缓存，在项目根目录创建 `.gitignore` 文件：

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# 虚拟环境
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 系统
.DS_Store
Thumbs.db

# 项目临时文件
*.part
*.tmp
```

创建后重新提交：

```powershell
git add .gitignore
git commit -m "添加 .gitignore"
git push
```

---

## 可选：添加 LICENSE（开源协议）

推荐添加开源协议。常见选择：

- **MIT**: 宽松协议（推荐用于个人项目）
- **Apache 2.0**: 包含专利保护
- **GPL 3.0**: 强制衍生品开源

在项目根目录创建 `LICENSE` 文件，内容参考：

- MIT: https://opensource.org/licenses/MIT
- 更多: https://choosealicense.com

推送：

```powershell
git add LICENSE
git commit -m "添加 MIT 许可证"
git push
```

---

## 后续更新（已上传后）

本地代码更新后，推送新版本：

```powershell
git add .
git commit -m "更新: 添加新功能"
git push
```

---

## 完整示例流程

```powershell
# 进入项目目录
cd C:\Users\1\Desktop\ex_1

# 初始化
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 添加并提交
git add .
git commit -m "初始提交"

# 添加远程仓库（替换 URL）
git remote add origin https://github.com/你的用户名/map-tile-crawler.git

# 推送
git branch -M main
git push -u origin main

# 验证
git status
git log
```

---

**需要帮助？** 查看 GitHub 官方指南：https://docs.github.com/en/get-started
