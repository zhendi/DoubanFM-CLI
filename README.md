豆瓣电台 命令行版
=================

**用法:**

`python doubanfm.py`

**频道列表:**

```
-3   红心
 0   私人
 1   华语
 2   欧美
 3   七零
 4   八零
 5   九零
 6   粤语
 7   摇滚
 8   民谣
 9   轻音乐
10   电影原声
```

**功能列表:**

跳过输入 `n`

加心输入 `f`

删歌输入 `d`

暂停输入 `p`

播放输入 `r`

切换频道输入 `c`

(并按Enter键)

**配置**

配置文件名：`doubanfm.config`

```
[DEFAULT]
interval=30 ; 歌与歌之间的沉默间隙，单位：秒。默认值：0
email=xxx@gmail.com; 登录用户名
passwd=xxx; 登录密码
```

**依賴**

- `python-gst` ，如debian系需要 `sudo apt-get install python-gst0.10`
- `Python Imaging Library` ，如debian系 `sudo apt-get install python-imaging`
- `python-dateutil` ，如debian系 `sudo apt-get install python-dateutil`
- `gstreamer0.10-plugins`
- `gstreamer0.10-plugins-ugly`

**其他**

- 不支持 Windows 

