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
# 调色板：var(--mc-ink) ink / var(--mc-terra) terra / var(--mc-mustard) mustard / var(--mc-moss) moss / var(--mc-cream) cream
PX_ICON = {
    "upload": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="7" y="2" width="2" height="9" fill="#2E1D12"/><rect x="5" y="4" width="2" height="1" fill="#2E1D12"/><rect x="9" y="4" width="2" height="1" fill="#2E1D12"/><rect x="3" y="6" width="2" height="1" fill="#2E1D12"/><rect x="11" y="6" width="2" height="1" fill="#2E1D12"/><rect x="2" y="13" width="12" height="1" fill="#2E1D12"/><rect x="2" y="13" width="1" height="2" fill="#2E1D12"/><rect x="13" y="13" width="1" height="2" fill="#2E1D12"/></svg>',
    "read": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="1" y="3" width="6" height="1" fill="#2E1D12"/><rect x="9" y="3" width="6" height="1" fill="#2E1D12"/><rect x="1" y="3" width="1" height="10" fill="#2E1D12"/><rect x="6" y="3" width="1" height="10" fill="#2E1D12"/><rect x="9" y="3" width="1" height="10" fill="#2E1D12"/><rect x="14" y="3" width="1" height="10" fill="#2E1D12"/><rect x="1" y="12" width="14" height="1" fill="#2E1D12"/><rect x="2" y="5" width="3" height="1" fill="#B96A4A"/><rect x="2" y="7" width="3" height="1" fill="#B96A4A"/><rect x="2" y="9" width="3" height="1" fill="#B96A4A"/><rect x="10" y="5" width="3" height="1" fill="#B96A4A"/><rect x="10" y="7" width="3" height="1" fill="#B96A4A"/><rect x="10" y="9" width="3" height="1" fill="#B96A4A"/></svg>',
    "chat": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="2" y="3" width="12" height="1" fill="#2E1D12"/><rect x="2" y="10" width="8" height="1" fill="#2E1D12"/><rect x="1" y="4" width="1" height="6" fill="#2E1D12"/><rect x="14" y="4" width="1" height="6" fill="#2E1D12"/><rect x="4" y="11" width="2" height="1" fill="#2E1D12"/><rect x="5" y="12" width="1" height="1" fill="#2E1D12"/><rect x="4" y="6" width="2" height="2" fill="#B96A4A"/><rect x="7" y="6" width="2" height="2" fill="#B96A4A"/><rect x="10" y="6" width="2" height="2" fill="#B96A4A"/></svg>',
    "keyboard": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="1" y="4" width="14" height="1" fill="#2E1D12"/><rect x="1" y="11" width="14" height="1" fill="#2E1D12"/><rect x="1" y="4" width="1" height="8" fill="#2E1D12"/><rect x="14" y="4" width="1" height="8" fill="#2E1D12"/><rect x="3" y="6" width="2" height="1" fill="#2E1D12"/><rect x="6" y="6" width="2" height="1" fill="#2E1D12"/><rect x="9" y="6" width="2" height="1" fill="#2E1D12"/><rect x="12" y="6" width="1" height="1" fill="#2E1D12"/><rect x="3" y="8" width="2" height="1" fill="#2E1D12"/><rect x="6" y="8" width="2" height="1" fill="#2E1D12"/><rect x="9" y="8" width="2" height="1" fill="#2E1D12"/><rect x="12" y="8" width="1" height="1" fill="#2E1D12"/><rect x="4" y="10" width="8" height="1" fill="#2E1D12"/></svg>',
    "pin": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="6" y="2" width="4" height="1" fill="#2E1D12"/><rect x="5" y="3" width="1" height="4" fill="#2E1D12"/><rect x="10" y="3" width="1" height="4" fill="#2E1D12"/><rect x="6" y="3" width="4" height="4" fill="#B96A4A"/><rect x="7" y="4" width="1" height="1" fill="#e07b5a"/><rect x="3" y="7" width="10" height="2" fill="#2E1D12"/><rect x="7" y="9" width="2" height="5" fill="#2E1D12"/></svg>',
    "palette": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="4" y="2" width="8" height="1" fill="#2E1D12"/><rect x="3" y="3" width="1" height="1" fill="#2E1D12"/><rect x="12" y="3" width="1" height="1" fill="#2E1D12"/><rect x="2" y="4" width="1" height="6" fill="#2E1D12"/><rect x="13" y="4" width="1" height="6" fill="#2E1D12"/><rect x="3" y="10" width="1" height="2" fill="#2E1D12"/><rect x="4" y="12" width="3" height="1" fill="#2E1D12"/><rect x="7" y="11" width="1" height="1" fill="#2E1D12"/><rect x="8" y="10" width="5" height="1" fill="#2E1D12"/><rect x="4" y="4" width="2" height="2" fill="#B96A4A"/><rect x="9" y="4" width="2" height="2" fill="#D7A441"/><rect x="4" y="7" width="2" height="2" fill="#6E8B5B"/><rect x="9" y="7" width="2" height="2" fill="#7a96b4"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="5" y="2" width="6" height="1" fill="#2E1D12"/><rect x="5" y="13" width="6" height="1" fill="#2E1D12"/><rect x="3" y="3" width="2" height="1" fill="#2E1D12"/><rect x="11" y="3" width="2" height="1" fill="#2E1D12"/><rect x="3" y="12" width="2" height="1" fill="#2E1D12"/><rect x="11" y="12" width="2" height="1" fill="#2E1D12"/><rect x="2" y="4" width="1" height="8" fill="#2E1D12"/><rect x="13" y="4" width="1" height="8" fill="#2E1D12"/><rect x="7" y="5" width="2" height="4" fill="#2E1D12"/><rect x="8" y="8" width="3" height="1" fill="#B96A4A"/></svg>',
    "save": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="2" y="2" width="12" height="1" fill="#2E1D12"/><rect x="2" y="13" width="12" height="1" fill="#2E1D12"/><rect x="2" y="2" width="1" height="12" fill="#2E1D12"/><rect x="13" y="2" width="1" height="12" fill="#2E1D12"/><rect x="4" y="3" width="7" height="3" fill="#2E1D12"/><rect x="5" y="4" width="2" height="2" fill="#B96A4A"/><rect x="4" y="8" width="8" height="5" fill="#2E1D12"/><rect x="5" y="9" width="6" height="1" fill="#FFF6E8"/><rect x="5" y="11" width="6" height="1" fill="#FFF6E8"/></svg>',
    "robot": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="7" y="1" width="2" height="2" fill="#2E1D12"/><rect x="3" y="3" width="10" height="1" fill="#2E1D12"/><rect x="3" y="9" width="10" height="1" fill="#2E1D12"/><rect x="3" y="3" width="1" height="7" fill="#2E1D12"/><rect x="12" y="3" width="1" height="7" fill="#2E1D12"/><rect x="5" y="5" width="2" height="2" fill="#B96A4A"/><rect x="9" y="5" width="2" height="2" fill="#B96A4A"/><rect x="6" y="8" width="4" height="1" fill="#2E1D12"/><rect x="1" y="5" width="2" height="1" fill="#2E1D12"/><rect x="13" y="5" width="2" height="1" fill="#2E1D12"/><rect x="4" y="10" width="2" height="4" fill="#2E1D12"/><rect x="10" y="10" width="2" height="4" fill="#2E1D12"/></svg>',
    "download": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="7" y="2" width="2" height="5" fill="#2E1D12"/><rect x="5" y="7" width="6" height="1" fill="#2E1D12"/><rect x="6" y="8" width="4" height="1" fill="#2E1D12"/><rect x="7" y="9" width="2" height="1" fill="#2E1D12"/><rect x="2" y="12" width="12" height="1" fill="#2E1D12"/><rect x="2" y="12" width="1" height="2" fill="#2E1D12"/><rect x="13" y="12" width="1" height="2" fill="#2E1D12"/></svg>',
    "shelf": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="2" y="3" width="2" height="9" fill="#B96A4A"/><rect x="5" y="2" width="2" height="10" fill="#6E8B5B"/><rect x="8" y="4" width="2" height="8" fill="#A86A33"/><rect x="11" y="3" width="2" height="9" fill="#D7A441"/><rect x="1" y="12" width="14" height="1" fill="#2E1D12"/><rect x="1" y="13" width="1" height="2" fill="#2E1D12"/><rect x="14" y="13" width="1" height="2" fill="#2E1D12"/></svg>',
    "chart": '<svg xmlns="http://www.w3.org/2000/svg" class="px-ic" viewBox="0 0 16 16" shape-rendering="crispEdges"><rect x="2" y="10" width="2" height="4" fill="#B96A4A"/><rect x="6" y="7" width="2" height="7" fill="#6E8B5B"/><rect x="10" y="4" width="2" height="10" fill="#D7A441"/><rect x="1" y="14" width="13" height="1" fill="#2E1D12"/></svg>',
}

# 左侧导航菜单（spec v1 §9 模块 A；key → Chinese label + emoji icon，阶段 8 会换像素 SVG）
NAV_ITEMS = [
    ("shelf",    "书架",      "📚"),
    ("reading",  "正在阅读",  "📖"),
    ("upload",   "上传书籍",  "📤"),
    ("notes",    "摘录笔记",  "✏️"),
    ("ai",       "AI 助读",   "🤖"),
    ("settings", "阅读设置",  "⚙"),
    ("stats",    "阅读统计",  "📊"),
]
NAV_LABELS = {k: label for k, label, _ in NAV_ITEMS}

# 阅读页配色主题（bg = 纸底，fg = 墨色）
READING_THEMES = {
    "奶油": {"bg": "var(--mc-cream)", "fg": "var(--mc-ink)"},
    "米黄": {"bg": "#f3e4c0", "fg": "#4a3419"},
    "护眼": {"bg": "#dae8d1", "fg": "#2d3e2a"},
    "凉灰": {"bg": "#e0e6ec", "fg": "#2a3340"},
    "暮色": {"bg": "#3a3228", "fg": "#e8d9b4"},
}

# 2. 全局自定义样式
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Noto+Serif+SC:wght@400;700;900&family=Noto+Sans+SC:wght@400;500;700&family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">', unsafe_allow_html=True)
st.markdown("""
<style>
/* ==========================================================================
   色板 token（spec v1 第 5.1 节）
   —— mc-* = main-console，UI 改版后新色板
   —— SVG fill/stroke 不能用 var()，直接用具体 hex（以下 token 仅用于 CSS）
   —— 详见 DESIGN_SPEC.md §5.1
   ========================================================================== */
:root {
    /* 核心色 */
    --mc-ink: #2E1D12;              /* 深文字 */
    --mc-cream: #FFF6E8;            /* 浅纸白（书页纸张） */
    --mc-paper: #F6E7C8;            /* 奶油纸（卡片底） */
    --mc-mustard: #D7A441;          /* 金黄强调（进度/高亮） */
    --mc-terra: #B96A4A;            /* 柔红棕（强调按钮/shadow） */
    --mc-moss: #6E8B5B;             /* 苔绿（成功/已读） */
    --mc-dusty: #7a96b4;            /* 蓝调（spec 无，保留原值） */

    /* 木质系列 */
    --mc-wood-deep: #3B2416;        /* 最外层深木棕（背景） */
    --mc-wood-mid: #6B4024;         /* 中木棕（中层框） */
    --mc-wood-light: #A86A33;       /* 焦糖棕（主按钮底） */

    /* 辅助色 */
    --mc-lamp-yellow: #F2C66D;      /* 暖灯黄 */
    --mc-gray-brown: #8E735B;       /* 次级灰棕（placeholder/分隔） */

    /* 次级变体（兼容现有样式） */
    --mc-paper-highlight: #FFFEF8;
    --mc-paper-alt: #E8DCBC;
    --mc-terra-light: #E07B5A;
    --mc-ink-soft: #6B5843;
    --mc-wood-brown: #8B5E3C;
}

/* ==========================================================================
   阶段 2 四区骨架占位（mc-zone-placeholder）
   —— 本阶段仅验证 CSS Grid × Streamlit st.columns 布局可行
   —— 后续阶段 3/4/7 会逐一替换这些占位
   ========================================================================== */
.mc-zone-placeholder {
    border: 2px dashed var(--mc-terra);
    background: rgba(185, 106, 74, 0.08);
    color: var(--mc-gray-brown);
    text-align: center;
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 11px;
    letter-spacing: 1.5px;
    padding: 18px 12px;
    margin: 6px 0;
    line-height: 1.8;
    user-select: none;
}
.mc-topbar-slot {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 12px;
}
.mc-nav-slot {
    min-height: 480px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.mc-right-slot {
    min-height: 480px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.mc-bottom-slot {
    min-height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* ==========================================================================
   阶段 3 左侧导航区（.mc-nav-*）
   —— 对照 DESIGN_SPEC §9 模块 A：深木棕立柜 + 品牌 + 7 菜单 + 底部装饰
   ========================================================================== */

/* 整列背景：找到含 .mc-nav-brand 的 stColumn，应用深木棕底 */
[data-testid="stColumn"]:has(.mc-nav-brand) {
    background: var(--mc-wood-deep) !important;
    border: 2px solid var(--mc-ink) !important;
    padding: 0 !important;
    margin: 0 !important;
    min-height: 640px;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stColumn"]:has(.mc-nav-brand) > div {
    padding: 0 !important;
    flex: 1;
    display: flex;
    flex-direction: column;
}

/* 品牌区 */
.mc-nav-brand {
    padding: 22px 14px 18px 14px;
    text-align: center;
    border-bottom: 1px solid var(--mc-wood-mid);
    background: linear-gradient(180deg, rgba(107, 64, 36, 0.5) 0%, transparent 100%);
}
.mc-nav-brand-title {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 28px;
    color: var(--mc-cream);
    letter-spacing: 6px;
    margin: 0 0 8px 0;
    text-shadow: 3px 3px 0 var(--mc-wood-mid);
    line-height: 1.2;
}
.mc-nav-brand-subtitle {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 11px;
    color: var(--mc-cream);
    opacity: 0.78;
    letter-spacing: 2px;
    margin: 0;
}
.mc-nav-brand-figure {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 8px;
    margin-top: 14px;
}
.mc-nav-brand-figure svg {
    image-rendering: pixelated;
    shape-rendering: crispEdges;
}

/* 7 菜单项样式：通过 st-key-nav_* 定位 Streamlit button */
[class*="st-key-nav_"] {
    margin: 0 !important;
    padding: 0 !important;
}
[class*="st-key-nav_"] button {
    background: transparent !important;
    color: var(--mc-cream) !important;
    border: 0 !important;
    border-left: 3px solid transparent !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    font-family: 'Zpix', 'Noto Sans SC', monospace !important;
    font-size: 15px !important;
    letter-spacing: 3px !important;
    padding: 14px 16px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    transition: background 0.15s ease, border-left-color 0.15s ease !important;
    width: 100% !important;
}
[class*="st-key-nav_"] button p {
    margin: 0 !important;
    color: var(--mc-cream) !important;
    font-size: 15px !important;
    letter-spacing: 3px !important;
}
[class*="st-key-nav_"] button:hover {
    background: rgba(168, 106, 51, 0.28) !important;
    transform: none !important;
    border-left-color: var(--mc-wood-light) !important;
}
[class*="st-key-nav_"] button:focus-visible {
    outline: 2px solid var(--mc-mustard) !important;
    outline-offset: -4px !important;
}
[class*="st-key-nav_"] button .px-ic {
    margin-right: 10px;
    vertical-align: -3px;
}
/* 菜单区 wrapper：让它占据中段空间 */
.mc-nav-menu-wrap {
    flex: 1;
    padding: 6px 0 0 0;
}

/* 底部装饰 */
.mc-nav-decor {
    padding: 18px 14px 22px 14px;
    text-align: center;
    border-top: 1px solid var(--mc-wood-mid);
    background: linear-gradient(0deg, rgba(107, 64, 36, 0.6) 0%, transparent 100%);
}
.mc-nav-decor svg {
    image-rendering: pixelated;
    shape-rendering: crispEdges;
}

/* 中央列的"即将上线"占位（非 reading 视图） */
.mc-soon-placeholder {
    padding: 80px 30px;
    text-align: center;
    background: var(--mc-cream);
    border: 3px dashed var(--mc-gray-brown);
    margin: 40px 20px;
    border-radius: 4px;
    color: var(--mc-ink);
}
.mc-soon-placeholder h2 {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 20px;
    color: var(--mc-wood-light);
    margin: 0 0 20px 0;
    letter-spacing: 2px;
}
.mc-soon-placeholder p {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 14px;
    color: var(--mc-ink-soft);
    line-height: 1.8;
    margin: 6px 0;
    letter-spacing: 1px;
}
.mc-soon-placeholder .mc-soon-icon {
    font-size: 48px;
    margin-bottom: 20px;
}

/* ==========================================================================
   阶段 4 顶部状态条（.mc-topbar-*）
   —— spec v1 §9 模块 B：横向木质工具条 + 书信息 + 进度 + 5 icon popover
   ========================================================================== */

/* 整条状态条的 st.columns 所在行：统一背景为浅木色 */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] .mc-topbar-info) {
    background: var(--mc-paper);
    border: 2px solid var(--mc-ink);
    box-shadow: 3px 3px 0 var(--mc-wood-mid);
    padding: 8px 12px !important;
    margin: 0 0 14px 0 !important;
    align-items: center !important;
    gap: 8px !important;
}

/* 左侧信息区（HTML） */
.mc-topbar-info {
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    color: var(--mc-ink);
    flex-wrap: nowrap;
    overflow: hidden;
    min-width: 0;
}
.mc-topbar-book-icon {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
}
.mc-topbar-book-icon .px-ic {
    width: 22px;
    height: 22px;
}
.mc-topbar-title {
    font-weight: 700;
    font-size: 15px;
    color: var(--mc-ink);
    letter-spacing: 0.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 360px;
    flex-shrink: 1;
}
.mc-topbar-author {
    color: var(--mc-gray-brown);
    font-size: 13px;
    flex-shrink: 0;
}
.mc-topbar-sep {
    color: var(--mc-gray-brown);
    font-size: 13px;
    flex-shrink: 0;
}
.mc-topbar-chapter {
    font-size: 13px;
    color: var(--mc-ink);
    letter-spacing: 0.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
    flex-shrink: 1;
}
.mc-topbar-progress {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: auto;
    flex-shrink: 0;
}
.mc-topbar-progress-label {
    font-size: 12px;
    color: var(--mc-ink-soft);
    font-family: 'Press Start 2P', 'Zpix', monospace;
    letter-spacing: 1px;
    white-space: nowrap;
}
.mc-topbar-progress-bar {
    width: 140px;
    height: 8px;
    background: var(--mc-paper-alt);
    border: 1px solid var(--mc-wood-brown);
}
.mc-topbar-progress-fill {
    height: 100%;
    background: var(--mc-mustard);
    transition: width 0.3s ease;
}

/* 右侧 5 个 popover / button —— 用 st-key-tb_* 定位 */
[class*="st-key-tb_"] {
    margin: 0 !important;
}
[class*="st-key-tb_"] > button,
[class*="st-key-tb_"] [data-testid="stPopoverButton"] {
    background: transparent !important;
    color: var(--mc-ink) !important;
    border: 2px solid var(--mc-ink) !important;
    box-shadow: 2px 2px 0 var(--mc-wood-mid) !important;
    border-radius: 0 !important;
    font-family: 'Press Start 2P', 'Zpix', monospace !important;
    font-size: 14px !important;
    padding: 6px 10px !important;
    min-height: 38px !important;
    width: 100% !important;
    transition: background 0.15s ease !important;
}
[class*="st-key-tb_"] > button:hover,
[class*="st-key-tb_"] [data-testid="stPopoverButton"]:hover {
    background: var(--mc-cream) !important;
    transform: translate(-1px, -1px) !important;
    box-shadow: 3px 3px 0 var(--mc-wood-mid) !important;
}
[class*="st-key-tb_"] > button p,
[class*="st-key-tb_"] [data-testid="stPopoverButton"] p {
    margin: 0 !important;
    color: var(--mc-ink) !important;
    font-size: 14px !important;
}
/* 用户头像 popover：特殊背景色 */
.st-key-tb_avatar > button,
.st-key-tb_avatar [data-testid="stPopoverButton"] {
    background: var(--mc-wood-light) !important;
    color: var(--mc-cream) !important;
}
.st-key-tb_avatar > button p,
.st-key-tb_avatar [data-testid="stPopoverButton"] p {
    color: var(--mc-cream) !important;
}

/* ==========================================================================
   阶段 5 中央阅读器重做（.mc-reader-frame / .mc-reader-ctrl）
   —— spec v1 §9 模块 C：木质外框 + 双页书本 + 6 按钮控制条
   ========================================================================== */

/* 木质外框：包住 book-spread */
.mc-reader-frame {
    padding: 22px 20px;
    background: var(--mc-wood-mid);
    border: 3px solid var(--mc-wood-deep);
    border-radius: 4px;
    box-shadow: inset 0 0 0 2px var(--mc-wood-light), 5px 5px 0 var(--mc-wood-deep);
    position: relative;
}
.mc-reader-frame::before, .mc-reader-frame::after {
    content: "[+]";
    position: absolute;
    font-family: 'Press Start 2P', monospace;
    font-size: 10px;
    color: var(--mc-mustard);
    opacity: 0.8;
}
.mc-reader-frame::before { top: 6px; left: 8px; }
.mc-reader-frame::after  { bottom: 6px; right: 8px; }

/* 6 按钮控制条：st.columns 所在的水平块 */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] .st-key-rd_prev) {
    background: var(--mc-paper);
    border: 2px solid var(--mc-ink);
    box-shadow: 3px 3px 0 var(--mc-wood-mid);
    padding: 10px 14px !important;
    margin: 14px 0 !important;
    align-items: center !important;
    gap: 8px !important;
}

/* 控制条按钮 & popover 统一样式 */
[class*="st-key-rd_"] {
    margin: 0 !important;
}
[class*="st-key-rd_"] > button,
[class*="st-key-rd_"] [data-testid="stPopoverButton"] {
    background: var(--mc-cream) !important;
    color: var(--mc-ink) !important;
    border: 2px solid var(--mc-ink) !important;
    box-shadow: 2px 2px 0 var(--mc-wood-mid) !important;
    border-radius: 0 !important;
    font-family: 'Zpix', 'Noto Sans SC', sans-serif !important;
    font-size: 13px !important;
    padding: 8px 12px !important;
    min-height: 40px !important;
    width: 100% !important;
    letter-spacing: 1px !important;
    transition: background 0.15s ease !important;
}
[class*="st-key-rd_"] > button:hover,
[class*="st-key-rd_"] [data-testid="stPopoverButton"]:hover {
    background: var(--mc-mustard) !important;
    transform: translate(-1px, -1px) !important;
    box-shadow: 3px 3px 0 var(--mc-wood-mid) !important;
}
[class*="st-key-rd_"] > button:disabled,
[class*="st-key-rd_"] > button[disabled] {
    background: var(--mc-paper-alt) !important;
    color: var(--mc-gray-brown) !important;
    opacity: 0.6 !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: 1px 1px 0 var(--mc-wood-brown) !important;
}
[class*="st-key-rd_"] > button p,
[class*="st-key-rd_"] [data-testid="stPopoverButton"] p {
    margin: 0 !important;
    color: inherit !important;
    font-size: 13px !important;
}
/* 主翻页按钮（rd_prev / rd_next）：焦糖棕底更突出 */
.st-key-rd_prev > button,
.st-key-rd_next > button {
    background: var(--mc-wood-light) !important;
    color: var(--mc-cream) !important;
    font-weight: 700 !important;
}
.st-key-rd_prev > button p,
.st-key-rd_next > button p {
    color: var(--mc-cream) !important;
}
.st-key-rd_prev > button:hover,
.st-key-rd_next > button:hover {
    background: var(--mc-terra) !important;
}

/* ==========================================================================
   阶段 6 右侧 AI 助读区（.mc-ai-*）
   —— spec v1 §9 模块 D：标题 + 4 tab + 卡片式回答 + 自定义输入
   ========================================================================== */

/* 整个 AI 列：奶油底 + 木纹边框 */
[data-testid="stColumn"]:has(.mc-ai-title) {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    box-shadow: 3px 3px 0 var(--mc-wood-mid) !important;
    padding: 14px 12px !important;
    margin: 0 !important;
    min-height: 640px;
}

/* 顶部标题区 */
.mc-ai-title {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 4px 12px 4px;
    border-bottom: 2px dashed var(--mc-wood-brown);
    margin-bottom: 12px;
    position: relative;
}
.mc-ai-title-icon .px-ic { width: 22px; height: 22px; }
.mc-ai-title-text {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 16px;
    color: var(--mc-ink);
    letter-spacing: 2px;
    flex: 1;
}
.mc-ai-title-pin {
    font-size: 16px;
    color: var(--mc-terra);
    transform: rotate(20deg);
    margin-right: 4px;
}

/* 4 个 tab 按钮：通过 st-key-ai_tab_* 命中 */
[class*="st-key-ai_tab_"] {
    margin: 0 !important;
}
[class*="st-key-ai_tab_"] > button {
    background: transparent !important;
    color: var(--mc-ink) !important;
    border: 2px solid var(--mc-wood-brown) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    font-family: 'Zpix', 'Noto Sans SC', sans-serif !important;
    font-size: 12px !important;
    padding: 6px 4px !important;
    min-height: 32px !important;
    width: 100% !important;
    letter-spacing: 1px !important;
    transition: background 0.15s ease !important;
}
[class*="st-key-ai_tab_"] > button:hover {
    background: var(--mc-mustard) !important;
    border-color: var(--mc-ink) !important;
    transform: none !important;
}
[class*="st-key-ai_tab_"] > button p {
    margin: 0 !important;
    color: inherit !important;
    font-size: 12px !important;
}
/* "问这段" tab 默认高亮（focus 行为） */
.st-key-ai_tab_ask > button {
    background: var(--mc-wood-light) !important;
    color: var(--mc-cream) !important;
    border-color: var(--mc-ink) !important;
}
.st-key-ai_tab_ask > button p {
    color: var(--mc-cream) !important;
}

/* 输入区表单：text_input + submit button 横排 */
[class*="st-key-mc_ai_input"] input,
.stForm [data-testid="stTextInput"] input {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', sans-serif !important;
    font-size: 13px !important;
    padding: 8px 10px !important;
}
[data-testid="stColumn"]:has(.mc-ai-title) [data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin-top: 8px !important;
}
[data-testid="stColumn"]:has(.mc-ai-title) [data-testid="stFormSubmitButton"] > button {
    background: var(--mc-wood-light) !important;
    color: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    box-shadow: 2px 2px 0 var(--mc-wood-mid) !important;
    border-radius: 0 !important;
    font-family: 'Press Start 2P', monospace !important;
    font-size: 14px !important;
    padding: 8px 4px !important;
    min-height: 38px !important;
    width: 100% !important;
}
[data-testid="stColumn"]:has(.mc-ai-title) [data-testid="stFormSubmitButton"] > button:hover {
    background: var(--mc-terra) !important;
    transform: translate(-1px, -1px) !important;
}

/* ==========================================================================
   阶段 7 底部四卡（.mc-card-*）
   —— spec v1 §9 模块 E：书架 / 摘录与笔记 / 上传 / 统计
   ========================================================================== */

/* 4 卡所在的水平块：整体框 */
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] .mc-card-library),
[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] .mc-card-upload) {
    margin-top: 18px !important;
    gap: 12px !important;
}

/* 每张卡列：奶油底 + 木框 */
[data-testid="stColumn"]:has(.mc-card-library),
[data-testid="stColumn"]:has(.mc-card-notes),
[data-testid="stColumn"]:has(.mc-card-upload),
[data-testid="stColumn"]:has(.mc-card-stats) {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    box-shadow: 3px 3px 0 var(--mc-wood-mid) !important;
    padding: 14px 14px !important;
    min-height: 240px;
}

/* 卡片标题 */
.mc-card-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 2px dashed var(--mc-wood-brown);
}
.mc-card-title-left {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 13px;
    color: var(--mc-ink);
    letter-spacing: 1.5px;
}
.mc-card-title-left .px-ic { width: 16px; height: 16px; }
.mc-card-viewall {
    font-family: 'Zpix', sans-serif;
    font-size: 11px;
    color: var(--mc-wood-light);
    cursor: default;
    letter-spacing: 0.5px;
}

/* 书架卡：4 封面 grid */
.mc-lib-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 6px;
}
.mc-lib-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
}
.mc-lib-cover {
    width: 100%;
    aspect-ratio: 3 / 4;
    border: 2px solid var(--mc-ink);
    box-shadow: 2px 2px 0 var(--mc-wood-mid);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Zpix', 'Noto Serif SC', serif;
    font-size: 11px;
    color: var(--mc-cream);
    text-align: center;
    padding: 6px 4px;
    line-height: 1.3;
    overflow: hidden;
    word-break: break-all;
}
.mc-lib-name {
    font-size: 11px;
    color: var(--mc-ink);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
    font-family: 'Zpix', sans-serif;
}
.mc-lib-progress-wrap {
    width: 100%;
    height: 4px;
    background: var(--mc-paper-alt);
    border: 1px solid var(--mc-wood-brown);
}
.mc-lib-progress-fill {
    height: 100%;
    background: var(--mc-mustard);
}
.mc-lib-percent {
    font-size: 10px;
    color: var(--mc-gray-brown);
    font-family: 'Press Start 2P', monospace;
}
.mc-lib-empty {
    text-align: center;
    padding: 30px 10px;
    color: var(--mc-gray-brown);
    font-family: 'Zpix', sans-serif;
    font-size: 12px;
    line-height: 1.8;
}

/* 摘录笔记卡 */
.mc-notes-quote {
    background: var(--mc-paper);
    border-left: 3px solid var(--mc-terra);
    padding: 10px 12px;
    font-family: 'Zpix', 'Noto Serif SC', serif;
    font-size: 12px;
    color: var(--mc-ink);
    line-height: 1.8;
    margin-bottom: 8px;
    position: relative;
}
.mc-notes-quote::before {
    content: "\201C";
    position: absolute;
    top: -2px;
    left: 6px;
    font-size: 20px;
    color: var(--mc-wood-light);
    font-family: Georgia, serif;
}
.mc-notes-meta {
    font-size: 11px;
    color: var(--mc-gray-brown);
    margin-bottom: 10px;
    font-family: 'Zpix', sans-serif;
}
.mc-notes-body {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-family: 'Zpix', sans-serif;
    font-size: 12px;
    color: var(--mc-ink);
    line-height: 1.7;
    margin-bottom: 6px;
}
.mc-notes-body-label {
    color: var(--mc-wood-light);
    flex-shrink: 0;
}
.mc-notes-date {
    font-size: 11px;
    color: var(--mc-gray-brown);
    text-align: right;
    font-family: 'Press Start 2P', monospace;
    margin-top: auto;
}

/* 上传卡（file_uploader 包在内） */
.mc-card-upload .mc-upload-hint {
    font-family: 'Zpix', sans-serif;
    font-size: 11px;
    color: var(--mc-gray-brown);
    text-align: center;
    margin-bottom: 8px;
}
[data-testid="stColumn"]:has(.mc-card-upload) [data-testid="stFileUploader"] {
    background: transparent !important;
}
[data-testid="stColumn"]:has(.mc-card-upload) [data-testid="stFileUploader"] section {
    background: var(--mc-paper) !important;
    border: 2px dashed var(--mc-wood-light) !important;
    border-radius: 0 !important;
    padding: 16px 10px !important;
    min-height: 90px !important;
}
[data-testid="stColumn"]:has(.mc-card-upload) [data-testid="stFileUploader"] button {
    background: var(--mc-wood-light) !important;
    color: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    box-shadow: 2px 2px 0 var(--mc-wood-mid) !important;
    border-radius: 0 !important;
    font-family: 'Zpix', sans-serif !important;
    font-size: 12px !important;
}

/* 统计卡：3 行 */
.mc-stats-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 4px;
    border-bottom: 1px dotted var(--mc-wood-brown);
}
.mc-stats-row:last-child { border-bottom: none; }
.mc-stats-icon {
    font-size: 18px;
    margin-right: 6px;
}
.mc-stats-label {
    flex: 1;
    font-family: 'Zpix', sans-serif;
    font-size: 12px;
    color: var(--mc-ink);
}
.mc-stats-value {
    font-family: 'Press Start 2P', monospace;
    font-size: 14px;
    color: var(--mc-wood-light);
    letter-spacing: 1px;
}
.mc-stats-delta {
    font-family: 'Zpix', sans-serif;
    font-size: 10px;
    margin-left: 8px;
    padding: 2px 6px;
    border-radius: 2px;
    white-space: nowrap;
}
.mc-stats-delta.up {
    color: var(--mc-moss);
    background: rgba(110, 139, 91, 0.15);
}
.mc-stats-delta.down {
    color: var(--mc-terra);
    background: rgba(185, 106, 74, 0.15);
}
.mc-stats-delta.flat {
    color: var(--mc-gray-brown);
    background: rgba(142, 115, 91, 0.1);
}

/* 主标题：像素刊头（原 Caveat 手写体像素化） */
.handwrite-title {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 12px;
    font-weight: 400;
    color: var(--mc-ink);
    text-align: center;
    margin: 12px 0 12px 0;
    letter-spacing: 3px;
    text-shadow: 2px 2px 0 var(--mc-mustard);
    text-transform: uppercase;
}
.handwrite-title .hw-dot {
    color: var(--mc-terra);
    margin: 0 8px;
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

    /* 不再通用压缩 h1 / h2：.zw-title 是 h1 超大像素字，不能被一刀切到 24px。
       只对没有专属类名的 h1/h2 收敛（放 Streamlit 默认 st.title/st.subheader 的兜底）*/
    h1:not(.zw-title):not(.handwrite-title) { font-size: 24px !important; }
    h2:not([class]), .stSubheader { font-size: 18px !important; }
    /* 手机上 .zw-title 专属大小，保持首屏冲击（但比桌面小一号） */
    .zw-title { font-size: 54px !important; letter-spacing: 6px !important; }
}

@media (max-width: 480px) {
    .book-page {
        padding: 16px 12px;
        min-height: 220px;
        font-size: 15px;
    }
}

/* ===== 减少动效偏好（a11y）：所有入场 / 循环动画禁用或瞬完 ===== */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
    /* 仍然给 hover 反馈一个瞬时变化，不破坏可用性 */
    .reading-area .nav-btn,
    body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button {
        transition: background 0.01ms !important;
    }
}

/* ===== 阅读区域：像素风（与欢迎页同一套调色） ===== */
/* 顶部 header 保持存在（防止 Streamlit 内部渲染失衡），只换成奶油色与页面融合 */
body:has(.reading-area) header[data-testid="stHeader"] {
    background: var(--mc-paper) !important;
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
    background-color: var(--mc-paper) !important;
}

/* A1：侧栏背景奶油 + 右侧虚线分隔（仅改最外层 section，不动任何子元素） */
body:has(.reading-area) section[data-testid="stSidebar"] {
    background: #e8dcbc !important;
    border-right: 2px dashed var(--mc-ink) !important;
}
/* A2：侧栏文字颜色深棕 + Zpix 像素字体
   只命中 widget 的 <label>、独立 st.markdown/st.caption 的段落/粗体
   —— 刻意避开按钮内的 stMarkdownContainer（按钮留到 A3 统一改），
   避免当前阶段按钮文本字体或颜色错乱 */
body:has(.reading-area) section[data-testid="stSidebar"] label,
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stMarkdown"] strong {
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
}

/* A3：侧栏按钮方角像素化（与欢迎页 upload 按钮同一视觉语言）
   只改 stButton 的 button 元素本体和其内部 <p>；不碰 chat_input 的 send 按钮
   （chat_input 是 stChatInput，不是 stButton，自然不会被命中） */
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: var(--mc-ink) !important;
    color: var(--mc-paper) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 3px 3px 0 var(--mc-mustard) !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
    transition: transform 0.08s steps(2), box-shadow 0.08s steps(2), background 0.15s !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: var(--mc-terra) !important;
    color: #fffef8 !important;
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0 var(--mc-mustard) !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button:focus-visible {
    outline: 2px solid var(--mc-terra) !important;
    outline-offset: 3px !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stButton"] > button p {
    color: inherit !important;
    font-family: inherit !important;
}

/* A4：侧栏 selectbox 最外层可见框方角 + 奶油底
   只命中 BaseWeb select 的外层 div；不动弹出层（弹出层走 portal 挂到 body 上，
   不是这个选择器的后代），不动 position/display 相关属性 */
body:has(.reading-area) section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 2px 2px 0 var(--mc-mustard) !important;
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
}

/* A5：侧栏 slider 拇指方角像素化
   只改 role="slider" 的拇指本体；轨道与刻度保持 Streamlit 默认（不碰尺寸、
   位置、transform，避免影响拖拽手势的命中区域） */
body:has(.reading-area) section[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {
    background: var(--mc-terra) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 2px 2px 0 var(--mc-ink) !important;
}

/* A6：侧栏 number_input（跳转页码）方角像素化 */
/* 去掉外层容器多余的边框 / 圆角 / 阴影 */
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] > div,
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] [data-baseweb="input"],
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] [data-baseweb="base-input"] {
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    background: transparent !important;
    outline: none !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] input {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    color: var(--mc-ink) !important;
    font-family: 'Press Start 2P', 'Zpix', monospace !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {
    background: var(--mc-ink) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    color: var(--mc-paper) !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] button:hover {
    background: var(--mc-terra) !important;
}
body:has(.reading-area) section[data-testid="stSidebar"] [data-testid="stNumberInput"] button svg {
    fill: var(--mc-paper) !important;
    color: var(--mc-paper) !important;
}

/* B1：主区分隔线（st.divider）换成虚线深棕；AI 小标题本身已由
   MainBlockContainer h3 规则自动像素化，不再重复 */
body:has(.reading-area) [data-testid="stMainBlockContainer"] hr {
    border: none !important;
    border-top: 2px dashed var(--mc-ink) !important;
    background: transparent !important;
    margin: 18px 0 !important;
    opacity: 1 !important;
}

/* B2：AI 聊天气泡只改 bg + text color，不动 border-radius/position/margin
   —— 之前的 bug 正是因为改了 margin 和通配 * color 导致 chat_input 跑位 */
body:has(.reading-area) [data-testid="stChatMessage"] {
    background: var(--mc-cream) !important;
}
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
body:has(.reading-area) [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code {
    color: var(--mc-ink) !important;
}

/* B3（新版）：chat_input 的 textarea 同时设 bg + text color + 字体
   不碰 stChatInput / stBottom 外层容器的 position/margin/bg/border/box-shadow
   textarea 是叶子元素，覆盖其 bg 不影响布局定位 */
body:has(.reading-area) [data-testid="stChatInput"] textarea {
    background: var(--mc-cream) !important;
    color: var(--mc-ink) !important;
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
    background: var(--mc-paper) !important;
}
/* B3.6：chat_input 内层 baseweb 包装（真正那个黑色圆角框）也统一成米白
   覆盖多种可能的内层 DOM 结构 */
body:has(.reading-area) [data-testid="stChatInput"] > div,
body:has(.reading-area) [data-testid="stChatInput"] > div > div,
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="textarea"],
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="input"],
body:has(.reading-area) [data-testid="stChatInput"] [data-baseweb="base-input"] {
    background: var(--mc-cream) !important;
}

/* B4：chat_input 外观完整像素化
   —— 仅最外层直接子 div 加边框 + 偏移阴影（避免多层重复描边）
   —— 内层 baseweb / textarea 去掉圆角和边框，保持方角一致 */
body:has(.reading-area) [data-testid="stChatInput"] > div {
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 3px 3px 0 var(--mc-mustard) !important;
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
    background: var(--mc-ink) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
}
body:has(.reading-area) [data-testid="stChatInput"] button:hover {
    background: var(--mc-terra) !important;
}
body:has(.reading-area) [data-testid="stChatInput"] button:focus-visible {
    outline: 2px solid var(--mc-terra) !important;
    outline-offset: 3px !important;
}
body:has(.reading-area) [data-testid="stChatInput"] button svg {
    fill: var(--mc-paper) !important;
    color: var(--mc-paper) !important;
}


/* 章节标题（只改主区里的，避开侧栏和 chat 内部） */
body:has(.reading-area) [data-testid="stMainBlockContainer"] h1,
body:has(.reading-area) [data-testid="stMainBlockContainer"] h2,
body:has(.reading-area) [data-testid="stMainBlockContainer"] h3 {
    color: var(--mc-ink) !important;
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
    border-top: 2px solid var(--mc-ink);
    border-bottom: 2px dashed var(--mc-ink);
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: var(--mc-ink);
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
    color: var(--mc-ink);
    max-width: 50%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-transform: none;
}
.rd-topbar .dot {
    color: var(--mc-terra);
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
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    height: 10px !important;
    box-shadow: 3px 3px 0 var(--mc-mustard) !important;
    padding: 0 !important;
}
body:has(.reading-area) .progress-fill {
    background: var(--mc-terra) !important;
    border-radius: 0 !important;
    transition: width 0.3s steps(12) !important;
}
/* 书页容器：虚线外框 + 芥末黄偏移阴影 */
.reading-area .book-spread {
    background: var(--mc-cream) !important;
    border: 2px dashed var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 6px 6px 0 var(--mc-mustard) !important;
    color: var(--mc-ink) !important;
    position: relative;
}
.reading-area .book-page-left {
    border-right: 1px dashed var(--mc-ink) !important;
}
.reading-area .book-page .page-num {
    color: var(--mc-ink) !important;
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
    color: var(--mc-terra);
    z-index: 2;
    letter-spacing: 0;
}
.reading-area .book-spread::before { content: "[+]"; top: 8px; left: 10px; }
.reading-area .book-spread::after  { content: "[+]"; bottom: 8px; right: 10px; }

/* 页码信息：主行像素刊头字体，副行 Zpix 柔化 */
.reading-area .page-indicator {
    color: var(--mc-ink) !important;
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
    color: #6b5843;
    margin-top: 4px;
}

/* 翻页按钮：方角 + 深棕底 + 芥末黄偏移阴影 */
.reading-area .nav-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 40px;
    cursor: pointer;
    user-select: none;
    text-decoration: none !important;
    background: var(--mc-ink) !important;
    color: var(--mc-paper) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0 var(--mc-mustard) !important;
    font-family: 'Press Start 2P', 'Zpix', monospace !important;
    font-size: 10px !important;
    letter-spacing: 2px !important;
    padding: 10px 18px !important;
    text-shadow: none !important;
    transition: transform 0.08s steps(2), box-shadow 0.08s steps(2), background 0.15s !important;
}
.reading-area .nav-btn:hover {
    background: var(--mc-terra) !important;
    color: #fffef8 !important;
    border-color: var(--mc-ink) !important;
    transform: translate(-2px, -2px) !important;
    box-shadow: 6px 6px 0 var(--mc-mustard) !important;
}
/* 键盘聚焦态：像素风用 terra 方框描边（默认浏览器圆角 outline 会破风格） */
.reading-area .nav-btn:focus-visible {
    outline: 2px solid var(--mc-terra) !important;
    outline-offset: 3px !important;
}
/* active（鼠标按下 / 键盘 space）：像素下压感 */
.reading-area .nav-btn:active {
    transform: translate(0, 0) !important;
    box-shadow: 2px 2px 0 var(--mc-mustard) !important;
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
/* 阶段 5：旧隐藏翻页按钮（.st-key-prev_page / .st-key-next_page）已移除，
   改由 .st-key-rd_prev / .st-key-rd_next 控制条按钮直接接管翻页。 */

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
    background-color: var(--mc-paper) !important;
    min-height: unset;
}
body:has(.zine-welcome) {
    background-color: var(--mc-paper) !important;
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

/* 调色盘：alias 到新 mc-* token（spec v1 第 5.1 节） */
.zine-welcome {
    --zw-paper: var(--mc-paper);
    --zw-paper-2: var(--mc-paper-alt);
    --zw-ink: var(--mc-ink);
    --zw-ink-soft: var(--mc-ink-soft);
    --zw-terra: var(--mc-terra);
    --zw-terra-soft: var(--mc-terra-light);
    --zw-moss: var(--mc-moss);
    --zw-mustard: var(--mc-mustard);
    --zw-dusty: var(--mc-dusty);
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
    font-family: 'Press Start 2P', monospace;
    font-size: 76px;
    font-weight: 400;
    line-height: 1.0;
    color: var(--zw-ink) !important;
    margin: 0 0 8px;
    letter-spacing: 6px;
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
    font-family: 'Press Start 2P', monospace;
    font-size: 11px;
    color: var(--zw-ink) !important;
    margin: 0 0 24px;
    letter-spacing: 2px;
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
    max-width: 480px;
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
.zw-desc .line-3 { animation: zw-typewriter 2s steps(32) 3.3s both; font-style: italic; color: var(--zw-ink) !important; }
.zw-desc .line-4 { animation: zw-typewriter 1.2s steps(18) 5.3s both; font-size: 11px; color: var(--zw-ink-soft) !important; letter-spacing: 1px; }
.zw-desc .caret {
    display: inline-block;
    width: 8px;
    height: 14px;
    background: var(--zw-terra);
    vertical-align: middle;
    margin-left: 2px;
    animation: zw-blink 1s step-end infinite;
    animation-delay: 6.5s;
    opacity: 0;
}
.zw-desc .caret.on { animation-delay: 6.5s; opacity: 1; }

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

/* 像素粒子装饰 */
@keyframes zw-sparkle {
    0%   { opacity: 0; transform: translateY(0); }
    20%  { opacity: 1; }
    80%  { opacity: 1; }
    100% { opacity: 0; transform: translateY(-14px); }
}
.zw-sparkles {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 1;
    overflow: hidden;
}
.zw-sparkles .sp {
    position: absolute;
    animation: zw-sparkle 3s ease-in-out infinite;
    opacity: 0;
}
@media (max-width: 900px) { .zw-sparkles { display: none; } }

/* 像素壁挂火把 */
@keyframes zw-f {
    0%    { opacity: 1; }
    32%   { opacity: 1; }
    32.1% { opacity: 0; }
    100%  { opacity: 0; }
}
.zw-f1 { animation: zw-f 0.6s linear 0s infinite; }
.zw-f2 { animation: zw-f 0.6s linear 0.2s infinite; opacity: 0; }
.zw-f3 { animation: zw-f 0.6s linear 0.4s infinite; opacity: 0; }
@media (max-width: 900px) { .zw-torch { display: none; } }
/* 像素心形生命值 */
@keyframes zw-heartbeat {
    0%,100% { transform: scale(1); }
    15%     { transform: scale(1.35); }
    30%     { transform: scale(1); }
    45%     { transform: scale(1.18); }
    60%     { transform: scale(1); }
}
.zw-heart-beat { animation: zw-heartbeat 2.2s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
@media (max-width: 900px) { .zw-hearts { display: none; } }

/* 像素书架书本抽出动效 */
@keyframes zw-book-pull {
    0%, 30%  { transform: translateY(0); }
    50%, 70% { transform: translateY(-10px); }
    100%     { transform: translateY(0); }
}
.zw-book-pull { animation: zw-book-pull 5s ease-in-out infinite; animation-delay: 2s; }
@media (max-width: 900px) { .zw-shelf { display: none; } }
/* 星星浮动 + 药水浮动 */
@keyframes zw-float {
    0%,100% { transform: translateY(0); }
    50%     { transform: translateY(-5px); }
}
.zw-stars  { animation: zw-float 4s ease-in-out infinite; }
.zw-potion { animation: zw-float 3.5s ease-in-out 0.8s infinite; }
@media (max-width: 900px) { .zw-stars,.zw-mushroom,.zw-plant,.zw-potion { display: none; } }

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
.ai-quick-actions-label {
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 11px;
    letter-spacing: 1px;
    color: #8b5e3c;
    margin: 6px 0 8px 2px;
    opacity: 0.85;
}
body:has(.reading-area) section[data-testid="stSidebar"] .sbh .px-ic {
    width: 12px; height: 12px; margin-right: 6px; margin-bottom: 1px;
}

/* ===== 原生 Streamlit 提示态像素化（alert / toast / spinner） ===== */
/* st.warning / st.error / st.info / st.success 外框 */
body:has(.reading-area) [data-testid="stAlert"] {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0 var(--mc-mustard) !important;
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
    padding: 14px 16px !important;
}
/* error 态改用 terra 色描边 / 投影，情绪层级清晰但仍然是像素语言 */
body:has(.reading-area) [data-testid="stAlertContentError"],
body:has(.reading-area) [data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {
    border-color: var(--mc-terra) !important;
    box-shadow: 4px 4px 0 var(--mc-terra) !important;
}
body:has(.reading-area) [data-testid="stAlert"] p,
body:has(.reading-area) [data-testid="stAlert"] div,
body:has(.reading-area) [data-testid="stAlert"] span {
    color: var(--mc-ink) !important;
    font-family: inherit !important;
}
/* Toast（toast 可能挂在 body 根，不受 reading-area 作用域限制，不加 :has 前缀） */
[data-testid="stToast"],
[data-testid="stToastContainer"] [role="status"] {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    box-shadow: 3px 3px 0 var(--mc-mustard) !important;
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', 'PingFang SC', monospace !important;
    letter-spacing: 1px !important;
}
[data-testid="stToast"] * {
    color: var(--mc-ink) !important;
    font-family: inherit !important;
}
/* Spinner：方角 + 深棕骨架（默认是彩色圆环旋转，和像素风冲突） */
body:has(.reading-area) .stSpinner > div > div,
body:has(.reading-area) [data-testid="stSpinner"] > div > div {
    border-color: var(--mc-ink) #e8dcbc #e8dcbc #e8dcbc !important;
    border-radius: 0 !important;
    border-width: 3px !important;
}
body:has(.reading-area) .stSpinner,
body:has(.reading-area) [data-testid="stSpinner"] {
    color: var(--mc-ink) !important;
    font-family: 'Zpix', monospace !important;
}
/* ===== /animate: pixel motion ===== */
/* flip-in: JS 通过 MutationObserver 检测到翻页后添加此 class */
@keyframes rb-flip-in {
    0%   { opacity: 0.1; transform: perspective(900px) rotateY(7deg) scaleX(0.97); }
    100% { opacity: 1;   transform: perspective(900px) rotateY(0deg) scaleX(1); }
}
.reading-area .book-spread {
    transform-style: preserve-3d;
}
.reading-area .book-spread.rb-anim-in {
    animation: rb-flip-in 0.28s steps(7) both;
}
/* ===== /delight: 章末烟花庆祝 ===== */
/* 烟花粒子：从爆炸点向外放射 */
@keyframes rb-fw-burst {
    0%   { opacity: 1;   transform: translate(0, 0) scale(1); }
    65%  { opacity: 0.9; }
    100% { opacity: 0;   transform: translate(var(--dx), var(--dy)) scale(0.1); }
}
/* 爆炸中心闪光 */
@keyframes rb-fw-flash {
    0%   { opacity: 1; transform: scale(0.4); }
    40%  { opacity: 0; transform: scale(2.5); }
    100% { opacity: 0; }
}
.rb-firework {
    position: fixed;
    pointer-events: none;
    z-index: 9999;
    width: 0; height: 0;
    overflow: visible;
}
.rb-fw-p {
    position: absolute;
    width: var(--sz, 7px);
    height: var(--sz, 7px);
    /* 粒子从中心点出发 */
    left: calc(var(--sz, 7px) / -2);
    top: calc(var(--sz, 7px) / -2);
    image-rendering: pixelated;
    animation: rb-fw-burst 1.3s steps(10) var(--bd, 0s) forwards;
}
.rb-fw-flash {
    position: absolute;
    width: 10px; height: 10px;
    left: -5px; top: -5px;
    background: var(--mc-cream);
    border: 1px solid var(--mc-mustard);
    image-rendering: pixelated;
    animation: rb-fw-flash 0.35s steps(4) var(--bd, 0s) forwards;
}
/* 横幅 */
@keyframes rb-banner-pop {
    0%   { opacity: 0; transform: translate(-50%, -40%) scale(0.7); }
    12%  { opacity: 1; transform: translate(-50%, -52%) scale(1.07); }
    22%  { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    78%  { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    100% { opacity: 0; transform: translate(-50%, -62%) scale(0.9); }
}
.rb-banner {
    position: fixed;
    top: 50%;
    left: 50%;
    background: var(--mc-cream);
    border: 3px solid var(--mc-ink);
    box-shadow: 6px 6px 0 var(--mc-mustard);
    color: var(--mc-ink);
    font-family: 'Press Start 2P', 'Zpix', monospace;
    font-size: 13px;
    padding: 18px 32px;
    letter-spacing: 3px;
    white-space: nowrap;
    z-index: 10000;
    pointer-events: none;
    animation: rb-banner-pop 3.4s steps(12) 0.15s forwards;
}
/* 点猫猫：鼠标变小手 */
#zw-cat-svg { cursor: pointer; }
/* keyboard hint pill shake */
@keyframes rb-shake {
    0%,100% { transform: translateX(0); }
    20%     { transform: translateX(-4px); }
    50%     { transform: translateX(4px); }
    80%     { transform: translateX(-2px); }
}
.rb-kbd-hint.rb-shake {
    animation: rb-shake 0.35s steps(4);
}
/* 每日开场签 */
.zw-daily-quote {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 18px 24px;
    margin: 0 auto 8px;
    max-width: 520px;
    border-top: 1px dashed #8a7a5a;
    border-bottom: 1px dashed #8a7a5a;
    text-align: center;
}
.zw-dq-text {
    color: var(--mc-ink);
    font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', serif;
    font-size: 14px;
    line-height: 1.8;
    letter-spacing: 1px;
}
.zw-dq-src {
    color: #8a7a5a;
    font-family: 'Zpix', 'Noto Sans SC', monospace;
    font-size: 11px;
    letter-spacing: 1px;
}
/* 笔记 expander 像素风 */
body:has(.reading-area) [data-testid="stExpander"] {
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    background: var(--mc-cream) !important;
    box-shadow: 3px 3px 0 var(--mc-mustard) !important;
}
body:has(.reading-area) [data-testid="stExpander"] summary {
    background: var(--mc-cream) !important;
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', monospace !important;
    font-size: 13px !important;
}
body:has(.reading-area) [data-testid="stExpander"] textarea {
    border: 2px solid var(--mc-ink) !important;
    border-radius: 0 !important;
    background: #fdf6e0 !important;
    color: var(--mc-ink) !important;
    font-family: 'Zpix', 'Noto Sans SC', monospace !important;
}

/* ===== 专注模式：隐藏所有干扰 UI，只留书页 ===== */
body:has(.rd-focus-flag) section[data-testid="stSidebar"],
body:has(.rd-focus-flag) [data-testid="collapsedControl"],
body:has(.rd-focus-flag) .rd-topbar,
body:has(.rd-focus-flag) .progress-container,
body:has(.rd-focus-flag) .page-indicator,
body:has(.rd-focus-flag) .nav-row,
body:has(.rd-focus-flag) [data-testid="stChatInput"],
body:has(.rd-focus-flag) [data-testid="stBottom"],
body:has(.rd-focus-flag) [data-testid="stMainBlockContainer"] hr,
body:has(.rd-focus-flag) .rd-focus-flag {
    display: none !important;
}
/* 阶段 6 后：专注模式下隐藏左侧导航列、右侧 AI 列、底部占位、TOPBAR 占位 */
body:has(.rd-focus-flag) [data-testid="stColumn"]:has(.mc-nav-brand),
body:has(.rd-focus-flag) [data-testid="stColumn"]:has(.mc-ai-title),
body:has(.rd-focus-flag) .mc-zone-placeholder,
body:has(.rd-focus-flag) [data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] .mc-topbar-info) {
    display: none !important;
}
/* 专注模式：顶部 Streamlit header 也隐藏 */
body:has(.rd-focus-flag) header[data-testid="stHeader"] {
    opacity: 0 !important;
    pointer-events: none !important;
}
/* 专注模式：主容器居中 + 更大阅读空间 */
body:has(.rd-focus-flag) [data-testid="stMainBlockContainer"] {
    padding-top: 64px !important;
    max-width: 960px !important;
}
body:has(.rd-focus-flag) .book-spread {
    box-shadow: 0 12px 48px rgba(0,0,0,0.35) !important;
}
/* 浮动退出按钮（Streamlit 会给 key 加 st-key-XXX class） */
body:has(.rd-focus-flag) .st-key-rd_focus_exit {
    position: fixed !important;
    top: 14px !important;
    right: 14px !important;
    z-index: 99999 !important;
    width: auto !important;
}
body:has(.rd-focus-flag) .st-key-rd_focus_exit button {
    background: var(--mc-cream) !important;
    border: 2px solid var(--mc-ink) !important;
    color: var(--mc-ink) !important;
    box-shadow: 3px 3px 0 var(--mc-terra) !important;
    font-family: 'Press Start 2P', 'Zpix', monospace !important;
    font-size: 11px !important;
    letter-spacing: 1.5px !important;
    padding: 8px 14px !important;
    border-radius: 0 !important;
}
body:has(.rd-focus-flag) .st-key-rd_focus_exit button:hover {
    background: var(--mc-terra) !important;
    color: var(--mc-cream) !important;
    transform: translate(-1px, -1px);
    box-shadow: 4px 4px 0 var(--mc-ink) !important;
}
/* 键盘翻页提示也隐藏（保持画面纯净，键盘照常可用） */
body:has(.rd-focus-flag) iframe[title*="components"] {
    opacity: 0 !important;
    pointer-events: none !important;
    height: 0 !important;
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
    # 回到欢迎页：清书 + 清会话相关 state，触发 rerun 显示 zine-welcome
    if st.sidebar.button("← 回到欢迎页", key="back_to_welcome", use_container_width=True):
        for _k in (
            "file_bytes", "file_name", "loaded_book",
            "messages", "chapter_select", "last_chapter",
        ):
            st.session_state.pop(_k, None)
        # 清所有 page_N 记忆，避免新书串台
        for _k in [k for k in st.session_state.keys() if str(k).startswith("page_")]:
            st.session_state.pop(_k, None)
        st.rerun()
    uploaded_file = st.sidebar.file_uploader(
        "请上传一本电子书吧～",
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

@st.cache_data(show_spinner=False)
def split_into_pages(text, chars_per_page=600):
    """将文本按段落智能分页，避免截断句子。
    cache_data：text 字符串哈希作 key；同一章节在整个进程里只分页一次。
    chapter_page_counts 的列表推导会自动吃缓存，翻页不再重算全书。"""
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


# ==== 持久化：浏览器 localStorage ====
# 旧版写到容器 ~/.reading_buddy_*.json，Streamlit Cloud 冷启即清、且多用户共用同一文件。
# 改用 streamlit-local-storage → 每个浏览器各存各的，天然隔离，容器重启不丢。
# 注意：组件异步，首帧 getItem 可能返回 None，第二次 rerun 数据到位。
from streamlit_local_storage import LocalStorage

_LS_PROGRESS_KEY = "reading_buddy_progress_v1"
_LS_BOOKMARKS_KEY = "reading_buddy_bookmarks_v1"
_LS_MESSAGES_KEY = "reading_buddy_messages_v1"
_LS_NOTES_KEY = "reading_buddy_notes_v1"
_LS_READTIME_KEY = "reading_buddy_readtime_v1"
_LS_LIBRARY_KEY = "reading_buddy_library_v1"       # 书库元数据（不存文件内容）
_LS_DAILYSTREAK_KEY = "reading_buddy_dailystreak_v1"  # 连续阅读天数 + 每日会话记录


def _get_ls():
    """懒初始化 LocalStorage 组件；挂到 session_state 保证整个 session 内同一实例。"""
    if "_rb_ls" not in st.session_state:
        st.session_state["_rb_ls"] = LocalStorage()
    return st.session_state["_rb_ls"]


def _ls_read_dict(key):
    """从 localStorage 读一个 JSON dict，容错：不存在 / 解析失败 → 空 dict。"""
    try:
        raw = _get_ls().getItem(key)
    except Exception:
        return {}
    if raw in (None, "", "null"):
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _ls_write_dict(key, data):
    try:
        _get_ls().setItem(key, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def _load_progress():
    return _ls_read_dict(_LS_PROGRESS_KEY)


def _save_progress(book_key, chapter_idx, page):
    data = _load_progress()
    data[book_key] = {
        "chapter_idx": int(chapter_idx),
        "page": int(page),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _ls_write_dict(_LS_PROGRESS_KEY, data)


def _load_bookmarks():
    return _ls_read_dict(_LS_BOOKMARKS_KEY)


def _save_bookmarks(data):
    _ls_write_dict(_LS_BOOKMARKS_KEY, data)


def _load_all_messages():
    """读取所有书的聊天记录 {book_key: [messages]}。"""
    return _ls_read_dict(_LS_MESSAGES_KEY)


def _save_book_messages(book_key, messages):
    """把当前 book_key 的聊天数组写回 localStorage，保留其它书的记录不动。"""
    all_msgs = _load_all_messages()
    all_msgs[book_key] = messages
    _ls_write_dict(_LS_MESSAGES_KEY, all_msgs)


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


def _load_all_notes():
    return _ls_read_dict(_LS_NOTES_KEY)


def _save_book_notes(book_key, notes):
    all_notes = _load_all_notes()
    all_notes[book_key] = notes
    _ls_write_dict(_LS_NOTES_KEY, all_notes)


def _add_note(book_key, chapter_idx, page, passage, note_text):
    from datetime import timezone, timedelta
    all_notes = _load_all_notes()
    lst = all_notes.setdefault(book_key, [])
    import uuid
    lst.append({
        "id": str(uuid.uuid4())[:8],
        "chapter_idx": int(chapter_idx),
        "page": int(page),
        "passage": passage.strip(),
        "note": note_text.strip(),
        "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M"),
    })
    _ls_write_dict(_LS_NOTES_KEY, all_notes)


def _remove_note(book_key, note_id):
    all_notes = _load_all_notes()
    lst = all_notes.get(book_key, [])
    all_notes[book_key] = [n for n in lst if n.get("id") != note_id]
    _ls_write_dict(_LS_NOTES_KEY, all_notes)


def _load_reading_times():
    """读取所有书的累计阅读秒数 {book_key: seconds}。"""
    return _ls_read_dict(_LS_READTIME_KEY)


def _format_duration(seconds):
    """把秒数格式化成中文友好的时长字符串。"""
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds} 秒"
    if seconds < 3600:
        return f"{seconds // 60} 分钟"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if minutes == 0:
        return f"{hours} 小时"
    return f"{hours} 小时 {minutes} 分钟"


def _load_library():
    """读取书库元数据 {book_key: {title, chapter_count, uploaded_at, last_opened_at, cover_color}}。"""
    return _ls_read_dict(_LS_LIBRARY_KEY)


def _save_library(data):
    _ls_write_dict(_LS_LIBRARY_KEY, data)


def _pick_cover_color(book_key):
    """根据书名哈希确定性地选一个封面色（6 个主色轮转）。"""
    _palette = ["#B96A4A", "#6E8B5B", "#A86A33", "#D7A441", "#7a96b4", "#8B5E3C"]
    return _palette[abs(hash(book_key)) % len(_palette)]


def _record_book_in_library(book_key, chapter_count):
    """把当前打开的书记入书库（元数据），顺便更新 last_opened_at。"""
    _lib = _load_library()
    _now_iso = datetime.now().isoformat(timespec="seconds")
    _title = book_key.rsplit(".", 1)[0] if "." in book_key else book_key
    # 清掉常见下载源后缀
    import re as _re_lib
    _title = _re_lib.sub(
        r"\s*[（(](?:Z[\-－]?Library|Anna'?s\s*Archive|libgen|annas[-_]archive)[)）]\s*",
        "",
        _title,
        flags=_re_lib.IGNORECASE,
    ).strip()
    _existing = _lib.get(book_key, {})
    _lib[book_key] = {
        "title": _existing.get("title") or _title,
        "chapter_count": int(chapter_count),
        "uploaded_at": _existing.get("uploaded_at") or _now_iso,
        "last_opened_at": _now_iso,
        "cover_color": _existing.get("cover_color") or _pick_cover_color(book_key),
    }
    _save_library(_lib)


def _load_daily_streak():
    """{last_date, current_streak, longest_streak, history: {YYYY-MM-DD: session_count}}。"""
    return _ls_read_dict(_LS_DAILYSTREAK_KEY)


def _record_daily_session(book_key):
    """当用户打开一本书时调用；每本书每天只记一次。更新 streak + history。"""
    import datetime as _dt_dse
    _data = _load_daily_streak()
    _today = _dt_dse.date.today().isoformat()
    _session_tag = f"{_today}:{book_key}"
    _history = _data.get("history", {})
    _last_session = _data.get("_last_session_tag")
    if _last_session == _session_tag:
        return  # 今天已经为这本书记过了
    # 增加今日会话计数
    _history[_today] = int(_history.get(_today, 0)) + 1
    _data["history"] = _history
    _data["_last_session_tag"] = _session_tag

    # 更新 streak
    _last_date_str = _data.get("last_date")
    if _last_date_str != _today:
        if _last_date_str:
            try:
                _prev = _dt_dse.date.fromisoformat(_last_date_str)
                _gap = (_dt_dse.date.today() - _prev).days
                if _gap == 1:
                    _data["current_streak"] = int(_data.get("current_streak", 0)) + 1
                elif _gap > 1:
                    _data["current_streak"] = 1
            except Exception:
                _data["current_streak"] = 1
        else:
            _data["current_streak"] = 1
        _data["last_date"] = _today
        _data["longest_streak"] = max(int(_data.get("longest_streak", 0)), int(_data["current_streak"]))
    _ls_write_dict(_LS_DAILYSTREAK_KEY, _data)


def _compute_reading_stats():
    """返回 dashboard 所需的四项数据 + 与上周 delta。"""
    import datetime as _dt_st
    _times = _load_reading_times()
    _total_sec = int(sum(int(v or 0) for v in _times.values()))
    _books_read = int(sum(1 for v in _times.values() if int(v or 0) >= 60))
    _streak_data = _load_daily_streak()
    _streak = int(_streak_data.get("current_streak", 0))

    # 与上周对比：用 history 里的日期计数
    _history = _streak_data.get("history", {})
    _today_date = _dt_st.date.today()
    _this_week_start = _today_date - _dt_st.timedelta(days=_today_date.weekday())
    _last_week_start = _this_week_start - _dt_st.timedelta(days=7)
    _this_week_days = sum(
        1 for k in _history
        if _this_week_start <= _dt_st.date.fromisoformat(k) <= _today_date
    )
    _last_week_days = sum(
        1 for k in _history
        if _last_week_start <= _dt_st.date.fromisoformat(k) < _this_week_start
    )
    _weekly_delta_days = _this_week_days - _last_week_days

    return {
        "total_hours": _total_sec // 3600,
        "total_minutes": (_total_sec % 3600) // 60,
        "total_seconds": _total_sec,
        "books_read": _books_read,
        "streak": _streak,
        "weekly_delta_days": _weekly_delta_days,
    }


def _build_export_markdown(book_name, messages, notes, bookmarks, chapter_titles):
    """把当前书的书签/笔记/AI 对话打包成一份 markdown 文本。"""
    from datetime import timezone, timedelta
    now_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    book_title = book_name.rsplit(".", 1)[0] if "." in book_name else book_name

    def _ch_title(idx):
        try:
            return chapter_titles[int(idx)]
        except (IndexError, ValueError, TypeError):
            return f"章节 {int(idx) + 1}"

    def _quote_block(text):
        return "\n".join("> " + line if line else ">" for line in text.split("\n"))

    lines = [
        f"# 《{book_title}》读书笔记",
        "",
        f"> 导出时间：{now_str}  ",
        f"> {len(bookmarks)} 条书签 · {len(notes)} 条笔记 · {len(messages)} 条 AI 对话",
        "",
        "---",
        "",
    ]

    if bookmarks:
        lines.append(f"## 📌 书签 ({len(bookmarks)})")
        lines.append("")
        for b in bookmarks:
            ch = _ch_title(b.get("chapter_idx", 0))
            pg = int(b.get("page", 0)) + 1
            ts = b.get("ts", "")
            ts_part = f" — *{ts}*" if ts else ""
            lines.append(f"- **{ch}** · 第 {pg} 页{ts_part}")
        lines.append("")

    if notes:
        lines.append(f"## ✏️ 笔记 ({len(notes)})")
        lines.append("")
        for i, n in enumerate(notes):
            ch = _ch_title(n.get("chapter_idx", 0))
            pg = int(n.get("page", 0)) + 1
            ts = n.get("ts", "")
            passage = (n.get("passage") or "").strip()
            note_text = (n.get("note") or "").strip()
            lines.append(f"### {ch} · 第 {pg} 页")
            if ts:
                lines.append(f"*{ts}*")
            lines.append("")
            if passage:
                lines.append(_quote_block(passage))
                lines.append("")
            if note_text:
                lines.append(f"**笔记：** {note_text}")
                lines.append("")
            if i < len(notes) - 1:
                lines.append("---")
                lines.append("")

    if messages:
        lines.append(f"## 💭 AI 对话 ({len(messages)})")
        lines.append("")
        for i, m in enumerate(messages):
            role_label = "🙋 我" if m.get("role") == "user" else "🤖 AI"
            content = (m.get("content") or "").strip()
            lines.append(f"**{role_label}：**")
            lines.append("")
            lines.append(content)
            lines.append("")
            if i < len(messages) - 1:
                lines.append("---")
                lines.append("")

    if not bookmarks and not notes and not messages:
        lines.append("*还没有任何书签、笔记或 AI 对话。去读几页试试吧。*")
        lines.append("")

    return "\n".join(lines)


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

        # 首次载入此书时，恢复上次的章节 + 页码 + 聊天记录
        if st.session_state.get("loaded_book") != book_key:
            saved = _load_progress().get(book_key, {})
            saved_ch = 0
            if saved:
                saved_ch = min(max(int(saved.get("chapter_idx", 0)), 0), len(chapters) - 1)
                st.session_state[f"page_{saved_ch}"] = int(saved.get("page", 0))
            st.session_state[sel_key] = saved_ch
            st.session_state.last_chapter = saved_ch
            # 聊天记录按书隔离：从 localStorage hydrate 这本书之前的对话
            st.session_state.messages = _load_all_messages().get(book_key, [])
            # 笔记按书隔离：hydrate 到 session_state
            st.session_state.notes = _load_all_notes().get(book_key, [])
            st.session_state.loaded_book = book_key
            # 阶段 7：入书库 + 每日会话记录（每切一本书只跑一次）
            _record_book_in_library(book_key, len(chapters))
            _record_daily_session(book_key)

        # 书签跳转：在 selectbox 渲染之前应用 pending 状态
        if "_pending_jump" in st.session_state:
            _jmp = st.session_state.pop("_pending_jump")
            _jch = int(_jmp.get("chapter", 0))
            _jch = min(max(_jch, 0), len(chapters) - 1)
            st.session_state[sel_key] = _jch
            st.session_state[f"page_{_jch}"] = int(_jmp.get("page", 0))
            st.session_state.last_chapter = _jch

        # 初始化已读章节集合（session 内追踪）
        if "read_chapters" not in st.session_state:
            st.session_state.read_chapters = set()
        _rc = st.session_state.read_chapters

        # 阶段 5：章节选择从 sidebar 迁到中央控制条的 📋 目录 popover。
        # 这里仅从 session_state 读当前 chapter_idx；popover 里的 selectbox 会写回同一个 key。
        _stored_ch = int(st.session_state.get(sel_key, 0))
        chapter_idx = min(max(_stored_ch, 0), len(chapters) - 1)
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

        # 阶段 5：页码跳转从 sidebar 迁到中央控制条的页码按钮 popover。
        # 此处只保留兜底校验：防止越界。
        if current_page >= total_pages:
            st.session_state[page_key] = max(0, total_pages - 1)
            current_page = st.session_state[page_key]
            st.rerun()

        # 阶段 4：书签迁移到顶部状态条 🔖 按钮（加入）。
        # 书签列表 UI 按用户决定暂不展示（设计图没有），代码保留（_add_bookmark / _load_bookmarks）供阶段 10 的"摘录与笔记"子页调用。

        # --- 侧边栏：笔记 ---
        st.sidebar.divider()
        st.sidebar.markdown(
            f'<strong class="sbh">{PX_ICON["save"]}笔记</strong>',
            unsafe_allow_html=True,
        )
        _all_notes = st.session_state.get("notes", [])
        if not _all_notes:
            st.sidebar.caption("还没有笔记")
        else:
            for _n in _all_notes:
                _nch = int(_n.get("chapter_idx", 0))
                _npg = int(_n.get("page", 0))
                _nts = _n.get("ts", "")
                _nch_title = chapter_titles[_nch] if 0 <= _nch < len(chapter_titles) else f"章节 {_nch+1}"
                _nshort = _nch_title if len(_nch_title) <= 8 else _nch_title[:8] + "…"
                _passage_preview = _n.get("passage", "")
                _passage_preview = _passage_preview[:20] + "…" if len(_passage_preview) > 20 else _passage_preview
                _note_preview = _n.get("note", "")
                _note_preview = _note_preview[:18] + "…" if len(_note_preview) > 18 else _note_preview
                _nc1, _nc2 = st.sidebar.columns([6, 1])
                with _nc1:
                    _btn_label = f"{_nshort} · 第{_npg+1}页"
                    if _passage_preview:
                        _btn_label += f"\n「{_passage_preview}」"
                    if st.button(_btn_label, key=f"note_go_{_n['id']}", use_container_width=True):
                        st.session_state._pending_jump = {"chapter": _nch, "page": _npg}
                        st.rerun()
                with _nc2:
                    if st.button("✕", key=f"note_del_{_n['id']}", help="删除此笔记"):
                        _remove_note(book_key, _n["id"])
                        st.session_state.notes = [x for x in st.session_state.get("notes", []) if x.get("id") != _n["id"]]
                        st.rerun()

        # --- 侧边栏：导出 ---
        st.sidebar.divider()
        st.sidebar.markdown(
            f'<strong class="sbh">{PX_ICON["download"]}导出</strong>',
            unsafe_allow_html=True,
        )
        _export_bookmarks = _load_bookmarks().get(book_key, [])
        _export_notes = st.session_state.get("notes", [])
        _export_messages = st.session_state.get("messages", [])
        _export_md = _build_export_markdown(
            st.session_state.file_name,
            _export_messages,
            _export_notes,
            _export_bookmarks,
            chapter_titles,
        )
        _safe_stem = (
            st.session_state.file_name.rsplit(".", 1)[0]
            .replace("/", "_").replace("\\", "_").replace(":", "_")
        )
        _export_date = datetime.now().strftime("%Y%m%d")
        _export_filename = f"{_safe_stem}_读书笔记_{_export_date}.md"
        st.sidebar.download_button(
            label="下载 Markdown",
            data=_export_md.encode("utf-8"),
            file_name=_export_filename,
            mime="text/markdown",
            use_container_width=True,
            key="export_md_btn",
        )
        _total = len(_export_bookmarks) + len(_export_notes) + len(_export_messages)
        if _total == 0:
            st.sidebar.caption("还没有书签/笔记/对话")
        else:
            st.sidebar.caption(
                f"📌 {len(_export_bookmarks)} · ✏️ {len(_export_notes)} · 💭 {len(_export_messages)}"
            )

        # ============================================================
        # --- 阅读界面（阶段 4：顶部状态条 + 三列骨架）---
        # ============================================================
        # 计算 topbar 需要的信息
        _tb_progress_pct = int(((current_page + 1) / total_pages if total_pages > 0 else 1) * 100)
        _tb_chapter_title = chapter_titles[chapter_idx] if 0 <= chapter_idx < len(chapter_titles) else ""
        _tb_book_title = (
            st.session_state.file_name.rsplit(".", 1)[0]
            if "." in st.session_state.file_name
            else st.session_state.file_name
        )
        # 清理常见后缀（Z-Library / Anna's Archive 等下载源标签）
        import re as _re_clean
        _tb_book_title = _re_clean.sub(
            r"\s*[（(](?:Z[\-－]?Library|Anna'?s\s*Archive|libgen|annas[-_]archive)[)）]\s*",
            "",
            _tb_book_title,
            flags=_re_clean.IGNORECASE,
        ).strip()

        # 顶部状态条：info(左) + 5 popover/button(右)
        _tb_info, _tb_search, _tb_theme, _tb_font, _tb_bm, _tb_avatar = st.columns(
            [60, 8, 8, 8, 8, 8], gap="small"
        )
        with _tb_info:
            st.markdown(
                f'''<div class="mc-topbar-info">
                    <span class="mc-topbar-book-icon">{PX_ICON["read"]}</span>
                    <span class="mc-topbar-title">《{html.escape(_tb_book_title)}》</span>
                    <span class="mc-topbar-sep">·</span>
                    <span class="mc-topbar-chapter">{html.escape(_tb_chapter_title)}</span>
                    <div class="mc-topbar-progress">
                        <span class="mc-topbar-progress-label">{_tb_progress_pct}%</span>
                        <div class="mc-topbar-progress-bar">
                            <div class="mc-topbar-progress-fill" style="width:{_tb_progress_pct}%"></div>
                        </div>
                    </div>
                </div>''',
                unsafe_allow_html=True,
            )
        with _tb_search:
            with st.popover("🔍", use_container_width=True, help="全书搜索（阶段 10 实装）", key="tb_search"):
                st.markdown("**🔍 全书搜索**")
                st.info("🚧 搜索功能开发中，阶段 10 上线。")
        with _tb_theme:
            with st.popover("☀", use_container_width=True, help="配色主题", key="tb_theme"):
                st.markdown("**☀ 配色主题**")
                _tb_theme_keys = list(READING_THEMES.keys())
                _tb_theme_pick = st.radio(
                    "主题",
                    _tb_theme_keys,
                    index=_tb_theme_keys.index(st.session_state.get("reading_theme", "奶油"))
                    if st.session_state.get("reading_theme", "奶油") in _tb_theme_keys else 0,
                    key="tb_theme_radio",
                    label_visibility="collapsed",
                )
                if _tb_theme_pick != st.session_state.get("reading_theme"):
                    st.session_state.reading_theme = _tb_theme_pick
                    st.rerun()
        with _tb_font:
            with st.popover("Aa", use_container_width=True, help="字号与字体", key="tb_font"):
                st.markdown("**Aa 字号与字体**")
                _tb_fs = st.slider(
                    "字号",
                    14, 28, st.session_state.get("font_size", 18), step=2,
                    key="tb_fs_slider",
                )
                if _tb_fs != st.session_state.get("font_size", 18):
                    st.session_state.font_size = _tb_fs
                    st.rerun()
                _tb_font_keys = list({
                    "默认": 'system-ui, -apple-system, "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif',
                    "宋体": '"Source Han Serif SC", "Noto Serif SC", "Songti SC", "SimSun", "PingFang SC", serif',
                    "楷体": '"Kaiti SC", "STKaiti", "KaiTi", "BiauKai", serif',
                    "仿宋": '"FangSong", "STFangsong", "FangSong_GB2312", "Noto Serif SC", serif',
                    "黑体": '"Source Han Sans SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
                    "隶书": '"LiSu", "STLiti", "Noto Serif SC", serif',
                    "圆体": '"Yuanti SC", "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif',
                }.keys())
                _tb_ff = st.selectbox(
                    "字体",
                    _tb_font_keys,
                    index=_tb_font_keys.index(st.session_state.get("font_family_name", "默认"))
                    if st.session_state.get("font_family_name", "默认") in _tb_font_keys else 0,
                    key="tb_ff_select",
                )
                if _tb_ff != st.session_state.get("font_family_name", "默认"):
                    st.session_state.font_family_name = _tb_ff
                    st.rerun()
        with _tb_bm:
            if st.button("🔖", key="tb_bm_add", help="加入当前位置为书签", use_container_width=True):
                _tb_added = _add_bookmark(book_key, chapter_idx, current_page)
                st.toast("[+] 已添加书签" if _tb_added else "此位置已有书签")
                st.rerun()
        with _tb_avatar:
            with st.popover("👤", use_container_width=True, help="账号与偏好", key="tb_avatar"):
                st.markdown("**👤 我**")
                st.caption("当前书库：本地浏览器")
                if st.button(
                    ("▶ 进入专注模式" if not st.session_state.get("focus_mode") else "✕ 退出专注"),
                    key="tb_focus_toggle",
                    use_container_width=True,
                ):
                    st.session_state.focus_mode = not st.session_state.get("focus_mode", False)
                    st.rerun()
        # 当前激活的左侧导航项（默认 reading）
        if "_active_nav" not in st.session_state:
            st.session_state._active_nav = "reading"
        _active_nav = st.session_state._active_nav

        _mc_nav, _mc_center, _mc_right = st.columns([16, 56, 28], gap="small")
        with _mc_nav:
            # 品牌区：嘟哒 Logo + 副标 + 读书角色 + 小花盆
            st.markdown("""
            <div class="mc-nav-brand">
                <h1 class="mc-nav-brand-title">嘟哒</h1>
                <p class="mc-nav-brand-subtitle">我的阅读伙伴</p>
                <div class="mc-nav-brand-figure" aria-hidden="true">
                    <svg width="44" height="44" viewBox="0 0 22 22">
                        <rect x="5" y="1" width="12" height="6" fill="#4A2D1A"/>
                        <rect x="6" y="3" width="10" height="6" fill="#E5C9A3"/>
                        <rect x="5" y="7" width="2" height="2" fill="#4A2D1A"/>
                        <rect x="15" y="7" width="2" height="2" fill="#4A2D1A"/>
                        <rect x="8" y="5" width="2" height="1" fill="#2E1D12"/>
                        <rect x="12" y="5" width="2" height="1" fill="#2E1D12"/>
                        <rect x="7" y="7" width="1" height="1" fill="#E8A08F"/>
                        <rect x="14" y="7" width="1" height="1" fill="#E8A08F"/>
                        <rect x="10" y="7" width="2" height="1" fill="#B96A4A"/>
                        <rect x="9" y="9" width="4" height="1" fill="#E5C9A3"/>
                        <rect x="5" y="10" width="12" height="7" fill="#6E8B5B"/>
                        <rect x="3" y="11" width="2" height="5" fill="#6E8B5B"/>
                        <rect x="17" y="11" width="2" height="5" fill="#6E8B5B"/>
                        <rect x="4" y="14" width="2" height="2" fill="#E5C9A3"/>
                        <rect x="16" y="14" width="2" height="2" fill="#E5C9A3"/>
                        <rect x="6" y="14" width="10" height="4" fill="#B96A4A"/>
                        <rect x="7" y="15" width="8" height="2" fill="#F6E7C8"/>
                        <rect x="2" y="19" width="18" height="3" fill="#8B5E3C"/>
                        <rect x="1" y="20" width="20" height="2" fill="#6B4024"/>
                    </svg>
                    <svg width="28" height="36" viewBox="0 0 14 18">
                        <rect x="5" y="1" width="4" height="1" fill="#D7A441"/>
                        <rect x="4" y="2" width="6" height="2" fill="#D7A441"/>
                        <rect x="5" y="4" width="4" height="1" fill="#D7A441"/>
                        <rect x="6" y="2" width="2" height="2" fill="#B96A4A"/>
                        <rect x="6" y="5" width="2" height="6" fill="#6E8B5B"/>
                        <rect x="3" y="8" width="3" height="1" fill="#6E8B5B"/>
                        <rect x="8" y="9" width="3" height="1" fill="#6E8B5B"/>
                        <rect x="2" y="11" width="10" height="1" fill="#D7A441"/>
                        <rect x="2" y="12" width="10" height="4" fill="#B96A4A"/>
                        <rect x="3" y="16" width="8" height="1" fill="#8B3F2A"/>
                    </svg>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 7 菜单项：点击 → 切 _active_nav → rerun
            for _nav_key, _nav_label, _nav_emoji in NAV_ITEMS:
                if st.button(
                    f"{_nav_emoji}  {_nav_label}",
                    key=f"nav_{_nav_key}",
                    use_container_width=True,
                ):
                    st.session_state._active_nav = _nav_key
                    st.rerun()

            # 底部装饰：像素台灯 + 小书堆（阶段 8 会再精细化）
            st.markdown("""
            <div class="mc-nav-decor" aria-hidden="true">
                <svg width="40" height="48" viewBox="0 0 16 20">
                    <rect x="2" y="2" width="12" height="2" fill="#2E1D12"/>
                    <rect x="3" y="4" width="10" height="4" fill="#D7A441"/>
                    <rect x="4" y="5" width="8" height="2" fill="#F2C66D"/>
                    <rect x="7" y="8" width="2" height="8" fill="#6B4024"/>
                    <rect x="4" y="16" width="8" height="2" fill="#3B2416"/>
                </svg>
                <svg width="40" height="22" viewBox="0 0 16 10" style="margin-top:8px">
                    <rect x="2" y="3" width="12" height="2" fill="#6E8B5B"/>
                    <rect x="1" y="5" width="14" height="2" fill="#B96A4A"/>
                    <rect x="2" y="7" width="12" height="1" fill="#8B3F2A"/>
                </svg>
            </div>
            """, unsafe_allow_html=True)

            # 动态注入：当前激活菜单的高亮样式
            st.markdown(f"""
            <style>
            .st-key-nav_{_active_nav} button {{
                background: var(--mc-wood-light) !important;
                border-left-color: var(--mc-mustard) !important;
                font-weight: 700 !important;
            }}
            .st-key-nav_{_active_nav} button p {{
                font-weight: 700 !important;
            }}
            </style>
            """, unsafe_allow_html=True)
        with _mc_center:

            # 当用户切到非"正在阅读"的导航项时给个提示（视图切换留给阶段 10）
            if _active_nav != "reading":
                _nav_label_now = NAV_LABELS.get(_active_nav, _active_nav)
                st.warning(
                    f"🚧 「{_nav_label_now}」功能即将上线。当前视图仍为「正在阅读」。"
                    "点左栏「正在阅读」即可回到这里。"
                )

            # 专注模式：flag + 浮动退出按钮（CSS 会把它固定到右上角）
            if "focus_mode" not in st.session_state:
                st.session_state.focus_mode = False
            if st.session_state.focus_mode:
                st.markdown('<div class="rd-focus-flag"></div>', unsafe_allow_html=True)
                if st.button("✕ 退出专注", key="rd_focus_exit"):
                    st.session_state.focus_mode = False
                    st.rerun()
    
            # 阶段 5：旧 rd-topbar 被新的顶部状态条取代（阶段 4），此处不再渲染。
            from datetime import timezone, timedelta  # noqa: F401 — 其他逻辑仍需要
    
            # 阅读时长追踪：用 data-key 给 JS 传递 book_key
            st.markdown(
                f'<div class="rd-book-key" data-key="{html.escape(book_key)}" style="display:none"></div>',
                unsafe_allow_html=True,
            )
    
            # 进度条
            progress = (current_page + 1) / total_pages if total_pages > 0 else 1
            st.markdown(f"""
            <div class="progress-container">
                <div class="progress-fill" style="width: {progress * 100:.1f}%"></div>
            </div>
            """, unsafe_allow_html=True)
    
            # 像素风主题：根据用户选择的配色
            fs = st.session_state.get("font_size", 18)
            _rt = READING_THEMES.get(st.session_state.get("reading_theme", "奶油"), READING_THEMES["奶油"])
            theme_css = f"background: {_rt['bg']}; color: {_rt['fg']};"
            # 字体族（基于 session_state，默认系统字体）
            # 用单引号包裹字体名，以便安全嵌入 style="..." 属性
            _font_stacks = {
                "默认": "system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', sans-serif",
                "宋体": "'Source Han Serif SC', 'Noto Serif SC', 'Songti SC', 'SimSun', 'PingFang SC', serif",
                "楷体": "'Kaiti SC', 'STKaiti', 'KaiTi', 'BiauKai', serif",
                "仿宋": "'FangSong', 'STFangsong', 'FangSong_GB2312', 'Noto Serif SC', serif",
                "黑体": "'Source Han Sans SC', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif",
                "隶书": "'LiSu', 'STLiti', 'Noto Serif SC', serif",
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
    
            # 章节已读标记：到达最后一页时加入集合
            if next_disabled:
                st.session_state.read_chapters.add((book_key, chapter_idx))
    
            # 章末庆祝：4 个像素烟花爆炸点 + 中央横幅
            # 每个爆炸点：8 方向粒子 + 中心闪光，错开触发时间
            _FW_BURSTS = [
                {"left": "18%", "top": "44vh", "bd": "0.0s",  "sz": "7px",
                 "colors": ["var(--mc-terra)", "var(--mc-mustard)", "var(--mc-terra)", "var(--mc-cream)", "var(--mc-terra)", "var(--mc-mustard)", "var(--mc-terra)", "var(--mc-cream)"]},
                {"left": "40%", "top": "32vh", "bd": "0.45s", "sz": "9px",
                 "colors": ["var(--mc-mustard)", "var(--mc-dusty)", "var(--mc-mustard)", "var(--mc-cream)", "var(--mc-mustard)", "var(--mc-dusty)", "var(--mc-mustard)", "var(--mc-cream)"]},
                {"left": "62%", "top": "38vh", "bd": "0.25s", "sz": "8px",
                 "colors": ["var(--mc-moss)", "var(--mc-terra)", "var(--mc-moss)", "var(--mc-cream)", "var(--mc-moss)", "var(--mc-terra)", "var(--mc-moss)", "var(--mc-cream)"]},
                {"left": "82%", "top": "44vh", "bd": "0.7s",  "sz": "7px",
                 "colors": ["var(--mc-dusty)", "var(--mc-moss)", "var(--mc-dusty)", "var(--mc-cream)", "var(--mc-dusty)", "var(--mc-moss)", "var(--mc-dusty)", "var(--mc-cream)"]},
            ]
            # 8 方向 (dx, dy) 单位 px
            _FW_DIRS = [(0,-65),(46,-46),(65,0),(46,46),(0,65),(-46,46),(-65,0),(-46,-46)]
            _celebrate_html = ""
            if next_disabled:
                _bursts_html = ""
                for _b in _FW_BURSTS:
                    _particles = "".join(
                        f'<div class="rb-fw-p" style="background:{_b["colors"][_i]};--dx:{_dx}px;--dy:{_dy}px;--sz:{_b["sz"]};--bd:{_b["bd"]}"></div>'
                        for _i, (_dx, _dy) in enumerate(_FW_DIRS)
                    )
                    _flash = f'<div class="rb-fw-flash" style="--bd:{_b["bd"]}"></div>'
                    _bursts_html += f'<div class="rb-firework" style="left:{_b["left"]};top:{_b["top"]}">{_flash}{_particles}</div>'
                _celebrate_html = _bursts_html + '<div class="rb-banner">★ 本章读完 ★</div>'
    
            # 阶段 5：book-spread 外套 mc-reader-frame；page-indicator/nav-row 迁到下方控制条
            reading_html = f'''
            <div class="reading-area">
                <div class="mc-reader-frame">
                    <div class="book-spread" data-page="{current_page}" style="{theme_css} font-size: {fs}px; font-family: {ff_css};">
                        <div class="book-page book-page-left">
                            {left_html}
                            <div class="page-num">{left_num}</div>
                        </div>
                        <div class="book-page book-page-right">
                            {right_html}
                            <div class="page-num">{right_num}</div>
                        </div>
                    </div>
                </div>
                {_celebrate_html}
            </div>
            '''
            st.markdown(reading_html, unsafe_allow_html=True)
    
            # 持久化阅读进度
            _save_progress(book_key, chapter_idx, current_page)
    
            # --- 笔记：当前页提示 + 添加入口 ---
            _page_notes = [
                n for n in st.session_state.get("notes", [])
                if int(n.get("chapter_idx", -1)) == chapter_idx
                and int(n.get("page", -1)) == current_page
            ]
            if _page_notes:
                for _pn in _page_notes:
                    _pn_passage = _pn.get("passage", "")
                    _pn_note = _pn.get("note", "")
                    _pn_ts = _pn.get("ts", "")
                    _note_md = f"**{_pn_ts}**　"
                    if _pn_passage:
                        _note_md += f"「{_pn_passage}」  \n"
                    if _pn_note:
                        _note_md += _pn_note
                    st.info(_note_md)
    
            # 阶段 5：6 按钮控制条（替代 HTML nav-row + page-indicator + 旧 expander）
            _ctrl_prev, _ctrl_page, _ctrl_next, _ctrl_bm, _ctrl_note, _ctrl_toc = st.columns(
                [2, 2, 2, 1.2, 1.2, 1.6], gap="small"
            )
            with _ctrl_prev:
                if st.button(
                    "← 上一页",
                    key="rd_prev",
                    disabled=prev_disabled,
                    use_container_width=True,
                ):
                    st.session_state[page_key] = max(0, current_page - 2)
                    st.rerun()

            with _ctrl_page:
                _pg_label = f"{left_num}" + (f"-{right_num}" if right_num else "") + f" / {total_pages}"
                with st.popover(_pg_label, use_container_width=True, help="跳转页码 / 进度", key="rd_page"):
                    st.markdown(f"**📄 本章 · 第 {_pg_label}**")
                    st.caption(f"全书 {overall:.1f}% · {_time_left}")
                    _rd_jp = st.number_input(
                        "跳到第几页",
                        min_value=1,
                        max_value=total_pages,
                        value=current_page + 1,
                        step=1,
                        key=f"rd_ctrl_jumpto_{chapter_idx}",
                    )
                    if st.button("跳转", key=f"rd_ctrl_jump_btn_{chapter_idx}", use_container_width=True):
                        if _rd_jp - 1 != current_page:
                            st.session_state[page_key] = _rd_jp - 1
                            st.rerun()

            with _ctrl_next:
                if st.button(
                    "下一页 →",
                    key="rd_next",
                    disabled=next_disabled,
                    use_container_width=True,
                ):
                    st.session_state[page_key] = min(total_pages - 1, current_page + 2)
                    st.rerun()

            with _ctrl_bm:
                if st.button("🔖", key="rd_bm", help="加入当前位置为书签", use_container_width=True):
                    _added_bm = _add_bookmark(book_key, chapter_idx, current_page)
                    st.toast("[+] 已添加书签" if _added_bm else "此位置已有书签")
                    st.rerun()

            with _ctrl_note:
                _nf_ver = st.session_state.get("_note_form_ver", 0)
                with st.popover("✏", use_container_width=True, help="添加摘录/笔记", key="rd_note"):
                    st.markdown("**✏️ 添加摘录 / 笔记**")
                    _passage_in = st.text_area(
                        "摘录片段（可选）",
                        placeholder="粘贴你想记录的原文片段……",
                        key=f"note_passage_{chapter_idx}_{current_page}_{_nf_ver}",
                        height=80,
                    )
                    _note_in = st.text_area(
                        "你的想法",
                        placeholder="写下你的感想、疑问或联想……",
                        key=f"note_text_{chapter_idx}_{current_page}_{_nf_ver}",
                        height=80,
                    )
                    if st.button(
                        "保存笔记",
                        key=f"note_save_{chapter_idx}_{current_page}_{_nf_ver}",
                        use_container_width=True,
                    ):
                        if _note_in.strip() or _passage_in.strip():
                            import uuid as _uuid
                            _new_note = {
                                "id": str(_uuid.uuid4())[:8],
                                "chapter_idx": int(chapter_idx),
                                "page": int(current_page),
                                "passage": _passage_in.strip(),
                                "note": _note_in.strip(),
                                "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M"),
                            }
                            _cur_notes = list(st.session_state.get("notes", []))
                            _cur_notes.append(_new_note)
                            st.session_state.notes = _cur_notes
                            _save_book_notes(book_key, _cur_notes)
                            st.session_state._note_form_ver = _nf_ver + 1
                            st.toast("[+] 笔记已保存")
                            st.rerun()
                        else:
                            st.warning("请至少填写摘录或想法其中一项。")

            with _ctrl_toc:
                with st.popover("📋 目录", use_container_width=True, help="章节目录", key="rd_toc"):
                    st.markdown("**📋 章节目录**")
                    st.selectbox(
                        "选择章节",
                        range(len(chapters)),
                        format_func=lambda x: ("✓ " if (book_key, x) in _rc else "　") + chapter_titles[x],
                        key=sel_key,
                        label_visibility="collapsed",
                    )
    
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
                  body { margin: 0; background: var(--mc-paper); }
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
                    background: var(--mc-cream);
                    border: 2px solid var(--mc-ink);
                    color: var(--mc-ink);
                    font-size: 11px;
                    font-family: 'Press Start 2P', 'Zpix', monospace;
                    letter-spacing: 1px;
                    user-select: none;
                    box-shadow: 3px 3px 0 var(--mc-mustard);
                  }
                  .rb-kbd-hint kbd {
                    display: inline-block;
                    min-width: 18px;
                    padding: 1px 6px;
                    border: 1.5px solid var(--mc-ink);
                    border-radius: 0;
                    background: #e8dcbc;
                    color: var(--mc-ink);
                    font-size: 11px;
                    font-family: 'Press Start 2P', monospace;
                    line-height: 1.4;
                    text-align: center;
                    box-shadow: 1px 1px 0 var(--mc-ink);
                  }
                  .rb-kbd-hint.rb-err {
                    background: var(--mc-cream);
                    border-color: var(--mc-terra);
                    color: var(--mc-terra);
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
                        // 阶段 5：控制条的 st.button (rd_prev / rd_next) 直接接管翻页。
                        function getNavBtn(action) {
                            const sel = action === 'prev'
                                ? '.st-key-rd_prev button'
                                : '.st-key-rd_next button';
                            return p.document.querySelector(sel);
                        }
                        function flipAndNavigate(action) {
                            const btn = getNavBtn(action);
                            if (!btn || btn.disabled) return;
                            const spread = p.document.querySelector('.book-spread');
                            if (spread) {
                                spread.style.opacity = '0';
                                spread.style.transform = 'perspective(900px) rotateY(-5deg) scaleX(0.98)';
                            }
                            btn.click();
                        }
                        function handler(e) {
                            if (e.ctrlKey || e.metaKey || e.altKey) return;
                            if (isTextEditing(e.target)) return;
                            let action = null;
                            if (e.key === 'ArrowLeft') action = 'prev';
                            else if (e.key === 'ArrowRight') action = 'next';
                            if (!action) return;
                            const btn = getNavBtn(action);
                            if (!btn || btn.disabled) return;
                            e.preventDefault();
                            try { if (e.target && e.target.blur) e.target.blur(); } catch (_) {}
                            flipAndNavigate(action);
                        }
                        p._rb_kbd_handler = handler;
                        p.document.addEventListener('keydown', handler, true);
                        p.addEventListener('keydown', handler, true);
    
                        // ── MutationObserver: 监听 data-page 变化，重启 flip-in 动画 ──
                        let _animLastPage = null;
                        function triggerFlipIn() {
                            const spread = p.document.querySelector('.book-spread');
                            if (!spread) return;
                            const pg = spread.getAttribute('data-page');
                            if (pg === _animLastPage) return;
                            _animLastPage = pg;
                            spread.classList.remove('rb-anim-in');
                            void spread.offsetWidth; // force reflow to reset animation
                            spread.classList.add('rb-anim-in');
                        }
                        if (p._rb_mo) { try { p._rb_mo.disconnect(); } catch(_) {} }
                        const _moRoot = p.document.querySelector('.reading-area') || p.document.body;
                        const _mo = new MutationObserver(triggerFlipIn);
                        _mo.observe(_moRoot, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-page'] });
                        p._rb_mo = _mo;
                        triggerFlipIn(); // 首次挂载时立刻播放
    
                        // ── 移动端 swipe 翻页 ──
                        if (p._rb_touch_start) {
                            try { p.document.removeEventListener('touchstart', p._rb_touch_start); } catch(_) {}
                            try { p.document.removeEventListener('touchend',   p._rb_touch_end);   } catch(_) {}
                        }
                        let _tx0 = null, _ty0 = null;
                        p._rb_touch_start = function(e) {
                            _tx0 = e.touches[0].clientX;
                            _ty0 = e.touches[0].clientY;
                        };
                        p._rb_touch_end = function(e) {
                            if (_tx0 === null) return;
                            const dx = e.changedTouches[0].clientX - _tx0;
                            const dy = e.changedTouches[0].clientY - _ty0;
                            _tx0 = null; _ty0 = null;
                            // 水平滑动幅度 > 50px，且水平分量 > 垂直（防止上下滚动误触）
                            if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy)) return;
                            const action = dx < 0 ? 'next' : 'prev';
                            flipAndNavigate(action);
                        };
                        p.document.addEventListener('touchstart', p._rb_touch_start, { passive: true });
                        p.document.addEventListener('touchend',   p._rb_touch_end,   { passive: true });
    
                        setMsg('⌨ 键盘翻页已启用（← / →）', '#4caf50');
                        // Shake hint pill once per session
                        if (!sessionStorage.getItem('rb_hint_shaken')) {
                            setTimeout(function() {
                                s.classList.add('rb-shake');
                                s.addEventListener('animationend', function() {
                                    s.classList.remove('rb-shake');
                                }, { once: true });
                                sessionStorage.setItem('rb_hint_shaken', '1');
                            }, 600);
                        }
                    } catch (err) {
                        setMsg('⌨ 键盘翻页不可用: ' + (err && err.message || err), '#f44336');
                    }
                })();
                </script>
                """,
                height=36,
            )
    
            # 双击词语查词典：悬浮小窗（萌典 API 优先 + 百度回退）
            components.html("""
            <script>
            (function() {
                const p = window.parent;
                const pd = p.document;
                const STYLE_CONTENT = `
                    #rb-dict-overlay {
                        position: fixed;
                        display: none;
                        z-index: 99999;
                        background: var(--mc-cream);
                        border: 2px solid var(--mc-ink);
                        box-shadow: 4px 4px 0 var(--mc-terra);
                        padding: 14px 16px 14px 14px;
                        font-family: 'Zpix', 'Microsoft YaHei', monospace;
                        font-size: 13px;
                        color: var(--mc-ink);
                        width: 280px;
                        max-height: 360px;
                        overflow-y: auto;
                        line-height: 1.65;
                    }
                    #rb-dict-overlay .rb-dict-title {
                        font-family: 'Press Start 2P', monospace;
                        font-size: 12px;
                        color: var(--mc-terra);
                        margin: 0 0 6px 0;
                        padding-right: 18px;
                        letter-spacing: 1px;
                    }
                    #rb-dict-overlay .rb-dict-close {
                        position: absolute;
                        top: 6px; right: 8px;
                        background: none; border: none;
                        color: var(--mc-ink);
                        font-size: 18px;
                        cursor: pointer;
                        font-family: 'Press Start 2P', monospace;
                        line-height: 1;
                        padding: 2px 6px;
                    }
                    #rb-dict-overlay .rb-dict-close:hover { color: var(--mc-terra); }
                    #rb-dict-overlay .rb-dict-pinyin {
                        color: var(--mc-moss);
                        font-size: 11px;
                        margin: 4px 0;
                        font-style: italic;
                    }
                    #rb-dict-overlay .rb-dict-def { margin: 5px 0; }
                    #rb-dict-overlay .rb-dict-link {
                        display: inline-block;
                        margin-top: 10px;
                        color: var(--mc-terra);
                        text-decoration: none;
                        font-size: 11px;
                        border-bottom: 1px dashed var(--mc-terra);
                        padding-bottom: 1px;
                    }
                    #rb-dict-overlay .rb-dict-link:hover { background: #fff2d8; }
                    #rb-dict-overlay .rb-dict-loading { color: #8b5e3c; font-style: italic; }
                `;
    
                function escapeHtml(s) {
                    return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
                }
                function ensureStyles() {
                    if (pd.getElementById('rb-dict-overlay-style')) return;
                    const s = pd.createElement('style');
                    s.id = 'rb-dict-overlay-style';
                    s.textContent = STYLE_CONTENT;
                    pd.head.appendChild(s);
                }
                function ensureOverlay() {
                    let ov = pd.getElementById('rb-dict-overlay');
                    if (ov) return ov;
                    ensureStyles();
                    ov = pd.createElement('div');
                    ov.id = 'rb-dict-overlay';
                    pd.body.appendChild(ov);
                    return ov;
                }
                function closeOverlay() {
                    const ov = pd.getElementById('rb-dict-overlay');
                    if (ov) ov.style.display = 'none';
                }
                function positionOverlay(ov, x, y) {
                    const vw = p.innerWidth;
                    const vh = p.innerHeight;
                    const ow = 300;
                    const oh = 240;
                    let left = x + 12;
                    let top = y + 16;
                    if (left + ow > vw - 10) left = vw - ow - 10;
                    if (top + oh > vh - 10) top = y - oh - 10;
                    if (top < 10) top = 10;
                    ov.style.left = Math.max(10, left) + 'px';
                    ov.style.top = top + 'px';
                }
                async function showDefinition(word, x, y) {
                    const ov = ensureOverlay();
                    positionOverlay(ov, x, y);
                    const baiduUrl = 'https://dict.baidu.com/s?wd=' + encodeURIComponent(word);
                    ov.innerHTML = `
                        <button class="rb-dict-close" aria-label="关闭">×</button>
                        <div class="rb-dict-title">「${escapeHtml(word)}」</div>
                        <div class="rb-dict-loading">查询中…</div>
                    `;
                    ov.style.display = 'block';
                    ov.querySelector('.rb-dict-close').onclick = closeOverlay;
    
                    const hasCJK = /[\\u4e00-\\u9fff]/.test(word);
                    if (!hasCJK) {
                        renderNotFound(ov, word, baiduUrl, '外部词典可能有释义');
                        return;
                    }
                    try {
                        const res = await fetch('https://www.moedict.tw/uni/' + encodeURIComponent(word) + '.json');
                        if (!res.ok) { renderNotFound(ov, word, baiduUrl); return; }
                        const data = await res.json();
                        renderDefinition(ov, word, data, baiduUrl);
                    } catch (err) {
                        renderNotFound(ov, word, baiduUrl);
                    }
                }
                function renderDefinition(ov, word, data, baiduUrl) {
                    if (!data || !data.heteronyms || !data.heteronyms.length) {
                        renderNotFound(ov, word, baiduUrl);
                        return;
                    }
                    let html = `<button class="rb-dict-close" aria-label="关闭">×</button>
                                <div class="rb-dict-title">「${escapeHtml(word)}」</div>`;
                    let hasDef = false;
                    data.heteronyms.slice(0, 3).forEach(h => {
                        if (h.pinyin) html += `<div class="rb-dict-pinyin">${escapeHtml(h.pinyin)}</div>`;
                        if (h.definitions) {
                            h.definitions.slice(0, 4).forEach((d, i) => {
                                const defText = (d.def || '').trim();
                                if (!defText) return;
                                html += `<div class="rb-dict-def">${i + 1}. ${escapeHtml(defText)}</div>`;
                                hasDef = true;
                            });
                        }
                    });
                    if (!hasDef) { renderNotFound(ov, word, baiduUrl); return; }
                    html += `<a class="rb-dict-link" href="${baiduUrl}" target="_blank" rel="noopener">查百度词典 →</a>`;
                    ov.innerHTML = html;
                    ov.querySelector('.rb-dict-close').onclick = closeOverlay;
                }
                function renderNotFound(ov, word, baiduUrl, hint) {
                    ov.innerHTML = `
                        <button class="rb-dict-close" aria-label="关闭">×</button>
                        <div class="rb-dict-title">「${escapeHtml(word)}」</div>
                        <div class="rb-dict-def">${hint || '萌典未收录此词。'}</div>
                        <a class="rb-dict-link" href="${baiduUrl}" target="_blank" rel="noopener">查百度词典 →</a>
                    `;
                    ov.querySelector('.rb-dict-close').onclick = closeOverlay;
                }
                function attach() {
                    if (pd._rb_dict_bound) return;
                    pd._rb_dict_bound = true;
                    pd.addEventListener('dblclick', function(e) {
                        const inRead = e.target && e.target.closest && e.target.closest('.book-page');
                        if (!inRead) return;
                        const selObj = p.getSelection ? p.getSelection() : null;
                        const sel = (selObj && selObj.toString() || '').trim();
                        if (!sel || sel.length > 15) return;
                        showDefinition(sel, e.clientX, e.clientY);
                    });
                    pd.addEventListener('mousedown', function(e) {
                        const ov = pd.getElementById('rb-dict-overlay');
                        if (!ov || ov.style.display === 'none') return;
                        if (!ov.contains(e.target)) closeOverlay();
                    });
                    pd.addEventListener('keydown', function(e) {
                        if (e.key === 'Escape') closeOverlay();
                    });
                }
                function boot() {
                    if (!pd || !pd.body) { setTimeout(boot, 200); return; }
                    ensureOverlay();
                    attach();
                }
                boot();
            })();
            </script>
            """, height=0)
    
            # 选中文本 → 浮动"📷 分享"按钮 → 生成像素风引用卡片 PNG
            components.html("""
            <script>
            (function() {
                const p = window.parent;
                const pd = p.document;
                const STYLE = `
                    #rb-share-btn {
                        position: fixed;
                        display: none;
                        z-index: 99998;
                        background: var(--mc-cream);
                        border: 2px solid var(--mc-ink);
                        box-shadow: 3px 3px 0 var(--mc-mustard);
                        padding: 6px 12px;
                        font-family: 'Press Start 2P', 'Zpix', monospace;
                        font-size: 11px;
                        color: var(--mc-ink);
                        cursor: pointer;
                        letter-spacing: 1px;
                        user-select: none;
                        border-radius: 0;
                    }
                    #rb-share-btn:hover {
                        background: var(--mc-terra);
                        color: var(--mc-cream);
                        transform: translate(-1px, -1px);
                        box-shadow: 4px 4px 0 var(--mc-ink);
                    }
                    #rb-share-btn.is-loading { pointer-events: none; opacity: 0.6; }
                `;
    
                function escapeHtml(s) {
                    return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
                }
                function ensureStyles() {
                    if (pd.getElementById('rb-share-style')) return;
                    const s = pd.createElement('style');
                    s.id = 'rb-share-style';
                    s.textContent = STYLE;
                    pd.head.appendChild(s);
                }
                function ensureButton() {
                    let btn = pd.getElementById('rb-share-btn');
                    if (btn) return btn;
                    ensureStyles();
                    btn = pd.createElement('button');
                    btn.id = 'rb-share-btn';
                    btn.textContent = '📷 分享';
                    btn.type = 'button';
                    pd.body.appendChild(btn);
                    btn.addEventListener('click', onShareClick);
                    btn.addEventListener('mousedown', e => e.stopPropagation());
                    return btn;
                }
    
                let pendingQuote = '';
    
                function getBookTitle() {
                    const el = pd.querySelector('.rd-book-key');
                    if (!el) return '未命名';
                    const key = el.dataset.key || '';
                    const idx = key.lastIndexOf('.');
                    return idx > 0 ? key.substring(0, idx) : key;
                }
    
                function loadHtml2Canvas() {
                    return new Promise((resolve, reject) => {
                        if (p.html2canvas) return resolve(p.html2canvas);
                        const s = pd.createElement('script');
                        s.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
                        s.onload = () => resolve(p.html2canvas);
                        s.onerror = () => reject(new Error('html2canvas load failed'));
                        pd.head.appendChild(s);
                    });
                }
    
                function buildCardElement(quote, bookTitle) {
                    const wrap = pd.createElement('div');
                    wrap.style.cssText = `
                        position: absolute; left: -10000px; top: 0;
                        padding: 8px 32px 32px 8px; background: transparent;
                    `;
                    const cornerStyle = "position:absolute;font-family:'Press Start 2P','Zpix',monospace;color:var(--mc-terra);font-size:14px";
                    const noStr = String(Math.floor(Math.random() * 999)).padStart(3, '0');
                    wrap.innerHTML = `
                        <div style="position:relative;width:680px;padding:56px 56px 40px 56px;background:var(--mc-cream);border:5px solid var(--mc-ink);box-shadow:14px 14px 0 var(--mc-terra);font-family:'Zpix','Noto Serif SC','PingFang SC','Microsoft YaHei',monospace;color:var(--mc-ink);box-sizing:border-box">
                            <div style="${cornerStyle};top:10px;left:14px">[+]</div>
                            <div style="${cornerStyle};top:10px;right:14px">[+]</div>
                            <div style="${cornerStyle};bottom:10px;left:14px">[+]</div>
                            <div style="${cornerStyle};bottom:10px;right:14px">[+]</div>
                            <div style="font-family:'Press Start 2P',monospace;font-size:10px;color:#8b5e3c;letter-spacing:2px;margin-bottom:24px">VOL.01 · QUOTE · NO.${noStr}</div>
                            <div style="font-family:Georgia,serif;font-size:64px;color:var(--mc-mustard);line-height:0.5;margin:0 0 -6px -6px">&ldquo;</div>
                            <div style="font-size:19px;line-height:1.9;letter-spacing:0.5px;padding:0 8px 0 20px;border-left:4px solid var(--mc-terra);white-space:pre-wrap;color:var(--mc-ink);min-height:60px">${escapeHtml(quote)}</div>
                            <div style="font-family:Georgia,serif;font-size:64px;color:var(--mc-mustard);line-height:0.5;text-align:right;margin:-2px -6px 0 0">&rdquo;</div>
                            <div style="margin-top:28px;padding-top:18px;border-top:2px dashed #8b5e3c;display:flex;justify-content:space-between;align-items:baseline;gap:16px">
                                <div style="font-size:14px;color:#8b5e3c;letter-spacing:0.5px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">——《${escapeHtml(bookTitle)}》</div>
                                <div style="font-size:10px;color:var(--mc-moss);font-family:'Press Start 2P',monospace;letter-spacing:2px;white-space:nowrap">★ VIA 嘟哒 DUDA</div>
                            </div>
                        </div>
                    `;
                    return wrap;
                }
    
                async function onShareClick(e) {
                    e.stopPropagation();
                    const btn = pd.getElementById('rb-share-btn');
                    if (!pendingQuote || !btn) return;
                    btn.classList.add('is-loading');
                    btn.textContent = '⏳ 生成中…';
                    const quote = pendingQuote;
                    try {
                        const html2canvas = await loadHtml2Canvas();
                        const wrap = buildCardElement(quote, getBookTitle());
                        pd.body.appendChild(wrap);
                        await new Promise(r => setTimeout(r, 120));
                        const canvas = await html2canvas(wrap, {
                            scale: 2,
                            backgroundColor: null,
                            logging: false,
                            useCORS: true,
                        });
                        wrap.remove();
                        canvas.toBlob(blob => {
                            if (!blob) return;
                            const url = URL.createObjectURL(blob);
                            const a = pd.createElement('a');
                            a.href = url;
                            a.download = `嘟哒_引用_${Date.now()}.png`;
                            pd.body.appendChild(a);
                            a.click();
                            a.remove();
                            setTimeout(() => URL.revokeObjectURL(url), 1000);
                        }, 'image/png');
                    } catch (err) {
                        console.error('Card generation failed:', err);
                    } finally {
                        btn.classList.remove('is-loading');
                        btn.textContent = '📷 分享';
                        btn.style.display = 'none';
                        pendingQuote = '';
                    }
                }
    
                function attach() {
                    if (pd._rb_share_bound) return;
                    pd._rb_share_bound = true;
    
                    pd.addEventListener('mouseup', function(e) {
                        if (e.target && e.target.id === 'rb-share-btn') return;
                        const btn = pd.getElementById('rb-share-btn');
                        const inRead = e.target && e.target.closest && e.target.closest('.book-page');
                        const selObj = p.getSelection ? p.getSelection() : null;
                        const sel = (selObj && selObj.toString() || '').trim();
                        if (!inRead || !sel || sel.length < 8 || sel.length > 500) {
                            if (btn) btn.style.display = 'none';
                            pendingQuote = '';
                            return;
                        }
                        // 确认选区在 book-page 内
                        if (selObj.rangeCount > 0) {
                            const range = selObj.getRangeAt(0);
                            const node = range.commonAncestorContainer;
                            const el = node.nodeType === 1 ? node : node.parentElement;
                            if (!el || !el.closest('.book-page')) {
                                if (btn) btn.style.display = 'none';
                                pendingQuote = '';
                                return;
                            }
                        }
                        pendingQuote = sel;
                        const sb = ensureButton();
                        const x = Math.min(p.innerWidth - 130, Math.max(10, e.clientX + 12));
                        const y = Math.min(p.innerHeight - 50, Math.max(10, e.clientY + 14));
                        sb.style.left = x + 'px';
                        sb.style.top = y + 'px';
                        sb.style.display = 'block';
                    });
    
                    pd.addEventListener('mousedown', function(e) {
                        if (e.target && e.target.id === 'rb-share-btn') return;
                        const btn = pd.getElementById('rb-share-btn');
                        if (btn) btn.style.display = 'none';
                    });
                }
    
                function boot() {
                    if (!pd || !pd.body) { setTimeout(boot, 200); return; }
                    ensureButton();
                    attach();
                }
                boot();
            })();
            </script>
            """, height=0)
    
            # 阅读时长追踪：后台累计每本书的阅读秒数到 localStorage
            components.html("""
            <script>
            (function() {
                const p = window.parent;
                const pd = p.document;
                const STORAGE_KEY = 'reading_buddy_readtime_v1';
                const FLUSH_INTERVAL_MS = 15000;  // 每 15s 刷到 localStorage
                const TICK_INTERVAL_MS = 5000;     // 每 5s 累加
                const MAX_DELTA_S = 60;            // 单次 delta 封顶（防止系统睡眠误算）
    
                let accumulated = 0;
                let lastTick = Date.now();
                let active = true;
    
                function getBookKey() {
                    const el = pd.querySelector('.rd-book-key');
                    return el ? el.dataset.key : null;
                }
    
                function flush() {
                    const bookKey = getBookKey();
                    if (!bookKey || accumulated <= 0) return;
                    try {
                        const raw = p.localStorage.getItem(STORAGE_KEY);
                        let data = {};
                        if (raw) {
                            try { data = JSON.parse(raw); } catch(_) { data = {}; }
                            if (typeof data !== 'object' || data === null) data = {};
                        }
                        data[bookKey] = (data[bookKey] || 0) + accumulated;
                        p.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
                        accumulated = 0;
                    } catch (e) { /* silent */ }
                }
    
                if (pd._rb_readtime_bound) return;
                pd._rb_readtime_bound = true;
    
                setInterval(() => {
                    if (!active) { lastTick = Date.now(); return; }
                    const now = Date.now();
                    const delta = Math.floor((now - lastTick) / 1000);
                    if (delta > 0 && delta <= MAX_DELTA_S) {
                        accumulated += delta;
                    }
                    lastTick = now;
                }, TICK_INTERVAL_MS);
    
                setInterval(flush, FLUSH_INTERVAL_MS);
    
                pd.addEventListener('visibilitychange', () => {
                    if (pd.hidden) {
                        active = false;
                        flush();
                    } else {
                        active = true;
                        lastTick = Date.now();
                    }
                });
                p.addEventListener('pagehide', flush);
                p.addEventListener('beforeunload', flush);
            })();
            </script>
            """, height=0)

        # 侧边栏：阅读记录（字号/字体/主题/专注/书签 已迁到顶部状态条；阶段 7 会把阅读时长也搬到底部统计卡）
        st.sidebar.divider()
        st.sidebar.markdown(
            f'<strong class="sbh">{PX_ICON["clock"]}阅读记录</strong>',
            unsafe_allow_html=True,
        )

        # 阅读时长（累计到 localStorage，JS 后台计数）
        _rt_all = _load_reading_times()
        _rt_book = int(_rt_all.get(book_key, 0))
        if _rt_book >= 60:
            st.sidebar.caption(f"📚 你和这本书相处了 {_format_duration(_rt_book)}")
        elif _rt_book > 0:
            st.sidebar.caption(f"📚 刚开始读这本书（{_rt_book} 秒）")
        else:
            st.sidebar.caption("📚 还没开始计时")

        # 阶段 6：右侧 AI 助读区（spec §9 模块 D）
        with _mc_right:
            # 顶部标题
            st.markdown(
                f'<div class="mc-ai-title">'
                f'<span class="mc-ai-title-icon">{PX_ICON["robot"]}</span>'
                f'<span class="mc-ai-title-text">AI 助读</span>'
                f'<span class="mc-ai-title-pin">📍</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 4 个 tab：spec D.2
            _ai_tab_specs = [
                ("ai_tab_ask", "问这段", None),
                ("ai_tab_summary", "总结本章",
                    "请用简洁清晰的语言总结本章的核心内容、主要事件和关键转折，控制在 6-10 行。"),
                ("ai_tab_explain", "解释词句",
                    "请从本章找出 6-10 个较难理解的生词、成语或关键术语，用 Markdown 表格列出：| 词语 | 释义 | 在本章中的用法 |。"),
                ("ai_tab_viewpoints", "提取观点",
                    "请基于本章内容，提取 3-5 个核心观点或主题，每条简明扼要、附一行展开解释。"),
            ]
            _ai_tab_cols = st.columns(4, gap="small")
            for _i, (_k, _l, _p) in enumerate(_ai_tab_specs):
                with _ai_tab_cols[_i]:
                    if st.button(_l, key=_k, use_container_width=True):
                        if _p:
                            st.session_state._queued_ai_prompt = _p
                            st.rerun()

            # 聊天记录
            if "messages" not in st.session_state:
                st.session_state.messages = []
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.write(m["content"])
            if not st.session_state.messages:
                st.caption("📝 还没开始对话。点上方 4 个 tab 一键提问，或在下方输入框自由发问。")

            # 输入表单（替代 st.chat_input；form 自带 Enter 提交）
            with st.form("mc_ai_form", clear_on_submit=True):
                _form_in_col, _form_btn_col = st.columns([5, 1], gap="small")
                with _form_in_col:
                    _ai_user_input = st.text_input(
                        "向嘟哒提问",
                        placeholder="继续向嘟哒提问…",
                        label_visibility="collapsed",
                        key="mc_ai_input",
                    )
                with _form_btn_col:
                    _ai_submitted = st.form_submit_button("→", use_container_width=True)

            # 决定 prompt 来源（tab 预填优先）
            _queued_prompt = st.session_state.pop("_queued_ai_prompt", None)
            prompt = _queued_prompt
            if not prompt and _ai_submitted and _ai_user_input.strip():
                prompt = _ai_user_input.strip()

            if prompt:
                # 1. 存入并立刻在屏幕上显示用户发的消息
                st.session_state.messages.append({"role": "user", "content": prompt})
                _save_book_messages(book_key, st.session_state.messages)
                with st.chat_message("user"):
                    st.write(prompt)

                # 2. 构造上下文：当前章节全文（长书头尾夹） + 当前 spread 精确位置
                _full_chapter = chapters[chapter_idx]["text"]
                _CH_BUDGET = 8000
                if len(_full_chapter) <= _CH_BUDGET:
                    _chapter_ctx = _full_chapter
                else:
                    _half = _CH_BUDGET // 2
                    _chapter_ctx = (
                        _full_chapter[:_half]
                        + '\n\n……（中间省略，读者正在读的是下方"当前这两页"）……\n\n'
                        + _full_chapter[-_half:]
                    )
                _spread_text = pages[left_idx]
                if right_idx is not None:
                    _spread_text += "\n\n" + pages[right_idx]

                context_msg = (
                    "你正在陪一位读者读书。以下是当前章节的上下文（长章节仅头尾）：\n"
                    "========== 章节内容 ==========\n"
                    f"{_chapter_ctx}\n"
                    "========== 章节内容结束 ==========\n\n"
                    f"读者现在正停在第 {left_num} 页"
                    + (f"-{right_num}" if right_idx is not None else "")
                    + f"（共 {total_pages} 页），这两页原文：\n"
                    "---\n"
                    f"{_spread_text}\n"
                    "---\n\n"
                    "最近的对话历史会在 messages 里给你，请结合。\n"
                    f"读者此刻说：{prompt}"
                )

                # 3. 召唤豆包大脑：流式输出
                with st.chat_message("assistant"):
                    try:
                        client = OpenAI(
                            api_key=st.secrets["ARK_API_KEY"],
                            base_url="https://ark.cn-beijing.volces.com/api/v3",
                        )
                        _history = st.session_state.messages[-9:-1]
                        _api_messages = [
                            {"role": "system", "content": "你是一个高水平的阅读助手，擅长理解复杂的人性、行为逻辑以及具有宏大设定的文学作品。"}
                        ]
                        _api_messages.extend(_history)
                        _api_messages.append({"role": "user", "content": context_msg})

                        stream = client.chat.completions.create(
                            model=st.secrets["ARK_MODEL_ID"],
                            messages=_api_messages,
                            stream=True,
                        )

                        def _token_iter():
                            for chunk in stream:
                                delta = chunk.choices[0].delta.content if chunk.choices else None
                                if delta:
                                    yield delta

                        response_text = st.write_stream(_token_iter())
                        if response_text:
                            st.session_state.messages.append(
                                {"role": "assistant", "content": response_text}
                            )
                            _save_book_messages(book_key, st.session_state.messages)

                    except Exception as e:
                        st.error("嘟哒暂时联系不上大脑，休息一下再试吧。")
                        if st.button("重试", key="ai_retry"):
                            st.session_state.messages.append({"role": "user", "content": prompt})
                            st.rerun()
                        with st.expander("详情"):
                            st.code(str(e))

        # --- 阶段 7 底部四卡 ---
        _c_lib, _c_notes, _c_upload, _c_stats = st.columns([30, 24, 22, 24], gap="small")

        # 卡 1：我的书架
        with _c_lib:
            st.markdown(
                f'<div class="mc-card-library"></div>'
                f'<div class="mc-card-title">'
                f'<span class="mc-card-title-left">{PX_ICON["shelf"]} 我的书架</span>'
                f'<span class="mc-card-viewall">查看全部 ›</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _lib_all = _load_library()
            # 按最后打开时间降序，取最近 4 本
            _recent = sorted(
                _lib_all.items(),
                key=lambda kv: kv[1].get("last_opened_at", ""),
                reverse=True,
            )[:4]
            if not _recent:
                st.markdown(
                    '<div class="mc-lib-empty">还没有书～<br>右边上传你的第一本书</div>',
                    unsafe_allow_html=True,
                )
            else:
                _read_times = _load_reading_times()
                _progress_store = _load_progress()
                _lib_html = '<div class="mc-lib-grid">'
                for _bk, _bm in _recent:
                    _cover = _bm.get("cover_color", "#8B5E3C")
                    _title_disp = _bm.get("title", _bk)
                    _title_short = _title_disp[:8] + "…" if len(_title_disp) > 8 else _title_disp
                    # 进度百分比：从 _LS_PROGRESS_KEY 或根据章节数估算
                    _prog = _progress_store.get(_bk, {})
                    _pct = 0
                    if _bm.get("chapter_count"):
                        _pct = int(
                            (int(_prog.get("chapter_idx", 0)) + 1) / max(1, int(_bm["chapter_count"])) * 100
                        )
                        _pct = min(max(_pct, 0), 100)
                    _lib_html += (
                        f'<div class="mc-lib-item">'
                        f'<div class="mc-lib-cover" style="background:{_cover}">{html.escape(_title_short)}</div>'
                        f'<div class="mc-lib-name">{html.escape(_title_disp)}</div>'
                        f'<div class="mc-lib-progress-wrap"><div class="mc-lib-progress-fill" style="width:{_pct}%"></div></div>'
                        f'<div class="mc-lib-percent">{_pct}%</div>'
                        f'</div>'
                    )
                _lib_html += '</div>'
                st.markdown(_lib_html, unsafe_allow_html=True)

        # 卡 2：摘录与笔记
        with _c_notes:
            st.markdown(
                f'<div class="mc-card-notes"></div>'
                f'<div class="mc-card-title">'
                f'<span class="mc-card-title-left">{PX_ICON["save"]} 摘录与笔记</span>'
                f'<span class="mc-card-viewall">查看全部 ›</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _latest_notes = st.session_state.get("notes", [])
            if not _latest_notes:
                st.markdown(
                    '<div class="mc-lib-empty">暂无摘录<br>去阅读并保存第一条摘录</div>',
                    unsafe_allow_html=True,
                )
            else:
                _latest_n = _latest_notes[-1]
                _np_text = (_latest_n.get("passage") or "").strip()
                _nt_text = (_latest_n.get("note") or "").strip()
                _n_ch = int(_latest_n.get("chapter_idx", 0))
                _n_pg = int(_latest_n.get("page", 0)) + 1
                _n_title = chapter_titles[_n_ch] if 0 <= _n_ch < len(chapter_titles) else f"章节 {_n_ch+1}"
                _n_date = _latest_n.get("ts", "")
                _book_disp = _tb_book_title
                _notes_html = ""
                if _np_text:
                    _notes_html += (
                        f'<div class="mc-notes-quote">'
                        f'{html.escape(_np_text[:90] + ("…" if len(_np_text) > 90 else ""))}'
                        f'</div>'
                        f'<div class="mc-notes-meta">——《{html.escape(_book_disp)}》 · {html.escape(_n_title)} · 第 {_n_pg} 页</div>'
                    )
                if _nt_text:
                    _notes_html += (
                        f'<div class="mc-notes-body">'
                        f'<span class="mc-notes-body-label">✏ 我的笔记：</span>'
                        f'<span>{html.escape(_nt_text[:60] + ("…" if len(_nt_text) > 60 else ""))}</span>'
                        f'</div>'
                    )
                if _n_date:
                    _notes_html += f'<div class="mc-notes-date">{html.escape(_n_date)}</div>'
                st.markdown(_notes_html, unsafe_allow_html=True)

        # 卡 3：上传书籍
        with _c_upload:
            st.markdown(
                f'<div class="mc-card-upload"></div>'
                f'<div class="mc-card-title">'
                f'<span class="mc-card-title-left">{PX_ICON["upload"]} 上传书籍</span>'
                f'</div>'
                f'<div class="mc-upload-hint">支持 EPUB / PDF / MOBI / TXT / AZW3 格式</div>',
                unsafe_allow_html=True,
            )
            _bottom_upload = st.file_uploader(
                "上传新书",
                type=SUPPORTED_FORMATS,
                help="支持 EPUB、TXT、PDF、MOBI、AZW3",
                key="upload_bottom_card",
                label_visibility="collapsed",
            )
            if _bottom_upload:
                st.session_state.file_bytes = _bottom_upload.getvalue()
                st.session_state.file_name = _bottom_upload.name
                st.rerun()

        # 卡 4：阅读统计
        with _c_stats:
            st.markdown(
                f'<div class="mc-card-stats"></div>'
                f'<div class="mc-card-title">'
                f'<span class="mc-card-title-left">{PX_ICON["chart"]} 阅读统计</span>'
                f'<span class="mc-card-viewall">本周</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _stats = _compute_reading_stats()
            # 时长行
            _h = _stats["total_hours"]
            _m = _stats["total_minutes"]
            _hm = f"{_h} h {_m} m" if _h > 0 else f"{_m} m" if _m > 0 else "未开始"
            # 连续天数 delta
            _wd = _stats["weekly_delta_days"]
            if _wd > 0:
                _delta_cls, _delta_txt = "up", f"▲{_wd}"
            elif _wd < 0:
                _delta_cls, _delta_txt = "down", f"▼{abs(_wd)}"
            else:
                _delta_cls, _delta_txt = "flat", "持平"
            _stats_html = (
                f'<div class="mc-stats-row">'
                f'<span class="mc-stats-icon">🕐</span>'
                f'<span class="mc-stats-label">总阅读时长</span>'
                f'<span class="mc-stats-value">{_hm}</span>'
                f'</div>'
                f'<div class="mc-stats-row">'
                f'<span class="mc-stats-icon">📖</span>'
                f'<span class="mc-stats-label">已读书籍</span>'
                f'<span class="mc-stats-value">{_stats["books_read"]} 本</span>'
                f'</div>'
                f'<div class="mc-stats-row">'
                f'<span class="mc-stats-icon">🔥</span>'
                f'<span class="mc-stats-label">连续天数</span>'
                f'<span class="mc-stats-value">{_stats["streak"]} 天</span>'
                f'<span class="mc-stats-delta {_delta_cls}">{_delta_txt}</span>'
                f'</div>'
            )
            st.markdown(_stats_html, unsafe_allow_html=True)

    else:
        st.warning("书本解析失败，请确认文件是否损坏，或换一本书试试。")
else:
    # 日式编辑 zine 风欢迎页（全屏覆盖 + 内嵌上传器）
    # 拆成两段：上段（刊头 + Hero）→ 上传器 → 下段（流程 + 特性 + 底栏），
    # 这样上传器在首屏可见，无需下滑。
    # 随机开场签：以当天日期为种子，一天内保持同一句
    import html as _html
    _QUOTES = [
        ("不去想那些遥远的事，只是走，一步一步。", "《瓦尔登湖》亨利·梭罗"),
        ("今天的太阳照在昨天的雪上。", "《局外人》阿尔贝·加缪"),
        ("我只是个过客，可我爱这个世界。", "《挪威的森林》村上春树"),
        ("细节是魔鬼，也是天使。", "《包法利夫人》福楼拜"),
        ("人只有在孤独中才能认识自己。", "《约翰·克利斯朵夫》罗曼·罗兰"),
        ("所谓青春，就是一种永久的失去。", "《挪威的森林》村上春树"),
        ("书是人类进步的阶梯，也是孤独时最好的伴侣。", "高尔基"),
        ("我们都是时间的旅人，只是速度不同。", "《时间简史》霍金"),
        ("真正的旅行不是用眼睛看，而是用心感受。", "马塞尔·普鲁斯特"),
        ("读一本好书，就是和许多高尚的人谈话。", "歌德"),
        ("没有什么比一本旧书更让人感到安慰的了。", "简·奥斯汀"),
        ("世界上只有一种英雄主义，就是认清生活的真相之后依然热爱生活。", "罗曼·罗兰"),
        ("阅读是一种孤独。", "毕淑敏"),
        ("每一本书都是一个世界。", "爱默生"),
        ("书给了我一个世界，而我居住其中。", "乌苏拉·勒古恩"),
    ]
    _q_idx = datetime.now().timetuple().tm_yday % len(_QUOTES)
    _q_text, _q_from = _QUOTES[_q_idx]
    st.markdown("""
    <div class="zine-welcome zw-top">
        <div class="zw-sparkles" aria-hidden="true">
            <span class="sp" style="left:1%;top:18%;width:4px;height:4px;background:var(--mc-terra);animation-delay:0s;animation-duration:2.8s"></span>
            <span class="sp" style="left:3%;top:42%;width:6px;height:6px;background:var(--mc-mustard);animation-delay:1.1s;animation-duration:3.5s"></span>
            <span class="sp" style="left:1.5%;top:68%;width:4px;height:4px;background:var(--mc-moss);animation-delay:2.2s;animation-duration:2.5s"></span>
            <span class="sp" style="left:4%;top:85%;width:2px;height:2px;background:var(--mc-dusty);animation-delay:0.5s;animation-duration:4s"></span>
            <span class="sp" style="left:2.5%;top:30%;width:4px;height:4px;background:var(--mc-mustard);animation-delay:3s;animation-duration:3.2s"></span>
            <span class="sp" style="left:5%;top:55%;width:2px;height:2px;background:var(--mc-terra);animation-delay:1.7s;animation-duration:4.4s"></span>
            <span class="sp" style="right:1%;top:25%;width:4px;height:4px;background:var(--mc-mustard);animation-delay:0.7s;animation-duration:3.1s"></span>
            <span class="sp" style="right:3%;top:58%;width:6px;height:6px;background:var(--mc-terra);animation-delay:1.8s;animation-duration:2.7s"></span>
            <span class="sp" style="right:1.5%;top:75%;width:4px;height:4px;background:var(--mc-dusty);animation-delay:2.5s;animation-duration:3.8s"></span>
            <span class="sp" style="right:4%;top:38%;width:2px;height:2px;background:var(--mc-moss);animation-delay:0.3s;animation-duration:4.2s"></span>
            <span class="sp" style="right:2%;top:88%;width:4px;height:4px;background:var(--mc-mustard);animation-delay:3.5s;animation-duration:2.9s"></span>
            <span class="sp" style="right:5%;top:14%;width:2px;height:2px;background:var(--mc-terra);animation-delay:2.1s;animation-duration:3.6s"></span>
            <span class="sp" style="left:8%;top:6%;width:2px;height:2px;background:var(--mc-moss);animation-delay:1.5s;animation-duration:5s"></span>
            <span class="sp" style="right:9%;top:94%;width:2px;height:2px;background:var(--mc-mustard);animation-delay:2.8s;animation-duration:4.5s"></span>
            <span class="sp" style="right:12%;top:4%;width:4px;height:4px;background:var(--mc-dusty);animation-delay:2s;animation-duration:4.1s"></span>
        </div>
        <!-- 左侧像素书架 -->
        <div class="zw-shelf" style="position:absolute;left:8px;bottom:24px;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="52" height="122" viewBox="0 0 52 122" xmlns="http://www.w3.org/2000/svg" style="image-rendering:pixelated;shape-rendering:crispEdges;display:block">
            <rect x="0" y="112" width="52" height="2" fill="#2E1D12"/>
            <rect x="1" y="68" width="8" height="44" fill="#B96A4A"/>
            <rect x="1" y="68" width="8" height="1" fill="#7d2e21"/>
            <rect x="1" y="111" width="8" height="1" fill="#7d2e21"/>
            <rect x="2" y="75" width="5" height="1" fill="#F6E7C8" opacity="0.7"/>
            <rect x="10" y="54" width="8" height="58" fill="#D7A441"/>
            <rect x="10" y="54" width="8" height="1" fill="#8a7420"/>
            <rect x="10" y="111" width="8" height="1" fill="#8a7420"/>
            <rect x="11" y="62" width="5" height="1" fill="#2E1D12" opacity="0.35"/>
            <rect x="11" y="66" width="4" height="1" fill="#2E1D12" opacity="0.35"/>
            <g class="zw-book-pull">
              <rect x="19" y="72" width="7" height="40" fill="#6E8B5B"/>
              <rect x="19" y="72" width="7" height="1" fill="#2d4130"/>
              <rect x="19" y="111" width="7" height="1" fill="#2d4130"/>
              <rect x="20" y="79" width="4" height="1" fill="#F6E7C8" opacity="0.5"/>
            </g>
            <rect x="27" y="63" width="8" height="49" fill="#7a96b4"/>
            <rect x="27" y="63" width="8" height="1" fill="#4a6878"/>
            <rect x="27" y="111" width="8" height="1" fill="#4a6878"/>
            <rect x="36" y="76" width="5" height="36" fill="#2E1D12"/>
            <rect x="36" y="76" width="5" height="1" fill="#1a1209"/>
            <rect x="36" y="111" width="5" height="1" fill="#1a1209"/>
            <rect x="37" y="83" width="3" height="1" fill="#F6E7C8" opacity="0.3"/>
            <rect x="42" y="70" width="9" height="42" fill="#e07b5a"/>
            <rect x="42" y="70" width="9" height="1" fill="#B96A4A"/>
            <rect x="42" y="111" width="9" height="1" fill="#B96A4A"/>
          </svg>
        </div>
        <!-- 左侧像素星星群 -->
        <div class="zw-stars" style="position:absolute;left:6px;top:10%;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="24" height="26" viewBox="0 0 24 26" style="image-rendering:pixelated;shape-rendering:crispEdges">
            <rect x="3" y=  "8" width="1" height="5" fill="#D7A441"/>
            <rect x="1" y="10" width="5" height="1" fill="#D7A441"/>
            <rect x="16" y="2" width="1" height="5" fill="#D7A441"/>
            <rect x="14" y="4" width="5" height="1" fill="#D7A441"/>
            <rect x="18" y="13" width="1" height="3" fill="#7a96b4"/>
            <rect x="17" y="14" width="3" height="1" fill="#7a96b4"/>
            <rect x="7" y="1" width="1" height="3" fill="#B96A4A" opacity="0.7"/>
            <rect x="6" y="2" width="3" height="1" fill="#B96A4A" opacity="0.7"/>
            <rect x="0" y="18" width="2" height="2" fill="#D7A441" opacity="0.5"/>
            <rect x="11" y="9" width="2" height="2" fill="#6E8B5B" opacity="0.6"/>
            <rect x="9" y="20" width="2" height="2" fill="#7a96b4" opacity="0.5"/>
            <rect x="21" y="20" width="2" height="2" fill="#D7A441" opacity="0.4"/>
          </svg>
        </div>
        <!-- 左侧像素蘑菇 -->
        <div class="zw-mushroom" style="position:absolute;left:6px;top:46%;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="24" height="22" viewBox="0 0 12 11" style="image-rendering:pixelated;shape-rendering:crispEdges">
            <rect x="3" y="0" width="6" height="1" fill="#B96A4A"/>
            <rect x="1" y="1" width="10" height="1" fill="#B96A4A"/>
            <rect x="0" y="2" width="12" height="3" fill="#B96A4A"/>
            <rect x="1" y="2" width="2" height="1" fill="#F6E7C8"/>
            <rect x="9" y="2" width="2" height="1" fill="#F6E7C8"/>
            <rect x="5" y="3" width="2" height="1" fill="#F6E7C8" opacity="0.7"/>
            <rect x="1" y="5" width="10" height="1" fill="#8b3f2a"/>
            <rect x="3" y="6" width="6" height="1" fill="#f0e6cc"/>
            <rect x="4" y="7" width="4" height="3" fill="#e8d8b0"/>
            <rect x="3" y="10" width="6" height="1" fill="#8b7450"/>
          </svg>
        </div>
        <!-- 右侧像素火把 -->
        <div class="zw-torch" style="position:absolute;right:8px;top:18%;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="24" height="48" viewBox="0 0 24 48" style="image-rendering:pixelated;shape-rendering:crispEdges">
            <rect x="0" y="20" width="24" height="3" fill="#2E1D12"/>
            <rect x="9" y="23" width="6" height="20" fill="#6b4226"/>
            <rect x="9" y="23" width="6" height="1" fill="#4a2d16"/>
            <rect x="6" y="14" width="12" height="8" fill="#8b5e3c"/>
            <rect x="7" y="13" width="10" height="2" fill="#a0723c"/>
            <rect x="6" y="21" width="12" height="1" fill="#4a2d16"/>
            <g class="zw-f1">
              <rect x="10" y="4" width="4" height="10" fill="#ff8c00"/>
              <rect x="9" y="7" width="6" height="7" fill="#ff4500"/>
              <rect x="11" y="1" width="2" height="5" fill="#ffd700"/>
            </g>
            <g class="zw-f2">
              <rect x="8" y="5" width="4" height="9" fill="#ff8c00"/>
              <rect x="7" y="8" width="7" height="6" fill="#ff4500"/>
              <rect x="9" y="2" width="2" height="5" fill="#ffd700"/>
            </g>
            <g class="zw-f3">
              <rect x="12" y="5" width="4" height="9" fill="#ff8c00"/>
              <rect x="10" y="8" width="7" height="6" fill="#ff4500"/>
              <rect x="13" y="2" width="2" height="5" fill="#ffd700"/>
            </g>
          </svg>
        </div>
        <!-- 右侧像素心形 -->
        <div class="zw-hearts" style="position:absolute;right:5px;top:56%;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="56" height="24" viewBox="0 0 56 24" style="image-rendering:pixelated;shape-rendering:crispEdges">
            <g fill="#e04040">
              <rect x="2" y="0" width="4" height="4"/>
              <rect x="10" y="0" width="4" height="4"/>
              <rect x="0" y="4" width="16" height="8"/>
              <rect x="2" y="12" width="12" height="4"/>
              <rect x="4" y="16" width="8" height="4"/>
              <rect x="6" y="20" width="4" height="4"/>
            </g>
            <rect x="2" y="2" width="3" height="2" fill="#ff6868" opacity="0.6"/>
            <g fill="#e04040">
              <rect x="22" y="0" width="4" height="4"/>
              <rect x="30" y="0" width="4" height="4"/>
              <rect x="20" y="4" width="16" height="8"/>
              <rect x="22" y="12" width="12" height="4"/>
              <rect x="24" y="16" width="8" height="4"/>
              <rect x="26" y="20" width="4" height="4"/>
            </g>
            <rect x="22" y="2" width="3" height="2" fill="#ff6868" opacity="0.6"/>
            <g class="zw-heart-beat" fill="#e04040">
              <rect x="42" y="0" width="4" height="4"/>
              <rect x="50" y="0" width="4" height="4"/>
              <rect x="40" y="4" width="16" height="8"/>
              <rect x="42" y="12" width="12" height="4"/>
              <rect x="44" y="16" width="8" height="4"/>
              <rect x="46" y="20" width="4" height="4"/>
              <rect x="42" y="2" width="3" height="2" fill="#ff6868" opacity="0.6"/>
            </g>
          </svg>
        </div>
        <div class="zw-corner tl">[+]</div>
        <div class="zw-corner tr">[+]</div>
        <div class="zw-topbar">
            <span>VOL.01 <span class="dot">■</span> EST.2026</span>
            <b>SWEET SWEET HOMELAND</b>
            <span>№001 <span class="dot">■</span> PIXEL EDITION</span>
        </div>
        <div class="zw-hero">
            <div class="zw-hero-text">
                <div class="zw-kicker">A READING CLUB</div>
                <h1 class="zw-title">DUDA</h1>
                <div class="zw-title-bar"></div>
                <div class="zw-subtitle-zh">YOUR COZY READING PAL</div>
                <div class="zw-desc">
                    <span class="line line-1">在这里，每一本书都值得被深度对话。</span>
                    <span class="line line-3">「""" + _html.escape(_q_text) + """」</span>
                    <span class="line line-4">—— """ + _html.escape(_q_from) + """<span class="caret on"></span></span>
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
                <svg id="zw-cat-svg" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                    <!-- 书 1 底部 陶土红 -->
                    <rect x="6" y="50" width="52" height="8" fill="#B96A4A"/>
                    <rect x="6" y="50" width="52" height="1" fill="#7d2e21"/>
                    <rect x="6" y="57" width="52" height="1" fill="#7d2e21"/>
                    <rect x="10" y="53" width="16" height="1" fill="#F6E7C8"/>
                    <rect x="10" y="55" width="12" height="1" fill="#F6E7C8"/>
                    <!-- 书 2 中间 苔绿 -->
                    <rect x="10" y="42" width="44" height="8" fill="#6E8B5B"/>
                    <rect x="10" y="42" width="44" height="1" fill="#2d4130"/>
                    <rect x="10" y="49" width="44" height="1" fill="#2d4130"/>
                    <rect x="14" y="45" width="14" height="1" fill="#F6E7C8"/>
                    <!-- 书 3 顶部 芥黄 -->
                    <rect x="14" y="34" width="36" height="8" fill="#D7A441"/>
                    <rect x="14" y="34" width="36" height="1" fill="#8a7420"/>
                    <rect x="14" y="41" width="36" height="1" fill="#8a7420"/>
                    <rect x="18" y="37" width="10" height="1" fill="#2E1D12"/>
                    <!-- 白猫 curled 在书顶 -->
                    <!-- 耳朵（描边 + 白填充 + 粉内耳） -->
                    <rect x="15" y="19" width="6" height="1" fill="#2E1D12"/>
                    <rect x="21" y="19" width="6" height="1" fill="#2E1D12"/>
                    <rect x="15" y="20" width="1" height="4" fill="#2E1D12"/>
                    <rect x="20" y="20" width="1" height="4" fill="#2E1D12"/>
                    <rect x="21" y="20" width="1" height="4" fill="#2E1D12"/>
                    <rect x="26" y="20" width="1" height="4" fill="#2E1D12"/>
                    <rect x="16" y="20" width="4" height="4" fill="#fffef8"/>
                    <rect x="22" y="20" width="4" height="4" fill="#fffef8"/>
                    <rect x="17" y="22" width="2" height="2" fill="#e07b5a"/>
                    <rect x="23" y="22" width="2" height="2" fill="#e07b5a"/>
                    <!-- 头身描边 -->
                    <rect x="13" y="24" width="30" height="1" fill="#2E1D12"/>
                    <rect x="11" y="26" width="34" height="1" fill="#2E1D12"/>
                    <rect x="11" y="31" width="34" height="1" fill="#2E1D12"/>
                    <rect x="13" y="33" width="30" height="1" fill="#2E1D12"/>
                    <rect x="11" y="27" width="1" height="4" fill="#2E1D12"/>
                    <rect x="44" y="27" width="1" height="4" fill="#2E1D12"/>
                    <rect x="13" y="25" width="1" height="8" fill="#2E1D12"/>
                    <rect x="42" y="25" width="1" height="8" fill="#2E1D12"/>
                    <!-- 身体（白填充） -->
                    <rect x="14" y="24" width="28" height="10" fill="#fffef8"/>
                    <rect x="12" y="26" width="32" height="6" fill="#fffef8"/>
                    <!-- 底部浅灰阴影增加立体感 -->
                    <rect x="14" y="32" width="28" height="1" fill="#e5dcc0"/>
                    <!-- 闭眼（黑色短横线） -->
                    <g id="zw-eyes-closed">
                        <rect x="17" y="28" width="3" height="1" fill="#2E1D12"/>
                        <rect x="22" y="28" width="3" height="1" fill="#2E1D12"/>
                    </g>
                    <!-- 睁眼（点击后短暂显示） -->
                    <g id="zw-eyes-open" style="display:none">
                        <rect x="17" y="27" width="3" height="3" fill="#2E1D12"/>
                        <rect x="18" y="28" width="1" height="1" fill="#fffef8"/>
                        <rect x="22" y="27" width="3" height="3" fill="#2E1D12"/>
                        <rect x="23" y="28" width="1" height="1" fill="#fffef8"/>
                    </g>
                    <!-- 鼻 -->
                    <rect x="20" y="30" width="2" height="1" fill="#B96A4A"/>
                    <!-- 嘴 -->
                    <rect x="19" y="31" width="1" height="1" fill="#2E1D12"/>
                    <rect x="22" y="31" width="1" height="1" fill="#2E1D12"/>
                    <!-- 腮红 -->
                    <rect x="15" y="29" width="1" height="1" fill="#e07b5a" opacity="0.5"/>
                    <rect x="26" y="29" width="1" height="1" fill="#e07b5a" opacity="0.5"/>
                    <!-- 尾巴（描边 + 白填充） -->
                    <rect x="40" y="21" width="2" height="1" fill="#2E1D12"/>
                    <rect x="39" y="22" width="1" height="6" fill="#2E1D12"/>
                    <rect x="42" y="22" width="1" height="6" fill="#2E1D12"/>
                    <rect x="40" y="22" width="2" height="6" fill="#fffef8"/>
                    <rect x="42" y="19" width="3" height="1" fill="#2E1D12"/>
                    <rect x="42" y="20" width="1" height="2" fill="#2E1D12"/>
                    <rect x="44" y="20" width="1" height="2" fill="#2E1D12"/>
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
        <div class="zw-sparkles" aria-hidden="true">
            <span class="sp" style="left:1.5%;top:28%;width:4px;height:4px;background:var(--mc-mustard);animation-delay:0.4s;animation-duration:3.2s"></span>
            <span class="sp" style="left:3.5%;top:62%;width:6px;height:6px;background:var(--mc-moss);animation-delay:1.6s;animation-duration:2.8s"></span>
            <span class="sp" style="left:2%;top:82%;width:2px;height:2px;background:var(--mc-terra);animation-delay:2.8s;animation-duration:4s"></span>
            <span class="sp" style="left:5%;top:45%;width:2px;height:2px;background:var(--mc-dusty);animation-delay:3.4s;animation-duration:3.7s"></span>
            <span class="sp" style="right:1.5%;top:20%;width:4px;height:4px;background:var(--mc-terra);animation-delay:1s;animation-duration:3.5s"></span>
            <span class="sp" style="right:3%;top:52%;width:6px;height:6px;background:var(--mc-dusty);animation-delay:2.2s;animation-duration:2.6s"></span>
            <span class="sp" style="right:2%;top:76%;width:2px;height:2px;background:var(--mc-mustard);animation-delay:0.6s;animation-duration:4.3s"></span>
            <span class="sp" style="right:5%;top:38%;width:4px;height:4px;background:var(--mc-moss);animation-delay:1.9s;animation-duration:3.1s"></span>
            <span class="sp" style="left:7%;top:90%;width:2px;height:2px;background:var(--mc-moss);animation-delay:1.8s;animation-duration:5s"></span>
            <span class="sp" style="right:8%;top:8%;width:4px;height:4px;background:var(--mc-terra);animation-delay:3.2s;animation-duration:3.8s"></span>
        </div>
        <!-- 左侧像素盆栽 -->
        <div class="zw-plant" style="position:absolute;left:6px;top:24%;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="20" height="28" viewBox="0 0 10 14" style="image-rendering:pixelated;shape-rendering:crispEdges">
            <rect x="3" y="0" width="4" height="1" fill="#6E8B5B"/>
            <rect x="2" y="1" width="6" height="2" fill="#5a8060"/>
            <rect x="0" y="3" width="4" height="2" fill="#6E8B5B"/>
            <rect x="6" y="3" width="4" height="2" fill="#5a8060"/>
            <rect x="1" y="4" width="2" height="1" fill="#3a5a3e"/>
            <rect x="7" y="4" width="2" height="1" fill="#3a5a3e"/>
            <rect x="4" y="3" width="2" height="2" fill="#6b4226"/>
            <rect x="1" y="5" width="8" height="1" fill="#d46a4a"/>
            <rect x="2" y="6" width="6" height="5" fill="#B96A4A"/>
            <rect x="3" y="6" width="4" height="1" fill="#d46a4a"/>
            <rect x="3" y="11" width="4" height="1" fill="#8b3f2a"/>
            <rect x="4" y="12" width="2" height="2" fill="#8b3f2a"/>
          </svg>
        </div>
        <!-- 右侧像素药水 -->
        <div class="zw-potion" style="position:absolute;right:8px;top:32%;z-index:2;pointer-events:none" aria-hidden="true">
          <svg width="20" height="30" viewBox="0 0 10 15" style="image-rendering:pixelated;shape-rendering:crispEdges">
            <rect x="3" y="0" width="4" height="1" fill="#8b5e3c"/>
            <rect x="3" y="1" width="4" height="2" fill="#9ab6c4"/>
            <rect x="2" y="3" width="6" height="1" fill="#4a6878"/>
            <rect x="1" y="4" width="8" height="8" fill="#7a96b4"/>
            <rect x="1" y="7" width="8" height="5" fill="#5a86b4"/>
            <rect x="2" y="4" width="2" height="3" fill="#b8d0dc" opacity="0.5"/>
            <rect x="5" y="9" width="2" height="1" fill="#9ab6c4" opacity="0.6"/>
            <rect x="4" y="11" width="1" height="1" fill="#9ab6c4" opacity="0.5"/>
            <rect x="1" y="12" width="8" height="1" fill="#4a6878"/>
            <rect x="2" y="13" width="6" height="1" fill="#3a5868"/>
            <rect x="3" y="14" width="4" height="1" fill="#2a4858"/>
          </svg>
        </div>
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
    # 点猫眨眼：click → 睁眼 0.9s → 闭眼
    components.html("""
    <script>
    (function() {
        function attachCatBlink() {
            const svg = window.parent.document.getElementById('zw-cat-svg');
            if (!svg) { setTimeout(attachCatBlink, 200); return; }
            if (svg._rb_blink_bound) return;
            svg._rb_blink_bound = true;
            svg.addEventListener('click', function() {
                const closed = window.parent.document.getElementById('zw-eyes-closed');
                const open   = window.parent.document.getElementById('zw-eyes-open');
                if (!closed || !open) return;
                closed.style.display = 'none';
                open.style.display   = '';
                setTimeout(function() {
                    open.style.display   = 'none';
                    closed.style.display = '';
                }, 900);
            });
        }
        attachCatBlink();
    })();

    // 猫猫 parallax：鼠标在 hero 区域移动时，猫轻微跟随偏移
    (function() {
        function attachParallax() {
            const p = window.parent.document;
            const art = p.querySelector('.zw-art');
            if (!art) { setTimeout(attachParallax, 200); return; }
            if (art._rb_parallax_bound) return;
            art._rb_parallax_bound = true;
            art.style.transition = 'transform 0.18s steps(3)';
            let raf = null;
            p.addEventListener('mousemove', function(e) {
                const hero = p.querySelector('.zw-hero');
                if (!hero) return;
                const rect = hero.getBoundingClientRect();
                const inside = e.clientX >= rect.left && e.clientX <= rect.right &&
                               e.clientY >= rect.top  && e.clientY <= rect.bottom;
                if (!inside) { art.style.transform = 'translate(0,0)'; return; }
                if (raf) return;
                raf = requestAnimationFrame(function() {
                    raf = null;
                    const cx = rect.left + rect.width / 2;
                    const cy = rect.top  + rect.height / 2;
                    const dx = (e.clientX - cx) / (rect.width  / 2);
                    const dy = (e.clientY - cy) / (rect.height / 2);
                    const tx = Math.round(dx * 16);
                    const ty = Math.round(dy * 10);
                    art.style.transform = 'translate(' + tx + 'px,' + ty + 'px)';
                });
            });
        }
        attachParallax();
    })();
    </script>
    """, height=0)
