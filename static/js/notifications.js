(function() {
    'use strict';

    function updateBadge(count) {
        var $badge = $('#notif-badge');
        if (count > 0) {
            $badge.text(count > 99 ? '99+' : count).show();
        } else {
            $badge.hide();
        }
    }

    function renderNotification(item) {
        var unreadClass = item.is_read ? '' : ' unread';
        var time = SimTrade.formatDateTime(item.created_at, 'MM-DD HH:mm');
        return '<li class="notification-item' + unreadClass + '" data-id="' + item.id + '">' +
            '<div class="notif-type">' + SimTrade.escapeHtml(item.type_display) + '</div>' +
            '<div class="notif-title">' + SimTrade.escapeHtml(item.title) + '</div>' +
            '<div class="notif-time">' + time + '</div>' +
            '</li>';
    }

    function renderEmpty() {
        return '<li class="notification-empty">暂无通知</li>';
    }

    function loadNotifications() {
        $.get('/api/v1/notifications/', {is_read: 'false'}, function(resp) {
            var $menu = $('#notif-dropdown-menu');
            $menu.empty();
            var data = resp.data || [];
            if (data.length === 0) {
                $menu.append(renderEmpty());
            } else {
                for (var i = 0; i < Math.min(data.length, 10); i++) {
                    $menu.append(renderNotification(data[i]));
                }
                if (data.length > 10) {
                    $menu.append('<li class="notif-footer">还有 ' + (data.length - 10) + ' 条通知</li>');
                }
            }
        });
    }

    function init() {
        if (!window.user || !window.user.is_authenticated) return;

        $.get('/api/v1/notifications/unread-count/', function(resp) {
            updateBadge(resp.data.count);
        });

        $('#notif-dropdown').on('show.bs.dropdown', function() {
            loadNotifications();
        });

        $(document).on('click', '#notif-dropdown-menu .notification-item', function() {
            var id = $(this).data('id');
            $.post('/api/v1/notifications/' + id + '/read/');
            $(this).removeClass('unread');
            var count = parseInt($('#notif-badge').text()) || 0;
            updateBadge(Math.max(0, count - 1));
        });
    }

    $(document).ready(init);
})();
