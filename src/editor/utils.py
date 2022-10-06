# -*- coding: utf-8 -*-
import numpy as np
import glob
import io
import os
import random
import secrets
from string import ascii_lowercase, ascii_uppercase, ascii_letters, digits
from uuid import uuid4

from faker import Faker
from skimage.io import imread, imsave
from unidecode import unidecode

fake = Faker()


def decode_if_unicode(s):
    return unidecode(s)


def coin_flip():
    return random.randrange(0, 2) == 1


def get_random_user_agent():
    return fake.user_agent()


def generate_user_name():
    return uuid4().hex[:random.randrange(16, 22)]


def generate_user_pass():
    length = random.randrange(12, 20)
    special = '!"#$%&\'()*+,-./;<=>?@[\\]^_`{|}~'
    alphabet = ascii_letters + digits
    requirements = [
        ascii_uppercase,  # at least one uppercase letter
        ascii_lowercase,  # at least one lowercase letter
        digits,  # at least one digit
        special,  # at least one special symbol
        *(length - 4) * [alphabet]  # rest: letters digits and symbols
    ]
    return ''.join(secrets.choice(req) for req in random.sample(requirements, length))


def generate_first_name():
    return fake.first_name()


def generate_last_name():
    return fake.last_name()


def generate_bio():
    return fake.sentence(nb_words=random.randrange(5, 20))


def generate_image_name():
    return uuid4().hex[:random.randrange(12, 20)]


def image_raw_to_array(image_raw_data):
    return imread(io.BytesIO(image_raw_data))


def image_array_to_raw(image_array, image_format):
    buf = io.BytesIO()
    imsave(buf, image_array, format=image_format)
    buf.seek(0, 0)
    return buf.read()


def generate_fake_image(img_fmt, raw_data):
    img_fmt = img_fmt if img_fmt != 'jpg' else 'jpeg'
    width = random.randrange(512, 1024)
    height = random.randrange(512, 1024)
    image_data = fake.image(size=(width, height), image_format=img_fmt)
    if raw_data:
        return image_data, (width, height, 3)
    else:
        return image_raw_to_array(image_data), (height, width, 3)


def generate_image(assets_folder_path, image_format, raw_data=True):
    if coin_flip():
        return generate_fake_image(image_format, raw_data)

    try:
        images_folder_path = os.path.join(assets_folder_path, image_format)
        image_file_path = random.choice(glob.glob(os.path.join(images_folder_path, '*.{}'.format(image_format))))
        image_array = imread(image_file_path)
        image_shape = image_array.shape
        if raw_data:
            with open(image_file_path, 'rb') as f:
                return f.read(), image_shape
        else:
            return image_array, image_shape

    except Exception:
        return generate_fake_image(image_format, raw_data)


def embed_lsb(image_array, capsule):
    def access_bit(_data, _num):
        base = int(_num // 8)
        shift = int(_num % 8)
        return (_data[base] >> shift) & 0x1

    # 1. flatten the image and check if capsule can be embedded
    data = capsule.encode('utf-8')
    data_length = len(data)
    image_data = image_array.flatten()
    image_length = len(image_data)
    if image_length < data_length * 8 + 32:
        raise Exception('Image data is too short: len(image)={0}, len(data)={1}'.format(image_length, data_length))

    # 2. data bytes to array of bits
    dl_bytes = int.to_bytes(data_length, byteorder='little', length=4, signed=True)
    data_bit_string = np.array([access_bit(data, i) for i in range(len(data) * 8)], dtype=np.uint8)
    dl_bit_string = np.array([access_bit(dl_bytes, i) for i in range(len(dl_bytes) * 8)], dtype=np.uint8)
    padding = np.zeros(image_length - len(dl_bit_string) - len(data_bit_string), dtype=np.uint8)
    payload = np.concatenate((dl_bit_string, data_bit_string, padding), axis=0)

    # 3. embed the payload and return the image
    image_data = image_data & ~np.uint8(1)
    image_data = image_data | payload
    image_array = image_data.reshape(image_array.shape)

    return image_array


def extract_lsb(image_array):
    def to_int(b):
        val = 0
        for i, d in enumerate(b):
            val = val | (d << i)
        return val

    # 1. flatten the image and check its length
    image_array = image_array.flatten()
    lsb_bytes_length = int(len(image_array) / 8.0)
    if len(image_array) < 4 * 8:
        raise Exception('Image data is too short: len(lsb_bytes)={0} bytes'.format(lsb_bytes_length))

    # 2. unpack message length
    lsb = image_array & 0x1
    lsb = lsb[:int(len(lsb) / 8.0) << 3]
    message_length_bytes = bytes([to_int(lsb[i:i + 8]) for i in range(0, 32, 8)])
    message_length = int.from_bytes(message_length_bytes, byteorder='little', signed=True)
    if not 0 < message_length < lsb_bytes_length:
        raise Exception('Incorrect packed message_length: expected 0 < message_length < {0}, but recv={1}'
                        .format(lsb_bytes_length, message_length))

    # 3. extract the embedded message and check the capsule
    message_bytes = bytes([to_int(lsb[i:i + 8]) for i in range(32, 32 + 8 * message_length, 8)])
    capsule_recv = message_bytes.decode('utf-8')
    return capsule_recv
