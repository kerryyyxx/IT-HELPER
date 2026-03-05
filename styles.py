import streamlit as st


def apply_styles():
    st.markdown("""
        <style>
        /* 1. 侧边栏：胶囊按钮美化 */
        [data-testid="stSidebarNav"] {display: none;}
        [data-testid="stSidebarContent"] { background-color: #f8f9fa; padding: 10px; }
        div.stButton > button {
            width: 100% !important;
            height: 52px !important;
            border-radius: 12px !important;
            text-align: left !important;
            padding: 0 20px !important;
            border: none !important;
            transition: 0.3s;
        }
        div.stButton > button[kind="primary"] {
            background-color: #e8f0fe !important;
            color: #1a73e8 !important;
            font-weight: 600 !important;
        }

        /* 2. 核心：防止遮挡的“空气垫” */
        .main .block-container {
            padding-bottom: 220px !important; 
        }

        /* 3. 输入框：大尺寸+居中稳定性 */
        [data-testid="stChatInput"] {
            border-radius: 15px !important;
            box-shadow: 0 -4px 20px rgba(0,0,0,0.1) !important;
            padding: 10px !important;
        }
        [data-testid="stChatInput"] textarea {
            font-size: 17px !important;
            min-height: 100px !important;
        }

        /* 4. 老师讲内容：高亮黄色背景 */
        .teacher-note-box {
            background-color: #fff9c4 !important;
            border-left: 6px solid #fbc02d !important;
            padding: 15px !important;
            margin: 15px 0 !important;
            border-radius: 8px;
            color: #333 !important;
            font-size: 15px !important;
            line-height: 1.6;
        }

        /* 5. 修正 Streamlit 默认容器间距 */
        .stTabs [data-baseweb="tab-list"] { gap: 20px; }
        </style>
    """, unsafe_allow_html=True)