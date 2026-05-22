/**
 * SimTrade 单证模块脚本
 */

$(document).ready(function() {
    'use strict';

    // 全局初始化
    initDocumentsModule();
});

function initDocumentsModule() {
    // 初始化日期选择器
    if ($.fn.datepicker) {
        $('input[type="date"]').datepicker({
            format: 'yyyy-mm-dd',
            autoclose: true
        });
    }

    // 初始化自动保存
    initAutoSave();
}

// 自动保存草稿
function initAutoSave() {
    var saveTimer;
    $('form#documentForm').on('change', 'input, textarea, select', function() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(function() {
            if (typeof saveDraft === 'function') {
                if (currentDocumentId) {
                    saveDraft();
                }
            }
        }, 3000);
    });
}

// 格式化日期
function formatDate(dateStr) {
    if (!dateStr) return '';
    var date = new Date(dateStr);
    return date.toISOString().split('T')[0];
}

// 格式化金额
function formatAmount(amount) {
    if (!amount) return '0.00';
    return parseFloat(amount).toFixed(2);
}

// 显示加载状态
function showLoading(container) {
    $(container).html('<div class="text-center"><i class="glyphicon glyphicon-refresh spinning"></i> 加载中...</div>');
}

// 显示错误消息
function showError(container, message) {
    $(container).html('<div class="alert alert-danger">' + message + '</div>');
}

// 旋转动画样式
if ($('.spinning').length === 0) {
    $('<style>.spinning { animation: spin 1s linear infinite; } @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }</style>').appendTo('head');
}
