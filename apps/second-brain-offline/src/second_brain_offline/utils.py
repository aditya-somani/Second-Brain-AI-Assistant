import random
import string

def generate_random_hex(length:int) -> str:
    """Generate a random hex string of specified length.

    Args:
        length: The desired length of the hex string.

    Returns:
        str: Random hex string of the specified length.
    """

    #hex_chars is a string of all the hex characters in lowercase - 0123456789abcdefabcdef
    hex_chars = string.hexdigits.lower()

    #join is used to concatenate the hex characters into a single string
    #random.choice is used to randomly select a character from the hex_chars string
    #range(length) number of times to repeat the random choice
    return ''.join(random.choice(hex_chars) for _ in range(length))



