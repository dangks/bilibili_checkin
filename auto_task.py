import requests

import json

import time

import os

import sys

from datetime import datetime, timedelta, timezone

from loguru import logger

# 配置日志 (这部分代码保持不变)

class BeijingFormatter:

    @staticmethod

    def format(record):

        dt = datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc)

        local_dt = dt + timedelta(hours=8)

        record["extra"]["local_time"] = local_dt.strftime('%H:%M:%S,%f')[:-3]

        return "{time:YYYY-MM-DD HH:mm:ss,SSS}(CST {extra[local_time]}) - {level} - {message}\n"

logger.remove()

logger.add(sys.stdout, format=BeijingFormatter.format, level="INFO", colorize=True)

# BilibiliTask 类 (这部分代码保持不变)

class BilibiliTask:

    def __init__(self, cookie):

        self.cookie = cookie

        self.headers = {

            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',

            'Accept': 'application/json, text/plain, */*',

            'Cookie': cookie

        }

        

    def get_csrf(self):

        """从cookie获取csrf"""

        for item in self.cookie.split(';'):

            if item.strip().startswith('bili_jct'):

                return item.split('=')[1]

        return None

    def check_login_status(self):

        """检查登录状态"""

        try:

            res = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=self.headers)

            if res.json()['code'] == -101:

                return False, '账号未登录或Cookie失效'

            return True, None

        except Exception as e:

            return False, str(e)

        

    def share_video(self):

        """分享视频"""

        try:

            res = requests.get('https://api.bilibili.com/x/web-interface/dynamic/region?ps=1&rid=1', headers=self.headers)

            bvid = res.json()['data']['archives'][0]['bvid']

            data = {'bvid': bvid, 'csrf': self.get_csrf()}

            res = requests.post('https://api.bilibili.com/x/web-interface/share/add', headers=self.headers, data=data)

            if res.json()['code'] == 0:

                return True, None

            else:

                return False, res.json().get('message', '未知错误')

        except Exception as e:

            return False, str(e)

            

    def watch_video(self, bvid):

        """观看视频"""

        try:

            data = {'bvid': bvid, 'csrf': self.get_csrf(), 'played_time': '2'}

            res = requests.post('https://api.bilibili.com/x/click-interface/web/heartbeat', 

                              headers=self.headers, data=data)

            if res.json()['code'] == 0:

                return True, None

            else:

                return False, res.json().get('message', '未知错误')

        except Exception as e:

            return False, str(e)

            

    def live_sign(self):

        """直播签到"""

        try:

            res = requests.get('https://api.live.bilibili.com/xlive/web-ucenter/v1/sign/DoSign',

                             headers=self.headers)

            if res.json()['code'] == 0:

                return True, None

            else:

                return False, res.json().get('message', '未知错误')

        except Exception as e:

            return False, str(e)

            

    def manga_sign(self):

        """漫画签到"""

        try:

            res = requests.post('https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn',

                              headers=self.headers,

                              data={'platform': 'ios'})

            if res.json()['code'] == 0:

                return True, None

            else:

                return False, res.json().get('message', '未知错误')

        except Exception as e:

            return False, str(e)

            

    def get_user_info(self):

        """获取用户信息"""

        try:

            res = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=self.headers)

            data = res.json()['data']

            return {

                'uname': data['uname'],

                'uid': data['mid'],

                'level': data['level_info']['current_level'],

                'exp': data['level_info']['current_exp'],

                'coin': data['money']

            }

        except:

            return None

# log_info 日志函数 (这部分代码保持不变)

def log_info(tasks, user_info):

    """记录任务和用户信息的日志"""

    logger.info('=' * 20 + ' 任务完成情况 ' + '=' * 20)

    for name, (success, message) in tasks.items():

        if success:

            logger.info(f'任务【{name}】: ✅成功')

        else:

            logger.error(f'任务【{name}】: ❌失败，原因: {message}')

        

    if user_info:

        logger.info('=' * 22 + ' 用户信息 ' + '=' * 22)

        logger.info(f'用户名称: {user_info["uname"]}')

        logger.info(f'用户等级: {user_info["level"]}')

        logger.info(f'当前经验: {user_info["exp"]}')

        logger.info(f'拥有硬币: {user_info["coin"]}')

    logger.info('=' * 58)

# ====================================================================

# 【新增】格式化推送消息的函数

# ====================================================================

def format_push_message(tasks, user_info):

    """将任务结果和用户信息格式化为推送内容"""

    # 使用 Markdown 格式

    content = []

    content.append("### Bilibili 签到任务报告\n")

    

    # 任务详情

    content.append("#### 任务详情")

    for name, (success, message) in tasks.items():

        status_icon = "✅" if success else "❌"

        reason = f" - 原因: {message}" if not success and message else ""

        content.append(f"- **{name}**: {status_icon}{reason}")

        

    # 用户信息

    if user_info:

        content.append("\n#### 用户信息")

        content.append(f"- **用户名称**: {user_info['uname']}")

        content.append(f"- **用户等级**: Lv.{user_info['level']}")

        content.append(f"- **当前经验**: {user_info['exp']}")

        content.append(f"- **拥有硬币**: {user_info['coin']}")

        

    # 添加时间戳

    beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')

    content.append(f"\n> 报告时间: {beijing_time}")

    

    return "\n".join(content)

# ====================================================================

# 【新增】发送到 PushPlus 的函数

# ====================================================================

def send_to_pushplus(token, title, content):

    """发送消息到 PushPlus"""

    url = "http://www.pushplus.plus/send"

    data = {

        "token": token,

        "title": title,

        "content": content,

        "template": "markdown"  # 使用 markdown 格式

    }

    try:

        res = requests.post(url, json=data)

        res_json = res.json()

        if res_json.get('code') == 200:

            logger.info('PushPlus 推送成功！')

        else:

            logger.error(f'PushPlus 推送失败: {res_json.get("msg", "未知错误")}')

    except Exception as e:

        logger.error(f'PushPlus 推送异常: {e}')

def main():

    # ====================================================================

    # 【修改】从环境变量获取 cookie 和 push_plus_token

    # ====================================================================

    cookie = os.environ.get('BILIBILI_COOKIE')

    push_plus_token = os.environ.get('PUSH_PLUS_TOKEN') # 新增获取token

    

    if not cookie:

        try:

            with open('cookie.txt', 'r', encoding='utf-8') as f:

                cookie = f.read().strip()

        except FileNotFoundError:

            logger.error('未找到cookie.txt文件且环境变量BILIBILI_COOKIE未设置')

            sys.exit(1)

        except Exception as e:

            logger.error(f'读取cookie失败: {e}')

            sys.exit(1)

    

    if not cookie:

        logger.error('cookie为空，程序终止')

        sys.exit(1)

    bili = BilibiliTask(cookie)

    

    # 检查登录状态

    login_status, message = bili.check_login_status()

    if not login_status:

        # 如果登录失败，也尝试发送通知

        error_title = "Bilibili 签到失败"

        error_content = f"登录失败，请检查 Cookie 是否有效！\n\n原因: {message}"

        logger.error(error_content)

        if push_plus_token:

            send_to_pushplus(push_plus_token, error_title, error_content)

        sys.exit(1)

    

    # 执行每日任务

    tasks = {

        '分享视频': bili.share_video(),

        '观看视频': bili.watch_video('BV1GJ411x7h7'),  # B站官方视频，比较稳定

        '直播签到': bili.live_sign(),

        '漫画签到': bili.manga_sign()

    }

    

    # 获取用户信息

    user_info = bili.get_user_info()

    

    # 记录日志到控制台

    log_info(tasks, user_info)

    

    # ====================================================================

    # 【修改】在任务最后增加推送逻辑

    # ====================================================================

    if push_plus_token:

        logger.info('检测到 PUSH_PLUS_TOKEN，准备发送推送...')

        title = "Bilibili 签到通知"

        content = format_push_message(tasks, user_info)

        send_to_pushplus(push_plus_token, title, content)

    else:

        logger.info('未配置 PUSH_PLUS_TOKEN，跳过推送。')

if __name__ == '__main__':

    main()

