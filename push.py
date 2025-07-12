import requests
from datetime import datetime, timedelta, timezone
from loguru import logger

def format_push_message(all_results):
    content = ["### Bilibili 任务报告\n"]
    
    for result in all_results:
        user_info = result.get('user_info')
        if user_info:
            account_name = user_info['uname']
            content.append(f"--- \n#### 账号: {account_name} (Lv.{user_info['level_info']['current_level']})")
        else:
            account_name = f"账号 {result['account_index']}"
            content.append(f"--- \n#### {account_name}")

        for name, (success, message) in result['tasks'].items():
            status_icon = "✅" if success else "❌"
            reason = f" - {message}" if message else ""
            content.append(f"- **{name}**: {status_icon}{reason}")
            
        if user_info:
            content.append(f"- **硬币余额**: {user_info['money']}")
    
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