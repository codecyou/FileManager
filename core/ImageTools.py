"""图片相关的工具模块，计算图片相似度、以图搜图"""
import json
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


def phash4thread(path_list, img2phash_dict, cal_res, mutex):
    """
    计算图片文件的phash值
    :param path_list: 图片文件路径列表
    :param img2phash_dict: 图片文件和phash值对应信息，数据格式{img:phash,...}
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    :param mutex: 互斥锁
    """
    for item in path_list:
        try:  # 文件不是图片时会报错
            item_phash = phash(item)
        except UnidentifiedImageError:
            item_phash = None
            print("%s不是图像无法比对，已跳过！" % item)
        mutex.acquire()
        cal_res['count'] += 1
        # print('count:{}'.format(cal_res))
        # print(item, item_phash)
        if item_phash:
            img2phash_dict[item] = item_phash
        mutex.release()
    print('子线程结束！')


# 计算两个图片相似度函数局部敏感哈希算法
def phash_img_similarity(img1_phash, img2_phash):
    """
    :param img1_phash: 图片1phash
    :param img2_phash: 图片2phash
    :return: 图片相似度
    """
    # 计算汉明距离
    if img1_phash == img2_phash:
        return 1
    distance = bin(img1_phash ^ img2_phash).count('1')
    similary = 1 - distance / max(len(bin(img1_phash)), len(bin(img2_phash)))
    return similary


# 融合函数计算图片相似度
def calc_image_similarity(img2phash_dict, threshold):
    """
    计算图片相似度
    :param img2phash_dict: 图片文件和phash值对应信息，数据格式{img:phash,...}
    :param threshold: 相似度阈值
    :return:
    """
    # 计算图片相似度
    sim_dict = {}  # 记录相似图片的信息 格式{id编号: [img1,img2,],}
    sim_id = 0  # 相似编号，用于识别相似图片分组方便重命名
    for i in range(len(img2phash_dict)):
        # print('进度：[{}|{}]'.format(i, total_count))
        if len(img2phash_dict) <= 1:  # 只剩下最后一个则不与其他做比对
            if len(img2phash_dict):
                img2phash_dict.popitem()
            break
        sim_list = []  # 记录相似的图片文件路径
        img1, img1_phash = img2phash_dict.popitem()
        img_list = list(img2phash_dict.keys())
        for img2 in img_list:
            img2_phash = img2phash_dict[img2]
            sim_phash = float(phash_img_similarity(img1_phash, img2_phash))
            if sim_phash >= threshold:
                # print('相似图片+1')
                # 如果图片为相似图片则添加到相似结果集
                if img1 not in sim_list:
                    sim_list.append(img1)
                if img2 not in sim_list:
                    sim_list.append(img2)
                img2phash_dict.pop(img2)  # 将已经匹配为相似的图片从删除，防止重复比对
        # 判断是否本轮循环有相似图片记录，若有则添加到sim_dict中
        if len(sim_list):
            sim_id += 1
            sim_dict[sim_id] = sim_list[:]

    return sim_dict


# 融合函数计算图片相似度适配以图搜图
def calc_image_similarity4searchImg(src_img2phash_dict, dst_img2phash_dict, threshold):
    """
    计算图片相似度
    :param src_img2phash_dict: 样品图片文件和phash值对应信息，数据格式{img:phash,...}
    :param dst_img2phash_dict: 目标图片文件和phash值对应信息，数据格式{img:phash,...}
    :param threshold: 相似度阈值
    :return:
    """
    # 计算图片相似度
    sim_dict = {}  # 记录相似图片的信息 格式{id编号: [img1,img2,],}
    sim_id = 0  # 相似编号，用于识别相似图片分组方便重命名
    # 外圈遍历样本图片信息
    for i in range(len(src_img2phash_dict)):
        # print('进度：[{}|{}]'.format(i, total_count))
        if len(src_img2phash_dict) < 1:
            break
        sim_list = []  # 记录相似的图片文件路径
        img1, img1_phash = src_img2phash_dict.popitem()
        # 先自比对样本目录是否有相似图片
        if len(src_img2phash_dict) > 1:
            img_list = list(src_img2phash_dict.keys())
            for img2 in img_list:
                img2_phash = src_img2phash_dict[img2]
                sim_phash = float(phash_img_similarity(img1_phash, img2_phash))
                if sim_phash >= threshold:
                    # print('相似图片+1')
                    # 如果图片为相似图片则添加到相似结果集
                    if img1 not in sim_list:
                        sim_list.append(img1)
                    if img2 not in sim_list:
                        sim_list.append(img2)
                    src_img2phash_dict.pop(img2)  # 将已经匹配为相似的图片从删除，防止重复比对
        # 再比对目标目录图片
        # 内圈循环，拿着样本图片信息与目标图片信息计算相似度，一样则记录到sim_dict并从dst_img2phash_dict中移除，减少后续重复比对
        img_list = list(dst_img2phash_dict.keys())
        for img2 in img_list:
            img2_phash = dst_img2phash_dict[img2]
            sim_phash = float(phash_img_similarity(img1_phash, img2_phash))
            if sim_phash >= threshold:
                # print('相似图片+1')
                # 如果图片为相似图片则添加到相似结果集
                if img1 not in sim_list:
                    sim_list.append(img1)
                if img2 not in sim_list:
                    sim_list.append(img2)
                dst_img2phash_dict.pop(img2)  # 将已经匹配为相似的图片从删除，防止重复比对
        # 判断是否本轮循环有相似图片记录，若有则添加到sim_dict中
        if len(sim_list):
            sim_id += 1
            sim_dict[sim_id] = sim_list[:]
    return sim_dict


def deal_image(sim_dict, search_path, same_path):
    """
    用于剪切或拷贝相似图片
    :param sim_dict: 记录相似图片的信息 格式{id编号: [img1,img2,],}
    :param search_path: 比对相似图片的目录路径
    :param same_path:  导出相似图片的目录路径
    :return:
    """
    new_old_record = {}
    # count = 0
    for sim_id in sim_dict:
        # 拼接新路径
        img_path_list = sim_dict[sim_id]
        for img_path in img_path_list:
            # count += 1
            # print(img_path)
            new_img_name = os.path.basename(Mytools.make_new_path(img_path, search_path, same_path, name_simple=True))
            new_img_name = 'S%s__%s' % (sim_id, new_img_name)
            new_img_path = os.path.join(same_path, new_img_name)
            # if new_img_path in new_old_record:
            #     print(img_path)
            new_old_record[new_img_path] = img_path
    # print("共有相似图片 %s 张" % count)
    return new_old_record


# 适配以图搜图
def deal_image4SearchImg(sim_dict, same_path):
    """
    用于剪切或拷贝相似图片,适配以图搜图功能模块
    :param sim_dict: 记录相似图片的信息 格式{id编号: [img1,img2,],}
    :param same_path:  导出相似图片的目录路径
    :return:
    """
    new_old_record = {}
    for sim_id in sim_dict:
        # 拼接新路径
        img_path_list = sim_dict[sim_id]
        for img_path in img_path_list:
            old_name = os.path.basename(img_path)
            old_pardir_path = os.path.dirname(img_path)
            dir_str = '__[{}]'.format(old_pardir_path.replace(':', '').replace('\\', '_').replace('/', '_'))
            new_img_name = old_name + dir_str + os.path.splitext(old_name)[1]
            new_img_name = 'S%s__%s' % (sim_id, new_img_name)
            new_img_path = os.path.join(same_path, new_img_name)
            new_old_record[new_img_path] = img_path
    return new_old_record


def get_path_list(dir_path):
    """
    获取目录中的 文件路径列表
    :param dir_path: 目录路径
    :return: path_list 文件路径列表
    """
    path_list = []
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            img_path = os.path.join(root, filename)
            path_list.append(img_path)
    return path_list


def get_phash_list(path_list, img2phash_dict, cal_res):
    """
    用于计算获取图片文件的phash值字典结果
    :param path_list: 文件路径列表
    :param img2phash_dict: 图片文件和phash值对应信息，数据格式{img:phash,...}
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    :return:
    """
    mutex = threading.Lock()  # 创建互斥锁
    if len(path_list) > 4:
        sub_count = len(path_list) // 4
        t1 = threading.Thread(target=phash4thread, args=(path_list[: sub_count], img2phash_dict, cal_res, mutex))
        t2 = threading.Thread(target=phash4thread, args=(path_list[sub_count: sub_count * 2], img2phash_dict, cal_res, mutex))
        t3 = threading.Thread(target=phash4thread, args=(path_list[sub_count * 2: sub_count * 3], img2phash_dict, cal_res, mutex))
        # t4 = threading.Thread(target=phash4thread, args=(path_list[sub_count * 3:],))
        thread_list = [t1, t2, t3]
        for t in thread_list:
            t.setDaemon(True)
            t.start()
        phash4thread(path_list[sub_count * 3:], img2phash_dict, cal_res, mutex)
        print('主线程等待中。。。')
        # 判断是否所有文件已计算完成
        # 查看是否所有计算phash的子线程已结束
        while True:
            flag = True  # 是否可以所有子线程已结束
            for item in thread_list:
                if item.is_alive():
                    flag = False
            if flag is True:
                print('子线程已全部结束')
                break
            time.sleep(0.5)
    else:
        phash4thread(path_list, img2phash_dict, cal_res, mutex)


# 适配以图搜图
def get_phash_list4SearchImg(path_list, img2phash_dict, cal_res):
    """
    用于计算获取图片文件的phash值字典结果,适配以图搜图
    :param path_list: 文件路径列表
    :param img2phash_dict: 图片文件和phash值对应信息，数据格式{img:phash,...}
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    :return:
    """
    mutex = threading.Lock()  # 创建互斥锁
    if len(path_list) > 4:
        sub_count = len(path_list) // 4
        t1 = threading.Thread(target=phash4thread, args=(path_list[: sub_count], img2phash_dict, cal_res, mutex))
        t2 = threading.Thread(target=phash4thread, args=(path_list[sub_count: sub_count * 2], img2phash_dict, cal_res, mutex))
        t3 = threading.Thread(target=phash4thread, args=(path_list[sub_count * 2: sub_count * 3], img2phash_dict, cal_res, mutex))
        # t4 = threading.Thread(target=phash4thread, args=(path_list[sub_count * 3:],))
        thread_list = [t1, t2, t3]
        for t in thread_list:
            t.setDaemon(True)
            t.start()
        phash4thread(path_list[sub_count * 3:], img2phash_dict, cal_res, mutex)
        print('主线程等待中。。。')
        # 判断是否所有文件已计算完成
        # 查看是否所有计算phash的子线程已结束
        while True:
            flag = True  # 是否可以所有子线程已结束
            for item in thread_list:
                if item.is_alive():
                    flag = False
            if flag is True:
                print('子线程已全部结束')
                break
            time.sleep(0.5)
    else:
        phash4thread(path_list, img2phash_dict, cal_res, mutex)


def show_rate(win, img2phash_dict):
    """
    显示计算图片相似度的进度条
    :param win: GUI窗口对象
    :param img2phash_dict: 样品图片文件和phash值对应信息，数据格式{img:phash,...}
    """
    total_count = len(img2phash_dict)
    win.pb1["maximum"] = total_count
    win.pb1['value'] = 0
    while True:
        print(total_count)
        print(len(img2phash_dict))
        finished_num = total_count - len(img2phash_dict)
        print("now finish %s" % finished_num)
        win.pb1["value"] = finished_num
        # print(rate_value)
        if finished_num >= total_count:
            print('total_count:{}'.format(total_count))
            print(len(img2phash_dict))
            win.pb1["value"] = total_count
            break
        time.sleep(0.1)
    print('显示计算相似度进度条子线程退出！')


def show_rate_calc(win, cal_res, total_count):
    """
    显示计算进度或者操作文件进度进度条
    :param win: GUI窗口对象
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    :param total_count: 总文件数
    """
    win.pb1["maximum"] = total_count
    win.pb1["value"] = 0
    while True:
        finished_num = cal_res['count']
        # print("now finish %s" % finished_num)
        win.pb1["value"] = finished_num
        print('finished_num: {}, total_count: {}'.format(finished_num, total_count))
        if finished_num >= total_count:  # 通过判断计算次数
            win.pb1["value"] = total_count
            break
        time.sleep(0.05)
    print('显示计算进度条子线程退出！')


def export_phash_info(export_path, img2phash_dict):
    """用于导出图片phash信息到json"""
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(img2phash_dict, f, ensure_ascii=False)  # 记录已经计算过的phash信息
        print(img2phash_dict)


def find_sim_img(win, search_path, same_path, threshold, deal_img_mode, log_flag=True):
    """
    找出相似图片，供外部模块调用
    :param win: GUI窗口对象
    :param search_path: 要计算相似度的目录路径
    :param same_path: 保存相似图片的目录路径
    :param threshold: 相似度阈值
    :param deal_img_mode: 相似图片处理方式 “move”  "copy"
    :param log_flag: 是否记录日志
    :return:
    """
    record_path = None  # 用于记录相似文件new_old_record文件的路径
    cal_res = {'count': 0}  # 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    img2phash_dict = {}  # 图片文件和phash值对应信息，数据格式{img:phash,...}
    print("设置：相似度阈值 %s，相似图片 %s" % (threshold, deal_img_mode))
    time_str = Mytools.get_time_now().get('time_str')
    win.scr.insert("end", "%s  设置：相似度阈值 %s，相似图片 %s\n开始计算图片phash值...\n" % (time_str, threshold, deal_img_mode))
    # 检测要查找相似图片的路径是否存在
    if not os.path.exists(search_path):
        print("要查找的路径 %s不存在！" % search_path)
        return
    # 检测存放相似图片的路径是否存在，不存在则创建
    if not os.path.exists(same_path):
        os.makedirs(same_path)
    print("正在计算所有图片的phash值...")
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_phash = time_res.get('timestamp')  # 开始时间
    win.scr.insert("end", "%s  开始遍历文件目录...\n" % time_str)
    # 计算所有图片的phash
    search_list = get_path_list(search_path)
    time_str = Mytools.get_time_now().get('time_str')
    win.scr.insert("end", "\n%s  遍历 %s 完成，共有 %s 个文件！\n\t正在计算phash值......\n" % (time_str, search_path, len(search_list)))
    t1 = threading.Thread(target=show_rate_calc, args=(win, cal_res, len(search_list)))
    t1.setDaemon(True)
    t1.start()
    print("no1 t1.is_alive?:{}".format(t1.is_alive()))
    get_phash_list(search_list, img2phash_dict, cal_res)  # 多线程计算phash
    total_count = len(img2phash_dict)
    get_phash_time_msg = "遍历 %s 计算phash值完成！总共 %s 个图片文件,用时%.3fs" % (search_path, total_count, (time.time() - start_phash))
    win.scr.insert("end", "\n%s  %s\n" % (time_str, get_phash_time_msg))
    print("\n%s  %s\n" % (time_str, get_phash_time_msg))
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_cmp = time_res.get('timestamp')  # 用以记录开始计算比对的时间，后续显示比对用了多次时间
    # print("t1.is_alive?:{}".format(t1.is_alive()))
    t2 = threading.Thread(target=show_rate, args=(win, img2phash_dict))
    t2.setDaemon(True)
    t2.start()
    sim_dict = calc_image_similarity(img2phash_dict, threshold)
    new_old_record = deal_image(sim_dict, search_path, same_path)
    print("比对用时%s秒" % (time.time() - start_cmp))
    win.scr.insert("end", "\n%s  比对相似度完成，比对用时 %s 秒，开始操作相似文件...\n" % (time_str, (time.time() - start_cmp)))
    win.scr.see('end')
    # 拷贝或剪切相似图片
    error_count = 0  # 用于记录操作失败数
    # 操作文件
    failed_dict = {}  # 记录失败文件信息 ， 数据格式 {filepath: errormsg,}
    # 显示操作文件进度条
    deal_file_count_res = {'count': 0}  # 记录操作文件计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    t3 = threading.Thread(target=show_rate_calc, args=(win, deal_file_count_res, len(new_old_record)))
    t3.setDaemon(True)
    t3.start()
    for new_file in new_old_record:
        deal_file_count_res['count'] += 1
        old_file = new_old_record[new_file]
        try:
            if deal_img_mode == "copy":
                shutil.copy2(old_file, new_file)
            else:
                shutil.move(old_file, new_file)
        except Exception as e:
            error_count += 1
            failed_dict[old_file] = e
            win.scr.insert("end", "error[%s] 程序操作文件出错：  %s\n%s  ->  %s\n\n" % (error_count, e, old_file, new_file))

    # 写出文件名前后记录到文件,记录到日志文件
    local_time = time.localtime()  # 当前时间元组
    local_time1 = time.strftime("%Y%m%d%H%M%S", local_time)  # 用来生成文件名
    local_time2 = time.strftime("%Y-%m-%d %H:%M:%S", local_time)  # 用来记录传递给日志函数的时间
    if len(new_old_record):
        # 新旧文件名记录文件的路径
        record_path = os.path.join(settings.RECORD_DIR, 'same_photos_%s.txt' % local_time1)
        Mytools.export_new_old_record(new_old_record, record_path)
        if deal_img_mode == "move":
            msg = "【查找相似图片操作】  比对 %s 找到相似图片 %s 张,剪切后新旧文件名导出到 %s" % (search_path, len(new_old_record), record_path)
        else:
            msg = "【查找相似图片操作】  比对 %s 找到相似图片 %s 张,拷贝后新旧文件名导出到 %s" % (search_path, len(new_old_record), record_path)
    else:
        msg = "【查找相似图片操作】  比对 %s 未找到相似图片！" % search_path

    total_msg = "比对 %s 下 %s 张图片找到相似图片 %s 张,用时%.3fs" % (search_path, total_count, len(new_old_record), time.time() - start_phash)
    if log_flag:
        # 输出显示操作失败信息
        if len(failed_dict):
            win.scr.insert("end", "操作 %s 个文件失败，失败信息如下：\n" % error_count)
            i = 0  # 记录文件编号
            for filepath in failed_dict:
                i += 1
                win.scr.insert("end", "ERROR:(%s/%s)  %s 操作过程出错！错误：%s\n" % (i, error_count, filepath, failed_dict[filepath]))

        process_name = sys.argv[0]  # 当前程序名称
        logger.proces_logger("%s\n\t%s" % (process_name, get_phash_time_msg))
        logger.proces_logger('【查找相似图片操作】  %s' % total_msg, local_time2)
        logger.operate_logger(msg, local_time2)
    win.scr.insert("end", "\n\n%s  %s\n%s\n" % (local_time2, total_msg, msg))
    win.scr.see('end')

    return new_old_record, total_msg, record_path


def search_img_by_img(win, search_path, dst_path, same_path, threshold, deal_img_mode, log_flag=True):
    """
    用于实现以图搜图功能
    :param win: GUI窗口对象
    :param search_path: 要搜索的对象，即要从原有图片中找出相似图片的新增图片
    :param dst_path: 原有图片目录地址
    :param same_path: 保存相似图片的目录路径
    :param threshold: 相似度阈值
    :param deal_img_mode: 相似图片处理方式 “move”  "copy"
    :param log_flag: 是否记录日志
    :return:
    """
    record_path = None  # 用于记录相似文件new_old_record文件的路径
    cal_res = {'count': 0}  # 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    src_img2phash_dict = {}  # 样品图片文件和phash值对应信息，数据格式{img:phash,...}
    dst_img2phash_dict = {}  # 目标图片文件和phash值对应信息，数据格式{img:phash,...}
    print("设置：相似度阈值 %s，相似图片 %s" % (threshold, deal_img_mode))
    # 检测要查找相似图片的路径是否存在
    if not os.path.exists(search_path):
        print("要查找的路径 %s不存在！" % search_path)
        return
    # 检测存放相似图片的路径是否存在，不存在则创建
    if not os.path.exists(same_path):
        os.makedirs(same_path)
    print("正在计算所有图片的phash值...")
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_phash = time_res.get('timestamp')  # 开始时间
    win.scr.insert("end", "%s  开始遍历文件目录...\n" % time_str)
    # 计算所有图片的phash
    search_list = get_path_list(search_path)
    time_str = Mytools.get_time_now().get('time_str')
    win.scr.insert("end", "\n%s  遍历 %s 完成，共有 %s 个文件！\n\t正在计算phash值......\n" % (time_str, search_path, len(search_list)))
    t1 = threading.Thread(target=show_rate_calc, args=(win, cal_res, len(search_list)))
    t1.setDaemon(True)
    t1.start()
    print("no1 t1.is_alive?:{}".format(t1.is_alive()))
    get_phash_list4SearchImg(search_list, src_img2phash_dict, cal_res)  # 多线程计算phash
    # print('src_img2phash_dict:\n{}'.format(src_img2phash_dict))
    time_str = Mytools.get_time_now().get('time_str')
    get_phash_time_msg = "遍历%s 计算phash值完成！总共 %s 个图片文件,用时%.3fs" % (search_path, len(src_img2phash_dict), (time.time() - start_phash))
    win.scr.insert("end", "\n%s  %s\n\t正在获取原有图片 %s 的phash值......\n" % (time_str, get_phash_time_msg, dst_path))
    # 获取目标目录图片信息
    if os.path.isdir(dst_path):
        dst_path_list = get_path_list(dst_path)  # 获取原有图片的phash值
        cal_res = {'count': 0}  # 记录计算技术的变量，由于子线程和址传递的关系故该变量格式为{'count': 0}
        t2 = threading.Thread(target=show_rate_calc, args=(win, cal_res, len(dst_path_list)))
        t2.setDaemon(True)
        t2.start()
        get_phash_list4SearchImg(dst_path_list, dst_img2phash_dict, cal_res)
        # print('dst_img2phash_dict:\n{}'.format(dst_img2phash_dict))
    elif dst_path.endswith(".json"):
        with open(dst_path, 'r', encoding='utf-8') as f:
            tmp_img2phash_dict = json.load(f)  # 记录配置信息
            dst_img2phash_dict.clear()
            dst_img2phash_dict.update(tmp_img2phash_dict)  # 这两步用来确保内存地址未发生变化
    else:
        print("输入的原有图片phash记录文件格式有误！请检查！")
        win.scr.insert("end", "输入的原有图片phash记录文件格式有误！请检查！\n")
    # start_cmp = time.time()  # 用以记录开始计算比对的时间，后续显示比对用了多次时间
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_cmp = time_res.get('timestamp')   # 用以记录开始计算比对的时间，后续显示比对用了多次时间
    t3 = threading.Thread(target=show_rate, args=(win, src_img2phash_dict))
    t3.setDaemon(True)
    t3.start()
    win.scr.insert("end", "\n%s  获取原有图片phash信息完成，开始搜索相似图片......\n" % time_str)
    sim_dict = calc_image_similarity4searchImg(src_img2phash_dict, dst_img2phash_dict, threshold)
    new_old_record = deal_image4SearchImg(sim_dict, same_path)
    win.scr.insert("end", "\n%s  比对相似度完成，比对用时 %s 秒，开始操作相似文件...\n" % (time_str, (time.time() - start_cmp)))
    win.scr.see('end')
    # 拷贝或剪切相似图片
    # 显示操作文件进度条
    deal_file_count_res = {'count': 0}  # 记录操作文件计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    t4 = threading.Thread(target=show_rate_calc, args=(win, deal_file_count_res, len(new_old_record)))
    t4.setDaemon(True)
    t4.start()
    for new_file in new_old_record:
        deal_file_count_res['count'] += 1
        old_file = new_old_record[new_file]
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
        record_path = os.path.join(settings.RECORD_DIR, 'same_photos_%s.txt' % local_time1)
        Mytools.export_new_old_record(new_old_record, record_path)
        if deal_img_mode == "move":
            msg = "以图搜图完成！找到相似图片 %s 张,剪切后新旧文件名导出到 %s" % (len(new_old_record), record_path)
        else:
            msg = "以图搜图完成！找到相似图片 %s 张,拷贝后新旧文件名导出到 %s" % (len(new_old_record), record_path)
    else:
        msg = "以图搜图完成！ %s 未找到相似图片！" % search_path

    total_msg = "以图搜图完成！找到相似图片 %s 张,用时%.3fs" % (len(new_old_record), time.time() - start_phash)
    if log_flag:
        process_name = sys.argv[0]  # 当前程序名称
        logger.proces_logger("%s\n\t%s" % (process_name, get_phash_time_msg))
        logger.proces_logger(total_msg, local_time2)
        logger.operate_logger('【以图搜图操作】  %s' % msg, local_time2)
    win.scr.insert("end", "\n\n%s  %s\n%s\n" % (local_time2, total_msg, msg))
    win.scr.see('end')
    return new_old_record, total_msg, record_path

