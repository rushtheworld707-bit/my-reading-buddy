import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
import io
import os
import tempfile
import chardet
from datetime import datetime
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
/* 整体阅读区域 */
.reading-area {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 40px 48px;
    margin: 10px 0;
    min-height: 420px;
    color: #e0e0e0;
    font-size: 18px;
    line-height: 2;
    letter-spacing: 0.5px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    white-space: pre-wrap;
    word-wrap: break-word;
    position: relative;
}

/* 页码标签 */
.page-indicator {
    text-align: center;
    color: #888;
    font-size: 14px;
    margin: 8px 0;
}

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

/* 时间显示 */
.time-display {
    text-align: right;
    color: #666;
    font-size: 13px;
    padding: 4px 8px;
}

/* 猫猫按钮动画 */
@keyframes wiggle {
    0% { transform: rotate(0deg); }
    25% { transform: rotate(-15deg); }
    50% { transform: rotate(15deg); }
    75% { transform: rotate(-10deg); }
    100% { transform: rotate(0deg); }
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}

.cat-btn {
    font-size: 48px;
    cursor: pointer;
    display: inline-block;
    transition: transform 0.2s;
    user-select: none;
}
.cat-btn:hover {
    animation: wiggle 0.5s ease-in-out infinite;
}

/* 猫猫按钮下方文字 */
.cat-label {
    text-align: center;
    color: #888;
    font-size: 12px;
    margin-top: -4px;
}

/* 翻页导航栏 */
.nav-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    margin: 4px 0;
}
.nav-btn-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
}
.nav-center {
    text-align: center;
    color: #666;
    font-size: 13px;
    flex: 1;
}

/* 隐藏 Streamlit 默认按钮样式，美化 */
.stButton > button {
    background: transparent !important;
    border: 2px solid #333 !important;
    border-radius: 50% !important;
    width: 72px !important;
    height: 72px !important;
    font-size: 36px !important;
    padding: 0 !important;
    transition: all 0.3s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.stButton > button:hover {
    border-color: #e94560 !important;
    background: rgba(233, 69, 96, 0.1) !important;
    animation: bounce 0.6s ease-in-out infinite;
}

/* 侧边栏美化 */
.sidebar-title {
    font-size: 14px;
    color: #aaa;
    margin-bottom: 4px;
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
    /* 阅读区域：缩小内边距，调整字体 */
    .reading-area {
        padding: 20px 16px;
        font-size: 16px;
        line-height: 1.8;
        min-height: 300px;
        border-radius: 12px;
    }

    /* 按钮缩小 */
    .stButton > button {
        width: 56px !important;
        height: 56px !important;
        font-size: 28px !important;
    }

    /* 欢迎页面 */
    .welcome-box {
        padding: 40px 16px;
    }
    .welcome-cat {
        font-size: 56px;
    }
    .welcome-title {
        font-size: 22px;
    }
    .welcome-desc {
        font-size: 14px;
    }
    .welcome-formats {
        gap: 8px;
    }
    .format-tag {
        padding: 4px 12px;
        font-size: 12px;
    }

    /* 时间显示 */
    .time-display {
        font-size: 12px;
    }

    /* 隐藏侧边栏默认展开，移动端用汉堡菜单 */
    .css-1d391kg, [data-testid="stSidebar"] {
        min-width: 0px;
    }

    /* 标题缩小 */
    h1 {
        font-size: 24px !important;
    }
    h2, .stSubheader {
        font-size: 18px !important;
    }
}

/* 小屏手机（<480px） */
@media (max-width: 480px) {
    .reading-area {
        padding: 16px 12px;
        font-size: 15px;
        line-height: 1.75;
        min-height: 250px;
        border-radius: 8px;
    }

    .stButton > button {
        width: 48px !important;
        height: 48px !important;
        font-size: 24px !important;
    }

    .cat-label {
        font-size: 10px;
    }

    .page-indicator {
        font-size: 12px;
    }
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

@st.cache_data
def extract_text_from_epub(file_bytes):
    try:
        book = epub.read_epub(io.BytesIO(file_bytes))
        chapters = []
        for item in book.get_items():
            if item.get_type() == 9:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                text = soup.get_text(separator='\n\n', strip=True)
                if len(text) > 50:
                    chapters.append(text)
        return chapters
    except Exception:
        return None

@st.cache_data
def extract_text_from_txt(file_bytes):
    try:
        detected = chardet.detect(file_bytes)
        encoding = detected.get('encoding', 'utf-8') or 'utf-8'
        text = file_bytes.decode(encoding, errors='replace')

        raw_chapters = text.split('\n\n\n')
        chapters = []
        current_chunk = ""
        for part in raw_chapters:
            part = part.strip()
            if not part:
                continue
            current_chunk += part + "\n\n"
            if len(current_chunk) > 2000:
                chapters.append(current_chunk.strip())
                current_chunk = ""
        if current_chunk.strip():
            chapters.append(current_chunk.strip())

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
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                current_chunk += page_text + "\n\n"
                if len(current_chunk) > 3000:
                    chapters.append(current_chunk.strip())
                    current_chunk = ""
        if current_chunk.strip():
            chapters.append(current_chunk.strip())
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

def _text_from_html_files(file_list):
    """从一组 HTML/XHTML 文件中提取文本，返回章节列表"""
    chapters = []
    for fpath in sorted(file_list):
        content = _read_file_with_auto_encoding(fpath)
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text(separator='\n\n', strip=True)
        if len(text) > 50:
            chapters.append(text)
    return chapters if chapters else None

def _extract_mobi_content(file_bytes, suffix):
    """MOBI/AZW3 通用提取逻辑"""
    import mobi
    import glob
    import zipfile
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
            result = _text_from_html_files(xhtml_files)
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
                        result = _text_from_html_files(xhtml_files)
                        if result:
                            return result
            except Exception:
                pass

        # 策略4：直接读取主文件作为 HTML（老式 MOBI）
        if os.path.isfile(filepath):
            content = _read_file_with_auto_encoding(filepath)
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n\n', strip=True)
            # 检查是否大部分是可读文本（非乱码）
            cjk_count = sum(1 for c in text[:500] if '\u4e00' <= c <= '\u9fff')
            latin_count = sum(1 for c in text[:500] if c.isalpha())
            if cjk_count > 20 or latin_count > 100:
                chapters = []
                current_chunk = ""
                for para in text.split('\n\n'):
                    para = para.strip()
                    if not para:
                        continue
                    current_chunk += para + "\n\n"
                    if len(current_chunk) > 3000:
                        chapters.append(current_chunk.strip())
                        current_chunk = ""
                if current_chunk.strip():
                    chapters.append(current_chunk.strip())
                return chapters if chapters else None

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

# 5. 主逻辑控制
# 将上传文件缓存到 session_state，防止翻页时丢失
if uploaded_file:
    st.session_state.file_bytes = uploaded_file.getvalue()
    st.session_state.file_name = uploaded_file.name

has_file = "file_bytes" in st.session_state and st.session_state.file_bytes
if has_file:
    chapters = extract_chapters(st.session_state.file_bytes, st.session_state.file_name)

    if chapters:
        # 侧边栏：章节选择
        chapter_idx = st.sidebar.selectbox(
            "选择章节",
            range(len(chapters)),
            format_func=lambda x: f"第 {x+1} 章"
        )
        current_text = chapters[chapter_idx]

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
            st.markdown(f"**第 {chapter_idx + 1} 章**")
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

        # 阅读主题样式映射
        theme_styles = {
            "深海蓝": "background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: #e0e0e0;",
            "暖光黄": "background: linear-gradient(135deg, #3e2f1a 0%, #4a3728 50%, #5c4433 100%); color: #f5e6c8;",
            "护眼绿": "background: linear-gradient(135deg, #1a2e1a 0%, #1e3e21 50%, #1a4a2e 100%); color: #d0e8c8;",
            "纯黑":   "background: #0a0a0a; color: #c0c0c0;",
        }
        current_theme = st.session_state.get("reading_theme", "深海蓝")
        fs = st.session_state.get("font_size", 18)
        theme_css = theme_styles.get(current_theme, theme_styles["深海蓝"])

        # 阅读区域
        page_content = pages[current_page] if current_page < total_pages else pages[-1]
        st.markdown(f'<div class="reading-area" style="{theme_css} font-size: {fs}px;">{page_content}</div>', unsafe_allow_html=True)

        # 页码显示
        st.markdown(f'<div class="page-indicator">第 {current_page + 1} / {total_pages} 页</div>', unsafe_allow_html=True)

        # 翻页按钮：猫猫头，紧贴两端
        nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])

        with nav_col1:
            if current_page > 0:
                if st.button("🐱", key="prev", help="上一页"):
                    st.session_state[page_key] = current_page - 1
                    st.rerun()
                st.markdown('<div class="cat-label">上一页</div>', unsafe_allow_html=True)
            else:
                st.write("")  # 占位

        with nav_col2:
            total_all_pages = sum(len(split_into_pages(ch)) for ch in chapters)
            read_pages = sum(len(split_into_pages(chapters[i])) for i in range(chapter_idx)) + current_page + 1
            overall = read_pages / total_all_pages * 100 if total_all_pages > 0 else 0
            st.markdown(f'<div style="text-align:center; color:#666; font-size:13px;">全书进度 {overall:.1f}%</div>', unsafe_allow_html=True)

        with nav_col3:
            if current_page < total_pages - 1:
                if st.button("😺", key="next", help="下一页"):
                    st.session_state[page_key] = current_page + 1
                    st.rerun()
                st.markdown('<div class="cat-label">下一页</div>', unsafe_allow_html=True)
            else:
                st.write("")  # 占位

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
                    context_msg = f"你是一个博学的共读伙伴，擅长从哲学、生物学或行为因果的角度深度分析文本。正在阅读的内容：\n{page_content[:1200]}\n\n读者感悟：{prompt}"

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
elif not has_file:
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
