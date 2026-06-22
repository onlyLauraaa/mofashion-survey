# MoFashion 公开问卷部署

## 后端设置（5 分钟）

### 方案 A：Google Sheets（推荐，免费，自动汇总）
1. 打开 Google Sheets，新建表格
2. 扩展程序 → Apps Script，粘贴 `survey_backend.gs` 的全部代码
3. 部署 → 新部署 → 类型"Web 应用" → 访问权限"任何人" → 部署
4. 复制生成的 URL（如 `https://script.google.com/macros/s/xxx/exec`）
5. 编辑 `build_public_survey.py` 第 21 行，将 URL 填入 `GOOGLE_SCRIPT_URL`
6. 重新运行 `python build_public_survey.py`

### 方案 B：本地服务器（无需 Google）
1. cd MoFashion && python survey_server.py
2. 编辑 `build_public_survey.py` 第 24 行，URL 改为 `http://YOUR_IP:8899/api/submit`
3. 重新运行 `python build_public_survey.py`

## 前端部署（2 分钟）

### GitHub Pages
1. 将 `public_survey/` 整个文件夹推送到 GitHub 仓库
2. Settings → Pages → Source: main → Save
3. 公开地址: https://USERNAME.github.io/REPO/

### Gitee Pages（国内访问更快）
1. 将 `public_survey/` 推送到 Gitee 仓库
2. 服务 → Gitee Pages → 启动
3. 公开地址: https://USERNAME.gitee.io/REPO/

## 问卷链接（分发给被试）
- 首页: https://你的域名/
- 问卷1: https://你的域名/survey-1.html
- 问卷2: https://你的域名/survey-2.html
- 问卷3: https://你的域名/survey-3.html

## 查看结果
- Google Sheets: 直接打开表格，实时更新
- 本地服务器: http://YOUR_IP:8899/admin
