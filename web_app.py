import streamlit as st
from database import SchoolAIDatabase
from openai import OpenAI
import httpx

# --- 1. 配置 ---
st.set_page_config(page_title="信息技术 AI 云助手", layout="wide")
db = SchoolAIDatabase()

client = OpenAI(
    api_key=st.secrets["API_KEY"], 
    base_url=st.secrets["BASE_URL"],
    http_client=httpx.Client(verify=False)
)
SYSTEM_PROMPT = "你是一位资深信息技术老师。回答学生问题时，请先肯定他们的思考，多用引导式提问，解释逻辑而非单纯提供代码，鼓励他们动手实践。"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
if "current_chat" not in st.session_state:
    st.session_state.current_chat = []

# --- 2. 展示组件 ---
def show_list_history(history, prefix):
    if not history:
        st.info("目前还没有记录。")
        return
    history_rev = list(reversed(history))
    options = [f"#{len(history_rev)-i} | {t[5:16]} | {q[:12]}..." for i, (q, a, t) in enumerate(history_rev)]
    l_col, r_col = st.columns([1, 2.5])
    with l_col:
        sel = st.radio("选择记录", options, label_visibility="collapsed", key=f"{prefix}_radio")
        idx = options.index(sel)
    with r_col:
        q, a, t = history_rev[idx]
        st.markdown(f"##### 🕒 时间: {t}")
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"): st.markdown(a)

# --- 3. 弹窗组件 (修复点：确保这些函数在主循环之前定义) ---

@st.dialog("🔑 找回密码")
def forgot_pwd_dialog():
    uname = st.text_input("用户名", key="f_u")
    if uname:
        q = db.get_user_security_q(uname)
        if q:
            st.info(f"密保问题：{q}")
            ans = st.text_input("答案", key="f_a")
            new_p = st.text_input("新密码", type="password", key="f_p")
            if st.button("验证重置", key="f_b"):
                if db.verify_security(uname, q, ans):
                    db.update_password(uname, new_p)
                    st.success("成功！请重新登录。")
                else: st.error("答案错误")

@st.dialog("📜 学生档案", width="large")
def show_student_profile(username, name):
    st.write(f"### {name} 的学习档案")
    t1, t2 = st.tabs(["💬 对话记录", "📥 课件下载"])
    with t1:
        history = db.get_chat_history(username)
        show_list_history(history, f"profile_hist_{username}")
    with t2:
        dls = db.get_student_downloads(username)
        if dls:
            for fn, dt in dls: st.write(f"✅ {fn}  *(时间: {dt})*")
        else: st.info("该生暂无下载记录")

@st.dialog("🔑 管理员修改密码")
def admin_reset_pwd_dialog(username, name):
    st.write(f"正在重置学生 **{name}** 的密码")
    new_p = st.text_input("设置新密码", type="password", key=f"adm_pw_input_{username}")
    if st.button("确认修改", key=f"adm_pw_btn_{username}"):
        db.update_password(username, new_p)
        st.success(f"学生 {name} 的密码已重置！")

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🍀 账户中心")
    if not st.session_state.logged_in:
        t1, t2 = st.tabs(["登录", "注册"])
        with t1:
            u, p = st.text_input("用户名", key="l_u"), st.text_input("密码", type="password", key="l_p")
            if st.button("登录", use_container_width=True, key="l_b"):
                res = db.login(u, p)
                if res:
                    st.session_state.logged_in = True
                    st.session_state.user_info = {"username": u, "role": res[0], "name": res[1]}
                    st.rerun()
            if st.button("忘记密码？", key="f_link"): forgot_pwd_dialog()
        with t2:
            nu, nn = st.text_input("新用户名", key="r_u"), st.text_input("真实姓名", key="r_n")
            c1, c2 = st.columns(2)
            g_v = c1.text_input("级", key="r_g")
            c_v = c2.text_input("班", key="r_c")
            np, nq, na = st.text_input("密码", type="password", key="r_p"), st.text_input("密保问题", key="r_q"), st.text_input("答案", key="r_a")
            if st.button("提交注册", key="reg_b"):
                db.register_user(nu, np, nn, f"{g_v}级{c_v}班", nq, na, "student")
                st.success("注册成功！")
    else:
        st.success(f"在线：{st.session_state.user_info['name']}")
        if st.button("退出登录", use_container_width=True, key="logout_b"):
            st.session_state.logged_in = False; st.session_state.current_chat = []; st.rerun()

# --- 5. 主界面 ---
if not st.session_state.logged_in:
    st.info("👋 欢迎！请先在左侧登录。")
else:
    user = st.session_state.user_info
    
    # 【学生端逻辑保持沉底优化】
    if user['role'] == 'student':
        t_chat, t_hist, t_file = st.tabs(["💬 AI 咨询", "📚 历史回顾", "📥 课件下载"])
        with t_chat:
            h_c1, h_c2 = st.columns([5, 1])
            h_c1.subheader("💡 探索信息技术")
            if h_c2.button("🧹 清空"):
                st.session_state.current_chat = []; st.rerun()
            for m in st.session_state.current_chat:
                with st.chat_message(m["role"]): st.markdown(m["content"])
        with t_hist: show_list_history(db.get_chat_history(user['username']), "stu_hist")
        with t_file:
            @st.fragment(run_every=5)
            def refresh_mats():
                mats = db.get_all_materials()
                for mid, fn, ut in mats:
                    c_n, c_d = st.columns([3, 1])
                    c_n.write(f"📄 {fn}")
                    _, data = db.get_material_data(mid)
                    if c_d.download_button("下载", data=data, file_name=fn, key=f"d_{mid}"):
                        db.log_download(user['username'], mid)
            refresh_mats()
        
        # 学生端输入逻辑
        if prompt := st.chat_input("在此输入你的疑问..."):
            st.session_state.current_chat.append({"role": "user", "content": prompt})
            st.rerun()
        if st.session_state.current_chat and st.session_state.current_chat[-1]["role"] == "user":
            with t_chat:
                with st.chat_message("assistant"):
                    res_p, full_res = st.empty(), ""
                    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.current_chat
                    stream = client.chat.completions.create(model="ep-20260224161941-nqw6c", messages=msgs, stream=True)
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            full_res += chunk.choices[0].delta.content
                            res_p.markdown(full_res + "▌")
                    res_p.markdown(full_res)
                    db.save_chat(user['username'], st.session_state.current_chat[-1]["content"], full_res)
                    st.session_state.current_chat.append({"role": "assistant", "content": full_res})
                    st.rerun()

    # 【老师端逻辑修复】
    elif user['role'] == 'admin':
        t_m, t_f = st.tabs(["👨‍🏫 班级看板", "📤 课件管理"])
        
        with t_f:
            st.subheader("📤 发布课件")
            f = st.file_uploader("上传文件", key="adm_f")
            if f and st.button("确认发布", key="adm_up"):
                db.upload_material(f.name, f.read()); st.success("已发布"); st.rerun()
            st.divider()
            for mid, fn, ut in db.get_all_materials():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"📄 {fn}"); c2.caption(ut)
                with c3.popover("撤回"):
                    if st.button("确认", key=f"del_{mid}"):
                        db.delete_material(mid); st.rerun()

        with t_m:
            all_c = db.get_all_classes()
            if all_c:
                target_c = st.selectbox("选择管理班级", sorted(all_c), key="adm_cl_sel")
                s_total, c_total = db.get_class_stats(target_c)
                k1, k2, k3 = st.columns(3)
                k1.metric("班级人数", s_total)
                k2.metric("互动总量", c_total)
                k3.metric("人均提问", round(c_total/max(s_total,1), 1))
                
                st.divider()
                # 列表表头
                h1, h2, h3, h4 = st.columns([1, 1, 1, 1.5])
                h1.write("**姓名**"); h2.write("**班级**"); h3.write("**互动**"); h4.write("**操作**")
                
                # 学生列表记录
                for name, clz, uname, cnt in db.get_students_by_class(target_c):
                    r1, r2, r3, r4 = st.columns([1, 1, 1, 1.5])
                    r1.write(name)
                    r2.write(clz)
                    r3.write(f"📝 {cnt}")
                    
                    # 在操作列放两个按钮
                    b_col1, b_col2 = r4.columns(2)
                    if b_col1.button("📜 档案", key=f"btn_prof_{uname}"):
                        show_student_profile(uname, name)
                    if b_col2.button("🔑 改密", key=f"btn_reset_{uname}"):
                        admin_reset_pwd_dialog(uname, name)
            else:
                st.warning("暂无学生数据")
