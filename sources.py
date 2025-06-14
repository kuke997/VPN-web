import requests
import re
import json
import base64
import socket
import time
import random
import yaml
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures

# 更新为更可靠的免费节点源
SOURCES = [
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/ssrsub/ssr/master/ssrsub",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2"
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
    try:
        # 直接加载YAML
        config = yaml.safe_load(content)
        return config.get("proxies", [])
    except:
        # 尝试手动解析
        nodes = []
        proxies_start = content.find("proxies:")
        if proxies_start == -1:
            return []
        
        proxies_content = content[proxies_start:]
        node_pattern = r"- {.*?}\n"
        matches = re.findall(node_pattern, proxies_content, re.DOTALL)
        
        for match in matches:
            try:
                node_data = match.strip()[2:]  # 移除 "- "
                node_dict = {}
                
                for line in node_data.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        elif value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                            
                        node_dict[key] = value
                
                if "name" in node_dict and "server" in node_dict and "port" in node_dict:
                    nodes.append(node_dict)
            except:
                pass
        
        return nodes
    except Exception as e:
        print(f"解析Clash配置失败: {str(e)}")
        return []

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
                
            if line.startswith("vmess://") or line.startswith("ss://"):
                try:
                    if line.startswith("vmess://"):
                        base64_str = line[8:]
                        if len(base64_str) % 4 != 0:
                            base64_str += '=' * (4 - len(base64_str) % 4)
                        decoded = base64.b64decode(base64_str).decode('utf-8')
                        config = json.loads(decoded)
                        
                        node = {
                            "name": config.get("ps", f"vmess-{config.get('add', '')}:{config.get('port', '')}"),
                            "type": "vmess",
                            "server": config.get("add", ""),
                            "port": config.get("port", ""),
                            "uuid": config.get("id", ""),
                            "alterId": config.get("aid", 0),
                            "cipher": config.get("scy", "auto"),
                            "network": config.get("net", "tcp"),
                            "ws-path": config.get("path", "/"),
                            "ws-headers": {"Host": config.get("host", "")},
                            "tls": config.get("tls", "") == "tls",
                            "skip-cert-verify": True,
                            "config": line
                        }
                        nodes.append(node)
                    
                    elif line.startswith("ss://"):
                        base64_str = line[5:].split('#')[0]
                        if len(base64_str) % 4 != 0:
                            base64_str += '=' * (4 - len(base64_str) % 4)
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
                        
                        node = {
                            "name": f"ss-{server}:{port}",
                            "type": "ss",
                            "server": server,
                            "port": port,
                            "cipher": method,
                            "password": password,
                            "udp": True,
                            "config": line
                        }
                        nodes.append(node)
                except:
                    pass
        
        return nodes, "mixed"
    except Exception as e:
        print(f"解析订阅内容失败: {str(e)}")
        return [], "unknown"

def test_node_connectivity(node):
    """测试节点连接性"""
    try:
        # 测试TCP连接
        start_time = time.time()
        sock = socket.create_connection((node["server"], int(node["port"])), timeout=5)
        sock.close()
        return int((time.time() - start_time) * 1000)
    except:
        return None

def fetch_all_sources():
    """从所有源获取并处理节点"""
    all_nodes = []
    
    print("开始获取节点源...")
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
    print("开始验证节点连通性...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(test_node_connectivity, node): node for node in unique_nodes}
        for future in concurrent.futures.as_completed(futures):
            node = futures[future]
            try:
                latency = future.result()
                if latency is not None:
                    node["latency"] = latency
                    valid_nodes.append(node)
                    print(f"节点有效: {node['name']} - 延迟: {latency}ms")
                else:
                    print(f"节点无效: {node['name']}")
            except:
                print(f"验证节点失败: {node.get('name', '未知节点')}")
    
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
        return
    
    # 1. 生成Clash订阅
    clash_config = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": nodes,
        "proxy-groups": [
            {
                "name": "自动选择",
                "type": "url-test",
                "proxies": [node["name"] for node in nodes],
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300
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
    
    with open('clash_subscription.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(clash_config, f, allow_unicode=True)
    
    # 2. 生成Shadowrocket订阅
    shadowrocket_config = ""
    for node in nodes:
        if "config" in node:
            shadowrocket_config += node["config"] + "\n"
    
    # Base64编码
    shadowrocket_base64 = base64.b64encode(shadowrocket_config.encode()).decode()
    with open('shadowrocket_subscription.txt', 'w', encoding='utf-8') as f:
        f.write(shadowrocket_base64)
    
    print("✅ 已生成订阅文件:")
    print("- clash_subscription.yaml (Clash客户端)")
    print("- shadowrocket_subscription.txt (Shadowrocket客户端)")

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
        with open('nodes.json', 'w') as f:
            json.dump([], f)
        print("已创建空的 nodes.json 文件")
    
    print("="*50)
