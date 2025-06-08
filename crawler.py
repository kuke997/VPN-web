from sources import fetch_all_sources
import json
import os
import time

def main():
    print("开始爬取所有来源的免费VPN节点...")
    start_time = time.time()
    
    try:
        nodes = fetch_all_sources()
    except Exception as e:
        print(f"爬取过程中发生错误: {e}")
        nodes = []
    
    if not nodes:
        print("⚠️ 未获取到任何节点，尝试使用备份源...")
        # 这里可以添加备份逻辑
        print("无法获取节点，退出。")
        return

    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", "nodes.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start_time
    print(f"✅ 已保存 nodes.json，共 {len(nodes)} 条节点，耗时 {elapsed:.2f} 秒")

if __name__ == "__main__":
    main()
