import re
import io
import os
import glob
import html
import json
import tempfile
import zipfile
import chardet
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from ebooklib import epub
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 页面基础配置
st.set_page_config(page_title="嘟哒", layout="wide")

# 像素 SVG 图标库（替换 emoji，与猫 SVG 同像素语法：单色块 + crispEdges）
# 调色板：#3b2e1e ink / #c25a44 terra / #d4b54c mustard / #4a6d4e moss / #fffaec cream
PX_ICON = {
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="7" y="2" width="2" height="9" fill="#3b2e1e"/><rect x="5" y="4" width="2" height="1" fill="#3b2e1e"/><rect x="9" y="4" width="2" height="1" fill="#3b2e1e"/><rect x="3" y="6" width="2" height="1" fill="#3b2e1e"/><rect x="11" y="6" width="2" height="1" fill="#3b2e1e"/><rect x="2" y="13" width="12" height="1" fill="#3b2e1e"/><rect x="2" y="13" width="1" height="2" fill="#3b2e1e"/><rect x="13" y="13" width="1" height="2" fill="#3b2e1e"/></svg>',
    "read": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="1" y="3" width="6" height="1" fill="#3b2e1e"/><rect x="9" y="3" width="6" height="1" fill="#3b2e1e"/><rect x="1" y="3" width="1" height="10" fill="#3b2e1e"/><rect x="6" y="3" width="1" height="10" fill="#3b2e1e"/><rect x="9" y="3" width="1" height="10" fill="#3b2e1e"/><rect x="14" y="3" width="1" height="10" fill="#3b2e1e"/><rect x="1" y="12" width="14" height="1" fill="#3b2e1e"/><rect x="2" y="5" width="3" height="1" fill="#c25a44"/><rect x="2" y="7" width="3" height="1" fill="#c25a44"/><rect x="2" y="9" width="3" height="1" fill="#c25a44"/><rect x="10" y="5" width="3" height="1" fill="#c25a44"/><rect x="10" y="7" width="3" height="1" fill="#c25a44"/><rect x="10" y="9" width="3" height="1" fill="#c25a44"/></svg>',
    "chat": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="2" y="3" width="12" height="1" fill="#3b2e1e"/><rect x="2" y="10" width="8" height="1" fill="#3b2e1e"/><rect x="1" y="4" width="1" height="6" fill="#3b2e1e"/><rect x="14" y="4" width="1" height="6" fill="#3b2e1e"/><rect x="4" y="11" width="2" height="1" fill="#3b2e1e"/><rect x="5" y="12" width="1" height="1" fill="#3b2e1e"/><rect x="4" y="6" width="2" height="2" fill="#c25a44"/><rect x="7" y="6" width="2" height="2" fill="#c25a44"/><rect x="10" y="6" width="2" height="2" fill="#c25a44"/></svg>',
    "keyboard": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="1" y="4" width="14" height="1" fill="#3b2e1e"/><rect x="1" y="11" width="14" height="1" fill="#3b2e1e"/><rect x="1" y="4" width="1" height="8" fill="#3b2e1e"/><rect x="14" y="4" width="1" height="8" fill="#3b2e1e"/><rect x="3" y="6" width="2" height="1" fill="#3b2e1e"/><rect x="6" y="6" width="2" height="1" fill="#3b2e1e"/><rect x="9" y="6" width="2" height="1" fill="#3b2e1e"/><rect x="12" y="6" width="1" height="1" fill="#3b2e1e"/><rect x="3" y="8" width="2" height="1" fill="#3b2e1e"/><rect x="6" y="8" width="2" height="1" fill="#3b2e1e"/><rect x="9" y="8" width="2" height="1" fill="#3b2e1e"/><rect x="12" y="8" width="1" height="1" fill="#3b2e1e"/><rect x="4" y="10" width="8" height="1" fill="#3b2e1e"/></svg>',
    "pin": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="6" y="2" width="4" height="1" fill="#3b2e1e"/><rect x="5" y="3" width="1" height="4" fill="#3b2e1e"/><rect x="10" y="3" width="1" height="4" fill="#3b2e1e"/><rect x="6" y="3" width="4" height="4" fill="#c25a44"/><rect x="7" y="4" width="1" height="1" fill="#e07b5a"/><rect x="3" y="7" width="10" height="2" fill="#3b2e1e"/><rect x="7" y="9" width="2" height="5" fill="#3b2e1e"/></svg>',
    "palette": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="4" y="2" width="8" height="1" fill="#3b2e1e"/><rect x="3" y="3" width="1" height="1" fill="#3b2e1e"/><rect x="12" y="3" width="1" height="1" fill="#3b2e1e"/><rect x="2" y="4" width="1" height="6" fill="#3b2e1e"/><rect x="13" y="4" width="1" height="6" fill="#3b2e1e"/><rect x="3" y="10" width="1" height="2" fill="#3b2e1e"/><rect x="4" y="12" width="3" height="1" fill="#3b2e1e"/><rect x="7" y="11" width="1" height="1" fill="#3b2e1e"/><rect x="8" y="10" width="5" height="1" fill="#3b2e1e"/><rect x="4" y="4" width="2" height="2" fill="#c25a44"/><rect x="9" y="4" width="2" height="2" fill="#d4b54c"/><rect x="4" y="7" width="2" height="2" fill="#4a6d4e"/><rect x="9" y="7" width="2" height="2" fill="#7a96b4"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="5" y="2" width="6" height="1" fill="#3b2e1e"/><rect x="5" y="13" width="6" height="1" fill="#3b2e1e"/><rect x="3" y="3" width="2" height="1" fill="#3b2e1e"/><rect x="11" y="3" width="2" height="1" fill="#3b2e1e"/><rect x="3" y="12" width="2" height="1" fill="#3b2e1e"/><rect x="11" y="12" width="2" height="1" fill="#3b2e1e"/><rect x="2" y="4" width="1" height="8" fill="#3b2e1e"/><rect x="13" y="4" width="1" height="8" fill="#3b2e1e"/><rect x="7" y="5" width="2" height="4" fill="#3b2e1e"/><rect x="8" y="8" width="3" height="1" fill="#c25a44"/></svg>',
    "save": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="2" y="2" width="12" height="1" fill="#3b2e1e"/><rect x="2" y="13" width="12" height="1" fill="#3b2e1e"/><rect x="2" y="2" width="1" height="12" fill="#3b2e1e"/><rect x="13" y="2" width="1" height="12" fill="#3b2e1e"/><rect x="4" y="3" width="7" height="3" fill="#3b2e1e"/><rect x="5" y="4" width="2" height="2" fill="#c25a44"/><rect x="4" y="8" width="8" height="5" fill="#3b2e1e"/><rect x="5" y="9" width="6" height="1" fill="#fffaec"/><rect x="5" y="11" width="6" height="1" fill="#fffaec"/></svg>',
    "robot": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="7" y="1" width="2" height="2" fill="#3b2e1e"/><rect x="3" y="3" width="10" height="1" fill="#3b2e1e"/><rect x="3" y="9" width="10" height="1" fill="#3b2e1e"/><rect x="3" y="3" width="1" height="7" fill="#3b2e1e"/><rect x="12" y="3" width="1" height="7" fill="#3b2e1e"/><rect x="5" y="5" width="2" height="2" fill="#c25a44"/><rect x="9" y="5" width="2" height="2" fill="#c25a44"/><rect x="6" y="8" width="4" height="1" fill="#3b2e1e"/><rect x="1" y="5" width="2" height="1" fill="#3b2e1e"/><rect x="13" y="5" width="2" height="1" fill="#3b2e1e"/><rect x="4" y="10" width="2" height="4" fill="#3b2e1e"/><rect x="10" y="10" width="2" height="4" fill="#3b2e1e"/></svg>',
}

# 2. 全局自定义样式
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Noto+Serif+SC:wght@400;700;900&family=Noto+Sans+SC:wght@400;500;700&family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">', unsafe_allow_html=True)
st.markdown("""
<style>
/* 主标题：像素刊头（原 Caveat 手写体像素化） */
.handwrite-title {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 13px;
    font-weight: 400;
    color: #3b2e1e;
    text-align: center;
    margin: 10px 0 14px 0;
    letter-spacing: 3px;
    text-shadow: 2px 2px 0 #d4b54c;
    text-transform: uppercase;
}
.handwrite-title .hw-dot {
    color: #c25a44;
    margin: 0 10px;
    text-shadow: none;
}
/* 书页区域 */
.book-spread {
    display: flex;
    flex: 1;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.book-page {
    flex: 1;
    padding: 32px 36px;
    min-height: 420px;
    line-height: 1.85;
    letter-spacing: 0.3px;
    word-wrap: break-word;
    position: relative;
}
.book-page-left {
    border-right: 1px solid rgba(255,255,255,0.08);
}
.book-page p {
    text-indent: 2em;
    margin: 0.5em 0;
}
.book-page p:first-child {
    margin-top: 0;
}
.book-page .page-num {
    position: absolute;
    bottom: 12px;
    font-size: 12px;
    opacity: 0.4;
}
.book-page-left .page-num { left: 36px; }
.book-page-right .page-num { right: 36px; }

/* progress / page-indicator / time-display 的基础态定义从未渲染（一进 reading-area 就被覆盖），已移除；欢迎页旧 .welcome-* 一并移除（含 BAN 2 渐变文字） */

/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
    /* 移动端：单页模式 */
    .book-spread {
        flex-direction: column;
    }
    .book-page {
        padding: 20px 16px;
        min-height: 280px;
        font-size: 16px;
    }
    .book-page-left {
        border-right: none;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    h1 { font-size: 24px !important; }
    h2, .stSubheader { font-size: 18px !important; }
}

@media (max-width: 480px) {
    .book-page {
        padding: 16px 12px;
        min-height: 220px;
        font-size: 15px;
    }
}

/* ===== 阅读区域：像素风（与欢迎页同一套调色） ===== */
/* 顶部 header 保持存在（防止 Streamlit 内部渲染失衡），只换成奶油色与页面融合 */
body:has(.reading-area) header[data-testid="stHeader"] {
    background: #f3e9cf !important;
}
/* C2：顶栏右上角 toolbar 按钮透明化（Share / GitHub / 三点菜单等）
   不用 display:none（会触发 DOM 累加 bug），用 opacity + hover 恢复
   保留 pointer-events，需要时 hover 仍能点到 */
body:has(.reading-area) [data-testid="stToolbar"] {
    opacity: 0.25 !important;
    transition: opacity 0.25s ease !important;
}
body:has(.reading-area) [data-testid="stToolbar"]:hover {
    opacity: 1 !important;
}
/* 整体背景奶油色（不动 max-width / padding / min-height，避免影响 chat_input 等元素的定位） */
body:has(.reading-area) [data-testid="stMainBlockContainer"],
body:has(.reading-area) [data-testid="stAppViewContainer"] > .main > div,
body:has(.reading-area) .main .block-container,
body:has(.reading-area) [class*="block-container"] {
    background-color: #f3e9cf !important;
}

/* A1：侧栏背景奶油 + 右侧虚线分隔（仅改最外层 section，不动任何子元素） */
body:has(.reading-area) section[data-testid="stSidebar"] {
    background: #e8dcbc !important;
    border-right: 2px dashed #3b2e1e !important;
}
/* A2：侧栏文字颜色深棕 + Zpix 像素字体
   只命中 widget 的 <label>、独立 st.markdown/st.caption 的段落/粗体
   —— 刻意避开按钮内的 stMarkdownContainer（按钮留到 A3 统一改），
   避免当前阶段按钮文本字体或颜色错乱 */
body:has(.reading-area) section[data-testid="stSidebar"] label,
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stMarkdown"] strong {
    color: #3b2e1e !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
}

/* A3：侧栏按钮方角像素化（与欢迎页 upload 按钮同一视觉语言）
   只改 stButton 的 button 元素本体和其内部 <p>；不碰 chat_input 的 send 按钮
   （chat_input 是 stChatInput，不是 stButton，自然不会被命中） */
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: #3b2e1e !important;
    color: #f3e9cf !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 3px 3px 0 #d4b54c !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
    transition: transform 0.08s steps(2), box-shadow 0.08s steps(2), background 0.15s !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: #c25a44 !important;
    color: #fffef8 !important;
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0 #d4b54c !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button p {
    color: inherit !important;
    font-family: inherit !important;
}

/* A4：侧栏 selectbox 最外层可见框方角 + 奶油底
   只命中 BaseWeb select 的外层 div；不动弹出层（弹出层走 portal 挂到 body 上，
   不是这个选择器的后代），不动 position/display 相关属性 */
body:has(.reading-area) section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #fffaec !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 2px 2px 0 #d4b54c !important;
    color: #3b2e1e !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
}

/* A5：侧栏 slider 拇指方角像素化
   只改 role="slider" 的拇指本体；轨道与刻度保持 Streamlit 默认（不碰尺寸、
   位置、transform，避免影响拖拽手势的命中区域） */
body:has(.reading-area) section[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {
    background: #c25a44 !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 2px 2px 0 #3b2e1e !important;
}

/* A6：侧栏 number_input（跳转页码）方角像素化
   分两部分：① 输入框本体 ② +/- 步进按钮；都只改颜色/边框/字体，不动尺寸与布局 */
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] input {
    background: #fffaec !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    color: #3b2e1e !important;
    font-family: 'Press Start 2P', 'Zpix', monospace !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {
    background: #3b2e1e !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    color: #f3e9cf !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] button:hover {
    background: #c25a44 !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] button svg {
    fill: #f3e9cf !important;
    color: #f3e9cf !important;
}

/* B1：主区分隔线（st.divider）换成虚线深棕；AI 小标题本身已由
   MainBlockContainer h3 规则自动像素化，不再重复 */
body:has(.reading-area) [data-testid="stMainBlockContainer"] hr {
    border: none !important;
    border-top: 2px dashed #3b2e1e !important;
    background: transparent !important;
    margin: 18px 0 !important;
    opacity: 1 !important;
}

/* B2：AI 聊天气泡只改 bg + text color，不动 border-radius/position/margin
   —— 之前的 bug 正是因为改了 margin 和通配 * color 导致 chat_input 跑位 */
body:has(.reading-area) [data-testid="stChatMessage"] {
    background: #fffaec !important;
}
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code {
    color: #3b2e1e !important;
}

/* B3（新版）：chat_input 的 textarea 同时设 bg + text color + 字体
   不碰 stChatInput / stBottom 外层容器的 position/margin/bg/border/box-shadow
   textarea 是叶子元素，覆盖其 bg 不影响布局定位 */
body:has(.reading-area) [data-testid="stChatInput"] textarea {
    background: #fffaec !important;
    color: #3b2e1e !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
}
body:has(.reading-area) [data-testid="stChatInput"] textarea::placeholder {
    color: #6b5843 !important;
    opacity: 0.6 !important;
}

/* B3.5：填补 chat_input 周围的黑空白
   只改 background，不动 position/margin/padding/size */
body:has(.reading-area) [data-testid="stApp"],
body:has(.reading-area) [data-testid="stBottom"],
body:has(.reading-area) [data-testid="stBottom"] > div,
body:has(.reading-area) [data-testid="stChatInput"] {
    background: #f3e9cf !important;
}
/* B3.6：chat_input 内层 baseweb 包装（真正那个黑色圆角框）也统一成米白
   覆盖多种可能的内层 DOM 结构 */
body:has(.reading-area) [data-testid="stChatInput"] > div,
body:has(.reading-area) [data-testid="stChatInput"] > div > div,
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="textarea"],
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="input"],
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="base-input"] {
    background: #fffaec !important;
}

/* B4：chat_input 外观完整像素化
   —— 仅最外层直接子 div 加边框 + 偏移阴影（避免多层重复描边）
   —— 内层 baseweb / textarea 去掉圆角和边框，保持方角一致 */
body:has(.reading-area) [data-testid="stChatInput"] > div {
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 3px 3px 0 #d4b54c !important;
}
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="textarea"],
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="input"],
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="base-input"],
body:has(.reading-area) [data-testid="stChatInput"] textarea {
    border-radius: 0 !important;
    border: none !important;
}
/* 发送按钮（右侧向上箭头）像素化：方角深棕底 + 米白图标 */
body:has(.reading-area) [data-testid="stChatInput"] button {
    background: #3b2e1e !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
}
body:has(.reading-area) [data-testid="stChatInput"] button:hover {
    background: #c25a44 !important;
}
body:has(.reading-area) [data-testid="stChatInput"] button svg {
    fill: #f3e9cf !important;
    color: #f3e9cf !important;
}


/* 章节标题（只改主区里的，避开侧栏和 chat 内部） */
body:has(.reading-area) [data-testid="stMainBlockContainer"] h1,
body:has(.reading-area) [data-testid="stMainBlockContainer"] h2,
body:has(.reading-area) [data-testid="stMainBlockContainer"] h3 {
    color: #3b2e1e !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 2px;
}

/* D1：阅读页顶部杂志刊头带（与欢迎页 zw-topbar 视觉呼应） */
.rd-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 14px;
    margin-bottom: 14px;
    background: #e8dcbc;
    border-top: 2px solid #3b2e1e;
    border-bottom: 2px dashed #3b2e1e;
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: #3b2e1e;
    text-transform: uppercase;
    animation: rd-fade-in 0.55s ease-out both;
}

/* D2：阅读页 / 欢迎页切换淡入动画（纯 CSS，不动 DOM） */
@keyframes rd-fade-in {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.reading-area {
    animation: rd-fade-in 0.55s ease-out 0.08s both;
}
.zine-welcome.zw-top {
    animation: rd-fade-in 0.6s ease-out both;
}
.zine-welcome.zw-bottom {
    animation: rd-fade-in 0.6s ease-out 0.15s both;
}
.rd-topbar .rd-mid {
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace;
    font-size: 12px;
    letter-spacing: 1.5px;
    color: #3b2e1e;
    max-width: 50%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-transform: none;
}
.rd-topbar .dot {
    color: #c25a44;
    margin: 0 6px;
}
.rd-topbar .rd-clock {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-family: 'Press Start 2P', monospace;
    font-size: 10px;
    letter-spacing: 1px;
}
.rd-topbar .rd-clock .px-ic {
    width: 10px;
    height: 10px;
    margin-bottom: 0;
}
/* 进度条：方形像素 */
body:has(.reading-area) .progress-container {
    background: #e8dcbc !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    height: 10px !important;
    box-shadow: 3px 3px 0 #d4b54c !important;
    padding: 0 !important;
}
body:has(.reading-area) .progress-fill {
    background: #c25a44 !important;
    border-radius: 0 !important;
}
/* 书页容器：虚线外框 + 芥末黄偏移阴影 */
.reading-area .book-spread {
    background: #fffaec !important;
    border: 2px dashed #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 6px 6px 0 #d4b54c !important;
    color: #3b2e1e !important;
    position: relative;
}
.reading-area .book-page-left {
    border-right: 1px dashed #3b2e1e !important;
}
.reading-area .book-page .page-num {
    color: #3b2e1e !important;
    opacity: 0.65 !important;
    font-family: 'Press Start 2P', monospace !important;
    font-size: 10px !important;
}
/* 书页四角的 [+] 像素标记 */
.reading-area .book-spread::before,
.reading-area .book-spread::after {
    position: absolute;
    font-family: 'Press Start 2P', monospace;
    font-size: 10px;
    color: #c25a44;
    z-index: 2;
    letter-spacing: 0;
}
.reading-area .book-spread::before { content: "[+]"; top: 8px; left: 10px; }
.reading-area .book-spread::after  { content: "[+]"; bottom: 8px; right: 10px; }

/* 页码信息：主行像素刊头字体，副行 Zpix 柔化 */
.reading-area .page-indicator {
    color: #3b2e1e !important;
    margin-top: 14px !important;
    text-align: center;
}
.reading-area .page-indicator .pg-main {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 10px;
    letter-spacing: 2px;
}
.reading-area .page-indicator .pg-sub {
    font-family: 'Zpix', 'Noto Sans SC', monospace;
    font-size: 11px;
    letter-spacing: 1px;
    opacity: 0.65;
    margin-top: 4px;
}

/* 翻页按钮：方角 + 深棕底 + 芥末黄偏移阴影 */
.reading-area .nav-btn {
    display: inline-flex;
    align-items: center;
    cursor: pointer;
    user-select: none;
    text-decoration: none !important;
    background: #3b2e1e !important;
    color: #f3e9cf !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0 #d4b54c !important;
    font-family: 'Press Start 2P', 'Zpix', monospace !important;
    font-size: 10px !important;
    letter-spacing: 2px !important;
    padding: 10px 18px !important;
    text-shadow: none !important;
    transition: transform 0.08s steps(2), box-shadow 0.08s steps(2), background 0.15s !important;
}
.reading-area .nav-btn:hover {
    background: #c25a44 !important;
    color: #fffef8 !important;
    border-color: #3b2e1e !important;
    transform: translate(-2px, -2px) !important;
    box-shadow: 6px 6px 0 #d4b54c !important;
}
.reading-area .nav-btn.nav-disabled {
    opacity: 0.35 !important;
    box-shadow: none !important;
    pointer-events: none !important;
}

/* ===== 阅读区域 + 导航按钮 =====
   book-spread、页码指示、翻页按钮在同一个 .reading-area 里，宽度严格一致 */
.reading-area {
    width: 100%;
}
.nav-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    margin-top: 4px;
}
/* 隐藏的 Streamlit 按钮（仅用于通过 JS 点击触发 rerun） */
.st-key-prev_page, .st-key-next_page {
    display: none !important;
}
div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] .st-key-prev_page) {
    display: none !important;
}

/* ===== 现代像素风欢迎页 (全屏覆盖) ===== */
/* 当 .zine-welcome 出现时隐藏 Streamlit 外壳，主内容区铺满 */
body:has(.zine-welcome) header[data-testid="stHeader"] {
    display: none !important;
}
body:has(.zine-welcome) section[data-testid="stSidebar"] {
    display: none !important;
}
body:has(.zine-welcome) [data-testid="stMainBlockContainer"],
body:has(.zine-welcome) [data-testid="stAppViewContainer"] > .main > div,
body:has(.zine-welcome) .main .block-container,
body:has(.zine-welcome) [class*="block-container"] {
    padding: 0 !important;
    max-width: 100% !important;
    background-color: #f3e9cf !important;
    min-height: 100vh;
}
body:has(.zine-welcome) .handwrite-title {
    display: none !important;
}

/* 中文像素字体 Zpix（最像素）from jsDelivr */
@font-face {
    font-family: 'Zpix';
    src: url('https://cdn.jsdelivr.net/gh/SolidZORO/zpix-pixel-font/dist/zpix.ttf') format('truetype');
    font-display: swap;
}

/* 调色盘：Stardew-ish 暖色 */
.zine-welcome {
    --zw-paper: #f3e9cf;
    --zw-paper-2: #e8dcbc;
    --zw-ink: #3b2e1e;
    --zw-ink-soft: #6b5843;
    --zw-terra: #c25a44;
    --zw-terra-soft: #e07b5a;
    --zw-moss: #4a6d4e;
    --zw-mustard: #d4b54c;
    --zw-dusty: #7a96b4;
}

@keyframes zw-fade-in {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes zw-pop {
    from { opacity: 0; transform: scale(0.92); }
    to   { opacity: 1; transform: scale(1); }
}
@keyframes zw-float {
    0%, 100% { transform: translateY(0); }
    50%      { transform: translateY(-6px); }
}
@keyframes zw-blink {
    0%, 49%  { opacity: 1; }
    50%, 100%{ opacity: 0; }
}
/* 标题像素弹跳（每一步缩放，带点8-bit感） */
@keyframes zw-bounce {
    0%   { opacity: 0; transform: scale(0); }
    40%  { opacity: 1; transform: scale(1.15); }
    70%  { transform: scale(0.94); }
    100% { transform: scale(1); }
}
/* 色条从左往右展开 */
@keyframes zw-bar-grow {
    from { width: 0; }
    to   { width: 180px; }
}
/* 副标题从左滑入 */
@keyframes zw-slide-in {
    from { opacity: 0; transform: translateX(-24px); }
    to   { opacity: 1; transform: translateX(0); }
}
/* 描述逐字显示（用 clip-path） */
@keyframes zw-typewriter {
    from { clip-path: inset(0 100% 0 0); }
    to   { clip-path: inset(0 0 0 0); }
}

.zine-welcome {
    position: relative;
    width: 100%;
    background-color: var(--zw-paper);
    background-image:
        url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='280' height='280'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.2 0 0 0 0 0.15 0 0 0 0 0.08 0 0 0 0.1 0'/></filter><rect width='280' height='280' filter='url(%23n)'/></svg>");
    padding: 36px 80px 100px;
    overflow: hidden;
    box-sizing: border-box;
    font-family: 'Noto Sans SC', 'PingFang SC', sans-serif;
}
/* 拆分为上下两段（上传器夹在中间），需要调整 padding 让视觉连续 */
.zine-welcome.zw-top {
    padding: 36px 80px 24px;
}
.zine-welcome.zw-bottom {
    padding: 24px 80px 60px;
}
/* 上传器外层块的横向 padding 与 zine 对齐 */
body:has(.zine-welcome) [data-testid="stHorizontalBlock"]:has(.zw-upload-label) {
    padding: 10px 80px 10px !important;
    background-color: var(--zw-paper);
}

/* 顶部刊头 */
.zw-topbar {
    position: relative;
    z-index: 4;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 0 10px;
    border-bottom: 2px solid var(--zw-ink);
    margin-bottom: 28px;
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    color: var(--zw-ink) !important;
    animation: zw-fade-in 0.6s ease-out both;
}
.zw-topbar span, .zw-topbar b { color: var(--zw-ink) !important; }
.zw-topbar .dot { color: var(--zw-terra) !important; margin: 0 4px; }

/* 四角装饰 */
.zw-corner {
    position: absolute;
    color: var(--zw-ink);
    font-family: 'Press Start 2P', monospace;
    font-size: 10px;
    opacity: 0.4;
    z-index: 2;
}
.zw-corner.tl { top: 10px; left: 12px; }
.zw-corner.tr { top: 10px; right: 12px; }
.zw-corner.bl { bottom: 10px; left: 12px; }
.zw-corner.br { bottom: 10px; right: 12px; }

/* Hero 双栏 */
.zw-hero {
    position: relative;
    z-index: 3;
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    gap: 60px;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
    padding: 10px 0 50px;
}

/* 左：文字（全部像素字体） */
.zw-eyebrow {
    font-family: 'Zpix', 'Press Start 2P', monospace;
    font-size: 14px;
    color: var(--zw-ink) !important;
    letter-spacing: 2px;
    margin-bottom: 8px;
    opacity: 0.6;
    animation: zw-fade-in 0.6s ease-out both;
}

.zw-kicker {
    display: inline-block;
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    color: var(--zw-moss) !important;
    letter-spacing: 3px;
    padding: 6px 10px;
    border: 2px solid var(--zw-moss);
    margin-bottom: 28px;
    animation: zw-fade-in 0.6s ease-out 0.15s both;
}

.zw-title {
    font-family: 'Zpix', 'Noto Serif SC', serif;
    font-size: 96px;
    font-weight: 400;
    line-height: 1.0;
    color: var(--zw-ink) !important;
    margin: 0 0 8px;
    letter-spacing: 8px;
    animation: zw-bounce 0.9s cubic-bezier(.34,1.56,.64,1) 0.2s both;
    text-shadow: 4px 4px 0 var(--zw-mustard);
    transform-origin: left center;
    -webkit-font-smoothing: none;
    -moz-osx-font-smoothing: grayscale;
}

.zw-title-bar {
    width: 180px;
    height: 10px;
    background-image: linear-gradient(90deg, var(--zw-terra) 20%, var(--zw-mustard) 20% 45%, var(--zw-moss) 45% 70%, var(--zw-dusty) 70%);
    image-rendering: pixelated;
    margin: 14px 0 18px;
    animation: zw-bar-grow 0.6s steps(9) 0.9s both;
}

.zw-subtitle-zh {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 22px;
    color: var(--zw-ink) !important;
    margin: 0 0 24px;
    letter-spacing: 4px;
    animation: zw-slide-in 0.5s cubic-bezier(.2,.8,.2,1) 1.3s both;
    -webkit-font-smoothing: none;
}

/* 描述逐字显示（typewriter） */
.zw-desc {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 14px;
    line-height: 1.9;
    color: var(--zw-ink-soft) !important;
    margin-bottom: 26px;
    max-width: 440px;
    -webkit-font-smoothing: none;
    position: relative;
}
.zw-desc .line {
    display: block;
    overflow: hidden;
    white-space: nowrap;
    animation: zw-typewriter 1.4s steps(30) both;
}
.zw-desc .line-1 { animation-delay: 1.7s; }
.zw-desc .line-2 { animation-delay: 3.1s; }
.zw-desc .caret {
    display: inline-block;
    width: 8px;
    height: 14px;
    background: var(--zw-terra);
    vertical-align: middle;
    margin-left: 2px;
    animation: zw-blink 1s step-end infinite;
    animation-delay: 4.5s;
    opacity: 0;
}
.zw-desc .caret.on { animation-delay: 4.5s; opacity: 1; }

.zw-formats {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    animation: zw-fade-in 0.6s ease-out 0.55s both;
}
.zw-tag {
    padding: 6px 10px;
    background: transparent;
    border: 2px solid var(--zw-ink) !important;
    color: var(--zw-ink) !important;
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    letter-spacing: 2px;
}

/* 右：像素艺术 */
.zw-art {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    animation: zw-pop 0.7s ease-out 0.35s both;
}
.zw-art svg {
    width: 100%;
    max-width: 360px;
    height: auto;
    image-rendering: pixelated;
    shape-rendering: crispEdges;
    animation: zw-float 4.5s ease-in-out infinite;
    filter: drop-shadow(4px 6px 0 rgba(59, 46, 30, 0.18));
}
.zw-art-caption {
    position: absolute;
    bottom: -10px;
    right: 20px;
    font-family: 'Press Start 2P', monospace;
    font-size: 8px;
    color: var(--zw-ink) !important;
    opacity: 0.45;
    letter-spacing: 2px;
}

/* HOW IT WORKS 面板 */
.zw-howto {
    position: relative;
    z-index: 3;
    max-width: 900px;
    margin: 20px auto 40px;
    padding: 18px 24px 20px;
    background: rgba(255, 255, 255, 0.35);
    border: 2px solid var(--zw-ink);
    box-shadow: 5px 5px 0 var(--zw-terra);
    animation: zw-fade-in 0.7s ease-out 0.7s both;
}
.zw-howto-title {
    font-family: 'Press Start 2P', monospace;
    font-size: 11px;
    color: var(--zw-terra) !important;
    letter-spacing: 2px;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px dashed var(--zw-ink);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.zw-howto-title .zw-meter {
    font-family: 'Press Start 2P', monospace;
    color: var(--zw-moss) !important;
    font-size: 9px;
}
.zw-steps {
    display: flex;
    justify-content: space-between;
    align-items: stretch;
    gap: 10px;
}
.zw-step {
    flex: 1;
    text-align: center;
    padding: 14px 10px;
    background: var(--zw-paper);
    border: 2px solid var(--zw-ink);
    transition: all 0.2s ease;
}
.zw-step:hover {
    transform: translate(-1px, -1px);
    box-shadow: 3px 3px 0 var(--zw-mustard);
}
.zw-step-num {
    font-family: 'Press Start 2P', monospace;
    font-size: 12px;
    color: var(--zw-mustard) !important;
    margin-bottom: 4px;
    letter-spacing: 2px;
}
.zw-step-icon {
    font-size: 30px;
    line-height: 1;
    margin-bottom: 6px;
}
.zw-step-label {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 14px;
    color: var(--zw-ink) !important;
    margin-bottom: 2px;
    -webkit-font-smoothing: none;
}
.zw-step-sub {
    font-family: 'Press Start 2P', monospace;
    font-size: 7px;
    color: var(--zw-ink-soft) !important;
    letter-spacing: 2px;
}
.zw-step-arrow {
    align-self: center;
    font-family: 'Press Start 2P', monospace;
    font-size: 14px;
    color: var(--zw-terra) !important;
    padding: 0 2px;
    animation: zw-float 2s ease-in-out infinite;
}

/* 特性徽章栏 */
.zw-features {
    position: relative;
    z-index: 3;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    max-width: 900px;
    margin: 0 auto 32px;
    padding: 0 20px;
    animation: zw-fade-in 0.7s ease-out 0.85s both;
}
.zw-feature {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: transparent;
    border: 1.5px dashed var(--zw-ink-soft);
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 12px;
    color: var(--zw-ink) !important;
    -webkit-font-smoothing: none;
}
.zw-feature .ic {
    font-size: 14px;
}

/* 底部像素装饰条 */
.zw-footer-strip {
    position: relative;
    z-index: 2;
    max-width: 900px;
    margin: 20px auto 0;
    padding-top: 16px;
    border-top: 2px dashed var(--zw-ink);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: 'Press Start 2P', monospace;
    font-size: 9px;
    color: var(--zw-ink-soft) !important;
    letter-spacing: 2px;
    animation: zw-fade-in 0.7s ease-out 1s both;
}
.zw-footer-strip .hearts { color: var(--zw-terra) !important; letter-spacing: 3px; }

/* 上传区标签 */
.zw-upload-label {
    font-family: 'Press Start 2P', monospace;
    font-size: 11px;
    color: var(--zw-terra) !important;
    letter-spacing: 3px;
    margin-bottom: 10px;
    text-align: center;
}
.zw-upload-label .caret {
    display: inline-block;
    margin-left: 4px;
    color: var(--zw-ink);
    animation: zw-blink 1.1s step-end infinite;
}

/* 上传器皮肤 */
body:has(.zine-welcome) [data-testid="stFileUploader"] {
    position: relative;
    z-index: 3;
    margin: 0 !important;
    animation: zw-fade-in 0.7s ease-out 0.9s both;
}
body:has(.zine-welcome) [data-testid="stFileUploader"] section {
    background: rgba(255, 255, 255, 0.55) !important;
    border: 2px dashed var(--zw-ink) !important;
    border-radius: 0 !important;
    padding: 22px 18px !important;
    box-shadow: 4px 4px 0 var(--zw-mustard) !important;
    transition: all 0.2s ease;
}
body:has(.zine-welcome) [data-testid="stFileUploader"] section:hover {
    transform: translate(-2px, -2px);
    box-shadow: 6px 6px 0 var(--zw-mustard) !important;
    background: rgba(255, 255, 255, 0.85) !important;
}
body:has(.zine-welcome) [data-testid="stFileUploader"] section p,
body:has(.zine-welcome) [data-testid="stFileUploader"] section small,
body:has(.zine-welcome) [data-testid="stFileUploader"] section > div > span {
    color: var(--zw-ink) !important;
    font-family: 'Noto Sans SC', sans-serif !important;
}
body:has(.zine-welcome) [data-testid="stFileUploader"] section > button,
body:has(.zine-welcome) [data-testid="stFileUploader"] section > div > button,
body:has(.zine-welcome) [data-testid="stFileUploaderDropzone"] button {
    background: var(--zw-ink) !important;
    color: var(--zw-paper) !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 8px 14px !important;
    font-family: 'Press Start 2P', monospace !important;
    font-size: 9px !important;
    letter-spacing: 2px !important;
}
body:has(.zine-welcome) [data-testid="stFileUploader"] section > button:hover,
body:has(.zine-welcome) [data-testid="stFileUploaderDropzone"] button:hover {
    background: var(--zw-terra) !important;
}
body:has(.zine-welcome) [data-testid="stFileUploader"] section > button p,
body:has(.zine-welcome) [data-testid="stFileUploaderDropzone"] button p {
    color: var(--zw-paper) !important;
    font-family: 'Press Start 2P', monospace !important;
}

@media (max-width: 900px) {
    .zw-hero { grid-template-columns: 1fr; gap: 30px; }
    .zw-title { font-size: 74px; letter-spacing: 10px; }
    .zine-welcome { padding: 32px 28px 80px; }
    .zw-art svg { max-width: 240px; }
}

/* ===== 像素图标通用 ===== */
.px-ic {
    display: inline-block;
    vertical-align: middle;
    image-rendering: pixelated;
    shape-rendering: crispEdges;
}
.zw-step-icon .px-ic { width: 28px; height: 28px; }
.zw-feature .ic .px-ic { width: 14px; height: 14px; margin-bottom: 1px; }
.ai-chat-heading .px-ic { width: 18px; height: 18px; margin-right: 8px; margin-bottom: 2px; }
body:has(.reading-area) section[data-testid="stSidebar"] .sbh .px-ic {
    width: 12px; height: 12px; margin-right: 6px; margin-bottom: 1px;
}

/* ===== 原生 Streamlit 提示态像素化（alert / toast / spinner） ===== */
/* st.warning / st.error / st.info / st.success 外框 */
body:has(.reading-area) [data-testid="stAlert"] {
    background: #fffaec !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0 #d4b54c !important;
    color: #3b2e1e !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
    padding: 14px 16px !important;
}
/* error 态改用 terra 色描边 / 投影，情绪层级清晰但仍然是像素语言 */
body:has(.reading-area) [data-testid="stAlertContentError"],
body:has(.reading-area) [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {
    border-color: #c25a44 !important;
    box-shadow: 4px 4px 0 #c25a44 !important;
}
body:has(.reading-area) [data-testid="stAlert"] p,
body:has(.reading-area) [data-testid="stAlert"] div,
body:has(.reading-area) [data-testid="stAlert"] span {
    color: #3b2e1e !important;
    font-family: inherit !important;
}
/* Toast（toast 可能挂在 body 根，不受 reading-area 作用域限制，不加 :has 前缀） */
[data-testid="stToast"],
[data-testid="stToastContainer"] [role="status"] {
    background: #fffaec !important;
    border: 2px solid #3b2e1e !important;
    border-radius: 0 !important;
    box-shadow: 3px 3px 0 #d4b54c !important;
    color: #3b2e1e !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
}
[data-testid="stToast"] * {
    color: #3b2e1e !important;
    font-family: inherit !important;
}
/* Spinner：方角 + 深棕骨架（默认是彩色圆环旋转，和像素风冲突） */
body:has(.reading-area) .stSpinner > div > div,
body:has(.reading-area) [data-testid="stSpinner"] > div > div {
    border-color: #3b2e1e #e8dcbc #e8dcbc #e8dcbc !important;
    border-radius: 0 !important;
    border-width: 3px !important;
}
body:has(.reading-area) .stSpinner,
body:has(.reading-area) [data-testid="stSpinner"] {
    color: #3b2e1e !important;
    font-family: 'Zpix', monospace !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="handwrite-title">'
    '<span class="hw-dot">■</span>SWEET SWEET HOMELAND<span class="hw-dot">■</span>'
    '</div>',
    unsafe_allow_html=True,
)

# 3. 上传文件：有书在读时放侧边栏，空态时放在欢迎页中央
SUPPORTED_FORMATS = ['epub', 'txt', 'pdf', 'mobi', 'azw3']
_has_prev_file = "file_bytes" in st.session_state and st.session_state.file_bytes
if _has_prev_file:
    uploaded_file = st.sidebar.file_uploader(
        "请上传一本电子书吧(๑•̀ㅂ•́)و✧",
        type=SUPPORTED_FORMATS,
        help="支持格式：EPUB、TXT、PDF、MOBI、AZW3",
        key="upload_sidebar",
    )
else:
    uploaded_file = None  # 稍后在欢迎页中渲染

# 4. 各格式解析函数

def _clean_text(text):
    """清理文本：合并多余空行，去除首尾空白"""
    # 将连续3个以上换行合并为2个
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 去除每行首尾多余空格
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

def _extract_chapter_title(soup):
    """从 HTML 中提取章节标题"""
    # 尝试从 h1, h2, h3, title 标签获取标题
    for tag in ['h1', 'h2', 'h3', 'title']:
        heading = soup.find(tag)
        if heading:
            title = heading.get_text(strip=True)
            if title and len(title) < 60:
                return title
    return None

@st.cache_data
def extract_text_from_epub(file_bytes):
    try:
        book = epub.read_epub(io.BytesIO(file_bytes))

        # href → item 映射（全路径 + basename 两种键）
        href_map = {}
        for item in book.get_items():
            if item.get_type() == 9:
                name = item.get_name()
                href_map[name] = item
                href_map[name.split('/')[-1]] = item

        def item_text(item):
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            return _clean_text(soup.get_text(separator='\n\n', strip=True))

        def flatten_toc(toc):
            result = []
            for entry in toc:
                if isinstance(entry, tuple):
                    section, children = entry
                    result.append((section.title or '', section.href or ''))
                    result.extend(flatten_toc(children))
                elif hasattr(entry, 'title'):
                    result.append((entry.title or '', entry.href or ''))
            return result

        chapters = []
        seen = set()

        # 优先用 TOC 元数据获取真实章节名
        if book.toc:
            for title, href in flatten_toc(book.toc):
                bare = href.split('#')[0]
                if bare in seen:
                    continue
                seen.add(bare)
                item = href_map.get(bare) or href_map.get(bare.split('/')[-1])
                if item:
                    text = item_text(item)
                    if len(text) > 50:
                        chapters.append({"title": title.strip() or bare, "text": text})

        # 兜底：按 spine 顺序遍历，用标题标签提取章节名
        if not chapters:
            for item in book.get_items():
                if item.get_type() == 9:
                    text = item_text(item)
                    if len(text) > 50:
                        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                        title = _extract_chapter_title(soup)
                        if not title:
                            first_line = text.split('\n')[0].strip()
                            title = first_line[:20] + ('...' if len(first_line) > 20 else '')
                        chapters.append({"title": title, "text": text})

        return chapters if chapters else None
    except Exception:
        return None

def _make_chapter_dict(text, idx):
    """从文本块创建章节字典，尝试提取标题"""
    text = _clean_text(text)
    first_line = text.split('\n')[0].strip()
    # 检测是否像章节标题
    title_match = re.match(r'^(第.{1,5}[章节回篇].*|Chapter\s*\d+.*|CHAPTER\s*\d+.*)', first_line)
    if title_match and len(first_line) < 50:
        title = first_line
    else:
        title = first_line[:20] + ('...' if len(first_line) > 20 else '')
    return {"title": title, "text": text}

@st.cache_data
def extract_text_from_txt(file_bytes):
    try:
        detected = chardet.detect(file_bytes)
        encoding = detected.get('encoding', 'utf-8') or 'utf-8'
        text = file_bytes.decode(encoding, errors='replace')

        raw_chapters = text.split('\n\n\n')
        chapters = []
        current_chunk = ""
        chunk_idx = 0
        for part in raw_chapters:
            part = part.strip()
            if not part:
                continue
            current_chunk += part + "\n\n"
            if len(current_chunk) > 2000:
                chapters.append(_make_chapter_dict(current_chunk.strip(), chunk_idx))
                current_chunk = ""
                chunk_idx += 1
        if current_chunk.strip():
            chapters.append(_make_chapter_dict(current_chunk.strip(), chunk_idx))

        return chapters if chapters else None
    except Exception:
        return None

@st.cache_data
def extract_text_from_pdf(file_bytes):
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        chapters = []
        current_chunk = ""
        page_start = 1
        page_num = 0
        for page in reader.pages:
            page_num += 1
            page_text = page.extract_text()
            if page_text:
                current_chunk += page_text + "\n\n"
                if len(current_chunk) > 3000:
                    ch = _make_chapter_dict(current_chunk.strip(), len(chapters))
                    ch["title"] = f"第 {page_start}-{page_num} 页"
                    chapters.append(ch)
                    current_chunk = ""
                    page_start = page_num + 1
        if current_chunk.strip():
            ch = _make_chapter_dict(current_chunk.strip(), len(chapters))
            ch["title"] = f"第 {page_start}-{page_num} 页"
            chapters.append(ch)
        return chapters if chapters else None
    except Exception:
        return None

def _read_file_with_auto_encoding(filepath):
    """读取文件并自动检测编码"""
    with open(filepath, 'rb') as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected.get('encoding', 'utf-8') or 'utf-8'
    # 尝试检测到的编码，再依次尝试常见中文编码
    for enc in [encoding, 'utf-8', 'gb18030', 'gbk', 'gb2312', 'big5', 'shift_jis']:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode('utf-8', errors='replace')

_CHAPTER_RE = re.compile(
    r'^(第\s*[零一二三四五六七八九十百千\d]+\s*[章节回篇卷][^\n]{0,40}|'
    r'Chapter\s+\d+[^\n]{0,40}|CHAPTER\s+\d+[^\n]{0,40}|'
    r'Part\s+\d+[^\n]{0,40}|PART\s+\d+[^\n]{0,40})$',
    re.MULTILINE
)

def _split_text_by_pattern(text, chunk_size=3000):
    """先按中英文章节标题切，找不到再按大小切块"""
    matches = list(_CHAPTER_RE.finditer(text))
    chapters = []
    if len(matches) >= 2:
        for i, match in enumerate(matches):
            title = match.group().strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = _clean_text(text[start:end].strip())
            if len(body) > 30 or not chapters:
                chapters.append({"title": title[:40], "text": body or title})
        return chapters
    # 按大小切块
    current_chunk, idx = "", 0
    for para in text.split('\n\n'):
        para = para.strip()
        if not para:
            continue
        current_chunk += para + "\n\n"
        if len(current_chunk) > chunk_size:
            chapters.append(_make_chapter_dict(current_chunk.strip(), idx))
            current_chunk, idx = "", idx + 1
    if current_chunk.strip():
        chapters.append(_make_chapter_dict(current_chunk.strip(), idx))
    return chapters


def _soup_to_chapters_by_headings(soup, chunk_size=3000):
    """按 h1/h2/h3 标题标签将单个 HTML soup 切割成章节列表"""
    headings = soup.find_all(['h1', 'h2', 'h3'])
    chapters = []

    if headings:
        for i, heading in enumerate(headings):
            title = heading.get_text(strip=True)
            if not title or len(title) > 80:
                continue
            parts = []
            node = heading.next_sibling
            next_heading = headings[i + 1] if i + 1 < len(headings) else None
            while node:
                if next_heading and node is next_heading:
                    break
                if hasattr(node, 'get_text'):
                    t = node.get_text(separator='\n', strip=True)
                    if t:
                        parts.append(t)
                elif isinstance(node, str):
                    t = node.strip()
                    if t:
                        parts.append(t)
                node = node.next_sibling
            body = _clean_text('\n\n'.join(parts))
            if len(body) > 30 or not chapters:
                chapters.append({"title": title[:40], "text": body or title})

    # 如果标题检测只得到 1 个章节（很可能只抓到目录标题），
    # 用全文模式重新切割
    if len(chapters) <= 1:
        full_text = _clean_text(soup.get_text(separator='\n\n', strip=True))
        fallback = _split_text_by_pattern(full_text, chunk_size)
        if len(fallback) > len(chapters):
            chapters = fallback

    return chapters if chapters else None


def _parse_ncx_titles(ncx_path):
    """解析 NCX 文件，返回 {basename: title} 字典"""
    try:
        content = _read_file_with_auto_encoding(ncx_path)
        soup = BeautifulSoup(content, 'xml')
        result = {}
        for np in soup.find_all('navPoint'):
            label = np.find('navLabel')
            src_tag = np.find('content')
            if label and src_tag:
                title = label.get_text(strip=True)
                src = os.path.basename(src_tag.get('src', '').split('#')[0])
                if title and src:
                    result[src] = title
        return result
    except Exception:
        return {}


def _text_from_html_files(file_list, title_map=None):
    """从一组 HTML/XHTML 文件中提取文本，返回章节列表。
    title_map: {basename: title}，来自 NCX，优先于标题标签推断。"""
    chapters = []
    for fpath in sorted(file_list):
        file_content = _read_file_with_auto_encoding(fpath)
        soup = BeautifulSoup(file_content, 'html.parser')
        basename = os.path.basename(fpath)
        if title_map and basename in title_map:
            text = _clean_text(soup.get_text(separator='\n\n', strip=True))
            if len(text) > 50:
                chapters.append({"title": title_map[basename], "text": text})
        else:
            sub = _soup_to_chapters_by_headings(soup)
            if sub:
                chapters.extend(sub)
    return chapters if chapters else None

def _extract_mobi_content(file_bytes, suffix):
    """MOBI/AZW3 通用提取逻辑"""
    import mobi
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        tempdir, filepath = mobi.extract(tmp_path)

        # 策略1：在提取目录中找 .epub 文件，用 epub 解析器读取
        epub_files = glob.glob(os.path.join(tempdir, '**', '*.epub'), recursive=True)
        for ef in epub_files:
            try:
                with open(ef, 'rb') as f:
                    return extract_text_from_epub(f.read())
            except Exception:
                continue

        # 策略2：查找 OEBPS/Text 等目录中的 xhtml/html 文件（KF8 解包结构）
        xhtml_files = glob.glob(os.path.join(tempdir, '**', '*.xhtml'), recursive=True)
        xhtml_files += glob.glob(os.path.join(tempdir, '**', '*.html'), recursive=True)
        xhtml_files += glob.glob(os.path.join(tempdir, '**', '*.htm'), recursive=True)
        if xhtml_files:
            ncx_files = glob.glob(os.path.join(tempdir, '**', '*.ncx'), recursive=True)
            title_map = _parse_ncx_titles(ncx_files[0]) if ncx_files else {}
            result = _text_from_html_files(xhtml_files, title_map or None)
            if result:
                return result

        # 策略3：mobi.extract 返回的主文件可能是个 zip/epub，尝试解压
        if os.path.isfile(filepath):
            try:
                if zipfile.is_zipfile(filepath):
                    extract_dir = os.path.join(tempdir, '_unzipped')
                    with zipfile.ZipFile(filepath, 'r') as zf:
                        zf.extractall(extract_dir)
                    xhtml_files = glob.glob(os.path.join(extract_dir, '**', '*.xhtml'), recursive=True)
                    xhtml_files += glob.glob(os.path.join(extract_dir, '**', '*.html'), recursive=True)
                    if xhtml_files:
                        ncx_files = glob.glob(os.path.join(extract_dir, '**', '*.ncx'), recursive=True)
                        title_map = _parse_ncx_titles(ncx_files[0]) if ncx_files else {}
                        result = _text_from_html_files(xhtml_files, title_map or None)
                        if result:
                            return result
            except Exception:
                pass

        # 策略4：直接读取主文件作为 HTML（老式 MOBI），按标题标签切章节
        if os.path.isfile(filepath):
            file_content = _read_file_with_auto_encoding(filepath)
            soup = BeautifulSoup(file_content, 'html.parser')
            text_probe = soup.get_text()
            cjk_count = sum(1 for c in text_probe[:500] if '\u4e00' <= c <= '\u9fff')
            latin_count = sum(1 for c in text_probe[:500] if c.isalpha())
            if cjk_count > 20 or latin_count > 100:
                return _soup_to_chapters_by_headings(soup)

        return None
    finally:
        os.unlink(tmp_path)

@st.cache_data
def extract_text_from_mobi(file_bytes):
    try:
        return _extract_mobi_content(file_bytes, '.mobi')
    except Exception:
        return None

@st.cache_data
def extract_text_from_azw3(file_bytes):
    try:
        return _extract_mobi_content(file_bytes, '.azw3')
    except Exception:
        return None

def extract_chapters(file_bytes, file_name):
    """根据文件扩展名调用对应的解析函数"""
    ext = file_name.rsplit('.', 1)[-1].lower()
    if ext == 'epub':
        return extract_text_from_epub(file_bytes)
    elif ext == 'txt':
        return extract_text_from_txt(file_bytes)
    elif ext == 'pdf':
        return extract_text_from_pdf(file_bytes)
    elif ext == 'mobi':
        return extract_text_from_mobi(file_bytes)
    elif ext == 'azw3':
        return extract_text_from_azw3(file_bytes)
    else:
        return None

def split_into_pages(text, chars_per_page=600):
    """将文本按段落智能分页，避免截断句子"""
    paragraphs = text.split('\n')
    pages = []
    current_page = ""
    for para in paragraphs:
        if len(current_page) + len(para) > chars_per_page and current_page:
            pages.append(current_page.strip())
            current_page = para + "\n"
        else:
            current_page += para + "\n"
    if current_page.strip():
        pages.append(current_page.strip())
    return pages if pages else [text]


def _to_html(page_text):
    """将纯文本段落转为 HTML <p> 标签，转义特殊字符"""
    result = ""
    for para in page_text.split('\n'):
        para = para.strip()
        if para:
            result += f"<p>{html.escape(para)}</p>"
    return result


_PROGRESS_FILE = os.path.join(os.path.expanduser("~"), ".reading_buddy_progress.json")
_BOOKMARKS_FILE = os.path.join(os.path.expanduser("~"), ".reading_buddy_bookmarks.json")


def _load_progress():
    try:
        with open(_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_progress(book_key, chapter_idx, page):
    data = _load_progress()
    data[book_key] = {
        "chapter_idx": int(chapter_idx),
        "page": int(page),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        with open(_PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_bookmarks():
    try:
        with open(_BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_bookmarks(data):
    try:
        with open(_BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _add_bookmark(book_key, chapter_idx, page):
    from datetime import timezone, timedelta
    data = _load_bookmarks()
    lst = data.setdefault(book_key, [])
    # 去重：相同章节 + 页不重复添加
    for b in lst:
        if int(b.get("chapter_idx", -1)) == int(chapter_idx) and int(b.get("page", -1)) == int(page):
            return False
    lst.append({
        "chapter_idx": int(chapter_idx),
        "page": int(page),
        "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M"),
    })
    _save_bookmarks(data)
    return True


def _remove_bookmark(book_key, index):
    data = _load_bookmarks()
    lst = data.get(book_key, [])
    if 0 <= index < len(lst):
        lst.pop(index)
        _save_bookmarks(data)

# 5. 主逻辑控制
# 将上传文件缓存到 session_state，防止翻页时丢失
if uploaded_file:
    st.session_state.file_bytes = uploaded_file.getvalue()
    st.session_state.file_name = uploaded_file.name

has_file = "file_bytes" in st.session_state and st.session_state.file_bytes
if has_file:
    chapters = extract_chapters(st.session_state.file_bytes, st.session_state.file_name)

    if chapters:
        # 侧边栏：章节选择（显示真实标题）
        chapter_titles = [ch["title"] for ch in chapters]
        book_key = st.session_state.file_name
        sel_key = "chapter_select"

        # 首次载入此书时，恢复上次的章节 + 页码
        if st.session_state.get("loaded_book") != book_key:
            saved = _load_progress().get(book_key, {})
            saved_ch = 0
            if saved:
                saved_ch = min(max(int(saved.get("chapter_idx", 0)), 0), len(chapters) - 1)
                st.session_state[f"page_{saved_ch}"] = int(saved.get("page", 0))
            st.session_state[sel_key] = saved_ch
            st.session_state.last_chapter = saved_ch
            st.session_state.loaded_book = book_key

        # 书签跳转：在 selectbox 渲染之前应用 pending 状态
        if "_pending_jump" in st.session_state:
            _jmp = st.session_state.pop("_pending_jump")
            _jch = int(_jmp.get("chapter", 0))
            _jch = min(max(_jch, 0), len(chapters) - 1)
            st.session_state[sel_key] = _jch
            st.session_state[f"page_{_jch}"] = int(_jmp.get("page", 0))
            st.session_state.last_chapter = _jch

        chapter_idx = st.sidebar.selectbox(
            "选择章节",
            range(len(chapters)),
            format_func=lambda x: chapter_titles[x],
            key=sel_key,
        )
        current_text = chapters[chapter_idx]["text"]

        # 将当前章节分页
        pages = split_into_pages(current_text)
        total_pages = len(pages)

        # 初始化页码状态
        page_key = f"page_{chapter_idx}"
        if page_key not in st.session_state:
            st.session_state[page_key] = 0

        current_page = st.session_state[page_key]

        # 切换章节时重置页码
        if "last_chapter" not in st.session_state:
            st.session_state.last_chapter = chapter_idx
        if st.session_state.last_chapter != chapter_idx:
            st.session_state[page_key] = 0
            current_page = 0
            st.session_state.last_chapter = chapter_idx

        # --- 侧边栏：书签 ---
        st.sidebar.divider()
        st.sidebar.markdown(
            f'<strong class="sbh">{PX_ICON["pin"]}书签</strong>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("加入当前位置", key="bm_add", use_container_width=True):
            added = _add_bookmark(book_key, chapter_idx, current_page)
            st.toast("[+] 已添加书签" if added else "此位置已有书签")
            st.rerun()

        _bms = _load_bookmarks().get(book_key, [])
        if not _bms:
            st.sidebar.caption("还没有书签")
        else:
            for _i, _b in enumerate(_bms):
                _ch = int(_b.get("chapter_idx", 0))
                _pg = int(_b.get("page", 0))
                _ts = _b.get("ts", "")
                _ch_title = chapter_titles[_ch] if 0 <= _ch < len(chapter_titles) else f"章节 {_ch+1}"
                _short = _ch_title if len(_ch_title) <= 10 else _ch_title[:10] + "…"
                _label = f"{_short} · 第{_pg+1}页"
                if _ts:
                    _label += f"　{_ts}"
                _bc1, _bc2 = st.sidebar.columns([6, 1])
                with _bc1:
                    if st.button(_label, key=f"bm_go_{_i}", use_container_width=True):
                        st.session_state._pending_jump = {"chapter": _ch, "page": _pg}
                        st.rerun()
                with _bc2:
                    if st.button("✕", key=f"bm_del_{_i}", help="删除此书签"):
                        _remove_bookmark(book_key, _i)
                        st.rerun()

        # --- 阅读界面 ---

        # D1：顶部杂志刊头带（VOL / 章节名 / CH.XX · 时钟）
        # 时钟并入 rd-topbar 右段，替掉原装饰 "PIXEL EDITION"；
        # 原 top_col1/top_col2（章节名重复 + 时间）整行删除
        from datetime import timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%H:%M")
        _ch_title_safe = html.escape(chapter_titles[chapter_idx])
        _topbar_html = (
            '<div class="rd-topbar">'
            '<span>VOL.01 <span class="dot">■</span> EST.2026</span>'
            f'<span class="rd-mid">{_ch_title_safe}</span>'
            f'<span>CH.{chapter_idx + 1:02d}/{len(chapters):02d} '
            '<span class="dot">■</span> '
            f'<span class="rd-clock">{PX_ICON["clock"]}{now}</span>'
            '</span>'
            '</div>'
        )
        st.markdown(_topbar_html, unsafe_allow_html=True)

        # 进度条
        progress = (current_page + 1) / total_pages if total_pages > 0 else 1
        st.markdown(f"""
        <div class="progress-container">
            <div class="progress-fill" style="width: {progress * 100:.1f}%"></div>
        </div>
        """, unsafe_allow_html=True)

        # 像素风主题：奶油纸底 + 深棕墨色（由 CSS 覆写，inline 仅占位保留结构）
        fs = st.session_state.get("font_size", 18)
        theme_css = "background: #fffaec; color: #3b2e1e;"
        # 字体族（基于 session_state，默认系统字体）
        # 用单引号包裹字体名，以便安全嵌入 style="..." 属性
        _font_stacks = {
            "默认": "system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', sans-serif",
            "宋体": "'Source Han Serif SC', 'Noto Serif SC', 'Songti SC', 'SimSun', 'PingFang SC', serif",
            "楷体": "'Kaiti SC', 'STKaiti', 'KaiTi', 'BiauKai', serif",
            "圆体": "'Yuanti SC', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', sans-serif",
        }
        ff_css = _font_stacks.get(st.session_state.get("font_family_name", "默认"), _font_stacks["默认"])

        # 双页展示：当前页 = 左页，下一页 = 右页
        left_idx  = current_page
        right_idx = current_page + 1 if current_page + 1 < total_pages else None

        left_num = left_idx + 1
        right_num = right_idx + 1 if right_idx is not None else ""

        left_html  = _to_html(pages[left_idx])
        right_html = (_to_html(pages[right_idx]) if right_idx is not None
                      else '<p style="opacity:0.3; text-align:center; text-indent:0;">— 本章完 —</p>')

        # 页码指示 & 总进度
        chapter_page_counts = [len(split_into_pages(ch["text"])) for ch in chapters]
        total_all_pages = sum(chapter_page_counts)
        read_pages = sum(chapter_page_counts[:chapter_idx]) + current_page + 1
        overall = read_pages / total_all_pages * 100 if total_all_pages > 0 else 0

        prev_disabled = current_page <= 0
        next_disabled = current_page >= total_pages - 1
        prev_cls = "nav-btn nav-prev" + (" nav-disabled" if prev_disabled else "")
        next_cls = "nav-btn nav-next" + (" nav-disabled" if next_disabled else "")

        # 本章剩余阅读时间估算（未读页字数 / 300 字每分钟）
        _remaining_chars = sum(len(p) for p in pages[current_page + 2:])
        if _remaining_chars <= 0:
            _time_left = "本章即将读完"
        else:
            _mins = max(1, round(_remaining_chars / 300))
            _time_left = f"本章约剩 {_mins} 分钟"

        # page-indicator 拆两行：主行像素刊头字体，副行柔化
        _pg_range_label = (
            f"PAGE {left_num}"
            + (f"-{right_num}" if right_num else "")
            + f" / {total_pages}"
        )
        _pg_main = f'<div class="pg-main">{_pg_range_label}</div>'
        _pg_sub = (
            f'<div class="pg-sub">全书 {overall:.1f}% · {_time_left}</div>'
        )
        page_range = _pg_main + _pg_sub

        # book-spread + page-indicator + nav-row 在同一个容器内，保证三者宽度严格一致
        reading_html = f'''
        <div class="reading-area">
            <div class="book-spread" style="{theme_css} font-size: {fs}px; font-family: {ff_css};">
                <div class="book-page book-page-left">
                    {left_html}
                    <div class="page-num">{left_num}</div>
                </div>
                <div class="book-page book-page-right">
                    {right_html}
                    <div class="page-num">{right_num}</div>
                </div>
            </div>
            <div class="page-indicator">{page_range}</div>
            <div class="nav-row">
                <button type="button" class="{prev_cls}">上一页</button>
                <button type="button" class="{next_cls}">下一页</button>
            </div>
        </div>
        '''
        st.markdown(reading_html, unsafe_allow_html=True)

        # 持久化阅读进度
        _save_progress(book_key, chapter_idx, current_page)

        # 隐藏的 Streamlit 按钮：真正处理翻页逻辑（HTML 按钮通过 JS 点击它们）
        hcol1, hcol2 = st.columns(2)
        with hcol1:
            if st.button("prev", key="prev_page"):
                if current_page > 0:
                    st.session_state[page_key] = max(0, current_page - 2)
                    st.rerun()
        with hcol2:
            if st.button("next", key="next_page"):
                if current_page < total_pages - 1:
                    st.session_state[page_key] = min(total_pages - 1, current_page + 2)
                    st.rerun()

        # 键盘 ← / → 翻页（点击 HTML 导航链接来触发翻页）
        components.html(
            """
            <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
            <style>
              @font-face {
                font-family: 'Zpix';
                src: url('https://cdn.jsdelivr.net/gh/SolidZORO/zpix-pixel-font/dist/zpix.ttf') format('truetype');
                font-display: swap;
              }
              body { margin: 0; background: #f3e9cf; }
              .rb-kbd-wrap {
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 4px 0;
              }
              .rb-kbd-hint {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 12px;
                border-radius: 0;
                background: #fffaec;
                border: 2px solid #3b2e1e;
                color: #3b2e1e;
                font-size: 11px;
                font-family: 'Press Start 2P', 'Zpix', monospace;
                letter-spacing: 1px;
                user-select: none;
                box-shadow: 3px 3px 0 #d4b54c;
              }
              .rb-kbd-hint kbd {
                display: inline-block;
                min-width: 18px;
                padding: 1px 6px;
                border: 1.5px solid #3b2e1e;
                border-radius: 0;
                background: #e8dcbc;
                color: #3b2e1e;
                font-size: 11px;
                font-family: 'Press Start 2P', monospace;
                line-height: 1.4;
                text-align: center;
                box-shadow: 1px 1px 0 #3b2e1e;
              }
              .rb-kbd-hint.rb-err {
                background: #fffaec;
                border-color: #c25a44;
                color: #c25a44;
              }
            </style>
            <div class="rb-kbd-wrap">
              <div id="rb-kbd-status" class="rb-kbd-hint">加载中…</div>
            </div>
            <script>
            (function() {
                const s = document.getElementById('rb-kbd-status');
                function setReady() {
                    if (s) {
                        s.classList.remove('rb-err');
                        s.innerHTML = '<kbd>←</kbd> 键盘翻页已启动 <kbd>→</kbd>';
                    }
                }
                function setErr(msg) {
                    if (s) { s.classList.add('rb-err'); s.innerText = '⚠ 键盘翻页不可用: ' + msg; }
                }
                function setMsg(txt, c) {
                    if (c === '#4caf50') { setReady(); return; }
                    if (c === '#f44336') { setErr(txt); return; }
                    if (s) s.innerText = txt;
                }
                try {
                    const p = window.parent;
                    // 移除之前 iframe 留下的 handler（iframe 被重新挂载时旧闭包会失效）
                    if (p._rb_kbd_handler) {
                        try { p.document.removeEventListener('keydown', p._rb_kbd_handler, true); } catch (_) {}
                        try { p.removeEventListener('keydown', p._rb_kbd_handler, true); } catch (_) {}
                    }
                    if (p._rb_click_handler) {
                        try { p.document.removeEventListener('click', p._rb_click_handler, true); } catch (_) {}
                    }
                    function isTextEditing(el) {
                        if (!el) return false;
                        if (el.isContentEditable) return true;
                        const tag = el.tagName;
                        if (tag === 'TEXTAREA') return true;
                        if (tag === 'INPUT') {
                            if (el.readOnly || el.disabled) return false;
                            // 忽略 selectbox/combobox 内的搜索输入框
                            if (el.closest && (el.closest('[role="combobox"]') || el.closest('[data-baseweb="select"]'))) return false;
                            const blocked = ['button','submit','reset','checkbox','radio','file','range','color'];
                            if (blocked.indexOf(el.type) !== -1) return false;
                            return true;
                        }
                        return false;
                    }
                    function clickHiddenBtn(action) {
                        const sel = action === 'prev'
                            ? '.st-key-prev_page button'
                            : '.st-key-next_page button';
                        const btn = p.document.querySelector(sel);
                        if (btn && !btn.disabled) btn.click();
                    }
                    function handler(e) {
                        if (e.ctrlKey || e.metaKey || e.altKey) return;
                        if (isTextEditing(e.target)) return;
                        let action = null;
                        if (e.key === 'ArrowLeft') action = 'prev';
                        else if (e.key === 'ArrowRight') action = 'next';
                        if (!action) return;
                        const visEl = p.document.querySelector(action === 'prev' ? '.nav-prev' : '.nav-next');
                        if (!visEl || visEl.classList.contains('nav-disabled')) return;
                        e.preventDefault();
                        try { if (e.target && e.target.blur) e.target.blur(); } catch (_) {}
                        clickHiddenBtn(action);
                    }
                    // 绑定并把 handler 引用存到 parent，下次 iframe 挂载时可以清掉
                    p._rb_kbd_handler = handler;
                    p.document.addEventListener('keydown', handler, true);
                    p.addEventListener('keydown', handler, true);
                    // 点击委托：HTML 导航按钮 → 隐藏 st.button
                    const clickHandler = function(e) {
                        const btn = e.target.closest && e.target.closest('.nav-btn');
                        if (!btn) return;
                        e.preventDefault();
                        if (btn.classList.contains('nav-disabled')) return;
                        const action = btn.classList.contains('nav-prev') ? 'prev' : 'next';
                        clickHiddenBtn(action);
                    };
                    p._rb_click_handler = clickHandler;
                    p.document.addEventListener('click', clickHandler, true);
                    setMsg('⌨ 键盘翻页已启用（← / →）', '#4caf50');
                } catch (err) {
                    setMsg('⌨ 键盘翻页不可用: ' + (err && err.message || err), '#f44336');
                }
            })();
            </script>
            """,
            height=36,
        )

        # 侧边栏：阅读设置
        st.sidebar.divider()
        st.sidebar.markdown("**阅读设置**")

        # 字体大小
        if "font_size" not in st.session_state:
            st.session_state.font_size = 18
        font_size = st.sidebar.slider("字体大小", 14, 28, st.session_state.font_size, step=2)
        if font_size != st.session_state.font_size:
            st.session_state.font_size = font_size
            st.rerun()

        # 字体 (基于系统自带中文字体，跨平台自动回退)
        _font_options = {
            "默认": 'system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif',
            "宋体": '"Source Han Serif SC", "Noto Serif SC", "Songti SC", "SimSun", "PingFang SC", serif',
            "楷体": '"Kaiti SC", "STKaiti", "KaiTi", "BiauKai", serif',
            "圆体": '"Yuanti SC", "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif',
        }
        if "font_family_name" not in st.session_state:
            st.session_state.font_family_name = "默认"
        _font_keys = list(_font_options.keys())
        _ff = st.sidebar.selectbox(
            "字体",
            _font_keys,
            index=_font_keys.index(st.session_state.font_family_name),
        )
        if _ff != st.session_state.font_family_name:
            st.session_state.font_family_name = _ff
            st.rerun()

        # 页码跳转
        jump_page = st.sidebar.number_input(
            "跳转到页码",
            min_value=1,
            max_value=total_pages,
            value=current_page + 1,
            step=1
        )
        if jump_page - 1 != current_page:
            st.session_state[page_key] = jump_page - 1
            st.rerun()

        # --- 分隔：AI 聊天区域 ---
        st.divider()
        st.markdown(
            f'<h3 class="ai-chat-heading">{PX_ICON["chat"]}与 AI 探讨本章内容</h3>',
            unsafe_allow_html=True,
        )

        # 初始化聊天记录
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # 在屏幕上显示之前的历史聊天记录
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.write(m["content"])

        # 等待用户输入感悟
        if prompt := st.chat_input("请尽情与我交谈ฅ՞•ﻌ•՞ฅ"):

            # 1. 存入并立刻在屏幕上显示用户发的消息
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            # 2. 召唤豆包大脑开始思考并回复
            with st.chat_message("assistant"):
                try:
                    client = OpenAI(
                        api_key=st.secrets["ARK_API_KEY"],
                        base_url="https://ark.cn-beijing.volces.com/api/v3",
                    )

                    # 用当前页内容作为语境
                    context_msg = f"你是一个博学的共读伙伴，擅长从哲学、生物学或行为因果的角度深度分析文本。正在阅读的内容：\n{pages[left_idx][:1200]}\n\n读者感悟：{prompt}"

                    completion = client.chat.completions.create(
                        model=st.secrets["ARK_MODEL_ID"],
                        messages=[
                            {"role": "system", "content": "你是一个高水平的阅读助手，擅长理解复杂的人性、行为逻辑以及具有宏大设定的文学作品。"},
                            {"role": "user", "content": context_msg}
                        ],
                    )

                    response_text = completion.choices[0].message.content
                    st.write(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

                except Exception as e:
                    st.error("嘟哒暂时联系不上大脑，休息一下再试吧。")
                    with st.expander("详情"):
                        st.code(str(e))

    else:
        st.warning("书本解析失败，请确认文件是否损坏，或换一本书试试。")
else:
    # 日式编辑 zine 风欢迎页（全屏覆盖 + 内嵌上传器）
    # 拆成两段：上段（刊头 + Hero）→ 上传器 → 下段（流程 + 特性 + 底栏），
    # 这样上传器在首屏可见，无需下滑。
    st.markdown("""
    <div class="zine-welcome zw-top">
        <div class="zw-corner tl">[+]</div>
        <div class="zw-corner tr">[+]</div>
        <div class="zw-topbar">
            <span>VOL.01 <span class="dot">■</span> EST.2026</span>
            <b>SWEET SWEET HOMELAND</b>
            <span>№001 <span class="dot">■</span> PIXEL EDITION</span>
        </div>
        <div class="zw-hero">
            <div class="zw-hero-text">
                <div class="zw-eyebrow">Sweet Sweet Homeland</div>
                <div class="zw-kicker">A READING CLUB</div>
                <h1 class="zw-title">嘟 哒</h1>
                <div class="zw-title-bar"></div>
                <div class="zw-subtitle-zh">你 的 共 读 伴 侣</div>
                <div class="zw-desc">
                    <span class="line line-1">在这里，每一本书都值得被深度对话。</span>
                    <span class="line line-2">上传你的电子书，和 AI 一起开启阅读旅程。<span class="caret on"></span></span>
                </div>
                <div class="zw-formats">
                    <span class="zw-tag">EPUB</span>
                    <span class="zw-tag">TXT</span>
                    <span class="zw-tag">PDF</span>
                    <span class="zw-tag">MOBI</span>
                    <span class="zw-tag">AZW3</span>
                </div>
            </div>
            <div class="zw-art">
                <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                    <!-- 书 1 底部 陶土红 -->
                    <rect x="6" y="50" width="52" height="8" fill="#c25a44"/>
                    <rect x="6" y="50" width="52" height="1" fill="#7d2e21"/>
                    <rect x="6" y="57" width="52" height="1" fill="#7d2e21"/>
                    <rect x="10" y="53" width="16" height="1" fill="#f3e9cf"/>
                    <rect x="10" y="55" width="12" height="1" fill="#f3e9cf"/>
                    <!-- 书 2 中间 苔绿 -->
                    <rect x="10" y="42" width="44" height="8" fill="#4a6d4e"/>
                    <rect x="10" y="42" width="44" height="1" fill="#2d4130"/>
                    <rect x="10" y="49" width="44" height="1" fill="#2d4130"/>
                    <rect x="14" y="45" width="14" height="1" fill="#f3e9cf"/>
                    <!-- 书 3 顶部 芥黄 -->
                    <rect x="14" y="34" width="36" height="8" fill="#d4b54c"/>
                    <rect x="14" y="34" width="36" height="1" fill="#8a7420"/>
                    <rect x="14" y="41" width="36" height="1" fill="#8a7420"/>
                    <rect x="18" y="37" width="10" height="1" fill="#3b2e1e"/>
                    <!-- 白猫 curled 在书顶 -->
                    <!-- 耳朵（描边 + 白填充 + 粉内耳） -->
                    <rect x="15" y="19" width="6" height="1" fill="#3b2e1e"/>
                    <rect x="21" y="19" width="6" height="1" fill="#3b2e1e"/>
                    <rect x="15" y="20" width="1" height="4" fill="#3b2e1e"/>
                    <rect x="20" y="20" width="1" height="4" fill="#3b2e1e"/>
                    <rect x="21" y="20" width="1" height="4" fill="#3b2e1e"/>
                    <rect x="26" y="20" width="1" height="4" fill="#3b2e1e"/>
                    <rect x="16" y="20" width="4" height="4" fill="#fffef8"/>
                    <rect x="22" y="20" width="4" height="4" fill="#fffef8"/>
                    <rect x="17" y="22" width="2" height="2" fill="#e07b5a"/>
                    <rect x="23" y="22" width="2" height="2" fill="#e07b5a"/>
                    <!-- 头身描边 -->
                    <rect x="13" y="24" width="30" height="1" fill="#3b2e1e"/>
                    <rect x="11" y="26" width="34" height="1" fill="#3b2e1e"/>
                    <rect x="11" y="31" width="34" height="1" fill="#3b2e1e"/>
                    <rect x="13" y="33" width="30" height="1" fill="#3b2e1e"/>
                    <rect x="11" y="27" width="1" height="4" fill="#3b2e1e"/>
                    <rect x="44" y="27" width="1" height="4" fill="#3b2e1e"/>
                    <rect x="13" y="25" width="1" height="8" fill="#3b2e1e"/>
                    <rect x="42" y="25" width="1" height="8" fill="#3b2e1e"/>
                    <!-- 身体（白填充） -->
                    <rect x="14" y="24" width="28" height="10" fill="#fffef8"/>
                    <rect x="12" y="26" width="32" height="6" fill="#fffef8"/>
                    <!-- 底部浅灰阴影增加立体感 -->
                    <rect x="14" y="32" width="28" height="1" fill="#e5dcc0"/>
                    <!-- 闭眼（黑色短横线） -->
                    <rect x="17" y="28" width="3" height="1" fill="#3b2e1e"/>
                    <rect x="22" y="28" width="3" height="1" fill="#3b2e1e"/>
                    <!-- 鼻 -->
                    <rect x="20" y="30" width="2" height="1" fill="#c25a44"/>
                    <!-- 嘴 -->
                    <rect x="19" y="31" width="1" height="1" fill="#3b2e1e"/>
                    <rect x="22" y="31" width="1" height="1" fill="#3b2e1e"/>
                    <!-- 腮红 -->
                    <rect x="15" y="29" width="1" height="1" fill="#e07b5a" opacity="0.5"/>
                    <rect x="26" y="29" width="1" height="1" fill="#e07b5a" opacity="0.5"/>
                    <!-- 尾巴（描边 + 白填充） -->
                    <rect x="40" y="21" width="2" height="1" fill="#3b2e1e"/>
                    <rect x="39" y="22" width="1" height="6" fill="#3b2e1e"/>
                    <rect x="42" y="22" width="1" height="6" fill="#3b2e1e"/>
                    <rect x="40" y="22" width="2" height="6" fill="#fffef8"/>
                    <rect x="42" y="19" width="3" height="1" fill="#3b2e1e"/>
                    <rect x="42" y="20" width="1" height="2" fill="#3b2e1e"/>
                    <rect x="44" y="20" width="1" height="2" fill="#3b2e1e"/>
                    <rect x="43" y="20" width="1" height="2" fill="#fffef8"/>
                    <!-- Z 泡泡 -->
                    <rect x="30" y="12" width="3" height="1" fill="#7a96b4"/>
                    <rect x="32" y="13" width="1" height="1" fill="#7a96b4"/>
                    <rect x="30" y="14" width="3" height="1" fill="#7a96b4"/>
                    <rect x="36" y="6" width="5" height="1" fill="#7a96b4"/>
                    <rect x="39" y="7" width="1" height="1" fill="#7a96b4"/>
                    <rect x="38" y="8" width="1" height="1" fill="#7a96b4"/>
                    <rect x="37" y="9" width="1" height="1" fill="#7a96b4"/>
                    <rect x="36" y="10" width="5" height="1" fill="#7a96b4"/>
                </svg>
                <div class="zw-art-caption">READING CLUB · 001</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # 上传区：标签 + 上传器（中央居中），夹在上下两段欢迎页之间
    _ul_col1, _ul_col2, _ul_col3 = st.columns([1, 2, 1])
    with _ul_col2:
        st.markdown(
            '<div class="zw-upload-label">&gt; PRESS UPLOAD TO BEGIN<span class="caret">_</span></div>',
            unsafe_allow_html=True,
        )
        _welcome_upload = st.file_uploader(
            "上传电子书",
            type=SUPPORTED_FORMATS,
            help="支持 EPUB、TXT、PDF、MOBI、AZW3",
            key="upload_welcome",
            label_visibility="collapsed",
        )
    if _welcome_upload:
        st.session_state.file_bytes = _welcome_upload.getvalue()
        st.session_state.file_name = _welcome_upload.name
        st.rerun()
    st.markdown("""
    <div class="zine-welcome zw-bottom">
        <div class="zw-corner bl">[+]</div>
        <div class="zw-corner br">[+]</div>
        <!-- HOW IT WORKS 3 步 -->
        <div class="zw-howto">
            <div class="zw-howto-title">
                <span>▶ HOW IT WORKS / 开始指南</span>
                <span class="zw-meter">■ ■ ■ □ □</span>
            </div>
            <div class="zw-steps">
                <div class="zw-step">
                    <div class="zw-step-num">01</div>
                    <div class="zw-step-icon">""" + PX_ICON["upload"] + """</div>
                    <div class="zw-step-label">上传电子书</div>
                    <div class="zw-step-sub">UPLOAD</div>
                </div>
                <div class="zw-step-arrow">&gt;</div>
                <div class="zw-step">
                    <div class="zw-step-num">02</div>
                    <div class="zw-step-icon">""" + PX_ICON["read"] + """</div>
                    <div class="zw-step-label">选章节阅读</div>
                    <div class="zw-step-sub">READ</div>
                </div>
                <div class="zw-step-arrow">&gt;</div>
                <div class="zw-step">
                    <div class="zw-step-num">03</div>
                    <div class="zw-step-icon">""" + PX_ICON["chat"] + """</div>
                    <div class="zw-step-label">AI 深度对话</div>
                    <div class="zw-step-sub">CHAT</div>
                </div>
            </div>
        </div>
        <!-- 特性徽章 -->
        <div class="zw-features">
            <span class="zw-feature"><span class="ic">""" + PX_ICON["keyboard"] + """</span> 键盘翻页</span>
            <span class="zw-feature"><span class="ic">""" + PX_ICON["pin"] + """</span> 书签收藏</span>
            <span class="zw-feature"><span class="ic">""" + PX_ICON["palette"] + """</span> 主题字体自定义</span>
            <span class="zw-feature"><span class="ic">""" + PX_ICON["clock"] + """</span> 剩余时间估算</span>
            <span class="zw-feature"><span class="ic">""" + PX_ICON["save"] + """</span> 进度自动保存</span>
            <span class="zw-feature"><span class="ic">""" + PX_ICON["robot"] + """</span> AI 共读</span>
        </div>
        <!-- 底部装饰条 -->
        <div class="zw-footer-strip">
            <span>PRESS UPLOAD TO BEGIN</span>
            <span class="hearts">♥ ♥ ♥</span>
            <span>SSH · №001 · 2026</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
