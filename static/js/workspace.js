/**
 * SimTrade 工作台核心脚本
 * 依赖：jQuery, Bootstrap 3
 */
(function() {
    'use strict';

    // ---------------------------------------------------------------
    // 角色名称映射
    // ---------------------------------------------------------------
    var ROLE_NAMES = {
        'exporter': '出口商',
        'importer': '进口商',
        'factory': '工厂',
        'bank': '银行',
        'customs': '海关',
        'shipping': '货运公司',
        'insurance': '保险公司',
        'inspection': '商检机构',
        'forex': '外汇局',
        'tax': '税务局'
    };

    // ---------------------------------------------------------------
    // 状态流转操作映射：roleCode -> status -> [actions]
    // ---------------------------------------------------------------
    var ACTION_MAP = {
        'customs': {
            'declared':    [{ label: '开始审核', action: 'review', btnClass: 'btn-primary' }],
            'reviewing':   [{ label: '评估', action: 'assess', btnClass: 'btn-warning' }],
            'assessed':    [{ label: '放行', action: 'clear', btnClass: 'btn-success' }]
        },
        'inspection': {
            'applied':     [{ label: '检验', action: 'inspect', btnClass: 'btn-primary' }],
            'inspecting':  [
                { label: '通过', action: 'pass_inspection', btnClass: 'btn-success' },
                { label: '不合格', action: 'fail', btnClass: 'btn-danger' }
            ],
            'passed':      [{ label: '出证', action: 'certify', btnClass: 'btn-success' }]
        },
        'forex': {
            'applied':     [{ label: '核验', action: 'verify', btnClass: 'btn-primary' }],
            'verified':    [{ label: '结算', action: 'settle', btnClass: 'btn-success' }]
        },
        'tax': {
            'reviewing':   [{ label: '批准', action: 'approve', btnClass: 'btn-success' }],
            'approved':    [{ label: '退税', action: 'refund', btnClass: 'btn-primary' }]
        },
        'factory': {
            'draft':       [{ label: '确认', action: 'confirm', btnClass: 'btn-primary' }],
            'confirmed':   [{ label: '发货', action: 'ship', btnClass: 'btn-warning' }],
            'shipped':     [{ label: '开票', action: 'invoice', btnClass: 'btn-success' }]
        },
        'bank': {
            'pending_issue': [{ label: '开证', action: 'issue', btnClass: 'btn-primary' }],
            'issued':        [{ label: '通知', action: 'advise', btnClass: 'btn-warning' }],
            'submitted':     [{ label: '议付', action: 'negotiate', btnClass: 'btn-primary' }],
            'negotiated':    [{ label: '付款', action: 'pay', btnClass: 'btn-success' }]
        },
        'shipping': {
            'draft':       [{ label: '订舱', action: 'book', btnClass: 'btn-primary' }],
            'booked':      [{ label: '装货', action: 'load', btnClass: 'btn-warning' }],
            'loaded':      [{ label: '签发提单', action: 'issue_bl', btnClass: 'btn-success' }],
            'shipped':     [{ label: '到港', action: 'arrive', btnClass: 'btn-info' }]
        },
        'insurance': {
            'applied':        [{ label: '核保', action: 'underwrite', btnClass: 'btn-primary' }],
            'underwritten':   [{ label: '出单', action: 'issue', btnClass: 'btn-success' }]
        }
    };

    // ---------------------------------------------------------------
    // 辅助：HTML 转义
    // ---------------------------------------------------------------
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ---------------------------------------------------------------
    // 初始化侧边栏
    // ---------------------------------------------------------------
    function initSidebar(config) {
        var roleCode = config.roleCode || '';
        var roleName = ROLE_NAMES[roleCode] || roleCode;

        // 设置角色名称
        $('#sidebar-role-name').text(roleName);

        // 从 role-switcher API 获取公司名
        $.get('/api/v1/my-roles/current/', function(resp) {
            if (resp.data && resp.data.company_name) {
                $('#sidebar-company-name').text(resp.data.company_name);
            }
        });

        // 渲染侧边栏导航（从页面 tab 导航同步）
        var $tabNav = $('#workspace-tab-nav');
        var $sidebarNav = $('#sidebar-nav');
        $sidebarNav.empty();

        $tabNav.find('li a').each(function() {
            var label = $(this).text().trim();
            var tabId = $(this).attr('href');
            var isActive = $(this).closest('li').hasClass('active');
            var html = '<li' + (isActive ? ' class="active"' : '') + '>' +
                '<a href="javascript:void(0)" data-sidebar-tab="' + tabId + '">' +
                escapeHtml(label) + '</a></li>';
            $sidebarNav.append(html);
        });
    }

    // ---------------------------------------------------------------
    // 获取 Tab 对应的 API URL
    // ---------------------------------------------------------------
    function getTabApi(tabIndex) {
        var $tabLink = $('#workspace-tab-nav a[data-tab="' + tabIndex + '"]');
        if (!$tabLink.length) return null;
        return $tabLink.data('api');
    }

    // ---------------------------------------------------------------
    // 加载统计数据
    // ---------------------------------------------------------------
    function loadStats() {
        var $cards = $('#stats-row .stat-card');
        $cards.each(function() {
            var $card = $(this);
            var apiUrl = $card.data('api');
            if (!apiUrl) return;

            var $number = $card.find('.stat-number');
            $number.text('...');

            $.get(apiUrl, function(resp) {
                var count = 0;
                if (resp.data) {
                    if (Array.isArray(resp.data)) {
                        count = resp.data.length;
                    } else if (typeof resp.data === 'object' && resp.data.count !== undefined) {
                        count = resp.data.count;
                    }
                }
                $number.text(count);
            }).fail(function() {
                $number.text('-');
            });
        });
    }

    // ---------------------------------------------------------------
    // 加载列表数据
    // ---------------------------------------------------------------
    function loadList(apiUrl, roleCode) {
        if (!apiUrl) return;

        var $activePane = $('#workspace-tab-content .tab-pane.active');
        if ($activePane.find('table.data-table').length > 0) return; // 已渲染

        $.get(apiUrl, function(resp) {
            var items = [];
            if (resp.data) {
                items = Array.isArray(resp.data) ? resp.data : (resp.data.results || []);
            }
            renderTable($activePane, items, roleCode);
        }).fail(function(xhr) {
            $activePane.html(
                '<div class="alert alert-danger">加载失败: ' +
                escapeHtml(xhr.responseJSON && xhr.responseJSON.message || '未知错误') +
                '</div>'
            );
        });
    }

    // ---------------------------------------------------------------
    // 渲染数据表格
    // ---------------------------------------------------------------
    function renderTable($container, items, roleCode) {
        if (!items || items.length === 0) {
            $container.html('<div class="alert alert-info">暂无数据</div>');
            return;
        }

        // 根据第一个 item 的字段生成列头
        var firstItem = items[0];
        var skipFields = { 'id': true };
        var columns = [];

        for (var key in firstItem) {
            if (firstItem.hasOwnProperty(key) && !skipFields[key]) {
                columns.push(key);
            }
        }

        var html = '<table class="table table-striped table-hover data-table"><thead><tr>';

        // 表头
        html += '<th>ID</th>';
        for (var c = 0; c < columns.length; c++) {
            html += '<th>' + escapeHtml(columns[c]) + '</th>';
        }
        html += '<th>操作</th>';
        html += '</tr></thead><tbody>';

        // 数据行
        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            html += '<tr>';
            html += '<td>' + escapeHtml(item.id) + '</td>';

            for (var j = 0; j < columns.length; j++) {
                var val = item[columns[j]];
                html += '<td>' + escapeHtml(val !== null && val !== undefined ? val : '') + '</td>';
            }

            // 操作按钮列
            html += '<td class="action-cell">';
            html += renderActionButtons(item, roleCode);
            html += '</td>';
            html += '</tr>';
        }

        html += '</tbody></table>';
        $container.html(html);
    }

    // ---------------------------------------------------------------
    // 渲染操作按钮
    // ---------------------------------------------------------------
    function renderActionButtons(item, roleCode) {
        var status = item.status;
        if (!status) return '';

        var roleActions = ACTION_MAP[roleCode];
        if (!roleActions) return '';

        var actions = roleActions[status];
        if (!actions || actions.length === 0) return '';

        var html = '';
        for (var i = 0; i < actions.length; i++) {
            var a = actions[i];
            html += '<button class="action-btn ' + escapeHtml(a.btnClass || '') +
                '" data-action="' + escapeHtml(a.action) +
                '" data-item-id="' + escapeHtml(item.id) +
                '">' + escapeHtml(a.label) + '</button> ';
        }
        return html;
    }

    // ---------------------------------------------------------------
    // 执行操作
    // ---------------------------------------------------------------
    function executeAction(apiUrl, itemId, action, roleCode) {
        if (!apiUrl || !action) return;

        var url = apiUrl.replace(/\/$/, '') + '/' + itemId + '/' + action + '/';
        var csrftoken = $.cookie('csrftoken') || $('input[name="csrfmiddlewaretoken"]').val();

        $.ajax({
            url: url,
            type: 'POST',
            beforeSend: function(xhr) {
                if (csrftoken) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                }
            },
            success: function(resp) {
                var msg = (resp && resp.message) || '操作成功';
                SimTrade.showSuccess(msg);
                // 重新加载列表和统计
                loadStats();
                loadList(apiUrl, roleCode);
            },
            error: function(xhr) {
                var msg = '操作失败';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg = xhr.responseJSON.message;
                }
                SimTrade.showError(msg);
            }
        });
    }

    // ---------------------------------------------------------------
    // 点击统计卡片跳转到对应 tab
    // ---------------------------------------------------------------
    function initStatCardClick() {
        $(document).on('click', '#stats-row .stat-card', function() {
            var $card = $(this);
            var api = $card.data('api');

            // 验证属性存在性和有效性
            if (!api || api === '' || api === undefined || api === null) {
                console.log('No valid API found on stat card');
                return;
            }
            console.log('Stat card clicked, API:', api);

            // 查找匹配的 tab
            var $matchingTab = $('#workspace-tab-nav a[data-api="' + api + '"]');
            console.log('Matching tabs found:', $matchingTab.length);

            if ($matchingTab.length > 0) {
                console.log('Switching to tab:', $matchingTab.attr('href'));
                $matchingTab.tab('show');
            } else {
                console.log('No matching tab found for API:', api);
            }
        });
    }

    // ---------------------------------------------------------------
    // 初始化
    // ---------------------------------------------------------------
    function init() {
        var config = window.workspaceConfig;
        if (!config) return;

        // 初始化侧边栏
        initSidebar(config);

        // 初始化统计卡片点击
        initStatCardClick();

        // 加载统计
        loadStats();

        // 加载初始激活 tab 的列表
        var initialTabApi = getTabApi(1);
        if (initialTabApi) {
            loadList(initialTabApi, config.roleCode);
        }

        // Tab 切换：点击侧边栏导航切换 tab
        $(document).on('click', '#sidebar-nav a[data-sidebar-tab]', function(e) {
            e.preventDefault();
            var tabTarget = $(this).data('sidebar-tab');
            $('#workspace-tab-nav a[href="' + tabTarget + '"]').tab('show');

            // 更新 active 状态
            $('#sidebar-nav li').removeClass('active');
            $(this).closest('li').addClass('active');
        });

        // Tab 切换：Bootstrap tab 事件同步侧边栏
        $(document).on('shown.bs.tab', '#workspace-tab-nav a', function() {
            var tabTarget = $(this).attr('href');
            $('#sidebar-nav li').removeClass('active');
            $('#sidebar-nav a[data-sidebar-tab="' + tabTarget + '"]').closest('li').addClass('active');

            // 获取当前 tab 的 API URL
            var tabIndex = $(this).data('tab');
            var tabApi = getTabApi(tabIndex);

            // 检查是否是外部链接
            var isExternal = $(this).data('external');
            if (isExternal) {
                // 外部链接，跳转到指定页面
                window.location.href = $(this).attr('href');
                return;
            }

            // 加载当前 tab 的列表
            if (tabApi) {
                loadList(tabApi, config.roleCode);
            }
        });

        // 操作按钮点击
        $(document).on('click', '.action-btn[data-action]', function() {
            var $btn = $(this);
            var action = $btn.data('action');
            var itemId = $btn.data('item-id');

            if (!action || !itemId) return;

            if (confirm('确认执行此操作？')) {
                $btn.prop('disabled', true);
                executeAction(config.listApi, itemId, action, config.roleCode);
                $btn.prop('disabled', false);
            }
        });
    }

    $(document).ready(init);

})();
