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
    var pagination = {
        count: 0,
        next: null,
        previous: null,
        currentPage: 1,
        pageSize: 20
    };

    // 加载数据
    loadCompanies(1);
    loadRoles();
    loadMyRoles();

    // ==================== 数据加载 ====================

    function loadCompanies(page) {
        if (!page) page = 1;
        pagination.currentPage = page;

        // 获取筛选参数
        var search = $('#searchInput').val().trim();
        var typeFilter = $('#typeFilter').val();

        // 构建 URL 参数
        var params = 'page=' + page + '&page_size=' + pagination.pageSize;
        if (search) params += '&search=' + encodeURIComponent(search);
        if (typeFilter) params += '&type=' + encodeURIComponent(typeFilter);

        $.get('/api/v1/companies/?' + params, function(resp) {
            // DRF 标准分页格式
            if (resp.results) {
                allCompanies = resp.results || [];
                pagination.count = resp.count || 0;
                pagination.next = resp.next;
                pagination.previous = resp.previous;
            } else {
                // 兼容旧格式（如果后端还没更新）
                allCompanies = [];
                pagination.count = 0;
            }
            renderCompanies();
            renderPagination();
        }).fail(function() {
            $('#companyList').html('<div class="alert alert-danger">加载失败，请刷新页面重试</div>');
        });
    }

    function renderPagination() {
        var totalPages = Math.ceil(pagination.count / pagination.pageSize);
        if (totalPages <= 1) {
            $('.pagination-bar').remove();
            return;
        }

        // 移除旧的分页栏
        $('.pagination-bar').remove();

        var html = '<div class="pagination-bar text-center" style="margin: 20px 0;">';
        html += '<nav><ul class="pagination">';

        // 上一页
        if (pagination.previous) {
            html += '<li><a href="#" data-page="' + (pagination.currentPage - 1) + '">&laquo; 上一页</a></li>';
        } else {
            html += '<li class="disabled"><span>&laquo; 上一页</span></li>';
        }

        // 页码
        var startPage = Math.max(1, pagination.currentPage - 2);
        var endPage = Math.min(totalPages, pagination.currentPage + 2);

        if (startPage > 1) {
            html += '<li><a href="#" data-page="1">1</a></li>';
            if (startPage > 2) html += '<li class="disabled"><span>...</span></li>';
        }

        for (var i = startPage; i <= endPage; i++) {
            if (i === pagination.currentPage) {
                html += '<li class="active"><span>' + i + ' <span class="sr-only">(current)</span></span></li>';
            } else {
                html += '<li><a href="#" data-page="' + i + '">' + i + '</a></li>';
            }
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) html += '<li class="disabled"><span>...</span></li>';
            html += '<li><a href="#" data-page="' + totalPages + '">' + totalPages + '</a></li>';
        }

        // 下一页
        if (pagination.next) {
            html += '<li><a href="#" data-page="' + (pagination.currentPage + 1) + '">下一页 &raquo;</a></li>';
        } else {
            html += '<li class="disabled"><span>下一页 &raquo;</span></li>';
        }

        html += '</ul></nav>';
        html += '<div class="text-muted" style="margin-top: 10px; font-size: 13px;">';
        html += '共 ' + pagination.count + ' 条记录，第 ' + pagination.currentPage + '/' + totalPages + ' 页';
        html += '</div></div>';

        $('#companyList').after(html);
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
        // 后端已处理筛选和分页，直接渲染
        if (allCompanies.length === 0) {
            $('#companyList').html('' +
                '<div class="empty-state">' +
                '<span class="glyphicon glyphicon-inbox"></span>' +
                '<p>' + (pagination.count === 0 ? '暂无公司数据' : '没有匹配的公司') + '</p>' +
                '</div>');
            return;
        }

        var html = '';
        allCompanies.forEach(function(c) {
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

    // 搜索（实时）- 使用防抖
    var searchTimeout;
    $('#searchInput').on('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function() {
            loadCompanies(1);
        }, 300);
    });

    // 类型筛选（实时）
    $('#typeFilter').on('change', function() {
        loadCompanies(1);
    });

    // 查询按钮
    $('#queryBtn').click(function() {
        var btn = $(this);
        var originalText = btn.html();
        btn.prop('disabled', true).html('<span class="glyphicon glyphicon-hourglass"></span> 查询中...');
        loadCompanies(1);
        setTimeout(function() {
            btn.prop('disabled', false).html(originalText);
        }, 300);
    });

    // 刷新
    $('#refreshBtn').click(function() {
        var btn = $(this);
        var originalText = btn.html();
        btn.prop('disabled', true).html('<span class="glyphicon glyphicon-hourglass"></span> 刷新中...');
        loadCompanies(1);
        loadMyRoles();
        setTimeout(function() {
            btn.prop('disabled', false).html(originalText);
        }, 500);
    });

    // 分页点击
    $(document).on('click', '.pagination-bar a', function(e) {
        e.preventDefault();
        var page = $(this).data('page');
        if (page) {
            loadCompanies(page);
            $('html, body').animate({ scrollTop: $('#companyList').offset().top - 100 }, 300);
        }
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
            url: '/api/v1/my-roles/request/',
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
