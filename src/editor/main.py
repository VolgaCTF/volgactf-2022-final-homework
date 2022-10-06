# -*- coding: utf-8 -*-
import base64
import io
import logging
import os
import random

import aiohttp
from volgactf.final.checker.result import Result

from .utils import (
    decode_if_unicode,
    coin_flip,
    generate_user_name, generate_user_pass,
    generate_first_name, generate_last_name, generate_bio,
    get_random_user_agent,
    generate_image_name, generate_image,
    image_raw_to_array, image_array_to_raw,
    embed_lsb, extract_lsb
)

logger = logging.getLogger(__name__)

# region Environment variables

PORT = int(os.getenv('EDITOR_PORT', 8080))
SESSION_TOTAL_TIMEOUT = int(os.getenv('EDITOR_TIMEOUT', 30))
N_MAX_IMAGES_PER_PUSH = int(os.getenv('EDITOR_N_MAX_IMAGES_PER_PUSH', 3))
ASSETS_FOLDER_PATH = os.getenv('EDITOR_ASSETS_FOLDER_PATH', '/dist/editor/assets')

IMAGE_MULTIPART_FILENAME = 'image'

REGISTER_RET_CODE_OK = 201
POST_IMAGE_RET_CODE_OK = 201
LOGIN_RET_CODE_OK = 200
LOGIN_RET_CODE_INVALID = 400
LOGOUT_RET_CODE_OK = 200
GET_IMAGE_RET_CODE_OK = 200
DOWNLOAD_IMAGE_RET_CODE_OK = 200

REGISTER_URI_FMT = os.getenv('REGISTER_URI_FMT', 'http://{endpoint}:{port}/signup')
LOGIN_URI_FMT = os.getenv('LOGIN_URI_FMT', 'http://{endpoint}:{port}/login')
LOGOUT_URI_FMT = os.getenv('LOGOUT_URI_FMT', 'http://{endpoint}:{port}/logout')
POST_IMAGE_URI_FMT = os.getenv('POST_IMAGE_URI_FMT', 'http://{endpoint}:{port}/image')
GET_IMAGE_URI_FMT = os.getenv('GET_IMAGE_URI_FMT', 'http://{endpoint}:{port}/image/{image_id}')
GET_IMAGE_CONTENTS_FMT = os.getenv('GET_IMAGE_CONTENTS_FMT', 'http://{endpoint}:{port}/{uri}')


# endregion Environment variables


# region Payload generation and capsule checking

def generate_post_image_requests(capsule):
    n_images = random.randrange(1, N_MAX_IMAGES_PER_PUSH + 1)
    strategies = [0 for _ in range(n_images)]
    save_into_index = random.randrange(n_images)
    strategies[save_into_index] = None

    datas, post_image_infos = [], []
    for emb_strategy in strategies:
        post_image_info = generate_post_image_request(capsule, emb_strategy=emb_strategy)
        data = aiohttp.FormData()
        data.add_field(
            IMAGE_MULTIPART_FILENAME,
            io.BytesIO(post_image_info['image_data']),
            filename=post_image_info['filename'],
            content_type=post_image_info['content_type']
        )
        data.add_field('name', post_image_info['name'])
        if post_image_info['about'] is not None:
            data.add_field('about', post_image_info['about'])

        datas.append(data)
        post_image_infos.append(post_image_info)

    post_image_info = post_image_infos[save_into_index]
    return datas, post_image_info, save_into_index


def generate_post_image_request(capsule, emb_strategy=None):
    im_rec = {
        'name': generate_image_name(),
        'about': None,  # N.B. about is optional
        'image_shape': None,
        'image_data': None,
        'filename': None,
        'content_type': None,
        'emb_strategy': random.randrange(1, 4) if emb_strategy is None else emb_strategy
    }

    # generate capsule embedding according to the strategy
    if im_rec['emb_strategy'] == 0:
        # jpg image, capsule in about field
        im_rec['content_type'] = 'image/jpeg'
        if coin_flip():
            im_rec['about'] = generate_bio()
        im_rec['image_data'], im_rec['image_shape'] = generate_image(ASSETS_FOLDER_PATH, image_format='jpg')
        im_rec['filename'] = 'image.jpg'
        return im_rec

    elif im_rec['emb_strategy'] == 1:
        # jpg image, capsule in about field
        im_rec['content_type'] = 'image/jpeg'
        im_rec['about'] = base64.b64encode(capsule.encode('utf-8')).decode('utf-8')
        im_rec['image_data'], im_rec['image_shape'] = generate_image(ASSETS_FOLDER_PATH, image_format='jpg')
        im_rec['filename'] = 'image.jpg'
        return im_rec

    elif im_rec['emb_strategy'] == 2:
        # png image, capsule in about field
        im_rec['content_type'] = 'image/png'
        im_rec['about'] = base64.b64encode(capsule.encode('utf-8')).decode('utf-8')
        im_rec['image_data'], im_rec['image_shape'] = generate_image(ASSETS_FOLDER_PATH, image_format='png')
        im_rec['filename'] = 'image.png'
        return im_rec

    else:
        # png image, capsule in the data
        im_rec['content_type'] = 'image/png'
        try:
            if coin_flip():
                im_rec['about'] = generate_bio()
            im_rec['image_data'], im_rec['image_shape'] = \
                generate_image(ASSETS_FOLDER_PATH, image_format='png', raw_data=False)
            im_rec['image_data'] = image_array_to_raw(embed_lsb(im_rec['image_data'], capsule), image_format='png')
        except Exception:
            # if failed to embed, switch to strategy png + about field
            im_rec['emb_strategy'] = 2  # N.B. emb_strategy must be set to 1
            im_rec['about'] = base64.b64encode(capsule.encode('utf-8')).decode('utf-8')
            im_rec['image_data'], im_rec['image_shape'] = generate_image(ASSETS_FOLDER_PATH, image_format='png')
        return im_rec


def check_capsule(image_rec, image_raw_data, image_shape, emb_strategy, capsule):
    if emb_strategy == 0:
        # capsule was not saved
        raise Exception("No capsule was not saved (strategy = 0)")

    elif emb_strategy == 1 or emb_strategy == 2:
        # png or jpg image, capsule in about field
        ret_capsule = base64.b64decode(image_rec['about'].encode('utf-8')).decode('utf-8')
        if ret_capsule != capsule:
            raise Exception('The retrieved and the actual capsules don\'t match')

    else:
        # png image, capsule in the data
        # N.B. we consider any error that might occur here to result in CORRUPT state
        image_array = image_raw_to_array(image_raw_data)
        if image_array.shape != image_shape:
            raise Exception('Incorrect image size: expected={0}, recv]{1}'.format(image_array.shape, image_shape))

        capsule_recv = extract_lsb(image_array)
        if capsule_recv != capsule:
            raise Exception('Retrieved capsule doesn\'t match the correct one: capsule="{0}", recv="{1}"'
                            .format(capsule, capsule_recv))


# endregion Payload generation and capsule checking


async def do_push(endpoint, capsule, _label, _metadata):
    # 1. preprocess the capsule
    capsule = decode_if_unicode(capsule)
    checker_name, checker_pass = generate_user_name(), generate_user_pass()

    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True),
                                     timeout=aiohttp.ClientTimeout(total=SESSION_TOTAL_TIMEOUT),
                                     skip_auto_headers={'User-Agent'}) as session:
        # 2. register a new user
        logger.info('[%s] on PUSH: registering user %s via POST /signup', endpoint, checker_name)
        try:
            # prepare POST request parameters
            headers = {'User-Agent': get_random_user_agent()}
            url = REGISTER_URI_FMT.format(endpoint=endpoint, port=PORT)
            data = {
                'username': checker_name,
                'first_name': generate_first_name(),
                'last_name': generate_last_name(),
                'password': checker_pass,
            }
            if coin_flip():
                data['about'] = generate_bio()

            # make the request
            async with session.post(url, headers=headers, data=data) as r:
                if r.status != REGISTER_RET_CODE_OK:
                    logger.info('[%s] on PUSH: registering failed, received code: %s', endpoint, r.status)
                    return Result.MUMBLE, '', 'Failed to register a new user'

        except aiohttp.ClientResponseError as ex:
            logger.error('[%s] on PUSH: failed to proceed after server had responded: %s', endpoint, ex)
            return Result.MUMBLE, '', 'Failed to register a new user'
        except aiohttp.ClientConnectionError as ex:
            logger.error('[%s] on PUSH: failed to establish connection: %s', endpoint, ex)
            return Result.DOWN, '', 'Connection error on POST /signup'
        except Exception as ex:
            logger.error('[%s] on PUSH: Exception while registering: %s', endpoint, ex)
            return Result.DOWN, '', 'Connection error on POST /signup'

        # 3. login as the user
        logger.info('[%s] on PUSH: logging in via POST at /login with %s:%s', endpoint, checker_name, checker_pass)
        try:
            url = LOGIN_URI_FMT.format(endpoint=endpoint, port=PORT)
            data = {
                'username': checker_name,
                'password': checker_pass,
            }
            async with session.post(url, headers=headers, data=data) as r:
                if r.status != LOGIN_RET_CODE_OK:
                    logger.info('[%s] on PUSH: failed to login with %s:%s, status=%s', endpoint, checker_name,
                                checker_pass, r.status)
                    return Result.MUMBLE, '', 'Failed to login'

        except aiohttp.ClientResponseError as ex:
            logger.error('[%s] on PUSH: failed to proceed after server had responded: %s', endpoint, ex)
            return Result.MUMBLE, '', 'Failed to login'
        except aiohttp.ClientConnectionError as ex:
            logger.error('[%s] on PUSH: failed to establish connection: %s', endpoint, ex)
            return Result.MUMBLE, '', 'Connection error on POST /login'
        except Exception as ex:
            logger.error('[%s] on PUSH: Exception while logging in: %s', endpoint, ex)
            return Result.MUMBLE, '', 'Connection error on POST /login'

        # 4. POST upload a new image
        try:
            logger.info('[%s] on PUSH: POSTing images via POST /image', endpoint)

            # generate request data
            url = POST_IMAGE_URI_FMT.format(endpoint=endpoint, port=PORT)
            datas, post_image_info, save_into_index = generate_post_image_requests(capsule)
            logger.info('[%s] on PUSH: uploading %s images', endpoint, len(datas))
            logger.info('[%s] on PUSH: using strategy \"%s\" to save the capsule', endpoint,
                        post_image_info['emb_strategy'])

            # make the requests
            image_records = []
            for data in datas:
                async with session.post(url, headers=headers, data=data) as r:
                    if r.status != POST_IMAGE_RET_CODE_OK:
                        logger.info('[%s] on PUSH: failed to POST /image, received code: %s', endpoint, r.status)
                        return Result.MUMBLE, '', 'Failed to create a new image'
                    image_record = await r.json()
                    if 'id' not in image_record:
                        logger.info('[%s] on PUSH: response doesn\'t contain ID of the newly created image', endpoint)
                        return Result.MUMBLE, '', 'Failed to create a new image'
                    image_records.append(image_record)
                    logger.info('[%s] on PUSH: saved image, image_id=%s', endpoint, image_record['id'])

            image_record = image_records[save_into_index]
            image_id = image_record['id']
            logger.info('[%s] on PUSH: saved the flag, image_id=%s', endpoint, image_id)

        except aiohttp.ClientResponseError as ex:
            logger.error('[%s] on PUSH: failed to proceed after server had responded: %s', endpoint, ex)
            return Result.MUMBLE, '', 'Failed to save a new image'
        except aiohttp.ClientConnectionError as ex:
            logger.error('[%s] on PUSH: surprisingly failed to connect (after successful /register and /login): %s',
                         endpoint, ex)
            logger.info('[%s] on PUSH: returning MUMBLE since the first part was successful', endpoint)
            return Result.MUMBLE, '', 'Connection error on POST /image'
        except Exception as ex:
            logger.error('[%s] on PUSH: Exception while querying /image: %s', endpoint, ex)
            return Result.MUMBLE, '', 'Failed to save a new image'

        # 4. get any of the images immediately (execute ~half the time)
        random.shuffle(image_records)
        for get_image_record in image_records:
            try:
                get_image_id = get_image_record['id']
                logger.info('[%s] on PUSH: GETing the image via GET at /image/%s', endpoint, get_image_id)
                url = GET_IMAGE_URI_FMT.format(endpoint=endpoint, port=PORT, image_id=get_image_id)
                async with session.get(url, headers=headers) as r:
                    if r.status != GET_IMAGE_RET_CODE_OK:
                        logger.info('[%s] on PUSH: received code=%s', endpoint, r.status)
                        return Result.MUMBLE, '', 'Failed to fetch an image info'
                    im_rec = await r.json()
                    im_rec_id = im_rec.get('id') or None
                    if im_rec_id is None or im_rec_id != get_image_id:
                        logger.info('[%s] on PUSH: retrieved an incorrect image record: expected id=%s, got=%s',
                                    endpoint, get_image_id, im_rec_id)
                        logger.debug('[%s] on PUSH: retrieved image record: %s', endpoint, im_rec)
                        return Result.MUMBLE, '', 'Incorrect image info'

            except aiohttp.ClientResponseError as ex:
                logger.error('[%s] on PUSH: failed to proceed after server had responded: %s', endpoint, ex)
                return Result.MUMBLE, '', 'Failed to fetch an image info'
            except aiohttp.ClientConnectionError as ex:
                logger.error('[%s] on PUSH: surprisingly failed to connect (after successful requests): %s',
                             endpoint, ex)
                logger.info('[%s] on PUSH: returning MUMBLE since the first part was a success', endpoint)
                return Result.MUMBLE, '', 'Connection error on GET /image/{id}'
            except Exception as ex:
                logger.error('[%s] on PUSH: Exception while querying /image/{id}: %s', endpoint, ex)
                return Result.MUMBLE, '', 'Failed to fetch an image info'

        logger.info('[%s] on PUSH: checked GETing the images info', endpoint)

        # 5. logout (half the time)
        # N.B. any errors are just ignored - we don't care
        if coin_flip():
            try:
                async with session.get(LOGOUT_URI_FMT.format(endpoint=endpoint, port=PORT), headers=headers) as r:
                    if r.status != LOGOUT_RET_CODE_OK:
                        logger.info('[%s] on PUSH: server returned %d on /logout', endpoint, r.status)
                    else:
                        await r.text()
                    logger.info('[%s] on PUSH: checked /logout', endpoint)
            except Exception as ex:
                logger.error('[%s] on PUSH: Exception on /logout: %s', endpoint, ex)
                logger.info('[%s] on PUSH:     ignoring', endpoint)

    # 5. save the user's creds and the image id for PULLing
    label = '{0}:{1}:{2}:{3}:{4}'.format(
        checker_name, checker_pass, post_image_info['image_shape'], image_id, post_image_info['emb_strategy']
    )
    return Result.UP, label, 'UP'


async def do_pull(endpoint, capsule, label, _metadata):
    # 1. get the checker's user credentials and other saved data
    capsule = decode_if_unicode(capsule)
    label = decode_if_unicode(label)
    v = label.split(':')
    checker_name, checker_pass, image_shape, image_id, emb_strategy = v[0], v[1], v[2], v[3], v[4]
    image_shape = tuple(map(int, image_shape.replace('(', '').replace(')', '').split(',')))
    emb_strategy = int(emb_strategy)

    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True),
                                     timeout=aiohttp.ClientTimeout(total=SESSION_TOTAL_TIMEOUT),
                                     skip_auto_headers={'User-Agent'}) as session:
        # 2. login as the user
        logger.info('[%s] on PULL: logging in via POST at /login as user: %s:%s', endpoint, checker_name, checker_pass)
        try:
            headers = {'User-Agent': get_random_user_agent()}
            url = LOGIN_URI_FMT.format(endpoint=endpoint, port=PORT)
            data = {
                'username': checker_name,
                'password': checker_pass,
            }
            async with session.post(url, headers=headers, data=data) as r:
                if r.status != LOGIN_RET_CODE_OK:
                    logger.info('[%s] on PULL: failed to login with %s:%s, status=%s', endpoint, checker_name,
                                checker_pass, r.status)
                    return Result.MUMBLE, 'Failed to login'

        except aiohttp.ClientResponseError as ex:
            logger.error('[%s] on PULL: failed to proceed after server had responded: %s', endpoint, ex)
            return Result.MUMBLE, 'Failed to login'
        except aiohttp.ClientConnectionError as ex:
            logger.error('[%s] on PULL: failed to establish connection: %s', endpoint, ex)
            return Result.DOWN, 'Connection error on POST /login'
        except Exception as ex:
            logger.error('[%s] on PULL: Exception while logging in: %s', endpoint, ex)
            return Result.DOWN, 'Connection error on POST /login'

        # 3. get the image info
        try:
            logger.info('[%s] on PULL: GETing the image via GET at /image/%s', endpoint, image_id)
            url = GET_IMAGE_URI_FMT.format(endpoint=endpoint, port=PORT, image_id=image_id)
            async with session.get(url, headers=headers) as r:
                if r.status != GET_IMAGE_RET_CODE_OK:
                    logger.info('[%s] on PULL: received code=%s', endpoint, r.status)
                    return Result.MUMBLE, 'Failed to fetch the image info'
                image_rec = await r.json()
                if 'url' not in image_rec:
                    logger.info('[%s] on PULL: response doesn\'t contain the contents url', endpoint)
                    return Result.MUMBLE, 'Failed to fetch the image info'
                image_contents_url = image_rec['url'] or ''

        except aiohttp.ClientResponseError as ex:
            logger.error('[%s] on PULL: failed to proceed after server had responded: %s', endpoint, ex)
            return Result.MUMBLE, 'Failed to fetch the image info'
        except aiohttp.ClientConnectionError as ex:
            logger.error('[%s] on PULL: surprisingly failed to connect (after successful /login): %s', endpoint, ex)
            logger.info('[%s] on PULL: returning MUMBLE since the first part was a success', endpoint)
            return Result.MUMBLE, 'Connection error on GET /image/{id}'
        except Exception as ex:
            logger.error('[%s] on PULL: Exception while querying /image/{id}: %s', endpoint, ex)
            return Result.MUMBLE, 'Failed to fetch the image info'

        # 4. fetch the image contents (raw data of .jpg or .png) via the link
        try:
            logger.info('[%s] on PULL: GETing the image contents via %s', endpoint, image_contents_url)
            image_contents_url = image_contents_url[1:] if image_contents_url.startswith('/') else image_contents_url
            url = GET_IMAGE_CONTENTS_FMT.format(endpoint=endpoint, port=PORT, uri=image_contents_url)
            async with session.get(url, headers=headers) as r:
                if r.status != DOWNLOAD_IMAGE_RET_CODE_OK:
                    logger.info('[%s] on PULL: received code: %s', endpoint, r.status)
                    return Result.MUMBLE, 'Failed to download the image'
                image_raw_data = await r.read()

        except aiohttp.ClientResponseError as ex:
            logger.error('[%s] on PULL: failed to proceed after server had responded: %s', endpoint, ex)
            return Result.MUMBLE, 'Failed to download the image'
        except aiohttp.ClientConnectionError as ex:
            logger.error('[%s] on PULL: surprisingly failed to connect (after successful reqs): %s', endpoint, ex)
            logger.info('[%s] on PULL: returning MUMBLE since the first part was successful', endpoint)
            return Result.MUMBLE, 'Failed to download the image'
        except Exception as ex:
            logger.error('[%s] on PULL: Exception while querying image contests: %s', endpoint, ex)
            return Result.MUMBLE, 'Failed to download the image'

    # 5. extract the LSB-embedded message and check it
    # N.B. we finished the session to check the flag without time restrictions (imposed by SESSION_TIMEOUT)
    try:
        check_capsule(image_rec, image_raw_data, image_shape, emb_strategy, capsule)
    except Exception as ex:
        logger.error('[%s] on PULL: Exception while checking the retrieved image: %s', endpoint, ex)
        return Result.CORRUPT, 'Incorrect flag'

    return Result.UP, 'UP'


async def push(endpoint, capsule, label, metadata):
    try:
        return await do_push(endpoint, capsule, label, metadata)
    except Exception as ex:
        # N.B. PARANOIA MODE ON!!! JAVA STYLE PROGRAMMING MODE ON!!!
        #      Only way we can end up here is an Exception while creating aiohttp.ClientSession,
        #        which kind of seems improbable, but...
        logger.exception('[%s] on PUSH: Exception while PUSHing capsule: %s', endpoint, ex)
        return Result.MUMBLE, '', 'Incorrect server response'


async def pull(endpoint, capsule, label, metadata):
    try:
        return await do_pull(endpoint, capsule, label, metadata)
    except Exception as ex:
        # N.B. PARANOIA MODE ON!!! JAVA STYLE PROGRAMMING MODE ON!!!
        #      sim.
        logger.exception('[%s] on PULL: Exception while PULLing capsule: %s', endpoint, ex)
        return Result.MUMBLE, 'Incorrect server response'


# region Tests


def embedding_successful_for_all_png_and_payloads():
    import glob
    from skimage.io import imread
    from utils import generate_fake_image

    capsule = 'VolgaCTF{eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.' \
              'eyJmbGFnIjoiNjNmNDRkNjk1YTZiZTFjZGFjYTllMzgwZjYwNTU5NTI9In0.' \
              'm-AchvFvM0e82H-FTRfGPzAnArxlh811Io74sJtww-QzgOLbxdJiAjXHi1Ds8lR59Ednv4piMQsQJrtShqfeMw}'
    capsule = capsule * 3

    # enumerate all the .png images in the assets and embed a string thrice the length of a typical capsule
    for image_file_path in glob.glob(os.path.join(os.path.join(ASSETS_FOLDER_PATH, 'png'), '*.png')):
        image_array = imread(image_file_path)
        stego_image_array = embed_lsb(image_array, capsule)
        extracted_capsule = extract_lsb(stego_image_array)
        assert extracted_capsule == capsule

    for _ in range(0, 10000):
        image_array, _ = generate_fake_image(img_fmt='png', raw_data=False)
        stego_image_array = embed_lsb(image_array, capsule)
        extracted_capsule = extract_lsb(stego_image_array)
        assert extracted_capsule == capsule


def image_array_data_transformations_are_successful():
    import glob
    import numpy as np
    from skimage.io import imread

    # enumerate all the images in the assets and check the conversion
    for ext in ['png', 'jpg']:
        for image_file_path in glob.glob(os.path.join(os.path.join(ASSETS_FOLDER_PATH, ext), '*.' + ext)):
            image_array = imread(image_file_path)
            image_raw_data = image_array_to_raw(image_array, image_format='png')
            converted_image_array = image_raw_to_array(image_raw_data)
            assert np.all(converted_image_array == image_array)


if __name__ == '__main__':
    embedding_successful_for_all_png_and_payloads()
    image_array_data_transformations_are_successful()

    pass

# endregion Tests
