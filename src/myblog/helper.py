import random
import string


def get_rand_element(collection):
    limit = len(collection)
    num = random.randint(0, limit-1)
    return collection[num]


def random_str(length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def make_creds():
    username = f'{{{random_str(15)}}}'
    password = random_str(20)
    return dict(username=username, password=password)



