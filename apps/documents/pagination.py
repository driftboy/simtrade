"""
Pagination configuration for Document API.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DocumentPagination(PageNumberPagination):
    """
    分页配置类 - 单证列表
    - 默认每页 5 条
    - 支持通过 URL 参数 page_size 自定义
    - 最大每页 50 条
    """
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        """
        Return a custom paginated response format compatible with frontend expectations.

        Args:
            data: The serialized data list from the viewset

        Returns:
            Response with format: {count, next, previous, results}
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

