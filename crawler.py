import requests
import re
import json
import base64
import socket
import time
import random
import uuid
import os
import logging
import argparse
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
import concurrent.futures
import yaml
import ssl

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vpn_crawler.log'),
        logging.StreamHandler()
    ]
)

# 合法的Shadowsocks加密方法
VALID_SS_CIPHERS = [
    "aes-128-gcm", "aes-256-gcm", "chacha20-ietf-poly1305", 
    "xchacha20-ietf-poly1305", "none", "plain", "aes-128-cfb",
    "aes-192-cfb", "aes-256-cfb", "aes-128-ctr", "aes-192-ctr",
    "aes-256-ctr", "rc4-md5", "chacha20-ietf", "chacha20", "salsa20"
]

# 更新为更可靠的免费节点源
SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt"
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/free",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ss-sub",
    "https://raw.githubusercontent.com/colatiger/v2ray-nodes/master/sg.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data2023042.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/all",
    "https://raw.githubusercontent.com/pojiezhiyuanjun/freev2/master/v2",
    "https://raw.githubusercontent.com/vveg26/get_proxy/main/sub",
    "https://raw.githubusercontent.com/alanbobs999/TopFreeProxies/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/zealson/Zure/master/Config/Config.conf",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
    "https://raw.githubusercontent.com/adiwzx/freenode/main/adispeed.txt",
    "https://raw.githubusercontent.com/baixf-go/baixf/main/README.md",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/eycorsican/rule-sets/master/geosite/category-ads-all.txt",
    "https://raw.githubusercontent.com/Jason6111/TopFreeProxies/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/rdp-studio/Free-Node-Merge/main/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/yu-steven/openit/main/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/anaer/Sub/main/config.yaml",
    "https://raw.githubusercontent.com/mksshare/mksshare.github.io/main/README.md",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    "https://raw.githubusercontent.com/ClashrAuto/Clashr-Auto-Server/master/Clashr-Auto-Server.txt",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ss-sub",
    "https://raw.githubusercontent.com/rdp-studio/Free-Node-Merge/main/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/yu-steven/openit/main/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/Jason6111/TopFreeProxies/master/sub/sub_merge.txt"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

# 与前端共享的IP地区映射表
IP_REGION_MAP = {
    # 美国IP段
    "104.16": "美国", "104.17": "美国", "104.18": "美国", "104.19": "美国", "104.20": "美国", "104.21": "美国", 
    "104.22": "美国", "104.23": "美国", "104.24": "美国", "104.25": "美国", "104.26": "美国", "104.27": "美国", 
    "104.28": "美国", "104.29": "美国", "104.30": "美国", "104.31": "美国", "108.162": "美国", "141.101": "美国", 
    "162.158": "美国", "172.64": "美国", "172.65": "美国", "172.66": "美国", "172.67": "美国", "172.68": "美国", 
    "172.69": "美国", "172.70": "美国", "172.71": "美国", "172.72": "美国", "172.73": "美国", "172.74": "美国", 
    "172.75": "美国", "172.76": "美国", "172.77": "美国", "172.78": "美国", "172.79": "美国", "172.80": "美国", 
    "172.81": "美国", "172.82": "美国", "172.83": "美国", "172.84": "美国", "172.85": "美国", "172.86": "美国", 
    "172.87": "美国", "172.88": "美国", "172.89": "美国", "172.90": "美国", "172.91": "美国", "172.92": "美国", 
    "172.93": "美国", "172.94": "美国", "172.95": "美国", "172.96": "美国", "172.97": "美国", "172.98": "美国", 
    "172.99": "美国", "172.100": "美国", "172.101": "美国", "172.102": "美国", "172.103": "美国", "172.104": "美国", 
    "172.105": "美国", "172.106": "美国", "172.107": "美国", "172.108": "美国", "172.109": "美国", "172.110": "美国", 
    "172.111": "美国", "172.112": "美国", "172.113": "美国", "172.114": "美国", "172.115": "美国", "172.116": "美国", 
    "172.117": "美国", "172.118": "美国", "172.119": "美国", "172.120": "美国", "172.121": "美国", "172.122": "美国", 
    "172.123": "美国", "172.124": "美国", "172.125": "美国", "172.126": "美国", "172.127": "美国", "172.128": "美国", 
    "172.129": "美国", "172.130": "美国", "172.131": "美国", "172.132": "美国", "172.133": "美国", "172.134": "美国", 
    "172.135": "美国", "172.136": "美国", "172.137": "美国", "172.138": "美国", "172.139": "美国", "172.140": "美国", 
    "172.141": "美国", "172.142": "美国", "172.143": "美国", "172.144": "美国", "172.145": "美国", "172.146": "美国", 
    "172.147": "美国", "172.148": "美国", "172.149": "美国", "172.150": "美国", "172.151": "美国", "172.152": "美国", 
    "172.153": "美国", "172.154": "美国", "172.155": "美国", "172.156": "美国", "172.157": "美国", "172.158": "美国", 
    "172.159": "美国", "172.160": "美国", "172.161": "美国", "172.162": "美国", "172.163": "美国", "172.164": "美国", 
    "172.165": "美国", "172.166": "美国", "172.167": "美国", "172.168": "美国", "172.169": "美国", "172.170": "美国", 
    "172.171": "美国", "172.172": "美国", "172.173": "美国", "172.174": "美国", "172.175": "美国", "172.176": "美国", 
    "172.177": "美国", "172.178": "美国", "172.179": "美国", "172.180": "美国", "172.181": "美国", "172.182": "美国", 
    "172.183": "美国", "172.184": "美国", "172.185": "美国", "172.186": "美国", "172.187": "美国", "172.188": "美国", 
    "172.189": "美国", "172.190": "美国", "172.191": "美国", "172.192": "美国", "172.193": "美国", "172.194": "美国", 
    "172.195": "美国", "172.196": "美国", "172.197": "美国", "172.198": "美国", "172.199": "美国", "172.200": "美国", 
    "172.201": "美国", "172.202": "美国", "172.203": "美国", "172.204": "美国", "172.205": "美国", "172.206": "美国", 
    "172.207": "美国", "172.208": "美国", "172.209": "美国", "172.210": "美国", "172.211": "美国", "172.212": "美国", 
    "172.213": "美国", "172.214": "美国", "172.215": "美国", "172.216": "美国", "172.217": "美国", "172.218": "美国", 
    "172.219": "美国", "172.220": "美国", "172.221": "美国", "172.222": "美国", "172.223": "美国", "172.224": "美国", 
    "172.225": "美国", "172.226": "美国", "172.227": "美国", "172.228": "美国", "172.229": "美国", "172.230": "美国", 
    "172.231": "美国", "172.232": "美国", "172.233": "美国", "172.234": "美国", "172.235": "美国", "172.236": "美国", 
    "172.237": "美国", "172.238": "美国", "172.239": "美国", "172.240": "美国", "172.241": "美国", "172.242": "美国", 
    "172.243": "美国", "172.244": "美国", "172.245": "美国", "172.246": "美国", "172.247": "美国", "172.248": "美国", 
    "172.249": "美国", "172.250": "美国", "172.251": "美国", "172.252": "美国", "172.253": "美国", "172.254": "美国", 
    "172.255": "美国",
    
    # 日本IP段
    "45.32": "日本", "45.33": "日本", "45.34": "日本", "45.35": "日本", "45.36": "日本", "45.37": "日本", 
    "45.38": "日本", "45.39": "日本", "45.40": "日本", "45.41": "日本", "45.42": "日本", "45.43": "日本", 
    "45.44": "日本", "45.45": "日本", "45.46": "日本", "45.47": "日本", "45.48": "日本", "45.49": "日本", 
    "45.50": "日本", "45.51": "日本", "45.52": "日本", "45.53": "日本", "45.54": "日本", "45.55": "日本", 
    "45.56": "日本", "45.57": "日本", "45.58": "日本", "45.59": "日本", "45.60": "日本", "45.61": "日本", 
    "45.62": "日本", "45.63": "日本", "45.64": "日本", "45.65": "日本", "45.66": "日本", "45.67": "日本", 
    "45.68": "日本", "45.69": "日本", "45.70": "日本", "45.71": "日本", "45.72": "日本", "45.73": "日本", 
    "45.74": "日本", "45.75": "日本", "45.76": "日本", "45.77": "日本", "45.78": "日本", "45.79": "日本", 
    "45.80": "日本", "45.81": "日本", "45.82": "日本", "45.83": "日本", "45.84": "日本", "45.85": "日本", 
    "45.86": "日本", "45.87": "日本", "45.88": "日本", "45.89": "日本", "45.90": "日本", "45.91": "日本", 
    "45.92": "日本", "45.93": "日本", "45.94": "日本", "45.95": "日本", "45.96": "日本", "45.97": "日本", 
    "45.98": "日本", "45.99": "日本", "45.100": "日本", "45.101": "日本", "45.102": "日本", "45.103": "日本", 
    "45.104": "日本", "45.105": "日本", "45.106": "日本", "45.107": "日本", "45.108": "日本", "45.109": "日本", 
    "45.110": "日本", "45.111": "日本", "45.112": "日本", "45.113": "日本", "45.114": "日本", "45.115": "日本", 
    "45.116": "日本", "45.117": "日本", "45.118": "日本", "45.119": "日本", "45.120": "日本", "45.121": "日本", 
    "45.122": "日本", "45.123": "日本", "45.124": "日本", "45.125": "日本", "45.126": "日本", "45.127": "日本", 
    "45.128": "日本", "45.129": "日本", "45.130": "日本", "45.131": "日本", "45.132": "日本", "45.133": "日本", 
    "45.134": "日本", "45.135": "日本", "45.136": "日本", "45.137": "日本", "45.138": "日本", "45.139": "日本", 
    "45.140": "日本", "45.141": "日本", "45.142": "日本", "45.143": "日本", "45.144": "日本", "45.145": "日本", 
    "45.146": "日本", "45.147": "日本", "45.148": "日本", "45.149": "日本", "45.150": "日本", "45.151": "日本", 
    "45.152": "日本", "45.153": "日本", "45.154": "日本", "45.155": "日本", "45.156": "日本", "45.157": "日本", 
    "45.158": "日本", "45.159": "日本", "45.160": "日本", "45.161": "日本", "45.162": "日本", "45.163": "日本", 
    "45.164": "日本", "45.165": "日本", "45.166": "日本", "45.167": "日本", "45.168": "日本", "45.169": "日本", 
    "45.170": "日本", "45.171": "日本", "45.172": "日本", "45.173": "日本", "45.174": "日本", "45.175": "日本", 
    "45.176": "日本", "45.177": "日本", "45.178": "日本", "45.179": "日本", "45.180": "日本", "45.181": "日本", 
    "45.182": "日本", "45.183": "日本", "45.184": "日本", "45.185": "日本", "45.186": "日本", "45.187": "日本", 
    "45.188": "日本", "45.189": "日本", "45.190": "日本", "45.191": "日本", "45.192": "日本", "45.193": "日本", 
    "45.194": "日本", "45.195": "日本", "45.196": "日本", "45.197": "日本", "45.198": "日本", "45.199": "日本", 
    "45.200": "日本", "45.201": "日本", "45.202": "日本", "45.203": "日本", "45.204": "日本", "45.205": "日本", 
    "45.206": "日本", "45.207": "日本", "45.208": "日本", "45.209": "日本", "45.210": "日本", "45.211": "日本", 
    "45.212": "日本", "45.213": "日本", "45.214": "日本", "45.215": "日本", "45.216": "日本", "45.217": "日本", 
    "45.218": "日本", "45.219": "日本", "45.220": "日本", "45.221": "日本", "45.222": "日本", "45.223": "日本", 
    "45.224": "日本", "45.225": "日本", "45.226": "日本", "45.227": "日本", "45.228": "日本", "45.229": "日本", 
    "45.230": "日本", "45.231": "日本", "45.232": "日本", "45.233": "日本", "45.234": "日本", "45.235": "日本", 
    "45.236": "日本", "45.237": "日本", "45.238": "日本", "45.239": "日本", "45.240": "日本", "45.241": "日本", 
    "45.242": "日本", "45.243": "日本", "45.244": "日本", "45.245": "日本", "45.246": "日本", "45.247": "日本", 
    "45.248": "日本", "45.249": "日本", "45.250": "日本", "45.251": "日本", "45.252": "日本", "45.253": "日本", 
    "45.254": "日本", "45.255": "日本",
    
    # 韩国IP段
    "125.141": "韩国", "125.142": "韩国", "125.143": "韩国", "125.144": "韩国", "125.145": "韩国", "125.146": "韩国", 
    "125.147": "韩国", "125.148": "韩国", "125.149": "韩国", "125.150": "韩国", "125.151": "韩国", "125.152": "韩国", 
    "125.153": "韩国", "125.154": "韩国", "125.155": "韩国", "125.156": "韩国", "125.157": "韩国", "125.158": "韩国", 
    "125.159": "韩国", "125.160": "韩国", "125.161": "韩国", "125.162": "韩国", "125.163": "韩国", "125.164": "韩国", 
    "125.165": "韩国", "125.166": "韩国", "125.167": "韩国", "125.168": "韩国", "125.169": "韩国", "125.170": "韩国", 
    "125.171": "韩国", "125.172": "韩国", "125.173": "韩国", "125.174": "韩国", "125.175": "韩国", "125.176": "韩国", 
    "125.177": "韩国", "125.178": "韩国", "125.179": "韩国", "125.180": "韩国", "125.181": "韩国", "125.182": "韩国", 
    "125.183": "韩国", "125.184": "韩国", "125.185": "韩国", "125.186": "韩国", "125.187": "韩国", "125.188": "韩国", 
    "125.189": "韩国", "125.190": "韩国", "125.191": "韩国", "125.192": "韩国", "125.193": "韩国", "125.194": "韩国", 
    "125.195": "韩国", "125.196": "韩国", "125.197": "韩国", "125.198": "韩国", "125.199": "韩国", "125.200": "韩国", 
    "125.201": "韩国", "125.202": "韩国", "125.203": "韩国", "125.204": "韩国", "125.205": "韩国", "125.206": "韩国", 
    "125.207": "韩国", "125.208": "韩国", "125.209": "韩国", "125.210": "韩国", "125.211": "韩国", "125.212": "韩国", 
    "125.213": "韩国", "125.214": "韩国", "125.215": "韩国", "125.216": "韩国", "125.217": "韩国", "125.218": "韩国", 
    "125.219": "韩国", "125.220": "韩国", "125.221": "韩国", "125.222": "韩国", "125.223": "韩国", "125.224": "韩国", 
    "125.225": "韩国", "125.226": "韩国", "125.227": "韩国", "125.228": "韩国", "125.229": "韩国", "125.230": "韩国", 
    "125.231": "韩国", "125.232": "韩国", "125.233": "韩国", "125.234": "韩国", "125.235": "韩国", "125.236": "韩国", 
    "125.237": "韩国", "125.238": "韩国", "125.239": "韩国", "125.240": "韩国", "125.241": "韩国", "125.242": "韩国", 
    "125.243": "韩国", "125.244": "韩国", "125.245": "韩国", "125.246": "韩国", "125.247": "韩国", "125.248": "韩国", 
    "125.249": "韩国", "125.250": "韩国", "125.251": "韩国", "125.252": "韩国", "125.253": "韩国", "125.254": "韩国", 
    "125.255": "韩国",
    
    # 香港IP段
    "43.128": "香港", "43.129": "香港", "43.130": "香港", "43.131": "香港", "43.132": "香港", "43.133": "香港", 
    "43.134": "香港", "43.135": "香港", "43.136": "香港", "43.137": "香港", "43.138": "香港", "43.139": "香港", 
    "43.140": "香港", "43.141": "香港", "43.142": "香港", "43.143": "香港", "43.144": "香港", "43.145": "香港", 
    "43.146": "香港", "43.147": "香港", "43.148": "香港", "43.149": "香港", "43.150": "香港", "43.151": "香港", 
    "43.152": "香港", "43.153": "香港", "43.154": "香港", "43.155": "香港", "43.156": "香港", "43.157": "香港", 
    "43.158": "香港", "43.159": "香港", "43.160": "香港", "43.161": "香港", "43.162": "香港", "43.163": "香港", 
    "43.164": "香港", "43.165": "香港", "43.166": "香港", "43.167": "香港", "43.168": "香港", "43.169": "香港", 
    "43.170": "香港", "43.171": "香港", "43.172": "香港", "43.173": "香港", "43.174": "香港", "43.175": "香港", 
    "43.176": "香港", "43.177": "香港", "43.178": "香港", "43.179": "香港", "43.180": "香港", "43.181": "香港", 
    "43.182": "香港", "43.183": "香港", "43.184": "香港", "43.185": "香港", "43.186": "香港", "43.187": "香港", 
    "43.188": "香港", "43.189": "香港", "43.190": "香港", "43.191": "香港", "43.192": "香港", "43.193": "香港", 
    "43.194": "香港", "43.195": "香港", "43.196": "香港", "43.197": "香港", "43.198": "香港", "43.199": "香港", 
    "43.200": "香港", "43.201": "香港", "43.202": "香港", "43.203": "香港", "43.204": "香港", "43.205": "香港", 
    "43.206": "香港", "43.207": "香港", "43.208": "香港", "43.209": "香港", "43.210": "香港", "43.211": "香港", 
    "43.212": "香港", "43.213": "香港", "43.214": "香港", "43.215": "香港", "43.216": "香港", "43.217": "香港", 
    "43.218": "香港", "43.219": "香港", "43.220": "香港", "43.221": "香港", "43.222": "香港", "43.223": "香港", 
    "43.224": "香港", "43.225": "香港", "43.226": "香港", "43.227": "香港", "43.228": "香港", "43.229": "香港", 
    "43.230": "香港", "43.231": "香港", "43.232": "香港", "43.233": "香港", "43.234": "香港", "43.235": "香港", 
    "43.236": "香港", "43.237": "香港", "43.238": "香港", "43.239": "香港", "43.240": "香港", "43.241": "香港", 
    "43.242": "香港", "43.243": "香港", "43.244": "香港", "43.245": "香港", "43.246": "香港", "43.247": "香港", 
    "43.248": "香港", "43.249": "香港", "43.250": "香港", "43.251": "香港", "43.252": "香港", "43.253": "香港", 
    "43.254": "香港", "43.255": "香港",
    
    # 新加坡IP段
    "103.27": "新加坡", "103.28": "新加坡", "103.29": "新加坡", "103.30": "新加坡", "103.31": "新加坡", 
    "103.32": "新加坡", "103.33": "新加坡", "103.34": "新加坡", "103.35": "新加坡", "103.36": "新加坡", 
    "103.37": "新加坡", "103.38": "新加坡", "103.39": "新加坡", "103.40": "新加坡", "103.41": "新加坡", 
    "103.42": "新加坡", "103.43": "新加坡", "103.44": "新加坡", "103.45": "新加坡", "103.46": "新加坡", 
    "103.47": "新加坡", "103.48": "新加坡", "103.49": "新加坡", "103.50": "新加坡", "103.51": "新加坡", 
    "103.52": "新加坡", "103.53": "新加坡", "103.54": "新加坡", "103.55": "新加坡", "103.56": "新加坡", 
    "103.57": "新加坡", "103.58": "新加坡", "103.59": "新加坡", "103.60": "新加坡", "103.61": "新加坡", 
    "103.62": "新加坡", "103.63": "新加坡", "103.64": "新加坡", "103.65": "新加坡", "103.66": "新加坡", 
    "103.67": "新加坡", "103.68": "新加坡", "103.69": "新加坡", "103.70": "新加坡", "103.71": "新加坡", 
    "103.72": "新加坡", "103.73": "新加坡", "103.74": "新加坡", "103.75": "新加坡", "103.76": "新加坡", 
    "103.77": "新加坡", "103.78": "新加坡", "103.79": "新加坡", "103.80": "新加坡", "103.81": "新加坡", 
    "103.82": "新加坡", "103.83": "新加坡", "103.84": "新加坡", "103.85": "新加坡", "103.86": "新加坡", 
    "103.87": "新加坡", "103.88": "新加坡", "103.89": "新加坡", "103.90": "新加坡", "103.91": "新加坡", 
    "103.92": "新加坡", "103.93": "新加坡", "103.94": "新加坡", "103.95": "新加坡", "103.96": "新加坡", 
    "103.97": "新加坡", "103.98": "新加坡", "103.99": "新加坡", "103.100": "新加坡", "103.101": "新加坡", 
    "103.102": "新加坡", "103.103": "新加坡", "103.104": "新加坡", "103.105": "新加坡", "103.106": "新加坡", 
    "103.107": "新加坡", "103.108": "新加坡", "103.109": "新加坡", "103.110": "新加坡", "103.111": "新加坡", 
    "103.112": "新加坡", "103.113": "新加坡", "103.114": "新加坡", "103.115": "新加坡", "103.116": "新加坡", 
    "103.117": "新加坡", "103.118": "新加坡", "103.119": "新加坡", "103.120": "新加坡", "103.121": "新加坡", 
    "103.122": "新加坡", "103.123": "新加坡", "103.124": "新加坡", "103.125": "新加坡", "103.126": "新加坡", 
    "103.127": "新加坡", "103.128": "新加坡", "103.129": "新加坡", "103.130": "新加坡", "103.131": "新加坡", 
    "103.132": "新加坡", "103.133": "新加坡", "103.134": "新加坡", "103.135": "新加坡", "103.136": "新加坡", 
    "103.137": "新加坡", "103.138": "新加坡", "103.139": "新加坡", "103.140": "新加坡", "103.141": "新加坡", 
    "103.142": "新加坡", "103.143": "新加坡", "103.144": "新加坡", "103.145": "新加坡", "103.146": "新加坡", 
    "103.147": "新加坡", "103.148": "新加坡", "103.149": "新加坡", "103.150": "新加坡", "103.151": "新加坡", 
    "103.152": "新加坡", "103.153": "新加坡", "103.154": "新加坡", "103.155": "新加坡", "103.156": "新加坡", 
    "103.157": "新加坡", "103.158": "新加坡", "103.159": "新加坡", "103.160": "新加坡", "103.161": "新加坡", 
    "103.162": "新加坡", "103.163": "新加坡", "103.164": "新加坡", "103.165": "新加坡", "103.166": "新加坡", 
    "103.167": "新加坡", "103.168": "新加坡", "103.169": "新加坡", "103.170": "新加坡", "103.171": "新加坡", 
    "103.172": "新加坡", "103.173": "新加坡", "103.174": "新加坡", "103.175": "新加坡", "103.176": "新加坡", 
    "103.177": "新加坡", "103.178": "新加坡", "103.179": "新加坡", "103.180": "新加坡", "103.181": "新加坡", 
    "103.182": "新加坡", "103.183": "新加坡", "103.184": "新加坡", "103.185": "新加坡", "103.186": "新加坡", 
    "103.187": "新加坡", "103.188": "新加坡", "103.189": "新加坡", "103.190": "新加坡", "103.191": "新加坡", 
    "103.192": "新加坡", "103.193": "新加坡", "103.194": "新加坡", "103.195": "新加坡", "103.196": "新加坡", 
    "103.197": "新加坡", "103.198": "新加坡", "103.199": "新加坡", "103.200": "新加坡", "103.201": "新加坡", 
    "103.202": "新加坡", "103.203": "新加坡", "103.204": "新加坡", "103.205": "新加坡", "103.206": "新加坡", 
    "103.207": "新加坡", "103.208": "新加坡", "103.209": "新加坡", "103.210": "新加坡", "103.211": "新加坡", 
    "103.212": "新加坡", "103.213": "新加坡", "103.214": "新加坡", "103.215": "新加坡", "103.216": "新加坡", 
    "103.217": "新加坡", "103.218": "新加坡", "103.219": "新加坡", "103.220": "新加坡", "103.221": "新加坡", 
    "103.222": "新加坡", "103.223": "新加坡", "103.224": "新加坡", "103.225": "新加坡", "103.226": "新加坡", 
    "103.227": "新加坡", "103.228": "新加坡", "103.229": "新加坡", "103.230": "新加坡", "103.231": "新加坡", 
    "103.232": "新加坡", "103.233": "新加坡", "103.234": "新加坡", "103.235": "新加坡", "103.236": "新加坡", 
    "103.237": "新加坡", "103.238": "新加坡", "103.239": "新加坡", "103.240": "新加坡", "103.241": "新加坡", 
    "103.242": "新加坡", "103.243": "新加坡", "103.244": "新加坡", "103.245": "新加坡", "103.246": "新加坡", 
    "103.247": "新加坡", "103.248": "新加坡", "103.249": "新加坡", "103.250": "新加坡", "103.251": "新加坡", 
    "103.252": "新加坡", "103.253": "新加坡", "103.254": "新加坡", "103.255": "新加坡"
}

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def fetch_source(url, retry=3, backoff_factor=0.5):
    """从单个源获取节点数据，带重试机制"""
    for attempt in range(retry):
        try:
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                logging.info(f"成功获取源: {url}")
                return response.text
            else:
                logging.warning(f"源 {url} 返回状态码: {response.status_code} (尝试 {attempt+1}/{retry})")
        except Exception as e:
            logging.error(f"获取源 {url} 失败 (尝试 {attempt+1}/{retry}): {str(e)}")
        
        # 指数退避重试
        sleep_time = backoff_factor * (2 ** attempt)
        time.sleep(sleep_time)
    
    logging.error(f"无法获取源: {url} (已重试 {retry} 次)")
    return None

def safe_base64_decode(base64_str):
    """安全地解码Base64字符串"""
    try:
        # 移除所有非Base64字符
        base64_str = re.sub(r'[^A-Za-z0-9+/=]', '', base64_str)
        
        # 处理URL安全的Base64
        base64_str = base64_str.replace('-', '+').replace('_', '/')
        
        # 添加必要的填充
        padding = len(base64_str) % 4
        if padding > 0:
            base64_str += '=' * (4 - padding)
        
        return base64.b64decode(base64_str).decode('utf-8', errors='ignore')
    except Exception as e:
        logging.warning(f"Base64解码失败: {str(e)}")
        return None

def get_region_from_ip(ip):
    """根据IP地址获取地区（使用共享的IP_REGION_MAP）"""
    if not ip:
        return "未知地区"
    
    # 尝试匹配IP段
    for prefix, region in IP_REGION_MAP.items():
        if ip.startswith(prefix):
            return region
    
    # 尝试根据IP第一段判断大致地区
    first_octet = ip.split('.')[0]
    if first_octet >= 1 and first_octet <= 126: return "美国"   # A类地址
    if first_octet >= 128 and first_octet <= 191: return "欧洲" # B类地址
    if first_octet >= 192 and first_octet <= 223: return "亚洲" # C类地址
    
    # 常见云服务商IP段
    if ip.startswith("172."): return "美国"
    if ip.startswith("192."): return "日本"
    if ip.startswith("104."): return "美国"
    if ip.startswith("45."): return "新加坡"
    if ip.startswith("103."): return "新加坡"
    
    return f"IP段 {ip.split('.')[0]}"

def clean_node_name(name, server=None, port=None):
    """清洗节点名称，确保唯一性"""
    if not name:
        name = "未知节点"
    
    # 移除源信息
    name = re.sub(r'github\.com/[^\-]+\-', '', name)
    
    # 移除速度信息
    name = re.sub(r'\d+\.\d+MB/s\|\d+%\|.*', '', name)
    
    # 移除多余符号
    name = re.sub(r'[|\\]', ' ', name)
    
    # 提取国家/地区信息
    country_match = re.search(r'(美国|日本|韩国|新加坡|台湾|香港|英国|德国|加拿大|俄罗斯|印度|巴西|澳大利亚|法国|荷兰|瑞士|瑞典|意大利|西班牙|土耳其|南非)', name)
    region = country_match.group(1) if country_match else None
    
    # 提取服务商信息
    provider_match = re.search(r'(CloudFlare|Fastly|AWS|Azure|Google Cloud|Akamai|DigitalOcean|Linode|Vultr)', name, re.IGNORECASE)
    provider = provider_match.group(1) if provider_match else "未知服务商"
    
    # 提取节点类型
    type_match = re.search(r'(CDN节点|Anycast节点|中转节点|直连节点|优质线路|普通线路|高速节点)', name)
    node_type = type_match.group(1) if type_match else "节点"
    
    # 构建唯一标识字符串
    unique_str = f"{name}{server}{port}{time.time()}{random.randint(1000,9999)}"
    
    # 生成更可靠的唯一标识符
    unique_id = hashlib.md5(unique_str.encode()).hexdigest()[:6]
    
    # 添加服务器IP后三位作为额外标识
    ip_suffix = ""
    if server:
        try:
            # 尝试解析IP地址
            ip = socket.gethostbyname(server)
            ip_parts = ip.split('.')
            if len(ip_parts) == 4:
                ip_suffix = f".{ip_parts[2]}{ip_parts[3][-1]}"
                
                # 如果未从名称中提取到地区，使用IP判断
                if not region:
                    region = get_region_from_ip(ip)
        except:
            # 如果解析失败，直接使用服务器地址判断
            if not region:
                region = get_region_from_ip(server)
    
    # 如果仍未确定地区，使用"未知地区"
    if not region:
        region = "未知地区"
    
    # 确保名称以地区开头
    if not name.startswith(f"[{region}]"):
        name = f"[{region}] {name}"
    
    # 返回格式化的节点名称
    return f"[{region}] {provider} - {node_type} - {unique_id}{ip_suffix}"

def parse_clash_config(content):
    """解析Clash配置文件"""
    nodes = []
    
    # 查找proxies部分
    proxies_start = content.find("proxies:")
    if proxies_start == -1:
        logging.warning("在Clash配置中未找到proxies部分")
        return nodes
        
    proxies_content = content[proxies_start:]
    
    # 使用正则表达式匹配每个节点
    node_pattern = r"- {.*?}\n"
    matches = re.findall(node_pattern, proxies_content, re.DOTALL)
    
    if not matches:
        logging.warning("在Clash配置中未找到任何节点")
        return nodes
    
    logging.info(f"在Clash配置中找到 {len(matches)} 个节点")
    
    for match in matches:
        try:
            node_data = match.strip()[2:]  # 移除 "- "
            node_dict = {}
            
            for line in node_data.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 移除值两端的引号
                    if value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    elif value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                        
                    node_dict[key] = value
            
            # 确保有必要的字段
            if "name" in node_dict and "server" in node_dict and "port" in node_dict:
                # 清洗节点名称
                node_dict["name"] = clean_node_name(
                    node_dict["name"], 
                    node_dict.get("server"), 
                    node_dict.get("port")
                )
                
                # 生成节点配置字符串
                node_type = node_dict.get("type", "unknown").lower()
                
                # 生成Clash配置
                clash_config = {
                    "name": node_dict["name"],
                    "type": node_type,
                    "server": node_dict["server"],
                    "port": int(node_dict["port"]),
                    "udp": True
                }
                
                # VMess节点
                if node_type == "vmess":
                    clash_config.update({
                        "uuid": node_dict.get("uuid", ""),
                        "alterId": int(node_dict.get("alterId", "0")),
                        "cipher": node_dict.get("cipher", "auto"),
                        "tls": node_dict.get("tls", False),
                        "skip-cert-verify": True
                    })
                    
                    # 网络类型相关设置
                    network = node_dict.get("network", "tcp")
                    if network == "ws":
                        clash_config["network"] = "ws"
                        clash_config["ws-path"] = node_dict.get("ws-path", "/")
                        clash_config["ws-headers"] = {"Host": node_dict.get("host", "")}
                
                # Shadowsocks节点 - 验证加密方法
                elif node_type == "ss":
                    cipher = node_dict.get("cipher", "aes-256-gcm")
                    if cipher not in VALID_SS_CIPHERS:
                        logging.warning(f"无效的加密方法: {cipher}, 使用默认值: aes-256-gcm")
                        cipher = "aes-256-gcm"
                    
                    clash_config.update({
                        "cipher": cipher,
                        "password": node_dict.get("password", "")
                    })
                
                nodes.append({
                    "id": str(uuid.uuid4()),
                    "type": node_type,
                    "server": node_dict["server"],
                    "port": node_dict["port"],
                    "name": node_dict["name"],
                    "clash_config": clash_config,
                    "source": "clash_config"
                })
        except Exception as e:
            logging.error(f"解析Clash节点失败: {str(e)}")
    
    logging.info(f"成功解析 {len(nodes)} 个Clash节点")
    return nodes

def parse_subscription_content(content, source_url):
    """解析订阅内容"""
    try:
        # 尝试Base64解码
        try:
            # 检查是否是有效的Base64字符串
            if re.match(r'^[a-zA-Z0-9+/=]+$', content) and len(content) > 100:
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                content = decoded
        except:
            pass
        
        # 检查是否是Clash配置
        if "proxies:" in content:
            logging.info("检测到Clash配置格式")
            return parse_clash_config(content), "clash"
        
        # 解析为节点列表
        nodes = []
        lines = content.splitlines()
        
        if not lines:
            logging.warning("订阅内容为空")
            return nodes, "empty"
        
        logging.info(f"开始解析订阅内容，共 {len(lines)} 行")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                # VMess节点
                if line.startswith("vmess://"):
                    # 解析VMess
                    base64_str = line[8:]
                    decoded = safe_base64_decode(base64_str)
                    
                    if not decoded:
                        continue
                        
                    try:
                        config = json.loads(decoded)
                    except:
                        # 尝试更宽松的解析
                        config = {
                            "add": "",
                            "port": "",
                            "ps": "",
                            "id": ""
                        }
                        logging.warning(f"VMess配置解析失败: {line[:60]}...")
                    
                    server = config.get("add", config.get("host", config.get("address", "")))
                    port = config.get("port", "443")
                    name = clean_node_name(
                        config.get("ps", config.get("name", f"vmess-{server}:{port}")), 
                        server, 
                        port
                    )
                    
                    # 跳过无效节点
                    if not server or not port:
                        continue
                        
                    # 生成Clash配置
                    clash_config = {
                        "name": name,
                        "type": "vmess",
                        "server": server,
                        "port": int(port),
                        "uuid": config.get("id", ""),
                        "alterId": int(config.get("aid", "0")),
                        "cipher": config.get("scy", "auto"),
                        "udp": True,
                        "tls": config.get("tls", "") == "tls",
                        "skip-cert-verify": True
                    }
                    
                    # 网络类型
                    network = config.get("net", "tcp")
                    if network == "ws":
                        clash_config["network"] = "ws"
                        clash_config["ws-path"] = config.get("path", "/")
                        clash_config["ws-headers"] = {"Host": config.get("host", "")}
                    
                    node = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "type": "vmess",
                        "server": server,
                        "port": port,
                        "clash_config": clash_config,
                        "source": source_url
                    }
                    nodes.append(node)
                
                # Shadowsocks节点
                elif line.startswith("ss://"):
                    # 解析Shadowsocks
                    base64_str = line[5:].split('#')[0]
                    
                    # 尝试直接解析
                    if '@' in base64_str:
                        decoded = base64_str
                    else:
                        decoded = safe_base64_decode(base64_str)
                    
                    if not decoded:
                        continue
                    
                    # 获取节点名称
                    name_match = re.search(r'#(.+)$', line)
                    name = clean_node_name(
                        name_match.group(1) if name_match else f"ss-{line[5:15]}", 
                        server, 
                        port
                    )
                    
                    # 处理不同的SS格式
                    method, password, server, port = "", "", "", ""
                    
                    # 尝试解析标准格式: method:password@server:port
                    if '@' in decoded:
                        parts = decoded.split('@', 1)
                        if ':' in parts[0]:
                            method_password = parts[0].split(':', 1)
                            method = method_password[0]
                            password = method_password[1] if len(method_password) > 1 else ""
                        else:
                            method = parts[0]
                            password = ""
                        
                        server_port = parts[1]
                        if ':' in server_port:
                            server_port_parts = server_port.split(':', 1)
                            server = server_port_parts[0]
                            port = server_port_parts[1]
                        else:
                            server = server_port
                    else:
                        # 尝试解析非标准格式
                        if ':' in decoded:
                            parts = decoded.split(':')
                            if len(parts) >= 2:
                                server = parts[0]
                                port = parts[1]
                                if len(parts) > 2:
                                    method = parts[2]
                                if len(parts) > 3:
                                    password = parts[3]
                    
                    # 验证端口是否为数字
                    try:
                        port = int(port)
                    except (ValueError, TypeError):
                        # 如果端口无效，尝试从其他位置提取
                        port_match = re.search(r':(\d+)(/|$)', line)
                        if port_match:
                            port = int(port_match.group(1))
                        else:
                            logging.warning(f"无效的端口号: {port}, 跳过节点: {name}")
                            continue
                    
                    # 跳过无效节点
                    if not server or not port:
                        logging.warning(f"跳过无效节点: {line[:60]}...")
                        continue
                    
                    # 验证加密方法有效性
                    if method not in VALID_SS_CIPHERS:
                        logging.warning(f"无效的加密方法: {method}, 使用默认值: aes-256-gcm")
                        method = "aes-256-gcm"
                    
                    # 生成Clash配置
                    clash_config = {
                        "name": name,
                        "type": "ss",
                        "server": server,
                        "port": int(port),
                        "cipher": method,
                        "password": password,
                        "udp": True
                    }
                    
                    node = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "type": "ss",
                        "server": server,
                        "port": port,
                        "clash_config": clash_config,
                        "source": source_url
                    }
                    nodes.append(node)
                
                # Trojan节点
                elif line.startswith("trojan://"):
                    # 解析Trojan节点
                    try:
                        parsed = urlparse(line)
                        server = parsed.hostname
                        port = parsed.port or 443
                        password = parsed.username
                        name = clean_node_name(
                            parsed.fragment if parsed.fragment else f"trojan-{server}", 
                            server, 
                            port
                        )
                        
                        # 生成Clash配置
                        clash_config = {
                            "name": name,
                            "type": "trojan",
                            "server": server,
                            "port": int(port),
                            "password": password,
                            "udp": True,
                            "skip-cert-verify": True
                        }
                        
                        node = {
                            "id": str(uuid.uuid4()),
                            "name": name,
                            "type": "trojan",
                            "server": server,
                            "port": port,
                            "clash_config": clash_config,
                            "source": source_url
                        }
                        nodes.append(node)
                    except Exception as e:
                        logging.error(f"解析Trojan节点失败: {str(e)} - {line[:60]}")
                
            except Exception as e:
                logging.error(f"解析节点失败: {str(e)} - {line[:60]}")
        
        logging.info(f"成功解析 {len(nodes)} 个节点")
        return nodes, "mixed"
    except Exception as e:
        logging.error(f"解析订阅内容失败: {str(e)}")
        return [], "unknown"

def test_node_connectivity(node, timeout=3):
    """测试节点连接性（支持SSL/TLS）"""
    server = node.get("server", "")
    port = node.get("port", "")
    
    if not server or not port:
        logging.warning(f"节点无效: {node.get('name', '未知节点')} - 缺少服务器或端口")
        return None
    
    try:
        # 尝试解析IP地址
        try:
            ip = socket.gethostbyname(server)
        except:
            ip = server
            
        # 创建socket连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # 处理SSL/TLS连接
        if node.get("clash_config", {}).get("tls", False) or node.get("clash_config", {}).get("security", "") == "tls":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            start_time = time.time()
            with context.wrap_socket(sock, server_hostname=server) as ssock:
                ssock.connect((ip, int(port)))
            latency = int((time.time() - start_time) * 1000)
        else:
            # 普通TCP连接
            start_time = time.time()
            sock.connect((ip, int(port)))
            latency = int((time.time() - start_time) * 1000)
        
        sock.close()
        logging.info(f"节点有效: {node['name']} - 延迟: {latency}ms")
        return latency
    except socket.gaierror:
        logging.warning(f"域名解析失败: {node['name']} - {server}")
        return None
    except socket.timeout:
        logging.warning(f"连接超时: {node['name']} - {server}:{port}")
        return None
    except Exception as e:
        logging.warning(f"连接失败: {node['name']} - {server}:{port} - {str(e)}")
        return None

def generate_clash_subscription(nodes):
    """生成标准的Clash订阅文件"""
    # 节点名称去重检查
    seen_names = set()
    unique_nodes = []
    
    for node in nodes:
        if "clash_config" in node:
            original_name = node["clash_config"]["name"]
            new_name = original_name
            suffix = 1
            
            # 如果名称重复，添加后缀
            while new_name in seen_names:
                new_name = f"{original_name}-{suffix}"
                suffix += 1
            
            if new_name != original_name:
                logging.warning(f"检测到重复节点名称: {original_name}, 已重命名为: {new_name}")
                node["clash_config"]["name"] = new_name
            
            seen_names.add(new_name)
            unique_nodes.append(node)
    
    config = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": False,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": [],
        "proxy-groups": [
            {
                "name": "自动选择",
                "type": "url-test",
                "proxies": [node["clash_config"]["name"] for node in unique_nodes],
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300
            },
            {
                "name": "香港节点",
                "type": "select",
                "proxies": [node["clash_config"]["name"] for node in unique_nodes if "香港" in node["clash_config"]["name"]]
            },
            {
                "name": "美国节点",
                "type": "select",
                "proxies": [node["clash_config"]["name"] for node in unique_nodes if "美国" in node["clash_config"]["name"]]
            },
            {
                "name": "日本节点",
                "type": "select",
                "proxies": [node["clash_config"]["name"] for node in unique_nodes if "日本" in node["clash_config"]["name"]]
            }
        ],
        "rules": [
            "DOMAIN-SUFFIX,google.com,自动选择",
            "DOMAIN-KEYWORD,github,自动选择",
            "IP-CIDR,91.108.56.0/22,自动选择",
            "GEOIP,CN,DIRECT",
            "MATCH,自动选择"
        ]
    }
    
    for node in unique_nodes:
        # 确保所有节点都有udp设置
        if "udp" not in node["clash_config"]:
            node["clash_config"]["udp"] = True
        
        config["proxies"].append(node["clash_config"])
    
    return yaml.dump(config, allow_unicode=True, sort_keys=False)

def generate_shadowrocket_subscription(nodes):
    """生成Shadowrocket订阅文件"""
    shadowrocket_configs = []
    
    for node in nodes:
        if 'clash_config' in node:
            config = node['clash_config']
            if config['type'] == 'vmess':
                # 转换为 V2RayN 格式
                vmess_config = {
                    "v": "2",
                    "ps": config['name'],
                    "add": config['server'],
                    "port": config['port'],
                    "id": config['uuid'],
                    "aid": config.get('alterId', 0),
                    "scy": config.get('cipher', 'auto'),
                    "net": config.get('network', 'tcp'),
                    "type": config.get('ws-headers', {}).get('Host', '') if config.get('network') == 'ws' else "none",
                    "host": config.get('ws-headers', {}).get('Host', ''),
                    "path": config.get('ws-path', ''),
                    "tls": "tls" if config.get('tls') else "",
                    "sni": config.get('servername', '')
                }
                vmess_str = base64.b64encode(json.dumps(vmess_config).encode()).decode()
                shadowrocket_configs.append(f"vmess://{vmess_str}")
            elif config['type'] == 'ss':
                # Shadowsocks 格式
                # 验证加密方法有效性
                cipher = config['cipher']
                if cipher not in VALID_SS_CIPHERS:
                    cipher = "aes-256-gcm"
                    
                ss_str = f"{cipher}:{config['password']}@{config['server']}:{config['port']}"
                encoded_ss = base64.b64encode(ss_str.encode()).decode()
                shadowrocket_configs.append(f"ss://{encoded_ss}#{config['name']}")
            elif config['type'] == 'trojan':
                # Trojan 格式
                trojan_str = f"trojan://{config['password']}@{config['server']}:{config['port']}?sni={config.get('sni', '')}#{config['name']}"
                shadowrocket_configs.append(trojan_str)
    
    return '\n'.join(shadowrocket_configs)

def fetch_all_sources(output_file):
    """从所有源获取并处理节点"""
    all_nodes = []
    
    logging.info("="*50)
    logging.info("开始获取节点源...")
    logging.info("="*50)
    
    # 获取所有源数据
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_source, url): url for url in SOURCES}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            content = future.result()
            if content:
                logging.info(f"处理源: {url}")
                nodes, source_type = parse_subscription_content(content, url)
                logging.info(f"从该源解析出 {len(nodes)} 个节点")
                all_nodes.extend(nodes)
            else:
                logging.warning(f"无法处理源: {url}")
    
    logging.info(f"初始节点数: {len(all_nodes)}")
    
    if not all_nodes:
        logging.error("⚠️ 未获取到任何节点，退出。")
        return []
    
    # 去重（使用节点ID）
    unique_nodes = []
    seen_ids = set()
    
    for node in all_nodes:
        if node["id"] not in seen_ids:
            seen_ids.add(node["id"])
            unique_nodes.append(node)
    
    logging.info(f"去重后节点数: {len(unique_nodes)}")
    
    # 验证节点有效性
    valid_nodes = []
    logging.info("="*50)
    logging.info("开始验证节点连通性...")
    logging.info("="*50)
    
    # 限制最大并发数
    max_workers = min(20, len(unique_nodes))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_node_connectivity, node): node for node in unique_nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                latency = future.result()
                if latency is not None and latency < 3000:  # 延迟限制在3秒内
                    node["latency"] = latency
                    node["last_checked"] = datetime.now(timezone.utc).isoformat()
                    valid_nodes.append(node)
                    logging.info(f"✅ 节点有效: {node['name']} - 延迟: {latency}ms")
                else:
                    logging.info(f"❌ 节点无效: {node['name']}")
            except Exception as e:
                logging.error(f"⚠️ 验证节点失败: {node.get('name', '未知节点')} - {str(e)}")
    
    logging.info(f"有效节点数: {len(valid_nodes)}")
    
    # 保存到文件
    try:
        # 保存节点数据
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(valid_nodes, f, indent=2, ensure_ascii=False)
        logging.info(f"节点数据已保存到 {output_file}")
        
        # 生成订阅文件（只在有效节点存在时）
        if valid_nodes:
            # 生成 Clash 订阅文件
            clash_config = generate_clash_subscription(valid_nodes)
            with open('website/clash_subscription.yaml', 'w', encoding='utf-8') as f:
                f.write(clash_config)
            logging.info("Clash订阅文件已生成")
            
            # 生成 Shadowrocket 订阅文件
            shadowrocket_config = generate_shadowrocket_subscription(valid_nodes)
            with open('website/shadowrocket_subscription.txt', 'w', encoding='utf-8') as f:
                f.write(shadowrocket_config)
            logging.info("Shadowrocket订阅文件已生成")
        
    except Exception as e:
        logging.error(f"保存文件失败: {str(e)}")
    
    return valid_nodes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='爬取免费VPN节点')
    parser.add_argument('-o', '--output', default='website/nodes.json', help='输出文件路径')
    args = parser.parse_args()
    
    logging.info("="*50)
    logging.info("开始爬取所有来源的免费VPN节点...")
    logging.info("="*50)
    
    start_time = time.time()
    
    try:
        nodes = fetch_all_sources(args.output)
    except Exception as e:
        logging.error(f"爬取过程中发生错误: {str(e)}")
        nodes = []
    
    elapsed_time = time.time() - start_time
    
    logging.info("\n" + "="*50)
    if nodes:
        logging.info(f"✅ 成功获取 {len(nodes)} 个有效节点 (耗时: {elapsed_time:.2f}秒)")
    else:
        logging.error("❌ 未获取到任何有效节点")
        # 创建空文件防止前端出错
        with open(args.output, 'w') as f:
            json.dump([], f)
        logging.info(f"已创建空的 {args.output} 文件")
    
    logging.info("="*50)
