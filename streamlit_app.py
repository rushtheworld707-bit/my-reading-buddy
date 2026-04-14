import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
import io
import google.generativeai as genai

# 1. 页面基础配置：适配移动端
st.set_page_config(page_title="我的共读空间", layout="centered")

# 2. 接入 Gemini 大脑
# 只要你在 Streamlit Secrets 里填了 GEMINI_API_KEY，这里就会自动通电
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("❌ 未在 Secrets 中发现 API Key，请检查配置。")

# 3. 移动端专属样式 (CSS)
st.markdown("""
    <style>
    .stApp { background-color: #FDFCFB; }
    .book-content {
        background: white; 
        padding: 24px; 
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        font-size: 19px; 
        line-height: 1.8; 
        color: #2C3E50;
        font-family: 'PingFang SC', 'Microsoft YaHei', serif;
        margin-bottom: 30px;
    }
    .stChatMessage { border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# 4. 侧边栏：文件管理
with st.sidebar:
    st.title("📚 阅读配置")
    uploaded_file = st.file_uploader("上传 Epub 电子书", type="epub")
    if uploaded_file:
        st.success("图书已载入")
    st.divider()
    st.caption("建议：读到触动处，直接在下方开启对话。")

# 5. 核心逻辑：解析与展示
if uploaded_file:
    # 读取 Epub
    book = epub.read_epub(io.BytesIO(uploaded_file.read()))
    chapters = []
    
    # 提取文字内容
    for item in book.get_items_of_type(9):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text = soup.get_text().strip()
        if len(text) > 100:  # 过滤掉太短的版权页或目录
            chapters.append(text)
    
    # 章节选择滑动条
    if chapters:
        chapter_idx = st.select_slider("当前进度", options=range(len(chapters)), value=0)
        current_text = chapters[chapter_idx]
        
        # 显示正文（手机端为了性能，展示前 3000 字）
        display_text = current_text[:3000] + ("..." if len(current_text) > 3000 else "")
        st.markdown(f'<div class="book-content">{display_text}</div>', unsafe_allow_html=True)

        # 6. 对话交互区
        st.divider()
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # 显示历史对话
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.write(m["content"])

        # 输入框：与 AI 探讨
        if prompt := st.chat_input("想聊聊这段吗？"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                # 构造包含上下文的指令
                # 我们告诉 AI：先看这一段书，再回答读者的问题
                context_prompt = f"""
                你是一个博学且富有洞察力的共读伙伴。
                以下是读者正在阅读的内容片段：
                ---
                {current_text[:1200]}
                ---
                读者的感悟或问题是："{prompt}"
                请结合文本内容，给出一个深刻、有趣且富有启发性的回应。
                """
                
                try:
                    response = model.generate_content(context_prompt)
                    ai_reply = response.text
                    st.write(ai_reply)
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                except Exception as e:
                    st.error(f"大脑离线中: {e}")
    else:
        st.warning("未能识别出书本内容，请尝试换一本 Epub 试试？")

else:
    st.info("👋 欢迎来到私人共读空间。请点击左侧上传一本 Epub，我们一起开启精神漫游。")