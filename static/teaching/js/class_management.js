/**
 * 班级管理前端脚本
 */

// 全局状态
const state = {
    classId: null,
    students: [],
    selectedStudents: new Set(),
    searchQuery: '',
    roleFilter: '',
    statusFilter: '',
    importPreviewData: null,
};

// 工具函数
const utils = {
    // 获取班级ID
    getClassId() {
        const pathParts = window.location.pathname.split('/');
        return parseInt(pathParts[pathParts.length - 2]) || null;
    },

    // 格式化日期
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN');
    },

    // 角色显示名称
    getRoleName(role) {
        const names = {
            student: '学生',
            assistant: '助教',
            monitor: '班长',
        };
        return names[role] || role;
    },

    // 状态显示名称
    getStatusName(status) {
        const names = {
            enrolled: '已选课',
            dropped: '已退课',
        };
        return names[status] || status;
    },

    // 显示提示消息
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    // 获取CSRF Token
    getCsrfToken() {
        // 先尝试从页面元素获取
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (token) return token;

        // 从 cookie 获取
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    },
};

// API 调用
const api = {
    async request(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const csrfToken = utils.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include',
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || '请求失败');
            }

            return data;
        } catch (error) {
            utils.showToast(error.message, 'error');
            throw error;
        }
    },

    // 获取班级学生列表
    async getStudents(classId, filters = {}) {
        const params = new URLSearchParams(filters);
        return this.request(`/api/v1/teaching/classes/${classId}/students/?${params}`);
    },

    // 搜索用户
    async searchUsers(query) {
        if (!query || query.length < 2) return { data: [] };
        return this.request(`/api/v1/users/search/?q=${encodeURIComponent(query)}`);
    },

    // 添加学生
    async addStudent(classId, data) {
        return this.request(`/api/v1/teaching/classes/${classId}/students/`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    // 移除学生
    async removeStudent(classId, studentId) {
        return this.request(`/api/v1/teaching/classes/${classId}/students/${studentId}/`, {
            method: 'DELETE',
        });
    },

    // 批量修改角色
    async batchUpdateRoles(classId, studentIds, role) {
        return this.request(`/api/v1/teaching/classes/${classId}/students/batch/`, {
            method: 'PATCH',
            body: JSON.stringify({ student_ids: studentIds, role }),
        });
    },

    // 批量导入
    async importStudents(classId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = {};
        const csrfToken = utils.getCsrfToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        const response = await fetch(`/api/v1/teaching/classes/${classId}/import/`, {
            method: 'POST',
            headers,
            body: formData,
            credentials: 'include',
        });

        return await response.json();
    },

    // 获取课程列表
    async getCourses() {
        return this.request('/api/v1/teaching/courses/');
    },

    // 创建班级
    async createClass(data) {
        return this.request('/api/v1/teaching/classes/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    // 更新班级
    async updateClass(classId, data) {
        return this.request(`/api/v1/teaching/classes/${classId}/`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    },

    // 删除班级
    async deleteClass(classId) {
        return this.request(`/api/v1/teaching/classes/${classId}/`, {
            method: 'DELETE',
        });
    },
};

// 模态框管理
const modals = {
    addStudent: null,
    importModal: null,
    batchRoleModal: null,
    importResultModal: null,

    init() {
        this.addStudent = document.getElementById('addStudentModal');
        this.importModal = document.getElementById('importModal');
        this.batchRoleModal = document.getElementById('batchRoleModal');
        this.importResultModal = document.getElementById('importResultModal');

        // 绑定关闭按钮
        document.querySelectorAll('.modal .close, .modal .close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.close(e.target.closest('.modal'));
            });
        });

        // 点击背景关闭
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.close(modal);
                }
            });
        });
    },

    open(modal) {
        if (typeof modal === 'string') {
            modal = this[modal];
        }
        if (modal) {
            modal.classList.add('active');
        }
    },

    close(modal) {
        if (typeof modal === 'string') {
            modal = this[modal];
        }
        if (modal) {
            modal.classList.remove('active');
        }
    },
};

// 添加学生功能
const addStudentFeature = {
    searchInput: null,
    searchResults: null,
    newStudentForm: null,
    selectedUser: null,
    searchTimeout: null,

    init() {
        this.searchInput = document.getElementById('studentSearchInput');
        this.searchResults = document.getElementById('searchResults');
        this.newStudentForm = document.getElementById('newStudentForm');

        // 搜索输入
        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchUsers(e.target.value);
            }, 300);
        });

        // 确认添加
        document.getElementById('addStudentConfirm').addEventListener('click', () => {
            this.confirmAdd();
        });

        // 取消添加
        document.getElementById('addStudentCancel').addEventListener('click', () => {
            modals.close('addStudent');
            this.reset();
        });
    },

    async searchUsers(query) {
        if (!query.trim()) {
            this.searchResults.innerHTML = '';
            this.newStudentForm.style.display = 'none';
            return;
        }

        try {
            const result = await api.searchUsers(query);
            this.displaySearchResults(result.data);
        } catch (error) {
            this.searchResults.innerHTML = '<p style="padding:12px;color:#991b1b;">搜索失败</p>';
        }
    },

    displaySearchResults(users) {
        if (users.length === 0) {
            this.searchResults.innerHTML = '<p style="padding:12px;color:#666;">未找到学生，请创建新学生</p>';
            this.newStudentForm.style.display = 'block';
            return;
        }

        this.searchResults.innerHTML = users.map(user => `
            <div class="search-result-item" data-user-id="${user.id}">
                <div class="student-name">${user.username}</div>
                <div class="student-id">学号: ${user.student_id || '未设置'}</div>
            </div>
        `).join('');

        // 绑定点击事件
        this.searchResults.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectUser(item.dataset.userId);
            });
        });
    },

    selectUser(userId) {
        this.selectedUser = userId;
        this.searchInput.value = this.searchResults.querySelector(
            `.search-result-item[data-user-id="${userId}"] .student-name`
        ).textContent;
        this.searchResults.innerHTML = '<p style="padding:12px;color:#065f46;">已选择学生</p>';
    },

    async confirmAdd() {
        const isNewStudent = this.newStudentForm.style.display === 'block';
        let data;

        if (isNewStudent) {
            // 创建新学生
            data = {
                student_id_new: document.getElementById('newStudentId').value,
                username: document.getElementById('newStudentName').value,
                name: document.getElementById('newStudentName').value,
                phone: document.getElementById('newStudentPhone').value,
                email: document.getElementById('newStudentEmail').value,
                admin_class: document.getElementById('newStudentAdminClass').value,
                grade: document.getElementById('newStudentGrade').value,
                role: document.getElementById('newStudentRole').value,
            };

            if (!data.student_id_new || !data.name) {
                utils.showToast('请填写必填字段', 'error');
                return;
            }
        } else if (this.selectedUser) {
            // 添加现有用户（需要获取学号）
            const user = await api.request(`/api/v1/users/${this.selectedUser}/`);
            data = { student_id: user.student_id };
        } else {
            utils.showToast('请选择或创建学生', 'error');
            return;
        }

        try {
            await api.addStudent(state.classId, data);
            utils.showToast('添加成功');
            modals.close('addStudent');
            this.reset();
            studentListFeature.loadStudents();
        } catch (error) {
            utils.showToast(error.message, 'error');
        }
    },

    reset() {
        this.searchInput.value = '';
        this.searchResults.innerHTML = '';
        this.newStudentForm.style.display = 'none';
        this.selectedUser = null;

        // 清空表单
        document.getElementById('newStudentId').value = '';
        document.getElementById('newStudentName').value = '';
        document.getElementById('newStudentPhone').value = '';
        document.getElementById('newStudentEmail').value = '';
        document.getElementById('newStudentAdminClass').value = '';
        document.getElementById('newStudentGrade').value = '';
        document.getElementById('newStudentRole').value = 'student';
    },
};

// 批量导入功能
const importFeature = {
    fileInput: null,
    uploadArea: null,
    previewData: null,

    init() {
        this.fileInput = document.getElementById('fileInput');
        this.uploadArea = document.getElementById('uploadArea');

        // 点击上传区域
        this.uploadArea.addEventListener('click', () => {
            this.fileInput.click();
        });

        // 文件选择
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });

        // 拖拽上传
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('drag-over');
        });

        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('drag-over');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                this.handleFile(e.dataTransfer.files[0]);
            }
        });

        // 确认导入
        document.getElementById('importConfirm').addEventListener('click', () => {
            this.confirmImport();
        });

        // 取消导入
        document.getElementById('importCancel').addEventListener('click', () => {
            modals.close('importModal');
            this.reset();
        });
    },

    async handleFile(file) {
        // 验证文件类型
        const validTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'text/csv',
        ];
        if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls|csv)$/i)) {
            utils.showToast('请上传 Excel 或 CSV 文件', 'error');
            return;
        }

        try {
            // 预览（实际应用中可能需要前端解析或调用预览API）
            document.getElementById('importPreview').style.display = 'block';
            document.getElementById('previewTableBody').innerHTML = `
                <tr><td colspan="3">已选择文件: ${file.name}</td></tr>
            `;
            this.previewData = file;
            document.getElementById('importConfirm').disabled = false;
        } catch (error) {
            utils.showToast('文件解析失败', 'error');
        }
    },

    async confirmImport() {
        if (!this.previewData) return;

        try {
            const result = await api.importStudents(state.classId, this.previewData);

            // 显示结果
            const summary = result.data?.summary || {};
            const message = `导入完成：成功 ${summary.created || 0} 人，更新 ${summary.updated || 0} 人，失败 ${summary.failed || 0} 人`;

            document.getElementById('importSummary').textContent = message;

            // 显示错误列表
            const errorsDiv = document.getElementById('importErrors');
            const errors = result.data?.errors || [];
            if (errors.length > 0) {
                errorsDiv.innerHTML = '<h4>导入失败：</h4>' +
                    errors.map(e => `<div class="import-error-item">第${e.row}行: ${e.error}</div>`).join('');
            } else {
                errorsDiv.innerHTML = '';
            }

            modals.close('importModal');
            modals.open('importResultModal');

            // 刷新列表
            studentListFeature.loadStudents();
        } catch (error) {
            utils.showToast(error.message, 'error');
        }

        this.reset();
    },

    reset() {
        this.fileInput.value = '';
        this.previewData = null;
        document.getElementById('importPreview').style.display = 'none';
        document.getElementById('importConfirm').disabled = true;
    },
};

// 批量修改角色功能
const batchRoleFeature = {
    init() {
        // 打开批量修改弹窗
        document.getElementById('batchUpdateBtn').addEventListener('click', () => {
            if (state.selectedStudents.size === 0) {
                utils.showToast('请先选择学生', 'error');
                return;
            }
            document.getElementById('selectedCount').textContent = state.selectedStudents.size;
            modals.open('batchRoleModal');
        });

        // 确认修改
        document.getElementById('batchRoleConfirm').addEventListener('click', () => {
            this.confirmUpdate();
        });

        // 取消修改
        document.getElementById('batchRoleCancel').addEventListener('click', () => {
            modals.close('batchRoleModal');
        });
    },

    async confirmUpdate() {
        const role = document.getElementById('batchRoleSelect').value;
        const studentIds = Array.from(state.selectedStudents);

        try {
            await api.batchUpdateRoles(state.classId, studentIds, role);
            utils.showToast('批量修改成功');
            modals.close('batchRoleModal');
            state.selectedStudents.clear();
            studentListFeature.loadStudents();
        } catch (error) {
            utils.showToast(error.message, 'error');
        }
    },
};

// 学生列表功能
const studentListFeature = {
    init() {
        // 筛选
        document.getElementById('roleFilter').addEventListener('change', (e) => {
            state.roleFilter = e.target.value;
            this.loadStudents();
        });

        document.getElementById('statusFilter').addEventListener('change', (e) => {
            state.statusFilter = e.target.value;
            this.loadStudents();
        });

        // 全选
        document.getElementById('selectAll').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        // 打开添加学生弹窗
        document.getElementById('addStudentBtn').addEventListener('click', () => {
            modals.open('addStudent');
        });

        // 打开导入弹窗
        document.getElementById('importBtn').addEventListener('click', () => {
            modals.open('importModal');
        });

        // 导出功能（占位）
        document.getElementById('exportBtn').addEventListener('click', () => {
            utils.showToast('导出功能开发中');
        });
    },

    async loadStudents() {
        const tbody = document.getElementById('studentTableBody');
        tbody.innerHTML = '<tr><td colspan="7"><div class="loading">加载中...</div></td></tr>';

        try {
            const filters = {};
            if (state.roleFilter) filters.role = state.roleFilter;
            if (state.statusFilter) filters.status = state.statusFilter;

            const result = await api.getStudents(state.classId, filters);
            state.students = result.data;
            this.renderStudents();
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state">加载失败</div></td></tr>';
        }
    },

    renderStudents() {
        const tbody = document.getElementById('studentTableBody');

        if (state.students.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state">暂无学生</div></td></tr>';
            return;
        }

        tbody.innerHTML = state.students.map(student => `
            <tr class="${state.selectedStudents.has(student.id) ? 'selected' : ''}" data-id="${student.id}">
                <td><input type="checkbox" class="student-checkbox" value="${student.id}"
                    ${state.selectedStudents.has(student.id) ? 'checked' : ''}></td>
                <td>${student.student_id || '-'}</td>
                <td>${student.username}</td>
                <td><span class="role-badge ${student.role}">${utils.getRoleName(student.role)}</span></td>
                <td><span class="status-badge ${student.status}">${utils.getStatusName(student.status)}</span></td>
                <td>${utils.formatDate(student.enrolled_at)}</td>
                <td>
                    <button class="btn btn-sm btn-danger remove-btn" data-student-id="${student.student_id || student.id}">
                        移除
                    </button>
                </td>
            </tr>
        `).join('');

        // 绑定事件
        tbody.querySelectorAll('.student-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.toggleSelectStudent(parseInt(e.target.value), e.target.checked);
            });
        });

        tbody.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.removeStudent(e.target.dataset.studentId);
            });
        });

        // 更新批量操作按钮状态
        document.getElementById('batchUpdateBtn').disabled = state.selectedStudents.size === 0;

        // 更新统计
        document.getElementById('studentCount').textContent = state.students.length;
    },

    toggleSelectStudent(id, selected) {
        if (selected) {
            state.selectedStudents.add(id);
        } else {
            state.selectedStudents.delete(id);
        }

        // 更新行样式
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (row) {
            row.classList.toggle('selected', selected);
        }

        // 更新批量操作按钮
        document.getElementById('batchUpdateBtn').disabled = state.selectedStudents.size === 0;
    },

    toggleSelectAll(selected) {
        state.students.forEach(student => {
            this.toggleSelectStudent(student.id, selected);
        });

        // 更新复选框状态
        document.querySelectorAll('.student-checkbox').forEach(checkbox => {
            checkbox.checked = selected;
        });
    },

    async removeStudent(studentId) {
        if (!confirm('确定要移除该学生吗？')) return;

        try {
            await api.removeStudent(state.classId, studentId);
            utils.showToast('移除成功');
            this.loadStudents();
        } catch (error) {
            utils.showToast(error.message, 'error');
        }
    },
};

// 页面初始化
function initClassDetailPage() {
    state.classId = utils.getClassId();

    if (!state.classId) {
        utils.showToast('无效的班级ID', 'error');
        return;
    }

    // 初始化各个模块
    modals.init();
    addStudentFeature.init();
    importFeature.init();
    batchRoleFeature.init();
    studentListFeature.init();

    // 加载数据
    studentListFeature.loadStudents();

    // 获取班级基本信息
    loadClassInfo();
}

async function loadClassInfo() {
    try {
        const result = await api.request(`/api/v1/teaching/classes/${state.classId}/`);
        const classInfo = result.data;

        document.getElementById('className').textContent = classInfo.name;
        document.getElementById('classTitle').textContent = `${classInfo.course_name} - ${classInfo.name}`;
        document.getElementById('enrollmentCode').textContent = classInfo.enrollment_code || '-';
    } catch (error) {
        console.error('加载班级信息失败', error);
    }
}

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    if (path.includes('/teaching/classes/') && path.match(/\d+/)) {
        // 班级详情页
        initClassDetailPage();
    } else if (path.includes('/teaching/classes')) {
        // 班级列表页（TODO）
        initClassListPage();
    }
});

// 班级列表页
const classListPage = {
    classes: [],
    editingClassId: null,

    init() {
        // 绑定创建按钮
        document.getElementById('createClassBtn').addEventListener('click', () => {
            this.openCreateModal();
        });

        // 绑定搜索输入
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.renderClasses(e.target.value);
        });

        // 绑定模态框关闭
        document.querySelectorAll('#classModal .close, #classCancelBtn').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });

        document.querySelectorAll('#deleteConfirmModal .close, #deleteCancelBtn').forEach(btn => {
            btn.addEventListener('click', () => this.closeDeleteModal());
        });

        // 绑定保存按钮
        document.getElementById('classSaveBtn').addEventListener('click', () => {
            this.saveClass();
        });

        // 绑定删除确认按钮
        document.getElementById('deleteConfirmBtn').addEventListener('click', () => {
            this.confirmDelete();
        });

        // 并行加载数据
        Promise.all([
            this.loadClasses(),
            this.loadCourses()
        ]);
    },

    async loadClasses() {
        const container = document.getElementById('classList');
        container.innerHTML = '<div class="loading">加载中...</div>';

        try {
            const response = await api.request('/api/v1/teaching/classes/');
            this.classes = response.results || [];
            this.renderClasses();
        } catch (error) {
            container.innerHTML = '<div class="empty-state">加载失败</div>';
            console.error('加载班级列表失败', error);
        }
    },

    async loadCourses() {
        try {
            const response = await api.getCourses();
            const courses = response.results || [];

            const select = document.getElementById('classCourse');
            select.innerHTML = '<option value="">请选择课程</option>' +
                courses.map(c => `<option value="${c.id}">${c.name} (${c.semester_name || '-'})</option>`).join('');
        } catch (error) {
            console.error('加载课程列表失败', error);
        }
    },

    renderClasses(filter = '') {
        const container = document.getElementById('classList');

        const filteredClasses = filter
            ? this.classes.filter(c =>
                (c.name || '').toLowerCase().includes(filter.toLowerCase()) ||
                (c.course_name || '').toLowerCase().includes(filter.toLowerCase())
            )
            : this.classes;

        if (filteredClasses.length === 0) {
            container.innerHTML = '<div class="empty-state">' + (filter ? '未找到匹配的班级' : '暂无班级') + '</div>';
            return;
        }

        container.innerHTML = `
            <table class="table table-bordered table-hover">
                <thead>
                    <tr>
                        <th>班级名称</th>
                        <th>课程</th>
                        <th>学期</th>
                        <th>学生人数</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${filteredClasses.map(cls => `
                        <tr>
                            <td><strong>${cls.name || '-'}</strong></td>
                            <td>${cls.course_name || '-'}</td>
                            <td>${cls.semester_name || '-'}</td>
                            <td>${cls.student_count || 0}</td>
                            <td class="action-buttons">
                                <a href="/teaching/classes/${cls.id}/" class="btn btn-sm btn-primary">查看学生</a>
                                <button class="btn btn-sm btn-secondary edit-btn" data-id="${cls.id}">编辑</button>
                                <button class="btn btn-sm btn-danger delete-btn" data-id="${cls.id}" data-name="${cls.name}">删除</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        // 绑定编辑和删除按钮
        container.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.openEditModal(parseInt(e.target.dataset.id));
            });
        });

        container.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.openDeleteModal(e.target.dataset.id, e.target.dataset.name);
            });
        });
    },

    openCreateModal() {
        this.editingClassId = null;
        document.getElementById('classModalTitle').textContent = '创建班级';
        document.getElementById('classForm').reset();
        document.getElementById('classModal').classList.add('active');
    },

    async openEditModal(classId) {
        this.editingClassId = classId;
        const cls = this.classes.find(c => c.id === classId);
        if (!cls) return;

        document.getElementById('classModalTitle').textContent = '编辑班级';
        document.getElementById('classCourse').value = cls.course || '';
        document.getElementById('className').value = cls.name || '';
        document.getElementById('classCapacity').value = cls.capacity || '';
        document.getElementById('classModal').classList.add('active');
    },

    closeModal() {
        document.getElementById('classModal').classList.remove('active');
        document.getElementById('classForm').reset();
        this.editingClassId = null;
    },

    async saveClass() {
        const course = document.getElementById('classCourse').value;
        const name = document.getElementById('className').value.trim();
        const capacity = document.getElementById('classCapacity').value;

        if (!course || !name) {
            utils.showToast('请填写必填字段', 'error');
            return;
        }

        const data = {
            course: parseInt(course),
            name,
        };
        if (capacity) data.capacity = parseInt(capacity);

        try {
            if (this.editingClassId) {
                await api.updateClass(this.editingClassId, data);
                utils.showToast('更新成功');
            } else {
                await api.createClass(data);
                utils.showToast('创建成功');
            }

            this.closeModal();
            this.loadClasses();
        } catch (error) {
            utils.showToast(error.message, 'error');
        }
    },

    openDeleteModal(classId, className) {
        this.deleteClassId = classId;
        document.getElementById('deleteClassName').textContent = className;
        document.getElementById('deleteConfirmModal').classList.add('active');
    },

    closeDeleteModal() {
        document.getElementById('deleteConfirmModal').classList.remove('active');
        this.deleteClassId = null;
    },

    async confirmDelete() {
        if (!this.deleteClassId) return;

        try {
            await api.deleteClass(this.deleteClassId);
            utils.showToast('删除成功');
            this.closeDeleteModal();
            this.loadClasses();
        } catch (error) {
            utils.showToast(error.message, 'error');
        }
    },
};

// 班级列表页初始化（旧版本兼容）
async function initClassListPage() {
    classListPage.init();
}
