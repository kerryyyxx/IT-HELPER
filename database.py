import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
import streamlit as st

class SchoolAIDatabase:
    def __init__(self, db_name="school_ai.db"):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def _hash_password(self, password):
        """私有方法：将明文密码转换为哈希乱码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. 创建基础表
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                         (username TEXT PRIMARY KEY, password TEXT, name TEXT, 
                          class_info TEXT, role TEXT, security_q TEXT, security_a TEXT)''')

        # 2. 检查并补齐安全字段
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'security_q' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN security_q TEXT DEFAULT '默认问题'")
        if 'security_a' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN security_a TEXT DEFAULT '默认答案'")

        # 3. 创建业务表
        cursor.execute('''CREATE TABLE IF NOT EXISTS chats 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, 
                          question TEXT, answer TEXT, timestamp DATETIME)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS materials 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, 
                          file_data BLOB, upload_time DATETIME, description TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS downloads 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, 
                          filename TEXT, download_time DATETIME)''')

        # --- 核心安全修改点 ---
        import streamlit as st  # 确保函数内或文件顶部有这一行

        # 从云端 Secrets 读取真正的强密码，如果没设置，本地默认用 admin123
        raw_admin_p = st.secrets.get("ADMIN_PASSWORD", "admin123")
        admin_p = self._hash_password(raw_admin_p)

        # 插入或忽略 admin 账号
        cursor.execute(
            "INSERT OR IGNORE INTO users VALUES ('admin', ?, '管理员', '全校中心', 'admin', '默认', '默认')",
            (admin_p,))

        # 强制更新密码：确保云端 Secrets 里的密码始终覆盖数据库旧值
        cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (admin_p,))

        conn.commit()
        conn.close()

    def login(self, u, p):
        conn = self.get_connection()
        hp = self._hash_password(p)  # 对输入的密码进行哈希后再对比
        try:
            res = conn.execute("SELECT role, name FROM users WHERE username=? AND password=?", (u, hp)).fetchone()
            return res
        except:
            return None
        finally:
            conn.close()

    def register_user(self, u, p, n, c, sq, sa):
        conn = self.get_connection()
        hp = self._hash_password(p)  # 加密存储
        try:
            conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)", (u, hp, n, c, 'student', sq, sa))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    def reset_student_password(self, username, new_password):
        conn = self.get_connection()
        hp = self._hash_password(new_password)  # 加密重置
        try:
            conn.execute("UPDATE users SET password = ? WHERE username = ?", (hp, username))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    # --- 以下方法保持不变 ---
    def get_all_classes(self):
        conn = self.get_connection()
        res = [r[0] for r in conn.execute("SELECT DISTINCT class_info FROM users WHERE role='student'").fetchall()]
        conn.close()
        return res

    def get_students_by_class(self, class_name):
        conn = self.get_connection()
        query = '''SELECT u.name, u.class_info, u.username, COUNT(c.id) 
                   FROM users u LEFT JOIN chats c ON u.username = c.username 
                   WHERE u.class_info = ? AND u.role = 'student'
                   GROUP BY u.username'''
        res = conn.execute(query, (class_name,)).fetchall()
        conn.close()
        return res

    def update_student_info(self, username, new_name, new_class):
        conn = self.get_connection()
        try:
            conn.execute("UPDATE users SET name = ?, class_info = ? WHERE username = ?",
                         (new_name, new_class, username))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()

    def save_chat(self, u, q, a):
        conn = self.get_connection()
        conn.execute("INSERT INTO chats (username, question, answer, timestamp) VALUES (?,?,?,?)",
                     (u, q, a, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def get_chat_history(self, u):
        conn = self.get_connection()
        res = conn.execute("SELECT question, answer, timestamp FROM chats WHERE username=? ORDER BY timestamp ASC",
                           (u,)).fetchall()
        conn.close()
        return res

    def get_student_downloads(self, u):
        conn = self.get_connection()
        res = conn.execute("SELECT filename, download_time FROM downloads WHERE username=? ORDER BY download_time DESC",
                           (u,)).fetchall()
        conn.close()
        return res

    def upload_material(self, fn, fd, ds):
        conn = self.get_connection()
        conn.execute("INSERT INTO materials (filename, file_data, upload_time, description) VALUES (?,?,?,?)",
                     (fn, fd, datetime.now().strftime("%Y-%m-%d %H:%M"), ds))
        conn.commit()
        conn.close()

    def get_all_materials(self):
        conn = self.get_connection()
        res = conn.execute(
            "SELECT id, filename, upload_time, description FROM materials ORDER BY upload_time DESC").fetchall()
        conn.close()
        return res

    def get_material_data(self, mid):
        conn = self.get_connection()
        res = conn.execute("SELECT filename, file_data FROM materials WHERE id=?", (mid,)).fetchone()
        conn.close()
        return res

    def delete_material(self, mid):
        conn = self.get_connection()
        conn.execute("DELETE FROM materials WHERE id=?", (mid,))
        conn.commit()
        conn.close()