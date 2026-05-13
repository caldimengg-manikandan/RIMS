import unittest
from app.services.interview_engine.adaptive_engine import adjust_difficulty

class TestAdaptiveEngine(unittest.TestCase):
    
    def test_difficulty_increases_on_high_score(self):
        # Should increase if score >= 8.0
        self.assertEqual(adjust_difficulty("easy", 8.5), "medium")
        self.assertEqual(adjust_difficulty("medium", 9.0), "hard")
        # Should cap at hard
        self.assertEqual(adjust_difficulty("hard", 10.0), "hard")

    def test_difficulty_decreases_on_low_score(self):
        # Should decrease if score <= 4.0
        self.assertEqual(adjust_difficulty("hard", 3.0), "medium")
        self.assertEqual(adjust_difficulty("medium", 2.0), "easy")
        # Should cap at easy
        self.assertEqual(adjust_difficulty("easy", 1.0), "easy")

    def test_difficulty_holds_on_average_score(self):
        # Should hold if 4.0 < score < 8.0
        self.assertEqual(adjust_difficulty("easy", 5.0), "easy")
        self.assertEqual(adjust_difficulty("medium", 6.5), "medium")
        self.assertEqual(adjust_difficulty("hard", 7.9), "hard")

if __name__ == '__main__':
    unittest.main()
