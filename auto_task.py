import requests
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from loguru import logger

class BeijingFormatter:
    @staticmethod
    def format(record):
        dt = datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc)
        local_dt = dt + timedelta(hours=8)
        record["extra"]["local_time"] = local_dt.strftime('%H:%M:%S,%f')[:-3]
        return "{time:YYYY-MM-DD HH:mm:ss,SSS}(CST {extra[local_time]}) - {level} - {message}\n"

logger.remove()
logger.add(sys.stdout, format=BeijingFormatter.format, level="INFO", colorize=True)

class BilibiliTask:
    def __init__(self, cookie):
        self.cookie = cookie
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Cookie': cookie
        }
        
    def get_csrf(self):
        for item in self.cookie.split(';'):
            if item.strip().startswith('bili_jct'):
                return item.split('=')[1]
        return None

    def check_login_status(self):
        try:
            res = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=self.headers)
            if res.json()['code'] == -101:
                return False, '账号未登录或Cookie失效'
            return True, None
        except Exception as e:
            return False, str(e)
        
    def share_video(self):
        try:
            res = requests.get('https://api.bilibili.com/x/web-interface/dynamic/region?ps=1&rid=1', headers=self.headers)
            bvid = res.json()['data']['archives'][0]['bvid']
            data = {'bvid': bvid, 'csrf': self.get_csrf()}
            res = requests.post('https://api.bilibili.com/x/web-interface/share/add', headers=self.headers, data=data)
            if res.json()['code'] == 0:
                return True, None
            return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def watch_video(self, bvid):
        try:
            data = {'bvid': bvid, 'csrf': self.get_csrf(), 'played_time': '2'}
            res = requests.post('https://api.bilibili.com/x/click-interface/web/heartbeat', 
                              headers=self.headers, data=data)
            if res.json()['code'] == 0:
                return True, None
            return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def live_sign(self):
        try:
            res = requests.get('https://api.live.bilibili.com/xlive/web-ucenter/v1/sign/DoSign', headers=self.headers)
            if res.json()['code'] == 0:
                return True, None
            return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def manga_sign(self):
        try:
            res = requests.post('https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn', headers=self.headers, data={'platform': 'ios'})
            if res.json()['code'] == 0:
                return True, None
            return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def get_user_info(self):
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

def log_all_results(all_results):
    for result in all_results:
        account_name = result.get('user_info', {}).get('uname', f"账号 {result['account_index']}")
        logger.info('=' * 20 + f' {account_name} 任务报告 ' + '=' * 20)
        
        for name, (success, message) in result['tasks'].items():
            if success:
                logger.info(f'任务【{name}】: ✅成功')
            else:
                logger.error(f'任务【{name}】: ❌失败，原因: {message}')
            
        if result.get('user_info'):
            user_info = result['user_info']
            logger.info(f'用户等级: {user_info["level"]}, 当前经验: {user_info["exp"]}, 拥有硬币: {user_info["coin"]}')
        else:
            logger.error(f"未能获取到 {account_name} 的用户信息。")
        logger.info('=' * (58 + len(account_name) - 5))

def format_push_message_for_all(all_results):
    content = ["### Bilibili 多账号签到任务报告\n"]
    
    for result in all_results:
        user_info = result.get('user_info')
        if user_info:
            account_name = user_info['uname']
            content.append(f"--- \n#### 账号: {account_name} (Lv.{user_info['level']})")
        else:
            account_name = f"账号 {result['account_index']}"
            content.append(f"--- \n#### {account_name}")

        for name, (success, message) in result['tasks'].items():
            status_icon = "✅" if success else "❌"
            reason = f" - 原因: {message}" if not success and message else ""
            content.append(f"- **{name}**: {status_icon}{reason}")
            
        if user_info:
            content.append(f"- **硬币余额**: {user_info['coin']}")
    
    beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    content.append(f"\n> 报告时间: {beijing_time}")
    
    return "\n".join(content)

def send_to_pushplus(token, title, content):
    url = "http://www.pushplus.plus/send"
    data = {"token": token, "title": title, "content": content, "template": "markdown"}
    try:
        res = requests.post(url, json=data)
        if res.json().get('code') == 200:
            logger.info('PushPlus 推送成功！')
        else:
            logger.error(f'PushPlus 推送失败: {res.json().get("msg", "未知错误")}')
    except Exception as e:
        logger.error(f'PushPlus 推送异常: {e}')

def main():
    cookie_string = os.environ.get('BILIBILI_COOKIE')
    push_plus_token = os.environ.get('PUSH_PLUS_TOKEN')
    
    if not cookie_string:
        logger.error('环境变量 BILIBILI_COOKIE 未设置，程序终止')
        sys.exit(1)

    cookies = [c.strip() for c in cookie_string.split('###') if c.strip()]
    if not cookies:
        logger.error('BILIBILI_COOKIE 内容为空，程序终止')
        sys.exit(1)

    logger.info(f"检测到 {len(cookies)} 个账号，开始执行任务...")
    
    all_results = []

    for i, cookie in enumerate(cookies, 1):
        account_index = i
        logger.info(f"--- 开始为账号 {account_index} 执行任务 ---")
        
        bili = BilibiliTask(cookie)
        
        login_status, message = bili.check_login_status()
        if not login_status:
            logger.error(f'账号 {account_index} 登录失败，原因: {message}，跳过该账号。')
            tasks_result = {
                '分享视频': (False, '登录失败'), '观看视频': (False, '登录失败'),
                '直播签到': (False, '登录失败'), '漫画签到': (False, '登录失败')
            }
            all_results.append({'account_index': account_index, 'tasks': tasks_result, 'user_info': None})
            continue

        tasks_result = {
            '分享视频': bili.share_video(),
            '观看视频': bili.watch_video('BV1GJ411x7h7'),
            '直播签到': bili.live_sign(),
            '漫画签到': bili.manga_sign()
        }
        
        user_info = bili.get_user_info()
        
        all_results.append({'account_index': account_index, 'tasks': tasks_result, 'user_info': user_info})
        logger.info(f"--- 账号 {account_index} 任务执行完毕 ---")
    
    logger.info("\n所有账号任务已执行完毕，生成总结报告...")
    log_all_results(all_results)
    
    if push_plus_token:
        logger.info('检测到 PUSH_PLUS_TOKEN，准备发送推送...')
        title = "Bilibili 多账号签到通知"
        content = format_push_message_for_all(all_results)
        send_to_pushplus(push_plus_token, title, content)
    else:
        logger.info('未配置 PUSH_PLUS_TOKEN，跳过推送。')

if __name__ == '__main__':
    main()
