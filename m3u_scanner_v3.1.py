#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║           M3U源扫描整理工具 v3.0 - 终端版                     ║
║     多源加载 | HTTP/VLC测速 | 台标EPG | 分类导出              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import time
import json
import asyncio
import aiohttp
import subprocess
import threading
import platform
import shutil
import urllib.request
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============ 路径常量 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURE_DIR = os.path.join(BASE_DIR, "Capture")
LIST_DIR = os.path.join(BASE_DIR, "List")
DATA_DIR = os.path.join(BASE_DIR, "Data")
BACKUPS_DIR = os.path.join(BASE_DIR, "Backups")
LOGOS_DIR = os.path.join(DATA_DIR, "logos")
EPG_DIR = os.path.join(DATA_DIR, "epg")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(LIST_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)
os.makedirs(LOGOS_DIR, exist_ok=True)
os.makedirs(EPG_DIR, exist_ok=True)

# ============ 终端工具 ============
class Term:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"

    @classmethod
    def clear(cls):
        os.system('cls' if platform.system() == 'Windows' else 'clear')

    @classmethod
    def color(cls, text, fg="", bg="", bold=False):
        result = ""
        if bold: result += cls.BOLD
        result += fg + bg + text + cls.RESET
        return result

    @classmethod
    def progress_bar(cls, current, total, width=40):
        if total == 0:
            return "[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%"
        percent = current / total
        filled = int(width * percent)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {percent*100:.1f}% ({current}/{total})"

    @classmethod
    def log(cls, level, msg):
        colors = {"INFO": cls.GREEN, "WARN": cls.YELLOW, "ERROR": cls.RED,
                  "DEBUG": cls.DIM, "SUCCESS": cls.GREEN, "TEST": cls.CYAN,
                  "VLC": cls.MAGENTA, "DOWNLOAD": cls.BLUE, "EPG": cls.YELLOW}
        color = colors.get(level, cls.WHITE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{cls.color('['+timestamp+']', cls.DIM)} {cls.color('['+level+']', color, bold=True)} {msg}")

# ============ 台标数据库 ============
class LogoDB:
    LOGO_URLS = {
        "CCTV-1": "https://live.fanmingming.com/tv/CCTV1.png",
        "CCTV-2": "https://live.fanmingming.com/tv/CCTV2.png",
        "CCTV-3": "https://live.fanmingming.com/tv/CCTV3.png",
        "CCTV-4": "https://live.fanmingming.com/tv/CCTV4.png",
        "CCTV-5": "https://live.fanmingming.com/tv/CCTV5.png",
        "CCTV-5+": "https://live.fanmingming.com/tv/CCTV5+.png",
        "CCTV-6": "https://live.fanmingming.com/tv/CCTV6.png",
        "CCTV-7": "https://live.fanmingming.com/tv/CCTV7.png",
        "CCTV-8": "https://live.fanmingming.com/tv/CCTV8.png",
        "CCTV-9": "https://live.fanmingming.com/tv/CCTV9.png",
        "CCTV-10": "https://live.fanmingming.com/tv/CCTV10.png",
        "CCTV-11": "https://live.fanmingming.com/tv/CCTV11.png",
        "CCTV-12": "https://live.fanmingming.com/tv/CCTV12.png",
        "CCTV-13": "https://live.fanmingming.com/tv/CCTV13.png",
        "CCTV-14": "https://live.fanmingming.com/tv/CCTV14.png",
        "CCTV-15": "https://live.fanmingming.com/tv/CCTV15.png",
        "CCTV-16": "https://live.fanmingming.com/tv/CCTV16.png",
        "CCTV-17": "https://live.fanmingming.com/tv/CCTV17.png",
        "CCTV-4K": "https://live.fanmingming.com/tv/CCTV4K.png",
        "CCTV-8K": "https://live.fanmingming.com/tv/CCTV8K.png",
        "北京卫视": "https://live.fanmingming.com/tv/北京卫视.png",
        "东方卫视": "https://live.fanmingming.com/tv/东方卫视.png",
        "湖南卫视": "https://live.fanmingming.com/tv/湖南卫视.png",
        "浙江卫视": "https://live.fanmingming.com/tv/浙江卫视.png",
        "江苏卫视": "https://live.fanmingming.com/tv/江苏卫视.png",
        "广东卫视": "https://live.fanmingming.com/tv/广东卫视.png",
        "深圳卫视": "https://live.fanmingming.com/tv/深圳卫视.png",
        "安徽卫视": "https://live.fanmingming.com/tv/安徽卫视.png",
        "山东卫视": "https://live.fanmingming.com/tv/山东卫视.png",
        "天津卫视": "https://live.fanmingming.com/tv/天津卫视.png",
        "重庆卫视": "https://live.fanmingming.com/tv/重庆卫视.png",
        "四川卫视": "https://live.fanmingming.com/tv/四川卫视.png",
        "湖北卫视": "https://live.fanmingming.com/tv/湖北卫视.png",
        "河南卫视": "https://live.fanmingming.com/tv/河南卫视.png",
        "河北卫视": "https://live.fanmingming.com/tv/河北卫视.png",
        "江西卫视": "https://live.fanmingming.com/tv/江西卫视.png",
        "广西卫视": "https://live.fanmingming.com/tv/广西卫视.png",
        "云南卫视": "https://live.fanmingming.com/tv/云南卫视.png",
        "贵州卫视": "https://live.fanmingming.com/tv/贵州卫视.png",
        "海南卫视": "https://live.fanmingming.com/tv/海南卫视.png",
        "辽宁卫视": "https://live.fanmingming.com/tv/辽宁卫视.png",
        "吉林卫视": "https://live.fanmingming.com/tv/吉林卫视.png",
        "黑龙江卫视": "https://live.fanmingming.com/tv/黑龙江卫视.png",
        "陕西卫视": "https://live.fanmingming.com/tv/陕西卫视.png",
        "甘肃卫视": "https://live.fanmingming.com/tv/甘肃卫视.png",
        "青海卫视": "https://live.fanmingming.com/tv/青海卫视.png",
        "宁夏卫视": "https://live.fanmingming.com/tv/宁夏卫视.png",
        "新疆卫视": "https://live.fanmingming.com/tv/新疆卫视.png",
        "西藏卫视": "https://live.fanmingming.com/tv/西藏卫视.png",
        "内蒙古卫视": "https://live.fanmingming.com/tv/内蒙古卫视.png",
        "东南卫视": "https://live.fanmingming.com/tv/东南卫视.png",
        "厦门卫视": "https://live.fanmingming.com/tv/厦门卫视.png",
        "凤凰卫视": "https://live.fanmingming.com/tv/凤凰卫视中文台.png",
        "凤凰中文": "https://live.fanmingming.com/tv/凤凰卫视中文台.png",
        "凤凰资讯": "https://live.fanmingming.com/tv/凤凰卫视资讯台.png",
        "凤凰香港": "https://live.fanmingming.com/tv/凤凰卫视香港台.png",
        "翡翠台": "https://live.fanmingming.com/tv/翡翠台.png",
        "明珠台": "https://live.fanmingming.com/tv/明珠台.png",
        "澳视澳门": "https://live.fanmingming.com/tv/澳视澳门.png",
        "澳亚卫视": "https://live.fanmingming.com/tv/澳亚卫视.png",
        "东森新闻": "https://live.fanmingming.com/tv/东森新闻.png",
        "中天新闻": "https://live.fanmingming.com/tv/中天新闻.png",
        "民视": "https://live.fanmingming.com/tv/民视.png",
        "三立": "https://live.fanmingming.com/tv/三立.png",
        "CGTN": "https://live.fanmingming.com/tv/CGTN.png",
        "CGTN-英语": "https://live.fanmingming.com/tv/CGTN.png",
        "CGTN-纪录": "https://live.fanmingming.com/tv/CGTN纪录.png",
        "中国教育": "https://live.fanmingming.com/tv/CETV1.png",
    }

    @classmethod
    def get_logo(cls, channel_name):
        if channel_name in cls.LOGO_URLS:
            return cls.LOGO_URLS[channel_name]
        name_lower = channel_name.lower().replace(" ", "").replace("-", "").replace("_", "")
        for key, url in cls.LOGO_URLS.items():
            key_lower = key.lower().replace(" ", "").replace("-", "").replace("_", "")
            if key_lower in name_lower or name_lower in key_lower:
                return url
        cctv_match = re.search(r'cctv[\s-]*(\d+)[\s\+]*', name_lower)
        if cctv_match:
            num = cctv_match.group(1)
            plus = "+" if "+" in channel_name else ""
            key = f"CCTV-{num}{plus}"
            if key in cls.LOGO_URLS:
                return cls.LOGO_URLS[key]
        return ""

    @classmethod
    def apply_logos(cls, channels):
        matched = 0
        for ch in channels:
            if not ch.logo:
                logo = cls.get_logo(ch.name)
                if logo:
                    ch.logo = logo
                    matched += 1
        Term.log("INFO", f"台标匹配: {matched}/{len(channels)} 个频道")
        return channels


# ============ EPG管理器 ============
class EPGManager:
    EPG_SOURCES = [
        {"name": "112114 EPG", "url": "https://epg.112114.xyz/pp.xml", "type": "xml"},
        {"name": "51zmt EPG", "url": "http://epg.51zmt.top:8000/e.xml", "type": "xml"},
        {"name": "Fanmingming EPG", "url": "https://live.fanmingming.com/e.xml", "type": "xml"},
        {"name": "APTV EPG", "url": "http://epg.aptvapp.com/xml", "type": "xml"},
        {"name": "EPG.PW 海外", "url": "https://epg.pw/xmltv.html?lang=zh-hans", "type": "xml"},
    ]

    @classmethod
    def download_epg(cls, source_idx=None, all_sources=False):
        if all_sources:
            Term.log("INFO", "开始下载所有EPG源...")
            combined = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv>']
            for i, src in enumerate(cls.EPG_SOURCES):
                try:
                    Term.log("DOWNLOAD", f"[{i+1}/{len(cls.EPG_SOURCES)}] {src['name']}: {src['url']}")
                    req = urllib.request.Request(src['url'], headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        content = resp.read().decode('utf-8', errors='ignore')
                        channels = re.findall(r'<channel.*?</channel>', content, re.DOTALL)
                        programmes = re.findall(r'<programme.*?</programme>', content, re.DOTALL)
                        combined.extend(channels)
                        combined.extend(programmes)
                        Term.log("SUCCESS", f"  OK 获取 {len(channels)} 频道, {len(programmes)} 节目")
                except Exception as e:
                    Term.log("ERROR", f"  FAIL {e}")
            combined.append('</tv>')
            output_path = os.path.join(EPG_DIR, "epg_combined.xml")
            with open(output_path, 'w', encoding='utf-8') as f2:
                f2.write('\n'.join(combined))
            Term.log("SUCCESS", f"EPG合并完成: {output_path}")
            return output_path
        else:
            src = cls.EPG_SOURCES[source_idx] if source_idx is not None else cls.EPG_SOURCES[0]
            Term.log("DOWNLOAD", f"下载EPG: {src['name']} - {src['url']}")
            try:
                req = urllib.request.Request(src['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    content = resp.read()
                output_path = os.path.join(EPG_DIR, f"epg_{src['name'].replace(' ', '_').lower()}.xml")
                with open(output_path, 'wb') as f2:
                    f2.write(content)
                Term.log("SUCCESS", f"EPG下载完成: {output_path} ({len(content)} bytes)")
                return output_path
            except Exception as e:
                Term.log("ERROR", f"EPG下载失败: {e}")
                return ""

    @classmethod
    def get_epg_url(cls, source_idx=None):
        if source_idx is not None and 0 <= source_idx < len(cls.EPG_SOURCES):
            return cls.EPG_SOURCES[source_idx]["url"]
        return cls.EPG_SOURCES[0]["url"]

    @classmethod
    def list_sources(cls):
        print()
        print(Term.color("  可用EPG源:", Term.CYAN, bold=True))
        for i, src in enumerate(cls.EPG_SOURCES):
            print(f"    [{i}] {src['name']:<20} {src['url']}")
        print()

# ============ GitHub下载器 ============
class GitHubDownloader:
    @staticmethod
    def is_github_url(url):
        return 'github.com' in url or 'raw.githubusercontent.com' in url

    @staticmethod
    def convert_to_raw(url):
        if 'raw.githubusercontent.com' in url:
            return url
        match = re.match(r'https?://github\.com/([^/]+)/([^/]+)/blob/(.+)', url)
        if match:
            user, repo, path = match.groups()
            return f"https://raw.githubusercontent.com/{user}/{repo}/{path}"
        match2 = re.match(r'https?://github\.com/([^/]+)/([^/]+)/raw/(.+)', url)
        if match2:
            user, repo, path = match2.groups()
            return f"https://raw.githubusercontent.com/{user}/{repo}/{path}"
        return url

    @classmethod
    def download(cls, url, timeout=30):
        raw_url = cls.convert_to_raw(url)
        Term.log("DOWNLOAD", f"下载: {raw_url[:80]}...")
        try:
            req = urllib.request.Request(raw_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/plain,text/html,application/octet-stream,*/*'
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read()
            filename = os.path.basename(raw_url.split('?')[0]) or f"github_{int(time.time())}.m3u"
            if not filename.endswith(('.m3u', '.m3u8', '.txt')):
                filename += '.m3u'
            filepath = os.path.join(CAPTURE_DIR, filename)
            with open(filepath, 'wb') as f2:
                f2.write(content)
            Term.log("SUCCESS", f"下载完成: {filename} ({len(content)} bytes)")
            return filepath
        except Exception as e:
            Term.log("ERROR", f"下载失败: {e}")
            return None

    @classmethod
    def download_multiple(cls, urls):
        downloaded = []
        for i, url in enumerate(urls):
            Term.log("INFO", f"[{i+1}/{len(urls)}] 处理链接...")
            path = cls.download(url.strip())
            if path:
                downloaded.append(path)
            time.sleep(0.5)
        return downloaded

# ============ 配置管理 ============
class Config:
    DEFAULTS = {
        "timeout": 10,
        "max_concurrent": 30,
        "test_duration": 3,
        "vlc_timeout": 15,
        "vlc_path": "vlc",
        "auto_classify": True,
        "keep_unavailable": False,
        "export_formats": ["m3u"],
        "apply_logo": True,
        "epg_source": 0,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f2:
                    loaded = json.load(f2)
                    self.data.update(loaded)
            except:
                pass

    def save(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f2:
                json.dump(self.data, f2, ensure_ascii=False, indent=2)
        except:
            pass

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


# ============ 数据模型 ============
@dataclass
class Channel:
    name: str
    url: str
    group: str = "未分类"
    logo: str = ""
    epg: str = ""
    tvg_id: str = ""
    tvg_name: str = ""
    extra_attrs: Dict[str, str] = field(default_factory=dict)
    source_file: str = ""
    http_response_time: float = 99999.0
    http_status_code: int = 0
    http_available: bool = False
    http_content_type: str = ""
    vlc_response_time: float = 99999.0
    vlc_available: bool = False
    vlc_error: str = ""
    is_available: bool = False
    best_response_time: float = 99999.0
    test_time: str = ""
    test_method: str = ""

    def __hash__(self):
        return hash((self.name.lower().strip(), self.url.strip()))

    def __eq__(self, other):
        if not isinstance(other, Channel):
            return False
        return (self.name.lower().strip() == other.name.lower().strip() and 
                self.url.strip() == other.url.strip())

# ============ 文件解析器 ============
class M3UParser:
    @staticmethod
    def parse_file(filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ('.m3u', '.m3u8'):
            return M3UParser._parse_m3u(filepath)
        else:
            return M3UParser._parse_txt(filepath)

    @staticmethod
    def _parse_m3u(filepath):
        channels = []
        current = None
        source_name = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f2:
                lines = f2.readlines()
        except Exception as e:
            Term.log("ERROR", f"读取失败: {e}")
            return channels
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            if line.startswith('#EXTINF:'):
                current = Channel(name="", url="", source_file=source_name)
                attrs = dict(re.findall(r'(\w+)="([^"]*)"', line))
                current.tvg_id = attrs.get('tvg-id', '')
                current.tvg_name = attrs.get('tvg-name', '')
                current.logo = attrs.get('tvg-logo', '')
                current.group = attrs.get('group-title', '未分类')
                current.epg = attrs.get('x-tvg-url', '')
                current.extra_attrs = attrs
                name_match = re.search(r',([^,]*)$', line)
                current.name = name_match.group(1).strip() if name_match else (current.tvg_name or f"频道_{i}")
            elif line.startswith('#EXTGRP:') and current:
                current.group = line.replace('#EXTGRP:', '').strip()
            elif not line.startswith('#') and current:
                current.url = line
                current.name = current.name or f"频道_{i}"
                channels.append(current)
                current = None
            elif not line.startswith('#') and not current and line.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
                channels.append(Channel(name=f"频道_{i}", url=line, group="未分类", source_file=source_name))
        return channels

    @staticmethod
    def _parse_txt(filepath):
        channels = []
        source_name = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f2:
                lines = f2.readlines()
        except Exception as e:
            Term.log("ERROR", f"读取失败: {e}")
            return channels
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ',' in line:
                comma_idx = line.rfind(',')
                name = line[:comma_idx].strip()
                url_part = line[comma_idx+1:].strip()
                group = "未分类"
                for sep in ['#', '$', '|']:
                    if sep in url_part:
                        parts = url_part.split(sep, 1)
                        url_part = parts[0].strip()
                        group = parts[1].strip()
                        break
                if url_part.startswith(('http://', 'https://', 'rtmp://', 'rtsp://')):
                    channels.append(Channel(name=name or f"频道_{i}", url=url_part, group=group, source_file=source_name))
            elif line.startswith(('http://', 'https://')):
                channels.append(Channel(name=f"频道_{i}", url=line, group="未分类", source_file=source_name))
        return channels

# ============ HTTP测速器 ============
class HTTPTester:
    def __init__(self, config):
        self.timeout = config.get('timeout', 10)
        self.max_concurrent = config.get('max_concurrent', 30)
        self.test_duration = config.get('test_duration', 3)
        self.headers = {'User-Agent': config.get('user_agent')}
        self.semaphore = None
        self.tested = 0
        self.total = 0
        self.lock = threading.Lock()

    def _progress(self):
        with self.lock:
            self.tested += 1
            if self.total > 0:
                sys.stdout.write(f"\r  {Term.progress_bar(self.tested, self.total)}")
                sys.stdout.flush()

    async def _test_one(self, session, ch):
        start = time.time()
        ch.test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ch.test_method = 'http'
        try:
            async with self.semaphore:
                try:
                    async with session.head(ch.url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as resp:
                        ch.http_status_code = resp.status
                except:
                    pass
                bytes_read = 0
                async with session.get(ch.url, timeout=aiohttp.ClientTimeout(total=self.timeout), allow_redirects=True) as resp:
                    ch.http_status_code = resp.status
                    ch.http_content_type = resp.headers.get('Content-Type', '')
                    test_start = time.time()
                    async for chunk in resp.content.iter_chunked(8192):
                        bytes_read += len(chunk)
                        if time.time() - test_start >= self.test_duration or bytes_read >= 2*1024*1024:
                            break
                    if resp.status == 200:
                        ch.http_response_time = round(time.time() - start, 3)
                        ch.http_available = True
        except asyncio.TimeoutError:
            ch.http_available = False
        except Exception:
            ch.http_available = False
        ch.is_available = ch.http_available
        ch.best_response_time = ch.http_response_time
        self._progress()
        return ch

    async def test_all(self, channels):
        self.total = len(channels)
        self.tested = 0
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        connector = aiohttp.TCPConnector(limit=self.max_concurrent*2, limit_per_host=5, force_close=True)
        async with aiohttp.ClientSession(connector=connector, headers=self.headers) as session:
            tasks = [self._test_one(session, c) for c in channels]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [r for r in results if not isinstance(r, Exception)]
        print()
        return valid

# ============ VLC测速器 ============
class VLCTester:
    def __init__(self, config):
        self.timeout = config.get('vlc_timeout', 15)
        self.vlc_path = config.get('vlc_path', 'vlc')
        self.max_workers = min(4, os.cpu_count() or 2)
        self.tested = 0
        self.total = 0
        self.lock = threading.Lock()

    def _check_vlc(self):
        try:
            result = subprocess.run([self.vlc_path, '--version'], capture_output=True, timeout=5)
            return result.returncode == 0 or b'VLC' in result.stdout or b'VLC' in result.stderr
        except:
            return False

    def _progress(self):
        with self.lock:
            self.tested += 1
            if self.total > 0:
                sys.stdout.write(f"\r  {Term.progress_bar(self.tested, self.total)}")
                sys.stdout.flush()

    def _test_single(self, ch):
        start = time.time()
        ch.test_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ch.test_method = 'vlc'
        cmd = [
            self.vlc_path, ch.url,
            '--intf=dummy', '--vout=dummy', '--aout=dummy',
            '--no-video-title-show', '--play-and-exit',
            f'--run-time={min(5, self.timeout - 2)}', '--quiet'
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=self.timeout,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elapsed = time.time() - start
            if elapsed >= 2.0:
                ch.vlc_available = True
                ch.vlc_response_time = round(elapsed, 3)
                ch.is_available = True
                ch.best_response_time = ch.vlc_response_time
            else:
                ch.vlc_available = False
                ch.vlc_error = "播放时间过短"
                ch.is_available = False
        except subprocess.TimeoutExpired:
            ch.vlc_available = False
            ch.vlc_error = "VLC超时"
            ch.is_available = False
        except FileNotFoundError:
            ch.vlc_available = False
            ch.vlc_error = "找不到VLC"
            ch.is_available = False
        except Exception as e:
            ch.vlc_available = False
            ch.vlc_error = str(e)[:50]
            ch.is_available = False
        self._progress()
        return ch

    def test_all(self, channels):
        if not self._check_vlc():
            Term.log("ERROR", f"VLC未安装: {self.vlc_path}")
            return channels
        self.total = len(channels)
        self.tested = 0
        Term.log("INFO", f"VLC测试: {len(channels)} 个源, 并发={self.max_workers}")
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._test_single, ch): ch for ch in channels}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    Term.log("ERROR", f"异常: {e}")
        print()
        return results


# ============ 数据处理器 ============
class DataProcessor:
    @staticmethod
    def deduplicate(channels):
        seen = set()
        unique = []
        dup = 0
        for ch in channels:
            key = (ch.name.lower().strip(), ch.url.strip())
            if key not in seen:
                seen.add(key)
                unique.append(ch)
            else:
                dup += 1
        return unique, dup

    @staticmethod
    def auto_classify(channels):
        keywords = {
            '央视频道': ['cctv', '中央', '央视', '中国之声', 'cgtn'],
            '卫视频道': ['卫视', '湖南卫视', '浙江卫视', '东方卫视', '北京卫视', '江苏卫视', '广东卫视'],
            '港澳台': ['凤凰', 'tvb', '澳视', '台湾', '东森', '中天', '民视', '三立', 'viu', 'now', '港', '澳', '台'],
            '电影频道': ['电影', '影院', 'hbo', 'fox', 'movie', 'film', '影视', '好莱坞'],
            '体育频道': ['体育', 'espn', 'nba', '足球', '高尔夫', '网球', '赛车', 'sport', '劲爆'],
            '少儿频道': ['少儿', '卡通', '动画', '动漫', 'kid', 'baby', '迪士尼', 'nick', '嘉佳'],
            '新闻频道': ['新闻', 'news', '资讯', '财经', 'bloomberg', 'cnn'],
            '地方频道': ['北京', '上海', '广东', '深圳', '四川', '湖南', '浙江', '江苏', '山东', '河南', '湖北'],
            '国际频道': ['bbc', 'nbc', 'abc', 'discovery', 'national', 'history', 'nhk', 'kbs', 'tvbs'],
            '音乐频道': ['音乐', 'mtv', 'vh1', 'music', '演唱会'],
            '4K/8K超清': ['4k', '8k', 'uhd', '超清', 'hdr'],
        }
        for ch in channels:
            if ch.group and ch.group != "未分类":
                continue
            name_lower = ch.name.lower()
            for group, keys in keywords.items():
                if any(k in name_lower for k in keys):
                    ch.group = group
                    break
            else:
                ch.group = "其他"
        return channels

    @staticmethod
    def keep_fastest_per_channel(channels):
        groups = defaultdict(list)
        for ch in channels:
            norm = re.sub(r'\s*(hd|fhd|uhd|4k|8k|1080p|720p|\d+p)\s*$', '', ch.name.lower(), flags=re.I)
            norm = re.sub(r'\s*\[.*?\]\s*', '', norm)
            norm = re.sub(r'\s*\(.*?\)\s*', '', norm)
            groups[norm.strip()].append(ch)

        fastest = []
        removed = 0
        for norm_name, ch_list in groups.items():
            if not ch_list:
                continue
            ch_list.sort(key=lambda c: (not c.is_available, c.best_response_time))
            fastest.append(ch_list[0])
            removed += len(ch_list) - 1
        return fastest, removed

    @staticmethod
    def classify(channels):
        groups = defaultdict(list)
        for ch in channels:
            g = ch.group.strip() if ch.group.strip() else "未分类"
            groups[g].append(ch)
        for g in groups:
            groups[g].sort(key=lambda c: c.name.lower())
        return dict(sorted(groups.items(), key=lambda x: x[0].lower()))

# ============ 导出器 ============
class Exporter:
    @staticmethod
    def export_m3u(channels, path, epg_url=""):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f2:
            f2.write('#EXTM3U')
            if epg_url:
                f2.write(f' x-tvg-url="{epg_url}"')
            f2.write('\n')
            f2.write(f'#EXTINF:-1,整理时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f2.write(f'#EXTINF:-1,总频道数: {len(channels)}\n\n')

            classified = DataProcessor.classify(channels)
            for group_name, group_chs in classified.items():
                f2.write(f'\n# === {group_name} ({len(group_chs)}个) ===\n')
                for ch in group_chs:
                    attrs = [f'tvg-name="{ch.tvg_name or ch.name}"']
                    if ch.logo:
                        attrs.append(f'tvg-logo="{ch.logo}"')
                    if ch.tvg_id:
                        attrs.append(f'tvg-id="{ch.tvg_id}"')
                    if ch.group:
                        attrs.append(f'group-title="{ch.group}"')
                    if ch.epg:
                        attrs.append(f'x-tvg-url="{ch.epg}"')

                    status = "✅" if ch.is_available else "❌"
                    method = ch.test_method.upper() if ch.test_method else "UNTESTED"
                    rt = f"{ch.best_response_time}s" if ch.best_response_time < 99999 else "超时"
                    f2.write(f'#EXTINF:-1 {" ".join(attrs)},{ch.name} [{status} {method} {rt}]\n')
                    f2.write(f'{ch.url}\n')
        Term.log("SUCCESS", f"导出M3U: {path}")

    @staticmethod
    def export_txt(channels, path):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f2:
            f2.write(f'# M3U源整理结果\n')
            f2.write(f'# 时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
            classified = DataProcessor.classify(channels)
            for group_name, group_chs in classified.items():
                f2.write(f'\n# === {group_name} ===\n')
                for ch in group_chs:
                    status = "✅" if ch.is_available else "❌"
                    rt = f"{ch.best_response_time}s" if ch.best_response_time < 99999 else "超时"
                    f2.write(f'{ch.name},{ch.url}#{ch.group} [{status} {rt}]\n')
        Term.log("SUCCESS", f"导出TXT: {path}")

    @staticmethod
    def export_json(channels, path):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        classified = DataProcessor.classify(channels)
        data = {
            'meta': {
                'time': datetime.now().isoformat(),
                'total': len(channels),
                'available': sum(1 for c in channels if c.is_available)
            },
            'groups': {
                g: [{'name': c.name, 'url': c.url, 'group': c.group, 'logo': c.logo,
                     'tvg_id': c.tvg_id, 'tvg_name': c.tvg_name,
                     'available': c.is_available, 'response_time': (c.best_response_time if c.best_response_time < 99999 else None),
                     'test_method': c.test_method, 'test_time': c.test_time,
                     'source_file': c.source_file}
                    for c in cls]
                for g, cls in classified.items()
            }
        }
        with open(path, 'w', encoding='utf-8') as f2:
            json.dump(data, f2, ensure_ascii=False, indent=2)
        Term.log("SUCCESS", f"导出JSON: {path}")


# ============ 主应用 ============
class M3UScannerApp:
    def __init__(self):
        self.config = Config()
        self.channels = []
        self.processed_channels = []
        self.current_file = ""
        self.loaded_files = []
        self.is_deduplicated = False
        self.is_tested = False
        self.is_filtered = False
        self.is_classified = False

    def backup_last_result(self):
        """扫描前备份 List 目录的上次结果到 Backups"""
        if not os.path.exists(LIST_DIR):
            return
        files = [f for f in os.listdir(LIST_DIR) 
                 if f.endswith(('.m3u', '.m3u8', '.txt', '.json'))]
        if not files:
            return

        # 创建带时间戳的子目录
        backup_subdir = os.path.join(BACKUPS_DIR, datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(backup_subdir, exist_ok=True)

        Term.log("INFO", f"备份上次扫描结果到: {backup_subdir}")
        for fname in files:
            src = os.path.join(LIST_DIR, fname)
            dst = os.path.join(backup_subdir, fname)
            shutil.copy2(src, dst)
            os.remove(src)
            Term.log("INFO", f"  已备份: {fname}")
        Term.log("SUCCESS", f"备份完成: {len(files)} 个文件")

    def load_backup_prompt(self):
        """启动时询问是否加载 Backups 中的上次结果"""
        # 获取所有备份子目录（按时间排序）
        if not os.path.exists(BACKUPS_DIR):
            return
        backup_dirs = sorted([d for d in os.listdir(BACKUPS_DIR) 
                              if os.path.isdir(os.path.join(BACKUPS_DIR, d))], reverse=True)
        if not backup_dirs:
            return

        latest_backup = os.path.join(BACKUPS_DIR, backup_dirs[0])
        backup_files = [f for f in os.listdir(latest_backup)
                        if f.endswith(('.m3u', '.m3u8', '.txt'))]
        if not backup_files:
            return

        print()
        print(Term.color(f"  📦 发现上次扫描备份 ({backup_dirs[0]}):", Term.YELLOW))
        for f in backup_files:
            print(f"     • {f}")
        print()

        if self._confirm("是否将上次备份结果追加到当前扫描中?"):
            for fname in backup_files:
                fpath = os.path.join(latest_backup, fname)
                Term.log("INFO", f"加载备份: {fname}")
                chs = M3UParser.parse_file(fpath)
                self.channels.extend(chs)
                self.processed_channels.extend(chs)
                self.loaded_files.append(f"[备份]{fname}")
            Term.log("SUCCESS", f"已追加 {len(backup_files)} 个备份文件")
            self._wait_key()

    def _draw_header(self):
        print(Term.color("╔══════════════════════════════════════════════════════════════╗", Term.CYAN))
        print(Term.color("║", Term.CYAN) + Term.color("           M3U源扫描整理工具 v3.0 - 终端版                  ", Term.YELLOW, bold=True) + Term.color("║", Term.CYAN))
        print(Term.color("║", Term.CYAN) + Term.color("  多源加载 | HTTP/VLC测速 | 台标EPG | 分类导出                ", Term.DIM) + Term.color("║", Term.CYAN))
        print(Term.color("╚══════════════════════════════════════════════════════════════╝", Term.CYAN))
        print()

    def _draw_status(self):
        total = len(self.channels)
        avail = sum(1 for c in self.processed_channels if c.is_available) if self.processed_channels else 0
        files_str = ", ".join(self.loaded_files[:3]) if self.loaded_files else "未加载"
        if len(self.loaded_files) > 3:
            files_str += f" 等{len(self.loaded_files)}个"

        status_parts = [
            f"📂 {files_str}",
            f"📊 {total}个",
            f"✅ {avail}可用",
            f"🧹 {'✓' if self.is_deduplicated else '✗'}",
            f"🔬 {'✓' if self.is_tested else '✗'}",
            f"⚡ {'✓' if self.is_filtered else '✗'}",
        ]

        bar = " │ ".join(status_parts)
        bar_clean = re.sub(r'\033\[[0-9;]*m', '', bar)
        if len(bar_clean) > 75:
            bar = bar[:75] + "..."
        print(Term.color(f"  {bar}", Term.BG_BLUE + Term.WHITE))
        print()

    def _draw_menu(self):
        print(Term.color("  ┌────────────────────────────────────────────────────────┐", Term.CYAN))
        print(Term.color("  │  📋 主菜单                                              │", Term.CYAN))
        print(Term.color("  ├────────────────────────────────────────────────────────┤", Term.CYAN))

        items = [
            ("1", "📂 加载本地文件", "从 tests/ 目录读取"),
            ("2", "🌐 加载GitHub链接", "支持多个链接批量下载"),
            ("3", "🧹 去重处理", "移除重复频道"),
            ("4", "🔬 HTTP快速测速", "并发HTTP请求测试"),
            ("5", "🎬 VLC真实测试", "VLC实际播放验证"),
            ("6", "⚡ 筛选最快源", "每频道保留最优"),
            ("7", "🏷️  智能分类+台标", "自动归类并匹配台标"),
            ("8", "📡 EPG节目单", "下载/更新EPG数据"),
            ("9", "💾 导出到 List/", "M3U/TXT/JSON"),
            ("10", "🚀 一键全自动", "全流程自动处理"),
            ("11", "⚙️  设置", "修改运行参数"),
            ("0", "❌ 退出", ""),
        ]

        for key, text, desc in items:
            line = f"  │  [{Term.color(key, Term.CYAN, bold=True)}] {Term.color(text, Term.WHITE, bold=True)}"
            if desc:
                line += f"  {Term.color(desc, Term.DIM)}"
            line_clean = re.sub(r'\033\[[0-9;]*m', '', line)
            padding = max(0, 58 - len(line_clean) + 2)
            print(line + " " * padding + Term.color("│", Term.CYAN))

        print(Term.color("  └────────────────────────────────────────────────────────┘", Term.CYAN))
        print()

    def _wait_key(self, msg="按 Enter 返回菜单..."):
        input(Term.color(f"\n  ⏎ {msg}", Term.DIM))

    def _input_path(self, prompt, default=""):
        default_str = f" [{default}]" if default else ""
        val = input(Term.color(f"  {prompt}{default_str}: ", Term.YELLOW)).strip()
        return val if val else default

    def _confirm(self, msg):
        r = input(Term.color(f"  {msg} (y/n): ", Term.YELLOW)).strip().lower()
        return r in ('y', 'yes', '是', '1')

    def action_load_local(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  📂 加载本地文件 (tests/ 目录)", Term.YELLOW, bold=True))
        print()

        if not os.path.exists(CAPTURE_DIR):
            os.makedirs(CAPTURE_DIR, exist_ok=True)

        files = [f for f in os.listdir(CAPTURE_DIR) 
                 if f.endswith(('.m3u', '.m3u8', '.txt'))]

        if not files:
            Term.log("WARN", f"tests/ 目录中没有 .m3u/.m3u8/.txt 文件")
            print(f"\n  提示: 请将源文件放入 {CAPTURE_DIR}")
            self._wait_key()
            return

        print(Term.color("  发现以下文件:", Term.CYAN))
        for i, f in enumerate(files):
            size = os.path.getsize(os.path.join(CAPTURE_DIR, f))
            print(f"    [{i+1}] {f:<40} ({size:,} bytes)")
        print(f"    [a] 加载全部")
        print(f"    [0] 取消")
        print()

        choice = input(Term.color("  请选择 (可多选，如: 1 3 5 或 a): ", Term.YELLOW)).strip()

        if choice == '0':
            return

        selected = []
        if choice.lower() == 'a':
            selected = files
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split()]
                selected = [files[i] for i in indices if 0 <= i < len(files)]
            except:
                Term.log("ERROR", "选择无效")
                self._wait_key()
                return

        all_channels = []
        self.loaded_files = []
        for fname in selected:
            fpath = os.path.join(CAPTURE_DIR, fname)
            Term.log("INFO", f"加载: {fname}")
            chs = M3UParser.parse_file(fpath)
            all_channels.extend(chs)
            self.loaded_files.append(fname)

        self.channels = all_channels
        self.processed_channels = list(all_channels)
        self.is_deduplicated = False
        self.is_tested = False
        self.is_filtered = False
        self.is_classified = False

        Term.log("SUCCESS", f"共加载 {len(selected)} 个文件, {len(all_channels)} 个频道")
        self._wait_key()

    def action_load_github(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  🌐 加载GitHub链接", Term.YELLOW, bold=True))
        print()

        print(Term.color("  请输入GitHub链接 (支持多行输入，空行结束):", Term.CYAN))
        print(Term.color("  支持格式:", Term.DIM))
        print("    https://github.com/user/repo/blob/main/file.m3u")
        print("    https://raw.githubusercontent.com/user/repo/main/file.m3u")
        print()

        urls = []
        while True:
            line = input("  > ").strip()
            if not line:
                break
            if GitHubDownloader.is_github_url(line):
                urls.append(line)
            else:
                print(Term.color(f"  ⚠️  不是GitHub链接，跳过: {line[:50]}", Term.YELLOW))

        if not urls:
            Term.log("WARN", "未输入有效链接")
            self._wait_key()
            return

        Term.log("INFO", f"准备下载 {len(urls)} 个GitHub链接...")
        downloaded = GitHubDownloader.download_multiple(urls)

        if not downloaded:
            Term.log("ERROR", "所有链接下载失败")
            self._wait_key()
            return

        all_channels = []
        self.loaded_files = []
        for fpath in downloaded:
            fname = os.path.basename(fpath)
            Term.log("INFO", f"解析: {fname}")
            chs = M3UParser.parse_file(fpath)
            all_channels.extend(chs)
            self.loaded_files.append(fname)

        self.channels = all_channels
        self.processed_channels = list(all_channels)
        self.is_deduplicated = False
        self.is_tested = False
        self.is_filtered = False
        self.is_classified = False

        Term.log("SUCCESS", f"GitHub加载完成: {len(downloaded)}/{len(urls)} 个文件, {len(all_channels)} 个频道")
        self._wait_key()

    def action_deduplicate(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  🧹 去重处理", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        Term.log("INFO", f"处理前: {len(self.processed_channels)} 个频道")
        self.processed_channels, dup = DataProcessor.deduplicate(self.processed_channels)
        self.is_deduplicated = True
        Term.log("SUCCESS", f"去重完成: 移除 {dup} 个重复, 剩余 {len(self.processed_channels)} 个")
        self._wait_key()

    def action_http_test(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  🔬 HTTP快速测速", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        tester = HTTPTester(self.config)
        Term.log("INFO", f"HTTP测试: {len(self.processed_channels)} 个源")
        Term.log("INFO", f"参数: 超时={self.config.get('timeout')}s 并发={self.config.get('max_concurrent')}")
        print()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.processed_channels = loop.run_until_complete(tester.test_all(self.processed_channels))
        loop.close()

        avail = sum(1 for c in self.processed_channels if c.http_available)
        Term.log("SUCCESS", f"HTTP测试完成: 可用 {avail}/{len(self.processed_channels)}")
        self.is_tested = True
        self._wait_key()

    def action_vlc_test(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  🎬 VLC真实播放测试", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        tester = VLCTester(self.config)

        targets = self.processed_channels
        if self.is_tested:
            http_avail = [c for c in self.processed_channels if c.http_available]
            if http_avail and self._confirm(f"只测试HTTP可用的 {len(http_avail)} 个源?"):
                targets = http_avail

        Term.log("INFO", f"VLC测试: {len(targets)} 个源")
        results = tester.test_all(targets)

        for r in results:
            for i, ch in enumerate(self.processed_channels):
                if ch.name == r.name and ch.url == r.url:
                    self.processed_channels[i] = r
                    break

        avail = sum(1 for c in self.processed_channels if c.vlc_available)
        Term.log("SUCCESS", f"VLC测试完成: 可用 {avail}/{len(targets)}")
        self.is_tested = True
        self._wait_key()

    def action_filter(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  ⚡ 筛选每个频道的最快源", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        before = len(self.processed_channels)
        self.processed_channels, removed = DataProcessor.keep_fastest_per_channel(self.processed_channels)
        self.is_filtered = True
        Term.log("SUCCESS", f"筛选: {before} → {len(self.processed_channels)} 个 (移除 {removed})")
        self._wait_key()

    def action_classify(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  🏷️  智能分类 + 台标匹配", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        self.processed_channels = DataProcessor.auto_classify(self.processed_channels)
        self.is_classified = True

        if self.config.get('apply_logo', True):
            self.processed_channels = LogoDB.apply_logos(self.processed_channels)

        classified = DataProcessor.classify(self.processed_channels)
        Term.log("SUCCESS", f"分类完成: {len(classified)} 个分组")
        for g, chs in classified.items():
            avail = sum(1 for c in chs if c.is_available)
            print(f"    📁 {g:<12} {len(chs):>3} 个 (可用: {avail})")

        self._wait_key()

    def action_epg(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  📡 EPG节目单管理", Term.YELLOW, bold=True))
        print()

        EPGManager.list_sources()

        print(Term.color("  [1] 下载单个EPG源", Term.CYAN))
        print(Term.color("  [2] 下载并合并所有EPG源", Term.CYAN))
        print(Term.color("  [3] 设置默认EPG源", Term.CYAN))
        print(Term.color("  [0] 返回", Term.CYAN))
        print()

        choice = input(Term.color("  请选择: ", Term.YELLOW)).strip()

        if choice == '1':
            idx = input(Term.color("  输入EPG源编号: ", Term.YELLOW)).strip()
            try:
                EPGManager.download_epg(int(idx))
            except:
                Term.log("ERROR", "无效编号")
        elif choice == '2':
            EPGManager.download_epg(all_sources=True)
        elif choice == '3':
            idx = input(Term.color("  输入默认EPG源编号: ", Term.YELLOW)).strip()
            try:
                self.config.set('epg_source', int(idx))
                Term.log("SUCCESS", f"默认EPG源已设置为: {EPGManager.EPG_SOURCES[int(idx)]['name']}")
            except:
                Term.log("ERROR", "无效编号")

        self._wait_key()

    def action_export(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  💾 导出文件到 List/", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        base = datetime.now().strftime("%Y-%m-%d")

        print(Term.color("  选择导出格式 (可多选，如: 1 2 3):", Term.CYAN))
        print("    [1] M3U 格式 (含EPG链接)")
        print("    [2] TXT 格式")
        print("    [3] JSON 格式")
        print()

        choice = input(Term.color("  请输入: ", Term.YELLOW)).strip()
        formats = []
        if '1' in choice: formats.append('m3u')
        if '2' in choice: formats.append('txt')
        if '3' in choice: formats.append('json')

        if not formats:
            Term.log("WARN", "未选择格式")
            self._wait_key()
            return

        epg_url = EPGManager.get_epg_url(self.config.get('epg_source', 0))

        for fmt in formats:
            if fmt == 'm3u':
                Exporter.export_m3u(self.processed_channels, 
                                   os.path.join(LIST_DIR, f"{base}_sorted.m3u"),
                                   epg_url=epg_url)
            elif fmt == 'txt':
                Exporter.export_txt(self.processed_channels, 
                                   os.path.join(LIST_DIR, f"{base}_sorted.txt"))
            elif fmt == 'json':
                Exporter.export_json(self.processed_channels, 
                                    os.path.join(LIST_DIR, f"{base}_sorted.json"))

        Term.log("SUCCESS", f"导出完成! 保存在: {LIST_DIR}")
        self._wait_key()

    def action_auto(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  🚀 一键全自动处理", Term.YELLOW, bold=True))
        print()

        if not self.processed_channels:
            Term.log("WARN", "请先加载文件")
            self._wait_key()
            return

        # 备份上次结果
        self.backup_last_result()

        print(Term.color("  选择测试方式:", Term.CYAN))
        print("    [1] HTTP快速测速")
        print("    [2] VLC真实测试")
        print("    [3] 两者都测 (推荐)")
        print("    [4] 跳过测试")

        test_choice = input(Term.color("  请输入: ", Term.YELLOW)).strip()

        # 1. 去重
        print()
        Term.log("INFO", "[1/6] 去重处理...")
        self.processed_channels, dup = DataProcessor.deduplicate(self.processed_channels)
        self.is_deduplicated = True
        Term.log("SUCCESS", f"去重: 移除 {dup} 个重复")

        # 2. 智能分类+台标
        print()
        Term.log("INFO", "[2/6] 智能分类 + 台标匹配...")
        self.processed_channels = DataProcessor.auto_classify(self.processed_channels)
        if self.config.get('apply_logo', True):
            self.processed_channels = LogoDB.apply_logos(self.processed_channels)
        self.is_classified = True

        # 3. 测试
        if test_choice == '1':
            print()
            Term.log("INFO", "[3/6] HTTP快速测速...")
            tester = HTTPTester(self.config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.processed_channels = loop.run_until_complete(tester.test_all(self.processed_channels))
            loop.close()
            self.is_tested = True
        elif test_choice == '2':
            print()
            Term.log("INFO", "[3/6] VLC真实测试...")
            tester = VLCTester(self.config)
            self.processed_channels = tester.test_all(self.processed_channels)
            self.is_tested = True
        elif test_choice == '3':
            print()
            Term.log("INFO", "[3/6] HTTP快速测速...")
            tester = HTTPTester(self.config)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.processed_channels = loop.run_until_complete(tester.test_all(self.processed_channels))
            loop.close()

            http_avail = [c for c in self.processed_channels if c.http_available]
            print()
            Term.log("INFO", f"[4/6] VLC验证 {len(http_avail)} 个源...")
            tester2 = VLCTester(self.config)
            results = tester2.test_all(http_avail)
            for r in results:
                for i, ch in enumerate(self.processed_channels):
                    if ch.name == r.name and ch.url == r.url:
                        self.processed_channels[i] = r
                        break
            self.is_tested = True
        else:
            print()
            Term.log("INFO", "[3/6] 跳过测试")

        # 4. 筛选
        print()
        Term.log("INFO", "[5/6] 筛选最快源...")
        before = len(self.processed_channels)
        self.processed_channels, removed = DataProcessor.keep_fastest_per_channel(self.processed_channels)
        self.is_filtered = True
        Term.log("SUCCESS", f"筛选: {before} → {len(self.processed_channels)} 个")

        # 5. 导出
        print()
        Term.log("INFO", "[6/6] 导出文件...")
        base = datetime.now().strftime("%Y-%m-%d")
        epg_url = EPGManager.get_epg_url(self.config.get('epg_source', 0))

        Exporter.export_m3u(self.processed_channels, os.path.join(LIST_DIR, f"{base}_sorted.m3u"), epg_url)
        Exporter.export_txt(self.processed_channels, os.path.join(LIST_DIR, f"{base}_sorted.txt"))
        Exporter.export_json(self.processed_channels, os.path.join(LIST_DIR, f"{base}_sorted.json"))

        # 统计
        print()
        print(Term.color("  ╔══════════════════════════════════════════════════════════════╗", Term.GREEN))
        print(Term.color("  ║                    🎉 全自动处理完成!                        ║", Term.GREEN, bold=True))
        print(Term.color("  ╚══════════════════════════════════════════════════════════════╝", Term.GREEN))

        classified = DataProcessor.classify(self.processed_channels)
        print()
        for g, chs in classified.items():
            avail = sum(1 for c in chs if c.is_available)
            print(f"    📁 {g:<12} {len(chs):>3} 个 (可用: {avail})")

        print()
        Term.log("SUCCESS", f"总计: {len(self.processed_channels)} 个频道 | 输出: {LIST_DIR}")
        self._wait_key("按 Enter 返回...")

    def action_settings(self):
        Term.clear()
        self._draw_header()
        print(Term.color("  ⚙️  设置", Term.YELLOW, bold=True))
        print()

        print(f"  当前配置 (保存于 {CONFIG_FILE}):")
        print(f"    HTTP超时:        {self.config.get('timeout')} 秒")
        print(f"    HTTP并发数:      {self.config.get('max_concurrent')}")
        print(f"    HTTP测速时长:    {self.config.get('test_duration')} 秒")
        print(f"    VLC超时:         {self.config.get('vlc_timeout')} 秒")
        print(f"    VLC路径:         {self.config.get('vlc_path')}")
        print(f"    自动分类:        {'开启' if self.config.get('auto_classify') else '关闭'}")
        print(f"    自动台标:        {'开启' if self.config.get('apply_logo') else '关闭'}")
        print(f"    保留失效源:      {'是' if self.config.get('keep_unavailable') else '否'}")
        print(f"    默认EPG源:       {EPGManager.EPG_SOURCES[self.config.get('epg_source', 0)]['name']}")
        print()

        print(Term.color("  [1] 修改HTTP超时", Term.CYAN))
        print(Term.color("  [2] 修改HTTP并发数", Term.CYAN))
        print(Term.color("  [3] 修改HTTP测速时长", Term.CYAN))
        print(Term.color("  [4] 修改VLC超时", Term.CYAN))
        print(Term.color("  [5] 修改VLC路径", Term.CYAN))
        print(Term.color("  [6] 切换自动分类", Term.CYAN))
        print(Term.color("  [7] 切换自动台标", Term.CYAN))
        print(Term.color("  [8] 切换保留失效源", Term.CYAN))
        print(Term.color("  [0] 返回", Term.CYAN))
        print()

        choice = input(Term.color("  请选择: ", Term.YELLOW)).strip()

        if choice == '1':
            v = self._input_path("HTTP超时(秒)", str(self.config.get('timeout')))
            self.config.set('timeout', int(v))
        elif choice == '2':
            v = self._input_path("HTTP并发数", str(self.config.get('max_concurrent')))
            self.config.set('max_concurrent', int(v))
        elif choice == '3':
            v = self._input_path("HTTP测速时长(秒)", str(self.config.get('test_duration')))
            self.config.set('test_duration', int(v))
        elif choice == '4':
            v = self._input_path("VLC超时(秒)", str(self.config.get('vlc_timeout')))
            self.config.set('vlc_timeout', int(v))
        elif choice == '5':
            v = self._input_path("VLC路径", self.config.get('vlc_path'))
            self.config.set('vlc_path', v)
        elif choice == '6':
            self.config.set('auto_classify', not self.config.get('auto_classify'))
        elif choice == '7':
            self.config.set('apply_logo', not self.config.get('apply_logo'))
        elif choice == '8':
            self.config.set('keep_unavailable', not self.config.get('keep_unavailable'))

        Term.log("SUCCESS", "设置已保存")
        self._wait_key()

    def run(self):
        # 启动时询问是否加载上次备份
        Term.clear()
        self._draw_header()
        self.load_backup_prompt()

        while True:
            Term.clear()
            self._draw_header()
            self._draw_status()
            self._draw_menu()

            choice = input(Term.color("  🔹 请选择操作: ", Term.YELLOW, bold=True)).strip()

            if choice == '1':
                self.action_load_local()
            elif choice == '2':
                self.action_load_github()
            elif choice == '3':
                self.action_deduplicate()
            elif choice == '4':
                self.action_http_test()
            elif choice == '5':
                self.action_vlc_test()
            elif choice == '6':
                self.action_filter()
            elif choice == '7':
                self.action_classify()
            elif choice == '8':
                self.action_epg()
            elif choice == '9':
                self.action_export()
            elif choice == '10':
                self.action_auto()
            elif choice == '11':
                self.action_settings()
            elif choice == '0':
                Term.clear()
                print(Term.color("\n  👋 感谢使用，再见!\n", Term.GREEN, bold=True))
                break
            else:
                Term.log("WARN", "无效选择")
                time.sleep(1)

# ============ 入口 ============
def main():
    try:
        app = M3UScannerApp()
        app.run()
    except KeyboardInterrupt:
        print(Term.color("\n\n  👋 程序已中断\n", Term.YELLOW))
        sys.exit(0)

if __name__ == '__main__':
    main()
