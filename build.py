import os
import json
import zipfile
import shutil

# --- 配置区 ---
# 定义需要包含在 Release ZIP 中的文件和文件夹
INCLUDE_FILES = ['main.py', 'plugin.json', 'LICENSE']
INCLUDE_DIRS = ['Images', 'lib']
# 定义输出目录
OUTPUT_DIR = 'dist'

def build():
    # 1. 读取 plugin.json 获取插件信息
    if not os.path.exists('plugin.json'):
        print("错误: 未找到 plugin.json，请确保在插件根目录运行此脚本。")
        return

    with open('plugin.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)
        plugin_name = meta.get('Name', 'Plugin').replace(' ', '_')
        version = meta.get('Version', '1.0.0')

    # 2. 准备输出目录
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    zip_name = f"{plugin_name}-v{version}.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_name)

    print(f"开始打包: {zip_name}...")

    # 3. 创建压缩包
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 打包文件
        for file in INCLUDE_FILES:
            if os.path.exists(file):
                zf.write(file)
                print(f"  已添加文件: {file}")
            else:
                print(f"  警告: 跳过未找到的文件 {file}")

        # 打包文件夹
        for folder in INCLUDE_DIRS:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    # 排除 Python 缓存目录
                    if '__pycache__' in dirs:
                        dirs.remove('__pycache__')
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 在压缩包内部保持相对路径
                        zf.write(file_path)
                print(f"  已添加文件夹: {folder} (已自动排除 __pycache__)")

    print("-" * 30)
    print(f"打包成功！生成的 Release 文件位于: {zip_path}")
    print("你可以直接将此 ZIP 文件上传到 GitHub Releases。")

if __name__ == "__main__":
    build()