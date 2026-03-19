import sys
import os
import time
import ctypes
from ctypes import wintypes
from io import BytesIO

# --- 环境依赖注入初始化 ---
plugin_dir = os.path.dirname(__file__)
lib_path = os.path.join(plugin_dir, 'lib')

sys.path.insert(0, lib_path)

if hasattr(os, 'add_dll_directory'):
    try:
        os.add_dll_directory(lib_path)
        pil_path = os.path.join(lib_path, 'PIL')
        if os.path.exists(pil_path):
            os.add_dll_directory(pil_path)
        pyzbar_path = os.path.join(lib_path, 'pyzbar')
        if os.path.exists(pyzbar_path):
            os.add_dll_directory(pyzbar_path)
    except Exception:
        pass
# ---------------------------

# --- Windows API 类型显式声明 ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
# 注意：已移除 GetForegroundWindow 和 ShowWindow API，避免破坏 Flow Launcher UI 状态
# ---------------------------

from PIL import Image, ImageGrab
from pyzbar.pyzbar import decode, ZBarSymbol
import qrcode
from flowlauncher import FlowLauncher 

class QRCodePlugin(FlowLauncher):

    def query(self, query):
        results = []
        query = query.strip().strip('"')
        
        is_image_file = False
        if os.path.isfile(query):
            ext = os.path.splitext(query)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif']:
                is_image_file = True

        if is_image_file:
            results.append({
                "Title": "解析此图片内的二维码",
                "SubTitle": f"路径: {query}",
                "IcoPath": "Images/scan.png",
                "JsonRPCAction": {
                    "method": "parse_local_image",
                    "parameters": [query],
                    "dontHideAfterAction": False
                }
            })
            results.append({
                "Title": "将此路径文本生成二维码",
                "SubTitle": "回车生成",
                "IcoPath": "Images/gen.png",
                "JsonRPCAction": {
                    "method": "generate_to_clipboard",
                    "parameters": [query],
                    "dontHideAfterAction": False
                }
            })
            return results

        if not query:
            results.append({
                "Title": "1. 瞬间扫描全屏二维码",
                "SubTitle": "无延迟截取全屏至内存(不污染剪贴板)，自动找出所有二维码并复制",
                "IcoPath": "Images/scan.png",
                "JsonRPCAction": {
                    "method": "scan_from_screen_silently",
                    "parameters": [],
                    # dontHideAfterAction=False 会指示 Flow Launcher 原生隐藏窗口
                    "dontHideAfterAction": False 
                }
            })
            results.append({
                "Title": "2. 区域截图扫描二维码",
                "SubTitle": "调用系统截图手动框选区域，完成后自动解析内容",
                "IcoPath": "Images/scan.png",
                "JsonRPCAction": {
                    "method": "scan_from_screen_manual",
                    "parameters": [],
                    "dontHideAfterAction": False 
                }
            })
            results.append({
                "Title": "3. 解析剪贴板内的二维码",
                "SubTitle": "直接读取当前剪贴板中的图片数据或文件路径并解析",
                "IcoPath": "Images/scan.png",
                "JsonRPCAction": {
                    "method": "parse_clipboard",
                    "parameters": [],
                    "dontHideAfterAction": False 
                }
            })
            results.append({
                "Title": "4. 生成二维码",
                "SubTitle": "请直接在 'qr ' 后面继续输入你想生成的文本...",
                "IcoPath": "Images/gen.png",
                "JsonRPCAction": {
                    "method": "do_nothing", 
                    "parameters": [],
                    "dontHideAfterAction": True 
                }
            })
            return results

        results.append({
            "Title": f"生成二维码: {query}",
            "SubTitle": "回车将对应的二维码图片直接写入剪贴板",
            "IcoPath": "Images/gen.png",
            "JsonRPCAction": {
                "method": "generate_to_clipboard",
                "parameters": [query],
                "dontHideAfterAction": False 
            }
        })

        return results

    def scan_from_screen_silently(self):
        # 依靠 dontHideAfterAction=False 的原生机制隐藏窗口
        # 休眠 0.4 秒，等待 Flow Launcher UI 彻底完成收回动画，以免截图中拍到残影
        time.sleep(0.4)
        
        try:
            img = ImageGrab.grab(all_screens=True)
            img = img.convert('RGB')
            return self._decode_and_respond(img, "全屏画面")
        except Exception as e:
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": ["全屏抓取失败", str(e), ""]
            }

    def scan_from_screen_manual(self):
        # 休眠 0.4 秒等待窗口原生隐藏
        time.sleep(0.4)
        
        self.empty_clipboard()
        os.startfile("ms-screenclip:")
        
        img = None
        for _ in range(30):
            time.sleep(0.5)
            img = ImageGrab.grabclipboard()
            if img is not None:
                break
                
        if isinstance(img, Image.Image):
            img = img.convert('RGB')
            return self._decode_and_respond(img, "区域截图")
        else:
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": ["操作取消", "超时未检测到新截图或动作已取消", ""]
            }

    def parse_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": ["剪贴板读取失败", str(e), ""]
            }
            
        if isinstance(img, Image.Image):
            img = img.convert('RGB')
            return self._decode_and_respond(img, "剪贴板图片")
            
        elif isinstance(img, list) and len(img) > 0 and isinstance(img[0], str):
            first_file = img[0]
            if os.path.isfile(first_file):
                return self.parse_local_image(first_file)
                
        return {
            "method": "Flow.Launcher.ShowMsg",
            "parameters": ["解析失败", "当前剪贴板中没有图片或不支持的内容", ""]
        }

    def parse_local_image(self, file_path):
        try:
            img = Image.open(file_path)
            img = img.convert('RGB')
            return self._decode_and_respond(img, "本地图片")
        except Exception as e:
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": ["解析失败", f"无法读取图片文件: {str(e)}", ""]
            }

    def _decode_and_respond(self, img, source_name):
        decoded_objects = decode(img, symbols=[ZBarSymbol.QRCODE])
        if decoded_objects:
            if len(decoded_objects) == 1:
                content = decoded_objects[0].data.decode('utf-8')
                success_title = "扫码成功"
                success_sub = f"内容已复制: {content}"
            else:
                contents = [obj.data.decode('utf-8') for obj in decoded_objects]
                content = "\n".join(contents)
                success_title = f"扫码成功 (共 {len(decoded_objects)} 个)"
                success_sub = "所有二维码内容已合并复制"

            try:
                self.send_text_to_clipboard(content)
            except Exception as e:
                return {
                    "method": "Flow.Launcher.ShowMsg",
                    "parameters": ["剪贴板写入失败", str(e), ""]
                }
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": [success_title, success_sub, ""]
            }
        else:
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": ["扫码失败", f"未能从[{source_name}]中找到二维码", ""]
            }

    def generate_to_clipboard(self, text):
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        output = BytesIO()
        img.convert('RGB').save(output, 'BMP')
        data = output.getvalue()[14:] 
        output.close()

        try:
            self.set_clipboard_dib(data)
        except Exception as e:
            return {
                "method": "Flow.Launcher.ShowMsg",
                "parameters": ["剪贴板写入失败", str(e), ""]
            }
        
        return {
            "method": "Flow.Launcher.ShowMsg",
            "parameters": ["生成成功", "二维码图片已放入剪贴板", ""]
        }

    def send_text_to_clipboard(self, text):
        CF_UNICODETEXT = 13 
        data = text.encode('utf-16le') + b'\x00\x00'

        hGlobalMem = kernel32.GlobalAlloc(0x0042, len(data))
        if not hGlobalMem:
            raise ctypes.WinError()

        lpGlobalMem = kernel32.GlobalLock(hGlobalMem)
        if not lpGlobalMem:
            raise ctypes.WinError()
        
        ctypes.memmove(lpGlobalMem, data, len(data))
        kernel32.GlobalUnlock(hGlobalMem)
        
        if user32.OpenClipboard(0):
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_UNICODETEXT, hGlobalMem)
            user32.CloseClipboard()
        else:
            raise Exception("无法打开系统剪贴板，可能被其他程序占用")

    def set_clipboard_dib(self, data):
        CF_DIB = 8 
        hGlobalMem = kernel32.GlobalAlloc(0x0042, len(data))
        if not hGlobalMem:
            raise ctypes.WinError()

        lpGlobalMem = kernel32.GlobalLock(hGlobalMem)
        if not lpGlobalMem:
            raise ctypes.WinError()
        
        ctypes.memmove(lpGlobalMem, data, len(data))
        kernel32.GlobalUnlock(hGlobalMem)
        
        if user32.OpenClipboard(0):
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_DIB, hGlobalMem)
            user32.CloseClipboard()
        else:
            raise Exception("无法打开系统剪贴板，可能被其他程序占用")

    def empty_clipboard(self):
        if user32.OpenClipboard(0):
            user32.EmptyClipboard()
            user32.CloseClipboard()

    def do_nothing(self):
        pass

if __name__ == "__main__":
    QRCodePlugin()