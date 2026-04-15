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
st.set_page_config(page_title="深度阅读伴侣", layout="wide")

# 2. 全局自定义样式
st.markdown("""
<style>
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
.welcome-box {
    text-align: center;
    padding: 80px 40px;
    color: #ccc;
}
.welcome-box h1 {
    font-size: 48px;
    margin-bottom: 8px;
}
.welcome-box p {
    font-size: 18px;
    color: #888;
}
</style>
""", unsafe_allow_html=True)

st.title("📚 深度共读伴侣")

# 3. 侧边栏：上传文件（支持多种格式）
SUPPORTED_FORMATS = ['epub', 'txt', 'pdf', 'mobi', 'azw3']
uploaded_file = st.sidebar.file_uploader(
    "上传你的电子书",
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

@st.cache_data
def extract_text_from_mobi(file_bytes):
    try:
        import mobi
        with tempfile.NamedTemporaryFile(suffix='.mobi', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            tempdir, filepath = mobi.extract(tmp_path)
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n\n', strip=True)
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
        finally:
            os.unlink(tmp_path)
    except Exception:
        return None

@st.cache_data
def extract_text_from_azw3(file_bytes):
    try:
        import mobi
        with tempfile.NamedTemporaryFile(suffix='.azw3', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            tempdir, filepath = mobi.extract(tmp_path)
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n\n', strip=True)
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
        finally:
            os.unlink(tmp_path)
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
if uploaded_file:
    chapters = extract_chapters(uploaded_file.getvalue(), uploaded_file.name)

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

        # 阅读区域
        page_content = pages[current_page] if current_page < total_pages else pages[-1]
        st.markdown(f'<div class="reading-area">{page_content}</div>', unsafe_allow_html=True)

        # 页码显示
        st.markdown(f'<div class="page-indicator">第 {current_page + 1} / {total_pages} 页</div>', unsafe_allow_html=True)

        # 翻页按钮：猫猫头
        nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])

        with nav_col1:
            if current_page > 0:
                if st.button("🐱", key="prev", help="上一页"):
                    st.session_state[page_key] = current_page - 1
                    st.rerun()
                st.markdown('<div class="cat-label">上一页</div>', unsafe_allow_html=True)

        with nav_col2:
            # 中间留白，显示整体阅读进度
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

        # 侧边栏：阅读设置
        st.sidebar.divider()
        st.sidebar.markdown("**阅读设置**")
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
        if prompt := st.chat_input("输入你的感悟，聊聊这段吧..."):

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
else:
    # 欢迎页面
    st.markdown("""
    <div class="welcome-box">
        <h1>🐱</h1>
        <p>欢迎来到深度共读伴侣</p>
        <p style="font-size: 15px; margin-top: 12px;">
            上传一本电子书（支持 EPUB、TXT、PDF、MOBI、AZW3 格式）<br>
            开启属于你的共读之旅
        </p>
    </div>
    """, unsafe_allow_html=True)
