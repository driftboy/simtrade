/**
 * SimTrade 角色切换器
 * 依赖：jQuery, Bootstrap 3 dropdown, SimTrade (main.js)
 */
(function() {
    'use strict';

    // 角色名称映射
    var ROLE_NAMES = {
        'exporter': '出口商', 'importer': '进口商', 'factory': '工厂',
        'bank': '银行', 'customs': '海关', 'shipping': '货运公司',
        'insurance': '保险公司', 'inspection': '商检机构',
        'forex': '外汇局', 'tax': '税务局'
    };

    /**
     * 渲染角色徽章 HTML
     */
    function renderBadge(roleCode) {
        var name = ROLE_NAMES[roleCode] || roleCode;
        return '<span class="role-badge role-' + roleCode + '">' + name + '</span>';
    }

    /**
     * 更新导航栏按钮显示
     */
    function updateButton(data) {
        var $label = $('#role-switcher-label');
        if (!data) {
            $label.html('选择角色');
            return;
        }
        $label.html(renderBadge(data.role_code) +
            ' <span class="role-switcher-label">' +
            SimTrade.escapeHtml(data.company_name) + '</span>');
    }

    /**
     * 渲染角色列表
     */
    function renderRoles(data) {
        var $menu = $('#role-dropdown-menu');
        $menu.empty();

        if (!data || data.length === 0) {
            $menu.append('<li class="role-empty-hint">暂无角色，请联系教师分配</li>');
            return;
        }

        // 分组：已激活角色 + 待审核角色
        var activeRoles = [];
        var pendingRoles = [];

        for (var i = 0; i < data.length; i++) {
            var item = data[i];
            if (item.status === 'active') {
                activeRoles.push(item);
            } else if (item.status === 'pending') {
                pendingRoles.push(item);
            }
            // rejected 状态不显示
        }

        // 已激活角色
        if (activeRoles.length > 0) {
            $menu.append('<li class="dropdown-header">已激活角色</li>');
            for (var j = 0; j < activeRoles.length; j++) {
                var role = activeRoles[j];
                var isActive = role.is_active;
                var checkMark = isActive ? '<span class="check-mark">&#10003;</span>' : '';
                var activeClass = isActive ? ' active-role' : '';
                var html = '<li class="role-item' + activeClass + '" data-id="' + role.id + '">' +
                    checkMark + renderBadge(role.role_code) +
                    ' <span class="role-item-name">' + SimTrade.escapeHtml(role.company_name) + '</span>' +
                    '</li>';
                $menu.append(html);
            }
        }

        // 待审核角色
        if (pendingRoles.length > 0) {
            if (activeRoles.length > 0) {
                $menu.append('<li role="separator" class="divider"></li>');
            }
            $menu.append('<li class="dropdown-header">待审核</li>');
            for (var k = 0; k < pendingRoles.length; k++) {
                var pRole = pendingRoles[k];
                $menu.append(
                    '<li class="role-item disabled">' +
                    renderBadge(pRole.role_code) +
                    ' <span class="role-item-name">' + SimTrade.escapeHtml(pRole.company_name) + '</span>' +
                    '<span class="pending-label">待审核</span></li>');
            }
        }
    }

    /**
     * 切换角色
     */
    function switchRole(assignmentId) {
        $.ajax({
            url: '/api/v1/my-roles/' + assignmentId + '/activate/',
            type: 'POST',
            success: function() {
                window.location.href = '/workspace/';
            },
            error: function(xhr) {
                var msg = '角色切换失败';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg = xhr.responseJSON.message;
                }
                SimTrade.showError(msg);
            }
        });
    }

    /**
     * 初始化角色切换器
     */
    function init() {
        if (!window.user || !window.user.is_authenticated) {
            return;
        }

        // 加载当前激活角色
        $.get('/api/v1/my-roles/current/', function(resp) {
            updateButton(resp.data);
        });

        // dropdown 展开时加载角色列表
        $('#role-dropdown').on('show.bs.dropdown', function() {
            $.get('/api/v1/my-roles/', function(resp) {
                renderRoles(resp.data);
            });
        });

        // 点击角色项切换
        $(document).on('click', '#role-dropdown-menu .role-item:not(.disabled):not(.active-role)', function(e) {
            var id = $(this).data('id');
            if (id) {
                switchRole(id);
            }
            e.stopPropagation();
        });
    }

    $(document).ready(init);

})();