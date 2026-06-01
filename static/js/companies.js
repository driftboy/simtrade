/**
 * 公司列表和角色申请功能
 */
$(document).ready(function() {
    'use strict';

    // 全局数据
    var allCompanies = [];
    var allRoles = [];
    var myRoles = [];
    var appliedCompanyRoles = {}; // companyId -> roleCode

    // 加载数据
    loadCompanies();
    loadRoles();
    loadMyRoles();

    // ==================== 数据加载 ====================

    function loadCompanies() {
        $.get('/api/v1/companies/', function(resp) {
            allCompanies = resp.data || [];
            renderCompanies();
        }).fail(function() {
            $('#companyList').html('<div class="alert alert-danger">加载失败，请刷新页面重试</div>');
        });
    }

    function loadRoles() {
        $.get('/api/v1/roles/', function(resp) {
            allRoles = resp.data || [];
        }).fail(function() {
            console.error('Failed to load roles');
        });
    }

    function loadMyRoles() {
        $.get('/api/v1/my-roles/', function(resp) {
            myRoles = resp.data || [];
            // 记录已申请的公司-角色组合
            myRoles.forEach(function(r) {
                var key = r.company_id;
                if (!appliedCompanyRoles[key]) {
                    appliedCompanyRoles[key] = [];
                }
                appliedCompanyRoles[key].push(r.role_code);
            });
            renderCompanies();
        }).fail(function() {
            console.error('Failed to load my roles');
        });
    }

    // ==================== 渲染公司列表 ====================

    function renderCompanies() {
        var search = $('#searchInput').val().trim().toLowerCase();
        var typeFilter = $('#typeFilter').val();

        // 过滤
        var filtered = allCompanies.filter(function(c) {
            var matchSearch = !search ||
                (c.name && c.name.toLowerCase().indexOf(search) >= 0) ||
                (c.name_en && c.name_en.toLowerCase().indexOf(search) >= 0) ||
                (c.code && c.code.toLowerCase().indexOf(search) >= 0);
            var matchType = !typeFilter || c.type === typeFilter;
            return matchSearch && matchType;
        });

        // 渲染
        if (filtered.length === 0) {
            $('#companyList').html('' +
                '<div class="empty-state">' +
                '<span class="glyphicon glyphicon-inbox"></span>' +
                '<p>' + (allCompanies.length === 0 ? '暂无公司数据' : '没有匹配的公司') + '</p>' +
                '</div>');
            return;
        }

        var html = '';
        filtered.forEach(function(c) {
            var appliedRoles = appliedCompanyRoles[c.id] || [];
            var hasPending = appliedRoles.length > 0;

            html += '<div class="company-card" data-company-id="' + c.id + '">';

            // 头部
            html += '<div class="company-card-header">' +
                '<div>' +
                '<h3 class="company-card-title">' + SimTrade.escapeHtml(c.name) + '</h3>';
            if (c.name_en) {
                html += '<div class="company-card-title-en">' + SimTrade.escapeHtml(c.name_en) + '</div>';
            }
            html += '</div>' +
                '<span class="company-card-badge">' + SimTrade.escapeHtml(c.type || '未分类') + '</span>' +
                '</div>';

            // 信息行
            html += '<div class="company-card-info">';
            if (c.country_name) {
                html += '<div class="company-card-info-item">' +
                    '<span class="glyphicon glyphicon-map-marker"></span>' +
                    SimTrade.escapeHtml(c.country_name) +
                    '</div>';
            }
            if (c.code) {
                html += '<div class="company-card-info-item">' +
                    '<span class="glyphicon glyphicon-barcode"></span>' +
                    SimTrade.escapeHtml(c.code) +
                    '</div>';
            }
            html += '</div>';

            // 简介
            if (c.description) {
                html += '<div class="company-card-desc">' + SimTrade.escapeHtml(c.description) + '</div>';
            }

            // 底部
            var memberCount = c.members_count || 0;
            html += '<div class="company-card-footer">' +
                '<div class="company-card-members">' +
                '<span class="glyphicon glyphicon-user"></span> ' + memberCount + ' 人' +
                '</div>' +
                '<div class="company-card-actions">';

            if (hasPending) {
                html += '<button class="btn btn-applied" disabled>' +
                    '<span class="glyphicon glyphicon-time"></span> 已申请' +
                    '</button>';
            } else {
                html += '<button class="btn btn-primary btn-apply" data-company-id="' + c.id + '" data-company-name="' + SimTrade.escapeHtml(c.name) + '">' +
                    '<span class="glyphicon glyphicon-plus"></span> 申请加入' +
                    '</button>';
            }

            html += '</div></div></div>';
        });

        $('#companyList').html(html);
    }

    // ==================== 事件处理 ====================

    // 搜索
    $('#searchInput').on('input', function() {
        renderCompanies();
    });

    // 类型筛选
    $('#typeFilter').on('change', function() {
        renderCompanies();
    });

    // 刷新
    $('#refreshBtn').click(function() {
        loadCompanies();
        loadMyRoles();
    });

    // 打开申请模态框
    $(document).on('click', '.btn-apply', function() {
        var companyId = $(this).data('company-id');
        var companyName = $(this).data('company-name');

        $('#applyCompanyId').val(companyId);
        $('#modalCompanyName').text(companyName);
        $('#applyNotes').val('');
        $('#roleError').hide();

        // 渲染角色选项
        renderRoleOptions();

        $('#roleApplyModal').modal('show');
    });

    // 渲染角色选项
    function renderRoleOptions() {
        if (allRoles.length === 0) {
            $('#roleOptions').html('<div class="text-center text-muted">加载中...</div>');
            return;
        }

        var html = '';
        allRoles.forEach(function(r) {
            if (!r.is_enabled) return;
            html += '<label class="role-option">' +
                '<input type="radio" name="role_code" value="' + r.code + '">' +
                '<span class="role-option-code" data-role="' + r.code + '">' + r.code + '</span>' +
                '<span class="role-option-name">' + r.name + '</span>';
            if (r.description) {
                html += '<span class="role-option-desc">' + SimTrade.escapeHtml(r.description) + '</span>';
            }
            html += '</label>';
        });

        $('#roleOptions').html(html);
    }

    // 提交申请
    $('#submitApplyBtn').click(function() {
        var companyId = parseInt($('#applyCompanyId').val());
        var roleCode = $('input[name="role_code"]:checked').val();
        var notes = $('#applyNotes').val().trim();

        // 验证
        if (!roleCode) {
            $('#roleError').show();
            return;
        }
        $('#roleError').hide();

        // 禁用按钮
        var btn = $(this);
        btn.prop('disabled', true).text('提交中...');

        // 提交
        $.ajax({
            url: '/api/v1/roles/my-roles/request',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                company_id: companyId,
                role_code: roleCode,
                notes: notes
            }),
            success: function(resp) {
                $('#roleApplyModal').modal('hide');
                SimTrade.showSuccess('申请已提交，等待教师审核');
                // 重新加载
                loadMyRoles();
            },
            error: function(xhr) {
                var msg = '申请失败';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    msg = xhr.responseJSON.message;
                }
                alert(msg);
                btn.prop('disabled', false).text('提交申请');
            }
        });
    });

    // 模态框关闭时重置
    $('#roleApplyModal').on('hidden.bs.modal', function() {
        $('#submitApplyBtn').prop('disabled', false).text('提交申请');
    });
});
