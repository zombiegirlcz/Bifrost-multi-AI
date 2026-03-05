def sum_numbers(a, b):
    return a + b

if __name__ == '__main__':
    print(sum_numbers(1, 2))

## tests/test_solution.py
from solution import sum_numbers

def test_sum():
    assert sum_numbers(1, 2) == 3
    assert sum_numbers(0, 0) == 0