import ftplib
import os
import sys
import time

ftp_host = os.getenv("FTP_HOST")
ftp_user = os.getenv("FTP_USER")
ftp_pass = os.getenv("FTP_PASS")

if not all([ftp_host, ftp_user, ftp_pass]):
    print("错误：请先设置环境变量 FTP_HOST、FTP_USER、FTP_PASS")
    sys.exit(1)

LOCAL_UPLOAD_DIR = "website"
FTP_BASE_DIR = "domains/cloakaccess.com/public_html"

# 确保日志目录存在
os.makedirs(os.path.dirname("logs/"), exist_ok=True)

def upload_dir(local_dir, ftp_dir, ftp):
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        ftp_path = f"{ftp_dir}/{item}" if ftp_dir != '.' else item

        if os.path.isdir(local_path):
            print(f"处理目录: {local_path}")
            try:
                # 尝试创建目录
                ftp.mkd(ftp_path)
                print(f"[MKDIR] 创建目录 {ftp_path}")
            except ftplib.error_perm as e:
                if '550' in str(e):
                    # 目录已存在
                    print(f"[INFO] 目录已存在: {ftp_path}")
                else:
                    print(f"[WARN] 创建目录异常: {e}")
                    continue
            
            # 递归上传子目录
            upload_dir(local_path, ftp_path, ftp)
        else:
            # 文件上传
            file_size = os.path.getsize(local_path)
            print(f"准备上传: {local_path} -> {ftp_path} ({file_size} 字节)")
            
            retry_count = 0
            max_retries = 3
            last_error = None
            
            while retry_count < max_retries:
                try:
                    with open(local_path, "rb") as f:
                        # 使用二进制模式上传
                        ftp.storbinary(f"STOR {ftp_path}", f)
                        print(f"[SUCCESS] 上传成功: {ftp_path}")
                        break  # 成功则跳出循环
                except Exception as e:
                    retry_count += 1
                    last_error = e
                    print(f"[ERROR] 上传文件失败 (尝试 {retry_count}/{max_retries}): {e}")
                    time.sleep(2 ** retry_count)  # 指数退避
            
            if retry_count == max_retries:
                print(f"[FATAL] 上传失败: {local_path} -> {ftp_path} (最后错误: {last_error})")
                # 记录错误文件
                with open("logs/upload_errors.log", "a") as log:
                    log.write(f"{time.ctime()} | {local_path} -> {ftp_path} | {last_error}\n")

def main():
    try:
        print(f"连接 FTP 服务器: {ftp_host}")
        ftp = ftplib.FTP(ftp_host, timeout=60)  # 增加超时时间
        ftp.login(ftp_user, ftp_pass)
        print(f"登录成功: {ftp_user}")
        
        # 启用被动模式
        ftp.set_pasv(True)
        
        # 切换到基础目录
        try:
            ftp.cwd(FTP_BASE_DIR)
            print(f"切换到 FTP 目录: {FTP_BASE_DIR}")
        except ftplib.error_perm as e:
            print(f"目录不存在，尝试创建: {FTP_BASE_DIR}")
            # 递归创建目录
            parts = FTP_BASE_DIR.split('/')
            path = ""
            for part in parts:
                if not part:
                    continue
                path += "/" + part
                try:
                    ftp.cwd(path)
                except:
                    try:
                        ftp.mkd(path)
                        ftp.cwd(path)
                    except:
                        print(f"创建目录失败: {path}")
            print(f"创建并切换到目录: {FTP_BASE_DIR}")

        if not os.path.exists(LOCAL_UPLOAD_DIR):
            print(f"本地文件夹 '{LOCAL_UPLOAD_DIR}' 不存在")
            return

        print(f"开始上传目录: {LOCAL_UPLOAD_DIR}")
        upload_dir(LOCAL_UPLOAD_DIR, ".", ftp)

        ftp.quit()
        print("上传完成，FTP连接关闭")
    except Exception as e:
        print(f"发生严重错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
