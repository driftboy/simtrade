from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService
from apps.notifications.permissions import IsOwner


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            is_read = is_read.lower() == 'true'
        notifications = NotificationService.get_notifications(request.user, is_read=is_read)
        serializer = NotificationSerializer(notifications, many=True)
        return Response({'code': 0, 'message': 'success', 'data': serializer.data})

    def destroy(self, request, pk=None):
        notification = Notification.objects.get(id=pk)
        if notification.user != request.user:
            return Response({'code': 2001, 'message': '无权操作'}, status=status.HTTP_403_FORBIDDEN)
        notification.delete()
        return Response({'code': 0, 'message': '已删除'})

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        try:
            notification = NotificationService.mark_as_read(pk, request.user)
            return Response({'code': 0, 'message': '已标记已读', 'data': NotificationSerializer(notification).data})
        except ValueError as e:
            return Response({'code': 5005, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Notification.DoesNotExist:
            return Response({'code': 4001, 'message': '通知不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        NotificationService.mark_all_read(request.user)
        return Response({'code': 0, 'message': '全部已标记已读'})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({'code': 0, 'message': 'success', 'data': {'count': count}})
