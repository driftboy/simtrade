import string

from django.db.models import Avg
from django.utils import timezone
from apps.teaching.models import (
    Semester, Course, TeachingClass, StudentEnrollment,
    ExperimentGroup, ExperimentTemplate, Assignment, AssignmentSubmission,
)
from apps.roles.models import Company, TradeRole, UserCompanyRole
from apps.scoring.models import Experiment, ScoreSheet


class SemesterService:
    """学期服务层：管理学期的激活、查询等业务逻辑。"""

    @staticmethod
    def create_semester(user, name, code, start_date, end_date):
        return Semester.objects.create(
            name=name, code=code,
            start_date=start_date, end_date=end_date,
            created_by=user,
        )

    @staticmethod
    def activate_semester(semester_id):
        semester = Semester.objects.get(id=semester_id)
        Semester.objects.filter(is_active=True).update(is_active=False)
        semester.is_active = True
        semester.status = 'active'
        semester.save()
        return semester

    @staticmethod
    def get_active_semester():
        return Semester.objects.filter(is_active=True).first()


class CourseService:
    """课程服务层：管理课程的创建、教师关联等业务逻辑。"""

    @staticmethod
    def create_course(user, semester_id, name, code, teacher_ids=None, **kwargs):
        course = Course.objects.create(
            semester_id=semester_id,
            name=name, code=code,
            created_by=user,
            **kwargs,
        )
        if teacher_ids:
            from apps.users.models import User
            teachers = User.objects.filter(id__in=teacher_ids)
            course.teachers.set(teachers)
        return course

    @staticmethod
    def get_teacher_courses(teacher):
        return Course.objects.filter(teachers=teacher)

    @staticmethod
    def get_student_courses(student):
        enrollment_ids = StudentEnrollment.objects.filter(
            student=student, status='enrolled',
        ).values_list('teaching_class__course_id', flat=True)
        return Course.objects.filter(id__in=enrollment_ids).distinct()


class TeachingClassService:
    """教学班级服务层：管理班级创建、学生选退课等业务逻辑。"""

    @staticmethod
    def create_class(user, course_id, name, capacity=40):
        return TeachingClass.objects.create(
            course_id=course_id,
            name=name, capacity=capacity,
            created_by=user,
        )

    @staticmethod
    def enroll_student(teaching_class_id, student, enrollment_code=None):
        cls = TeachingClass.objects.get(id=teaching_class_id)

        if enrollment_code and cls.enrollment_code != enrollment_code:
            raise ValueError('选课码错误')

        current_count = StudentEnrollment.objects.filter(
            teaching_class=cls, status='enrolled',
        ).count()
        if current_count >= cls.capacity:
            raise ValueError('班级已满')

        enrollment, created = StudentEnrollment.objects.get_or_create(
            teaching_class=cls,
            student=student,
            defaults={'status': 'enrolled'},
        )
        if not created and enrollment.status == 'dropped':
            enrollment.status = 'enrolled'
            enrollment.dropped_at = None
            enrollment.save()
        elif not created:
            raise ValueError('已经选过该班级')

        return enrollment

    @staticmethod
    def drop_student(enrollment_id, user):
        enrollment = StudentEnrollment.objects.get(
            id=enrollment_id, student=user,
        )
        enrollment.status = 'dropped'
        enrollment.dropped_at = timezone.now()
        enrollment.save()
        return enrollment

    @staticmethod
    def get_class_students(teaching_class_id):
        return StudentEnrollment.objects.filter(
            teaching_class_id=teaching_class_id,
            status='enrolled',
        ).select_related('student')


class ExperimentOrchestrationService:
    """实验编排服务：模板创建、自动分组、批量角色分配。"""

    @staticmethod
    def create_from_template(template_id, teaching_class_id, user, **overrides):
        template = ExperimentTemplate.objects.get(id=template_id)
        config = {**template.config, **overrides}
        experiment = Experiment.objects.create(
            name=overrides.get('name', template.name),
            description=template.description,
            teaching_class_id=teaching_class_id,
            template=template,
            group_config=config,
            created_by=user,
            start_date=overrides.get('start_date', timezone.now()),
        )
        template.use_count += 1
        template.save()
        return experiment

    @staticmethod
    def auto_group(experiment_id, group_size=5):
        experiment = Experiment.objects.get(id=experiment_id)
        enrollments = StudentEnrollment.objects.filter(
            teaching_class=experiment.teaching_class,
            status='enrolled',
        ).select_related('student')

        students = list(enrollments)
        group_names = list(string.ascii_uppercase)
        groups = []

        for i in range(0, len(students), group_size):
            chunk = students[i:i + group_size]
            letter = group_names[i // group_size]
            company = Company.objects.create(
                name=f'{experiment.name} - {letter}组',
                code=f'EXP{experiment.id:04d}{letter}',
            )
            group = ExperimentGroup.objects.create(
                experiment=experiment,
                company=company,
                group_name=f'{letter} 组',
            )
            groups.append(group)

        return groups

    @staticmethod
    def batch_assign_roles(experiment_id):
        experiment = Experiment.objects.get(id=experiment_id)
        groups = ExperimentGroup.objects.filter(
            experiment=experiment,
        ).select_related('company')

        all_roles = list(
            TradeRole.objects.filter(is_enabled=True).order_by('sort_order'),
        )
        assignments = []

        for group in groups:
            enrollments = list(StudentEnrollment.objects.filter(
                teaching_class=experiment.teaching_class,
                status='enrolled',
            ).select_related('student'))

            for idx, enrollment in enumerate(enrollments):
                if idx >= len(all_roles):
                    break
                role = all_roles[idx]
                assignment = UserCompanyRole.objects.create(
                    user=enrollment.student,
                    company=group.company,
                    role=role,
                    status='active',
                    is_active=(idx == 0),
                )
                assignments.append(assignment)

        return assignments

    @staticmethod
    def get_experiment_groups(experiment_id):
        return ExperimentGroup.objects.filter(
            experiment_id=experiment_id,
        ).select_related('company')


class AssignmentService:

    @staticmethod
    def create_assignment(user, teaching_class_id, **kwargs):
        return Assignment.objects.create(
            teaching_class_id=teaching_class_id,
            created_by=user,
            **kwargs,
        )

    @staticmethod
    def submit(assignment_id, student, content='', attachment=None):
        submission, _ = AssignmentSubmission.objects.get_or_create(
            assignment_id=assignment_id,
            student=student,
            defaults={'status': 'not_submitted'},
        )
        submission.content = content
        if attachment:
            submission.attachment = attachment
        submission.status = 'submitted'
        submission.submitted_at = timezone.now()
        submission.save()
        return submission

    @staticmethod
    def grade(submission_id, teacher, score, feedback=''):
        submission = AssignmentSubmission.objects.get(id=submission_id)
        submission.score = score
        submission.feedback = feedback
        submission.status = 'graded'
        submission.graded_by = teacher
        submission.graded_at = timezone.now()
        submission.save()
        return submission


class GradeReportService:

    @staticmethod
    def get_student_report(student, teaching_class_id):
        teaching_class = TeachingClass.objects.select_related(
            'course',
        ).get(id=teaching_class_id)
        course = teaching_class.course

        # 实验成绩
        experiment_ids = Experiment.objects.filter(
            teaching_class=teaching_class,
        ).values_list('id', flat=True)
        score_sheets = ScoreSheet.objects.filter(
            experiment_id__in=experiment_ids,
            user=student, status='finalized',
        )
        experiment_score = (
            score_sheets.aggregate(avg=Avg('final_score'))['avg'] or 0
        )

        # 作业成绩
        assignment_ids = Assignment.objects.filter(
            teaching_class=teaching_class,
        ).values_list('id', flat=True)
        submissions = AssignmentSubmission.objects.filter(
            assignment_id__in=assignment_ids,
            student=student, status='graded',
        )
        assignment_score = (
            submissions.aggregate(avg=Avg('score'))['avg'] or 0
        )

        # 加权总分
        total_score = (
            float(experiment_score) * float(course.experiment_weight)
            + float(assignment_score) * float(course.assignment_weight)
        )

        return {
            'student_id': student.id,
            'student_username': student.username,
            'teaching_class_id': teaching_class_id,
            'experiment_score': round(experiment_score, 2),
            'assignment_score': round(assignment_score, 2),
            'total_score': round(total_score, 2),
            'experiment_weight': float(course.experiment_weight),
            'assignment_weight': float(course.assignment_weight),
            'experiment_count': score_sheets.count(),
            'assignment_count': submissions.count(),
        }

    @staticmethod
    def get_class_report(teaching_class_id):
        teaching_class = TeachingClass.objects.select_related(
            'course',
        ).get(id=teaching_class_id)
        enrollments = StudentEnrollment.objects.filter(
            teaching_class=teaching_class, status='enrolled',
        ).select_related('student')

        scores = []
        for enrollment in enrollments:
            report = GradeReportService.get_student_report(
                enrollment.student, teaching_class_id,
            )
            scores.append(report)

        if not scores:
            return {
                'teaching_class_id': teaching_class_id,
                'student_count': 0,
                'avg_score': 0, 'max_score': 0, 'min_score': 0,
                'students': [],
            }

        total_scores = [s['total_score'] for s in scores]
        return {
            'teaching_class_id': teaching_class_id,
            'student_count': len(scores),
            'avg_score': round(sum(total_scores) / len(total_scores), 2),
            'max_score': round(max(total_scores), 2),
            'min_score': round(min(total_scores), 2),
            'students': scores,
        }

    @staticmethod
    def get_course_report(course_id):
        course = Course.objects.get(id=course_id)
        classes = TeachingClass.objects.filter(course=course)
        class_reports = []
        for cls in classes:
            report = GradeReportService.get_class_report(cls.id)
            class_reports.append(report)
        return {
            'course_id': course_id,
            'course_name': course.name,
            'class_count': len(class_reports),
            'class_reports': class_reports,
        }
