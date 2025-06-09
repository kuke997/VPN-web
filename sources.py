import requests
import re
import yaml
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import base64

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# 配置设置
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0"
}

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": get_random_user_agent()
    })
    session.headers.update(HEADERS)
    
    # 添加重试逻辑
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def fetch_page(url, session=None, verify_ssl=False):
    """获取页面内容，带重试机制"""
    if not session:
        session = get_session()
    
    for attempt in range(3):
        try:
            response = session.get(url, timeout=15, verify=verify_ssl)
            response.raise_for_status()
            
            # 检查是否被重定向到验证页面
            if "just a moment" in response.text.lower() or "cloudflare" in response.text.lower():
                print(f"⚠️ 检测到Cloudflare防护，尝试绕过... (尝试 {attempt+1}/3)")
                time.sleep(2 + attempt * 2)  # 逐渐增加等待时间
                session = get_session()  # 创建新的session
                continue
                
            return response.text, session
        except Exception as e:
            print(f"请求失败 (尝试 {attempt+1}/3): {e}")
            time.sleep(1)
    
    raise Exception(f"无法获取页面: {url}")

def extract_subscription_links(html, base_url):
    """从HTML中提取订阅链接"""
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    
    # 查找所有可能的链接元素
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href:
            full_url = urljoin(base_url, href)
            # 匹配常见的订阅文件扩展名
            if re.search(r'\.(yaml|yml|txt|conf|ini|v2ray|ssr?|sub|list)$', full_url, re.I):
                links.append(full_url)
    
    # 额外检查文本内容中的链接
    text_links = re.findall(r'https?://[^\s"\'<>]+?\.(?:yaml|yml|txt|conf|ini|v2ray|ssr?|sub|list)', html, re.I)
    for link in text_links:
        full_url = urljoin(base_url, link)
        links.append(full_url)
    
    # 去重并返回
    return list(set(links))

def parse_subscription_content(content, source_url):
    """解析订阅内容文本 - 增强解析能力"""
    nodes = []
    
    # 1. 解析YAML格式内容
    try:
        data = yaml.safe_load(content)
        if data and isinstance(data, dict) and data.get('proxies'):
            for proxy in data['proxies']:
                nodes.append({
                    "name": proxy.get('name', 'Unknown'),
                    "type": proxy.get('type', 'Unknown'),
                    "server": proxy.get('server', 'Unknown'),
                    "port": proxy.get('port', 'Unknown'),
                    "source": source_url
                })
    except:
        pass
    
    # 2. 解析各种协议节点
    # VMess格式: vmess://...
    vmess_matches = re.findall(r'vmess://[a-zA-Z0-9+/=]+', content)
    for match in vmess_matches:
        nodes.append({
            "name": "VMess节点",
            "type": "vmess",
            "config": match,
            "source": source_url
        })
    
    # SS格式: ss://...
    ss_matches = re.findall(r'ss://[a-zA-Z0-9+/=]+', content)
    for match in ss_matches:
        nodes.append({
            "name": "Shadowsocks节点",
            "type": "ss",
            "config": match,
            "source": source_url
        })
    
    # Trojan格式: trojan://...
    trojan_matches = re.findall(r'trojan://[a-zA-Z0-9+/=]+', content)
    for match in trojan_matches:
        nodes.append({
            "name": "Trojan节点",
            "type": "trojan",
            "config": match,
            "source": source_url
        })
    
    # 传统IP:PORT格式
    ip_port_matches = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})', content)
    for ip, port in ip_port_matches:
        nodes.append({
            "name": f"{ip}:{port}",
            "type": "unknown",
            "server": ip,
            "port": port,
            "source": source_url
        })
    
    return nodes

def parse_subscription(url, session=None):
    """解析订阅链接内容"""
    if not session:
        session = get_session()
    
    print(f"解析订阅: {url}")
    
    try:
        # 获取订阅内容 - 对于非GitHub链接禁用SSL验证
        verify_ssl = "github" in url  # 仅对GitHub链接启用SSL验证
        content, _ = fetch_page(url, session, verify_ssl=verify_ssl)
        
        # 尝试解析为YAML
        try:
            data = yaml.safe_load(content)
            if data and isinstance(data, dict) and data.get('proxies'):
                nodes = []
                for proxy in data['proxies']:
                    nodes.append({
                        "name": proxy.get('name', 'Unknown'),
                        "type": proxy.get('type', 'Unknown'),
                        "server": proxy.get('server', 'Unknown'),
                        "port": proxy.get('port', 'Unknown'),
                        "source": url
                    })
                print(f"✅ 从YAML订阅解析出 {len(nodes)} 个节点")
                return nodes
        except yaml.YAMLError:
            pass
        
        # 尝试解析为纯文本节点列表
        nodes = []
        
        # 1. 尝试Base64解码
        try:
            # 检查内容是否是Base64编码
            if len(content) > 100 and '=' in content:
                decoded = base64.b64decode(content).decode('utf-8')
                decoded_nodes = parse_subscription_content(decoded, url)
                if decoded_nodes:
                    nodes.extend(decoded_nodes)
                    print(f"✅ 从Base64解码内容解析出 {len(decoded_nodes)} 个节点")
        except Exception as e:
            # 如果Base64解码失败，继续尝试其他方式
            pass
        
        # 2. 如果Base64解码没有获取到节点，则直接解析内容
        if not nodes:
            # 调用通用解析函数
            nodes = parse_subscription_content(content, url)
        
        print(f"✅ 从文本订阅解析出 {len(nodes)} 个节点")
        return nodes
        
    except Exception as e:
        print(f"⚠️ 解析订阅失败: {e}")
        return []

def crawl_freefq():
    """专门抓取 freefq.com 的节点 - 使用API替代"""
    print("\n" + "="*50)
    print("开始抓取 freefq.com 免费节点")
    print("="*50)
    
    session = get_session()
    all_nodes = []
    
    try:
        # 使用freefq的GitHub API获取节点
        api_url = "https://api.github.com/repos/freefq/free/contents/v2"
        content, _ = fetch_page(api_url, session, verify_ssl=True)
        
        # 解析API响应
        files = json.loads(content)
        for file in files:
            if file['name'].endswith('.txt'):
                file_url = file['download_url']
                print(f"处理文件: {file['name']}")
                
                # 获取文件内容
                file_content, _ = fetch_page(file_url, session)
                
                # 解析节点
                nodes = parse_subscription_content(file_content, file_url)
                if nodes:
                    all_nodes.extend(nodes)
                    print(f"✅ 从 {file['name']} 解析出 {len(nodes)} 个节点")
        
        print(f"\n从 freefq.com 获取到 {len(all_nodes)} 个节点")
        return all_nodes
        
    except Exception as e:
        print(f"⚠️ 抓取 freefq.com 失败: {e}")
        return []

def fetch_reliable_sources():
    """获取可靠的订阅源"""
    print("\n" + "="*50)
    print("获取可靠订阅源")
    print("="*50)
    
    session = get_session()
    all_nodes = []
    
    # 更新可靠的订阅源列表 - 使用当前有效的源
    reliable_sources = [
        {
            "name": "freefq-github",
            "url": "https://raw.githubusercontent.com/freefq/free/master/v2"
        },
        {
            "name": "v2raydy-vless",
            "url": "https://raw.githubusercontent.com/v2raydy/v2ray/main/sub/vless.yml"
        },
        {
            "name": "alanbobs999",
            "url": "https://raw.githubusercontent.com/alanbobs999/TopFreeProxies/master/sub/sub_merge.yaml"
        },
        {
            "name": "pojiedi",
            "url": "https://raw.githubusercontent.com/pojiedi/pojiedi.github.io/master/-static-files-/clash/config.yaml"
        },
        {
            "name": "clashnode-archive",
            "url": "https://web.archive.org/web/202310/https://clashnode.com/wp-content/uploads/2023/08/20230815.yaml"
        },
        {
            "name": "Leon406-All",
            "url": "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/all_base64.txt"
        },
        {
            "name": "FreeNode",
            "url": "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/clash.yml"
        }
    ]
    
    for source in reliable_sources:
        print(f"\n处理订阅源: {source['name']} ({source['url']})")
        try:
            nodes = parse_subscription(source['url'], session)
            if nodes:
                all_nodes.extend(nodes)
                print(f"✅ 添加了 {len(nodes)} 个节点")
            else:
                print("⚠️ 未解析出节点")
        except Exception as e:
            print(f"⚠️ 处理订阅源失败: {e}")
    
    print(f"\n从可靠订阅源获取到 {len(all_nodes)} 个节点")
    return all_nodes

def fetch_all_sources():
    """获取所有来源的节点"""
    print("开始获取所有来源的免费VPN节点...")
    
    # 获取 freefq.com 的节点
    freefq_nodes = crawl_freefq()
    
    # 获取可靠源的节点
    reliable_nodes = fetch_reliable_sources()
    
    # 合并所有节点
    all_nodes = freefq_nodes + reliable_nodes
    
    # 去重
    unique_nodes = []
    seen = set()
    for node in all_nodes:
        # 使用配置或服务器+端口作为唯一标识
        identifier = node.get('config', None) or f"{node.get('server', '')}:{node.get('port', '')}"
        if identifier and identifier not in seen:
            seen.add(identifier)
            unique_nodes.append(node)
    
    print("\n" + "="*50)
    print("最终结果统计")
    print("="*50)
    print(f"总节点数: {len(all_nodes)}")
    print(f"去重后节点数: {len(unique_nodes)}")
    
    # 按类型统计
    type_count = {}
    for node in unique_nodes:
        node_type = node.get('type', 'unknown')
        type_count[node_type] = type_count.get(node_type, 0) + 1
    
    print("\n节点类型分布:")
    for t, count in type_count.items():
        print(f"{t.upper()}: {count} 个")
    
    return unique_nodes

def save_nodes(nodes, filename="vpn_nodes.txt"):
    """保存节点到文件"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("免费VPN节点列表\n")
        f.write("=" * 50 + "\n\n")
        
        for i, node in enumerate(nodes, 1):
            f.write(f"节点 #{i}\n")
            f.write(f"来源: {node.get('source', '未知')}\n")
            f.write(f"名称: {node.get('name', '未知')}\n")
            f.write(f"类型: {node.get('type', '未知')}\n")
            
            if 'server' in node and 'port' in node:
                f.write(f"地址: {node['server']}:{node['port']}\n")
            elif 'config' in node:
                f.write(f"配置: {node['config']}\n")
            
            f.write("-" * 50 + "\n")
    
    print(f"\n已保存 {len(nodes)} 个节点到 {filename}")

if __name__ == "__main__":
    # 当直接运行此脚本时
    nodes = fetch_all_sources()
    save_nodes(nodes)
    print("\n抓取完成!")
