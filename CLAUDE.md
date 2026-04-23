# CLAUDE.md

AI 协作上下文。新会话开始前读一遍。

## 项目是什么

**嘟哒（DUDA）** — 单文件 Streamlit 中文电子书阅读器 + AI 共读。仓库 `rushtheworld707-bit/my-reading-buddy`。

## 文件结构（全部内容）

```
my-reading-buddy/
├── .github/workflows/ci.yml    # ruff + py_compile（push 即跑）
├── docs/design-preview.png     # UI 改版预览图
├── streamlit_app.py            # ~3800 行，所有代码在这一个文件
├── requirements.txt            # 8 个包
├── README.md
├── TODO.md                     # 活的 backlog
├── CLAUDE.md                   # 本文件
├── DESIGN_SPEC.md              # UI 改版设计规格书（SSOT，946 行）
└── MIGRATION.md                # UI 改版迁移计划（阶段拆分 + 技术决策）
```

没有 `src/`、没有模块拆分、没有测试。**所有改动都在 `streamlit_app.py`**。

## 工作流硬约束

1. **改完直接 commit + push，不需要确认**。用户 [memory 已授权](#)：「改完直接提交推送到 GitHub，Streamlit Cloud 会自动部署」。
2. **不要修改用户系统配置**（git email / username / global config）。GitHub 正确邮箱是 `rushtheworld707@gmail.com`。
3. **不要用 `--no-verify` 跳过 hooks**，除非用户明说。
4. CI 是异步的，push 后 ~16s 出结果；Streamlit Cloud 部署独立进行，~1-2 分钟。CI 挂了不会拦住部署。
5. 不加测试 / 不重构旧代码 / 不做防御性兜底，除非任务要求。

## 本地验证命令

Windows 环境下的 `python` 有可能是 Store 假 python（exit 49）。用这些代替真正的验证：

```bash
# 语法 + 编译（CI 里也是这个）
python -m py_compile streamlit_app.py

# 静态分析（CI 里也是这个）
ruff check streamlit_app.py --select E9,F63,F7,F82,F401
```

改完推之前能本地跑这两个就跑一下。

## 代码心智模型

### 页面状态机

```
is_welcome = "file_bytes" not in session_state
├── is_welcome: 全屏欢迎页（.zine-welcome）+ 中央上传
└── has_file:   阅读页（.reading-area）+ 侧栏（章节/书签/笔记/导出/设置）
```

两种页面共用整个 `streamlit_app.py`，用顶层 `if has_file:` 分叉。

### CSS class 命名约定（严格）

- `.zw-*` = **zine-welcome**（欢迎页元素）
  - 例：`.zw-title` / `.zw-hero` / `.zw-howto` / `.zw-step` / `.zw-stars` / `.zw-mushroom`
- `.rd-*` = **reading area**（阅读页元素）
  - 例：`.rd-topbar` / `.rd-clock` / `.rd-focus-flag`
- `.rb-*` = **reading buddy** 运行时注入的 DOM
  - 例：`.rb-dict-overlay` / `#rb-share-btn` / `.rb-fw-flash`
- `.book-page` / `.book-spread` / `.page-num` / `.nav-row` / `.progress-container` — 核心阅读组件

**新增元素时必须沿用前缀**，不要造 `.page-xxx` 或 `.main-xxx` 这种无归属的名字。

### 调色板（hardcoded hex 满天飞，不要引入新色）

```
#3b2e1e  ink      主文字 / 深棕墨
#c25a44  terra    红土 / 强调 / shadow
#d4b54c  mustard  芥黄 / shadow 备选
#4a6d4e  moss     绿调点缀
#7a96b4  dusty    蓝调点缀
#fffaec  cream    白纸
#f3e9cf  paper    浅米（app 背景）
#e8dcbc  paper-2  次级米色
```

所有带颜色的新 SVG / 像素装饰都从这里选。

### LocalStorage keys（都是 v1）

```python
_LS_PROGRESS_KEY   = "reading_buddy_progress_v1"    # {book_key: {chapter, page, updated_at}}
_LS_BOOKMARKS_KEY  = "reading_buddy_bookmarks_v1"   # {book_key: [{ch, page, ts}]}
_LS_MESSAGES_KEY   = "reading_buddy_messages_v1"    # {book_key: [{role, content}]}
_LS_NOTES_KEY      = "reading_buddy_notes_v1"       # {book_key: [{id, ch, page, passage, note, ts}]}
_LS_READTIME_KEY   = "reading_buddy_readtime_v1"    # {book_key: seconds}
```

- `book_key` 现在就是 `file_name`（含扩展名）。
- 读：`_ls_read_dict(key)` → dict。写：`_ls_write_dict(key, dict)`。
- Python 和 JS 两边都能读写同一个 localStorage，且在 session 内通过 `streamlit-local-storage` 同步。

### AI 后端

- `OpenAI(api_key=st.secrets["ARK_API_KEY"], base_url="https://ark.cn-beijing.volces.com/api/v3")`
- 模型 ID 从 `st.secrets["ARK_MODEL_ID"]`。
- 走 `chat.completions.create(stream=True)` + `st.write_stream`。
- 发送上下文：当前章节全文（>8000 字头尾夹）+ 当前 spread 精确位置 + 最近 8 条历史消息。

### Pixel icons

文件头部 `PX_ICON = {...}` 存 SVG 字符串。当前有：`upload / read / chat / keyboard / pin / palette / clock / save / robot / download`。

需要新图标时：直接在 dict 里加一项，`viewBox="0 0 16 16"`，用 `<rect>` 像素画，主色 `#3b2e1e`，强调色可用 terra/mustard。

### 主题 / 字体 / 配色

- `READING_THEMES` dict：bg + fg 二元组。加主题就在里面加一项。
- 字体切换在侧栏 selectbox，`_font_stacks` dict 存 CSS font-family 字符串。
- `theme_css` 作为 inline style 注入 `.book-spread`。

## 常见坑

### Streamlit ↔ JS 通信

- **Python → JS**：通过 DOM 数据属性传递，例如 `<div class="rd-book-key" data-key="{book_key}">`，JS 里 `querySelector('.rd-book-key').dataset.key`。
- **JS → Python**：没有直接路径。用 `localStorage` 写入 → 下次 rerun 时 Python 读。不要尝试 postMessage / iframe 双向通信（Streamlit 没有官方支持）。
- 所有注入 JS 都在 `components.html(..., height=0)` 里，用 `window.parent.document` 操作主文档。

### 专注模式混合式隐藏

`focus_mode` 用 `body:has(.rd-focus-flag)` + CSS `display:none` 隐藏 UI。对几个顽固场景用了兜底：
- `st-key-XXX` 类来 target 特定 button（Streamlit 给 `key=` 参数的 widget 自动加的）
- `:has(.ai-chat-heading) ~ [data-testid="stElementContainer"]` sibling selector 一次性隐藏整个 AI 聊天区

### `st.button` 渲染顺序

`st.chat_input` 永远在主区域**底部 docked**，无视代码中出现位置。其他 button 按代码顺序从上到下渲染。

### 双击选词在中文里只选 1 字

词典悬浮用 `dblclick` 触发 → 一般只拿到 1 个汉字（浏览器默认行为）。想看多字词的话，用户得手动拖选。**接受这个限制**，不要试图写 JS 做中文分词（代价远大于价值）。

### `components.html` 的 height

- `height=0`：完全不占位（JS 运行但无可见 UI）
- `height=36`（键盘提示那条）：留一行高度
- 所有 `components.html` 在**焦点模式**下都会被 CSS 隐藏（`iframe[title*="components"]` 选择器）

## 部署模型

```
你 push → GitHub
            ├─→ Actions CI（ruff + py_compile，~16s，异步）
            └─→ Streamlit Cloud 拉代码 → 部署（~1-2 min）
                https://<app>.streamlit.app/
```

Secrets（`ARK_API_KEY` / `ARK_MODEL_ID`）在 Streamlit Cloud Dashboard → App settings → Secrets 配置，**不走 git**。

## 任务清单

见 [TODO.md](./TODO.md)。里面按优先级和 skill 视角分好了组。

## 历史上下文

这个项目经过多轮 `/critique` / `/polish` / `/audit` 迭代，视觉分数持续在 32-38/40 徘徊，用户追求的是"像素杂志风 + zine-ish 可爱感"。不要引入 Material Design / Tailwind 默认风格，会毁掉整体调性。
