"""所有view模块中的校验函数"""
from tkinter import messagebox as mBox
import os
from core import logger
import traceback


def check_path(pathObj, create_flag=False):
    """检查输入的路径是否合法"""
    flag = False
    if pathObj.get():  # 有输入内容
        dir_path = pathObj.get().strip()  # 防止出现输入' '
        if os.path.exists(dir_path):  # 检查路径是否存在
            # 当输入'/home/'时获取文件名就是''，所以加处理
            dir_path = os.path.abspath(dir_path)
            pathObj.set(dir_path)
            flag = True
        elif create_flag is True:
            # print("输入目录不存在！已为您新建该目录！")
            os.makedirs(dir_path)
            dir_path = os.path.abspath(dir_path)
            pathObj.set(dir_path)
            flag = True
    return flag


def show_path_error():
    mBox.showwarning("输入路径有误！", "输入路径不存在，请检查！")


def check_frameNum(numObj):
    """检查输入的帧数是否合法"""
    flag = False
    if numObj.get():  # 有输入内容
        num = str(numObj.get()).strip()  # 防止出现输入' '
        try:
            num = int(num)
            if num >= 0:
                numObj.set(num)
                flag = True
        except Exception:
            return False

    return flag


def check_intNum(num):
    """检查输入的整数是否合法"""
    flag = False
    if num:  # 有输入内容
        try:
            num = num.strip()  # 防止出现输入' '
            num = int(num)
            return True
        except Exception:
            return False
    return flag


def check_positiveIntNum(num):
    """检查输入的正整数是否合法"""
    flag = False
    if num:  # 有输入内容
        try:
            num = num.strip()  # 防止出现输入' '
            num = int(num)
            if num >= 0:
                flag = True
        except Exception:
            return False
    return flag


def check_floatNum(num):
    """检查输入的小数是否合法"""
    flag = False
    if num:  # 有输入内容
        try:
            num = num.strip()  # 防止出现输入' '
            num = float(num)
            return True
        except Exception:
            return False
    return flag


def show_frameNum_error():
    mBox.showwarning("输入的帧数有误！", "输入的帧数数据格式有误！\n帧数应为正整数！")


def check_threNum(num):
    """检查输入的相似度阈值是否合法"""
    flag = False
    if num:  # 有输入内容
        try:
            num = float(num)
            if 0 <= num <= 1:
                flag = True
        except Exception:
            return False
    return flag


def show_threNum_error():
    mBox.showwarning("输入的相似度阈值有误！", "输入的相似度阈值格式有误！\n相似度阈值应为0~1之间的小数！")


def log_error(func):
    """装饰器用于装饰各个模块页面的run方法来捕获异常"""

    def wrapped_func(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error_logger(traceback.format_exc())
            mBox.showerror("错误！", "程序运行出错！详情请查看日志")

    return wrapped_func