/**
 * SimTrade 管理后台脚本
 */

(function() {
    'use strict';

    /**
     * 加载用户列表，渲染用户管理表格
     */
    function loadUsers() {
        var userType = $('#filter-user-type').val();
        var search = $('#search-user').val();

        $.ajax({
            url: '/api/v1/auth/users/',
            method: 'GET',
            data: {
                user_type: userType,
                search: search
            },
            success: function(response) {
                var html = '';
                var users = response.data || response.results || response;
                if (!users || users.length === 0) {
                    html = '<tr><td colspan="5" class="text-center">暂无用户</td></tr>';
                } else {
                    users.forEach(function(user) {
                        var typeLabel = '';
                        switch(user.user_type) {
                            case 'student': typeLabel = '学生'; break;
                            case 'teacher': typeLabel = '教师'; break;
                            case 'admin': typeLabel = '管理员'; break;
                            default: typeLabel = user.user_type || '-';
                        }
                        html += '<tr data-user-id="' + user.id + '">' +
                            '<td>' + user.id + '</td>' +
                            '<td>' + SimTrade.escapeHtml(user.username || '') + '</td>' +
                            '<td>' + SimTrade.escapeHtml(user.email || '') + '</td>' +
                            '<td>' + typeLabel + '</td>' +
                            '<td>' +
                                '<select class="form-control input-sm change-type-select" data-user-id="' + user.id + '">' +
                                    '<option value="student"' + (user.user_type === 'student' ? ' selected' : '') + '>学生</option>' +
                                    '<option value="teacher"' + (user.user_type === 'teacher' ? ' selected' : '') + '>教师</option>' +
                                    '<option value="admin"' + (user.user_type === 'admin' ? ' selected' : '') + '>管理员</option>' +
                                '</select>' +
                            '</td>' +
                            '<td>' +
                                '<button class="btn btn-warning btn-xs btn-reset-pwd" data-user-id="' + user.id + '">重置密码</button>' +
                            '</td>' +
                        '</tr>';
                    });
                }
                $('#user-table-body').html(html);
            },
            error: function(xhr) {
                $('#user-table-body').html(
                    '<tr><td colspan="6" class="text-center text-danger">加载用户失败: ' +
                    (xhr.responseJSON && xhr.responseJSON.message || '未知错误') +
                    '</td></tr>'
                );
            }
        });
    }

    /**
     * 加载学期列表，渲染学期管理表格
     */
    function loadSemesters() {
        $.ajax({
            url: '/api/v1/teaching/semesters/',
            method: 'GET',
            success: function(response) {
                var html = '';
                var semesters = response.data || response.results || response;
                if (!semesters || semesters.length === 0) {
                    html = '<tr><td colspan="5" class="text-center">暂无学期</td></tr>';
                } else {
                    semesters.forEach(function(sem) {
                        var statusLabel = '';
                        if (sem.status === 'active') {
                            statusLabel = '<span class="label label-success">进行中</span>';
                        } else if (sem.status === 'upcoming') {
                            statusLabel = '<span class="label label-info">未开始</span>';
                        } else {
                            statusLabel = '<span class="label label-default">已结束</span>';
                        }
                        html += '<tr>' +
                            '<td>' + sem.id + '</td>' +
                            '<td>' + SimTrade.escapeHtml(sem.name || '') + '</td>' +
                            '<td>' + (sem.start_date || '-') + '</td>' +
                            '<td>' + (sem.end_date || '-') + '</td>' +
                            '<td>' + statusLabel + '</td>' +
                        '</tr>';
                    });
                }
                $('#semester-table-body').html(html);
            },
            error: function() {
                $('#semester-table-body').html(
                    '<tr><td colspan="5" class="text-center text-danger">加载学期失败</td></tr>'
                );
            }
        });
    }

    // 绑定事件
    $(document).ready(function() {
        // 用户筛选
        $('#filter-user-type').on('change', function() {
            loadUsers();
        });

        // 用户搜索
        var searchTimer;
        $('#search-user').on('input', function() {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(function() {
                loadUsers();
            }, 300);
        });

        // 修改用户类型
        $(document).on('change', '.change-type-select', function() {
            var userId = $(this).data('user-id');
            var newType = $(this).val();
            if (confirm('确认将用户类型修改为: ' + newType + '？')) {
                $.ajax({
                    url: '/api/v1/auth/users/' + userId + '/',
                    method: 'PATCH',
                    contentType: 'application/json',
                    data: JSON.stringify({ user_type: newType }),
                    success: function() {
                        SimTrade.showSuccess('用户类型已修改');
                    },
                    error: function() {
                        SimTrade.showError('修改用户类型失败');
                        loadUsers();
                    }
                });
            } else {
                loadUsers();
            }
        });

        // 重置密码
        $(document).on('click', '.btn-reset-pwd', function() {
            var userId = $(this).data('user-id');
            if (confirm('确认重置该用户密码？')) {
                $.ajax({
                    url: '/api/v1/auth/users/' + userId + '/reset-password/',
                    method: 'POST',
                    success: function() {
                        SimTrade.showSuccess('密码已重置');
                    },
                    error: function() {
                        SimTrade.showError('重置密码失败');
                    }
                });
            }
        });
    });

    // 暴露全局函数
    window.loadUsers = loadUsers;
    window.loadSemesters = loadSemesters;

})();
