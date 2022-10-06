# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import random
import sys

import aiohttp
from aiohttp import ClientSession, CookieJar, ClientTimeout, FormData
from volgactf.final.checker.result import Result

from .external import user_agents
from .helper import get_rand_element, random_str

logger = logging.getLogger(__name__)

# ------------------------ SOME CONSTANTS ------------------------

TIMEOUT = int(os.getenv('MYBLOG_TIMEOUT', 20))
PORT = int(os.getenv('MYBLOG_PORT', 13377))

# ------------------------ ANNOYING MESSAGES ---------------------

NOT_WORKING_MESSAGE = "Why is your service not working?"
FLAG_WAS_LOST = "You have just lost your flag :("
ALL_FINE = "You're doing good"
CORRUPTED = "Is your flag corruption an accident?"


def ping_enabled():
    return os.getenv('VOLGACTF_FINAL_PING_ENABLED', 'yes') == 'yes'


# -------------------------- HELP FUNCTION ---------------------------------------
async def post_request(url, headers, json_inp=None, data=None, cookies=None):
    timeout = ClientTimeout(total=TIMEOUT)
    jar = CookieJar(unsafe=True)
    async with ClientSession(cookie_jar=jar, cookies=cookies, timeout=timeout, skip_auto_headers={"User-Agent"}) as session:
        async with session.post(url, headers=headers, json=json_inp, data=data) as r:
            data = ""
            json_data = ""
            if hasattr(r, "data"):
                data = await r.data
            if r.content_type == 'application/json':
                json_data = await r.json()
            return r.status, json_data, data
async def get_request(url, headers, cookies={}):
    timeout = ClientTimeout(total=TIMEOUT)
    jar = CookieJar(unsafe=True)
    async with ClientSession(cookie_jar=jar, cookies=cookies, timeout=timeout, skip_auto_headers={"User-Agent"}) as session:
        async with session.get(url, headers=headers) as r:
            data = ""
            json_data = ""
            if hasattr(r, "data"):
                data = await r.data
            if r.content_type == 'application/json':
                json_data = await r.json()
            return r.status, json_data, data

# ------------------------ SIGN-UP & SIGN-IN FUNCTION ----------------------------

async def register_user(endpoint, creds):
    url = get_url(endpoint) + "/api/auth/sign_up"
    timeout = ClientTimeout(total=TIMEOUT)
    jar = CookieJar(unsafe=True)
    headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}

    session = ClientSession(cookie_jar=jar, timeout=timeout, skip_auto_headers={"User-Agent"})
    try:
        async with session.post(url, headers=headers, json=creds) as r:
            if r.status == 200 or r.status == 403:  # 403 stands for User Already Registered
                await session.close()
                return Result.UP
            await session.close()
            return Result.MUMBLE
    except Exception:
        logger.error('An exception occurred', exc_info=sys.exc_info())
        await session.close()
        return Result.MUMBLE
    return Result.MUMBLE


async def authN(endpoint, LOGIN_CREDS):
    result, auth_token = await login_user(endpoint, LOGIN_CREDS)
    if result != Result.UP:
        return ''
    return auth_token.value


async def login_user(endpoint, creds):
    url = get_url(endpoint) + "/api/auth/sign_in"
    timeout = ClientTimeout(total=TIMEOUT)
    jar = CookieJar(unsafe=True)
    headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}

    session = ClientSession(cookie_jar=jar, timeout=timeout, skip_auto_headers={"User-Agent"})
    try:
        async with session.post(url, headers=headers, json=creds) as r:
            if r.status == 200:
                await session.close()
                return Result.UP, r.cookies.get('session')
            await session.close()
            return Result.MUMBLE, None
    except Exception:
        logger.error('An exception occurred', exc_info=sys.exc_info())
        await session.close()
        return Result.MUMBLE, None
    return Result.MUMBLE, None


def get_url(endpoint):
    return "http://{0}:{1}".format(endpoint, PORT)


async def ping_service(endpoint):
    url = get_url(endpoint) +"/health_check"
    timeout = ClientTimeout(total=TIMEOUT)
    jar = CookieJar(unsafe=True)
    headers = {'User-Agent:': get_rand_element(user_agents)}

    session = ClientSession(cookie_jar=jar, timeout=timeout, skip_auto_headers={"User-Agent"})
    try:
        async with session.get(url, headers=headers) as r:
            await session.close()
            if r.status == 200:
                return Result.UP
            return Result.DOWN
    except Exception:
        logger.error('An exception occurred', exc_info=sys.exc_info())
        await session.close()
        return Result.DOWN
    return Result.MUMBLE

async def check_another_func(endpoint, creads):
    async def check_blogs_list(blog_id):
        url = get_url(endpoint)+"/api/blogs"
        headers = {'User-Agent:': get_rand_element(user_agents)}
        status_code, json_data, data_data = await get_request(url, headers=headers)
        if status_code == 200:
            record = next(item for item in json_data if item["url"] == blog_id)
            if record:
                return True
            else:
                print("check_blogs_list - not successful")
                return False

    async def check_image_upload(token):
        folder = random_str(8)
        url = get_url(endpoint)+f"/file/upload?path={folder}"
        cookies = {'session': token}
        file_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x02\x00\x00\x00\xfc\x18\xed\xa3\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x05\x17IDATH\x89\x9dV\xfdO\x13g\x1c\xef\xdf\xb0_\xf6\xc3\x94\xb6\x14*\xd2^\xefzo\xed\xd1\xbb\xbeS\xdan\xcc\x01+\xacF\x8dd.LE\x9c! \x03\xa2AQ\x06\x03\t40:p"2 \x0ep\xbe-31:q\xcaL\x9dC\xb7\xfd\xb0(\x0cfp0\xb0Z\xc4\x96\x97\xf6n\xb9\x1e4\xa4-P|\xf2\xe4~\xb8\xdc\xf3\xf9|\xbe\x9f\xef\xcb=<&\xb6\xe5}\xedu\xdd\xb9\xd7\xe6\xf8\xbaxo\xa1\xddb3a\x06\xad\x8c4\xa1\xfa\x8f,\xb6\xc3\xfb\x8a\\\x83.\x86ah\x9a\x8e<\xc8\x8b\x05\xbd\xab\xed\x9c\xcd\x98AI\x08D\x00\xe2"X\xb5U\xa1\x96\xa6h\x00\x95Z\x9aB&+Q!\xa4\x96\xa6\xdc\xbe1\xc00L \x10\xd8\x18A x\xc0Q\xdd {\'Y\x0f\xa9\xf5\x90Z\x07RZ\x19\xa9\x01T\xdc\xd6\xcaH\x83\\\x93\x92\x84[\t\xd3\xd3\xb1\x7f"\xe3X\x87\x80\x0e~\xfd\xca3c3e\xa6$\xe1+\xa1Wn=\xa4F\xf8\xb2\x93e\x95\x91A\xaco\x91\xdf\xefg\x18\xa6\xe5T3"\x00\xf5\x90:*\x81VFR\x12\xc2\xac0N>\x9b\x08\x0bb}\x82@P\xd1\xc3_\x87(\t\x11\x15\x9d\xdb:\x90\xc2E\xf2\xab\xfdWB\x9ab%\xa0\x83r\xe6|>[\xea:.\xc9\xe3\x80\x86\xaa\xfa\r\x130\xcb\x1c%\xf9EX\xbc\\\x07R\xd1#\x80(,\x1e*+(\xd9\xb0E\xcc\xb2"Gu\x83<\x0eX-\rA\x8b\xe0\xcf>>\x10v66\x82E\x96\xa0\xb3\xadc]\x82CoH\xe0g\t\xfa\xbazQ!\xa8[\x8d\x80\xb5H^z\xe0\xf0\x9b[\xd4\xdby~\x8dJ\xd5Cj\x98\x0f\xd4VT\x87\xb5\xc2\x06,jo\xf9\x06\xda,\xd5\xcbW\'\x88\x03\xbaNw\x86\xbe\xdf\x00A \xa8\xe8\x8b\xf2\x13\x08_\xb6F\xaf\xa9\xb6*\x06\x07\xeel<\x02\x9a},..\xe6f\xee"\xc4\xa86Z\x99je$\x99\xac\xb4(M\xcf\xa7\x9e\xbfa\'?\xf9\xeb\x89\x0e\xa4\xd8!*[\xb5\x84\x0e\xe6\xe6G\x1e\x8fu\x16\xb5\xb7\x9cY;\xc3\x88\x00\xec\xef\xea\rk\xe3X\xa7\xe9\xfc\xfc\xfc\x8et;!\xc6\xa2\xfb\x03R\xc4\x16,\'-k\xf6\xd5,G@\xc7\x9e\x03\x7fP\xce\x0f\x17\xaeb\xa2U\x87\x84\x1eR\xa3B\xe8r\xefE\xd6O\xff\x12\xb4\xdf\xef\x9f}5\xfb\xc2\xfd\x82\xb7\xae\xfc\x19\xcf\xccvk6!\xc6\xa2\x12p\x7f\x82\xe2\xbd\x85\\\xb6F\x1e\x8f\xf4u\xf5\x9e(=\x9eg\xdfcV\x18K\x0bJV%\xa0i:T\x9d\xa8\x10\xd2A\xd1\xd1q\x11l\xb7d\xbft\xbf\x1c\x7f:\xfe\xe9\xf6O\x0c\xb0\x16\x13\xc9a\xbe\x8c\x10c\xd0&I\xf5\x91\x93\xbc\xb5\xd1[\x1b\x9d\xb8H\x1euD\xb3\xe8\tp\x96\xfe\x83\xd1\xe1Q\x86a\x16\x16\x16>\xcf/\xe6\n!\r7\xa4\x93\x16\xc9\xdb\xe2s\xadg\xa3\x10\xd0\x01\xd6\x19\x9a\xa6\x9bk\x1d\xb8\x08f\xd1e\xd1}\xb7[\xb3\xc7F\xc6B\xa9\x9a|6\x91\xa1K\x97\xc7\x01\xd5G\xaa\x18\x86\xa9;V38p7\x9c\x80\x13\xfe\xd2\xfd\xa2\xac\xa0\x04\x8b\x8f\xa2\x9d\xfb\xe9#|\xb0`\xf7\xfe\xa9\xc9\xa9\xd0\x11.\xbd\xb5\xc7j\xe08\xc0\xac0v8\xdb9b^\xa4-\xf7\x07]9iY\x98\x10\n\xcb\xaaVF\xea J)FUI\x8a\xa6/\x1dsss+\x9b\x96\x9b?\x1d\xcevv\xa4\x83\x14\xb4YZ[Q\xb3T\xa6!h\x9f\xd7\xdbr\xaa\x89LV\x12[\xb0\x95cY\x07RzH\x9d\x92\x84#Bhw\xc6N\xd7\xdd{\x9c\xf0\x95#\x81\x8b\xe0ha9*\x84\xb8\xdb\r"\x00\xaf\xf4]\xe6\xd1\xc1\xc50\xcc\x90\xeb\xb7\xdc\xac]\xa8\x00\xe4\xc4\x86p5\x80J\x91\x88`\xf1P\xb6)\xf3|G\x8f\xcf\xeb\r\x9b6\x81@\x80C\x1f\xb8~\x8b\xbb\x90-\xcd\xbe$\xdc\x96\x9a\xc1F0\xe3\xf18\xaa\x1b\x82\xaf\x14FX\xcb:#U\x91[\x95\xb8\x08F\x04\xa0\x16P\xe5\xd9\xf7\\\xe8\xee\x9b\xf1x8h\xae\nX\xdc\xe5\x8e\xa5i\xfa\xd2w\x17\x8d\xb0\x96LV\xaeL[*\xaa\xe3}\xdf\xd3oD\xb4\xe2\xb7\x84p\x1c\x00\xf3\x01\x98\x0fr=\xf5>e=\xb4\xa7\xe0L\xf3\xe9?\x1f\xfd\xc1\x15\tM\xd3\x8b\x0b\x8ba\xf7*\xef\xeb\xd77\xaf\xdd8\xb0{\xbf"\x01\xa1$D\x08]/\xd7 \x02\xb0\xa2\xe8(\xaf\xa7\xbd\xbb\xb9\xd6\xe1\xac\xff\xaa\xa9\xd6\xd1\xda\xe8\xec>\xf3\xed\xb5\xcb?>z\xf0\xd0=\xed\x8e\xbch2\xcbu<\xfd\xdf\xd4\xad\xeb?\xd5W\xd6\xd9-6B\x8c*\x13\x11]\xd0wn\x1b`\x8dR\x8cZ\t\xd3\xe8\xf0\xdf1\x8dk\x9fonb\xfc\xdf\xfb\xbf\xb8\xfa{\xfa\xeb+\xeb\xf6\xef\xcc\xb3*M\x84\x18\x93o\x96*\x13QJBpu\xa1LD\x15\tl\xb6\xc0M\x92\xf7H\xf3\x90\xeb\x01[E\xfe\xe0\n\xf8\x03\xf3s\xf3\xeei\xf7\xd8\xc8\xd8\xefC\x8f~\xbey\xfbJ\xef\xa5\xd6F\xe7\xf1\x92\x8a\x83\xb9\xf99\xe6\x0f\xd3p\x83\x06P\xe1"\x18\x15\x80\xaa$\x85\x0e\xa4\xcc\xb81\x9d4oS\xbf\x9be\xd8f\xb7f\xe7f\xee\xda\xb7#\xafxoaUyek\xa3s\xe4\xf10\'\xee\x7f\xc8C\xe2\x94\xb5\xb8\xaa\xe6\x00\x00\x00\x00IEND\xaeB`\x82'
        data_file = FormData()
        data_file.add_field('file',
                       file_bytes,
                       filename='favicon.png',
                       content_type='image/png')
        headers = {'User-Agent:': get_rand_element(user_agents)}
        status_code, json_data, data_data = await post_request(url, headers=headers, cookies=cookies, data=data_file)
        if status_code == 200:
            name = json_data.get("filename")
            return folder, name
        else:
            print("check_image_upload - not successful")
            return None, None
    async def check_image_access(path, filename):
        async def check_file_list_exist():
            url = get_url(endpoint)+f"/file/list?path={path}"
            headers = {'User-Agent:': get_rand_element(user_agents)}
            status_code, json_data, data_data = await get_request(url, headers=headers)
            if (filename in json_data):
                return True
            else:
                print("check_file_list_exist - not successful")
                return False

        exist_in_list = await check_file_list_exist()
        if exist_in_list:
            url = get_url(endpoint)+f"/image/ss?another={path}&filename={filename}" #TODO WITHOUT SS -> payload
            headers = {'User-Agent:': get_rand_element(user_agents)}
            status_code, json_data, data_data = await get_request(url, headers=headers)
            if status_code == 200:
                return True
            else:
                print("check_image_access - not successful")
                return False

    try:
        auth_token = await authN(endpoint, {"username": creads.get("username"),
                                            "password": creads.get("password")})
        if auth_token:
            blog_url = await get_blog(endpoint, auth_token)
            if blog_url:
                if await check_blogs_list(blog_url):
                    path, filename = await check_image_upload(auth_token)
                    if filename and path:
                        check_image_result = await check_image_access(path, filename)
                        if check_image_result:
                            return Result.UP, ""
                        else:
                            return Result.MUMBLE, "check image access - failed"
                    else:
                        return Result.MUMBLE, "check file's name or path failed"
                else:
                    return Result.MUMBLE, "check_blogs_list failed"
            else:
                return Result.MUMBLE, "GET blog_url failed"
        else:
            return Result.MUMBLE, "auth failed"
    except:
        logger.error('An exception occurred', exc_info=sys.exc_info())
        return Result.MUMBLE, "exception"



# ------------------------ PUSH & PULL --------------------------

async def push_content_server_flag(endpoint, flag, TI_REGISTRATION_CREDS):
    result = await register_user(endpoint, TI_REGISTRATION_CREDS)
    if result == Result.UP:
        auth_token = await authN(endpoint, {"username": TI_REGISTRATION_CREDS.get("username"),
                                            "password": TI_REGISTRATION_CREDS.get("password")})
        cookies = {"session": auth_token}
        url = get_url(endpoint) + "/file/upload?path=secrets"
        timeout = ClientTimeout(total=TIMEOUT)
        jar = CookieJar(unsafe=True)
        headers = {'User-Agent:': get_rand_element(user_agents)}

        # with BytesIO() as myio:
        #     myio.write(flag.encode())
        form_data = aiohttp.FormData()
        form_data.add_field('file', flag.encode(), filename=TI_REGISTRATION_CREDS.get("username")+".txt", content_type='multipart/form-data')

        session = ClientSession(cookie_jar=jar, cookies=cookies, timeout=timeout, skip_auto_headers={"User-Agent"})
        try:
            async with session.post(url, headers=headers, data=form_data) as r:
                if r.status == 200:
                    await session.close()
                    return Result.UP
                await session.close()
                return Result.MUMBLE
        except Exception:
            logger.error('An exception occurred', exc_info=sys.exc_info())
            await session.close()
            return Result.MUMBLE
    return Result.MUMBLE

async def push_blog_flag(endpoint, capsule, TI_REGISTRATION_CREDS):
    result = await register_user(endpoint, TI_REGISTRATION_CREDS)
    if result == Result.UP:
        try:
            auth_token = await authN(endpoint, {"username":TI_REGISTRATION_CREDS.get("username"), "password":TI_REGISTRATION_CREDS.get("password")})
            return await send_create_site(endpoint, auth_token, capsule)
        except:
            logger.error('An exception occurred', exc_info=sys.exc_info())
            return Result.MUMBLE, ''
    return Result.MUMBLE, ''




async def send_create_site(endpoint, token, ti_capsule) -> (int, str):
    async def get_blog():
        url = get_url(endpoint) + "/api/blog"
        headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}
        cookies = {"session": token}
        status, json_data, data_data = await get_request(url, headers, cookies=cookies)
        if status == 200:
            return json_data.get("url")
        else:
            return None
    async def create_post(blog_id):
        url = get_url(endpoint) + f"/api/blog/{blog_id}/create_post"

        headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}
        json_data = {"title": "secret",
                "body": ti_capsule}
        cookies = {"session": token}
        status, json_data, data_data = await post_request(url, headers, json_inp=json_data, cookies=cookies)
        if status == 200:
            return Result.UP, json_data.get("post_id")
        return  Result.MUMBLE, ''
    blog_url = await get_blog()
    if blog_url:
        return await create_post(blog_url)
    else:
        return Result.MUMBLE, ""

async def push(endpoint, capsule, label, metadata):
    result = await ping_service(endpoint)
    if result != Result.UP:
        return result, label, NOT_WORKING_MESSAGE

    round_num = metadata.round  # .get('round') TODO
    round_remainder = round_num % 2

    ad_username = random_str(random.randrange(6, 10))  # "test"
    ad_password = random_str(random.randrange(8, 12))  # "test1337"
    AD_REGISTRATION_CREDS = dict(username=ad_username, password=ad_password)
    if round_remainder == 1:
        print('push content_server')
         #is_private == Null -> for server False
        result = await push_content_server_flag(endpoint, capsule, AD_REGISTRATION_CREDS)
        if result != Result.UP:
            return result, json.dumps({"round_remainder": round_remainder}), FLAG_WAS_LOST
        return result, json.dumps(
            {"round_remainder": round_remainder, "username": ad_username, "password": ad_password}), ALL_FINE
    else:
        print('push blog private text')
        result, post_id = await push_blog_flag(endpoint, capsule, AD_REGISTRATION_CREDS)
        if result != Result.UP:
            return result, json.dumps({"round_remainder": round_remainder}), FLAG_WAS_LOST
        return result, json.dumps({"round_remainder": round_remainder, "post_id": post_id, "username": ad_username,
                                   "password": ad_password}), ALL_FINE

async def pull(endpoint, capsule, label, metadata):
    result = await ping_service(endpoint)
    if result != Result.UP:
        return result, NOT_WORKING_MESSAGE

    round_num = metadata.round  # .get('round') TODO
    round_remainder = round_num % 2


    result, msg = await check_another_func(endpoint, json.loads(label))
    if result != Result.UP:
        return result, msg



    if round_remainder == 1:
        print('pull content_server')
        result = await pull_content_server_flag(endpoint, capsule, json.loads(label))
        if result == Result.UP:
            return result, ALL_FINE
        elif result == Result.CORRUPT:
            return result, CORRUPTED
        else:
            return result, NOT_WORKING_MESSAGE
    else:
        print('pull blog private text')
        result, msg = await pull_blog_flag(endpoint, capsule, json.loads(label))
        if result == Result.UP:
            return result, ALL_FINE
        elif result == Result.CORRUPT:
            return result, msg
        else:
            return result, msg

async def pull_blog_flag(endpoint, capsule, label):
    auth_token = await authN(endpoint, label)
    return await get_blog_capsule(endpoint, auth_token, capsule, label.get('username'))

async def pull_content_server_flag(endpoint, capsule, label):
    auth_token = await authN(endpoint, label)
    return await get_file_capsule(endpoint, auth_token, capsule, label.get('username'))

async def get_blog(endpoint, token):
    url = get_url(endpoint) + "/api/blog"
    headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}
    cookies = {"session": token}
    status, json_data, data_data = await get_request(url, headers, cookies=cookies)
    if status == 200:
        return json_data.get("url")
    else:
        return None

async def get_blog_capsule(endpoint, token, capsule, username):

    async def get_posts():
        url = get_url(endpoint) + f"/api/blog/{blog_id}"
        headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}
        cookies = {"session": token}
        status, json_data, data_data = await get_request(url, headers, cookies=cookies)
        if status == 200:
            return json_data.get("posts")
        else:
            return None

    async def get_post():
        url = get_url(endpoint) + f"/api/blog/{blog_id}/post/{needed_post_id}"
        headers = {'User-Agent:': get_rand_element(user_agents), 'content-type': 'application/json'}
        cookies = {"session": token}
        status, json_data, data_data = await get_request(url, headers, cookies=cookies)
        if status == 200:
            return json_data.get("body")
        else:
            return None

    try:
        blog_id = await get_blog(endpoint, token)
        if blog_id:
            posts = await get_posts()
            needed_post_id = next(item["id"] for item in posts if item["title"] == "secret")
            if needed_post_id:
                expected_capsule = await get_post()
                if expected_capsule == capsule:
                    return Result.UP, ''
                else:
                    return Result.CORRUPT, 'cant get flag in post'

    except:
        return Result.MUMBLE, 'except'


async def get_file_capsule(endpoint, token, capsule, username):
    async def check_file_secrets(filename):
        url = get_url(endpoint) + f"/file/list?path=secrets"
        headers = {'User-Agent:': get_rand_element(user_agents)}
        status_code, json_data, data_data = await get_request(url, headers=headers)
        if (filename in json_data):
            return True
        else:
            print("check_file_secrets - not successful")
            return False

    res = await check_file_secrets(username+'.txt')
    if res:
        url = get_url(endpoint) + f"/file/get/secrets?filename={username+'.txt'}"
        timeout = ClientTimeout(total=TIMEOUT)
        jar = CookieJar(unsafe=True)
        headers = {'User-Agent:': get_rand_element(user_agents)}
        cookies = {"session": token}
        session = ClientSession(cookie_jar=jar, cookies=cookies, timeout=timeout, skip_auto_headers={"User-Agent"})
        try:
            async with session.get(url, headers=headers) as r:
                if r.status == 200:
                    data = await r.read()
                    expected_capsule = data.decode("utf-8").strip()
                    await session.close()
                    if expected_capsule == capsule:
                        return Result.UP
                    else:
                        return Result.CORRUPT
                await session.close()
                return Result.MUMBLE
        except Exception:
            logger.error('An exception occurred', exc_info=sys.exc_info())
            await session.close()
            return Result.MUMBLE
        return Result.MUMBLE
    else:
        return Result.MUMBLE

# ------------------------ TEST MAIN ------------------------


def play_round(endpoint):
    metadata = {'round': 1}  # site_prefix to push_site)
    loop = asyncio.get_event_loop()

    total_rounds = 1

    for i in range(2 * total_rounds):
        label = ""
        capsule = 'time {}'.format(i)
        push_task = loop.create_task(push(endpoint, capsule, label, metadata))
        loop.run_until_complete(push_task)
        status, label, msg = push_task.result()
        print("push task", (status, label, msg))

        pull_task = loop.create_task(pull(endpoint, capsule, label, metadata))
        loop.run_until_complete(pull_task)
        status, msg = pull_task.result()
        print("pull task", (status, msg))

        metadata['round'] += 1

    loop.close()


if __name__ == "__main__":
    play_round(endpoint="127.0.0.1")
