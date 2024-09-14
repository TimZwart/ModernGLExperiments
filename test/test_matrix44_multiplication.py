import unittest
import numpy as np
from pyrr import Matrix44, matrix44

class TestMatrix44Multiplication(unittest.TestCase):
    def setUp(self):
        # Create two simple 4x4 matrices for testing
        self.matrix1 = Matrix44([
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16]
        ])
        self.matrix2 = Matrix44([
            [17, 18, 19, 20],
            [21, 22, 23, 24],
            [25, 26, 27, 28],
            [29, 30, 31, 32]
        ])
        # Expected result of multiplication
        self.expected_result = np.array([
            [250, 260, 270, 280],
            [618, 644, 670, 696],
            [986, 1028, 1070, 1112],
            [1354, 1412, 1470, 1528]
        ])

    def test_matmul_operator(self):
        print("test_matmul_operator")
        result = self.matrix1 @ self.matrix2
        print("Actual result: ", result)
        print("Expected result: ", self.expected_result)
        np.testing.assert_array_almost_equal(np.array(result), self.expected_result)
    def test_mul_operator(self):
        print("test_mul_operator")
        result = self.matrix1 * self.matrix2
        print("Actual result: ", result)
        print("Expected result: ", self.expected_result)
        np.testing.assert_array_almost_equal(np.array(result), self.expected_result)

    def test_multiply_method(self):
        result = matrix44.multiply(self.matrix1, self.matrix2)
        print("test_multiply_method")
        print("Actual result: ", result)
        print("Expected result: ", self.expected_result)
        np.testing.assert_array_almost_equal(np.array(result), self.expected_result)

if __name__ == '__main__':
    unittest.main()