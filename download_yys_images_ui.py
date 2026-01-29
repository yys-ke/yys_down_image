import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import re

def download_image(url, save_path, headers, callback=None):
    try:
        if callback:
            callback(f"开始下载: {url}")
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
        
        if callback:
            callback(f"下载成功: {os.path.basename(save_path)} ({downloaded_size/1024:.1f}KB)")
        return True
    except Exception as e:
        if callback:
            callback(f"下载失败 {url}: {e}")
        return False

def get_image_category(resolution):
    horizontal_res = {'1366x768', '1440x900', '1920x1080', '2048x1536', '2208x1242', '2732x2048'}
    vertical_res = {'640x960', '640x1136', '720x1280', '750x1334', '1080x1920'}
    mobile_res = {'1080x2340', '1920x1080', '2160x1620'}
    
    if resolution in horizontal_res:
        return '横版'
    elif resolution in vertical_res:
        return '竖版'
    elif resolution in mobile_res:
        return '手机壁纸'
    else:
        return '未知'

class YYSImageDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("阴阳师图片下载器")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 停止标志
        self.stop_flag = threading.Event()
        self.download_thread = None
        
        # 设置默认值
        self.category_resolutions = {
            '横版': ['1366x768', '1440x900', '1920x1080', '2048x1536', '2208x1242', '2732x2048'],
            '竖版': ['640x960', '640x1136', '720x1280', '750x1334', '1080x1920'],
            '手机壁纸': ['1080x2340', '1920x1080', '2160x1620']
        }
        
        self.selected_category = '横版'
        self.selected_resolution = self.category_resolutions['横版'][0]
        self.output_dir = os.path.join(os.path.expanduser("~"), "yys_images")
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        self.title_label = ttk.Label(self.main_frame, text="阴阳师图片下载器", font=("SimHei", 18, "bold"))
        self.title_label.pack(pady=(0, 20))
        
        # 分类选择
        self.category_frame = ttk.LabelFrame(self.main_frame, text="选择图片分类", padding="10")
        self.category_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.category_var = tk.StringVar(value=self.selected_category)
        self.category_buttons = []
        
        category_inner_frame = ttk.Frame(self.category_frame)
        category_inner_frame.pack(fill=tk.X)
        
        for category in ['横版', '竖版', '手机壁纸']:
            btn = ttk.Radiobutton(
                category_inner_frame, 
                text=category, 
                variable=self.category_var, 
                value=category,
                command=self.on_category_change
            )
            btn.pack(side=tk.LEFT, padx=10)
            self.category_buttons.append(btn)
        
        # 分辨率选择
        self.resolution_frame = ttk.LabelFrame(self.main_frame, text="选择分辨率", padding="10")
        self.resolution_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.resolution_var = tk.StringVar(value=self.selected_resolution)
        self.resolution_combobox = ttk.Combobox(
            self.resolution_frame,
            textvariable=self.resolution_var,
            state="readonly"
        )
        self.resolution_combobox['values'] = self.category_resolutions[self.selected_category]
        self.resolution_combobox.pack(fill=tk.X)
        
        # 保存目录选择
        self.dir_frame = ttk.LabelFrame(self.main_frame, text="保存目录", padding="10")
        self.dir_frame.pack(fill=tk.X, pady=(0, 15))
        
        dir_inner_frame = ttk.Frame(self.dir_frame)
        dir_inner_frame.pack(fill=tk.X)
        
        self.dir_var = tk.StringVar(value=self.output_dir)
        self.dir_entry = ttk.Entry(dir_inner_frame, textvariable=self.dir_var)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.browse_btn = ttk.Button(dir_inner_frame, text="浏览", command=self.browse_directory)
        self.browse_btn.pack(side=tk.RIGHT)
        
        # 按钮框架
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 下载按钮
        self.download_btn = ttk.Button(
            self.button_frame, 
            text="开始下载", 
            style="Accent.TButton",
            command=self.start_download
        )
        self.download_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # 停止按钮
        self.stop_btn = ttk.Button(
            self.button_frame, 
            text="停止下载", 
            command=self.stop_download,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # 状态文本框
        self.status_frame = ttk.LabelFrame(self.main_frame, text="下载状态", padding="10")
        self.status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.status_text = tk.Text(self.status_frame, height=12, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.config(state=tk.DISABLED)
        
        # 滚动条
        self.scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text['yscrollcommand'] = self.scrollbar.set
        
        # 配置样式
        style = ttk.Style()
        try:
            style.configure("Accent.TButton", font=("SimHei", 10, "bold"))
        except:
            style.configure("Accent.TButton", font=("Microsoft YaHei", 10, "bold"))
    
    def on_category_change(self):
        """分类改变时更新分辨率选项"""
        self.selected_category = self.category_var.get()
        self.selected_resolution = self.category_resolutions[self.selected_category][0]
        self.resolution_var.set(self.selected_resolution)
        self.resolution_combobox['values'] = self.category_resolutions[self.selected_category]
    
    def browse_directory(self):
        """浏览目录"""
        directory = filedialog.askdirectory(
            initialdir=self.output_dir,
            title="选择保存目录"
        )
        if directory:
            self.output_dir = directory
            self.dir_var.set(directory)
    
    def write_status(self, text):
        """更新状态文本框"""
        def update_text():
            self.status_text.config(state=tk.NORMAL)
            self.status_text.insert(tk.END, text)
            self.status_text.see(tk.END)
            self.status_text.config(state=tk.DISABLED)
        
        self.root.after(0, update_text)
    
    def scrape_yys_images(self, url, output_dir, resolution, category, batch_size=10):
        """爬取阴阳师图片"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if not category:
            category = get_image_category(resolution)
        
        expected_dir_name = f"{category}_{resolution}"
        
        dir_name = os.path.basename(output_dir.rstrip(os.sep))
        
        if dir_name == expected_dir_name:
            actual_output_dir = output_dir
            self.write_status(f"目标目录已符合格式: {dir_name}\n")
        else:
            actual_output_dir = os.path.join(output_dir, expected_dir_name)
            if not os.path.exists(actual_output_dir):
                os.makedirs(actual_output_dir)
            self.write_status(f"目标目录不符合格式，创建子目录: {expected_dir_name}\n")
        
        self.write_status(f"正在访问网页: {url}\n")
        self.write_status(f"当前选择: {category} | 分辨率: {resolution}\n")
        self.write_status(f"实际保存目录: {os.path.abspath(actual_output_dir)}\n")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            image_urls = []
            
            a_tags = soup.find_all('a')
            for a in a_tags:
                href = a.get('href')
                if href and resolution in href:
                    if not href.startswith('http'):
                        href = urljoin(url, href)
                    image_urls.append(href)
            
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('data-src') or img.get('src')
                if src:
                    full_url = urljoin(url, src)
                    if resolution in full_url:
                        image_urls.append(full_url)
            
            data_items = soup.find_all(['div', 'span'], {'data-src': True})
            for item in data_items:
                src = item.get('data-src')
                if src and resolution in src:
                    full_url = urljoin(url, src)
                    image_urls.append(full_url)
            
            image_urls = list(set(image_urls))
            
            filtered_urls = []
            for img_url in image_urls:
                if category == '横版':
                    if any(res in img_url for res in ['1366x768', '1440x900', '1920x1080', '2048x1536', '2208x1242', '2732x2048']):
                        filtered_urls.append(img_url)
                elif category == '竖版':
                    if any(res in img_url for res in ['640x960', '640x1136', '720x1280', '750x1334', '1080x1920']):
                        filtered_urls.append(img_url)
                elif category == '手机壁纸':
                    if any(res in img_url for res in ['1080x2340', '1920x1080', '2160x1620']):
                        filtered_urls.append(img_url)
                else:
                    filtered_urls.append(img_url)
            
            def get_sort_key(img_url):
                """获取排序键"""
                if '/data/picture/' in img_url:
                    try:
                        parts = img_url.split('/data/picture/')[-1].split('/')
                        if len(parts) >= 3:
                            date = parts[0]
                            seq = parts[1]
                            return (-int(date), int(seq))
                    except:
                        pass
                numbers = re.findall(r'\d+', img_url)
                if numbers:
                    try:
                        return (-int(numbers[-1]), 0)
                    except:
                        pass
                return (0, 0)
            
            filtered_urls.sort(key=get_sort_key)
            image_urls = filtered_urls
            self.write_status(f"找到 {len(image_urls)} 张 {category} 图片\n")
            self.write_status("已按日期降序、序号升序排序\n")
            
            total_images = len(image_urls)
            success_count = 0
            downloaded_count = 0
            
            while downloaded_count < total_images:
                # 检查是否需要停止
                if self.stop_flag.is_set():
                    self.write_status("\n检测到停止信号，停止下载\n")
                    break
                
                batch_end = min(downloaded_count + batch_size, total_images)
                batch_urls = image_urls[downloaded_count:batch_end]
                
                self.write_status(f"\n正在下载第 {downloaded_count + 1}-{batch_end} 张图片 (共 {total_images} 张)...\n")
                
                for i, img_url in enumerate(batch_urls, downloaded_count + 1):
                    # 检查是否需要停止
                    if self.stop_flag.is_set():
                        self.write_status("\n检测到停止信号，停止下载\n")
                        break
                    
                    self.write_status(f"处理第 {i} 张图片...\n")
                    try:
                        if not img_url.startswith('http'):
                            img_url = urljoin(url, img_url)
                            self.write_status(f"补全URL: {img_url}\n")
                        
                        if not img_url.startswith('http'):
                            self.write_status(f"URL格式错误，跳过: {img_url}\n")
                            continue
                        
                        file_name = f"{category}_{i}_{resolution}.jpg"
                        if '/data/picture/' in img_url:
                            try:
                                parts = img_url.split('/data/picture/')[-1].split('/')
                                if len(parts) >= 3:
                                    date = parts[0]
                                    seq = parts[1]
                                    file_name = f"{date}_{seq}_{resolution}.jpg"
                                    self.write_status(f"使用日期命名: {file_name}\n")
                            except Exception as e:
                                self.write_status(f"解析URL失败: {e}\n")
                                pass
                        
                        save_path = os.path.join(actual_output_dir, file_name)
                        self.write_status(f"保存路径: {save_path}\n")
                        
                        if os.path.exists(save_path):
                            self.write_status(f"文件已存在，跳过下载: {file_name}\n")
                            continue
                        
                        if download_image(img_url, save_path, headers, self.write_status):
                            success_count += 1
                            self.write_status(f"下载成功计数: {success_count}\n")
                        
                        time.sleep(0.5)
                    except Exception as e:
                        self.write_status(f"处理图片时出错: {e}\n")
                        continue
                
                downloaded_count = batch_end
                
                if downloaded_count < total_images:
                    self.write_status(f"\n已下载 {downloaded_count}/{total_images} 张图片\n")
                    self.write_status(f"继续下载下一批 {batch_size} 张图片...\n")
            
            self.write_status(f"\n下载完成! 成功下载 {success_count}/{downloaded_count} 张图片\n")
            self.write_status(f"图片保存在: {os.path.abspath(actual_output_dir)}\n")
            
        except Exception as e:
            self.write_status(f"发生错误: {e}\n")
    
    def start_download(self):
        """开始下载"""
        # 清空停止标志
        self.stop_flag.clear()
        
        # 禁用下载按钮，启用停止按钮
        self.download_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 清空状态文本
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        # 获取选择的值
        category = self.category_var.get()
        resolution = self.resolution_var.get()
        output_dir = self.dir_var.get()
        
        # 在后台线程中执行下载
        def download_thread():
            try:
                url = "https://yys.163.com/media/picture.html"
                self.scrape_yys_images(url, output_dir=output_dir, resolution=resolution, category=category)
                self.write_status("\n下载完成！\n")
            except Exception as e:
                self.write_status(f"\n发生错误: {e}\n")
            finally:
                # 启用下载按钮，禁用停止按钮
                self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
        
        self.download_thread = threading.Thread(target=download_thread)
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def stop_download(self):
        """停止下载"""
        self.write_status("\n正在停止下载...\n")
        self.stop_flag.set()
        self.stop_btn.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = YYSImageDownloaderGUI(root)
    root.mainloop()
