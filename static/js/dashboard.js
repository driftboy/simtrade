/**
 * SimTrade Dashboard JavaScript
 * 仪表盘通用逻辑
 */

(function() {
    'use strict';

    // ==========================================
    // 通用统计加载
    // ==========================================

    /**
     * 加载未读通知数和当前角色信息
     */
    function loadDashboardStats() {
        $.get('/api/v1/notifications/unread-count/', function(resp) {
            $('#stat-unread-count').text(resp.data.count || 0);
        }).fail(function() {
            $('#stat-unread-count').text('-');
        });

        $.get('/api/v1/roles/active/', function(resp) {
            var role = resp.data;
            if (role && role.name) {
                $('#stat-active-role').text(role.name);
            } else {
                $('#stat-active-role').text('未选择');
            }
        }).fail(function() {
            $('#stat-active-role').text('-');
        });
    }

    // ==========================================
    // 学生仪表盘数据加载
    // ==========================================

    /**
     * 加载学生仪表盘数据
     */
    function loadStudentData() {
        // 加载活跃交易数
        $.get('/api/v1/transactions/', {status: 'active'}, function(resp) {
            var count = (resp.data && resp.data.length) || 0;
            $('#stat-active-transactions').text(count);
        }).fail(function() {
            $('#stat-active-transactions').text('-');
        });

        // 加载待处理单证数
        $.get('/api/v1/documents/', {status: 'pending'}, function(resp) {
            var count = (resp.data && resp.data.length) || 0;
            $('#stat-pending-documents').text(count);
        }).fail(function() {
            $('#stat-pending-documents').text('-');
        });

        // 加载最近交易动态
        $.get('/api/v1/transactions/', function(resp) {
            var $container = $('#recent-activity');
            $container.empty();
            var data = resp.data || [];
            if (data.length === 0) {
                $container.html('<div class="text-muted">暂无交易动态</div>');
                return;
            }
            var items = data.slice(0, 5);
            for (var i = 0; i < items.length; i++) {
                var t = items[i];
                var time = SimTrade.formatDateTime(t.updated_at, 'MM-DD HH:mm');
                $container.append(
                    '<div class="dash-activity-item">' +
                        '<strong>' + SimTrade.escapeHtml(t.product_name || t.title || '') + '</strong>' +
                        ' <span class="text-muted">' + time + '</span>' +
                        '<br><small class="text-muted">' + SimTrade.escapeHtml(t.status_display || t.status || '') + '</small>' +
                    '</div>'
                );
            }
        }).fail(function() {
            $('#recent-activity').html('<div class="text-danger">加载失败</div>');
        });
    }

    // ==========================================
    // 教师仪表盘数据加载
    // ==========================================

    /**
     * 加载教师仪表盘数据
     */
    function loadTeacherData() {
        // 加载课程数
        $.get('/api/v1/teaching/courses/', function(resp) {
            var count = (resp.data && resp.data.length) || 0;
            $('#stat-courses').text(count);
        }).fail(function() {
            $('#stat-courses').text('-');
        });

        // 加载待审核角色
        $.get('/api/v1/roles/', {status: 'pending'}, function(resp) {
            var count = (resp.data && resp.data.length) || 0;
            $('#stat-pending-roles').text(count);
        }).fail(function() {
            $('#stat-pending-roles').text('-');
        });
    }

    // ==========================================
    // 管理员仪表盘数据加载
    // ==========================================

    /**
     * 加载管理员仪表盘数据
     */
    function loadAdminData() {
        // 加载学期数据
        $.get('/api/v1/admin/semesters/', function(resp) {
            var data = resp.data || [];
            var activeCount = 0;
            for (var i = 0; i < data.length; i++) {
                if (data[i].is_active) activeCount++;
            }
            $('#stat-active-semesters').text(activeCount);
        }).fail(function() {
            $('#stat-active-semesters').text('-');
        });
    }

    // ==========================================
    // 初始化
    // ==========================================

    function init() {
        if (!window.user || !window.user.is_authenticated) return;

        // 加载通用统计
        loadDashboardStats();

        // 根据用户类型加载专属数据
        var userType = window.dashboardUserType;
        if (userType === 'student') {
            loadStudentData();
        } else if (userType === 'teacher') {
            loadTeacherData();
        } else if (userType === 'admin') {
            loadAdminData();
        }
    }

    $(document).ready(init);

})();
