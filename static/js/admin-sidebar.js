/**
 * Admin Sidebar Navigation
 */
(function() {
    'use strict';

    // Menu configuration
    var MENU_ITEMS = [
        { path: '/admin/', icon: 'home', label: '概览' },
        { path: '/admin/users/', icon: 'user', label: '用户管理' },
        { path: '/admin/system/', icon: 'cog', label: '系统设置' }
    ];

    /**
     * Get current page info from path
     */
    function getCurrentPage() {
        var path = window.location.pathname;
        for (var i = 0; i < MENU_ITEMS.length; i++) {
            if (path.indexOf(MENU_ITEMS[i].path) === 0) {
                return MENU_ITEMS[i];
            }
        }
        return MENU_ITEMS[0]; // Default to overview
    }

    /**
     * Generate breadcrumb HTML
     */
    function generateBreadcrumb() {
        var current = getCurrentPage();
        var html = '<ol class="breadcrumb">' +
            '<li><a href="/">首页</a></li>' +
            '<li><a href="/admin/">管理后台</a></li>' +
            '<li class="active">' + current.label + '</li>' +
            '</ol>';
        return html;
    }

    /**
     * Set active menu item
     */
    function setActiveMenu() {
        var path = window.location.pathname;
        $('.admin-sidebar .list-group-item').each(function() {
            var href = $(this).attr('href');
            if (href && path.indexOf(href) === 0) {
                $(this).addClass('active');
            } else {
                $(this).removeClass('active');
            }
        });
    }

    /**
     * Initialize sidebar
     */
    function initSidebar() {
        // Render breadcrumb
        var breadcrumbHtml = generateBreadcrumb();
        $('.admin-breadcrumb').html(breadcrumbHtml);

        // Set active menu
        setActiveMenu();
    };

    // Export for external use
    window.AdminSidebar = {
        init: initSidebar,
        getCurrentPage: getCurrentPage,
        generateBreadcrumb: generateBreadcrumb,
        setActiveMenu: setActiveMenu
    };

    // Auto-initialize on document ready
    $(document).ready(function() {
        if ($('.admin-sidebar').length > 0) {
            initSidebar();
        }
    });

})();
