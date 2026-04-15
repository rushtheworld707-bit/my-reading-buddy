import streamlit as st
from ebooklib import epub
from bs4 import BeautifulSoup
import io
from openai import OpenAI

# 1. 页面基础配置
st.set_page_config(page_title="深度阅读伴侣", layout="wide")
st.title("📚 深度共读伴侣")

# 2. 侧边栏：上传文件
uploaded_file = st.sidebar.file_uploader("上传你的 Epub 电子书", type=['epub'])

# 3. 解析 Epub 电子书的函数
@st.cache_data
def extract_text_from_epub(file_bytes):
    try:
        book = epub.read_epub(io.BytesIO(file_bytes))
        chapters = []
        for item in book.get_items():
            if item.get_type() == 9: # 9 代表 ITEM_DOCUMENT
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                text = soup.get_text(separator='\n\n', strip=True)
                if len(text) > 50: # 过滤掉极短的废话或空白页
                    chapters.append(text)
        return chapters
    except Exception as e:
        return None

# 4. 主逻辑控制
if uploaded_file:
    chapters = extract_text_from_epub(uploaded_file.getvalue())
    
    if chapters:
        # 选择章节
        chapter_idx = st.sidebar.selectbox("选择章节", range(len(chapters)), format_func=lambda x: f"第 {x+1} 章节")
        current_text = chapters[chapter_idx]
        
        # 主界面：显示正文（使用折叠面板，让页面更清爽）
        with st.expander("📖 展开阅读当前章节正文", expanded=False):
            st.write(current_text)
            
        st.divider()
        st.subheader("💬 与 AI 探讨本章内容")
        
        # --- 核心：对话逻辑 ---
        
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
                    # 建立连接
                    client = OpenAI(
                        api_key=st.secrets["ARK_API_KEY"],
                        base_url="https://ark.cn-beijing.volces.com/api/v3",
                    )
                    
                    # 组织发送给AI的内容 (截取当前章节前1200字作为语境)
                    context_msg = f"你是一个博学的共读伙伴，擅长从哲学、生物学或行为因果的角度深度分析文本。正在阅读的内容：\n{current_text[:1200]}\n\n读者感悟：{prompt}"
                    
                    # 发送请求
                    completion = client.chat.completions.create(
                        model=st.secrets["ARK_MODEL_ID"],
                        messages=[
                            {"role": "system", "content": "你是一个高水平的阅读助手，擅长理解复杂的人性、行为逻辑以及具有宏大设定的文学作品。"},
                            {"role": "user", "content": context_msg}
                        ],
                    )
                    
                    # 获取并展示 AI 的回答
                    response_text = completion.choices[0].message.content
                    st.write(response_text)
                    
                    # 把 AI 的回答存入历史记录，方便它记住上下文
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    # 如果网络波动或其他问题，温柔地提示
                    st.error(f"大脑连接出现了一点小状况：{str(e)}")
                    
    else:
        st.warning("书本解析失败，请确认文件是否损坏，或换一本书试试。")
else:
    # 刚进网页时的默认欢迎语
    st.info("👋 欢迎！上传一本 Epub （比如《冰与火之歌》或《行为》）开启属于你的共读之旅。")