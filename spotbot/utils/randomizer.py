import random


def is_random(prob):
    if random.randint(0, 100) < prob:
        return True
    return False
