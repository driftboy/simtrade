/**
 * Sidebar Navigation JavaScript
 * 处理侧边栏折叠/展开功能
 */

(function() {
    'use strict';

    // Sidebar state management
    var SIDEBAR_STATE_KEY = 'sidebar_state';

    /**
     * Get sidebar state from localStorage
     * @returns {string} 'expanded' or 'collapsed'
     */
    function getSidebarState() {
        try {
            return localStorage.getItem(SIDEBAR_STATE_KEY) || 'expanded';
        } catch (e) {
            return 'expanded';
        }
    }

    /**
     * Save sidebar state to localStorage
     * @param {string} state - 'expanded' or 'collapsed'
     */
    function saveSidebarState(state) {
        try {
            localStorage.setItem(SIDEBAR_STATE_KEY, state);
        } catch (e) {
            // Ignore storage errors
        }
    }

    /**
     * Toggle sidebar state
     */
    function toggleSidebar() {
        var currentState = getSidebarState();
        var newState = currentState === 'expanded' ? 'collapsed' : 'expanded';

        // Update body class
        document.body.classList.remove('sidebar-' + currentState);
        document.body.classList.add('sidebar-' + newState);

        // Save state
        saveSidebarState(newState);

        // Trigger custom event
        $(document).trigger('sidebarToggled', { state: newState });
    }

    /**
     * Initialize sidebar
     */
    function initSidebar() {
        var state = getSidebarState();

        // Set initial state
        document.body.classList.remove('sidebar-expanded', 'sidebar-collapsed');
        document.body.classList.add('sidebar-' + state);

        // Add data-title attributes for tooltip in collapsed state
        $('.menu-link').each(function() {
            var $link = $(this);
            var text = $link.find('.menu-text').text();
            $link.attr('data-title', text);
        });

        // Highlight active menu item based on current path
        var currentPath = window.location.pathname;
        $('.menu-link').each(function() {
            var $link = $(this);
            var href = $link.attr('href');
            if (href && currentPath.indexOf(href) === 0) {
                $link.addClass('active');
                // For exact match, remove active from others
                if (currentPath === href) {
                    $('.menu-link').not($link).removeClass('active');
                }
            }
        });
    }

    // ==========================================
    // Event Handlers
    // ==========================================

    $(document).ready(function() {
        // Initialize sidebar state
        initSidebar();

        // Toggle button click handler
        $('#sidebar-toggle').on('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });

        // Close sidebar on mobile when clicking overlay
        $('.sidebar-overlay').on('click', function() {
            if ($(window).width() <= 768) {
                document.body.classList.remove('sidebar-expanded');
                document.body.classList.add('sidebar-collapsed');
                saveSidebarState('collapsed');
            }
        });

        // Handle window resize
        var resizeTimer;
        $(window).on('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                if ($(window).width() > 768) {
                    // On desktop, ensure sidebar is visible
                    var state = getSidebarState();
                    document.body.classList.remove('sidebar-expanded', 'sidebar-collapsed');
                    document.body.classList.add('sidebar-' + state);
                } else {
                    // On mobile, collapse by default
                    document.body.classList.remove('sidebar-expanded');
                    document.body.classList.add('sidebar-collapsed');
                }
            }, 100);
        });

        // Add mobile overlay element if not exists
        if ($('.sidebar-overlay').length === 0) {
            $('body').append('<div class="sidebar-overlay"></div>');
        }
    });

    // ==========================================
    // Export to global
    // ==========================================

    window.Sidebar = {
        toggle: toggleSidebar,
        getState: getSidebarState,
        setState: function(state) {
            if (state === 'expanded' || state === 'collapsed') {
                document.body.classList.remove('sidebar-expanded', 'sidebar-collapsed');
                document.body.classList.add('sidebar-' + state);
                saveSidebarState(state);
            }
        }
    };

})();
