# TODO

## 🔴 已知 Bug / 数据风险

- [x] ~~**P0 持久化**~~ ✅ **Done**（commit `2b4d1b5`，方案 B：streamlit-local-storage）。每个浏览器各存各的，天然用户隔离，容器重启不丢。已知限制：清浏览器缓存会丢；跨设备独立（不同步）；iOS Safari 隐私模式 7 天后可能清。若想跨设备同步，后续切 Supabase（方案 C）。
- [ ] **P1 分页性能**：`streamlit_app.py` 约 1850 行的 `chapter_page_counts = [len(split_into_pages(ch["text"])) for ch in chapters]` 每次 rerun 把整本书分页。长书翻一页就卡一次。用 `@st.cache_data(hash_funcs=...)` 缓存或只算当前章节。

## 🟡 功能 / 体验升级

- [ ] AI 流式输出：`client.chat.completions.create(..., stream=True)` + 逐 token 写入气泡
- [ ] AI 上下文扩大：当前仅 1200 字当前页 → 整章 or RAG
- [ ] 聊天记录按书持久化（当前仅 session_state）
- [ ] 全书文本搜索
- [ ] 高亮 / 笔记

## 🟢 工程健康

- [ ] README 仅 18 字节，补 "这是什么 / 怎么跑 / 部署" 三段
- [ ] 0 测试；先给 `extract_text_from_*`（epub / txt / pdf / mobi / azw3）加单元测试
- [ ] 键盘翻页 iframe + hidden button 的 hack 换成 `st.keybindings`（新 Streamlit API）
- [ ] 跟进 PyPDF2 / ebooklib / mobi 的 CVE
- [ ] 挂 Sentry 免费档收集线上异常

## 📋 UI 审美尾款（/critique + /polish 遗留）

- [ ] 翻页按钮视觉箭头（← 上一页 / 下一页 →）
- [ ] 书签空态 / AI chat 首次空态引导文案
- [ ] 侧栏分组标题图标一致性（阅读设置 / 章节选择前补像素 SVG）
- [ ] progress-fill width transition 恢复（Pass 2 清死代码时一起删了）
- [ ] AI 错误加 retry 按钮（last prompt 存 session_state）

## 🎨 UI 审美扩展（9 个 skill 角度）

### `/animate` — 动作质感
- [ ] 翻页 pixel book-page flip（`transform: rotateY` + `perspective` + `animation-timing-function: steps(6)` 保留像素跳变感）
- [ ] progress-fill width transition 恢复（Pass 2 清死代码误伤）：`transition: width 0.3s steps(12)`
- [ ] keyboard hint pill 首次出现 shake 0.3s 提示键盘翻页可用
- ROI：高（翻页是核心动作，每次体验都触发）

### `/delight` — 可分享的瞬间
- [ ] 章末庆祝：读完最后一页，书页右下角冒 pixel 花瓣 / 猫猫 Z 泡泡 / 上行箭头
- [ ] 点猫猫眨眼：欢迎页 SVG 猫闭眼睡，click 后眼睛短暂睁开 1s 再闭
- [ ] 随机开场签：欢迎页底栏加随机文学名句（瓦尔登湖 / 局外人 …）
- [ ] 康纳米彩蛋：↑↑↓↓←→←→ 解锁深色夜读模式
- ROI：中（累积产品性格）

### `/colorize` — 未用色承担语义
- [ ] moss 绿（目前仅在 .zw-kicker）→ "已读/已完成"：章节 selectbox 读完的章节左侧打 moss 小方块
- [ ] dusty 蓝（目前仅在猫 Z 泡泡）→ "当前位置"：侧栏书签列表里当前页高亮
- ROI：高（零增色、现有色做更多事）

### `/typeset` — 拓展中文阅读字体
- [ ] body 字体补：仿宋（古籍感）、隶书（装饰性）、魏碑（刚硬感）
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
- [ ] chat_input placeholder "跟我聊聊吧 [^_^]" → 更具体引导"对这段有什么想法？"
- ROI：低-中（成本低、累积效果好）

### `/distill` — 继续瘦
- [ ] rd-topbar 左段 `VOL.01 ■ EST.2026` 删 EST.2026 固定字符串
- [ ] HOW IT WORKS 三步 + 特性徽章 6 项信息重叠，二选一
- ROI：中（简化让核心信息更显眼）

### `/overdrive` — 艺术品级
- [ ] 欢迎页猫猫 parallax（鼠标移动轻微位移）
- [ ] 日期变装：中秋月亮底纹 / 春节春联 overlay / 生日蛋糕
- [ ] 每日像素装饰生成式（日期 seed）
- ROI：低-高（工程量大但能让朋友截图转发）

### `/audit` — 非美观但值得一跑
- [ ] 完整 WCAG 2.2 a11y 扫描
- [ ] 首屏性能（字体加载、SVG 大小、CSS 体积）
- [ ] Design tokens 化：所有 hardcoded hex 提取为 CSS 变量
- ROI：中（一次性结论、复用多次）

---

## 下次 UI 工作 top 3 组合（1-2h 最大冲击）
1. `/animate` 翻页 pixel flip + progress-fill transition
2. `/delight` 章末庆祝 + 点猫眨眼
3. `/colorize` moss 绿做"已读"标记

做完再跑 `/critique`，目标 38/40。
