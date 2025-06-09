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
            import base64
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
    """专门抓取 freefq.com 的节点"""
    print("\n" + "="*50)
    print("开始抓取 freefq.com 免费节点")
    print("="*50)
    
    base_url = "https://freefq.com/"
    session = get_session()
    all_nodes = []
    
    try:
        # 获取首页内容
        html, session = fetch_page(base_url, session)
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找所有文章链接 - 使用更通用的选择器
        article_links = []
        
        # 尝试多种选择器
        selectors = [
            'article a[href]',  # 文章中的链接
            '.post-title a[href]',  # 文章标题链接
            '.entry-title a[href]',  # 另一种标题链接
            'a[href*="/free-"]',  # 包含"/free-"的链接
            'a[href*="/ssr"]',  # 包含"/ssr"的链接
            'a[href*="/v2ray"]'  # 包含"/v2ray"的链接
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for a in links:
                href = a.get('href', '').strip()
                if href:
                    full_url = urljoin(base_url, href)
                    if full_url not in article_links and "freefq.com" in full_url:
                        article_links.append(full_url)
        
        # 如果没有找到文章链接，尝试直接抓取已知页面
        if len(article_links) == 0:
            known_pages = [
                "https://freefq.com/free-ssr/",
                "https://freefq.com/free-v2ray/",
                "https://freefq.com/free-trojan/"
            ]
            article_links.extend(known_pages)
        
        print(f"找到 {len(article_links)} 篇节点文章")
        
        # 处理每篇文章
        for i, article_url in enumerate(article_links):
            print(f"\n处理文章 {i+1}/{len(article_links)}: {article_url}")
            
            try:
                # 获取文章内容
                article_html, session = fetch_page(article_url, session)
                article_soup = BeautifulSoup(article_html, 'html.parser')
                
                # 查找文章正文 - 尝试多种选择器
                content_div = None
                content_selectors = [
                    'div.entry-content',
                    'div.post-content',
                    'div.article-content',
                    'div.content',
                    'div.main-content',
                    'article',
                    'div.post'
                ]
                
                for selector in content_selectors:
                    content_div = article_soup.select_one(selector)
                    if content_div:
                        break
                
                if not content_div:
                    print("⚠️ 未找到文章内容，使用整个页面")
                    content_div = article_soup
                
                # 提取所有可能的订阅链接
                subscription_links = extract_subscription_links(str(content_div), article_url)
                print(f"发现 {len(subscription_links)} 个订阅链接")
                
                # 解析每个订阅链接
                for j, sub_url in enumerate(subscription_links):
                    print(f"  解析订阅 {j+1}/{len(subscription_links)}: {sub_url}")
                    nodes = parse_subscription(sub_url, session)
                    if nodes:
                        all_nodes.extend(nodes)
                        print(f"  添加了 {len(nodes)} 个节点")
                
                # 直接提取文章中的节点信息
                print("尝试直接提取文章中的节点信息...")
                text_content = content_div.get_text()
                
                # 增强节点提取逻辑
                found_nodes = 0
                
                # 1. 提取IP:PORT格式的节点
                ip_port_nodes = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:：\s]+(\d{2,5})', text_content)
                for ip, port in ip_port_nodes:
                    all_nodes.append({
                        "name": f"{ip}:{port}",
                        "type": "unknown",
                        "server": ip,
                        "port": port,
                        "source": article_url
                    })
                found_nodes += len(ip_port_nodes)
                
                # 2. 提取特殊格式节点
                special_nodes = re.findall(r'(vmess|ss|trojan)://[a-zA-Z0-9+/=._\-]+', text_content)
                for node in special_nodes:
                    all_nodes.append({
                        "name": node.split('://')[0].upper() + "节点",
                        "type": node.split('://')[0],
                        "config": node,
                        "source": article_url
                    })
                found_nodes += len(special_nodes)
                
                # 3. 提取Base64编码的节点
                base64_nodes = re.findall(r'[A-Za-z0-9+/=]{30,}', text_content)
                for b64 in base64_nodes:
                    try:
                        import base64
                        decoded = base64.b64decode(b64).decode('utf-8')
                        # 尝试从解码后的内容中提取节点
                        decoded_nodes = parse_subscription_content(decoded, article_url)
                        if decoded_nodes:
                            all_nodes.extend(decoded_nodes)
                            found_nodes += len(decoded_nodes)
                    except:
                        pass
                
                print(f"文章直接提取到 {found_nodes} 个节点")
                
                # 避免请求过快
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ 处理文章失败: {e}")
                continue
    
    except Exception as e:
        print(f"⚠️ 抓取 freefq.com 失败: {e}")
    
    print(f"\n从 freefq.com 获取到 {len(all_nodes)} 个节点")
    return all_nodes

def fetch_reliable_sources():
    """获取可靠的订阅源"""
    print("\n" + "="*50)
    print("获取可靠订阅源")
    print("="*50)
    
    session = get_session()
    all_nodes = []
    
    # 更新可靠的订阅源列表
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
            "name": "free-yaml",
            "url": "https://raw.githubusercontent.com/freefq/free/master/v2"
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
