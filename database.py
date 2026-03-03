import sqlite3
import bcrypt

class SchoolAIDatabase:
    def __init__(self, db_name="school_system.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # 用户表：包含密保问题和答案
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password BLOB,  -- 注意：加密后的密码存为二进制格式
                name TEXT,
                class_id TEXT,
                security_q TEXT,
                security_a TEXT,
                role TEXT
            )
        """)
        # 课件资料表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                data BLOB,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 下载日志表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                material_id INTEGER,
                download_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 聊天记录表
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                question TEXT,
                answer TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    # --- 🔐 安全核心方法 ---

    def _hash_password(self, password):
        """将明文密码转化为加盐的哈希值"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    def _verify_password(self, password, hashed_pw):
        """对比明文密码与数据库中的哈希值"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_pw)
        except Exception:
            return False

    # --- 👤 用户管理 ---

    def register_user(self, username, password, name, class_id, security_q, security_a, role='student'):
        hashed = self._hash_password(password)
        try:
            self.cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                (username, hashed, name, class_id, security_q, security_a, role)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username, password):
        self.cursor.execute("SELECT password, role, name FROM users WHERE username=?", (username,))
        result = self.cursor.fetchone()
        if result and self._verify_password(password, result[0]):
            return result[1], result[2]  # 返回 role 和 name
        return None

    def update_password(self, username, new_password):
        hashed = self._hash_password(new_password)
        self.cursor.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
        self.conn.commit()
        return True

    def verify_security(self, username, question, answer):
        """验证密保问题和答案是否匹配"""
        self.cursor.execute(
            "SELECT 1 FROM users WHERE username=? AND security_q=? AND security_a=?", 
            (username, question, answer)
        )
        return self.cursor.fetchone() is not None

    def get_user_security_q(self, username):
        """获取用户的密保问题"""
        self.cursor.execute("SELECT security_q FROM users WHERE username=?", (username,))
        res = self.cursor.fetchone()
        return res[0] if res else None

    # --- 📊 教师管理看板数据 ---

    def get_all_classes(self):
        self.cursor.execute("SELECT DISTINCT class_id FROM users WHERE role='student'")
        return [row[0] for row in self.cursor.fetchall()]

    def get_students_by_class(self, class_id):
        """获取班级学生列表及提问总数"""
        query = """
            SELECT u.name, u.class_id, u.username, COUNT(c.id) 
            FROM users u
            LEFT JOIN chat_history c ON u.username = c.username
            WHERE u.class_id = ? AND u.role = 'student'
            GROUP BY u.username
        """
        self.cursor.execute(query, (class_id,))
        return self.cursor.fetchall()

    def get_class_stats(self, class_id):
        """统计班级概览：总人数、总提问数"""
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE class_id=? AND role='student'", (class_id,))
        total_stu = self.cursor.fetchone()[0]
        self.cursor.execute(
            "SELECT COUNT(c.id) FROM chat_history c JOIN users u ON c.username=u.username WHERE u.class_id=?", 
            (class_id,)
        )
        total_chats = self.cursor.fetchone()[0]
        return total_stu, total_chats

    # --- 📥 课件管理 ---

    def upload_material(self, filename, data):
        self.cursor.execute("INSERT INTO materials (filename, data) VALUES (?, ?)", (filename, data))
        self.conn.commit()

    def get_all_materials(self):
        self.cursor.execute("SELECT id, filename, upload_time FROM materials ORDER BY upload_time DESC")
        return self.cursor.fetchall()

    def get_material_data(self, m_id):
        self.cursor.execute("SELECT filename, data FROM materials WHERE id=?", (m_id,))
        return self.cursor.fetchone()

    def delete_material(self, m_id):
        self.cursor.execute("DELETE FROM materials WHERE id=?", (m_id,))
        self.conn.commit()

    def log_download(self, username, m_id):
        self.cursor.execute("INSERT INTO download_logs (username, material_id) VALUES (?, ?)", (username, m_id))
        self.conn.commit()

    def get_student_downloads(self, username):
        query = """
            SELECT m.filename, d.download_time 
            FROM download_logs d
            JOIN materials m ON d.material_id = m.id
            WHERE d.username = ?
            ORDER BY d.download_time DESC
        """
        self.cursor.execute(query, (username,))
        return self.cursor.fetchall()

    # --- 💬 聊天记录 ---

    def save_chat(self, username, question, answer):
        self.cursor.execute("INSERT INTO chat_history (username, question, answer) VALUES (?, ?, ?)", 
                           (username, question, answer))
        self.conn.commit()

    def get_chat_history(self, username):
        self.cursor.execute("SELECT question, answer, timestamp FROM chat_history WHERE username=? ORDER BY timestamp ASC", (username,))
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close()