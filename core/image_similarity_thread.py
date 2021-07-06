#! /usr/bin/python3
# -*- encoding=utf-8 -*-

from functools import reduce
from PIL import Image, UnidentifiedImageError
from core import Mytools
from core import logger
from conf import settings
import os
import shutil
import time
import threading
import sys
import warnings


mutex = threading.Lock()  # 创建互斥锁

new_old_record = {}  # 用以记录剪切或复制前后的文件名，方便后面程序还原文件 格式{newfilename:oldfilename,}
old_new_record = {}  # 用以记录剪切或复制前后的文件名，方便后面程序还原文件 格式{oldfilename:newfilename,}
g_img_list = []  # 用来记录图片路径和phash值  [(path, phash),]
g_num = 0  # 记录相似图片编号


# 计算图片的局部哈希值--pHash
def phash(img_path):
    """
    :param img_path: 图片路径
    :return: 返回图片的局部hash值
    """
    # 读取图片
    img = Image.open(img_path)
    img = img.resize((8, 8), Image.ANTIALIAS).convert('L')
    avg = reduce(lambda x, y: x + y, img.getdata()) / 64
    hash_value = reduce(lambda x, y: x | (y[1] << y[0]), enumerate(map(lambda i: 0 if i < avg else 1, img.getdata())), 0)
    return hash_value


def phash4thread(path_list):
    for item in path_list:
        try:  # 文件不是图片时会报错
            item_phash = phash(item)
        except UnidentifiedImageError:
            print("%s不是图像无法比对，已跳过！" % item)
            return
        mutex.acquire()
        g_img_list.append((item, item_phash))
        mutex.release()


# 计算两个图片相似度函数局部敏感哈希算法
def phash_img_similarity(img1_phash, img2_phash):
    """
    :param img1_phash: 图片1phash
    :param img2_phash: 图片2phash
    :return: 图片相似度
    """
    # 计算汉明距离
    distance = bin(img1_phash ^ img2_phash).count('1')
    similary = 1 - distance / max(len(bin(img1_phash)), len(bin(img2_phash)))
    return similary


# 融合函数计算图片相似度
def calc_image_similarity(img1, img_list, search_path, same_path, threshold):
    """
    计算图片相似度
    :param img1: (img_path, phash值)  元组， 存放图片绝对路径和phash值
    :param img_list:  图片列表[(img_path, phash值) ,]
    :param search_path: 比对相似图片的目录路径
    :param same_path:  导出相似图片的目录路径
    :param threshold: 相似度阈值
    :return:
    """
    # start_time = time.time()
    img1_path, img1_phash = img1
    while True:
        if len(img_list):
            img2_path, img2_phash = img_list.pop()
            similary_phash = float(phash_img_similarity(img1_phash, img2_phash))
            # print("similary_phash: %s" % similary_phash)
            if similary_phash >= threshold:
                kk = round(similary_phash, 3)
                print(img1_path, img2_path, kk)
                deal_image(img1_path, img2_path, search_path, same_path)

        else:
            # print("%s一轮比对完成！用时%s秒" % (os.getpid(), time.time()-start_time))
            break


def deal_image(img1_path, img2_path, search_path, same_path):
    """
    用于剪切或拷贝相似图片
    :param img1_path: 图片1地址
    :param img2_path: 图片2地址
    :param search_path: 比对相似图片的目录路径
    :param same_path:  导出相似图片的目录路径
    :return:
    """
    global g_num
    if img1_path not in old_new_record:
        # 获取当前编号并进行编号自增
        mutex.acquire()
        tmp_num = g_num  # 当前编号
        g_num += 1
        mutex.release()
        # 拼接新路径
        new_img1_name = os.path.basename(Mytools.make_new_path(img1_path, search_path, same_path, name_simple=True))
        new_img1_name = 'S%s__%s' % (tmp_num, new_img1_name)
        new_img1_path = os.path.join(same_path, new_img1_name)
        old_new_record[img1_path] = new_img1_path

    if img2_path not in old_new_record:
        new_img1_name = old_new_record[img1_path]
        tmp_str = os.path.basename(new_img1_name).split("__")[0]  # "S%s"
        new_img2_name = os.path.basename(Mytools.make_new_path(img2_path, search_path, same_path, name_simple=True))
        new_img2_name = '%s__%s' % (tmp_str, new_img2_name)
        new_img2_path = os.path.join(same_path, new_img2_name)
        old_new_record[img2_path] = new_img2_path


def get_phash_list(dir_path):
    # img_list = []  # 用来记录图片路径和phash值  [(path, phash),]
    path_list = []
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            img_path = os.path.join(root, filename)
            path_list.append(img_path)
    # print(path_list)
    if len(path_list) > 4:
        sub_count = len(path_list) // 4
        t1 = threading.Thread(target=phash4thread, args=(path_list[: sub_count],))
        t2 = threading.Thread(target=phash4thread, args=(path_list[sub_count: sub_count * 2],))
        t3 = threading.Thread(target=phash4thread, args=(path_list[sub_count * 2: sub_count * 3],))
        # t4 = threading.Thread(target=phash4thread, args=(path_list[sub_count * 3:],))
        t1.start()
        t2.start()
        t3.start()
        # t4.start()
        phash4thread(path_list[sub_count * 3:])
    else:
        phash4thread(path_list)
    # while len(threading.enumerate()) > 1:
    #     print("\r现有线程数：", len(threading.enumerate()), end='')
    while len(g_img_list) < len(path_list):
        # print("?")
        time.sleep(0.5)


def init():
    """
    用于重置该模块的全局变量，发现模块导入之后全局变量的值一直存在，会影响下次调用该模块的方法，所以每次调用该模块方法之前需要重置全局变量
    :return:
    """
    global g_img_list, g_num, new_old_record, old_new_record, old_new_record
    g_img_list = []
    g_num = 0
    new_old_record = {}
    old_new_record = {}


def show_rate(frame, total_count):
    global g_img_list
    while True:
        finished_num = total_count - len(g_img_list)+1  # 因为最后一个元素不比较，轮空
        print("now finish %s" % finished_num)
        frame.pb1["value"] = finished_num
        # print(rate_value)
        if finished_num >= total_count:
            frame.pb1["value"] = finished_num
            break


def run(window, search_path, same_path, threshold, deal_img_mode, log_flag=True):
    """
    实现模块功能主方法，供外部模块调用
    :param search_path: 要计算相似度的目录路径
    :param same_path: 保存相似图片的目录路径
    :param threshold: 相似度阈值
    :param deal_img_mode: 相似图片处理方式 “move”  "copy"
    :param log_flag: 是否记录日志
    :return:
    """
    init()
    record_path = None  # 用于记录相似文件new_old_record文件的路径
    print("设置：相似度阈值 %s，相似图片 %s" % (threshold, deal_img_mode))
    window.scr.insert("end", "设置：相似度阈值 %s，相似图片 %s\n开始计算图片phash值...\n" % (threshold, deal_img_mode))
    # print(g_img_list, new_old_record)
    # 检测要查找相似图片的路径是否存在
    if not os.path.exists(search_path):
        print("要查找的路径 %s不存在！" % search_path)
        return
    # 检测存放相似图片的路径是否存在，不存在则创建
    if not os.path.exists(same_path):
        os.makedirs(same_path)
    print("正在计算所有图片的phash值...")
    start_phash = time.time()  # 用以记录开始计算phash的时间，后续显示phash用了多次时间
    # 计算所有图片的phash 的到数据list,数据格式[(path, phash),]
    get_phash_list(search_path)  # 多线程计算phash
    total_count = len(g_img_list)  # 记录总文件数
    window.pb1["maximum"] = total_count
    get_phash_time_msg = "遍历%s 计算phash值完成！总共%s个文件,用时%.3fs" % (search_path, total_count, (time.time() - start_phash))
    # print("计算phash值用时%s秒" % (time.time() - start_phash))
    # print(g_img_list)
    # print("一共有%d张图片待比对！" % len(g_img_list))
    window.scr.insert("end", "%s\n" % get_phash_time_msg)
    start_cmp = time.time()  # 用以记录开始计算比对的时间，后续显示比对用了多次时间
    threading.Thread(target=show_rate, args=(window, total_count)).start()

    while True:
        if len(g_img_list) <= 1:
            # g_img_list.clear()  # 发现模块加载进来之后，全局变量一直存在，这里没有清空会影响下一次调用该模块
            break
        img1 = g_img_list.pop()
        calc_image_similarity(img1, g_img_list[:], search_path, same_path, threshold)
    print("比对用时%s秒" % (time.time() - start_cmp))
    # 拷贝或剪切相似图片
    error_count = 0  # 用于记录操作失败数

    # 将old_new_record 数据生成new_old_record
    for old_path in old_new_record:
        new_path = old_new_record[old_path]
        new_old_record[new_path] = old_path

    # 操作文件
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        # print(old_file)
        try:
            if deal_img_mode == "copy":
                shutil.copy2(old_file, new_file)
            else:
                shutil.move(old_file, new_file)
        except Exception as e:
            error_count += 1
            window.scr.insert("end", "error[%s] 程序操作文件出错：  %s\n%s  ->  %s\n\n" % (error_count, e, old_file, new_file))

    # 写出文件名前后记录到文件,记录到日志文件
    local_time = time.localtime()  # 当前时间元组
    local_time1 = time.strftime("%Y%m%d%H%M%S", local_time)  # 用来生成文件名
    local_time2 = time.strftime("%Y-%m-%d %H:%M:%S", local_time)  # 用来记录传递给日志函数的时间
    if len(new_old_record):
        # 新旧文件名记录文件的路径
        record_path = os.path.join(settings.RECORD_DIR, 'same_photo %s.txt' % local_time1)
        Mytools.export_new_old_record(new_old_record, record_path)
        if deal_img_mode == "move":
            msg = "比对%s 找到相似图片%s张,剪切后新旧文件名导出到%s" % (search_path, len(new_old_record), record_path)
        else:
            msg = "比对%s 找到相似图片%s张,拷贝后新旧文件名导出到%s" % (search_path, len(new_old_record), record_path)
    else:
        msg = "比对%s 未找到相似图片！" % search_path

    total_msg = "比对%s 下%s张图片找到相似图片%s张,用时%.3fs" % (search_path, total_count, len(new_old_record), time.time() - start_phash)
    if log_flag:
        process_name = sys.argv[0]  # 当前程序名称
        logger.proces_logger("%s\n\t%s" % (process_name, get_phash_time_msg))
        logger.proces_logger(total_msg, local_time2)
        logger.operate_logger(msg, local_time2)
    window.scr.insert("end", "%s\n%s\n" % (total_msg, msg))
    return new_old_record, total_msg, record_path




