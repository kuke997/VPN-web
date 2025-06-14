import requests
import re
import json
import base64
import socket
import time
import os
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
import random

# 更新为实际可用的免费节点源
SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def fetch_source(url):
    """从单个源获取节点数据"""
    try:
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # 尝试检测是否为Base64编码
            content = response.text
            try:
                # 如果是Base64编码，尝试解码
                if not content.startswith(("vmess://", "ss://", "trojan://")):
                    decoded = base64.b64decode(content).decode('utf-8')
                    return decoded
                return content
            except:
                return content
        else:
            print(f"源 {url} 返回状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"获取源 {url} 失败: {str(e)}")
        return None

def parse_vmess(uri):
    """解析VMess URI"""
    try:
        # 提取Base64部分
        base64_str = uri[8:]
        # 补足等号
        if len(base64_str) % 4 != 0:
            base64_str += '=' * (4 - len(base64_str) % 4)
        
        # 解码
        decoded = base64.b64decode(base64_str).decode('utf-8')
        config = json.loads(decoded)
        
        # 提取基本信息
        return {
            'id': str(hash(uri))[:8],  # 生成唯一ID
            'type': 'vmess',
            'server': config.get('add'),
            'port': config.get('port'),
            'id': config.get('id'),
            'alterId': config.get('aid'),
            'security': config.get('scy', 'auto'),
            'network': config.get('net'),
            'name': config.get('ps') or f"vmess-{config.get('add')}:{config.get('port')}",
            'config': uri
        }
    except Exception as e:
        print(f"解析VMess失败: {str(e)}")
        return None

def parse_ss(uri):
    """解析Shadowsocks URI"""
    try:
        # 处理SS-URI格式
        if "#" in uri:
            parts = uri.split("#", 1)
            base64_part = parts[0][5:]
            name = parts[1]
        else:
            base64_part = uri[5:]
            name = ""
        
        # 补足等号
        if len(base64_part) % 4 != 0:
            base64_part += '=' * (4 - len(base64_part) % 4)
        
        # 解码
        decoded = base64.b64decode(base64_part).decode('utf-8')
        
        # 处理可能存在的@符号
        if "@" in decoded:
            method_password, server_port = decoded.split("@", 1)
        else:
            method_password = decoded
            server_port = ""
        
        # 提取方法/密码
        if ":" in method_password:
            method, password = method_password.split(":", 1)
        else:
            method = method_password
            password = ""
        
        # 提取服务器/端口
        if ":" in server_port:
            server, port = server_port.split(":", 1)
        else:
            server = server_port
            port = "443"
        
        # 提取名称
        if not name:
            name = f"ss-{server}:{port}"
        
        return {
            'id': str(hash(uri))[:8],  # 生成唯一ID
            'type': 'ss',
            'server': server,
            'port': port,
            'method': method,
            'password': password,
            'name': name,
            'config': uri
        }
    except Exception as e:
        print(f"解析SS失败: {str(e)} - URI: {uri[:60]}...")
        return None

def parse_subscription_content(content):
    """解析订阅内容"""
    nodes = []
    
    # 分割为行
    lines = content.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            if line.startswith("vmess://"):
                node = parse_vmess(line)
            elif line.startswith("ss://"):
                node = parse_ss(line)
            else:
                # 尝试解析其他格式
                if "://" in line:
                    print(f"跳过不支持的协议: {line.split('://')[0]}")
                continue
                
            if node:
                nodes.append(node)
        except Exception as e:
            print(f"解析行失败: {line[:60]}... - {str(e)}")
    
    return nodes

def test_node_connectivity(node, timeout=3):
    """测试节点连接性"""
    server = node.get('server')
    port = node.get('port')
    
    if not server or not port:
        return False
    
    try:
        # 解析域名获取IP
        if not re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", server):
            try:
                server_ip = socket.gethostbyname(server)
            except socket.gaierror:
                return False
        else:
            server_ip = server
        
        # 尝试建立TCP连接
        start_time = time.time()
        sock = socket.create_connection((server_ip, int(port)), timeout=timeout)
        sock.close()
        latency = int((time.time() - start_time) * 1000)  # 计算延迟
        return latency
    except Exception as e:
        return False

def validate_node(node):
    """验证节点有效性"""
    # 基本字段检查
    required_fields = ['server', 'port', 'config']
    if not all(key in node for key in required_fields):
        return False
    
    # 协议特定验证
    if node['type'] == 'vmess':
        if not node.get('id') or not node.get('alterId'):
            return False
    elif node['type'] == 'ss':
        if not node.get('method') or not node.get('password'):
            return False
    
    # 测试连接性
    latency = test_node_connectivity(node)
    if not latency:
        return False
    
    # 添加额外信息
    node['latency'] = latency
    node['last_checked'] = datetime.utcnow().isoformat() + "Z"
    node['city'] = "未知地区"  # 实际应用中应使用IP地理定位服务
    return True

def fetch_all_sources():
    """从所有源获取并处理节点"""
    all_nodes = []
    
    print("开始获取节点源...")
    # 获取所有源数据
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_source, url) for url in SOURCES]
        for future in concurrent.futures.as_completed(futures):
            content = future.result()
            if content:
                print(f"成功获取源数据，长度: {len(content)} 字符")
                nodes = parse_subscription_content(content)
                all_nodes.extend(nodes)
    
    print(f"初始节点数: {len(all_nodes)}")
    
    if not all_nodes:
        print("⚠️ 未获取到任何节点，退出。")
        return []
    
    # 去重
    unique_nodes = []
    seen_ids = set()
    
    for node in all_nodes:
        if node and 'id' in node and node['id'] not in seen_ids:
            seen_ids.add(node['id'])
            unique_nodes.append(node)
    
    print(f"去重后节点数: {len(unique_nodes)}")
    
    # 验证节点有效性
    valid_nodes = []
    print("开始验证节点连通性...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(validate_node, node): node for node in unique_nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                if future.result():
                    valid_nodes.append(node)
            except Exception as e:
                print(f"验证节点失败: {node.get('name') if node else '未知节点'} - {str(e)}")
    
    # 按延迟排序
    valid_nodes.sort(key=lambda x: x.get('latency', 10000))
    
    print(f"有效节点数: {len(valid_nodes)}")
    
    # 保存到文件
    with open('nodes.json', 'w', encoding='utf-8') as f:
        json.dump(valid_nodes, f, indent=2, ensure_ascii=False)
    
    return valid_nodes

if __name__ == "__main__":
    print("="*50)
    print("开始爬取所有来源的免费VPN节点...")
    print("="*50)
    
    nodes = fetch_all_sources()
    
    print("\n" + "="*50)
    if nodes:
        print(f"✅ 成功获取 {len(nodes)} 个有效节点")
        print("结果已保存到 nodes.json")
    else:
        print("❌ 未获取到任何有效节点")
        # 创建空文件防止前端出错
        with open('nodes.json', 'w') as f:
            json.dump([], f)
        print("已创建空的 nodes.json 文件")
    
    print("="*50)
