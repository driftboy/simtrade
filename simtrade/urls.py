from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from apps.documents.models import Document, DocumentTemplate
from apps.roles.services import RoleService


# ---------------------------------------------------------------------------
# Panel type mapping: role_code -> panel category
# ---------------------------------------------------------------------------
PANEL_MAP = {
    'exporter': 'trader',
    'importer': 'trader',
    'customs': 'approver',
    'inspection': 'approver',
    'forex': 'approver',
    'tax': 'approver',
    'factory': 'provider',
    'bank': 'provider',
    'shipping': 'provider',
    'insurance': 'provider',
}

# ---------------------------------------------------------------------------
# Role workspace configurations
# ---------------------------------------------------------------------------
ROLE_CONFIGS = {
    'exporter': {
        'nav_items': [
            {'label': 'My Orders', 'icon': 'bi-box-seam', 'href': '/workspace/exporter/'},
            {'label': 'Create Contract', 'icon': 'bi-file-earmark-plus', 'href': '/workspace/exporter/'},
            {'label': 'Shipments', 'icon': 'bi-truck', 'href': '/workspace/exporter/'},
            {'label': 'Documents', 'icon': 'bi-folder2-open', 'href': '/documents/'},
        ],
        'actions': [
            {'label': 'Create Sales Contract', 'icon': 'bi-plus-circle', 'api': '/api/v1/contracts/', 'method': 'POST'},
            {'label': 'Apply for Inspection', 'icon': 'bi-clipboard-check', 'api': '/api/v1/inspection-applications/', 'method': 'POST'},
            {'label': 'Declare Export', 'icon': 'bi-flag', 'api': '/api/v1/customs-declarations/', 'method': 'POST'},
            {'label': 'Apply Tax Refund', 'icon': 'bi-cash-stack', 'api': '/api/v1/tax-refund-applications/', 'method': 'POST'},
        ],
        'stats': [
            {'label': 'Active Orders', 'icon': 'bi-box-seam', 'api': '/api/v1/purchase-orders/', 'color': 'primary'},
            {'label': 'Pending Shipments', 'icon': 'bi-truck', 'api': '/api/v1/shipments/', 'color': 'info'},
            {'label': 'Contracts', 'icon': 'bi-file-earmark-text', 'api': '/api/v1/contracts/', 'color': 'success'},
            {'label': 'Tax Refunds', 'icon': 'bi-cash-stack', 'api': '/api/v1/tax-refund-applications/', 'color': 'warning'},
        ],
        'list_api': '/api/v1/purchase-orders/',
        'panel': 'trader',
    },
    'importer': {
        'nav_items': [
            {'label': 'My Orders', 'icon': 'bi-bag-check', 'href': '/workspace/importer/'},
            {'label': 'Contracts', 'icon': 'bi-file-earmark-text', 'href': '/workspace/importer/'},
            {'label': 'Shipments', 'icon': 'bi-truck', 'href': '/workspace/importer/'},
            {'label': 'Documents', 'icon': 'bi-folder2-open', 'href': '/documents/'},
        ],
        'actions': [
            {'label': 'Create Purchase Order', 'icon': 'bi-plus-circle', 'api': '/api/v1/purchase-orders/', 'method': 'POST'},
            {'label': 'Apply for L/C', 'icon': 'bi-bank', 'api': '/api/v1/letters-of-credit/', 'method': 'POST'},
            {'label': 'Declare Import', 'icon': 'bi-flag', 'api': '/api/v1/customs-declarations/', 'method': 'POST'},
            {'label': 'Forex Settlement', 'icon': 'bi-currency-exchange', 'api': '/api/v1/forex-settlements/', 'method': 'POST'},
        ],
        'stats': [
            {'label': 'Purchase Orders', 'icon': 'bi-bag-check', 'api': '/api/v1/purchase-orders/', 'color': 'primary'},
            {'label': 'Pending L/C', 'icon': 'bi-bank', 'api': '/api/v1/letters-of-credit/', 'color': 'info'},
            {'label': 'Shipments', 'icon': 'bi-truck', 'api': '/api/v1/shipments/', 'color': 'success'},
            {'label': 'Forex Settlements', 'icon': 'bi-currency-exchange', 'api': '/api/v1/forex-settlements/', 'color': 'warning'},
        ],
        'list_api': '/api/v1/purchase-orders/',
        'panel': 'trader',
    },
    'customs': {
        'nav_items': [
            {'label': 'Declarations', 'icon': 'bi-clipboard-data', 'href': '/workspace/customs/'},
            {'label': 'Pending Review', 'icon': 'bi-hourglass-split', 'href': '/workspace/customs/'},
            {'label': 'History', 'icon': 'bi-clock-history', 'href': '/workspace/customs/'},
        ],
        'actions': [
            {'label': 'Approve Declaration', 'icon': 'bi-check-circle', 'api': '/api/v1/customs-declarations/', 'method': 'PATCH'},
            {'label': 'Reject Declaration', 'icon': 'bi-x-circle', 'api': '/api/v1/customs-declarations/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'api': '/api/v1/customs-declarations/', 'color': 'warning'},
            {'label': 'Approved Today', 'icon': 'bi-check-circle', 'api': '/api/v1/customs-declarations/', 'color': 'success'},
            {'label': 'Total Processed', 'icon': 'bi-clipboard-data', 'api': '/api/v1/customs-declarations/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/customs-declarations/',
        'panel': 'approver',
    },
    'inspection': {
        'nav_items': [
            {'label': 'Applications', 'icon': 'bi-clipboard-check', 'href': '/workspace/inspection/'},
            {'label': 'Pending Review', 'icon': 'bi-hourglass-split', 'href': '/workspace/inspection/'},
            {'label': 'Certificates', 'icon': 'bi-award', 'href': '/workspace/inspection/'},
        ],
        'actions': [
            {'label': 'Approve Application', 'icon': 'bi-check-circle', 'api': '/api/v1/inspection-applications/', 'method': 'PATCH'},
            {'label': 'Reject Application', 'icon': 'bi-x-circle', 'api': '/api/v1/inspection-applications/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'api': '/api/v1/inspection-applications/', 'color': 'warning'},
            {'label': 'Issued Certificates', 'icon': 'bi-award', 'api': '/api/v1/inspection-applications/', 'color': 'success'},
            {'label': 'Total Processed', 'icon': 'bi-clipboard-check', 'api': '/api/v1/inspection-applications/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/inspection-applications/',
        'panel': 'approver',
    },
    'forex': {
        'nav_items': [
            {'label': 'Settlements', 'icon': 'bi-currency-exchange', 'href': '/workspace/forex/'},
            {'label': 'Pending Review', 'icon': 'bi-hourglass-split', 'href': '/workspace/forex/'},
            {'label': 'History', 'icon': 'bi-clock-history', 'href': '/workspace/forex/'},
        ],
        'actions': [
            {'label': 'Approve Settlement', 'icon': 'bi-check-circle', 'api': '/api/v1/forex-settlements/', 'method': 'PATCH'},
            {'label': 'Reject Settlement', 'icon': 'bi-x-circle', 'api': '/api/v1/forex-settlements/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'api': '/api/v1/forex-settlements/', 'color': 'warning'},
            {'label': 'Settled Today', 'icon': 'bi-check-circle', 'api': '/api/v1/forex-settlements/', 'color': 'success'},
            {'label': 'Total Settled', 'icon': 'bi-currency-exchange', 'api': '/api/v1/forex-settlements/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/forex-settlements/',
        'panel': 'approver',
    },
    'tax': {
        'nav_items': [
            {'label': 'Refund Applications', 'icon': 'bi-cash-stack', 'href': '/workspace/tax/'},
            {'label': 'Pending Review', 'icon': 'bi-hourglass-split', 'href': '/workspace/tax/'},
            {'label': 'History', 'icon': 'bi-clock-history', 'href': '/workspace/tax/'},
        ],
        'actions': [
            {'label': 'Approve Refund', 'icon': 'bi-check-circle', 'api': '/api/v1/tax-refund-applications/', 'method': 'PATCH'},
            {'label': 'Reject Refund', 'icon': 'bi-x-circle', 'api': '/api/v1/tax-refund-applications/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'api': '/api/v1/tax-refund-applications/', 'color': 'warning'},
            {'label': 'Approved Today', 'icon': 'bi-check-circle', 'api': '/api/v1/tax-refund-applications/', 'color': 'success'},
            {'label': 'Total Refunded', 'icon': 'bi-cash-stack', 'api': '/api/v1/tax-refund-applications/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/tax-refund-applications/',
        'panel': 'approver',
    },
    'factory': {
        'nav_items': [
            {'label': 'Product Catalog', 'icon': 'bi-boxes', 'href': '/workspace/factory/'},
            {'label': 'Orders', 'icon': 'bi-bag', 'href': '/workspace/factory/'},
            {'label': 'Production', 'icon': 'bi-gear', 'href': '/workspace/factory/'},
        ],
        'actions': [
            {'label': 'Add Product', 'icon': 'bi-plus-circle', 'api': '/api/v1/products/products/', 'method': 'POST'},
            {'label': 'Update Catalog', 'icon': 'bi-pencil', 'api': '/api/v1/products/catalogs/', 'method': 'POST'},
        ],
        'stats': [
            {'label': 'Products', 'icon': 'bi-boxes', 'api': '/api/v1/products/products/', 'color': 'primary'},
            {'label': 'Catalogs', 'icon': 'bi-book', 'api': '/api/v1/products/catalogs/', 'color': 'success'},
            {'label': 'Active Orders', 'icon': 'bi-bag', 'api': '/api/v1/purchase-orders/', 'color': 'info'},
        ],
        'list_api': '/api/v1/products/products/',
        'panel': 'provider',
    },
    'bank': {
        'nav_items': [
            {'label': 'L/C Applications', 'icon': 'bi-bank', 'href': '/workspace/bank/'},
            {'label': 'Pending Review', 'icon': 'bi-hourglass-split', 'href': '/workspace/bank/'},
            {'label': 'Issued L/C', 'icon': 'bi-file-earmark-text', 'href': '/workspace/bank/'},
        ],
        'actions': [
            {'label': 'Issue L/C', 'icon': 'bi-check-circle', 'api': '/api/v1/letters-of-credit/', 'method': 'PATCH'},
            {'label': 'Reject L/C', 'icon': 'bi-x-circle', 'api': '/api/v1/letters-of-credit/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending L/C', 'icon': 'bi-hourglass-split', 'api': '/api/v1/letters-of-credit/', 'color': 'warning'},
            {'label': 'Issued Today', 'icon': 'bi-check-circle', 'api': '/api/v1/letters-of-credit/', 'color': 'success'},
            {'label': 'Total Issued', 'icon': 'bi-bank', 'api': '/api/v1/letters-of-credit/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/letters-of-credit/',
        'panel': 'provider',
    },
    'shipping': {
        'nav_items': [
            {'label': 'Shipments', 'icon': 'bi-truck', 'href': '/workspace/shipping/'},
            {'label': 'Pending Bookings', 'icon': 'bi-hourglass-split', 'href': '/workspace/shipping/'},
            {'label': 'B/L Issued', 'icon': 'bi-file-earmark-text', 'href': '/workspace/shipping/'},
        ],
        'actions': [
            {'label': 'Accept Shipment', 'icon': 'bi-check-circle', 'api': '/api/v1/shipments/', 'method': 'PATCH'},
            {'label': 'Issue B/L', 'icon': 'bi-file-earmark-plus', 'api': '/api/v1/shipments/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'api': '/api/v1/shipments/', 'color': 'warning'},
            {'label': 'In Transit', 'icon': 'bi-truck', 'api': '/api/v1/shipments/', 'color': 'info'},
            {'label': 'Delivered', 'icon': 'bi-check-circle', 'api': '/api/v1/shipments/', 'color': 'success'},
        ],
        'list_api': '/api/v1/shipments/',
        'panel': 'provider',
    },
    'insurance': {
        'nav_items': [
            {'label': 'Applications', 'icon': 'bi-shield-check', 'href': '/workspace/insurance/'},
            {'label': 'Pending Review', 'icon': 'bi-hourglass-split', 'href': '/workspace/insurance/'},
            {'label': 'Policies', 'icon': 'bi-file-earmark-text', 'href': '/workspace/insurance/'},
        ],
        'actions': [
            {'label': 'Issue Policy', 'icon': 'bi-check-circle', 'api': '/api/v1/insurance-policies/', 'method': 'PATCH'},
            {'label': 'Reject Application', 'icon': 'bi-x-circle', 'api': '/api/v1/insurance-policies/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'api': '/api/v1/insurance-policies/', 'color': 'warning'},
            {'label': 'Issued Policies', 'icon': 'bi-shield-check', 'api': '/api/v1/insurance-policies/', 'color': 'success'},
            {'label': 'Total Processed', 'icon': 'bi-clipboard-data', 'api': '/api/v1/insurance-policies/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/insurance-policies/',
        'panel': 'provider',
    },
}


# ---------------------------------------------------------------------------
# Page view functions
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    """根据用户类型分发仪表盘"""
    user_type = request.user.user_type
    if user_type == 'admin':
        return render(request, 'dashboard/admin.html', {'user': request.user})
    elif user_type == 'teacher':
        return render(request, 'dashboard/teacher.html', {'user': request.user})
    return render(request, 'dashboard/student.html', {'user': request.user})


@login_required
def workspace_view(request, role_code=None):
    """Workspace page - role-specific workbench"""
    current_role = RoleService.get_current_role(request.user)

    # If a specific role_code is requested via URL, use it
    if role_code is None and current_role:
        role_code = current_role.role.code

    # No role at all
    if not role_code and not current_role:
        return render(request, 'workspace/workspace.html', {
            'no_role': True,
            'user': request.user,
        })

    # Validate role_code exists in config
    role_config = ROLE_CONFIGS.get(role_code)
    if not role_config:
        return render(request, 'workspace/workspace.html', {
            'no_role': True,
            'user': request.user,
            'invalid_role': role_code,
        })

    panel_type = PANEL_MAP.get(role_code, 'trader')
    panel_template = 'workspace/panels/{}.html'.format(panel_type)

    context = {
        'role_code': role_code,
        'role_config': role_config,
        'panel_template': panel_template,
        'panel_type': panel_type,
        'current_role': current_role,
        'user': request.user,
        'list_api': role_config.get('list_api', ''),
        'stats': role_config.get('stats', []),
        'actions': role_config.get('actions', []),
        'nav_items': role_config.get('nav_items', []),
    }
    return render(request, 'workspace/workspace.html', context)


@login_required
def profile_view(request):
    """User profile page"""
    current_role = RoleService.get_current_role(request.user)
    return render(request, 'profile.html', {
        'user': request.user,
        'current_role': current_role,
    })


def register_view(request):
    """Registration page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'registration/register.html')


@login_required
def teaching_dashboard(request):
    """Teaching module dashboard"""
    return render(request, 'teaching/dashboard.html', {'user': request.user})


@login_required
def teaching_course_list(request):
    """Course list page"""
    return render(request, 'teaching/courses.html', {'user': request.user})


@login_required
def teaching_course_detail(request, course_id):
    """Course detail page"""
    return render(request, 'teaching/course_detail.html', {
        'user': request.user,
        'course_id': course_id,
    })


@login_required
def teaching_grading(request):
    """Grading page"""
    return render(request, 'teaching/grading.html', {'user': request.user})


@login_required
def admin_panel_dashboard(request):
    """Admin panel dashboard"""
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_panel/dashboard.html', {'user': request.user})


@login_required
def admin_panel_users(request):
    """Admin panel user management"""
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_panel/user_list.html', {'user': request.user})


@login_required
def admin_panel_system(request):
    """Admin panel system settings"""
    if not request.user.is_staff:
        return redirect('dashboard')
    return render(request, 'admin_panel/system.html', {'user': request.user})


# ---------------------------------------------------------------------------
# Document management temp views
# ---------------------------------------------------------------------------
def document_create(request):
    """Document create page - temp implementation"""
    templates = DocumentTemplate.objects.filter(is_active=True)
    return render(request, 'documents/create.html', {'templates': templates})


def document_preview(request, id):
    """Document preview page - temp implementation"""
    try:
        document = Document.objects.get(pk=id)
    except Document.DoesNotExist:
        return HttpResponse('Document not found', status=404)
    return render(request, 'documents/preview.html', {'document': document})


# ---------------------------------------------------------------------------
# URL patterns - API routes
# ---------------------------------------------------------------------------
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/documents/', include('apps.documents.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/', include('apps.transactions.urls')),
    path('api/v1/', include('apps.roles.urls')),
    path('api/v1/scoring/', include('apps.scoring.urls')),
    path('api/v1/teaching/', include('apps.teaching.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ---------------------------------------------------------------------------
# URL patterns - Page routes
# ---------------------------------------------------------------------------
urlpatterns += [
    path('', dashboard_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('workspace/', workspace_view, name='workspace'),
    path('workspace/<str:role_code>/', workspace_view, name='workspace-role'),
    # Market & transactions
    path('market/', lambda r: render(r, 'products/market.html'), name='market'),
    path('transactions/', lambda r: render(r, 'transactions/list.html'), name='transaction-list'),
    path('transactions/<int:id>/', lambda r, id: render(r, 'transactions/detail.html'), name='transaction-detail'),
    # Documents
    path('documents/', lambda r: render(r, 'documents/list.html'), name='document-list'),
    path('documents/create/', document_create, name='document-create'),
    path('documents/<int:id>/preview/', document_preview, name='document-preview'),
    # Teaching module
    path('teaching/', teaching_dashboard, name='teaching-dashboard'),
    path('teaching/courses/', teaching_course_list, name='teaching-courses'),
    path('teaching/courses/<int:course_id>/', teaching_course_detail, name='teaching-course-detail'),
    path('teaching/grading/', teaching_grading, name='teaching-grading'),
    # Admin panel
    path('admin-panel/', admin_panel_dashboard, name='admin-dashboard'),
    path('admin-panel/users/', admin_panel_users, name='admin-users'),
    path('admin-panel/system/', admin_panel_system, name='admin-system'),
    # Auth & profile
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', register_view, name='register'),
    path('profile/', profile_view, name='profile'),
]
