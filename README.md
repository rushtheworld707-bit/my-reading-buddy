# 嘟哒 · DUDA

> **YOUR COZY READING PAL** — 一个像素杂志风的中文电子书阅读器，自带 AI 共读伙伴。

上传 EPUB / TXT / PDF / MOBI / AZW3，像翻杂志一样读书；划词查字典、摘录分享卡片、和 AI 深度对话、一键导出读书笔记。

## ✨ 功能

**阅读**
- 双页翻阅 · 键盘 ← → 翻页 · 进度自动保存（localStorage）
- 5 套配色主题（奶油 / 米黄 / 护眼 / 凉灰 / 暮色）
- 7 种中文字体（宋 / 楷 / 仿宋 / 黑 / 隶 / 圆 / 系统默认）
- 字号滑条（14-28px）
- 专注模式：一键隐藏所有 UI，只剩书页

**标注 & 回顾**
- 书签（跨 session 持久化）
- 手写笔记：划线原文 + 个人批注
- 阅读时长累计（每本书独立计时，tab 切走自动暂停）
- 一键导出 Markdown：书签 + 笔记 + AI 对话全部打包

**AI 共读**（接豆包 / Volcengine Ark）
- 自由对话：带当前章节全文 + 当前 spread 上下文
- 4 个快捷按钮：本章摘要 / 生词释义 / 讨论问题 / 人物分析

**交互彩蛋**
- 双击任何字 → 萌典词典悬浮查询（失败自动回退百度）
- 选中 8-500 字 → 浮动"📷 分享"按钮 → 下载像素风引用卡片 PNG
- 读完一章 → 像素烟花庆祝

## 🏃 本地运行

```bash
# 1. 克隆
git clone https://github.com/rushtheworld707-bit/my-reading-buddy.git
cd my-reading-buddy

# 2. 装依赖（建议用虚拟环境）
pip install -r requirements.txt

# 3. 配置 AI 密钥
mkdir -p .streamlit
cat > .streamlit/secrets.toml <<EOF
ARK_API_KEY = "你的 Volcengine Ark API Key"
ARK_MODEL_ID = "你的 Doubao 模型 ID"
EOF

# 4. 起服务
streamlit run streamlit_app.py
```

浏览器打开 http://localhost:8501 即可。

## ☁️ 部署

托管在 **Streamlit Community Cloud**，自动部署：

```
git push origin main  →  1-2 分钟后线上更新
```

`.streamlit/secrets.toml` 的内容需要在 Streamlit Cloud Dashboard → App Settings → Secrets 里独立配置（不走 git）。

## 🔧 技术栈

- **前端 / 框架**：[Streamlit](https://streamlit.io/) 单文件应用
- **存储**：浏览器 localStorage（`streamlit-local-storage`）
- **解析**：`ebooklib` (EPUB) · `PyPDF2` · `mobi` · `chardet` (TXT 编码)
- **AI**：OpenAI SDK → Volcengine Ark 端点（豆包模型）
- **词典**：moedict.tw API + 百度词典 fallback
- **卡片渲染**：html2canvas (CDN)

## 🎨 设计

- 像素杂志风，**Stardew-ish 暖色调色板**：`#3b2e1e` ink / `#c25a44` terra / `#d4b54c` mustard / `#4a6d4e` moss / `#fffaec` cream
- 字体：Press Start 2P（英文像素）· Zpix（中文像素）· Noto Serif SC（正文）

## 📋 待办

见 [TODO.md](./TODO.md)。
