## 使用教程

首先搜索直播源，存放到playlists文件夹下，支持txt和m3u播放列表；并到 https://ffmpeg.org/download.html#build-windows 这里下载 ffmpeg.exe文件，放到当前项目的根目录；然后运行检测，检测完毕的直播源，输出在output文件夹下，然后使用播放器观看即可
<br>windows平台推荐 MPC-HC
<br>android平台推荐 IPTV Pro

## 检测原理
通过python，使用多线程的方式，调用ffmpeg来检查直播源地址的有效性（下载2秒的直播视频下来，判断分辨率和下载的文件大小），得到真实可以播放且不卡顿的直播源地址
