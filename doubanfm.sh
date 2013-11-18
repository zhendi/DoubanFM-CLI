#!/bin/bash

# 如果报错时间不能正确解析 (does not match format '%a, %d-%b-%Y %H:%M:%S GMT')，请运行这个脚本
# 为了解决cookie时间不能正常解析的问题。这里应该写在python代码里，而非sh脚本里 todo
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

python doubanfm.py
