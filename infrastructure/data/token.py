"""
This file contain function to generate a token
"""

import random
import string


def generate_token(length):
    """
    Generate a random string of specified length.

    :param length: Length of the random string to generate
    :return: A random string of the specified length
    """
    characters = string.ascii_letters + string.digits
    random_str = ''.join(random.choice(characters) for _ in range(length))
    return random_str
