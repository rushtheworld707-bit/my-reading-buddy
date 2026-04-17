import re
import io
import os
import glob
import html
import tempfile
import zipfile
import chardet
from datetime import datetime

import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. 页面基础配置
st.set_page_config(page_title="嘟哒", layout="wide")

# 2. 全局自定义样式
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)
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
    color: #888;
    font-size: 13px;
    margin: 8px 0;
}

/* 时间显示 */
.time-display {
    text-align: right;
    color: #666;
    font-size: 13px;
    padding: 4px 8px;
}

/* ===== 猫耳朵翻页按钮 ===== */

/* 阅读行（3列）：列高度对齐，侧列居中 */
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3)) {
    align-items: stretch !important;
    gap: 2px !important;
}
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:first-child,
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:last-child {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* 公共猫耳底色 */
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:first-child button,
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:last-child button {
    width: 46px !important;
    height: 68px !important;
    background: linear-gradient(165deg,
        #fff5f8 0%, #ffdce8 35%, #ffb3c8 70%, #ff85a1 100%) !important;
    border: 2px solid #ffb3c8 !important;
    border-bottom: 3px solid #ff6b9d !important;
    color: #b03060 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    line-height: 1.6 !important;
    padding: 6px 2px !important;
    white-space: pre-wrap !important;
    text-align: center !important;
    box-shadow:
        inset 0 -14px 18px rgba(255,107,157,0.25),
        inset 0 4px 8px rgba(255,255,255,0.6),
        0 6px 18px rgba(255,100,140,0.3) !important;
    transition: all 0.25s cubic-bezier(.34,1.56,.64,1) !important;
    cursor: pointer !important;
}

/* 左耳：右上角突出，整体向左倾斜 */
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:first-child button {
    border-radius: 48% 28% 18% 18% / 60% 55% 18% 18% !important;
    transform: rotate(-13deg) !important;
}
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:first-child button:hover {
    transform: rotate(-13deg) translateY(-5px) scale(1.12) !important;
    box-shadow:
        inset 0 -14px 18px rgba(255,107,157,0.35),
        inset 0 4px 8px rgba(255,255,255,0.7),
        0 12px 28px rgba(255,100,140,0.55) !important;
}

/* 右耳：左上角突出，整体向右倾斜 */
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:last-child button {
    border-radius: 28% 48% 18% 18% / 55% 60% 18% 18% !important;
    transform: rotate(13deg) !important;
}
[data-testid="stHorizontalBlock"]:has([data-testid="column"]:nth-child(3))
    > [data-testid="column"]:last-child button:hover {
    transform: rotate(13deg) translateY(-5px) scale(1.12) !important;
    box-shadow:
        inset 0 -14px 18px rgba(255,107,157,0.35),
        inset 0 4px 8px rgba(255,255,255,0.7),
        0 12px 28px rgba(255,100,140,0.55) !important;
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
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="handwrite-title">Sweet Sweet Homeland</div>', unsafe_allow_html=True)

# 3. 侧边栏：上传文件（支持多种格式）
SUPPORTED_FORMATS = ['epub', 'txt', 'pdf', 'mobi', 'azw3']
uploaded_file = st.sidebar.file_uploader(
    "请上传一本电子书吧(๑•̀ㅂ•́)و✧",
    type=SUPPORTED_FORMATS,
    help="支持格式：EPUB、TXT、PDF、MOBI、AZW3"
)

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
        chapter_idx = st.sidebar.selectbox(
            "选择章节",
            range(len(chapters)),
            format_func=lambda x: chapter_titles[x]
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

        # --- 阅读界面 ---

        # 顶部：时间 + 章节信息
        top_col1, top_col2 = st.columns([1, 1])
        with top_col1:
            st.markdown(f"**{chapter_titles[chapter_idx]}**")
        with top_col2:
            now = datetime.now().strftime("%H:%M")
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

        # 双页展示：当前页 = 左页，下一页 = 右页
        left_idx  = current_page
        right_idx = current_page + 1 if current_page + 1 < total_pages else None

        left_num = left_idx + 1
        right_num = right_idx + 1 if right_idx is not None else ""

        left_html  = _to_html(pages[left_idx])
        right_html = (_to_html(pages[right_idx]) if right_idx is not None
                      else '<p style="opacity:0.3; text-align:center; text-indent:0;">— 本章完 —</p>')

        book_html = f'''
        <div class="book-spread" style="{theme_css} font-size: {fs}px;">
            <div class="book-page book-page-left">
                {left_html}
                <div class="page-num">{left_num}</div>
            </div>
            <div class="book-page book-page-right">
                {right_html}
                <div class="page-num">{right_num}</div>
            </div>
        </div>
        '''

        # 猫耳翻页 + 书页：三列布局，两耳居中贴书侧
        ear_l, book_col, ear_r = st.columns([1, 16, 1])
        with ear_l:
            if current_page > 0:
                if st.button("上\n一\n页", key="prev", use_container_width=True):
                    st.session_state[page_key] = max(0, current_page - 2)
                    st.rerun()
        with book_col:
            st.markdown(book_html, unsafe_allow_html=True)
        with ear_r:
            if current_page < total_pages - 1:
                if st.button("下\n一\n页", key="next", use_container_width=True):
                    st.session_state[page_key] = min(total_pages - 1, current_page + 2)
                    st.rerun()

        # 页码指示
        chapter_page_counts = [len(split_into_pages(ch["text"])) for ch in chapters]
        total_all_pages = sum(chapter_page_counts)
        read_pages = sum(chapter_page_counts[:chapter_idx]) + current_page + 1
        overall = read_pages / total_all_pages * 100 if total_all_pages > 0 else 0
        st.markdown(
            f'<div class="page-indicator">第 {left_num}{f"-{right_num}" if right_num else ""}'
            f' / {total_pages} 页 · 全书 {overall:.1f}%</div>',
            unsafe_allow_html=True,
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
    # 欢迎页面
    st.markdown("""
    <div class="welcome-box">
        <div class="welcome-cat">🐱</div>
        <div class="welcome-title">欢迎来到深度共读伴侣</div>
        <div class="welcome-desc">
            在这里，每一本书都值得被深度对话<br>
            上传你的电子书，开启属于你的共读之旅
        </div>
        <div class="welcome-formats">
            <span class="format-tag">EPUB</span>
            <span class="format-tag">TXT</span>
            <span class="format-tag">PDF</span>
            <span class="format-tag">MOBI</span>
            <span class="format-tag">AZW3</span>
        </div>
        <div class="welcome-hint">
            <span>← 点击左侧上传电子书开始</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
