"""
双语过滤器 - 为中文标签添加英文翻译
格式：中文-English
"""
from django import template

register = template.Library()

# 翻译映射表：中文 -> 英文
TRANSLATION_MAP = {
    # 主导航
    '仪表盘': 'Dashboard',
    '工作台': 'Workspace',
    '教学管理': 'Teaching Management',
    '管理后台': 'Admin Panel',
    '市场': 'Market',
    '交易': 'Transactions',
    '单证': 'Documents',
    '个人中心': 'Profile',
    '退出登录': 'Logout',
    '登录': 'Login',
    '注册': 'Register',

    # 学生仪表盘
    '活跃交易': 'Active Transactions',
    '我的单证': 'My Documents',
    '待处理单证': 'Pending Documents',
    '未读通知': 'Unread Notifications',
    '市场大厅': 'Market Hall',
    '我的交易': 'My Transactions',
    '单证管理': 'Document Management',
    '待审核反馈': 'Pending Review Feedback',
    '即将到期交易': 'Expiring Transactions',

    # 教师仪表盘
    '我的课程': 'My Courses',
    '我的班级': 'My Classes',
    '待批改单证': 'Pending Grading',
    '成绩管理': 'Grade Management',
    '课程管理': 'Course Management',

    # 管理员仪表盘
    '注册用户': 'Registered Users',
    '单证总数': 'Total Documents',
    '课程总数': 'Total Courses',
    '待审核单证': 'Pending Review',
    '用户管理': 'User Management',
    '系统设置': 'System Settings',

    # 通用
    '最近活动': 'Recent Activity',
    '待办事项': 'To-Do List',
    '快捷入口': 'Quick Links',
    '暂无数据': 'No Data',
    '加载中': 'Loading',
    '暂无活动': 'No Activity',
    '暂无待办': 'No Tasks',
    '数据加载失败': 'Data Load Failed',
    '我的单证状态': 'My Document Status',
    '交易进度': 'Transaction Progress',
    '角色分布': 'Role Distribution',
    '课程进度分布': 'Course Progress Distribution',
    '学生单证状态': 'Student Document Status',
    '班级活跃度': 'Class Activity',
    '单证类型分布': 'Document Type Distribution',
    '用户类型分布': 'User Type Distribution',
    '单证状态分布': 'Document Status Distribution',
}


@register.filter
def bilingual(text, english=None):
    """
    将中文文本转换为双语格式：中文-English

    用法:
        {{ "仪表盘"|bilingual }}        → 仪表盘-Dashboard
        {{ "自定义"|bilingual:"Custom" }} → 自定义-Custom
    """
    if not text:
        return text

    # 如果提供了英文参数，优先使用
    if english:
        return f"{text}-{english}"

    # 查翻译表
    english = TRANSLATION_MAP.get(text)

    # 如果找到翻译，返回双语格式
    if english:
        return f"{text}-{english}"

    # 未找到翻译，返回原文
    return text
