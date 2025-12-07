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
    coins_to_add = int(config.get('COIN_ADD_NUM'))
    if coins_to_add <= 0:
        return True, "配置为0，跳过"
    
    coin_balance = user_info.get('money', 0)
    if coin_balance < 1:
        return True, f"硬币不足({coin_balance})，跳过"
    
    coins_to_add = min(coins_to_add, int(coin_balance), 5)

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
        
        success, msg = bili.add_coin(bvid, 1, int(config.get('COIN_SELECT_LIKE')))
        if success:
            added_coins += 1
            logger.info(f"为视频 {bvid} 投币成功。")
        elif "已达到" in msg:
            logger.warning("今日投币上限已满，终止投币。")
            added_coins = config.get('COIN_ADD_NUM')
            break
        else:
            logger.warning(f"为视频 {bvid} 投币失败: {msg}")
            if "硬币不足" in msg:
                break

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
    
    video_list = bili.get_dynamic_videos()
    bvid_for_task = video_list[0] if video_list else 'BV1GJ411x7h7'

    if 'share_video' in tasks_to_run:
        tasks_result['分享视频'] = bili.share_video(bvid_for_task)
    if 'live_sign' in tasks_to_run:
        tasks_result['直播签到'] = bili.live_sign()
    if 'manga_sign' in tasks_to_run:
        tasks_result['漫画签到'] = bili.manga_sign()
    if 'add_coin' in tasks_to_run:
        tasks_result['投币任务'] = execute_coin_task(bili, user_info, config)

    tasks_result['观看视频'] = bili.watch_video(bvid_for_task)

    return tasks_result, user_info

def main():
    # ==================== 【核心修改点在这里】 ====================
    # 我们先用 .get() 获取值，如果值是空字符串，就用 or 操作符来选择默认值。
    # 这样既能处理"变量不存在"的情况，也能处理"变量存在但为空"的情况。
    config = {
        "BILIBILI_COOKIE": os.environ.get('BILIBILI_COOKIE'),
        "PUSH_PLUS_TOKEN": os.environ.get('PUSH_PLUS_TOKEN'),
        "TASK_CONFIG": os.environ.get('TASK_CONFIG') or 'live_sign,manga_sign,share_video,add_coin',
        "COIN_ADD_NUM": os.environ.get('COIN_ADD_NUM') or '1',
        "COIN_SELECT_LIKE": os.environ.get('COIN_SELECT_LIKE') or '1',
        "COIN_VIDEO_SOURCE": os.environ.get('COIN_VIDEO_SOURCE') or 'dynamic'
    }
    # ============================================================
    
    if not config["BILIBILI_COOKIE"]:
        logger.error('环境变量 BILIBILI_COOKIE 未设置，程序终止')
        sys.exit(1)

    cookies = [c.strip() for c in config["BILIBILI_COOKIE"].split('###') if c.strip()]
    logger.info(f"检测到 {len(cookies)} 个账号，开始执行任务...")
    
    all_results = []
    for i, cookie in enumerate(cookies, 1):
        masked_account_name = None  # 提前声明
        logger.info(f"=== 账号{i} 任务完成情况 ===")
        bili = BilibiliTask(cookie)
        tasks_result, user_info = run_all_tasks_for_account(bili, config)
        final_user_info = bili.get_user_info() if user_info else None
        all_results.append({'account_index': i, 'tasks': tasks_result, 'user_info': final_user_info})

        # 任务日志输出
        for task_name, (success, msg) in tasks_result.items():
            level = logger.info if success else logger.error
            masked_account_name = mask_string(final_user_info.get('uname')) if final_user_info else f'账号{i}'
            if success:
                level(f"[账号{i}] {task_name}: 成功")
            else:
                level(f"[账号{i}] {task_name}: 失败，原因: {msg}")

        # 用户信息分段输出
        logger.info(f"=== 账号{i} 用户信息 ===")
        if final_user_info:
            logger.info(f"用户名: {mask_string(final_user_info.get('uname'))}")
            logger.info(f"UID: {final_user_info.get('mid')}")
            logger.info(f"等级: {final_user_info.get('level_info', {}).get('current_level')}")
            logger.info(f"经验: {final_user_info.get('level_info', {}).get('current_exp')}")
            logger.info(f"硬币: {final_user_info.get('money')}")
        else:
            logger.error("用户信息获取失败")
        logger.info(f"--- 账号 {masked_account_name} 任务执行完毕 ---")
        logger.info("-" * 40)
    
    if config["PUSH_PLUS_TOKEN"] and all_results:
        logger.info('准备发送推送通知...')
        title = "Bilibili 任务通知"
        content = format_push_message(all_results)
        send_to_pushplus(config["PUSH_PLUS_TOKEN"], title, content)
    else:
        logger.info('未配置 PUSH_PLUS_TOKEN，跳过推送。')

if __name__ == '__main__':
    main()