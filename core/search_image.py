#! /usr/bin/python3
# -*- encoding=utf-8 -*-
""""以图搜图模块"""
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
import json


mutex = threading.Lock()  # 创建互斥锁


# threshold = 0.98  # 最终相似度判断阈值

# search_path = r'C:\Users\pro\Desktop\金所泫'
# search_path = r'C:\Users\pro\Desktop\test'  # 需要比对的路径
# search_path = r'C:\Users\pro\Desktop\test'
# same_path = r'C:\Users\pro\Desktop\test1'  # 相似图片存放路径
# deal_img_mode = "copy"  # 选择处理相似图片的模式"copy" 或 "move"

new_old_record = {}  # 用以记录剪切或复制前后的文件名，方便后面程序还原文件 格式{newfilename:oldfilename,}
g_img_list = []  # 用来记录图片路径和phash值  [(path, phash),]
g_dst_img_list = []  # 用来记录原有图片路径和phash值  [(path, phash),] ,用于以图搜图功能


# 计算图片的局部哈希值--pHash
def phash(img_path):
    """
    :param img_path: 图片路径
    :return: 返回图片的局部hash值
    """
    # 读取图片
    img = Image.open(img_path)
    img = img.resize((8, 8), Image.ANTIALIAS).convert('L')
    avg = reduce(lambda x, y: x + y, img.getdata()) / 64.
    hash_value = reduce(lambda x, y: x | (y[1] << y[0]), enumerate(map(lambda i: 0 if i < avg else 1, img.getdata())), 0)
    return hash_value


def phash4thread(gl_img_list, path_list):
    for item in path_list:
        try:  # 文件不是图片时会报错
            item_phash = phash(item)
        except UnidentifiedImageError:
            print("%s不是图像无法比对，已跳过！" % item)
            return
        mutex.acquire()
        gl_img_list.append((item, item_phash))
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
def calc_image_similarity(img1, img_list, search_path, dst_path, same_path, threshold):
    """
    计算图片相似度
    :param img1: (img_path, phash值)  元组， 存放图片绝对路径和phash值
    :param img_list:  图片列表[(img_path, phash值) ,]
    :param search_path: 比对相似图片的目录路径
    :param same_path:  导出相似图片的目录路径
    :param threshold: 相似度阈值
    :return:
    """
    img1_path, img1_phash = img1
    for item in img_list:
        img2_path, img2_phash = item
        similary_phash = float(phash_img_similarity(img1_phash, img2_phash))
        if similary_phash >= threshold:
            kk = round(similary_phash, 3)
            print(img1_path, img2_path, kk)
            deal_image(img1_path, img2_path, search_path, dst_path, same_path)


def deal_image(img1_path, img2_path, search_path, dst_path, same_path):
    """
    用于剪切或拷贝相似图片
    :param img1_path: 图片1地址
    :param img2_path: 图片2地址
    :param search_path: 比对相似图片的目录路径
    :param same_path:  导出相似图片的目录路径
    :return:
    """

    if img1_path not in new_old_record.values():
        new_img1_path = Mytools.make_new_path(img1_path, search_path, same_path)
        new_old_record[new_img1_path] = img1_path
    if img2_path not in new_old_record.values():
        new_img1_name = os.path.basename(Mytools.make_new_path(img1_path, search_path, same_path, name_simple=True))
        new_img2_name = os.path.basename(Mytools.make_new_path(img2_path, dst_path, same_path, name_simple=True))
        new_img2_name = '%s__%s' % (new_img1_name, new_img2_name)
        new_img2_path = os.path.join(same_path, new_img2_name)
        new_old_record[new_img2_path] = img2_path


def get_path_list(dir_path):
    """获取目录中的 文件路径列表"""
    # img_list = []  # 用来记录图片路径和phash值  [(path, phash),]
    path_list = []
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            img_path = os.path.join(root, filename)
            path_list.append(img_path)
    # print(path_list)
    return path_list


def get_phash_list(gl_img_list, path_list):
    """用于计算列表中的图片文件的phash值"""
    if len(path_list) > 4:
        sub_count = len(path_list) // 4
        t1 = threading.Thread(target=phash4thread, args=(gl_img_list, path_list[: sub_count],))
        t2 = threading.Thread(target=phash4thread, args=(gl_img_list, path_list[sub_count: sub_count * 2],))
        t3 = threading.Thread(target=phash4thread, args=(gl_img_list, path_list[sub_count * 2: sub_count * 3],))
        # t4 = threading.Thread(target=phash4thread, args=(gl_img_list, path_list[sub_count * 3:],))
        t1.start()
        t2.start()
        t3.start()
        # t4.start()
        phash4thread(gl_img_list, path_list[sub_count * 3:])
    else:
        phash4thread(gl_img_list, path_list)
    # while len(threading.enumerate()) > 1:
    #     print("\r现有线程数：", len(threading.enumerate()), end='')
    while len(gl_img_list) < len(path_list):
        # print("?")
        time.sleep(0.1)


def init():
    """
    用于重置该模块的全局变量，发现模块导入之后全局变量的值一直存在，会影响下次调用该模块的方法，所以每次调用该模块方法之前需要重置全局变量
    :return:
    """
    global g_img_list, g_dst_img_list, new_old_record
    g_img_list = []
    g_dst_img_list = []
    new_old_record = {}


def show_rate(frame, total_count):
    global g_img_list
    while True:
        finished_num = total_count - len(g_img_list)+1
        if finished_num >= total_count:
            frame.pb1["value"] = finished_num
            break
        print("now finish %s" % finished_num)
        frame.pb1["value"] = finished_num
        # print(rate_value)


def export_phash_info(export_path):
    """用于导出图片phash信息到json"""
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(g_dst_img_list, f)  # 记录配置信息
        print(g_dst_img_list)


def run(window, search_path, dst_path, same_path, threshold, deal_img_mode, log_flag=True):
    """
    用于实现以图搜图功能
    :param window: GUI窗口对象
    :param search_path: 要搜索的对象，即要从原有图片中找出相似图片的新增图片
    :param dst_path: 原有图片目录地址
    :param same_path: 保存相似图片的目录路径
    :param threshold: 相似度阈值
    :param deal_img_mode: 相似图片处理方式 “move”  "copy"
    :param log_flag: 是否记录日志
    :return:
    """
    global g_img_list, g_dst_img_list
    init()
    print("设置：相似度阈值 %s，相似图片 %s" % (threshold, deal_img_mode))
    # print(g_img_list, new_old_record)
    # 检测要查找相似图片的路径是否存在
    if not os.path.exists(search_path):
        print("要查找的路径 %s不存在！" % search_path)
        return
    # 检测存放相似图片的路径是否存在，不存在则创建
    if not os.path.exists(same_path):
        os.makedirs(same_path)
    print("正在计算所有图片的phash值...")
    window.scr.insert("end", "正在计算所有图片的phash值...\n")
    start_phash = time.time()  # 用以记录开始计算phash的时间，后续显示phash用了多次时间
    # 计算所有图片的phash 的到数据list,数据格式[(path, phash),]
    search_list = get_path_list(search_path)
    window.scr.insert("end", "遍历%s 完成，共有%s 个文件！\n正在计算phash值......\n" % (search_path, len(search_list)))
    get_phash_list(g_img_list, search_list)  # 多线程计算phash
    total_count = len(g_img_list)  # 记录总文件数
    window.pb1["maximum"] = total_count
    get_phash_time_msg = "遍历%s 计算phash值完成！总共%s个文件,用时%.3fs" % (search_path, total_count, (time.time() - start_phash))
    # print("计算phash值用时%s秒" % (time.time() - start_phash))
    # print(g_img_list)
    # print("一共有%d张图片待比对！" % len(g_img_list))
    window.scr.insert("end", "%s\n正在获取原有图片%s 的phash值......\n" % (get_phash_time_msg, dst_path))
    if os.path.isdir(dst_path):
        dst_path_list = get_path_list(dst_path)  # 获取原有图片的phash值
        get_phash_list(g_dst_img_list, dst_path_list)
    elif dst_path.endswith(".json"):
        with open(dst_path, 'r', encoding='utf-8') as f:
            g_dst_img_list = json.load(f)  # 记录配置信息
    else:
        print("输入的原有图片phash记录文件格式有误！请检查！")
        window.scr.insert("end", "输入的原有图片phash记录文件格式有误！请检查！\n" )
    start_cmp = time.time()  # 用以记录开始计算比对的时间，后续显示比对用了多次时间
    threading.Thread(target=show_rate, args=(window, total_count)).start()
    window.scr.insert("end", "获取原有图片phash信息完成，开始搜索相似图片......\n")
    while True:
        if len(g_img_list) < 1:
            # g_img_list.clear()  # 发现模块加载进来之后，全局变量一直存在，这里没有清空会影响下一次调用该模块
            break
        img1 = g_img_list.pop()
        calc_image_similarity(img1, g_dst_img_list, search_path, dst_path, same_path, threshold)
    print("比对用时%s秒" % (time.time() - start_cmp))
    # 拷贝或剪切相似图片
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        # print(old_file)
        if deal_img_mode == "copy":
            shutil.copy2(old_file, new_file)
        else:
            shutil.move(old_file, new_file)

    # 写出文件名前后记录到文件,记录到日志文件
    local_time = time.localtime()  # 当前时间元组
    local_time1 = time.strftime("%Y%m%d%H%M%S", local_time)  # 用来生成文件名
    local_time2 = time.strftime("%Y-%m-%d %H:%M:%S", local_time)  # 用来记录传递给日志函数的时间
    if len(new_old_record):
        # 新旧文件名记录文件的路径
        record_path = os.path.join(settings.RECORD_DIR, 'same_photo %s.txt' % local_time1)
        Mytools.export_new_old_record(new_old_record, record_path)
        if deal_img_mode == "move":
            msg = "以图搜图完成！找到相似图片%s张,剪切后新旧文件名导出到%s" % (len(new_old_record), record_path)
        else:
            msg = "以图搜图完成！找到相似图片%s张,拷贝后新旧文件名导出到%s" % (len(new_old_record), record_path)
    else:
        msg = "以图搜图完成！未找到相似图片！" % search_path

    total_msg = "以图搜图完成！找到相似图片%s张,用时%.3fs" % (len(new_old_record), time.time() - start_phash)
    if log_flag:
        process_name = sys.argv[0]  # 当前程序名称
        logger.proces_logger("%s\n\t%s" % (process_name, get_phash_time_msg))
        logger.proces_logger(total_msg, local_time2)
        logger.operate_logger(msg, local_time2)
    window.scr.insert("end", "%s\n%s\n" % (total_msg, msg))
    return new_old_record, total_msg



