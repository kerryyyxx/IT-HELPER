from database import SchoolAIDatabase

db = SchoolAIDatabase()

# 这里设置你想要的老师账号和密码
admin_user = "admin"
admin_pwd = "itit888" # 建议设置一个复杂的
admin_name = "金老师"

# 尝试注册，如果已存在会返回 False
success = db.register_user(
    username=admin_user, 
    password=admin_pwd, 
    name=admin_name, 
    class_id="管理组", 
    security_q="我的工号", 
    security_a="001", 
    role="admin" # 关键点：role 设置为 admin
)

if success:
    print(f"✅ 老师账号创建成功！\n用户名: {admin_user}\n密码: {admin_pwd}")
else:
    print("❌ 创建失败，可能用户名已存在。")