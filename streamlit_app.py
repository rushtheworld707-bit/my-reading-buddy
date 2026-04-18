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

# 2. 全局自定义样式
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Noto+Serif+SC:wght@400;700;900&family=Noto+Sans+SC:wght@400;500;700&family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">', unsafe_allow_html=True)
st.markdown("""
<style>
/* 主标题手绘体 */
.handwrite-title {
    font-family: 'Caveat', cursive;
    font-size: 52px;
    font-weight: 700;
    color: #ff6b6b;
    text-align: center;
    margin: 8px 0 16px 0;
    letter-spacing: 2px;
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

/* 进度条容器 */
.progress-container {
    background: #2a2a3e;
    border-radius: 10px;
    height: 6px;
    margin: 8px 0 16px 0;
    overflow: hidden;
}
.progress-fill {
    background: linear-gradient(90deg, #e94560, #ff6b6b);
    height: 100%;
    border-radius: 10px;
    transition: width 0.3s ease;
}

/* 页码和进度信息 */
.page-indicator {
    text-align: center;
    color: #ff9eb3;
    font-size: 13px;
    font-weight: 500;
    margin: 8px 0;
}

/* 时间显示 */
.time-display {
    text-align: right;
    color: #666;
    font-size: 13px;
    padding: 4px 8px;
}


/* 欢迎页面 */
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-12px); }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes glow {
    0%, 100% { text-shadow: 0 0 10px rgba(233,69,96,0.3); }
    50% { text-shadow: 0 0 25px rgba(233,69,96,0.6), 0 0 50px rgba(233,69,96,0.2); }
}
@keyframes shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
}

.welcome-box {
    text-align: center;
    padding: 60px 40px 80px;
    color: #ccc;
}
.welcome-cat {
    font-size: 72px;
    display: inline-block;
    animation: float 3s ease-in-out infinite;
    margin-bottom: 16px;
}
.welcome-title {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(90deg, #e94560, #ff6b6b, #ffa07a, #e94560);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite, fadeInUp 1s ease-out;
    margin-bottom: 20px;
}
.welcome-desc {
    font-size: 16px;
    color: #888;
    animation: fadeInUp 1s ease-out 0.3s both;
    line-height: 1.8;
}
.welcome-formats {
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-top: 28px;
    flex-wrap: wrap;
    animation: fadeInUp 1s ease-out 0.6s both;
}
.format-tag {
    background: rgba(233, 69, 96, 0.12);
    border: 1px solid rgba(233, 69, 96, 0.3);
    color: #ff6b6b;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.3s;
}
.format-tag:hover {
    background: rgba(233, 69, 96, 0.25);
    transform: scale(1.05);
}
.welcome-hint {
    margin-top: 32px;
    font-size: 14px;
    color: #555;
    animation: fadeInUp 1s ease-out 0.9s both;
}
.welcome-hint span {
    animation: glow 2s ease-in-out infinite;
}

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

    /* 欢迎页面 */
    .welcome-box { padding: 40px 16px; }
    .welcome-cat { font-size: 56px; }
    .welcome-title { font-size: 22px; }
    .welcome-desc { font-size: 14px; }
    .welcome-formats { gap: 8px; }
    .format-tag { padding: 4px 12px; font-size: 12px; }
    .time-display { font-size: 12px; }

    h1 { font-size: 24px !important; }
    h2, .stSubheader { font-size: 18px !important; }
}

@media (max-width: 480px) {
    .book-page {
        padding: 16px 12px;
        min-height: 220px;
        font-size: 15px;
    }
    .page-indicator { font-size: 12px; }
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
.nav-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 20px;
    background: linear-gradient(135deg, rgba(255, 107, 107, 0.20), rgba(255, 154, 154, 0.12));
    border: 1.5px solid rgba(255, 154, 154, 0.50);
    border-radius: 18px;
    color: #ffd6d6;
    font-weight: 600;
    font-size: 14px;
    font-family: inherit;
    text-decoration: none !important;
    transition: all 0.25s ease;
    box-shadow: 0 2px 10px rgba(255, 107, 107, 0.18);
    cursor: pointer;
    user-select: none;
}
.nav-btn:hover {
    background: linear-gradient(135deg, rgba(255, 107, 107, 0.32), rgba(255, 154, 154, 0.20));
    border-color: rgba(255, 154, 154, 0.75);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(255, 107, 107, 0.30);
    color: #fff !important;
}
.nav-btn.nav-disabled {
    opacity: 0.35;
    pointer-events: none;
    transform: none;
    box-shadow: none;
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
}
body:has(.zine-welcome) .handwrite-title {
    display: none !important;
}

/* 中文像素字体 Zpix（最像素）from jsDelivr */
@font-face {
    font-family: 'Zpix';
    src: url('https://cdn.jsdelivr.net/gh/SolidZORO/zpix-pixel-font@main/fonts/.woff2/Zpix.woff2') format('woff2'),
         url('https://cdn.jsdelivr.net/gh/SolidZORO/zpix-pixel-font@main/fonts/.ttf/Zpix.ttf') format('truetype');
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

.zine-welcome {
    position: relative;
    min-height: 100vh;
    width: 100%;
    background-color: var(--zw-paper);
    background-image:
        url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='280' height='280'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.2 0 0 0 0 0.15 0 0 0 0 0.08 0 0 0 0.1 0'/></filter><rect width='280' height='280' filter='url(%23n)'/></svg>");
    padding: 36px 80px 100px;
    overflow: hidden;
    box-sizing: border-box;
    font-family: 'Noto Sans SC', 'PingFang SC', sans-serif;
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
    animation: zw-fade-in 0.7s ease-out 0.1s both;
    text-shadow: 4px 4px 0 var(--zw-mustard);
    /* 像素锐化渲染 */
    -webkit-font-smoothing: none;
    -moz-osx-font-smoothing: grayscale;
}

.zw-title-bar {
    width: 180px;
    height: 10px;
    background-image: linear-gradient(90deg, var(--zw-terra) 20%, var(--zw-mustard) 20% 45%, var(--zw-moss) 45% 70%, var(--zw-dusty) 70%);
    image-rendering: pixelated;
    margin: 14px 0 18px;
    animation: zw-fade-in 0.6s ease-out 0.3s both;
}

.zw-subtitle-zh {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 22px;
    color: var(--zw-ink) !important;
    margin: 0 0 24px;
    letter-spacing: 4px;
    animation: zw-fade-in 0.6s ease-out 0.35s both;
    -webkit-font-smoothing: none;
}

.zw-desc {
    font-family: 'Zpix', 'Noto Sans SC', sans-serif;
    font-size: 14px;
    line-height: 1.9;
    color: var(--zw-ink-soft) !important;
    margin-bottom: 26px;
    max-width: 440px;
    animation: zw-fade-in 0.6s ease-out 0.45s both;
    -webkit-font-smoothing: none;
}

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

/* 粉色爪印 SVG：左按钮在前，右按钮在后 */
.nav-prev::before,
.nav-next::after {
    content: '';
    display: inline-block;
    width: 14px;
    height: 14px;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><ellipse cx="12" cy="15.5" rx="4" ry="3.2" fill="%23ff9eb3"/><ellipse cx="5.5" cy="10.5" rx="2" ry="2.4" fill="%23ff9eb3"/><ellipse cx="18.5" cy="10.5" rx="2" ry="2.4" fill="%23ff9eb3"/><ellipse cx="9" cy="5.5" rx="1.6" ry="2" fill="%23ff9eb3"/><ellipse cx="15" cy="5.5" rx="1.6" ry="2" fill="%23ff9eb3"/></svg>');
    background-repeat: no-repeat;
    background-size: contain;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="handwrite-title">Sweet Sweet Homeland</div>', unsafe_allow_html=True)

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
        st.sidebar.markdown("**📌 书签**")
        if st.sidebar.button("加入当前位置", key="bm_add", use_container_width=True):
            added = _add_bookmark(book_key, chapter_idx, current_page)
            st.toast("📌 已添加书签" if added else "此位置已有书签")
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

        # 顶部：时间 + 章节信息
        top_col1, top_col2 = st.columns([1, 1])
        with top_col1:
            st.markdown(f"**{chapter_titles[chapter_idx]}**")
        with top_col2:
            from datetime import timezone, timedelta
            now = datetime.now(timezone(timedelta(hours=8))).strftime("%H:%M")
            st.markdown(f'<div class="time-display">🕐 {now}</div>', unsafe_allow_html=True)

        # 进度条
        progress = (current_page + 1) / total_pages if total_pages > 0 else 1
        st.markdown(f"""
        <div class="progress-container">
            <div class="progress-fill" style="width: {progress * 100:.1f}%"></div>
        </div>
        """, unsafe_allow_html=True)

        # 阅读主题样式映射（背景 + 对比度好的字体颜色）
        theme_styles = {
            "深海蓝": "background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: #d4d4e0;",
            "暖光黄": "background: linear-gradient(135deg, #2c2416 0%, #3a2e1c 50%, #453622 100%); color: #e8d5b5;",
            "护眼绿": "background: linear-gradient(135deg, #1a261a 0%, #1e301e 50%, #223a22 100%); color: #c8dcc0;",
            "纯黑":   "background: #0e0e0e; color: #b0b0b0;",
        }
        current_theme = st.session_state.get("reading_theme", "深海蓝")
        fs = st.session_state.get("font_size", 18)
        theme_css = theme_styles.get(current_theme, theme_styles["深海蓝"])
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

        page_range = (
            f"第 {left_num}{f'-{right_num}' if right_num else ''} / {total_pages} 页"
            f" · 全书 {overall:.1f}%"
            f" · {_time_left}"
        )

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
            <style>
              body { margin: 0; background: transparent; }
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
                border-radius: 999px;
                background: rgba(255, 107, 107, 0.10);
                border: 1px solid rgba(255, 107, 107, 0.28);
                color: #ff9a9a;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
                letter-spacing: 0.3px;
                user-select: none;
                box-shadow: 0 1px 6px rgba(255, 107, 107, 0.10);
              }
              .rb-kbd-hint kbd {
                display: inline-block;
                min-width: 18px;
                padding: 1px 6px;
                border: 1px solid rgba(255, 154, 154, 0.45);
                border-radius: 5px;
                background: rgba(255, 154, 154, 0.12);
                color: #ffc7c7;
                font-size: 11px;
                font-family: inherit;
                line-height: 1.4;
                text-align: center;
                box-shadow: 0 1px 0 rgba(0,0,0,0.25), inset 0 -1px 0 rgba(255,154,154,0.25);
              }
              .rb-kbd-hint.rb-err {
                background: rgba(244, 67, 54, 0.12);
                border-color: rgba(244, 67, 54, 0.35);
                color: #ff8a80;
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
                    if (p._rb_kbd_v2) { setMsg('⌨ 键盘翻页已启用（← / →）', '#4caf50'); return; }
                    p._rb_kbd_v2 = true;
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
                    p.document.addEventListener('keydown', handler, true);
                    p.addEventListener('keydown', handler, true);
                    // 点击委托：HTML 导航按钮 → 隐藏 st.button
                    p.document.addEventListener('click', function(e) {
                        const btn = e.target.closest && e.target.closest('.nav-btn');
                        if (!btn) return;
                        e.preventDefault();
                        if (btn.classList.contains('nav-disabled')) return;
                        const action = btn.classList.contains('nav-prev') ? 'prev' : 'next';
                        clickHiddenBtn(action);
                    }, true);
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

        # 阅读主题
        if "reading_theme" not in st.session_state:
            st.session_state.reading_theme = "深海蓝"
        theme = st.sidebar.selectbox("阅读主题", ["深海蓝", "暖光黄", "护眼绿", "纯黑"], index=["深海蓝", "暖光黄", "护眼绿", "纯黑"].index(st.session_state.reading_theme))
        if theme != st.session_state.reading_theme:
            st.session_state.reading_theme = theme
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
        st.subheader("💬 与 AI 探讨本章内容")

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
                    st.error(f"大脑连接出现了一点小状况：{str(e)}")

    else:
        st.warning("书本解析失败，请确认文件是否损坏，或换一本书试试。")
else:
    # 日式编辑 zine 风欢迎页（全屏覆盖 + 内嵌上传器）
    st.markdown("""
    <div class="zine-welcome">
        <div class="zw-corner tl">[+]</div>
        <div class="zw-corner tr">[+]</div>
        <div class="zw-corner bl">[+]</div>
        <div class="zw-corner br">[+]</div>
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
                <p class="zw-desc">
                    在这里，每一本书都值得被深度对话。<br>
                    上传你的电子书，和 AI 一起开启阅读旅程。
                </p>
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
        <!-- HOW IT WORKS 3 步 -->
        <div class="zw-howto">
            <div class="zw-howto-title">
                <span>▶ HOW IT WORKS / 开始指南</span>
                <span class="zw-meter">■ ■ ■ □ □</span>
            </div>
            <div class="zw-steps">
                <div class="zw-step">
                    <div class="zw-step-num">01</div>
                    <div class="zw-step-icon">📤</div>
                    <div class="zw-step-label">上传电子书</div>
                    <div class="zw-step-sub">UPLOAD</div>
                </div>
                <div class="zw-step-arrow">&gt;</div>
                <div class="zw-step">
                    <div class="zw-step-num">02</div>
                    <div class="zw-step-icon">📖</div>
                    <div class="zw-step-label">选章节阅读</div>
                    <div class="zw-step-sub">READ</div>
                </div>
                <div class="zw-step-arrow">&gt;</div>
                <div class="zw-step">
                    <div class="zw-step-num">03</div>
                    <div class="zw-step-icon">💬</div>
                    <div class="zw-step-label">AI 深度对话</div>
                    <div class="zw-step-sub">CHAT</div>
                </div>
            </div>
        </div>
        <!-- 特性徽章 -->
        <div class="zw-features">
            <span class="zw-feature"><span class="ic">⌨</span> 键盘翻页</span>
            <span class="zw-feature"><span class="ic">📌</span> 书签收藏</span>
            <span class="zw-feature"><span class="ic">🎨</span> 主题字体自定义</span>
            <span class="zw-feature"><span class="ic">⏱</span> 剩余时间估算</span>
            <span class="zw-feature"><span class="ic">💾</span> 进度自动保存</span>
            <span class="zw-feature"><span class="ic">🤖</span> AI 共读</span>
        </div>
        <!-- 底部装饰条 -->
        <div class="zw-footer-strip">
            <span>PRESS UPLOAD TO BEGIN</span>
            <span class="hearts">♥ ♥ ♥</span>
            <span>SSH · №001 · 2026</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # 上传区：标签 + 上传器（中央居中）
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
