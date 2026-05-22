/**
 * SimTrade 交易模块脚本
 */

$(document).ready(function() {
    'use strict';

    // WebSocket 通知连接
    var notificationSocket;
    var socketRetryCount = 0;
    var maxRetryCount = 5;

    function connectNotificationSocket() {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        var host = window.location.host;
        var wsUrl = protocol + '//' + host + '/ws/notifications/';

        notificationSocket = new WebSocket(wsUrl);

        notificationSocket.onopen = function() {
            console.log('WebSocket connected');
            socketRetryCount = 0;
            // 发送心跳
            setInterval(function() {
                if (notificationSocket.readyState === WebSocket.OPEN) {
                    notificationSocket.send(JSON.stringify({type: 'ping'}));
                }
            }, 30000);
        };

        notificationSocket.onmessage = function(e) {
            var data = JSON.parse(e.data);
            handleNotification(data);
        };

        notificationSocket.onclose = function() {
            console.log('WebSocket disconnected');
            // 自动重连
            if (socketRetryCount < maxRetryCount) {
                socketRetryCount++;
                setTimeout(connectNotificationSocket, 3000);
            }
        };

        notificationSocket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
    }

    function handleNotification(data) {
        // 显示通知
        if (data.type === 'inquiry_received') {
            showNotification('收到新询盘', data.message, 'info');
        } else if (data.type === 'offer_received') {
            showNotification('收到新发盘', data.message, 'success');
        } else if (data.type === 'counter_offer_received') {
            showNotification('收到还盘', data.message, 'warning');
        }

        // 刷新当前页面数据（如果在交易列表页）
        if (typeof refreshTransactionList === 'function') {
            refreshTransactionList();
        }
    }

    function showNotification(title, message, type) {
        type = type || 'info';
        var alertHtml = `
            <div class="alert alert-${type} alert-dismissible notification-toast" role="alert">
                <button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>
                <strong>${title}</strong> ${message}
            </div>
        `;
        $('.container').prepend(alertHtml);
        setTimeout(function() {
            $('.notification-toast').fadeOut();
        }, 5000);
    }

    // 初始化 WebSocket
    if (window.user && window.user.is_authenticated) {
        connectNotificationSocket();
    }
});
