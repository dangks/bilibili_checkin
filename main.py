import os
import sys
from datetime import datetime, timedelta, timezone
from loguru import logger
from bilibili import BilibiliTask
from push import format_push_message, send_to_pushplus

class BeijingFormatter:
    @staticmethod
    def format(record):
        dt = datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc)
        local_dt = dt + timedelta(hours=8)
        record["extra"]["local_time"] = local_dt.strftime('%H:%M:%S,%f')[:-3]
        return "{time:YYYY-MM-DD HH:mm:ss,SSS}(CST {extra[local_time]}) - {level} - {message}\n"

logger.remove()
logger.add(sys.stdout, format=BeijingFormatter.format, level="INFO", colorize=True)

def mask_string(s: str) -> str:
    if not isinstance(s, str) or len(s) <= 2:
        return s[:1] + '*' if s else '*'
    return f"{s[0]}{'*' * (len(s) - 2)}{s[-1]}"

def execute_coin_task(bili, user_info, config):
    coins_to_add = int(config.get('COIN_ADD_NUM', 1))
    if coins_to_add <= 0:
        return True, "配置为0，跳过"
    
    coin_balance = user_info.get('money', 0)
    if coin_balance < 1:
        return True, f"硬币不足({coin_balance})，跳过"
    
    coins_to_add = min(coins_to_add, int(coin_balance), 5) # 每日最多投5个币获取经验

    if config.get('COIN_VIDEO_SOURCE') == 'ranking':
        video_list = bili.get_ranking_videos()
        logger.info("获取排行榜视频作为投币目标。")
    else:
        video_list = bili.get_dynamic_videos()
        logger.info("获取动态视频作为投币目标。")

    if not video_list:
        return False, "无法获取视频列表"

    added_coins = 0
    for bvid in video_list:
        if added_coins >= coins_to_add:
            break
        
        # 乐观投币，依赖API的返回结果判断是否重复
        success, msg = bili.add_coin(bvid, 1, int(config.get('COIN_SELECT_LIKE', 1)))
        if success:
            added_coins += 1
            logger.info(f"为视频 {bvid} 投币成功。")
        elif "已达到" in msg:
            logger.warning("今日投币上限已满，终止投币。")
            # 如果API明确返回“已满”，我们可以提前终止循环
            added_coins = config.get('COIN_ADD_NUM', 1) # 标记为任务完成
            break
        else:
            logger.warning(f"为视频 {bvid} 投币失败: {msg}")

    return True, f"尝试投币，最终成功 {added_coins} 枚"

def run_all_tasks_for_account(bili, config):
    tasks_to_run = [task.strip() for task in config.get('TASK_CONFIG', '').split(',') if task.strip()]
    if not tasks_to_run:
        tasks_to_run = ['live_sign', 'manga_sign', 'share_video', 'add_coin']

    user_info = bili.get_user_info()
    if not user_info:
        return {'登录检查': (False, 'Cookie失效或网络问题')}, None
        
    masked_uname = mask_string(user_info.get('uname'))
    logger.info(f"账号名称: {masked_uname}")
    tasks_result = {}
    
    # 由于无法预先检查任务状态，我们总是尝试获取视频列表
    video_list = bili.get_dynamic_videos()
    bvid_for_task = video_list[0] if video_list else 'BV1GJ411x7h7' # 提供一个备用BVID

    # 直接执行任务，不再预先检查
    if 'share_video' in tasks_to_run:
        tasks_result['分享视频'] = bili.share_video(bvid_for_task)
    if 'live_sign' in tasks_to_run:
        tasks_result['直播签到'] = bili.live_sign()
    if 'manga_sign' in tasks_to_run:
        tasks_result['漫画签到'] = bili.manga_sign()
    if 'add_coin' in tasks_to_run:
        # 投币任务现在不依赖 reward_info
        tasks_result['投币任务'] = execute_coin_task(bili, user_info, config)

    # 观看视频任务仍然执行，B站API会处理重复观看的情况
    tasks_result['观看视频'] = bili.watch_video(bvid_for_task)

    return tasks_result, user_info

def main():
    config = {
        "BILIBILI_COOKIE": os.environ.get('BILIBILI_COOKIE'),
        "PUSH_PLUS_TOKEN": os.environ.get('PUSH_PLUS_TOKEN'),
        "TASK_CONFIG": os.environ.get('TASK_CONFIG', 'live_sign,manga_sign,share_video,add_coin'),
        "COIN_ADD_NUM": os.environ.get('COIN_ADD_NUM', '1'),
        "COIN_SELECT_LIKE": os.environ.get('COIN_SELECT_LIKE', '1'),
        "COIN_VIDEO_SOURCE": os.environ.get('COIN_VIDEO_SOURCE', 'dynamic')
    }
    
    if not config["BILIBILI_COOKIE"]:
        logger.error('环境变量 BILIBILI_COOKIE 未设置，程序终止')
        sys.exit(1)

    cookies = [c.strip() for c in config["BILIBILI_COOKIE"].split('###') if c.strip()]
    logger.info(f"检测到 {len(cookies)} 个账号，开始执行任务...")
    
    all_results = []
    for i, cookie in enumerate(cookies, 1):
        logger.info(f"--- 开始为账号 {i} 执行任务 ---")
        
        bili = BilibiliTask(cookie)
        tasks_result, user_info = run_all_tasks_for_account(bili, config)
        
        final_user_info = bili.get_user_info() if user_info else None
        all_results.append({'account_index': i, 'tasks': tasks_result, 'user_info': final_user_info})
        
        masked_account_name = mask_string(final_user_info.get('uname')) if final_user_info else f'账号{i}'
        logger.info(f"--- 账号 {masked_account_name} 任务执行完毕 ---")
    
    if config["PUSH_PLUS_TOKEN"] and all_results:
        logger.info('准备发送推送通知...')
        title = "Bilibili 任务通知"
        content = format_push_message(all_results)
        send_to_pushplus(config["PUSH_PLUS_TOKEN"], title, content)
    else:
        logger.info('未配置 PUSH_PLUS_TOKEN，跳过推送。')

if __name__ == '__main__':
    main()