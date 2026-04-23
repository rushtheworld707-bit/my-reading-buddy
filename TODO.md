# TODO

## 🔴 已知 Bug / 数据风险

（当前无。P0 持久化 & P1 分页性能已解决。）

## 🟡 功能 / 体验升级

- [ ] 全书文本搜索
- [ ] 划线高亮（选中后保存 + 跨 session 回显 + 锚定算法）— 之前推迟的大工程，配合"选中浮标工具条"一起做最自然
- [ ] 书库管理（多本书缩略图书架，切换不用重新上传；localStorage 容量可能不够，考虑 IndexedDB）
- [ ] 阅读统计 dashboard（总字数 / 阅读日历 / 最爱时段）

## 🟢 工程健康

- [ ] 0 单元测试；先给 `extract_text_from_*`（epub / txt / pdf / mobi / azw3）加
- [ ] 键盘翻页 iframe + hidden button 的 hack 换成 `st.keybindings`（新 Streamlit API）
- [ ] 跟进 PyPDF2 / ebooklib / mobi 的 CVE
- [ ] 挂 Sentry 免费档收集线上异常
- [ ] 把 ruff 规则从 CI yaml 挪到 `pyproject.toml`，本地也能统一跑

## 📋 UI 审美尾款（/critique + /polish 遗留）

- [ ] 翻页按钮视觉箭头（← 上一页 / 下一页 →）
- [ ] 书签空态引导文案再打磨（目前"点「加入当前位置」收藏你想回来的页面"）
- [ ] 侧栏分组标题图标一致性（章节选择前补像素 SVG）
- [ ] progress-fill width transition 恢复（Pass 2 清死代码时一起删了）

## 🎨 UI 审美扩展（按 skill 分组）

### `/animate` — 动作质感
- [ ] 翻页 pixel book-page flip（`transform: rotateY` + `perspective` + `animation-timing-function: steps(6)` 保留像素跳变）
- [ ] progress-fill width transition 恢复：`transition: width 0.3s steps(12)`
- [ ] keyboard hint pill 首次出现 shake 0.3s 提示键盘翻页可用
- ROI：高（翻页是核心动作，每次都触发）

### `/delight` — 可分享的瞬间
- [ ] 康纳米彩蛋：↑↑↓↓←→←→ 解锁深色夜读模式
- ROI：中（累积产品性格）

### `/colorize` — 未用色承担语义
- [ ] dusty 蓝 → "当前位置"：侧栏书签列表里当前页高亮
- ROI：高（零增色、现有色做更多事）

### `/typeset` — 拓展中文阅读字体
- [ ] body 字体补：魏碑（刚硬感）
- [ ] 章节标题 h3 在书页顶给更隆重字号 + 更多留白
- [ ] 中英混排时标点 fullwidth 替换（CSS `content`）
- ROI：中（直接影响阅读舒适度）

### `/bolder` — 欢迎页再放大一号
- [ ] 嘟哒标题 96 → 110px（手机端 54px 不动）
- [ ] `.zw-title-bar` 10 → 14px 高
- [ ] feature badges 改方角实边 + 2px 芥黄错位阴影，与 step 卡片语言统一
- ROI：中（peak 已经很好，边际递减）

### `/adapt` — 移动端手势与断点
- [ ] 左右 swipe 翻页（手机端键盘缺席）
- [ ] portrait / landscape 布局差异化
- [ ] <320px 小屏兼容验证
- ROI：中-高（朋友手机阅读是真实场景）

### `/clarify` — microcopy 再过一遍
- [ ] "加入当前位置" → "收藏本页"
- [ ] "本章约剩 N 分钟" → "本章还要 N 分钟读完"
- [ ] "跳转到页码" → "跳到第几页"
- [ ] "书本解析失败" error 换温暖版
- ROI：低-中（成本低、累积效果好）

### `/distill` — 继续瘦
- [ ] rd-topbar 左段 `VOL.01 ■ EST.2026` 删 EST.2026 固定字符串
- [ ] HOW IT WORKS 三步 + 特性徽章 6 项信息重叠，二选一
- ROI：中（简化让核心信息更显眼）

### `/overdrive` — 艺术品级
- [ ] 日期变装：中秋月亮底纹 / 春节春联 overlay / 生日蛋糕
- [ ] 每日像素装饰生成式（日期 seed）
- ROI：低-高（工程量大但能让朋友截图转发）
- ⛔ 欢迎页猫猫 parallax：**放弃**。试过 `mousemove + document` 都不生效，Streamlit iframe 结构吃掉事件，投入产出比不划算。

### `/audit` — 非美观但值得一跑
- [ ] 完整 WCAG 2.2 a11y 扫描
- [ ] 首屏性能（字体加载、SVG 大小、CSS 体积）
- [ ] Design tokens 化：所有 hardcoded hex 提取为 CSS 变量

## 下次 UI 工作 top 3 组合（1-2h 最大冲击）

1. `/animate` 翻页 pixel flip + progress-fill transition
2. `/colorize` dusty 蓝做"当前位置"标记
3. `/clarify` microcopy 过一遍

做完再跑 `/critique`，目标 38/40。

---

## ✅ 已完成归档

### 数据持久化 & 性能
- **P0 持久化**（commit `2b4d1b5`）方案 B：`streamlit-local-storage`。每浏览器各存各的，容器重启不丢。限制：清缓存丢；跨设备独立；iOS Safari 隐私模式 7 天可能清。
- **P1 分页性能**（commit `e9d75b0`）`split_into_pages` 加 `@st.cache_data`；`chapter_page_counts` 自动吃缓存。

### AI 共读
- AI 流式输出（`stream=True` + `st.write_stream`，消除 3-10 秒等待）
- AI 上下文扩大（当前章节全文头尾夹 + spread 精确位置 + 最近 8 条历史）
- 聊天记录按书持久化（`_LS_MESSAGES_KEY`，`{book_key: [msgs]}`）
- AI 错误 retry 按钮（last prompt 存 session_state）
- **AI 快捷分析**（4 按钮：本章摘要 / 生词释义 / 讨论问题 / 人物分析，一键预置 prompt）

### 阅读体验
- 5 套配色主题（奶油 / 米黄 / 护眼 / 凉灰 / 暮色）
- 专注模式（一键隐藏所有 UI，右上浮动✕退出）
- 阅读时长追踪（per-book，JS 后台累计，visibilitychange 暂停）
- 双击查词典（萌典 API + 百度 fallback，`Esc` 关闭）
- 选中 8-500 字 → 生成像素风引用卡片 PNG（html2canvas）
- 笔记/书签/AI 对话 一键导出 Markdown
- moss 绿 "已读章节" 标记（章节 selectbox 前缀 `■`）
- 章末庆祝烟花（`.rb-firework`）
- 点猫猫眨眼（欢迎页 SVG click → 眼睛短暂睁开）
- 随机开场签（欢迎页 hero typewriter 加入文学名句）
- chat_input placeholder 改"对这段有什么想法？"

### 欢迎页装修
- 嘟哒 → DUDA Press Start 2P 标题 + YOUR COZY READING PAL 副标
- 像素星星群 / 蘑菇 / 火把 / 心形 / 盆栽 / 药水瓶 / 书架 / 闪光装饰
- 底部留白修复（`min-height: 100vh` → `unset` + body 背景兜底）

### 工程基础
- README.md 从 18 字节扩充到完整的项目介绍
- CLAUDE.md 新建（AI 协作上下文：结构/约束/CSS 前缀/localStorage key/坑）
- GitHub Actions CI（ruff `E9,F63,F7,F82,F401` + `py_compile`，~16s）
