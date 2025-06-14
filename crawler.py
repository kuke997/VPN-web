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
from datetime import datetime, timezone
from urllib.parse import urlparse
import concurrent.futures
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vpn_crawler.log'),
        logging.StreamHandler()
    ]
)

# 更新为更可靠的免费节点源
SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data2023045.txt",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

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
        # 处理URL安全的Base64
        base64_str = base64_str.replace('-', '+').replace('_', '/')
        
        # 添加必要的填充
        padding = len(base64_str) % 4
        if padding > 0:
            base64_str += '=' * (4 - padding)
        
        return base64.b64decode(base64_str).decode('utf-8')
    except Exception as e:
        logging.warning(f"Base64解码失败: {str(e)}")
        return None

def clean_node_name(name):
    """清洗节点名称"""
    if not name:
        return "未知节点"
    
    # 移除源信息
    name = re.sub(r'github\.com/[^\-]+\-', '', name)
    
    # 移除速度信息
    name = re.sub(r'\d+\.\d+MB/s\|\d+%\|.*', '', name)
    
    # 移除多余符号
    name = re.sub(r'[|\\]', ' ', name)
    
    # 标准化国家/地区名称
    name = re.sub(r'([a-zA-Z]+)\d+', r'\1', name)  # 移除数字后缀
    
    # 提取国家/地区信息
    country_match = re.search(r'(美国|日本|韩国|新加坡|台湾|香港|英国|德国|加拿大|俄罗斯|印度|巴西|澳大利亚|法国|荷兰|瑞士|瑞典|意大利|西班牙|土耳其|南非)', name)
    country = country_match.group(1) if country_match else "未知地区"
    
    # 提取服务商信息
    provider_match = re.search(r'(CloudFlare|Fastly|AWS|Azure|Google Cloud|Akamai|DigitalOcean|Linode|Vultr)', name, re.IGNORECASE)
    provider = provider_match.group(1) if provider_match else "未知服务商"
    
    # 提取节点类型
    type_match = re.search(r'(CDN节点|Anycast节点|中转节点|直连节点|优质线路|普通线路|高速节点)', name)
    node_type = type_match.group(1) if type_match else "节点"
    
    # 构建标准化名称
    return f"[{country}] {provider} - {node_type}"

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
                node_dict["name"] = clean_node_name(node_dict["name"])
                
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
                
                # Shadowsocks节点
                elif node_type == "ss":
                    clash_config.update({
                        "cipher": node_dict.get("cipher", "aes-256-gcm"),
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
            if len(content) > 100 and '://' not in content:
                decoded = base64.b64decode(content).decode('utf-8')
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
                    name = clean_node_name(config.get("ps", config.get("name", f"vmess-{server}:{port}")))
                    
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
                    decoded = safe_base64_decode(base64_str)
                    
                    if not decoded:
                        continue
                    
                    # 获取节点名称
                    name_match = re.search(r'#(.+)$', line)
                    name = clean_node_name(name_match.group(1)) if name_match else f"ss-{line[5:15]}"
                    
                    # 处理不同的SS格式
                    method, password, server, port = "", "", "", ""
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
                    elif ':' in decoded:
                        parts = decoded.split(':')
                        if len(parts) >= 2:
                            server = parts[0]
                            port = parts[1]
                            method = parts[2] if len(parts) > 2 else ""
                            password = parts[3] if len(parts) > 3 else ""
                        else:
                            server, port = "", ""
                    else:
                        server, port = "", ""
                    
                    # 跳过无效节点
                    if not server or not port:
                        continue
                    
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
            except Exception as e:
                logging.error(f"解析节点失败: {str(e)} - {line[:60]}")
        
        logging.info(f"成功解析 {len(nodes)} 个节点")
        return nodes, "mixed"
    except Exception as e:
        logging.error(f"解析订阅内容失败: {str(e)}")
        return [], "unknown"

def test_node_connectivity(node, timeout=3):
    """测试节点连接性"""
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
            
        # 测试TCP连接
        start_time = time.time()
        sock = socket.create_connection((ip, int(port)), timeout=timeout)
        sock.close()
        
        latency = int((time.time() - start_time) * 1000)
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

def generate_clash_config(nodes):
    """生成Clash配置文件"""
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
        if "clash_config" in node:
            config["proxies"].append(node["clash_config"])
            config["proxy-groups"][0]["proxies"].append(node["name"])
    
    return yaml.dump(config, allow_unicode=True, sort_keys=False)

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
    
    # 去重
    unique_nodes = []
    seen_names = set()
    
    for node in all_nodes:
        if node["name"] not in seen_names:
            seen_names.add(node["name"])
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
                if latency is not None and latency < 5000:  # 放宽延迟限制到5秒
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
        
        # 生成Clash配置文件
        if valid_nodes:
            clash_config = generate_clash_config(valid_nodes)
            with open('clash_subscription.yaml', 'w', encoding='utf-8') as f:
                f.write(clash_config)
            logging.info("Clash配置文件已生成")
            
            # 生成Shadowrocket订阅
            shadowrocket_config = "\n".join([node.get("config", "") for node in valid_nodes if "config" in node])
            shadowrocket_base64 = base64.b64encode(shadowrocket_config.encode()).decode()
            with open('shadowrocket_subscription.txt', 'w', encoding='utf-8') as f:
                f.write(shadowrocket_base64)
            logging.info("Shadowrocket订阅文件已生成")
        
    except Exception as e:
        logging.error(f"保存文件失败: {str(e)}")
    
    return valid_nodes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='爬取免费VPN节点')
    parser.add_argument('-o', '--output', default='nodes.json', help='输出文件路径')
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
