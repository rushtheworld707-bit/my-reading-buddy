import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
import io

# 页面配置：为了适配手机，我们选 centered
st.set_page_config(page_title="我们的共读空间", layout="centered")

# --- 优雅的移动端样式 ---
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .book-content {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        font-size: 18px;
        line-height: 1.8;
        color: #2C3E50;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 侧边栏：多模型切换与文件上传 ---
with st.sidebar:
    st.title("📚 阅读配置")
    ai_partner = st.selectbox(
        "选择你的共读伙伴",
        ["Gemini (默认)", "ChatGPT (OpenAI)", "Claude (Anthropic)", "豆包 (火山引擎)"]
    )
    st.info(f"当前模式：{ai_partner}")
    
    st.divider()
    uploaded_file = st.file_uploader("上传 Epub 电子书", type="epub")

# --- 核心阅读逻辑 ---
if uploaded_file:
    # 解析 Epub
    book = epub.read_epub(io.BytesIO(uploaded_file.read()))
    chapters = []
    for item in book.get_items_of_type(9):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        chapters.append(soup.get_text())
    
    chapter_idx = st.slider("章节进度", 0, len(chapters)-1, 0)
    
    # 展示正文
    st.markdown(f'<div class="book-content">{chapters[chapter_idx]}</div>', unsafe_allow_html=True)

    # --- 对话交互区 ---
    st.divider()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    if prompt := st.chat_input("读到这里，有什么想和我聊的？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # 这里是 AI 的回应预留位
        with st.chat_message("assistant"):
            st.write(f"（{ai_partner} 正在深度解析这段文字...）")
            # 提示：具体的 API 接入逻辑我们等部署后再配置 Secrets
else:
    st.info("👋 欢迎！请在左侧上传一本 Epub，我们开始今天的精神漫游。")
