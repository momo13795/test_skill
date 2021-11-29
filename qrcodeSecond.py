import sys

import requests,time,json,random
from PIL import Image
import functools
import logging

"""设置日志输出方式 """
logging.basicConfig(format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('myLoger')



def parse_json(s):
    begin = s.find('{')
    end = s.rfind('}') + 1
    return json.loads(s[begin:end])


def response_status(resp):
    if resp.status_code != requests.codes.OK:
        print('Status: %u, Url: %s' % (resp.status_code, resp.url))
        return False
    return True


def check_login(func):
    """用户登陆态校验装饰器。若用户未登陆，则调用扫码登陆"""

    @functools.wraps(func)
    def new_func(self, *args, **kwargs):
        if not self.is_login:
            logger.info("{0} 需登陆后调用，开始扫码登陆".format(func.__name__))
            self.login_by_QRcode()
        return func(self, *args, **kwargs)

    return new_func


class User(object):
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        self.log_url = 'https://passport.jd.com/new/login.aspx'
        self.s = requests.Session()
        self.is_login = False
        self.headers = {'User-Agent': self.user_agent}


    def _get_login_page(self):
        url = "https://passport.jd.com/new/login.aspx"
        page = self.s.get(url, headers=self.headers)
        return page

    def loging(self):
        if self.is_login:
            logger.info('登录成功')
            self.open_order_page

        self._get_login_page()
        ticket = None
        retry_times = 10
        self.get_QR_code()
        for _ in range(retry_times):
            ticket = self._get_QRcode_ticket()
            if ticket:
                break
            else:
                print('二维码扫描结果异常')
            time.sleep(2)

        if not self._validate_QRcode_ticket(ticket):
            print('二维码信息校验失败')
            sys.exit()

        print('二维码登录成功')
        self.is_login = True
        self.nick_name = self.get_user_info()
        self.open_order_page()

    def get_QR_code(self):
        QR_code_url = 'http://qr.m.jd.com/show?appid=133&size=147&t=%d'%(time.time()*1000)
        headers = {':authority': 'qr.m.jd.com',
        ':method': 'GET',
        ':path': '/show?appid=133&size=147&t=',
        ':scheme': 'https',
        'referer': 'https://passport.jd.com/new/login.aspx',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-site',
        'user-agent':self.user_agent}
        response = self.s.get(url = QR_code_url,).content
        with open('QRcode.jpg','wb') as f:
            f.write(response)
        image = Image.open('QRcode.jpg')
        image.show()
        time.sleep(10)

    def _validate_QRcode_ticket(self, ticket):
        url = 'https://passport.jd.com/uc/qrCodeTicketValidation'
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://passport.jd.com/uc/login?ltype=logout',
        }
        resp = self.s.get(url=url, headers=headers, params={'t': ticket})

        if not response_status(resp):
            return False

        resp_json = json.loads(resp.text)
        if resp_json['returnCode'] == 0:
            return True
        else:
            logger.info(resp_json)
            return False


    def _get_QRcode_ticket(self):
        url = 'https://qr.m.jd.com/check'
        payload = {
            'appid': '133',
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'token': self.s.cookies.get('wlfstk_smdl'),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.s.get(url=url, headers=headers, params=payload)
        if not response_status(resp):
            print('获取二维码扫描结果异常')
            return False

        resp_json = parse_json(resp.text)
        if resp_json['code'] != 200:
            print('Code: %s, Message: %s', resp_json['code'], resp_json['msg'])
            return None
        else:
            print('已完成手机客户端确认')
            self.is_login  = True
            a = resp_json['ticket']
            return a

    @check_login
    def open_order_page(self):
        url = 'https://order.jd.com/center/list.action'
        payload = {
            'search': 0,
            'd': 1,
            's': 4096,
        }  # Orders for nearly three months
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://passport.jd.com/uc/login?ltype=logout',
        }

        resp = self.s.get(url=url, params=payload, headers=headers)
        print(resp.text)
        print(self.s.cookies)

    @check_login
    def get_user_info(self):
        """获取用户信息
        :return: 用户名
        """
        url = 'https://passport.jd.com/user/petName/getUserInfoForMiniJd.action'
        payload = {
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://order.jd.com/center/list.action',
        }
        try:
            resp = self.s.get(url=url, params=payload, headers=headers)
            resp_json = parse_json(resp.text)
            # many user info are included in response, now return nick name in it
            # jQuery2381773({"imgUrl":"//storage.360buyimg.com/i.imageUpload/xxx.jpg","lastLoginTime":"","nickName":"xxx","plusStatus":"0","realName":"xxx","userLevel":x,"userScoreVO":{"accountScore":xx,"activityScore":xx,"consumptionScore":xxxxx,"default":false,"financeScore":xxx,"pin":"xxx","riskScore":x,"totalScore":xxxxx}})
            return resp_json.get('nickName') or 'jd'
        except:
            return 'jd'






a = User()
a.loging()