# IPTV-test
自己测试的用于NAS自用

2026-09-8
1. 目录重命名
原名称	新名称
tests/	Capture/
oklist/	List/
data/	Data/
2. 新增 Backups 备份机制
扫描前自动备份：
导出前自动将 List/ 里的旧文件备份到 Backups/年-月-日_时-分-秒/
备份后清空 List/ 目录
启动时追加询问：
plain
📦 发现上次扫描备份 (2026-09-08_10-21-33):
   • 2026-09-07_sorted.m3u
   • 2026-09-07_sorted.txt

是否将上次备份结果追加到当前扫描中? (y/n):

3. 导出文件名改为日期格式
表格
原文件名	新文件名
xxx_sorted.m3u	2026-09-08.m3u
xxx_sorted.txt	2026-09-08.txt
xxx_sorted.json	2026-09-08.json

📁 新目录结构
plain
m3u_scanner_v3.py   ← 主程序
Capture/            ← GitHub下载的源文件
List/               ← 导出结果
Backups/            ← 历史备份
  └── 2026-09-08_10-21-33/
      ├── 2026-09-07.m3u
      └── 2026-09-07.txt
Data/
  ├── config.json   ← 设置文件
  ├── logos/        ← 台标缓存
  └── epg/          ← EPG缓存
  
  
🚀 使用流程
bash
# 1. 启动程序
python 出程序.py
# 2. 启动后询问是否追加备份（可选）
# 3. 加载源文件（本地 Capture/ 或 GitHub 链接）
# 4. 一键全自动 [10]
# 5. 结果自动导出到 List/2026-09-08.m3u


|  编号 | 名称              | URL                                      |
| :-: | --------------- | ---------------------------------------- |
|  0  | 112114 EPG      | `https://epg.112114.xyz/pp.xml`          |
|  1  | 51zmt EPG       | `http://epg.51zmt.top:8000/e.xml`        |
|  2  | Fanmingming EPG | `https://live.fanmingming.com/e.xml`     |
|  3  | APTV EPG        | `http://epg.aptvapp.com/xml`             |
|  4  | EPG.PW 海外       | `https://epg.pw/xmltv.html?lang=zh-hans` |







