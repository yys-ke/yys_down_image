import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin

def download_image(url, save_path, headers):
    try:
        print(f"开始下载: {url}")
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
        
        print(f"下载成功: {os.path.basename(save_path)} ({downloaded_size/1024:.1f}KB)")
        return True
    except Exception as e:
        print(f"下载失败 {url}: {e}")
        return False

def get_image_category(resolution):
    """根据分辨率判断图片分类"""
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

def select_output_directory():
    """选择保存文件夹"""
    default_dir = 'yys_images'
    
    print(f"默认保存目录: {default_dir}")
    print("按Enter键使用默认目录，或输入自定义目录路径:")
    
    user_input = input("保存目录: ").strip()
    
    if user_input:
        output_dir = user_input
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    else:
        output_dir = default_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    return output_dir

def scrape_yys_images(url, output_dir='yys_images', resolution='1920x1080', category=None, batch_size=10):
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
        print(f"目标目录已符合格式: {dir_name}")
    else:
        actual_output_dir = os.path.join(output_dir, expected_dir_name)
        if not os.path.exists(actual_output_dir):
            os.makedirs(actual_output_dir)
        print(f"目标目录不符合格式，创建子目录: {expected_dir_name}")
    
    print(f"正在访问网页: {url}")
    print(f"当前选择: {category} | 分辨率: {resolution}")
    print(f"实际保存目录: {os.path.abspath(actual_output_dir)}")
    
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
            # 尝试从URL中提取日期和序号
            if '/data/picture/' in img_url:
                try:
                    parts = img_url.split('/data/picture/')[-1].split('/')
                    if len(parts) >= 3:
                        date = parts[0]
                        seq = parts[1]
                        return (-int(date), int(seq))
                except:
                    pass
            # 尝试从URL中提取任何数字作为排序依据
            import re
            numbers = re.findall(r'\d+', img_url)
            if numbers:
                try:
                    # 使用最后一组数字作为排序依据
                    return (-int(numbers[-1]), 0)
                except:
                    pass
            return (0, 0)
        
        filtered_urls.sort(key=get_sort_key)
        image_urls = filtered_urls
        print(f"找到 {len(image_urls)} 张 {category} 图片")
        print("已按日期降序、序号升序排序")
        
        total_images = len(image_urls)
        success_count = 0
        downloaded_count = 0
        
        while downloaded_count < total_images:
            batch_end = min(downloaded_count + batch_size, total_images)
            batch_urls = image_urls[downloaded_count:batch_end]
            
            print(f"\n正在下载第 {downloaded_count + 1}-{batch_end} 张图片 (共 {total_images} 张)...")
            
            for i, img_url in enumerate(batch_urls, downloaded_count + 1):
                print(f"处理第 {i} 张图片...")
                try:
                    if not img_url.startswith('http'):
                        img_url = urljoin(url, img_url)
                        print(f"补全URL: {img_url}")
                    
                    # 确保URL格式正确
                    if not img_url.startswith('http'):
                        print(f"URL格式错误，跳过: {img_url}")
                        continue
                    
                    file_name = f"{category}_{i}_{resolution}.jpg"
                    if '/data/picture/' in img_url:
                        try:
                            parts = img_url.split('/data/picture/')[-1].split('/')
                            if len(parts) >= 3:
                                date = parts[0]
                                seq = parts[1]
                                file_name = f"{date}_{seq}_{resolution}.jpg"
                                print(f"使用日期命名: {file_name}")
                        except Exception as e:
                            print(f"解析URL失败: {e}")
                            pass
                    
                    save_path = os.path.join(actual_output_dir, file_name)
                    print(f"保存路径: {save_path}")
                    
                    if os.path.exists(save_path):
                        print(f"文件已存在，跳过下载: {file_name}")
                        continue
                    
                    if download_image(img_url, save_path, headers):
                        success_count += 1
                        print(f"下载成功计数: {success_count}")
                    
                    time.sleep(0.5)
                except Exception as e:
                    print(f"处理图片时出错: {e}")
                    continue
            
            downloaded_count = batch_end
            
            if downloaded_count < total_images:
                print(f"\n已下载 {downloaded_count}/{total_images} 张图片")
                try:
                    choice = input("请输入继续下载的张数 (输入0退出): ").strip()
                    if choice == '0':
                        print("用户选择停止下载")
                        break
                    elif choice.isdigit():
                        batch_size = int(choice)
                        print(f"继续下载 {batch_size} 张图片...")
                    else:
                        print("输入无效，使用默认批量大小 10...")
                        batch_size = 10
                except:
                    print("输入错误，使用默认批量大小 10...")
                    batch_size = 10
        
        print(f"\n下载完成! 成功下载 {success_count}/{downloaded_count} 张图片")
        print(f"图片保存在: {os.path.abspath(actual_output_dir)}")
        
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    url = "https://yys.163.com/media/picture.html"
    
    category_resolutions = {
        '横版': ['1366x768', '1440x900', '1920x1080', '2048x1536', '2208x1242', '2732x2048'],
        '竖版': ['640x960', '640x1136', '720x1280', '750x1334', '1080x1920'],
        '手机壁纸': ['1080x2340', '1920x1080', '2160x1620']
    }
    
    categories = ['横版', '竖版', '手机壁纸']
    print("可用的分类选项:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    
    cat_choice = input("\n请选择分类 (1-3, 默认为1即横版): ").strip()
    
    if cat_choice.isdigit() and 1 <= int(cat_choice) <= 3:
        category = categories[int(cat_choice) - 1]
    else:
        category = '横版'
    
    resolutions = category_resolutions[category]
    
    print(f"\n{category} 可用的分辨率选项:")
    for i, res in enumerate(resolutions, 1):
        print(f"{i}. {res}")
    
    res_choice = input(f"\n请选择分辨率 (1-{len(resolutions)}, 默认为1): ").strip()
    
    if res_choice.isdigit() and 1 <= int(res_choice) <= len(resolutions):
        resolution = resolutions[int(res_choice) - 1]
    else:
        resolution = resolutions[0]
    
    print("请选择保存文件夹...")
    output_dir = select_output_directory()
    
    if not output_dir:
        output_dir = 'yys_images'
        print(f"未选择文件夹，使用默认目录: {output_dir}")
    
    print(f"\n开始下载 {category} | {resolution} 的图片到 {output_dir}...")
    scrape_yys_images(url, output_dir=output_dir, resolution=resolution, category=category)

