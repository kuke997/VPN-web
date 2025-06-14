import requests
import re
import json
import base64
import socket
import time
import os
import random
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
        nodes = []
        # 解析proxies部分
        proxies_start = content.find("proxies:")
        if proxies_start == -1:
            return []
        
        proxies_content = content[proxies_start:]
        # 使用正则表达式匹配每个节点
        node_pattern = r"- {.*?}\n"
        matches = re.findall(node_pattern, proxies_content, re.DOTALL)
        
        for match in matches:
            try:
                # 提取节点信息
                node_data = match.strip()[2:]  # 移除 "- "
                node_dict = {}
                
                # 解析YAML格式的节点信息
                for line in node_data.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 处理值中的特殊字符
                        if value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        elif value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                            
                        node_dict[key] = value
                
                if "name" in node_dict and "server" in node_dict and "port" in node_dict:
                    # 生成节点配置
                    node_type = node_dict.get("type", "unknown")
                    config = ""
                    
                    if node_type.lower() == "vmess":
                        vmess_config = {
                            "v": "2",
                            "ps": node_dict["name"],
                            "add": node_dict["server"],
                            "port": node_dict["port"],
                            "id": node_dict.get("uuid", ""),
                            "aid": node_dict.get("alterId", "0"),
                            "scy": node_dict.get("cipher", "auto"),
                            "net": node_dict.get("network", "tcp"),
                            "type": node_dict.get("type", "none"),
                            "host": node_dict.get("servername", ""),
                            "path": node_dict.get("ws-path", ""),
                            "tls": node_dict.get("tls", "")
                        }
                        config = "vmess://" + base64.b64encode(json.dumps(vmess_config).encode()).decode()
                    
                    elif node_type.lower() == "ss":
                        ss_config = f"{node_dict.get('cipher', 'aes-256-gcm')}:{node_dict.get('password', '')}@{node_dict['server']}:{node_dict['port']}"
                        config = "ss://" + base64.b64encode(ss_config.encode()).decode()
                    
                    if config:
                        nodes.append({
                            "id": str(random.randint(10000000, 99999999)),
                            "type": node_type,
                            "server": node_dict["server"],
                            "port": node_dict["port"],
                            "name": node_dict["name"],
                            "config": config,
                            "source": url
                        })
            except Exception as e:
                print(f"解析节点失败: {str(e)}")
        
        return nodes
    except Exception as e:
        print(f"解析Clash配置失败: {str(e)}")
        return []

def parse_subscription_content(content, source_url):
    """解析订阅内容"""
    try:
        # 尝试解码Base64
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            content = decoded
        except:
            pass
        
        # 检查是否是Clash配置
        if "proxies:" in content:
            return parse_clash_config(content)
        
        # 尝试解析为节点列表
        nodes = []
        lines = content.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("vmess://") or line.startswith("ss://"):
                try:
                    if line.startswith("vmess://"):
                        # 解析VMess
                        base64_str = line[8:]
                        if len(base64_str) % 4 != 0:
                            base64_str += '=' * (4 - len(base64_str) % 4)
                        decoded = base64.b64decode(base64_str).decode('utf-8')
                        config = json.loads(decoded)
                        
                        node = {
                            "id": str(random.randint(10000000, 99999999)),
                            "type": "vmess",
                            "server": config.get("add", ""),
                            "port": config.get("port", ""),
                            "name": config.get("ps", f"vmess-{config.get('add', '')}:{config.get('port', '')}"),
                            "config": line,
                            "source": source_url
                        }
                        nodes.append(node)
                    
                    elif line.startswith("ss://"):
                        # 解析Shadowsocks
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
                            "id": str(random.randint(10000000, 99999999)),
                            "type": "ss",
                            "server": server,
                            "port": port,
                            "name": f"ss-{server}:{port}",
                            "config": line,
                            "source": source_url
                        }
                        nodes.append(node)
                except Exception as e:
                    print(f"解析节点失败: {str(e)} - {line[:60]}")
        
        return nodes
    except Exception as e:
        print(f"解析订阅内容失败: {str(e)}")
        return []

def test_node_connectivity(node):
    """测试节点连接性 - 更全面的测试"""
    try:
        # 测试TCP连接
        start_time = time.time()
        sock = socket.create_connection((node["server"], int(node["port"])), timeout=5)
        sock.close()
        latency = int((time.time() - start_time) * 1000)
        
        # 简单的HTTP测试（可选）
        # 实际应用中可能需要更复杂的代理测试
        return latency
    except Exception:
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
                nodes = parse_subscription_content(content, url)
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
        if node["config"] not in seen_configs:
            seen_configs.add(node["config"])
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
                    node["last_checked"] = datetime.utcnow().isoformat() + "Z"
                    node["city"] = "未知地区"
                    valid_nodes.append(node)
                    print(f"节点有效: {node['name']} - 延迟: {latency}ms")
                else:
                    print(f"节点无效: {node['name']}")
            except Exception as e:
                print(f"验证节点失败: {node.get('name')} - {str(e)}")
    
    # 按延迟排序
    valid_nodes.sort(key=lambda x: x.get("latency", 10000))
    
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
        
        # 生成Clash订阅文件
        generate_clash_config(nodes)
    else:
        print("❌ 未获取到任何有效节点")
        # 创建空文件防止前端出错
        with open('nodes.json', 'w') as f:
            json.dump([], f)
        print("已创建空的 nodes.json 文件")
    
    print("="*50)

def generate_clash_config(nodes):
    """生成Clash配置文件"""
    if not nodes:
        return
    
    clash_config = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": "127.0.0.1:9090",
        "proxies": [],
        "proxy-groups": [
            {
                "name": "自动选择",
                "type": "url-test",
                "proxies": [],
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
    
    for node in nodes:
        if node["type"].lower() == "vmess":
            try:
                # 解析VMess配置
                base64_str = node["config"][8:]
                if len(base64_str) % 4 != 0:
                    base64_str += '=' * (4 - len(base64_str) % 4)
                decoded = base64.b64decode(base64_str).decode('utf-8')
                vmess_config = json.loads(decoded)
                
                clash_proxy = {
                    "name": node["name"],
                    "type": "vmess",
                    "server": node["server"],
                    "port": int(node["port"]),
                    "uuid": vmess_config.get("id", ""),
                    "alterId": int(vmess_config.get("aid", 0)),
                    "cipher": vmess_config.get("scy", "auto"),
                    "udp": True
                }
                
                # 添加网络类型相关设置
                network = vmess_config.get("net", "tcp")
                if network == "ws":
                    clash_proxy["network"] = "ws"
                    clash_proxy["ws-path"] = vmess_config.get("path", "/")
                    clash_proxy["ws-headers"] = {"Host": vmess_config.get("host", "")}
                
                clash_config["proxies"].append(clash_proxy)
                clash_config["proxy-groups"][0]["proxies"].append(node["name"])
                
            except Exception as e:
                print(f"生成Clash配置失败: {node['name']} - {str(e)}")
        
        elif node["type"].lower() == "ss":
            try:
                base64_str = node["config"][5:].split('#')[0]
                if len(base64_str) % 4 != 0:
                    base64_str += '=' * (4 - len(base64_str) % 4)
                decoded = base64.b64decode(base64_str).decode('utf-8')
                
                if '@' in decoded:
                    method_password, server_port = decoded.split('@', 1)
                    method, password = method_password.split(':', 1)
                    server, port = server_port.split(':', 1)
                else:
                    method, password, server, port = "", "", "", ""
                
                clash_proxy = {
                    "name": node["name"],
                    "type": "ss",
                    "server": server,
                    "port": int(port),
                    "cipher": method,
                    "password": password,
                    "udp": True
                }
                
                clash_config["proxies"].append(clash_proxy)
                clash_config["proxy-groups"][0]["proxies"].append(node["name"])
                
            except Exception as e:
                print(f"生成Clash配置失败: {node['name']} - {str(e)}")
    
    # 保存Clash配置文件
    with open('clash_config.yaml', 'w', encoding='utf-8') as f:
        f.write("port: 7890\n")
        f.write("socks-port: 7891\n")
        f.write("allow-lan: true\n")
        f.write("mode: Rule\n")
        f.write("log-level: info\n")
        f.write("external-controller: 127.0.0.1:9090\n\n")
        
        f.write("proxies:\n")
        for proxy in clash_config["proxies"]:
            f.write(f"  - name: {proxy['name']}\n")
            f.write(f"    type: {proxy['type']}\n")
            f.write(f"    server: {proxy['server']}\n")
            f.write(f"    port: {proxy['port']}\n")
            
            if proxy["type"] == "vmess":
                f.write(f"    uuid: {proxy['uuid']}\n")
                f.write(f"    alterId: {proxy['alterId']}\n")
                f.write(f"    cipher: {proxy['cipher']}\n")
                if "network" in proxy:
                    f.write(f"    network: {proxy['network']}\n")
                    if proxy["network"] == "ws":
                        f.write(f"    ws-path: {proxy.get('ws-path', '/')}\n")
                        f.write("    ws-headers:\n")
                        f.write(f"      Host: {proxy.get('ws-headers', {}).get('Host', '')}\n")
            
            elif proxy["type"] == "ss":
                f.write(f"    cipher: {proxy['cipher']}\n")
                f.write(f"    password: {proxy['password']}\n")
        
        f.write("\nproxy-groups:\n")
        for group in clash_config["proxy-groups"]:
            f.write(f"  - name: {group['name']}\n")
            f.write(f"    type: {group['type']}\n")
            f.write(f"    proxies: {group['proxies']}\n")
            f.write(f"    url: {group['url']}\n")
            f.write(f"    interval: {group['interval']}\n")
        
        f.write("\nrules:\n")
        for rule in clash_config["rules"]:
            f.write(f"  - {rule}\n")
    
    print("✅ 已生成Clash配置文件: clash_config.yaml")
