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
    # 增加 .strip() 自动删掉你粘贴时可能带入的隐形空格
    api_key = st.secrets["GEMINI_API_KEY"].strip()
    genai.configure(api_key=api_key)
    # 暂时删掉这里 model 的定义，我们挪到下面动态生成，防止 404
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
        # --- 对话交互区 (增强型) ---
        if prompt := st.chat_input("想聊聊这段吗？"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                success = False
                # 尝试多个暗号：1.5版、最新版、甚至是经典的 Pro 版
                for model_name in ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']:
                    try:
                        current_model = genai.GenerativeModel(model_name)
                        context_prompt = f"你是一个陪读伙伴。当前书的内容：\n{current_text[:1000]}\n\n读者问：{prompt}"
                        
                        response = current_model.generate_content(context_prompt)
                        ai_reply = response.text
                        st.write(ai_reply)
                        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                        success = True
                        break 
                    except Exception:
                        continue 
                
                if not success:
                    st.error("⚠️ 所有的 AI 通道都报了 404。这通常是 Google 服务器的地区性同步延迟，建议你去 Google AI Studio 重新生成一个新的 Key 试试。")