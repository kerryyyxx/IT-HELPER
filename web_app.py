import streamlit as st
from database import SchoolAIDatabase
from openai import OpenAI
import httpx
from styles import apply_styles

# --- 1. 初始化 ---
db = SchoolAIDatabase()
client = OpenAI(api_key=st.secrets["API_KEY"], base_url=st.secrets["BASE_URL"], http_client=httpx.Client(verify=False))

for key in ["logged_in", "menu", "msgs", "user_info", "forgot_step", "reset_un"]:
    if key not in st.session_state:
        if key == "logged_in":
            st.session_state[key] = False
        elif key == "msgs":
            st.session_state[key] = []
        elif key == "user_info":
            st.session_state[key] = {}
        elif key == "forgot_step":
            st.session_state[key] = 0
        else:
            st.session_state[key] = ""

apply_styles()

# --- 2. 侧边栏 ---
with st.sidebar:
    st.markdown("<h2 style='padding:15px 5px;'>🍀 IT Helper</h2>", unsafe_allow_html=True)

    if not st.session_state.logged_in:
        # --- 找回密码流程 ---
        if st.session_state.forgot_step > 0:
            st.markdown("### 🔑 找回密码")
            if st.session_state.forgot_step == 1:
                un = st.text_input("请输入账号", value=st.session_state.reset_un)
                if st.button("获取密保问题", use_container_width=True):
                    conn = db.get_connection()
                    res = conn.execute("SELECT security_q, security_a FROM users WHERE username=?", (un,)).fetchone()
                    conn.close()
                    if res:
                        st.session_state.reset_un = un
                        st.session_state.temp_q = res[0]
                        st.session_state.temp_a = res[1]
                    else:
                        st.error("账号不存在")

                if "temp_q" in st.session_state:
                    st.info(f"问题：{st.session_state.temp_q}")
                    ans = st.text_input("输入答案")
                    if st.button("验证回答", use_container_width=True, type="primary"):
                        if ans == st.session_state.temp_a:
                            st.session_state.forgot_step = 2
                            st.rerun()
                        else:
                            st.error("答案错误")

            elif st.session_state.forgot_step == 2:
                new_p = st.text_input("设定新密码", type="password")
                if st.button("确认修改", use_container_width=True, type="primary"):
                    if db.reset_student_password(st.session_state.reset_un, new_p):
                        st.success("重置成功！请重新登录")
                        st.session_state.forgot_step = 0
                        st.rerun()

            if st.button("返回登录"):
                st.session_state.forgot_step = 0
                st.rerun()

        else:
            t1, t2 = st.tabs(["🔐 登录", "📝 注册"])
            with t1:
                u = st.text_input("账号", key="l_u")
                p = st.text_input("密码", type="password", key="l_p")
                if st.button("进入系统", type="primary", use_container_width=True):
                    res = db.login(u, p)
                    if res:
                        st.session_state.user_info = {"username": u, "role": res[0], "name": res[1]}
                        st.session_state.logged_in = True
                        st.session_state.menu = "👨‍🏫 班级看板" if res[0] == 'admin' else "💡 灵感对话助手"
                        st.rerun()
                    else:
                        st.error("❌ 账号或密码错误")

                # 这里去掉了 variant="ghost" 避免报错
                if st.button("❓ 忘记密码？点击找回", use_container_width=True):
                    st.session_state.forgot_step = 1
                    st.rerun()

            with t2:
                ru = st.text_input("设定账号");
                rn = st.text_input("真实姓名")
                c1, c2 = st.columns(2)
                g = c1.number_input("年级", 2020, 2030, 2024);
                b = c2.number_input("班级", 1, 50, 1)
                rp = st.text_input("设定密码", type="password")
                st.divider()
                rq = st.text_input("密保问题 (必填)");
                ra = st.text_input("密保答案 (必填)")
                if st.button("提交注册", use_container_width=True):
                    if all([ru, rn, rp, rq, ra]):
                        if db.register_user(ru, rp, rn, f"{g}级{b}班", rq, ra):
                            st.success("✅ 注册成功！")
                        else:
                            st.error("账号已存在")
                    else:
                        st.warning("请填满所有信息")
    else:
        u_info = st.session_state.user_info
        st.markdown(f"👤 **{u_info['name']}**")
        items = ["👨‍🏫 班级看板", "📢 发布动态"] if u_info['role'] == 'admin' else ["💡 灵感对话助手", "📁 数字化教学资源"]
        for item in items:
            if st.button(item, type="primary" if st.session_state.menu == item else "secondary",
                         use_container_width=True):
                st.session_state.menu = item;
                st.rerun()
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.clear();
            st.rerun()

# --- 3. 主界面内容 ---
if st.session_state.logged_in:
    user, choice = st.session_state.user_info, st.session_state.menu

    if user['role'] == 'admin':
        if choice == "👨‍🏫 班级看板":
            st.subheader("📊 班级看板")
            clzs = db.get_all_classes()
            if clzs:
                target = st.selectbox("筛选班级", sorted(clzs))
                st.divider()
                h = st.columns([1, 1, 0.8, 1, 1])
                h[0].write("**姓名**");
                h[1].write("**班级**");
                h[2].write("**互动**");
                h[3].write("**档案**");
                h[4].write("**修改**")
                for n, c, un, cnt in db.get_students_by_class(target):
                    r = st.columns([1, 1, 0.8, 1, 1])
                    r[0].write(n);
                    r[1].write(c);
                    r[2].write(f"💬 {cnt}")
                    if r[3].button("📂 档案", key=f"v_{un}"): st.session_state.active_stu = (un, n)
                    if r[4].button("🔧 修改", key=f"ed_{un}"): st.session_state.editing_stu = {"un": un, "n": n, "c": c}

                if "editing_stu" in st.session_state:
                    with st.container(border=True):
                        e = st.session_state.editing_stu
                        st.markdown(f"#### 🛠️ 修改: {e['n']}")
                        new_n = st.text_input("姓名", value=e['n'])
                        new_c = st.text_input("班级", value=e['c'])
                        new_p = st.text_input("重设密码 (可选)", type="password")
                        if st.button("保存修改", type="primary"):
                            db.update_student_info(e['un'], new_n, new_c)
                            if new_p: db.reset_student_password(e['un'], new_p)
                            st.success("已更新");
                            del st.session_state.editing_stu;
                            st.rerun()
                        if st.button("取消"): del st.session_state.editing_stu; st.rerun()

                if "active_stu" in st.session_state:
                    aun, aname = st.session_state.active_stu
                    st.divider()
                    st.markdown(f"### 📁 学生档案：{aname}")
                    t_chat, t_down = st.tabs(["💬 互动详情", "📥 下载足迹"])
                    with t_chat:
                        history = db.get_chat_history(aun)
                        if history:
                            for q, a, t in reversed(history):
                                with st.expander(f"🕒 {t} | {q[:15]}..."):
                                    st.write(f"**问：** {q}\n\n**答：** {a}")
                        else:
                            st.info("暂无记录")
                    with t_down:
                        dls = db.get_student_downloads(aun)
                        if dls:
                            st.table(dls)
                        else:
                            st.info("无下载")
                    if st.button("关闭档案"): del st.session_state.active_stu; st.rerun()

        elif choice == "📢 发布动态":
            st.subheader("📢 资源发布")
            with st.form("pub"):
                ds = st.text_area("老师讲内容 (寄语)")
                f = st.file_uploader("附件")
                if st.form_submit_button("立即发布"):
                    if f: db.upload_material(f.name, f.read(), ds); st.success("成功")
            st.divider()
            for mid, fn, ut, ds in db.get_all_materials():
                with st.container(border=True):
                    st.write(f"📄 **{fn}** | {ut}")
                    if st.button("🗑️ 撤回", key=f"del_{mid}"): db.delete_material(mid); st.rerun()

    else:
        if choice == "💡 灵感对话助手":
            with st.expander("📜 咨询回顾", expanded=False):
                for q, a, t in reversed(db.get_chat_history(user['username'])):
                    with st.expander(f"🕒 {t} | {q[:15]}..."):
                        st.write(f"**问：** {q}\n\n**答：** {a}")

            for m in st.session_state.msgs:
                with st.chat_message(m["role"]): st.markdown(m["content"])

            if pr := st.chat_input("输入你的疑问..."):
                st.session_state.msgs.append({"role": "user", "content": pr})
                with st.chat_message("user"):
                    st.markdown(pr)
                with st.chat_message("assistant"):
                    think = st.empty();
                    think.info("🤖 AI 老师正在认真思考中...")
                    res_area = st.empty();
                    full_r = ""
                    try:
                        stream = client.chat.completions.create(
                            model="ep-20260224161941-nqw6c",
                            messages=[{"role": "system", "content": "你是一位资深IT老师"}] + st.session_state.msgs,
                            stream=True
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                think.empty()
                                full_r += chunk.choices[0].delta.content
                                res_area.markdown(full_r + "▌")
                        res_area.markdown(full_r)
                        db.save_chat(user['username'], pr, full_r)
                        st.session_state.msgs.append({"role": "assistant", "content": full_r})
                    except:
                        st.error("AI 接口连接失败")

        elif choice == "📁 数字化教学资源":
            st.subheader("📁 资源中心")
            if st.button("🔄 刷新", type="primary", use_container_width=True): st.rerun()
            for mid, fn, ut, ds in db.get_all_materials():
                with st.container(border=True):
                    st.markdown(f"### 📄 {fn}")
                    st.markdown(f'<div class="teacher-note-box"><b>💡 老师讲内容：</b><br>{ds}</div>',
                                unsafe_allow_html=True)
                    _, fd = db.get_material_data(mid)
                    st.download_button("📥 下载", fd, fn, key=f"dl_{mid}")
else:
    st.info("👋 请登录。如有问题请咨询管理员！")