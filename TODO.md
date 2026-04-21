# TODO

## 🔴 已知 Bug / 数据风险

- [ ] **P0 持久化**：`_PROGRESS_FILE` / `_BOOKMARKS_FILE` 写在 Streamlit Cloud 容器的临时文件系统，冷启即清。同时 app 无 user identity，所有用户共写一个 JSON —— 同名书会互相覆盖进度，朋友的书签也会出现在你侧栏。待决定方案：
  - A: 只修持久化，用户共用（Gist，~1h）
  - B: 持久化 + 隔离（localStorage 组件，~1.5h）
  - C: Supabase + magic-link 登录（~3h）
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

## 🎨 UI 审美扩展（/design-brainstorm 产出）

- [ ] `/animate` 翻页 pixel 书页翻转动画（transform3d + steps 离散）
- [ ] `/delight` 章末读完像素庆祝（pixel 花瓣 / 猫猫冒 Z）
- [ ] `/colorize` moss 绿（目前只在 kicker）承载"已读"语义 —— 章节列表右侧打 moss 小方块
- [ ] `/typeset` 读书 body 字体增加"仿宋"、"隶书"选项，做经典中文视觉
- [ ] `/adapt` 移动端翻页改左右 swipe 手势
- [ ] `/overdrive` 欢迎页猫猫 parallax + 随日期变装饰（中秋换月亮、春节换春联）
- [ ] `/clarify` 全站 microcopy 再过一遍（"加入当前位置"→"收藏本页" 之类）
