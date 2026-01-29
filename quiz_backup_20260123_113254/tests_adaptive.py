from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import User
from .views import quiz

class AdaptiveLogicTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser')

    def add_session(self, request):
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.user = self.user  # Attach user to request
        request.session.save()

    def test_pass_level_up(self):
        # Setup Request
        request = self.factory.post('/quiz/?subject=Python', {
            'q0': 'A', 'q1': 'A', 'q2': 'A', 'q3': 'A', 'q4': 'A'
        })
        self.add_session(request)
        
        # Setup Session Data
        request.session['subject'] = 'Python'
        request.session['difficulty'] = 'Foundation'
        request.session['questions'] = [
            {'question': 'Q1', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q2', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q3', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q4', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q5', 'answer': 'A', 'options': ['A', 'B']},
        ]
        request.session.save()

        # Execute View
        response = quiz(request)

        # Check Result
        self.assertEqual(request.session['difficulty'], 'Developing')
        self.assertNotIn('failed_questions_Python', request.session)

    def test_fail_stay_retry(self):
        # Setup Request: 2/5 Correct
        request = self.factory.post('/quiz/?subject=Python', {
            'q0': 'A', 'q1': 'A', 'q2': 'B', 'q3': 'B', 'q4': 'B'
        })
        self.add_session(request)

        request.session['subject'] = 'Python'
        request.session['difficulty'] = 'Foundation'
        request.session['questions'] = [
            {'question': 'Q1', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q2', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q3', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q4', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q5', 'answer': 'A', 'options': ['A', 'B']},
        ]
        request.session.save()

        response = quiz(request)

        self.assertEqual(request.session['difficulty'], 'Foundation')
        self.assertIn('failed_questions_Python', request.session)
        self.assertEqual(len(request.session['failed_questions_Python']), 3)

    def test_pass_threshold_boundary(self):
        # 4/5 Correct -> Pass (80% > 70%)
        request = self.factory.post('/quiz/?subject=Python', {
            'q0': 'A', 'q1': 'A', 'q2': 'A', 'q3': 'A', 'q4': 'B'
        })
        self.add_session(request)

        request.session['subject'] = 'Python'
        request.session['difficulty'] = 'Foundation'
        request.session['questions'] = [
            {'question': 'Q1', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q2', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q3', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q4', 'answer': 'A', 'options': ['A', 'B']},
            {'question': 'Q5', 'answer': 'A', 'options': ['A', 'B']},
        ]
        request.session.save()

        response = quiz(request)

        self.assertEqual(request.session['difficulty'], 'Developing')

    def test_failed_questions_isolation_by_subject(self):
        """Test that failed questions for Python don't show up in Math quiz."""
        from .views import DIFFICULTY_LEVELS
        
        # 1. Simulate failing Python quiz
        request = self.factory.get('/quiz/?subject=Python')
        self.add_session(request)
        request.session['failed_questions_Python'] = [{'question': 'Python Question', 'answer': 'A', 'options': ['A']}]
        request.session.save()

        # 2. Start Math quiz
        request_math = self.factory.get('/quiz/?subject=Math&start_new=true')
        self.add_session(request_math)
        # Mock what the view does to ensure session is initialized
        request_math.session['subject'] = 'Math'
        request_math.session['difficulty'] = 'Foundation'
        request_math.session.save()

        # Execute view for Math
        # We need to mock generate_questions because it will be called for Math
        from unittest.mock import patch
        with patch('quiz.views.async_to_sync') as mock_async:
            mock_gen = patch('quiz.views.generate_questions').start()
            
            async def mock_return(*args, **kwargs):
                return [{'question': 'Math Question', 'answer': 'M', 'options': ['M']}]
            mock_gen.side_effect = mock_return
            
            # Since async_to_sync(func)(*args) is called, we need mock_async to return a wrapper that returns the result
            mock_async.side_effect = lambda x: (lambda *a, **k: [{'question': 'Math Question', 'answer': 'M', 'options': ['M']}])

            response = quiz(request_math)
            
            # The quiz should NOT have the Python question
            questions = request_math.session['questions']
            for q in questions:
                self.assertNotEqual(q['question'], 'Python Question')
            
            patch.stopall()

    def test_start_new_clears_subject_failed_questions(self):
        """Test that start_new=true clears subject-specific failed questions."""
        request = self.factory.get('/quiz/?subject=Python&start_new=true')
        self.add_session(request)
        
        # Manually set subject-specific failed questions
        request.session['failed_questions_Python'] = [{'question': 'Old Python Q', 'answer': 'A'}]
        request.session.save()

        # Run the view
        from unittest.mock import patch
        with patch('quiz.views.async_to_sync') as mock_async:
            mock_async.side_effect = lambda x: (lambda *a, **k: [])
            quiz(request)

        # Check if they were cleared
        self.assertNotIn('failed_questions_Python', request.session)
