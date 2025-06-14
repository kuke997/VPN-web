import requests
import re
import json
import base64
import socket
import time
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures

# 节点源列表
SOURCES = [
    "https://example.com/v1/nodes",  # 替换为实际源
    "https://example.com/v2/nodes",  # 替换为实际源
    "https://example.com/v3/nodes"   # 替换为实际源
]

def fetch_source(url):
    """从单个源获取节点数据"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
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
            'type': 'vmess',
            'server': config.get('add'),
            'port': config.get('port'),
            'id': config.get('id'),
            'alterId': config.get('aid'),
            'security': config.get('scy', 'auto'),
            'network': config.get('net'),
            'name': config.get('ps') or f"vmess-{config.get('add')}:{config.get('port')}"
        }
    except Exception as e:
        print(f"解析VMess失败: {str(e)}")
        return None

def parse_ss(uri):
    """解析Shadowsocks URI"""
    try:
        # 提取Base64部分
        base64_str = uri[5:].split('#')[0]
        # 补足等号
        if len(base64_str) % 4 != 0:
            base64_str += '=' * (4 - len(base64_str) % 4)
        
        # 解码
        decoded = base64.b64decode(base64_str).decode('utf-8')
        parts = decoded.split('@')
        method_password = parts[0]
        server_port = parts[1]
        
        # 提取方法/密码
        method, password = method_password.split(':', 1)
        
        # 提取服务器/端口
        server, port = server_port.split(':')
        
        # 提取名称
        name_match = re.search(r'#(.+)$', uri)
        name = name_match.group(1) if name_match else f"ss-{server}:{port}"
        
        return {
            'type': 'ss',
            'server': server,
            'port': port,
            'method': method,
            'password': password,
            'name': name
        }
    except Exception as e:
        print(f"解析SS失败: {str(e)}")
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
                continue
                
            if node:
                # 添加配置URI
                node['config'] = line
                nodes.append(node)
        except Exception as e:
            print(f"解析行失败: {line} - {str(e)}")
    
    return nodes

def test_node_connectivity(node, timeout=2):
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
    if not all(key in node for key in ['server', 'port', 'config']):
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
    return True

def get_city_from_ip(ip):
    """根据IP获取城市信息（简化版）"""
    # 实际应用中应使用IP地理定位服务
    return "未知地区"

def fetch_all_sources():
    """从所有源获取并处理节点"""
    all_nodes = []
    
    # 获取所有源数据
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_source, url) for url in SOURCES]
        for future in concurrent.futures.as_completed(futures):
            content = future.result()
            if content:
                nodes = parse_subscription_content(content)
                all_nodes.extend(nodes)
    
    print(f"初始节点数: {len(all_nodes)}")
    
    # 去重
    unique_nodes = []
    seen_configs = set()
    
    for node in all_nodes:
        if node['config'] not in seen_configs:
            seen_configs.add(node['config'])
            unique_nodes.append(node)
    
    print(f"去重后节点数: {len(unique_nodes)}")
    
    # 验证节点有效性
    valid_nodes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(validate_node, node): node for node in unique_nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                if future.result():
                    # 添加地理位置信息
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", node['server']):
                        node['city'] = get_city_from_ip(node['server'])
                    else:
                        node['city'] = "未知地区"
                    
                    valid_nodes.append(node)
            except Exception as e:
                print(f"验证节点失败: {node.get('name')} - {str(e)}")
    
    # 按延迟排序
    valid_nodes.sort(key=lambda x: x.get('latency', 10000))
    
    print(f"有效节点数: {len(valid_nodes)}")
    
    # 保存到文件
    with open('nodes.json', 'w') as f:
        json.dump(valid_nodes, f, indent=2)
    
    return valid_nodes

if __name__ == "__main__":
    print("开始获取节点...")
    nodes = fetch_all_sources()
    print(f"成功获取 {len(nodes)} 个有效节点")
