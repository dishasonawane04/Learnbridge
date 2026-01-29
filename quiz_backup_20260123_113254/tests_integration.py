from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

# Mock data for AI Engine
MOCK_QUESTIONS = [
    {'question': 'Mock Q1', 'answer': 'A', 'options': ['A', 'B', 'C', 'D']},
    {'question': 'Mock Q2', 'answer': 'A', 'options': ['A', 'B', 'C', 'D']},
    {'question': 'Mock Q3', 'answer': 'A', 'options': ['A', 'B', 'C', 'D']},
    {'question': 'Mock Q4', 'answer': 'A', 'options': ['A', 'B', 'C', 'D']},
    {'question': 'Mock Q5', 'answer': 'A', 'options': ['A', 'B', 'C', 'D']},
]

class QuizIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        # HOTFIX: Disable template context storage to avoid Python 3.14/Django copy bug
        # The crash involves deep copying context which fails on some objects.
        # We don't strictly need context assertion for these integration tests.
        patcher = patch('django.test.client.store_rendered_templates')
        self.mock_store = patcher.start()
        self.mock_store.return_value = True # Just to be safe
        self.addCleanup(patcher.stop)

    def test_home_page_loads(self):
        """Test that the home page loads correctly."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Master Any Subject with")

    def test_quiz_start_fresh(self):
        """Test starting a new quiz resets session."""
        session = self.client.session
        session['difficulty'] = 'Mastery'
        session.save()

        # Mock start_new logic
        response = self.client.get(reverse('quiz') + '?subject=Python&start_new=true')
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(self.client.session['difficulty'], 'Foundation')
        self.assertNotIn('failed_questions', self.client.session)

    @patch('quiz.views.generate_questions')
    def test_quiz_submission_flow(self, mock_gen):
        """Test submitting a quiz and getting results."""
        # Setup mock to return sync list (since view calls async_to_sync, we mock the underlying async func or the result)
        # However, async_to_sync(mock) calls mock().
        # In views.py: questions = async_to_sync(generate_questions)(...)
        # So mock_gen should be a callable that returns the list or coroutine.
        # But wait, async_to_sync expects an awaitable or a function returning awaitable.
        # EASIER: Mock the whole async_to_sync wrapper OR just make the mock return a coroutine.
        
        async def mock_return(*args, **kwargs):
            return MOCK_QUESTIONS

        mock_gen.side_effect = mock_return

        # 1. Start Quiz
        response = self.client.get(reverse('quiz') + '?subject=Python&start_new=true')
        self.assertEqual(response.status_code, 200)
        
        # 2. Submit
        # Use our mock questions because random shuffle might happen
        # Actually session['questions'] is what matters
        questions = self.client.session['questions']
        self.assertEqual(len(questions), 5)

        data = {}
        for i, q in enumerate(questions):
            data[f'q{i}'] = q['answer']
        
        # We also need to mock explain_answer and generate_feedback in the POST logic
        with patch('quiz.views.explain_answer') as mock_explain, \
             patch('quiz.views.generate_feedback') as mock_feedback:
            
            async def mock_str(*args, **kwargs): return "Mock Explanation"
            mock_explain.side_effect = mock_str
            mock_feedback.side_effect = mock_str

            response = self.client.post(reverse('quiz'), data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Level Up!")
            self.assertEqual(self.client.session['difficulty'], 'Developing')

    @patch('quiz.views.generate_questions')
    def test_quiz_submission_fail(self, mock_gen):
        async def mock_return(*args, **kwargs):
            return MOCK_QUESTIONS
        mock_gen.side_effect = mock_return

        # 1. Start Quiz
        self.client.get(reverse('quiz') + '?subject=Python&start_new=true')
        questions = self.client.session['questions']

        # 2. Submit wrong answers
        data = {}
        for i, q in enumerate(questions):
             # Force wrong answer
            data[f'q{i}'] = "WRONG"

        with patch('quiz.views.explain_answer') as mock_explain, \
             patch('quiz.views.generate_feedback') as mock_feedback:
            
            async def mock_str(*args, **kwargs): return "Mock Feedback"
            mock_explain.side_effect = mock_str
            mock_feedback.side_effect = mock_str

            response = self.client.post(reverse('quiz'), data)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Keep Trying!")
            self.assertEqual(self.client.session['difficulty'], 'Foundation')
