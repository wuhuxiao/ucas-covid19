"""
author: Les1ie
mail: me@les1ie.com
license: CC BY-NC-SA 3.0
"""
import os
import json
import pytz
import hashlib
import requests
from time import sleep
from pathlib import Path
from random import randint
from datetime import datetime
from email.utils import formataddr
from email.mime.text import MIMEText

# 开启debug将会输出打卡填报的数据，关闭debug只会输出打卡成功或者失败，如果使用github actions，请务必设置该选项为False
debug = False

# 忽略网站的证书错误，这很不安全 :(
verify_cert = True

if os.environ.get('SEP_USER_NAME', None):
    user = os.environ.get('SEP_USER_NAME', '')  # sep账号
    passwd = os.environ.get('SEP_PASSWD', '')  # sep密码
    api_key = os.environ.get('API_KEY', '')  # server酱的api，填了可以微信通知打卡结果，不填没影响


def login(s: requests.Session, username, password, cookie_file: Path):

    if cookie_file.exists():
        cookie = json.loads(cookie_file.read_text(encoding='utf-8'))
        s.cookies = requests.utils.cookiejar_from_dict(cookie)
        # 测试cookie是否有效
        if get_daily(s) == False:
            print("cookie失效，进入登录流程")
        else:
            print("cookie有效，跳过登录环节")
            return

    payload = {
        "username": username,
        "password": password
    }
    r = s.post("https://app.ucas.ac.cn/uc/wap/login/check", data=payload)

    if r.json().get('m') != "操作成功":
        print("登录失败")
        message(api_key, "健康打卡登录失败", "登录失败")
    else:
        cookie_file.write_text(json.dumps(requests.utils.dict_from_cookiejar(
            r.cookies), indent=2), encoding='utf-8', )
        print("登录成功，cookies 保存在文件 {}，下次登录将优先使用cookies".format(cookie_file))


def get_daily(s: requests.Session):
    daily = s.get(
        "https://app.ucas.ac.cn/ncov/api/default/daily?xgh=0&app_id=ucas")
    # info = s.get("https://app.ucas.ac.cn/ncov/api/default/index?xgh=0&app_id=ucas")
    if '操作成功' not in daily.text:
        # 会话无效，跳转到了登录页面
        print("会话无效")
        return False

    j = daily.json()
    return j.get('d') if j.get('d', False) else False


def submit(s: requests.Session, old: dict):
    new_daily = {
        'realname': old['realname'],  # 姓名
        'number': old['number'],  # 学工号
        'szgj_api_info': old['szgj_api_info'],
        'sfzx': old['sfzx'],  # 是否在校
        'szdd': old['szdd'],  # 所在地点
        'ismoved': 0,  # 如果前一天位置变化这个值会为1，第二天仍然获取到昨天的1，而事实上位置是没变化的，所以置0
        'tw': old['tw'],  # 体温
        'sfcxtz': old['sfcxtz'],
        'sfjcbh': old['sfjcbh'],  # 是否接触病患
        'sfcyglq': old['sfcyglq'],  # 是否处于隔离期
        'sfcxzysx': old['sfcxzysx'],
        'old_szdd': old['old_szdd'],
        'geo_api_info': old['old_city'],  # 保持昨天的结果
        'old_city': old['old_city'],
        'sfzx': old['sfzx'],  # 是否在校
        'geo_api_infot': old['geo_api_infot'],
        'date': datetime.now(tz=pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d"),
        'fjsj': old['fjsj'],
        'remark': '21级新生',
        'jrsflj': '否',  # 近日是否离京
        'jcjgqk': old['jcjgqk'],
        'ljrq': old['ljrq'],
        'qwhd': old['qwhd'],
        'chdfj': old['chdfj'],
        'jrsfdgzgfxdq': old['jrsfdgzgfxdq'],
        'gtshcyjkzt': old['gtshcyjkzt'],
        'app_id': 'ucas'
    }

    r = s.post("https://app.ucas.ac.cn/ncov/api/default/save", data=new_daily)
    if debug:
        from urllib.parse import parse_qs, unquote
        print("昨日信息:", json.dumps(old, ensure_ascii=False, indent=2))
        print("提交信息:",
              json.dumps(parse_qs(unquote(r.request.body), keep_blank_values=True), indent=2, ensure_ascii=False))

    result = r.json()
    if result.get('m') == "操作成功":
        print("打卡成功")
    else:
        print("打卡失败，错误信息: ", r.json().get("m"))

    message(api_key, result.get('m'), new_daily)


def message(key, title, msg):
    """
    微信通知打卡结果
    """
    # 错误的key也可以发送消息，无需处理 :)
    if key is not None:
        msg_url = "https://push.bot.qw360.cn/send/{}?msg=[{}]{}".format(
            key, title, msg)
        requests.get(msg_url)


def report(username, password):
    s = requests.Session()
    s.verify = verify_cert  # 不验证证书
    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 \
        Chrome/78.0.3904.62 XWEB/2693 MMWEBSDK/201201 Mobile Safari/537.36 MMWEBID/1300 \
        MicroMessenger/7.0.22.1820 WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64"
    }
    s.headers.update(header)

    print(datetime.now(tz=pytz.timezone("Asia/Shanghai")
                       ).strftime("%Y-%m-%d %H:%M:%S %Z"))

    cookie_file_name = Path("{}.json".format(
        hashlib.sha512(username.encode()).hexdigest()[:8]))

    login(s, username, password, cookie_file_name)
    yesterday = get_daily(s)
    submit(s, yesterday)


if __name__ == "__main__":
    report(username=user, password=passwd)
