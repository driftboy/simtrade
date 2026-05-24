/**
 * SimTrade 教学模块脚本
 */

(function() {
    'use strict';

    /**
     * 加载课程列表，渲染课程卡片
     */
    function loadCourses() {
        $.ajax({
            url: '/api/v1/teaching/courses/',
            method: 'GET',
            success: function(response) {
                var html = '';
                var courses = response.data || response.results || response;
                if (!courses || courses.length === 0) {
                    html = '<div class="alert alert-info">暂无课程</div>';
                } else {
                    courses.forEach(function(course) {
                        var semesterName = course.semester_name || (course.semester && course.semester.name) || '';
                        html += '<div class="course-card">' +
                            '<h4>' + (course.name || '未命名课程') + '</h4>' +
                            '<div class="course-meta">' +
                                '学期: ' + SimTrade.escapeHtml(semesterName) +
                                ' | 学生数: ' + (course.student_count || 0) +
                            '</div>' +
                            '<p>' + (course.description || '') + '</p>' +
                            '<a href="/teaching/courses/' + course.id + '/" class="btn btn-primary btn-sm">查看详情</a>' +
                        '</div>';
                    });
                }
                $('#course-list').html(html);
            },
            error: function(xhr) {
                $('#course-list').html(
                    '<div class="alert alert-danger">加载课程失败: ' +
                    (xhr.responseJSON && xhr.responseJSON.message || '未知错误') +
                    '</div>'
                );
            }
        });
    }

    /**
     * 加载课程详情和班级列表
     */
    function loadCourseDetail(courseId) {
        // 加载课程基本信息
        $.ajax({
            url: '/api/v1/teaching/courses/' + courseId + '/',
            method: 'GET',
            success: function(response) {
                var course = response.data || response;
                $('#course-title').text(course.name || '课程详情');
            },
            error: function() {
                $('#course-title').text('课程详情');
                SimTrade.showError('加载课程信息失败');
            }
        });

        // 加载班级列表
        $.ajax({
            url: '/api/v1/teaching/classes/',
            method: 'GET',
            data: { course_id: courseId },
            success: function(response) {
                var html = '';
                var classes = response.data || response.results || response;
                if (!classes || classes.length === 0) {
                    html = '<tr><td colspan="4" class="text-center">暂无班级</td></tr>';
                } else {
                    classes.forEach(function(cls) {
                        var statusLabel = cls.is_active ? '<span class="label label-success">进行中</span>' : '<span class="label label-default">已结束</span>';
                        html += '<tr>' +
                            '<td>' + SimTrade.escapeHtml(cls.name || '') + '</td>' +
                            '<td>' + (cls.student_count || 0) + '</td>' +
                            '<td><code class="enrollment-code">' + SimTrade.escapeHtml(cls.enrollment_code || '') + '</code></td>' +
                            '<td>' + statusLabel + '</td>' +
                        '</tr>';
                    });
                }
                $('#class-table-body').html(html);
            },
            error: function() {
                $('#class-table-body').html(
                    '<tr><td colspan="4" class="text-center text-danger">加载班级失败</td></tr>'
                );
            }
        });
    }

    /**
     * 加载实验模板列表，填充下拉选择框
     */
    function loadGradingData() {
        $.ajax({
            url: '/api/v1/teaching/experiment-templates/',
            method: 'GET',
            success: function(response) {
                var html = '<option value="">请选择实验</option>';
                var templates = response.data || response.results || response;
                if (templates && templates.length > 0) {
                    templates.forEach(function(tpl) {
                        html += '<option value="' + tpl.id + '">' + SimTrade.escapeHtml(tpl.name || '') + '</option>';
                    });
                }
                $('#experiment-select').html(html);
            },
            error: function() {
                $('#experiment-select').html('<option value="">加载失败</option>');
            }
        });
    }

    /**
     * 加载成绩单，渲染成绩表格
     */
    function loadScoreSheet(experimentId) {
        if (!experimentId) {
            $('#score-table-body').html('<tr><td colspan="6" class="text-center">请先选择实验</td></tr>');
            return;
        }

        $.ajax({
            url: '/api/v1/scoring/sheets/',
            method: 'GET',
            data: { experiment_id: experimentId },
            success: function(response) {
                var html = '';
                var sheets = response.data || response.results || response;
                if (!sheets || sheets.length === 0) {
                    html = '<tr><td colspan="6" class="text-center">暂无成绩数据</td></tr>';
                } else {
                    sheets.forEach(function(sheet) {
                        var statusLabel = '';
                        if (sheet.status === 'graded') {
                            statusLabel = '<span class="label label-success">已评分</span>';
                        } else if (sheet.status === 'submitted') {
                            statusLabel = '<span class="label label-info">已提交</span>';
                        } else {
                            statusLabel = '<span class="label label-default">未提交</span>';
                        }
                        html += '<tr>' +
                            '<td>' + SimTrade.escapeHtml(sheet.student_name || '') + '</td>' +
                            '<td>' + SimTrade.escapeHtml(sheet.company_name || '-') + '</td>' +
                            '<td>' + (sheet.auto_score != null ? sheet.auto_score : '-') + '</td>' +
                            '<td>' + (sheet.teacher_score != null ? sheet.teacher_score : '-') + '</td>' +
                            '<td>' + (sheet.final_score != null ? sheet.final_score : '-') + '</td>' +
                            '<td>' + statusLabel + '</td>' +
                        '</tr>';
                    });
                }
                $('#score-table-body').html(html);
            },
            error: function() {
                $('#score-table-body').html(
                    '<tr><td colspan="6" class="text-center text-danger">加载成绩失败</td></tr>'
                );
            }
        });
    }

    // 绑定事件
    $(document).ready(function() {
        // 成绩页实验选择变化事件
        $('#experiment-select').on('change', function() {
            var experimentId = $(this).val();
            loadScoreSheet(experimentId);
        });
    });

    // 暴露全局函数
    window.loadCourses = loadCourses;
    window.loadCourseDetail = loadCourseDetail;
    window.loadGradingData = loadGradingData;
    window.loadScoreSheet = loadScoreSheet;

})();
