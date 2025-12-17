import unittest

from lang_chain_backend.services.prueba import fibonacci_100, fibonacci_generator


class TestFibonacci(unittest.TestCase):
    def test_fibonacci_100_length(self):
        nums = fibonacci_100()
        self.assertEqual(len(nums), 100)

    def test_fibonacci_100_values(self):
        nums = fibonacci_100()
        self.assertEqual(nums[0], 0)
        self.assertEqual(nums[1], 1)
        # F(99) known value
        self.assertEqual(nums[-1], 218922995834555169026)

    def test_generator_equivalence(self):
        gen = list(fibonacci_generator(100))
        self.assertEqual(gen, fibonacci_100())


if __name__ == "__main__":
    unittest.main()
