def factorial(n):
    """Calculate the factorial of a non-negative integer."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("Input must be a non-negative integer")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
