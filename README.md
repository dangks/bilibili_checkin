# bilibili_checkin
<div align="center">

[![Bilibili Daily Checkin](https://github.com/Dangks/bilibili_checkin/actions/workflows/Bilibili_DailyCheckin.yml/badge.svg)](https://github.com/Dangks/bilibili_checkin/actions/workflows/Bilibili_DailyCheckin.yml)

</div>

## 项目简介
这是一个自动化打卡脚本，旨在帮助用户完成B站的每日签到任务，包括分享视频、观看视频、~~直播签到~~和漫画签到。通过使用GitHub Actions，可以实现每日自动运行脚本，完成签到任务并获取相应的奖励。  

## 包含功能:
1. 每天自动执行签到任务：包含每日分享、观看视频、~~直播签到~~(活动已下线,功能暂时保留)、漫画签到等任务  
2. 敏感信息安全传递：支持通过环境变量读取cookie  
3. 结合GitHub Actions实现自动化运行，可通过Actions日志查看执行结果   
4. 支持手动触发(每日奖励只能领取一次，故触发多次即使执行成功结果也不会变化)
5. **支持通过 PushPlus 推送任务运行结果，方便及时获取通知。**

## 签到奖励：
完成自动签到可获取到`硬币+1、经验值+15`  ，漫画签到目前似乎并没有实际的用处，也没有签到奖励。
![image](https://github.com/user-attachments/assets/32db5f6a-e023-4335-b458-c91b6504574c)
![image](https://github.com/user-attachments/assets/6136def4-ad03-4ab9-a959-c55737fb0c68)
![image](https://github.com/user-attachments/assets/23d8a98b-4143-4fb0-8ae9-47f42bf3a82d)

## 使用方法:  
1. Fork本项目到你的GitHub仓库中。
2. 在你的仓库 `Settings -> Secrets and variables -> Actions` 中，添加以下 `Repository secrets`：

   | 名称 | 是否必需 | 说明 |
   | --- | --- | --- |
   | `BILIBILI_COOKIE` | **是** | 你的B站Cookie。获取方式请参考下文。 |
   | `PUSH_PLUS_TOKEN` | **否** | 用于 [PushPlus](http://www.pushplus.plus/) 推送的 Token。配置后，任务执行结果会推送到你的微信。 |

  ![image](https://github.com/user-attachments/assets/49f54e56-67d5-4749-b8f6-4cd5105a1684)
3. 启用GitHub Actions，Fork的仓库默认是关闭workflow的，需要手动开启。   

## 执行结果查看  
可以在workflows里查看执行日志的输出结果。**如果你配置了推送，也会在手机上收到任务报告。**
![image](https://github.com/user-attachments/assets/8fd0839b-5a62-46d0-9ad5-b10dd3f99b32)


## Cookie获取：  
打开浏览器网页登录B站，然后进入开发人员工具(F12)，查看网络响应标头就能找到Cookie。
![image](https://github.com/user-attachments/assets/269747ab-a1ed-473b-964d-8a25a3bf7382)



## 注意事项:  
1. Cookie要包含`bili_jct`, `SESSDATA`, `DedeUserID`字段。
2. 建议先手动运行测试。
3. 可以根据需要修改cron表达式调整执行时间。
4. 请确保Cookie有效，修改密码或退出登录会导致Cookie失效。  
5. 请勿在任何位置明文泄露你的Cookie以防账号被盗。  
6. 本项目仅供学习交流使用，请勿滥用。


## 常规问题解答：  
1. 关于分享视频：  
- 这个分享操作是调用B站的分享接口，实际上只是模拟了一次分享行为。
- 不会真实分享到任何地方，只是为了完成每日任务获取经验值。
- B站会记录这个分享行为，但不会在任何地方显示出来。

2. 关于观看视频：  
- 程序里指定的视频BV号是随意挑选的(我认为这个视频很不错，联系侵删！)，不指定特定BV号也是可以的。
- 当前代码指定BV号主要是为了保证稳定性，因为随机视频可能会遇到:  
  - 视频已下架  
  - 视频需要会员才能观看   
  - 视频有年龄限制等情况  
- 如果想改成随机视频，可以像share_video()方法一样；指定固定视频是一种保守稳妥的做法，但不是必须的。如果你想改成随机视频完全可以。  


## 贡献指南
欢迎提交Issue和Pull Request来改进本项目。

分支说明：
- [main](https://github.com/Dangks/bilibili_checkin/tree/main)：主线分支，包含最新稳定版本代码  
- [dev](https://github.com/Dangks/bilibili_checkin/tree/dev)：开发分支，包含开发中的问题修改和新功能测试  
**请注意，直接向 `main` 分支发起的 PR 将不会被接受。


## 许可证
本项目采用[MIT](./LICENSE)许可证。  


## Todo:
- [ ] 网页获取的cookie时效问题，~~最短只有三天，后续考虑解决长期登录验证，~~ 只要不在网页再次登录就是长期有效
