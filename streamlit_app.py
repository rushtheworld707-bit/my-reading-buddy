import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
import io
import google.generativeai as genai

# 1. 页面基础配置
st.set_page_config(page_title="我的共读空间", layout="centered")

# 2. 接入 Gemini 大脑 (增强型)
if "GEMINI_API_KEY" in st.secrets:
    # 彻底清理可能存在的任何隐形字符
    raw_key = st.secrets["GEMINI_API_KEY"].replace('"', '').replace("'", "").strip()
    genai.configure(api_key=raw_key)
else:
    st.error("❌ 未在 Secrets 中发现 API Key，请检查配置。")

# 3. 样式优化
st.markdown("""
    <style>
    .stApp { background-color: #FDFCFB; }
    .book-content {
        background: white; padding: 24px; border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        font-size: 19px; line-height: 1.8; color: #2C3E50;
        margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# 4. 侧边栏
with st.sidebar:
    st.title("📚 阅读配置")
    uploaded_file = st.file_uploader("上传 Epub 电子书", type="epub")
    st.divider()
    # 调试模式：看看大脑能不能认出模型
    if st.checkbox("开启大脑自检"):
        try:
            models = [m.name for m in genai.list_models()]
            st.write("可用模型列表:", models)
        except Exception as e:
            st.error(f"自检失败: {e}")

# 5. 核心逻辑：解析与展示
if uploaded_file:
    book = epub.read_epub(io.BytesIO(uploaded_file.read()))
    chapters = []
    for item in book.get_items_of_type(9):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text = soup.get_text().strip()
        if len(text) > 100:
            chapters.append(text)
    
    if chapters:
        chapter_idx = st.select_slider("当前进度", options=range(len(chapters)), value=0)
        current_text = chapters[chapter_idx]
        st.markdown(f'<div class="book-content">{current_text[:3000]}</div>', unsafe_allow_html=True)

        st.divider()
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.write(m["content"])

        if prompt := st.chat_input("聊聊这段吧..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                response_text = ""
                # 为了绝对安全，我们这次把 "models/" 前缀也加上，和自检列表保持100%一致
                test_models = [
                    'models/gemini-2.5-flash', 
                    'models/gemini-2.0-flash', 
                    'models/gemini-1.5-flash', 
                    'models/gemini-pro'
                ]
                
                success = False
                error_logs = [] # 专门用来收集真实的报错原因
                
                for m_name in test_models:
                    try:
                        model = genai.GenerativeModel(m_name)
                        context = f"你是一个博学的共读伙伴。正在阅读的内容：\n{current_text[:1200]}\n\n读者感悟：{prompt}"
                        
                        response = model.generate_content(context)
                        response_text = response.text
                        success = True
                        break 
                    except Exception as e:
                        # 如果失败，把真实的错误记录下来
                        error_logs.append(f"【{m_name}】真实报错: {str(e)}")
                        continue 
                
                if success:
                    st.write(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    # 如果全失败了，把底裤都脱下来给我们看！
                    st.error("⚠️ 核心连接失败！请把下面这个灰色的错误代码截图发给你的助手：")
                    for err in error_logs:
                        st.code(err)
           
                if success:
                    st.write(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                else:
                    st.error("⚠️ 大脑连接依然受阻。可能是该地区 API 访问受限，或者 Google Cloud 项目正在同步中，请 5 分钟后再试。")
    else:
        st.warning("书本解析失败，请换一本书试试。")
else:
    st.info("👋 欢迎！上传一本 Epub 开启共读之旅。")