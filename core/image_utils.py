"""图片相关的工具模块，计算图片相似度、以图搜图"""
from functools import reduce
from core import common_utils
from core.logger import logger
from conf import settings
import os
import time
import threading
import sqlite3
from natsort import natsorted
from tkinter import messagebox as mBox
from PIL import Image, UnidentifiedImageError
from PIL.JpegImagePlugin import JpegImageFile
from pillow_heif import register_heif_opener
register_heif_opener()


# 计算图片的局部哈希值--pHash
def phash(img_path):
    """
    :param img_path: 图片路径
    :return: 返回图片的局部hash值
    """
    # 读取图片
    img = Image.open(img_path)
    # img = img.resize((8, 8), Image.ANTIALIAS).convert('L')
    # module 'PIL.Image' has no attribute 'ANTIALIAS'
    # 在新版本pillow(10.0.0之后)Image.ANTIALIAS 被移除了,取而代之的是Image.LANCZOS
    img = img.resize((8, 8), Image.LANCZOS).convert('L')
    avg = reduce(lambda x, y: x + y, img.getdata()) / 64
    hash_value = reduce(lambda x, y: x | (y[1] << y[0]), enumerate(map(lambda i: 0 if i < avg else 1, img.getdata())), 0)
    # print("image: %s  phash: %s  typeofphash:%s" % (img_path, hash_value, type(hash_value)))
    return hash_value


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
    :return: sim_dict {sim_id: [imgs, img2,]}
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


# 融合函数计算图片相似度
def calc_image_similarity_sub(img2phash_dict, threshold):
    """
    计算图片相似度  仅计算相邻图片
    :param img2phash_dict: 图片文件和phash值对应信息，数据格式{img:phash,...}
    :param threshold: 相似度阈值
    :return:sim_dict {sim_id: [imgs, img2,]}
    """
    # 计算图片相似度
    sim_dict = {}  # 记录相似图片的信息 格式{id编号: [img1,img2,],}
    sim_id = 0  # 相似编号，用于识别相似图片分组方便重命名
    sim_list = []  # 记录相似的图片文件路径
    # 1.先将图片按顺序排序
    img_list = natsorted(list(img2phash_dict.keys()))  # 文件名按自然数排序
    # 2.再取图片集合 前 len-1 个，每个元素跟下一个元素计算相似度，若相似则添加到sim_list，如果第一个元素不在simlist，sim_id增1，直到两个元素不相似则重置sim_list
    for i in range(len(img_list) - 1):
        img1 = img_list[i]
        img1_phash = img2phash_dict.pop(img1)
        img2 = (img_list[i+1])
        img2_phash = img2phash_dict[img2]
        sim_phash = float(phash_img_similarity(img1_phash, img2_phash))
        if sim_phash >= threshold:
            if img1 not in sim_list:
                sim_id += 1
                sim_list.append(img1)
            if img2 not in sim_list:
                sim_list.append(img2)
            sim_dict[sim_id] = sim_list
        else:
            sim_list = []
    img2phash_dict.popitem()  # 去除多出来的单个无法配对的最后一个
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
            new_img_name = os.path.basename(common_utils.make_new_path(img_path, search_path, same_path, name_simple=True))
            new_img_name = 'S%s__%s' % (sim_id, new_img_name)
            new_img_path = os.path.join(same_path, new_img_name)
            # if new_img_path in new_old_record:
            #     print(img_path)
            new_old_record[new_img_path] = img_path
    # print("共有相似图片 %s 张" % count)
    return new_old_record

# 适配以图搜图
def deal_image4SearchImg(sim_dict, save_dir):
    """
    用于剪切或拷贝相似图片,适配以图搜图功能模块
    :param sim_dict: 记录相似图片的信息 格式{id编号: [img1,img2,],}
    :param save_dir:  导出相似图片的目录路径
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
            new_img_path = os.path.join(save_dir, new_img_name)
            new_old_record[new_img_path] = img_path
    return new_old_record


def phash4thread(path_list, file_infos, insert_infos, update_infos, img2phash_dict, cal_res, mutex):
    """
    计算图片文件的phash值
    :param path_list: 图片文件路径列表
    :param file_infos: 文件信息
    :param insert_infos: 要插入数据库的数据
    :param update_infos: 有更新的文件信息
    :param img2phash_dict: 图片文件和phash值对应信息,数据格式{img:phash,...}
    :param cal_res: 记录计算计数的变量,由于子线程和址传递的关系故该变量格式为{'count':0}
    :param mutex: 互斥锁
    """
    res_insert = {}
    tmp_img2phash_dict = {}
    for _path in path_list:
        try:  # 文件不是图片时会报错
            size = file_infos[_path]['size']
            mtimestamp = file_infos[_path]['mtimestamp']
            mtime = file_infos[_path]['mtime']
            name = os.path.basename(_path)
            item_phash = phash(_path)
            res_insert[_path] = {'name': name, 'size': size, 'mtime': mtime, 'phash': item_phash, "mtimestamp":mtimestamp}
        except Exception:
            item_phash = None
            print("%s不是图像无法比对,已跳过!" % _path)
        if item_phash:
            tmp_img2phash_dict[_path] = item_phash
        # 进度值更新
        mutex.acquire()
        cal_res['count'] += 1
        mutex.release()
    # 记录有更新的文件信息
    img2phash_dict.update(tmp_img2phash_dict)
    if res_insert:
        mutex.acquire()
        insert_infos.update(res_insert)
        mutex.release()


def get_phash_list(file_infos, insert_infos, update_infos, img2phash_dict, cal_res):
    """
    用于计算获取图片文件的phash值字典结果
    :param file_infos: 文件信息
    :param insert_infos: 新增的文件信息
    :param update_infos: 有更新的文件信息
    :param img2phash_dict: 图片文件和phash值对应信息，数据格式{img:phash,...}
    :param sql_img2phash_dict: 数据库图片文件和phash值对应信息，数据格式{img:phash,...}
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    :return:
    """
    mutex = threading.Lock()  # 创建互斥锁
    path_list = list(file_infos.keys())
    if len(path_list) < 40:  # 数量少则单线程计算
        phash4thread(path_list, file_infos, insert_infos, update_infos, img2phash_dict, cal_res, mutex)
    else:  # 多线程
        num = len(path_list) // settings.CALC_THREAD_NUM
        thread_list = []
        for i in range(settings.CALC_THREAD_NUM-1):
            t = threading.Thread(target=phash4thread, args=(path_list[num*i: num*(i+1)], file_infos, insert_infos, update_infos, img2phash_dict, cal_res, mutex))
            t.daemon = True
            t.start()
            thread_list.append(t)
        phash4thread(path_list[num*(settings.CALC_THREAD_NUM-1):], file_infos, insert_infos, update_infos, img2phash_dict, cal_res, mutex)
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


def get_need_phash(file_infos, sql_file2phash_dict, dst_file2phash_dict):
    """获取需要计算的文件信息
    :param file_infos: 文件信息{path:{'name':name,'size':size,'mtime':mtime,'mtimestamp':mtimestamp}}
    :param sql_file2phash_dict: 数据库记录
    :param dst_file2phash_dict: 用于相似值比对的记录
    :return: need_phash_file_infos 需要计算phash的文件信息
    """
    need_phash_file_infos = {}  # 需要计算phash的图片信息
    for _path, file_info in file_infos.items():
        name = file_infos[_path]['name']
        size = file_infos[_path]['size']
        mtimestamp = file_infos[_path]['mtimestamp']
        if name in sql_file2phash_dict:
            if (size == sql_file2phash_dict[name]['size']) and (mtimestamp == sql_file2phash_dict[name]['mtimestamp']):
                dst_file2phash_dict[_path] = sql_file2phash_dict[name]['phash']
                continue
        need_phash_file_infos[_path] = file_info
    return need_phash_file_infos


def get_sql_res(table_name):
    """用于获取数据库信息"""
    conn = sqlite3.connect(settings.DATABASE['path'])
    cur = conn.cursor()
    sql_res = {}  # 数据库记录
    sql = "select filename,filesize,mtime,phash from %s where is_delete=0;" % table_name
    cur.execute(sql)
    res = cur.fetchall()
    if len(res):
        for item in res:
            sql_res[item[0]] = {'size': item[1], 'mtimestamp': item[2], 'phash': int(item[3])}
    cur.close()
    conn.close()
    return sql_res


def insert_db(file_infos, table_name):
    """用于将数据保存到数据库"""
    conn = sqlite3.connect(settings.DATABASE['path'])
    cur = conn.cursor()
    sql = "insert into %s(filename,filesize,mtime,phash) values(?,?,?,?);" % table_name
    for _path in file_infos:
        name = file_infos[_path]['name']
        size = file_infos[_path]['size']
        mtime = file_infos[_path]['mtimestamp']
        _phash = file_infos[_path].get('phash')
        if not _phash:
            continue
        cur.execute(sql, (name, size, mtime, str(_phash)))
    conn.commit()
    cur.close()
    conn.close()


def update_db(file_infos, table_name):
    """用于将数据保存到数据库"""
    conn = sqlite3.connect(settings.DATABASE['path'])
    cur = conn.cursor()
    sql = "update %s set filesize=?,mtime=?,phash=? where filename=?;" % table_name
    for _path in file_infos:
        name = file_infos[_path]['name']
        size = file_infos[_path]['size']
        mtime = file_infos[_path]['mtimestamp']
        _phash = file_infos[_path].get('phash')
        if not _phash:
            continue
        cur.execute(sql, (size, mtime, str(_phash), name))
    conn.commit()
    cur.close()
    conn.close()


def get_images_phash(self, src_dir, db_flag):
    """
    获取目录下所有图片phash值
    :param src_dir: 要计算相似度的目录路径
    :param db_flag: 使用启用数据库记录加速运算
    :return:img2phash_dict 图片文件和phash值对应信息,数据格式{img:phash,...}
    
    """
    img2phash_dict = {}  # 图片文件和phash值对应信息,数据格式{img:phash,...}

    time_res = common_utils.get_times_now()
    time_str = time_res.get('time_str')
    time_start = time_res.get('timestamp')  # 开始时间
    self.scr.insert("end", "\n%s  计算图像phash值...\n" % time_str)

    # 获取数据库信息
    if db_flag:
        sql_img2phash_dict = get_sql_res("images")
    else:
        sql_img2phash_dict = {}

    # 计算所有图片的phash值
    search_list = common_utils.get_files_by_filetype(src_dir, 'image')
    file_infos = common_utils.get_files_info_by_list(search_list)

    # 过滤数据库已有记录
    need_phash_file_infos = get_need_phash(file_infos, sql_img2phash_dict, img2phash_dict)

    # 计算图片phash
    self.is_complete = False  # 重置任务进度状态
    cal_res = {'count': 0}  # 记录计算计数的变量,由于子线程和址传递的关系故该变量格式为{'count':0}
    t = threading.Thread(target=self.show_rate_calc, args=(cal_res, len(need_phash_file_infos)))
    t.daemon = True
    t.start()
    update_infos = {}  # 有更新的文件信息 数据格式{path: {'name': name, 'size': size, 'mtime': mtime, 'phash':phash}, }
    insert_infos = {}  # 新增的文件信息 数据格式{path: {'name': name, 'size': size, 'mtime': mtime, 'phash':phash}, }
    self.scr.insert("end", "\n%s  遍历 %s 完成，共有 %s 个图像文件 ( %s 个文件需要计算)\n\t正在计算phash值......\n" % (common_utils.get_times_now().get('time_str'), src_dir, len(search_list), len(need_phash_file_infos)))
    get_phash_list(need_phash_file_infos, insert_infos, update_infos, img2phash_dict, cal_res)  # 多线程计算phash
    self.is_complete = True
    logger.debug("need_phash_file_infos:%s, insert_infos:%s, update_infos:%s, img2phash_dict:%s" % (need_phash_file_infos, insert_infos, update_infos, img2phash_dict))
    msg = "\n%s  计算图像phash值完成!总共 %s 个文件,用时 %.3f 秒\n" % (common_utils.get_times_now().get('time_str'), len(img2phash_dict), time.time() - time_start)
    self.scr.insert("end", msg)
    # 记录到数据库
    if db_flag:
        update_db(update_infos, "images")
        insert_db(insert_infos, "images")
    return img2phash_dict


def calc_image_sim(self, img2phash_dict, threshold):
    """比对图片相似度,带GUI组件交互"""
    time_res = common_utils.get_times_now()
    time_str = time_res.get('time_str')
    time_start = time_res.get('timestamp')
    self.scr.insert("end", "\n%s  开始计算相似度...\n" % time_str)
    # 新建进度条显示子线程
    self.is_complete = False
    t = threading.Thread(target=self.show_rate_sim, args=(img2phash_dict,))
    t.daemon = True
    t.start()
    # 计算相似度
    if self.sub_flag.get():  # 仅计算相邻图片
        sim_dict = calc_image_similarity_sub(img2phash_dict, threshold)
    else:  # 计算所有图片
        sim_dict = calc_image_similarity(img2phash_dict, threshold)
    self.is_complete = True
    msg = "\n%s  计算相似度完成!用时 %.3f 秒\n" % (common_utils.get_times_now().get('time_str'), time.time() - time_start)
    self.scr.insert("end", msg)
    return sim_dict


def calc_image_sim4search(self, eg_img2phash_dict, dst_img2phash_dict, threshold):
    """比对图片相似度,适配以图搜图,带GUI组件交互"""
    time_res = common_utils.get_times_now()
    time_str = time_res.get('time_str')
    time_start = time_res.get('timestamp')
    self.scr.insert("end", "\n%s  开始计算相似度...\n" % time_str)
    # 新建进度条显示子线程
    self.is_complete = False
    t = threading.Thread(target=self.show_rate_sim, args=(eg_img2phash_dict,))
    t.daemon = True
    t.start()
    # 计算相似度
    sim_dict = calc_image_similarity4searchImg(eg_img2phash_dict, dst_img2phash_dict, threshold)
    self.is_complete = True
    msg = "\n%s  计算相似度完成!用时 %.3f 秒\n" % (common_utils.get_times_now().get('time_str'), time.time() - time_start)
    self.scr.insert("end", msg)
    return sim_dict


def find_sim_img(self, src_dir, dst_dir, threshold, deal_img_mode, db_flag):
    """
    找出相似图片，供外部模块调用
    :param src_dir: 要计算相似度的目录路径
    :param dst_dir: 保存相似图片的目录路径
    :param threshold: 相似度阈值
    :param deal_img_mode: 相似图片处理方式 “move”  "copy"
    :param db_flag: 使用启用数据库记录加速运算
    :return:
    """
    start_time = common_utils.get_times_now().get('timestamp')  # 开始时间

    # 计算图片phash
    img2phash_dict = get_images_phash(self, src_dir, db_flag)

    # 计算图片相似度
    sim_dict = calc_image_sim(self, img2phash_dict, threshold)

    self.scr.insert('end', '\n%s  开始操作文件...\n' % common_utils.get_times_now().get('time_str'))

    # 生成new_old_record
    new_old_record = deal_image(sim_dict, src_dir, dst_dir)

    # 操作文件
    res = move_files(deal_img_mode, new_old_record, dst_dir)
    total_msg = res['msg']
    self.record_path = res['record_path']
    msg = "查找相似图片完成!比对 %s ,总共发现相似图片 %s 张,用时 %.3f 秒" % (src_dir, len(new_old_record), time.time() - start_time)
    logger.info('【查找相似图片】  %s %s' % (msg, total_msg))
    self.scr.insert("end", "\n%s  %s\n\t%s\n" % (common_utils.get_times_now().get('time_str'), msg, total_msg))
    self.scr.see("end")
    if self.record_path:
        self.btn_restore.config(state='normal')
    self.btn_show.config(state='normal')
    mBox.showinfo("任务完成", "查找相似图片完成!")


def search_img_by_img(self, eg_dir, src_dir, dst_dir, threshold, deal_img_mode, db_flag):
    """
    用于实现以图搜图功能
    :param eg_dir: 样品目录
    :param src_dir: 原有图片目录地址
    :param dst_dir: 保存相似图片的目录路径
    :param threshold: 相似度阈值
    :param deal_img_mode: 相似图片处理方式 “move”  "copy"
    :param db_flag: 使用启用数据库记录加速运算
    :return:
    """
    start_time = common_utils.get_times_now().get('timestamp')  # 开始时间

    # 计算图片phash
    eg_img2phash_dict = get_images_phash(self, eg_dir, db_flag)
    src_img2phash_dict = get_images_phash(self, src_dir, db_flag)

    # 计算图片相似度
    sim_dict = calc_image_sim4search(self, eg_img2phash_dict, src_img2phash_dict, threshold)

    self.scr.insert('end', '\n%s  开始操作文件...\n' % common_utils.get_times_now().get('time_str'))

    # 生成new_old_record
    new_old_record = deal_image4SearchImg(sim_dict, dst_dir)

    # 操作文件
    res = move_files(deal_img_mode, new_old_record, dst_dir)
    total_msg = res['msg']
    self.record_path = res['record_path']
    msg = "以图搜图完成!样本目录: %s ,源目录: %s ,总共发现相似图片 %s 张,用时 %.3f 秒" % (eg_dir, src_dir, len(new_old_record), time.time() - start_time)
    logger.info('【以图搜图】  %s %s' % (msg, total_msg))
    self.scr.insert("end", "\n%s  %s\n\t%s\n" % (common_utils.get_times_now().get('time_str'), msg, total_msg))
    self.scr.see("end")
    if self.record_path:
        self.btn_restore.config(state='normal')
    self.btn_show.config(state='normal')
    mBox.showinfo("任务完成", "以图搜图完成!")


def move_files(deal_file_mode, new_old_record, save_dir_path):
    """操作文件"""
    record_path = None  # 记录new_old_record文件路径
    if deal_file_mode == "copy":
        func = common_utils.copy_file  # 拷贝方法
    else:
        func = common_utils.move_file

    # 操作文件
    failed_list = []  # 用于记录操作失败的文件信息
    for new_file, old_file in new_old_record.items():
        try:
            func(old_file, new_file)
        except Exception as e:
            failed_list.append(old_file)
            logger.debug("操作 %s 文件失败,详情请查看错误日志!" % old_file)
            logger.error( '%s  error: %s' % (old_file, e))

    time_res = common_utils.get_times_now()
    total_msg = ''
    if len(new_old_record):
        record_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("new_old_record", time_res.get('time_num_str')))
        common_utils.export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        total_msg = "相似文件 %s 到 %s,文件新旧文件名记录到 %s" % (deal_file_mode, save_dir_path, record_path)
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("failed", time_res.get('time_num_str')))
            total_msg += "\n\t%s 个文件操作失败,文件信息导出到 %s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                f.write('\n'.join(failed_list) + '\n')
    return {'msg':total_msg, 'record_path':record_path, "failed_list": failed_list}


# 以下代码是与图片转码相关
def heic_to_jpg(file_path, dst_path):
    """HEIC转JPG"""
    # 判断照片格式
    if common_utils.check_filetype(file_path, 'heic'):  # 校对图片格式
        # 读取图片
        image = Image.open(file_path)
        dst_tmp_dir = os.path.dirname(dst_path)
        if not os.path.exists(dst_tmp_dir):
            os.makedirs(dst_tmp_dir)
        # 写出新图片
        image.save(dst_path, format="JPEG")


def webp_to_jpg(file_path, dst_path):
    """WEBP转JPG"""
    # 判断照片格式
    if common_utils.check_filetype(file_path, 'webp'):  # 校对图片格式
        img = Image.open(file_path)
        img.load()
        dst_tmp_dir = os.path.dirname(dst_path)
        if not os.path.exists(dst_tmp_dir):
            os.makedirs(dst_tmp_dir)
        img = img.convert('RGB')  # cannot write mode RGBA as JPEG  JPEG无法保存alpha通道
        img.save(dst_path, 'JPEG')


def transcode(file_path, dst_path, format, quality=None, subsampling=None, is_save_exif=False, ico_size_str=None, original_mtime_flag=False):
    """格式转换"""
    if not common_utils.check_filetype(file_path, 'image'):  # 非图片文件
        return
    dst_tmp_dir = os.path.dirname(dst_path)
    if not os.path.exists(dst_tmp_dir):
        os.makedirs(dst_tmp_dir)
    format = format.upper()  # 取后缀名文件类型
    if format in ['ICO', 'ICON']:
        return convert_to_icon(file_path, dst_path, ico_size_str, original_mtime_flag)
    img = Image.open(file_path)
    img.load()
    if format in ['JPG', 'JPEG']:
        format = 'JPEG'
        # print('移除alpha通道！')
        img = img.convert('RGB')  # cannot write mode RGBA as JPEG  JPEG无法保存alpha通道
    if format in ['HEIC']:
        format = 'HEIF'
    # 保存新图片
    kwargs = {}
    if quality:
        kwargs['quality'] = quality
    if subsampling is not None:
        kwargs['subsampling'] = subsampling
    if is_save_exif:
        exif_data = get_jpeg_exif_by_pillow(file_path)
        if exif_data:
            kwargs['exif'] = exif_data
    
    img.save(dst_path, format, **kwargs)
    # 修改文件时间戳
    if original_mtime_flag:
        _mtime = os.path.getmtime(file_path)
        os.utime(dst_path, (_mtime, _mtime))


def convert_to_icon(file_path, dst_path, ico_size_str, original_mtime_flag):
    """转换成ico图标"""
    # img = Image.open(file_path)
    # img.save(dst_path, format='ICO', sizes=[(32,32)])
    if not common_utils.check_filetype(file_path, 'image'):  # 非图片文件
        return
    img = Image.open(file_path)
    img.load()
    SIZE_DICT = {'16': (16,16),'20': (20,20),'24': (24,24),'32': (32,32),'48': (48,48),
                 '64': (64,64),'128': (128,128),'256':(256,256)}
    flag = False
    if ico_size_str:
        size_strs = ico_size_str.replace('，', ',').split(',')
        size_list = [SIZE_DICT.get(size_str) for size_str in size_strs]
    else:
        size_list = [(16,16),(20,20),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    for size in size_list:
        if size is None:
            continue
        if size > img.size:
            continue
        flag = True
        save_path = os.path.splitext(dst_path)[0] + '_(%sx%s)' % size + '.ico'
        # 判断是否目标路径下是否有重名文件，若有则重新规划目标文件名
        save_path = common_utils.get_new_path(save_path)
        img.save(save_path, format='ICO', sizes=[size,])
        # 修改文件时间戳
        if original_mtime_flag:
            _mtime = os.path.getmtime(file_path)
            os.utime(save_path, (_mtime, _mtime))
    if flag is False:
        raise NameError('输入的ICO尺寸有误!')


def get_jpeg_exif_by_pillow(file_path):
    """获取jpeg图片exif 信息"""
    print(common_utils.check_filetype(file_path, 'jpg'))
    if common_utils.check_filetype(file_path, 'jpg'):
        with JpegImageFile(file_path) as img_file:
            return img_file.getexif()


