from django.utils import timezone
from apps.teaching.models import Semester, Course, TeachingClass, StudentEnrollment


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
