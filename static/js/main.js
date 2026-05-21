/**
 * SimTrade Main JavaScript
 * 全局 AJAX 错误处理和工具函数
 */

(function() {
    'use strict';

    // ==========================================
    // CSRF Token 处理
    // ==========================================

    /**
     * 获取 CSRF token
     */
    function getCSRFToken() {
        // 优先从 cookie 中获取
        var cookie = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookieStr = jQuery.trim(cookies[i]);
                if (cookieStr.substring(0, 'csrftoken'.length + 1) === ('csrftoken=')) {
                    cookie = decodeURIComponent(cookieStr.substring('csrftoken'.length + 1));
                    break;
                }
            }
        }
        return cookie;
    }

    // 设置全局 AJAX 默认值
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader('X-CSRFToken', getCSRFToken());
            }
        },
        statusCode: {
            401: function() {
                // 未授权，跳转到登录页
                window.location.href = '/login/';
            },
            403: function() {
                // 禁止访问
                showError('您没有权限执行此操作');
            },
            404: function() {
                // 资源未找到
                showError('请求的资源不存在');
            },
            500: function() {
                // 服务器错误
                showError('服务器内部错误，请稍后重试');
            }
        }
    });

    // ==========================================
    // 错误处理
    // ==========================================

    /**
     * 显示错误信息
     * @param {string} message - 错误信息
     * @param {string} container - 容器选择器（可选）
     */
    function showError(message, container) {
        var $container = container ? $(container) : $('.main-content');
        var alertHtml = '<div class="alert alert-danger alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span></button>' +
            message +
            '</div>';

        // 移除已存在的错误提示
        $container.find('.alert-danger').remove();

        // 添加新的错误提示
        $container.prepend(alertHtml);

        // 5秒后自动消失
        setTimeout(function() {
            $container.find('.alert-danger').fadeOut(function() {
                $(this).remove();
            });
        }, 5000);
    }

    /**
     * 显示成功信息
     * @param {string} message - 成功信息
     * @param {string} container - 容器选择器（可选）
     */
    function showSuccess(message, container) {
        var $container = container ? $(container) : $('.main-content');
        var alertHtml = '<div class="alert alert-success alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span></button>' +
            message +
            '</div>';

        // 移除已存在的信息提示
        $container.find('.alert-success').remove();

        // 添加新的信息提示
        $container.prepend(alertHtml);

        // 3秒后自动消失
        setTimeout(function() {
            $container.find('.alert-success').fadeOut(function() {
                $(this).remove();
            });
        }, 3000);
    }

    /**
     * 显示警告信息
     * @param {string} message - 警告信息
     * @param {string} container - 容器选择器（可选）
     */
    function showWarning(message, container) {
        var $container = container ? $(container) : $('.main-content');
        var alertHtml = '<div class="alert alert-warning alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span></button>' +
            message +
            '</div>';

        // 移除已存在的警告提示
        $container.find('.alert-warning').remove();

        // 添加新的警告提示
        $container.prepend(alertHtml);

        // 4秒后自动消失
        setTimeout(function() {
            $container.find('.alert-warning').fadeOut(function() {
                $(this).remove();
            });
        }, 4000);
    }

    /**
     * 显示信息提示
     * @param {string} message - 提示信息
     * @param {string} container - 容器选择器（可选）
     */
    function showInfo(message, container) {
        var $container = container ? $(container) : $('.main-content');
        var alertHtml = '<div class="alert alert-info alert-dismissible" role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
            '<span aria-hidden="true">&times;</span></button>' +
            message +
            '</div>';

        // 移除已存在的信息提示
        $container.find('.alert-info').remove();

        // 添加新的信息提示
        $container.prepend(alertHtml);

        // 3秒后自动消失
        setTimeout(function() {
            $container.find('.alert-info').fadeOut(function() {
                $(this).remove();
            });
        }, 3000);
    }

    // ==========================================
    // 工具函数
    // ==========================================

    /**
     * 格式化日期时间
     * @param {string|Date} date - 日期对象或日期字符串
     * @param {string} format - 格式字符串（可选）
     * @returns {string} 格式化后的日期字符串
     */
    function formatDateTime(date, format) {
        format = format || 'YYYY-MM-DD HH:mm:ss';

        if (typeof date === 'string') {
            date = new Date(date);
        }

        var year = date.getFullYear();
        var month = String(date.getMonth() + 1).padStart(2, '0');
        var day = String(date.getDate()).padStart(2, '0');
        var hours = String(date.getHours()).padStart(2, '0');
        var minutes = String(date.getMinutes()).padStart(2, '0');
        var seconds = String(date.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    /**
     * 格式化数字
     * @param {number} num - 数字
     * @param {number} decimals - 小数位数
     * @returns {string} 格式化后的数字字符串
     */
    function formatNumber(num, decimals) {
        decimals = decimals || 2;
        return Number(num).toFixed(decimals);
    }

    /**
     * 格式化货币
     * @param {number} amount - 金额
     * @param {string} symbol - 货币符号
     * @returns {string} 格式化后的货币字符串
     */
    function formatCurrency(amount, symbol) {
        symbol = symbol || '¥';
        return symbol + formatNumber(amount, 2);
    }

    /**
     * 防抖函数
     * @param {Function} func - 要执行的函数
     * @param {number} wait - 等待时间（毫秒）
     * @returns {Function} 防抖后的函数
     */
    function debounce(func, wait) {
        var timeout;
        return function() {
            var context = this;
            var args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    }

    /**
     * 节流函数
     * @param {Function} func - 要执行的函数
     * @param {number} wait - 等待时间（毫秒）
     * @returns {Function} 节流后的函数
     */
    function throttle(func, wait) {
        var timeout;
        return function() {
            var context = this;
            var args = arguments;
            if (!timeout) {
                timeout = setTimeout(function() {
                    timeout = null;
                    func.apply(context, args);
                }, wait);
            }
        };
    }

    /**
     * 深拷贝对象
     * @param {Object} obj - 要拷贝的对象
     * @returns {Object} 拷贝后的对象
     */
    function deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    /**
     * 检查是否为空
     * @param {*} value - 要检查的值
     * @returns {boolean} 是否为空
     */
    function isEmpty(value) {
        if (value === null || value === undefined) {
            return true;
        }
        if (typeof value === 'string') {
            return value.trim() === '';
        }
        if (Array.isArray(value)) {
            return value.length === 0;
        }
        if (typeof value === 'object') {
            return Object.keys(value).length === 0;
        }
        return false;
    }

    // ==========================================
    // 全局初始化
    // ==========================================

    $(document).ready(function() {
        // 退出登录处理
        $('#logout-link').on('click', function(e) {
            e.preventDefault();
            $.ajax({
                url: '/api/logout/',
                type: 'POST',
                success: function(response) {
                    if (response.success) {
                        window.location.href = '/login/';
                    }
                },
                error: function() {
                    // 即使请求失败，也尝试跳转到登录页
                    window.location.href = '/login/';
                }
            });
        });

        // 自动隐藏 Django messages
        setTimeout(function() {
            $('.alert').fadeOut(function() {
                $(this).remove();
            });
        }, 5000);
    });

    // ==========================================
    // 导出到全局
    // ==========================================

    window.SimTrade = {
        showError: showError,
        showSuccess: showSuccess,
        showWarning: showWarning,
        showInfo: showInfo,
        formatDateTime: formatDateTime,
        formatNumber: formatNumber,
        formatCurrency: formatCurrency,
        debounce: debounce,
        throttle: throttle,
        deepClone: deepClone,
        isEmpty: isEmpty,
        getCSRFToken: getCSRFToken
    };

})();
