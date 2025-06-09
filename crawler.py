from sources import fetch_all_sources
import json
import os
import time
import hashlib
import sys

def main():
    print("开始爬取所有来源的免费VPN节点...")
    start_time = time.time()
    
    try:
        nodes = fetch_all_sources()
    except Exception as e:
        print(f"爬取过程中发生错误: {e}")
        nodes = []
    
    if not nodes:
        print("⚠️ 未获取到任何节点，退出。")
        sys.exit(1)

    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", "nodes.json")
    
    # 保存前确保数据有效
    if not isinstance(nodes, list):
        print(f"⚠️ 节点数据格式错误: {type(nodes)}")
        nodes = []
    
    # 保存节点数据
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    
    # 检查文件是否成功写入
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        print(f"✅ 已保存 nodes.json，文件大小: {file_size} 字节")
        
        # 计算MD5校验和
        with open(output_path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        print(f"文件MD5校验和: {md5}")
        
        # 检查文件是否为空
        if file_size == 0:
            print("⚠️ 警告: 节点文件为空，可能有配置问题")
            sys.exit(1)
    else:
        print("⚠️ 文件保存失败: nodes.json 未创建")
        sys.exit(1)
    
    elapsed = time.time() - start_time
    print(f"✅ 共 {len(nodes)} 条节点，耗时 {elapsed:.2f} 秒")

if __name__ == "__main__":
    main()
