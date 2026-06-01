from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse, JsonResponse
import json
from django.contrib.auth.decorators import login_required
from apps.documents.models import Document, DocumentTemplate
from apps.transactions.models import Transaction
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
            {'label': '我的订单 (Orders)', 'icon': 'bi-box-seam', 'href': '/workspace/exporter/', 'api': '/api/v1/purchase-orders/'},
            {'label': '销售合同 (Contracts)', 'icon': 'bi-file-earmark-text', 'href': '/workspace/exporter/', 'api': '/api/v1/contracts/'},
            {'label': '货运单证 (Shipments)', 'icon': 'bi-truck', 'href': '/workspace/exporter/', 'api': '/api/v1/shipments/'},
            {'label': '贸易单证 (Documents)', 'icon': 'bi-folder2-open', 'href': '/documents/', 'external': True},
        ],
        'actions': [
            {'label': '创建销售合同', 'icon': 'bi-plus-circle', 'api': '/api/v1/contracts/', 'method': 'POST'},
            {'label': '申请报检', 'icon': 'bi-clipboard-check', 'api': '/api/v1/inspection-applications/', 'method': 'POST'},
            {'label': '出口报关', 'icon': 'bi-flag', 'api': '/api/v1/customs-declarations/', 'method': 'POST'},
            {'label': '申请退税', 'icon': 'bi-cash-stack', 'api': '/api/v1/tax-refund-applications/', 'method': 'POST'},
        ],
        'stats': [
            {'label': '活跃订单', 'icon': 'bi-box-seam', 'api': '/api/v1/purchase-orders/', 'color': 'primary'},
            {'label': '待运货运', 'icon': 'bi-truck', 'api': '/api/v1/shipments/', 'color': 'info'},
            {'label': '销售合同', 'icon': 'bi-file-earmark-text', 'api': '/api/v1/contracts/', 'color': 'success'},
            {'label': '退税申请', 'icon': 'bi-cash-stack', 'api': '/api/v1/tax-refund-applications/', 'color': 'warning'},
        ],
        'list_api': '/api/v1/purchase-orders/',
        'panel': 'trader',
    },
    'importer': {
        'nav_items': [
            {'label': '采购订单 (Orders)', 'icon': 'bi-bag-check', 'href': '/workspace/importer/'},
            {'label': '采购合同 (Contracts)', 'icon': 'bi-file-earmark-text', 'href': '/workspace/importer/'},
            {'label': '货运单证 (Shipments)', 'icon': 'bi-truck', 'href': '/workspace/importer/'},
            {'label': '贸易单证 (Documents)', 'icon': 'bi-folder2-open', 'href': '/documents/'},
        ],
        'actions': [
            {'label': '创建采购订单', 'icon': 'bi-plus-circle', 'api': '/api/v1/purchase-orders/', 'method': 'POST'},
            {'label': '申请信用证', 'icon': 'bi-bank', 'api': '/api/v1/letters-of-credit/', 'method': 'POST'},
            {'label': '进口报关', 'icon': 'bi-flag', 'api': '/api/v1/customs-declarations/', 'method': 'POST'},
            {'label': '外汇结算', 'icon': 'bi-currency-exchange', 'api': '/api/v1/forex-settlements/', 'method': 'POST'},
        ],
        'stats': [
            {'label': '采购订单', 'icon': 'bi-bag-check', 'api': '/api/v1/purchase-orders/', 'color': 'primary'},
            {'label': '待审信用证', 'icon': 'bi-bank', 'api': '/api/v1/letters-of-credit/', 'color': 'info'},
            {'label': '货运单证', 'icon': 'bi-truck', 'api': '/api/v1/shipments/', 'color': 'success'},
            {'label': '外汇结算', 'icon': 'bi-currency-exchange', 'api': '/api/v1/forex-settlements/', 'color': 'warning'},
        ],
        'list_api': '/api/v1/purchase-orders/',
        'panel': 'trader',
    },
    'customs': {
        'nav_items': [
            {'label': '报关单据 (Declarations)', 'icon': 'bi-clipboard-data', 'href': '/workspace/customs/'},
            {'label': '待审核 (Pending)', 'icon': 'bi-hourglass-split', 'href': '/workspace/customs/'},
            {'label': '历史记录 (History)', 'icon': 'bi-clock-history', 'href': '/workspace/customs/'},
        ],
        'actions': [
            {'label': '批准报关单', 'icon': 'bi-check-circle', 'api': '/api/v1/customs-declarations/', 'method': 'PATCH'},
            {'label': '拒绝报关单', 'icon': 'bi-x-circle', 'api': '/api/v1/customs-declarations/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': '待审核', 'icon': 'bi-hourglass-split', 'api': '/api/v1/customs-declarations/', 'color': 'warning'},
            {'label': '今日批准', 'icon': 'bi-check-circle', 'api': '/api/v1/customs-declarations/', 'color': 'success'},
            {'label': '已处理总数', 'icon': 'bi-clipboard-data', 'api': '/api/v1/customs-declarations/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/customs-declarations/',
        'panel': 'approver',
    },
    'inspection': {
        'nav_items': [
            {'label': '报检申请 (Applications)', 'icon': 'bi-clipboard-check', 'href': '/workspace/inspection/'},
            {'label': '待审核 (Pending)', 'icon': 'bi-hourglass-split', 'href': '/workspace/inspection/'},
            {'label': '检验证书 (Certificates)', 'icon': 'bi-award', 'href': '/workspace/inspection/'},
        ],
        'actions': [
            {'label': '批准申请', 'icon': 'bi-check-circle', 'api': '/api/v1/inspection-applications/', 'method': 'PATCH'},
            {'label': '拒绝申请', 'icon': 'bi-x-circle', 'api': '/api/v1/inspection-applications/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': '待审核', 'icon': 'bi-hourglass-split', 'api': '/api/v1/inspection-applications/', 'color': 'warning'},
            {'label': '已发证书', 'icon': 'bi-award', 'api': '/api/v1/inspection-applications/', 'color': 'success'},
            {'label': '已处理总数', 'icon': 'bi-clipboard-check', 'api': '/api/v1/inspection-applications/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/inspection-applications/',
        'panel': 'approver',
    },
    'forex': {
        'nav_items': [
            {'label': '结算申请 (Settlements)', 'icon': 'bi-currency-exchange', 'href': '/workspace/forex/'},
            {'label': '待审核 (Pending)', 'icon': 'bi-hourglass-split', 'href': '/workspace/forex/'},
            {'label': '历史记录 (History)', 'icon': 'bi-clock-history', 'href': '/workspace/forex/'},
        ],
        'actions': [
            {'label': '批准结算', 'icon': 'bi-check-circle', 'api': '/api/v1/forex-settlements/', 'method': 'PATCH'},
            {'label': '拒绝结算', 'icon': 'bi-x-circle', 'api': '/api/v1/forex-settlements/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': '待审核', 'icon': 'bi-hourglass-split', 'api': '/api/v1/forex-settlements/', 'color': 'warning'},
            {'label': '今日结算', 'icon': 'bi-check-circle', 'api': '/api/v1/forex-settlements/', 'color': 'success'},
            {'label': '已结算总数', 'icon': 'bi-currency-exchange', 'api': '/api/v1/forex-settlements/', 'color': 'primary'},
        ],
        'list_api': '/api/v1/forex-settlements/',
        'panel': 'approver',
    },
    'tax': {
        'nav_items': [
            {'label': '退税申请 (Refunds)', 'icon': 'bi-cash-stack', 'href': '/workspace/tax/'},
            {'label': '待审核 (Pending)', 'icon': 'bi-hourglass-split', 'href': '/workspace/tax/'},
            {'label': '历史记录 (History)', 'icon': 'bi-clock-history', 'href': '/workspace/tax/'},
        ],
        'actions': [
            {'label': '批准退税', 'icon': 'bi-check-circle', 'api': '/api/v1/tax-refund-applications/', 'method': 'PATCH'},
            {'label': '拒绝退税', 'icon': 'bi-x-circle', 'api': '/api/v1/tax-refund-applications/', 'method': 'PATCH'},
        ],
        'stats': [
            {'label': '待审核', 'icon': 'bi-hourglass-split', 'api': '/api/v1/tax-refund-applications/', 'color': 'warning'},
            {'label': '今日批准', 'icon': 'bi-check-circle', 'api': '/api/v1/tax-refund-applications/', 'color': 'success'},
            {'label': '已退税总数', 'icon': 'bi-cash-stack', 'api': '/api/v1/tax-refund-applications/', 'color': 'primary'},
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
def admin_dashboard_stats(request):
    """Admin dashboard statistics API"""
    from django.db.models import Count
    from apps.users.models import User
    from apps.teaching.models import Course

    users = User.objects.all()
    documents = Document.objects.all()

    user_type_dist = list(users.values('user_type').annotate(count=Count('id')))
    doc_type_dist = list(
        documents.values('template__code', 'template__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    doc_status_dist = list(documents.values('status').annotate(count=Count('id')))

    pending_review = documents.filter(status='pending_review').count()

    recent_docs = list(
        documents.select_related('template', 'created_by')
        .order_by('-created_at')[:10]
        .values('id', 'template__name', 'created_by__username', 'status', 'created_at')
    )

    recent_users = list(
        users.order_by('-date_joined')[:5]
        .values('id', 'username', 'user_type', 'date_joined')
    )

    return JsonResponse({
        'summary': {
            'total_users': users.count(),
            'total_documents': documents.count(),
            'total_courses': Course.objects.count(),
            'pending_review': pending_review,
        },
        'user_type_distribution': [
            {'type': item['user_type'], 'count': item['count']}
            for item in user_type_dist
        ],
        'document_type_distribution': [
            {'code': item['template__code'], 'name': item['template__name'], 'count': item['count']}
            for item in doc_type_dist
        ],
        'document_status_distribution': [
            {'status': item['status'], 'count': item['count']}
            for item in doc_status_dist
        ],
        'recent_documents': [
            {
                'id': d['id'],
                'template_name': d['template__name'],
                'created_by': d['created_by__username'],
                'status': d['status'],
                'created_at': d['created_at'].isoformat() if d['created_at'] else None,
            }
            for d in recent_docs
        ],
        'recent_users': [
            {
                'id': u['id'],
                'username': u['username'],
                'user_type': u['user_type'],
                'date_joined': u['date_joined'].isoformat() if u['date_joined'] else None,
            }
            for u in recent_users
        ],
    })


@login_required
def teacher_dashboard_stats(request):
    """Teacher dashboard statistics API"""
    from django.db.models import Count, Q
    from apps.users.models import User
    from apps.teaching.models import Course, TeachingClass, StudentEnrollment
    from apps.roles.models import UserCompanyRole

    # Only teachers can access this
    if request.user.user_type != 'teacher':
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # Get teacher's courses (using teachers field which is ManyToMany)
    teacher_courses = Course.objects.filter(teachers=request.user)

    # Get teacher's class IDs
    teacher_class_ids = list(TeachingClass.objects.filter(
        course__teachers=request.user
    ).values_list('id', flat=True))

    # Get students in teacher's classes via StudentEnrollment
    student_ids = list(StudentEnrollment.objects.filter(
        teaching_class_id__in=teacher_class_ids,
        status='enrolled'
    ).values_list('student_id', flat=True).distinct())

    teacher_students = User.objects.filter(id__in=student_ids)

    # Get documents from teacher's students
    student_documents = Document.objects.filter(created_by_id__in=student_ids)

    # Course progress distribution
    course_progress = list(teacher_courses.annotate(
        student_count=Count('classes__enrollments')
    ).values('id', 'name', 'student_count'))

    # Document status distribution for teacher's students
    doc_status_dist = list(student_documents.values('status').annotate(count=Count('id')))

    # Pending review documents
    pending_review = student_documents.filter(status='pending_review').count()

    # Pending role requests (students with pending role assignments)
    pending_role_requests = UserCompanyRole.objects.filter(
        status='pending',
        user__user_type='student'
    ).count()

    # Class activity (students per class)
    class_activity = list(
        TeachingClass.objects.filter(id__in=teacher_class_ids)
        .annotate(student_count=Count('enrollments'))
        .values('name', 'student_count')
    )

    # Recent activities from students
    recent_activities = list(
        student_documents.select_related('template', 'created_by')
        .order_by('-created_at')[:10]
        .values('id', 'template__name', 'created_by__username', 'status', 'created_at')
    )

    return JsonResponse({
        'summary': {
            'courses_count': teacher_courses.count(),
            'classes_count': len(teacher_class_ids),
            'students_count': teacher_students.count(),
            'pending_review': pending_review,
            'pending_role_requests': pending_role_requests,
        },
        'course_progress_distribution': [
            {'status': 'in_progress' if c['student_count'] > 0 else 'not_started', 'count': 1}
            for c in course_progress
        ],
        'document_status_distribution': [
            {'status': item['status'], 'count': item['count']}
            for item in doc_status_dist
        ],
        'class_activity': [
            {'name': item['name'], 'count': item['student_count']}
            for item in class_activity
        ],
        'recent_activities': [
            {
                'description': d['template__name'] + ' - ' + (d['created_by__username'] or '未知'),
                'status': d['status'],
                'created_at': d['created_at'].isoformat() if d['created_at'] else None,
            }
            for d in recent_activities
        ],
    })


@login_required
def student_dashboard_stats(request):
    """Student dashboard statistics API"""
    from django.db.models import Count, Q
    from apps.users.models import User
    from apps.transactions.models import Transaction
    from apps.roles.models import UserCompanyRole, Company

    # Only students can access this
    if request.user.user_type != 'student':
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # Get student's documents
    my_documents = Document.objects.filter(created_by=request.user)

    # Get student's companies (via UserCompanyRole)
    my_company_ids = list(UserCompanyRole.objects.filter(
        user=request.user,
        status__in=['approved', 'active']
    ).values_list('company_id', flat=True).distinct())

    # Get transactions involving student's companies
    my_transactions = Transaction.objects.filter(
        Q(buyer_id__in=my_company_ids) | Q(seller_id__in=my_company_ids)
    ).distinct()

    # Pending documents (draft or submitted but not approved)
    pending_documents = my_documents.filter(
        Q(status='draft') | Q(status='pending_review') | Q(status='submitted')
    ).count()

    # Documents that need attention (rejected or need revision)
    pending_reviews = my_documents.filter(status='rejected').count()

    # Expiring transactions (mock - logic depends on transaction model)
    expiring_transactions = 0

    # Unread notifications (mock - depends on notification system)
    unread_notifications = 0

    # Document status distribution
    doc_status_dist = list(my_documents.values('status').annotate(count=Count('id')))

    # Transaction status distribution
    transaction_status_dist = list(
        my_transactions.values('status').annotate(count=Count('id'))
    )

    # Role distribution - using UserCompanyRole
    my_roles = UserCompanyRole.objects.filter(user=request.user).select_related('role')
    role_dist = {}
    for ur in my_roles:
        key = ur.role.name or ur.role.code
        role_dist[key] = role_dist.get(key, 0) + 1

    # Recent activities
    recent_activities = list(
        my_documents.select_related('template')
        .order_by('-created_at')[:10]
        .values('id', 'template__name', 'status', 'created_at')
    )

    return JsonResponse({
        'summary': {
            'transactions_count': my_transactions.count(),
            'documents_count': my_documents.count(),
            'pending_documents': pending_documents,
            'unread_notifications': unread_notifications,
            'pending_reviews': pending_reviews,
            'expiring_transactions': expiring_transactions,
        },
        'document_status_distribution': [
            {'status': item['status'], 'count': item['count']}
            for item in doc_status_dist
        ],
        'transaction_status_distribution': [
            {'status': item['status'], 'count': item['count']}
            for item in transaction_status_dist
        ],
        'role_distribution': [
            {'name': key, 'count': value}
            for key, value in role_dist.items()
        ],
        'recent_activities': [
            {
                'description': d['template__name'] or '单证更新',
                'status': d['status'],
                'created_at': d['created_at'].isoformat() if d['created_at'] else None,
            }
            for d in recent_activities
        ],
    })


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
@ensure_csrf_cookie
def teaching_dashboard(request):
    """Teaching module dashboard"""
    return render(request, 'teaching/dashboard.html', {'user': request.user})


@login_required
@ensure_csrf_cookie
def teaching_course_list(request):
    """Course list page"""
    return render(request, 'teaching/course_list.html', {'user': request.user})


@login_required
@ensure_csrf_cookie
def teaching_course_detail(request, course_id):
    """Course detail page"""
    return render(request, 'teaching/course_detail.html', {
        'user': request.user,
        'course_id': course_id,
    })


@login_required
@ensure_csrf_cookie
def teaching_grading(request):
    """Grading page"""
    return render(request, 'teaching/grading.html', {'user': request.user})


@login_required
@ensure_csrf_cookie
def teaching_experiments(request):
    """Experiment templates management page"""
    return render(request, 'teaching/experiments.html', {'user': request.user})


@login_required
@ensure_csrf_cookie
def teaching_class_list(request):
    """Class list page"""
    return render(request, 'teaching/class_list.html', {'user': request.user})


@login_required
@ensure_csrf_cookie
def teaching_class_detail(request, id):
    """Class detail page"""
    return render(request, 'teaching/class_detail.html', {'user': request.user, 'class_id': id})


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
    try:
        data = json.loads(document.data) if document.data else {}
    except (json.JSONDecodeError, TypeError):
        data = {}
    return render(request, 'documents/preview.html', {'document': document, 'data': data})


# ---------------------------------------------------------------------------
# URL patterns - API routes
# ---------------------------------------------------------------------------
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/dashboard/stats/', admin_dashboard_stats, name='admin-dashboard-stats'),
    path('api/v1/dashboard/teacher/', teacher_dashboard_stats, name='teacher-dashboard-stats'),
    path('api/v1/dashboard/student/', student_dashboard_stats, name='student-dashboard-stats'),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/documents/', include('apps.documents.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/', include('apps.transactions.urls')),
    path('api/v1/', include('apps.roles.urls')),
    path('api/v1/scoring/', include('apps.scoring.urls')),
    path('api/v1/teaching/', include('apps.teaching.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/core/', include('apps.core.urls')),
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
    # Companies & roles
    path('companies/', lambda r: render(r, 'companies/list.html'), name='company-list'),
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
    path('teaching/experiments/', teaching_experiments, name='teaching-experiments'),
    # Class management
    path('teaching/classes/', teaching_class_list, name='class-list'),
    path('teaching/classes/<int:id>/', teaching_class_detail, name='class-detail'),
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
