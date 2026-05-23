from django.test import TestCase
from django.utils import timezone
from apps.scoring.models import Experiment


class ExperimentModelTest(TestCase):
    def test_create_experiment(self):
        exp = Experiment.objects.create(
            name='实验一：CIF 出口流程',
            description='模拟 CIF 术语下的完整出口流程',
            start_date=timezone.now(),
        )
        self.assertEqual(exp.status, 'draft')
        self.assertTrue(exp.name)

    def test_status_transitions(self):
        exp = Experiment.objects.create(
            name='测试实验',
            start_date=timezone.now(),
        )
        self.assertEqual(exp.status, 'draft')
        exp.status = 'active'
        exp.save()
        self.assertEqual(exp.status, 'active')
        exp.status = 'completed'
        exp.save()
        self.assertEqual(exp.status, 'completed')
