# UI 改版迁移计划

> **改版目标：** 把当前"欢迎页 + 侧边栏 + 主区阅读 + 主区底部 AI"的双形态布局，改造成 spec v1 规定的**单一主控台**（4 区 + 底部卡片）。
>
> **范围：** 仅 UI 重构，不改后端、不迁移技术栈、不删除功能。
>
> **工作模式：** 本地小阶段 commit → 收工统一 push（见 CLAUDE.md）。
>
> **设计终态参考：** [DESIGN_SPEC.md](./DESIGN_SPEC.md)（视觉/文案/交互/组件规范的 SSOT）+ 预览图 `docs/design-preview.png`。每阶段开工前必查对应模块章节。

---

## 1. 当前代码解剖

### 1.1 文件位置映射

全部代码在 `streamlit_app.py`（~3770 行）。关键锚点：

| 段 | 起止行 | 内容 |
|----|------|------|
| Imports + PX_ICON + READING_THEMES | 1-34 | 像素图标 SVG 字符串 dict + 5 套主题色 |
| CSS `<style>` 块 | 37-1319 | 全局样式（包含 `.zw-*` 欢迎页 和 `.rd-*` 阅读页两套）|
| handwrite-title + Streamlit 样式 | 1322-1395 | 顶部装饰标题 + Streamlit 外壳样式 |
| 上传入口（欢迎模式） | 1396-1418 | 侧边栏 "回到欢迎页" 按钮 + file_uploader |
| 解析函数 | 1420-1817 | `extract_text_from_*`（epub/txt/pdf/mobi/azw3）+ `split_into_pages` + `_to_html` |
| LocalStorage helpers | 1819-1966 | `_LS_*` 常量 + `_ls_read_dict` / `_ls_write_dict` + 书签/笔记/进度/消息/读时长 CRUD |
| 导出函数 | 1968-2049 | `_build_export_markdown` |
| 主逻辑入口 | 2054-3365 | `if has_file:` 阅读模式（包含侧边栏 + 阅读区 + AI 聊天）|
| 欢迎页（`else:` 分支） | 3365-3700 | `zw-top` + `zw-bottom` 两段 markdown + 文件上传器 |
| 末尾 components.html | 3700+ | 猫眨眼 + parallax 放弃脚本 |

### 1.2 现有 session_state key 清单

```
file_bytes, file_name, loaded_book        # 当前书
last_chapter, read_chapters               # 当前章节 + 已读集合
messages, notes                           # AI 对话 + 笔记（session 内）
font_size, font_family_name, reading_theme  # 阅读设置
focus_mode                                # 专注模式开关
_pending_jump                             # 跳转请求
_queued_ai_prompt                         # AI 快捷按钮的预置 prompt
_note_form_ver                            # 笔记表单版本（rerun 清空用）
page_<book_key>                           # 每本书的翻页位置
```

### 1.3 现有 localStorage key

```python
_LS_PROGRESS_KEY   = "reading_buddy_progress_v1"    # {book_key: {chapter, page, updated_at}}
_LS_BOOKMARKS_KEY  = "reading_buddy_bookmarks_v1"   # {book_key: [{ch, page, ts}]}
_LS_MESSAGES_KEY   = "reading_buddy_messages_v1"    # {book_key: [{role, content}]}
_LS_NOTES_KEY      = "reading_buddy_notes_v1"       # {book_key: [{id, ch, page, passage, note, ts}]}
_LS_READTIME_KEY   = "reading_buddy_readtime_v1"    # {book_key: total_seconds}
```

### 1.4 现有侧边栏内容（`st.sidebar.*`）

从上到下：
1. 章节 selectbox（按章节跳转）
2. 页码 number_input（跳到第 N 页）
3. divider
4. 书签区：加入当前位置按钮 + 书签列表
5. divider
6. 笔记区：笔记列表（passage + 批注）
7. divider
8. 导出区：下载 Markdown 按钮
9. divider
10. 阅读设置区：阅读时长 caption + 进入专注模式按钮 + 字号 slider + 字体 selectbox + 配色 selectbox

### 1.5 现有主区内容（非 sidebar）

1. 顶部 `rd-topbar`（VOL.01 · 章节名 · CH.XX · 时钟）
2. 进度条 `.progress-container`
3. 双页 `.book-spread`（左右 `.book-page`）
4. 页码指示 `.page-indicator`
5. 导航按钮 `.nav-row`（上一页 / 下一页）
6. divider（st.divider）
7. AI 聊天标题 `.ai-chat-heading`
8. 快捷分析按钮（4 columns）
9. 聊天历史（st.chat_message 循环）
10. 聊天输入（st.chat_input，docked at bottom）

### 1.6 现有欢迎页（`else:` 分支）

`zw-top`：刊头 + DUDA 标题 + 副标 + 随机开场签 + 文件格式按钮 + 猫 + 像素装饰
`zw-bottom`：HOW IT WORKS 三步 + 6 个 feature badges + 底部 strip

---

## 2. 新布局目标（来自 spec + 预览图）

```
┌────────────────────────────────────────────────────────────────────┐
│ TOPBAR（整幅横条，跨全宽）                                          │
├──────┬─────────────────────────────────┬───────────────────────────┤
│ LEFT │         CENTER READER            │   RIGHT AI PANEL          │
│ NAV  │         (书本 + 控制条)            │   (tabs + 卡片 + 输入)     │
│ 16%  │              56%                 │         28%               │
├──────┴─────────────────────────────────┴───────────────────────────┤
│ BOTTOM 4 CARDS（整幅横条，4 等分）                                  │
│  我的书架 30% · 摘录与笔记 24% · 上传 22% · 阅读统计 24%              │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. 功能映射表（旧 → 新）

### 3.1 从 sidebar 迁出

| 原位置（sidebar） | 新位置 | 备注 |
|-----|-----|-----|
| 章节 selectbox | **Center · 控制条 · 目录按钮**（点击弹层显示章节列表） | 或 TOP BAR 的 "第 3 章" 点击触发 |
| 页码 number_input | **Center · 控制条 · 32 / 210** 点击弹层输入 | |
| 加入当前位置按钮 | **TOP BAR · 书签 icon** + **Center · 控制条 · 书签按钮** | 两处触发都保留 |
| 书签列表 | **点击 TOP BAR 书签 icon 弹层** 显示 | 或并入"摘录与笔记"页子页面 |
| 笔记列表 | **BOTTOM · 摘录与笔记卡片**（近一条）+ "查看全部" 跳子页 | 拆分：passage 字段 → 摘录，note 字段 → 笔记 |
| 下载 Markdown 按钮 | **子页"摘录与笔记"** 顶部（spec 没细说，合理归入） | |
| 阅读时长 caption | **BOTTOM · 阅读统计卡片** | |
| 进入专注模式按钮 | **子页"阅读设置"** 或保留 TOP BAR icon | |
| 字号 slider | **TOP BAR · 字号 icon（Aa）** 弹层 | |
| 字体 selectbox | **子页"阅读设置"** | TOP BAR 空间不够 |
| 配色 selectbox | **TOP BAR · 主题 icon（☀）** 弹层 | |
| 回到欢迎页按钮 | **废弃**（新版没有独立欢迎页）| |
| 文件上传器（欢迎态外的） | **BOTTOM · 上传书籍卡片** | |

### 3.2 从主区迁出

| 原位置（主区） | 新位置 |
|-----|-----|
| `rd-topbar`（VOL.01 · 章节 · 时钟） | 删除；被新 TOP BAR 取代 |
| progress-container 进度条 | **TOP BAR · 进度 32%** |
| book-spread 双页 | **CENTER · 书本阅读器**（视觉更新但内容逻辑不变）|
| page-indicator + nav-row | **CENTER · 控制条**（扩成 6 按钮） |
| AI chat 标题 + 快捷按钮 + 历史 | **RIGHT AI 面板**（所有内容搬过去） |
| st.chat_input | **RIGHT AI 面板底部**（必须换成 st.text_input + button，见决策 B）|

### 3.3 欢迎页 → 空状态

整个 `else:` 分支（zw-top + zw-bottom）将被删除。"没有书"的情形改为主控台 layout 本身的空状态：
- CENTER：合着的书 SVG + "上传一本书，开始与你的阅读伙伴一起读书"
- BOTTOM · 我的书架：显示 "还没有书" 引导
- BOTTOM · 上传书籍：成为主要 CTA
- RIGHT AI 面板：可显示 "先上传一本书吧" placeholder
- TOP BAR：书名/作者/章节 显示为 "—"

### 3.4 新增内容（spec 要求但目前没有）

| 新元素 | 数据来源 | 是否需要新 localStorage key |
|------|-----|-----|
| 书架（最近 4 本）| 需要"所有上传过的书"记录 | **是** → `_LS_LIBRARY_KEY` |
| 连续阅读天数 | 需要记录每日是否阅读 | **是** → `_LS_DAILYSTREAK_KEY` |
| 与上周对比（时长 / 书数 / 连读天数） | 基于上两个新 key 推算 | 无需新 key，函数计算 |
| 左 nav 角色头像 SVG | 新画 | |
| 左 nav 小花盆、书堆、台灯 SVG | 部分可复用现有 mushroom/plant/torch | |
| 书本 icon（Top bar 最左）| 新画或复用 PX_ICON["read"] | |
| 搜索 icon（Top bar）| 新画 | |
| 用户头像 icon | 新画 | |
| 机器人 icon（AI 助读）| 复用 PX_ICON["robot"] | |
| 咖啡杯 / 书柜 / 台灯 大 SVG | 新画 | |

---

## 4. 关键技术决策

### A. 布局方案：CSS Grid ✅

**选 Grid，不选 Flexbox 或 st.columns。**

**理由：**
- 目标是严格的"顶栏+三列+底栏"结构，Grid 天生擅长
- Flexbox 做嵌套三栏会因为 Streamlit 的 `stVerticalBlock` 打架
- `st.columns()` 只能水平分格，没法同时搞顶栏+左栏+中+右+底栏

**实现要点：**
```css
.mc-grid {
  display: grid;
  grid-template-areas:
    "topbar topbar topbar"
    "nav    center right"
    "bottom bottom bottom";
  grid-template-columns: 16% 56% 28%;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
  gap: 0;
}
```

**Streamlit 兼容问题：** Streamlit 会把每个 `st.markdown` / `st.button` / `st.xxx` 包装在 `stElementContainer` 里，这些默认是垂直堆叠。要让它们进入 Grid 格子，有两条路：

1. **纯 HTML 骨架 + Streamlit 组件后置注入**：用一个大 `st.markdown(unsafe_allow_html=True)` 画完整个 grid 骨架，里面留占位 id；然后通过 CSS `position: absolute / fixed` 把 Streamlit 生成的 widget 贴到位。**缺点：** 交互控件（按钮、输入框）必须靠 JS 把 Streamlit 生成的 DOM "搬家"，脆弱。
2. **Streamlit 原生 columns + CSS Grid 混合**：用 `st.columns([16, 56, 28])` 先做三栏骨架，Top Bar 和 Bottom 分别是独立的 `st.markdown` 或 `st.columns` 放在 columns 之前和之后。**缺点：** 每行是 `stHorizontalBlock`，做不到 topbar 跨全宽 + 下方三栏独立滚动。**优点：** 不用搬 DOM。

**决策：选方案 2（st.columns 混合）**。接受"topbar 和 bottom 是独立水平块"的事实，视觉上靠 CSS 让它们看起来像 Grid。Streamlit 原生渲染路径最稳。

### B. `st.chat_input` 替换方案 ✅

**必须换成 `st.text_input` + `st.button`。**

**理由：**
- `st.chat_input` 在 Streamlit 里是 **docked 到页面底部主区**的，位置固定，没有官方 API 放到右侧栏
- 即使用 CSS `position: fixed` 强制搬，也没法让它落进 RIGHT 列内部

**Loss：**
- 失去 Enter 键原生发送（但可以 JS 绑 keydown）
- 失去 docked 在底部的持久可见性（但新布局里 AI 输入框本来就在右列底部）
- 失去 placeholder 动画等细节

**实现：**
```python
# 右侧 AI 面板底部
with _right_col:
    with st.form("ai_chat_form", clear_on_submit=True):
        _user_input = st.text_input(
            "向嘟哒提问",
            placeholder="继续向嘟哒提问…",
            label_visibility="collapsed",
            key="ai_text_input",
        )
        _submitted = st.form_submit_button("▶")
    if _submitted and _user_input.strip():
        # 触发现有 AI 流式逻辑
```

`st.form` 自带 "Enter 提交" 行为，正好解决键盘提交。

### C. 新 CSS 命名前缀：`mc-*` ✅

- `mc-*` = **main-console**（主控台）= 新的四区布局元素
- 保留 `rd-*` = reading area（阅读器内部的 book-page、书脊等仍沿用）
- 保留 `rb-*` = runtime-injected（词典弹窗、分享按钮等 JS 注入 UI）
- **删除** `zw-*` = zine-welcome（阶段 9 时全部清理）

**命名示例：**
```
.mc-grid           整体 Grid 容器
.mc-topbar         顶部状态条
.mc-nav            左侧导航
.mc-nav-brand      品牌区
.mc-nav-menu       菜单列表
.mc-nav-decor      底部装饰
.mc-center         中央区（包 reader）
.mc-center-frame   木质外框
.mc-reader         reader 内层（保留 .book-spread 作为最内层）
.mc-reader-bar     控制条
.mc-ai             右侧 AI 面板
.mc-ai-tabs        tab 切换
.mc-ai-card        对话卡片
.mc-ai-input       输入区
.mc-bottom         底部四卡容器
.mc-card           单张卡
.mc-card--library / --notes / --upload / --stats  修饰符
```

### D. 不用 feature flag

已确认。直接 in-place 重构。本地 commit + 收工 push 的工作流提供天然保护。

### E. 色板策略

现有 7 色 → spec 8 色，不是 1:1 对应。映射规则（阶段 1 详细做）：
```
#3b2e1e (旧 ink)     → #2E1D12 (新深文字) + #3B2416 (新深木棕)
#fffaec (旧 cream)   → #FFF6E8 (新浅纸白)
#f3e9cf (旧 paper)   → #F6E7C8 (新奶油纸)
#d4b54c (旧 mustard) → #D7A441 (新金黄强调)
#c25a44 (旧 terra)   → #B96A4A (新柔红棕) 或拆分为 #A86A33 (新焦糖棕)
#4a6d4e (旧 moss)    → #6E8B5B (新苔绿，spec 给的值)
#7a96b4 (旧 dusty)   → 没直接对应，保留但 deprecate
```

**新增：** #6B4024（中木棕，spec 核心色，原色板没有）、#8E735B（次级灰棕）、#F2C66D（暖灯黄）

**实现：** 全部提取为 CSS 变量（`--mc-ink` / `--mc-wood-deep` / …），方便后续全局调节。

### F. 模块拆分？

**不拆。** 继续单文件 `streamlit_app.py`。重构后体积预计 ~4500-5000 行，虽大但仍可读。拆分会引入新的 import 开销 + Streamlit 的 rerun 模型对模块边界不友好。

---

## 5. 风险 & 缓解

| 风险 | 可能性 | 缓解 |
|------|------|------|
| CSS Grid 和 Streamlit block 冲突导致布局错位 | 高 | 阶段 2 先只做骨架，独立验证；选 st.columns 混合方案降低耦合 |
| `st.chat_input` 替换后，Enter 发送失效 | 中 | 用 `st.form` 自带 Enter 提交 |
| 配色变更引入不协调（新 #B96A4A vs 旧 #c25a44 差别细微但累计有感知） | 低-中 | 阶段 1 提取 CSS 变量后可快速微调 |
| 新"书架"需要全量书记录，但当前只存了当前上传 | 确定 | 阶段 7 新增 `_LS_LIBRARY_KEY`，`file_bytes` 留在 session_state 但 `file_name` 入 library 记录 |
| 旧欢迎页 zine 的精美装饰（像素 DUDA + 猫 + 蘑菇 + 火把 + 心 + 书架）全丢？| 中 | **复用方案：** 猫 SVG → 左 nav 角色头像；书架 → 中央 reader 旁装饰；蘑菇/植物 → 左 nav 底部；火把 → 中央 reader 旁；心/星星 → 散点式装饰；DUDA 字 → 左 nav 品牌区 |
| 删掉欢迎页后，首次访问用户没有"产品介绍"落地页 | 中 | spec 里首页清单第 1 条是"欢迎页"，但和主控台并列。**阶段 9 补策略：** 主控台 + 空状态即可充当欢迎体验，HOW IT WORKS 的 3 步并入某处简化版。若需要独立欢迎页，可在 `/welcome` 路由未来补。首版不做 |
| 响应式 + 移动端没做过，改造期间桌面设计可能假设太多 PC | 中 | 阶段 9 统一补；桌面优先，手机作为退化版本 |
| 阶段 6 `st.form + text_input` 流失去流式感 | 中 | 输出端不变（仍用 `st.write_stream`），只换输入端 |

---

## 6. 现有功能去哪了（终极清单）

逐条列保证**零功能丢失**：

| # | 功能 | 新家 | 阶段 |
|---|------|------|------|
| 1 | EPUB/TXT/PDF/MOBI/AZW3 上传 | BOTTOM 卡 3 + RETURN 路径保留 | 7 |
| 2 | 章节切换 | CENTER 控制条·目录按钮（弹层）| 5 |
| 3 | 页码跳转 | CENTER 控制条·32/210（弹层输入）| 5 |
| 4 | 上一页 / 下一页（键盘 & 按钮）| CENTER 控制条·左右按钮，键盘继续可用 | 5 |
| 5 | 书签 add + list | TOP BAR · 书签 icon（弹层）+ CENTER 控制条·书签按钮（add）| 4 + 5 |
| 6 | 笔记（带 passage + note）| BOTTOM 卡 2 近一条 + 子页"摘录与笔记"（查看全部）| 7 + 未来 |
| 7 | AI 自由对话 | RIGHT AI 面板 · 卡片区 + 自定义 input | 6 |
| 8 | AI 快捷分析（摘要/生词/提问/人物）| RIGHT AI 面板 · 4 tabs（问这段/总结本章/解释词句/提取观点）| 6 |
| 9 | 配色主题（5 套）| TOP BAR · 主题 icon 弹层（可能收敛为 3 套）| 4 |
| 10 | 字体（7 种）| 子页"阅读设置" | 未来或 TOP BAR Aa 弹层 |
| 11 | 字号 slider | TOP BAR · 字号 Aa 弹层 | 4 |
| 12 | 专注模式 | TOP BAR 角落 icon 或 "阅读设置" 子页 | 4 |
| 13 | 阅读时长显示 | BOTTOM 卡 4 阅读统计 · "总阅读时长 18h 42m" | 7 |
| 14 | 阅读时长 JS tracker | 不动，后台继续跑 | — |
| 15 | 笔记导出 Markdown | 子页"摘录与笔记"顶部 下载按钮 | 未来 |
| 16 | 双击查词典 | 不动（JS 层） | — |
| 17 | 选中文本分享卡片 | 不动（JS 层） | — |
| 18 | 已读章节 moss 绿标记 | 目录弹层里保留 | 5 |
| 19 | 章末烟花 | 中央 reader 内保留 | 5 |
| 20 | 点猫眨眼 | 猫搬到左 nav 角色头像，眨眼继续 | 3 |
| 21 | 欢迎页随机开场签 | 重新利用：空状态中央显示 或 弃用 | 9 |
| 22 | 欢迎页 HOW IT WORKS 3 步 | 空状态的引导，或子页"帮助" | 9 |
| 23 | 欢迎页 feature badges | 弃用（主控台已体现功能）| 9 |

---

## 7. 阶段分解对照

| 阶段 | 主要产出 | 验证点 |
|------|------|------|
| 0 | 本文档 | 用户 review + 确认所有决策 |
| 1 | 色板 CSS 变量化 | 目测现有界面色调一致、细微更新 |
| 2 | 四区骨架（占位）| 五格都在、位置正确、内容先挤进去 |
| 3 | 左 nav | Logo + 副标 + 菜单 + 装饰、点击切 active_nav |
| 4 | Top bar | 10 元素齐、弹层交互工作、sidebar 字体/主题/书签功能搬迁完成 |
| 5 | 中央 reader 重做 | 木质外框、6 按钮控制条、目录/摘录触发 |
| 6 | Right AI（风险）| 4 tab、卡片回答、自定义 input 替换 chat_input、Enter 提交、流式输出仍在 |
| 7 | Bottom 4 cards | 书架 4 本、摘录近 1 条、上传区、统计 4 指标 + 连续天数 + 与上周 delta |
| 8 | 像素装饰 | 书柜/台灯/植物/咖啡杯/木纹贴图、整体"书房化" |
| 9 | 空状态 + 清理 zine + 响应式 | 无书引导、zw-* 删除、平板/手机折叠 |

---

## 8. 开工前确认清单（全部已定）

### 技术决策
- [x] 阶段数：10（0-9）
- [x] 不用 feature flag
- [x] 布局用 st.columns + CSS Grid 混合
- [x] st.chat_input 替换为 st.form + st.text_input
- [x] 新 CSS 前缀 mc-*
- [x] 色板严格按 spec 规范
- [x] 保留所有现有功能、不做技术栈迁移
- [x] 复用现有像素 SVG 资产（猫/蘑菇/火把/心/星）

### 范围 & 优先级决策（2026-04-24 用户确认）

1. **严格按设计图做 UI，设计图里没有的 UI 先不展示**（对应代码保留，等后续需要再暴露入口）
   - ✅ **字体切换**：设计图 Top Bar 是 `Aa` 字号图标。首版把字号 + 字体一起塞进 Aa 弹层；如果视觉拥挤，**砍字体切换**（字号是核心，字体是锦上添花，而且还没独立入口需求）
   - ✅ **书签列表**：设计图只有"点击书签 icon 保存当前位置"，**不展示列表**（代码保留 `_load_bookmarks()` 和 list 逻辑，UI 暂时不暴露）
   - ✅ **笔记导出 Markdown 按钮**：设计图没画，**首版不做 UI 入口**（代码保留 `_build_export_markdown()`）

2. **不做独立欢迎页**：
   - 无书状态 = 主控台 + 空状态
   - 首次访问 = 直接主控台，左 nav/topbar 都正常渲染，中央显示"上传一本书"引导

3. **子页策略：先做占位**
   - 左 nav 的 7 个菜单项：正在阅读 = 默认主控台视图；**书架/上传书籍/摘录笔记/AI 助读/阅读设置/阅读统计** 点击后跳**占位子页**（显示"功能即将上线"+ 返回按钮）
   - 但底部 4 张卡片**必须做出内容**（书架卡 4 本封面 + 摘录卡一条 + 上传卡可用 + 统计卡 4 指标）。主控台的体验完整，子页留坑下轮补。
   - 注：上传书籍菜单其实和底部上传卡重复，但先按 spec 保留菜单项，都跳占位子页

4. **菜单项含义对齐**（用户确认）：
   - 正在阅读 = 回到主控台默认视图
   - 书架 = 所有上传过的书的列表（但因为 localStorage 容量限制，只存元数据，见下条）

5. **书架方案：A - 半功能（纯前端）**
   - 新增 `_LS_LIBRARY_KEY = "reading_buddy_library_v1"`
   - 数据结构：`{book_key: {title, author, chapter_count, uploaded_at, last_opened_at, cover_color}}`
   - **不存文件 bytes**（太大，localStorage 装不下）
   - 用户点书架里某本书 → 如果当前 session 有对应 `file_bytes` 就直接读；没有就弹"请重新上传《xxx》以继续"
   - 底部"我的书架卡片"显示最近 4 本（没有文件时封面标灰 + 提示）
   - 阅读进度 / 书签 / 笔记仍跨 session 保留（用的是原有的 `_LS_PROGRESS_KEY` 等）
   - 未来升级方案：加 Supabase 后端真正存文件（不在本次 UI 改版范围）

---

## 9. 阶段粒度微调（基于最终范围）

| 阶段 | 微调说明 |
|------|------|
| 0 | 本文档，就此 commit |
| 1 | 色板 — 不变 |
| 2 | 骨架 — 增加 5 个占位子页结构（`_active_nav` state 决定显示哪个） |
| 3 | 左 nav — 7 菜单项点击切 `_active_nav`；占位子页只渲染"即将上线" |
| 4 | Top bar — 字号 Aa 弹层含字体（若拥挤则砍字体）；书签 icon 只做"加入"动作不展列表；主题 icon 弹层 5 套主题 |
| 5 | Center reader — 6 按钮控制条；目录按钮弹层（章节列表）；摘录按钮触发现有笔记表单 |
| 6 | Right AI — 用 `st.form + st.text_input + st.form_submit_button` 替换 `st.chat_input`，Enter 提交 |
| 7 | Bottom 4 cards — 书架卡引入 `_LS_LIBRARY_KEY`；统计卡引入 `_LS_DAILYSTREAK_KEY` + 与上周 delta 算法 |
| 8 | 像素装饰 — 复用旧资产，新画书柜 / 台灯 / 植物 |
| 9 | 空状态 + 删除 zine-welcome + 响应式 |

---

## 10. 第一轮范围外（后续）

这些在 spec 里提到但本次改版**不做**，留给下一轮：

- 书签列表 UI（Top Bar icon 弹层显示所有书签）
- 笔记导出 Markdown UI 入口
- 字体切换（如果 Aa 弹层装不下就删）
- 所有子页的实际内容（本次只做占位）
- 独立首页/欢迎页
- Supabase 后端（书架真正跨设备同步）
- 搜索功能（Top Bar 搜索 icon 可能先做占位弹层，功能留坑）
