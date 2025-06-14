import requests
import re
import json
import base64
import socket
import time
import random
import uuid
import os
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures

# 更新为更可靠的免费节点源
SOURCES = [
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ssrsub",
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
            return response.text
        else:
            print(f"源 {url} 返回状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"获取源 {url} 失败: {str(e)}")
        return None

def parse_clash_config(content):
    """解析Clash配置文件"""
    nodes = []
    
    # 查找proxies部分
    proxies_start = content.find("proxies:")
    if proxies_start == -1:
        return nodes
        
    proxies_content = content[proxies_start:]
    
    # 使用正则表达式匹配每个节点
    node_pattern = r"- {.*?}\n"
    matches = re.findall(node_pattern, proxies_content, re.DOTALL)
    
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
                # 生成节点配置字符串
                node_type = node_dict.get("type", "unknown").lower()
                config = ""
                
                # VMess节点
                if node_type == "vmess":
                    vmess_config = {
                        "v": "2",
                        "ps": node_dict["name"],
                        "add": node_dict["server"],
                        "port": node_dict["port"],
                        "id": node_dict.get("uuid", node_dict.get("password", "")),
                        "aid": node_dict.get("alterId", "0"),
                        "scy": node_dict.get("cipher", "auto"),
                        "net": node_dict.get("network", "tcp"),
                        "type": node_dict.get("type", "none"),
                        "host": node_dict.get("servername", node_dict.get("host", "")),
                        "path": node_dict.get("ws-path", node_dict.get("path", "")),
                        "tls": node_dict.get("tls", "")
                    }
                    json_str = json.dumps(vmess_config, ensure_ascii=False)
                    config = "vmess://" + base64.b64encode(json_str.encode()).decode()
                
                # Shadowsocks节点
                elif node_type == "ss":
                    password = node_dict.get("password", "")
                    method = node_dict.get("cipher", "aes-256-gcm")
                    server = node_dict["server"]
                    port = node_dict["port"]
                    ss_config = f"{method}:{password}@{server}:{port}"
                    config = "ss://" + base64.b64encode(ss_config.encode()).decode()
                
                # 如果有有效的配置，添加到节点列表
                if config:
                    nodes.append({
                        "id": str(uuid.uuid4()),
                        "type": node_type,
                        "server": node_dict["server"],
                        "port": node_dict["port"],
                        "name": node_dict["name"],
                        "config": config,
                        "source": "clash_config"
                    })
        except Exception as e:
            print(f"解析Clash节点失败: {str(e)}")
    
    return nodes

def parse_subscription_content(content, source_url):
    """解析订阅内容"""
    try:
        # 尝试Base64解码
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            content = decoded
        except:
            pass
        
        # 检查是否是Clash配置
        if "proxies:" in content:
            return parse_clash_config(content), "clash"
        
        # 解析为节点列表
        nodes = []
        lines = content.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                # VMess节点
                if line.startswith("vmess://"):
                    # 解析VMess
                    base64_str = line[8:]
                    if len(base64_str) % 4 != 0:
                        base64_str += '=' * (4 - len(base64_str) % 4)
                    
                    # 处理URL安全的Base64
                    base64_str = base64_str.replace('-', '+').replace('_', '/')
                    try:
                        decoded = base64.b64decode(base64_str).decode('utf-8')
                    except:
                        # 如果仍然失败，尝试直接解码
                        decoded = base64.b64decode(base64_str + '=' * (-len(base64_str) % 4)).decode('utf-8')
                    
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
                    
                    server = config.get("add", config.get("host", config.get("address", "")))
                    port = config.get("port", "443")
                    name = config.get("ps", config.get("name", f"vmess-{server}:{port}"))
                    
                    node = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "type": "vmess",
                        "server": server,
                        "port": port,
                        "config": line,
                        "source": source_url
                    }
                    nodes.append(node)
                
                # Shadowsocks节点
                elif line.startswith("ss://"):
                    # 解析Shadowsocks
                    base64_str = line[5:].split('#')[0]
                    if len(base64_str) % 4 != 0:
                        base64_str += '=' * (4 - len(base64_str) % 4)
                    
                    # 处理URL安全的Base64
                    base64_str = base64_str.replace('-', '+').replace('_', '/')
                    try:
                        decoded = base64.b64decode(base64_str).decode('utf-8')
                    except:
                        decoded = base64.b64decode(base64_str + '=' * (-len(base64_str) % 4)).decode('utf-8')
                    
                    if '@' in decoded:
                        method_password, server_port = decoded.split('@', 1)
                        if ':' in method_password:
                            method, password = method_password.split(':', 1)
                        else:
                            method, password = method_password, ""
                        
                        if ':' in server_port:
                            server, port = server_port.split(':', 1)
                        else:
                            server, port = server_port, "443"
                    else:
                        method, password, server, port = "", "", "", ""
                    
                    # 获取节点名称
                    name_match = re.search(r'#(.+)$', line)
                    name = name_match.group(1) if name_match else f"ss-{server}:{port}"
                    
                    node = {
                        "id": str(uuid.uuid4()),
                        "name": name,
                        "type": "ss",
                        "server": server,
                        "port": port,
                        "config": line,
                        "source": source_url
                    }
                    nodes.append(node)
            except Exception as e:
                print(f"解析节点失败: {str(e)} - {line[:60]}")
        
        return nodes, "mixed"
    except Exception as e:
        print(f"解析订阅内容失败: {str(e)}")
        return [], "unknown"

def test_node_connectivity(node):
    """测试节点连接性 - 更严格的测试"""
    server = node.get("server", "")
    port = str(node.get("port", ""))
    
    if not server or not port or not port.isdigit():
        return None
    
    try:
        # 解析域名
        if not re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", server):
            try:
                server_ip = socket.gethostbyname(server)
            except socket.gaierror:
                return None
        else:
            server_ip = server
        
        # 测试TCP连接
        start_time = time.time()
        sock = socket.create_connection((server_ip, int(port)), timeout=5)
        
        # 发送测试数据
        if node["type"] == "ss":
            # Shadowsocks测试数据
            sock.send(b"\x05\x01\x00")
            response = sock.recv(2)
            if response != b"\x05\x00":
                return None
        
        sock.close()
        return int((time.time() - start_time) * 1000)
    except Exception as e:
        return None

def fetch_all_sources():
    """从所有源获取并处理节点"""
    all_nodes = []
    
    print("="*50)
    print("开始获取节点源...")
    print("="*50)
    
    # 获取所有源数据
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_source, url): url for url in SOURCES}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            content = future.result()
            if content:
                print(f"成功获取源: {url}")
                nodes, source_type = parse_subscription_content(content, url)
                print(f"从该源解析出 {len(nodes)} 个节点")
                all_nodes.extend(nodes)
            else:
                print(f"无法获取源: {url}")
    
    print(f"初始节点数: {len(all_nodes)}")
    
    if not all_nodes:
        print("⚠️ 未获取到任何节点，退出。")
        return []
    
    # 去重
    unique_nodes = []
    seen_configs = set()
    
    for node in all_nodes:
        config = node.get("config", "")
        if config and config not in seen_configs:
            seen_configs.add(config)
            unique_nodes.append(node)
    
    print(f"去重后节点数: {len(unique_nodes)}")
    
    # 验证节点有效性
    valid_nodes = []
    print("="*50)
    print("开始验证节点连通性...")
    print("="*50)
    
    # 限制最大并发数
    max_workers = min(20, len(unique_nodes))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_node_connectivity, node): node for node in unique_nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                latency = future.result()
                if latency is not None:
                    node["latency"] = latency
                    node["last_checked"] = datetime.utcnow().isoformat() + "Z"
                    valid_nodes.append(node)
                    print(f"✅ 节点有效: {node['name']} - 延迟: {latency}ms")
                else:
                    print(f"❌ 节点无效: {node['name']}")
            except Exception as e:
                print(f"⚠️ 验证节点失败: {node.get('name', '未知节点')} - {str(e)}")
    
    print(f"有效节点数: {len(valid_nodes)}")
    
    # 保存到文件
    with open('nodes.json', 'w', encoding='utf-8') as f:
        json.dump(valid_nodes, f, indent=2, ensure_ascii=False)
    
    # 生成订阅文件
    generate_subscriptions(valid_nodes)
    
    return valid_nodes

def generate_subscriptions(nodes):
    """生成Clash和Shadowrocket订阅"""
    if not nodes:
        print("⚠️ 没有有效节点，跳过订阅生成")
        return
    
    print("="*50)
    print("生成订阅文件中...")
    print("="*50)
    
    # 1. 生成Clash订阅
    clash_config = """port: 7890
socks-port: 7891
allow-lan: true
mode: Rule
log-level: info
external-controller: 127.0.0.1:9090

proxies:
"""

    # 添加节点
    for node in nodes:
        if node["type"] == "vmess":
            try:
                # 解析VMess配置
                base64_str = node["config"][8:]
                if len(base64_str) % 4 != 0:
                    base64_str += '=' * (4 - len(base64_str) % 4)
                
                # 处理URL安全的Base64
                base64_str = base64_str.replace('-', '+').replace('_', '/')
                decoded = base64.b64decode(base64_str).decode('utf-8')
                vmess_config = json.loads(decoded)
                
                clash_config += f"  - name: \"{node['name']}\"\n"
                clash_config += f"    type: vmess\n"
                clash_config += f"    server: {node['server']}\n"
                clash_config += f"    port: {node['port']}\n"
                clash_config += f"    uuid: {vmess_config.get('id', '')}\n"
                clash_config += f"    alterId: {vmess_config.get('aid', 0)}\n"
                clash_config += f"    cipher: {vmess_config.get('scy', 'auto')}\n"
                
                # 添加网络类型相关设置
                network = vmess_config.get("net", "tcp")
                if network == "ws":
                    clash_config += f"    network: ws\n"
                    clash_config += f"    ws-path: \"{vmess_config.get('path', '/')}\"\n"
                    clash_config += f"    ws-headers:\n"
                    clash_config += f"      Host: \"{vmess_config.get('host', '')}\"\n"
                
                if vmess_config.get("tls") == "tls":
                    clash_config += "    tls: true\n"
                
                clash_config += "    udp: true\n\n"
                
            except Exception as e:
                print(f"生成Clash配置失败: {node['name']} - {str(e)}")
        
        elif node["type"] == "ss":
            try:
                base64_str = node["config"][5:].split('#')[0]
                if len(base64_str) % 4 != 0:
                    base64_str += '=' * (4 - len(base64_str) % 4)
                
                # 处理URL安全的Base64
                base64_str = base64.b64encode(base64.b64decode(base64_str)).decode()  # 标准化base64
                decoded = base64.b64decode(base64_str).decode('utf-8')
                
                if '@' in decoded:
                    method_password, server_port = decoded.split('@', 1)
                    if ':' in method_password:
                        method, password = method_password.split(':', 1)
                    else:
                        method, password = method_password, ""
                    
                    if ':' in server_port:
                        server, port = server_port.split(':', 1)
                    else:
                        server, port = server_port, "443"
                else:
                    method, password, server, port = "", "", "", ""
                
                clash_config += f"  - name: \"{node['name']}\"\n"
                clash_config += f"    type: ss\n"
                clash_config += f"    server: {server}\n"
                clash_config += f"    port: {port}\n"
                clash_config += f"    cipher: {method}\n"
                clash_config += f"    password: \"{password}\"\n"
                clash_config += "    udp: true\n\n"
                
            except Exception as e:
                print(f"生成Clash配置失败: {node['name']} - {str(e)}")
    
    # 添加代理组和规则
    clash_config += """
proxy-groups:
  - name: 自动选择
    type: url-test
    proxies:
"""
    
    for node in nodes:
        clash_config += f"      - \"{node['name']}\"\n"
    
    clash_config += """    url: http://www.gstatic.com/generate_204
    interval: 300

rules:
  - DOMAIN-SUFFIX,google.com,自动选择
  - DOMAIN-KEYWORD,github,自动选择
  - IP-CIDR,91.108.56.0/22,自动选择
  - GEOIP,CN,DIRECT
  - MATCH,自动选择
"""
    
    # 保存Clash配置文件
    with open('clash_subscription.yaml', 'w', encoding='utf-8') as f:
        f.write(clash_config)
    
    # 2. 生成Shadowrocket订阅
    shadowrocket_config = ""
    for node in nodes:
        shadowrocket_config += node["config"] + "\n"
    
    # Base64编码
    shadowrocket_base64 = base64.b64encode(shadowrocket_config.encode()).decode()
    with open('shadowrocket_subscription.txt', 'w', encoding='utf-8') as f:
        f.write(shadowrocket_base64)
    
    print("✅ 订阅文件生成完成:")
    print(f"- Clash订阅: clash_subscription.yaml ({len(nodes)}个节点)")
    print(f"- Shadowrocket订阅: shadowrocket_subscription.txt ({len(nodes)}个节点)")

if __name__ == "__main__":
    print("="*50)
    print("开始爬取所有来源的免费VPN节点...")
    print("="*50)
    
    start_time = time.time()
    
    try:
        nodes = fetch_all_sources()
    except Exception as e:
        print(f"爬取过程中发生错误: {str(e)}")
        nodes = []
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*50)
    if nodes:
        print(f"✅ 成功获取 {len(nodes)} 个有效节点 (耗时: {elapsed_time:.2f}秒)")
        print("结果已保存到 nodes.json")
    else:
        print("❌ 未获取到任何有效节点")
        # 创建空文件防止前端出错
        with open('nodes.json', 'w') as f:
            json.dump([], f)
        print("已创建空的 nodes.json 文件")
    
    # 确保订阅文件存在
    if not os.path.exists('clash_subscription.yaml'):
        with open('clash_subscription.yaml', 'w') as f:
            f.write("# 没有可用节点")
    
    if not os.path.exists('shadowrocket_subscription.txt'):
        with open('shadowrocket_subscription.txt', 'w') as f:
            f.write("")
    
    print("="*50)
