# IPTV-test
自己测试的用于NAS自用

📁 新目录结构

m3u_scanner_v3.py
← 主程序

Capture/
← GitHub下载的源文件

List/ 
← 导出结果
IPTVlist.m3u   ← M3U格式（含EPG链接）
IPTVlist.txt   ← TXT格式
IPTVlist.json  ← JSON格式

Backups/            ← 历史备份
026-09-08_10-21-33/
IPTVlist.m3u
IPTVlist.txt
IPTVlist.json

Data/
  ├── config.json   ← 设置文件
  ├── logos/        ← 台标缓存
  └── epg/          ← EPG缓存

🚀 使用流程
加载 → 去重 → 分类+台标 → HTTP测速 → VLC验证 → 筛选最快 → 删除超时 → 导出
导出前自动执行
删除重复：同名只保留速度最快的1个
删除超时：HTTP/VLC测速失败的频道自动移除
首字母排序：每个分组内按频道名A-Z排序

# 1. 启动程序
python 出程序.py
# 2. 启动后询问是否追加备份（可选）
# 3. 加载源文件（本地 Capture/ 或 GitHub 链接）
# 4. 一键全自动 [10]
# 5. 结果自动导出到 List/IPTVlist.m3u


|  编号 | 名称              | URL                                      |
| :-: | --------------- | ---------------------------------------- |
|  0  | 112114 EPG      | `https://epg.112114.xyz/pp.xml`          |
|  1  | 51zmt EPG       | `http://epg.51zmt.top:8000/e.xml`        |
|  2  | Fanmingming EPG | `https://live.fanmingming.com/e.xml`     |
|  3  | APTV EPG        | `http://epg.aptvapp.com/xml`             |
|  4  | EPG.PW 海外       | `https://epg.pw/xmltv.html?lang=zh-hans` |

2026-09-09
六大分组（按优先级排序）
表格
分组	判定规则
央视	名称以 CCTV 或 CGTN 开头
卫视	名称包含 卫视
港澳台	凤凰、TVB、翡翠、明珠、澳视、东森、中天、台湾、香港、澳门等
国外	BBC、NBC、CNN、HBO、ESPN、NHK、迪士尼、日本、韩国、美国等
地方台	北京、上海、广东、四川、湖南、浙江等省市名称
其他	以上都不匹配的兜底分组



OK



