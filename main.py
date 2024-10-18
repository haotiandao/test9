import concurrent.futures
import subprocess
import re
import time
import os
import encodings.idna
import random
from fake_useragent import UserAgent


playlist_file = "playlists/"

m3u8_file_path = "output/"

filter_url_arr = ['stream1.freetv.fun','cnstream.top','goodiptv','jlntv','zjrtv.vip','epg.pw','21dtv.com/songs','sd5hxc','bs3/video-hls',
'gcalic.v.myalicdn.com/gc/','gctxyc.liveplay.myqcloud.com','bizcommon.alicdn.com'] # 剔除一些特定的直播源，因它们不是开放的静态直播源，或者其他一些不想要的

filter_url_arr_1 = ['live.metshop.top'] # 针对斗鱼，虎牙的直播源做特殊过滤，仅保留电影相关的

max_workers = 8  # 测试直播源的线程数量。线程数太多，容易被屏蔽请求

download_video_time = 4 # 使用ffmpeg下载多少秒直播源的视频时长，时间太短一些国外的源，可能还没发缓冲过来，不建议在调整该值

download_video_length = download_video_time * 70 # 使用ffmpeg下载{download_video_time}秒直播源的视频时长，如果视频文件的大小，小于这个值，说明下载很慢，那么剔除掉，一般1秒钟需要有70KB才不卡顿

timeout = download_video_time + 0.5  # 使用ffmpeg下载{download_video_time}秒直播源的视频，最大允许的耗时秒数，超过的终止请求。超时时间太短可能没法获取视频分辨率，不建议在调整该值

download_video_use_time = timeout + 0.5  # 使用ffmpeg下载{download_video_time}秒直播源的视频，到解析出视频分辨率，最大允许的耗时秒数，超过的剔除，不建议在调整该值

def get_fake_User_Agent():
    ua = UserAgent()
    user_agent = ua.random
    return user_agent


def print_time(start_time, width, height, url):
    end_time = time.time()
    get_time = end_time - start_time
    get_time = "{:.3f}".format(get_time)
    print(f"get_time: {get_time}  Resolution: {width}x{height} url: {url}")
    return get_time


def get_resolution_and_download_time(i, url):
    start_time = time.time()
    process = None
    output_file_name = "test_" + str(i) + ".mp4"

    try:
        # print(f"get_resolution_and_download_time start, url：{url}")
        ua = get_fake_User_Agent()

        cmd = ["ffmpeg"]
        cmd.append("-user_agent")
        cmd.append(ua)
        cmd.append("-i")
        cmd.append(url)
        cmd.append("-hide_banner")
        cmd.append("-t")
        cmd.append(str(download_video_time))  # 将xx秒钟的直播视频下载下来
        cmd.append("-c")
        cmd.append("copy")
        cmd.append(output_file_name)

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf-8",
            check=True,
        )

        if result is not None and result.returncode == 0:
            print(f"cmd result: {result}")
            file_size = os.path.getsize(output_file_name) / 1024

            # 删除之前测试直播源存储的视频文件
            os.remove(output_file_name)

            if file_size < download_video_length:
                print(f"{download_video_time}秒钟的视频大小没有超过{download_video_length}KB, 播放容易卡顿，故剔除掉 url: {url}")
                print_time(start_time, 0, 0, url)
                return None, None, None

            output_cont = result.stdout
            cont_arr = output_cont.split("\n")
            cont_len = len(cont_arr)

            width_height = ""
            for j in range(cont_len):
                if cont_arr[j].find("Stream #0:0:") > -1:
                    match = re.search(r"(\d{3,4}x\d{3,4})", cont_arr[j])
                    if match:
                        width_height = match.group(1)
                        print("width_height:" + width_height + " =======================================")
                        break

            if len(width_height) > 0:
                arr = width_height.split("x")
                width = arr[0]
                height = arr[1]

                get_time = print_time(start_time, width, height, url)
                return width, height, get_time
            else:
                print_time(start_time, 0, 0, url)
                return None, None, None

        else:
            # 删除之前测试直播源存储的视频文件
            if os.path.isfile(output_file_name):
                os.remove(output_file_name)

            print_time(start_time, 0, 0, url)
            return None, None, None

    except Exception as e:
        if process is not None:
            process.kill()

        # 删除之前测试直播源存储的视频文件
        if os.path.isfile(output_file_name):
            os.remove(output_file_name)

        print(f"Failed to get resolution for URL {url}: {e}")
        print_time(start_time, 0, 0, url)
        return None, None, None


def test_stream(url, output_file, tv_name, i, total):
    print(f"test url no.:{i} total: {total}")
    try:
        width, height, get_time = get_resolution_and_download_time(i, url)

        print("get_time:" + get_time + " =======================================")
       
        # 剔除获取不到视频分辨率的
        # 剔除下载2秒视频流，耗时超过xx秒的直播源
        if (width is None or height is None or get_time is None):
            print(f"TV Name: {tv_name} URL: {url} 未获取到分辨率，剔除掉")
        elif (float(width) > 2000):
            print(f"TV Name: {tv_name} URL: {url} 分辨率宽度超过2000，容易卡顿，剔除掉")
        elif (float(get_time) > download_video_use_time):
            print(f"TV Name: {tv_name} URL: {url} 获取分辨率超时，剔除掉")
        elif (width is not None
            and height is not None
            and get_time is not None
            and float(get_time) <= download_video_use_time
        ):
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"#EXTINF:-1,{tv_name}___{width}x{height}_{get_time}\n")
                f.write(url + "\n")
            print(f"TV Name: {tv_name}_{width}x{height}_{get_time} ===========================")
            print(f"URL: {url}")

    except Exception as e:
        print(f"Failed to test URL {url}: {e}")


def get_tv_name(line, isHandle):
    match = re.search(r'tvg-name="([^"]+)"', line)
    if match:
        if isHandle:
            new_parts = match.group(1).strip().split("_");
            return new_parts[0]
        else:
            return match.group(1).strip()
    else:
        parts = line.split(",")
        if len(parts) > 1:
            if isHandle:
                new_parts = parts[1].strip().split("_");
                return new_parts[0]
            else:
                return parts[1].strip();
        else:
            return "Unknown"


def main(playlist_file, m3u8_file_path):

    output_file = (
        m3u8_file_path + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + ".m3u"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    urls = []
    idx = 0

    for file_name in os.listdir(playlist_file):

        print(f"file_name: {file_name}")

        if file_name.endswith(".m3u") or file_name.endswith(".m3u8"):  # 处理m3u、m3u8格式的直播源列表
            file_path = os.path.join(playlist_file, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total = len(lines)
            for i in range(total):
                if lines[i].startswith("#EXTINF:-1"):
                    tv_name = get_tv_name(lines[i], True)
                    if i + 1 <= total and lines[i + 1].startswith("http"):
                        url = lines[i + 1].strip()
                        print(f"read file url: {url} TV Name: {tv_name}")
                        idx = idx + 1
                        urls.append((url, tv_name, idx))
                        

        else:  # 处理txt格式的直播源列表
            file_path = os.path.join(playlist_file, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total = len(lines)
            for i in range(total):
                if (lines[i].find("http:") != -1 or lines[i].find("https:") != -1) and lines[i].find(",") != -1:
                    arr = lines[i].split(",")
                    tv_name = arr[0].strip()
                    url = arr[1].strip()
                    if (url.find("#") != -1):  # 兼容txt格式直播源，带有多个直播源地址的情况
                        urlArr = url.split("#")
                        urlNum = len(urlArr)
                        for j in range(urlNum):
                            print(f"read file url: {urlArr[j]} TV Name: {tv_name}")
                            idx = idx + 1
                            urls.append((urlArr[j], tv_name, idx))
                            

                    else:
                        print(f"read file url: {url} TV Name: {tv_name}")
                        idx = idx + 1
                        urls.append((url, tv_name, idx))
                        
    unique_urls = []
    new_urls = []
    idx = 0
    for url_1, tv_name_1, idx_1 in urls:
        isExist = 1
        
        # 过滤重复的url
        if url_1 not in unique_urls:
            isExist = 0
            unique_urls.append(url_1);
            
        # 过滤不想要的url
        for url_2 in filter_url_arr:
            if url_1.find(url_2) != -1 :
                isExist = 1
                
        # 过滤不想要的url，专门针对斗鱼，虎牙      
        for url_2 in filter_url_arr_1:
            if url_1.find(url_2) != -1 and tv_name_1.find("电影")==-1:
                isExist = 1
                
        
        if isExist == 0 :
            new_urls.append((url_1, tv_name_1, idx))
        
    urls = new_urls;
    new_urls = []
    
    urlLen = len(urls)
    # 随机排序下，以便并发测试时，不要同时测试同一个ip地址的直播源
    random.shuffle(urls)
    new_idx = 0

    # 使用多线程并发测试
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for url, tv_name, idx in urls:
            new_idx = new_idx + 1
            future = executor.submit(
                test_stream, url, output_file, tv_name, new_idx, urlLen
            )

    # 将可用的直播源重新排序
    with open(output_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    new_urls = []
    idx = 0
    for i in range(total):
        if lines[i].startswith("#EXTINF:-1"):
            tv_name = get_tv_name(lines[i], False)
            if i + 1 <= total and lines[i + 1].startswith("http"):
                url = lines[i + 1].strip()
                host_name = url.split("/")[0]
                # print(f"read file url: {url} TV Name: {tv_name}")
                idx = idx + 1
                new_urls.append((url, host_name, tv_name, idx))

    new_sort_urls = sorted(new_urls, key=lambda d:(d[1],d[2]))  # 按照 host_name tv_name 排序

    # 再新建一个m3u文件来存储排序后的
    new_output_file = (
        m3u8_file_path + time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime()) + ".m3u"
    )

    with open(new_output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    with open(new_output_file, "a", encoding="utf-8") as f:
        for url, host_name, tv_name, idx in new_sort_urls:
            f.write(f"#EXTINF:-1,{tv_name}\n")
            f.write(url + "\n")

    # 删除之前的m3u文件，因没有排序
    os.remove(output_file)


if __name__ == "__main__":
    main(playlist_file, m3u8_file_path)
