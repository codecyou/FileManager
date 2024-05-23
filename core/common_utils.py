"""通用工具模块"""
from conf import settings
from core.logger import logger
import os
import shutil
import time
import re
import hashlib
import difflib
import subprocess
import mimetypes
import exifread
import filetype
import chardet
from decimal import Decimal
from PIL import Image
from pymediainfo import MediaInfo


# 开启静默模式不弹cmd窗口
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE


def my_init():
    """检查工作环境，初始化工作环境"""
    if not os.path.exists(settings.RECORD_DIR):
        os.makedirs(settings.RECORD_DIR)
    if not os.path.exists(settings.DB_DIR):
        os.makedirs(settings.DB_DIR)
    if not os.path.exists(settings.LOG_DIR):
        os.makedirs(settings.LOG_DIR)


def get_local_time(timestamp=None, strf_str=r'%Y-%m-%d %H:%M:%S'):
    """
    根据给定的时间格式返回格式化后的当前时间
    :param strf_str: 时间格式
    :param timestamp: 时间戳
    :return:
    """
    if timestamp:
        return time.strftime(strf_str, time.localtime(timestamp))
    return time.strftime(strf_str, time.localtime())


def get_times_now():
    """
    获取当前时间和标准时间字符串信息 "%Y-%m-%d %H:%M:%S"
    :return: {"time_str": time_str, "timestamp":timestamp}
    """
    timestamp = time.time()
    time_str = time.strftime(r"%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    time_num_str = time.strftime(r"%Y%m%d%H%M%S", time.localtime(timestamp))
    result = {"time_str": time_str, "time_num_str": time_num_str, "timestamp": timestamp}
    return result


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


def get_float(key, default=None):
    """字符串转数字,转换失败则返回默认值"""
    if key:
        try:
            return float(key)
        except Exception:
            return default
    return default


def get_int(key, default=None):
    """字符串转数字,转换失败则返回默认值"""
    if key:
        try:
            return int(key)
        except Exception:
            return default
    return default


def changeStrToTime(time_str):
    """用于将字符串转为时间 三种时间格式20210201135059,2021.2.1.13.05.59,2021-2-1-13-6-59"""
    # logger.debug("time_str:", time_str)
    time_a = re.search(r"(\d{4})[-\.](\d{1,2})[-\.](\d{1,2})[-\.]? *(\d{1,2})[-\.:：](\d{1,2})[-\.:：](\d{1,2})", time_str.strip())
    if time_a:
        # 匹配时间格式2021.2.1,2021-2-1
        time_y = time_a.group(1)
        time_m = time_a.group(2)
        time_d = time_a.group(3)
        time_H = time_a.group(4)
        time_M = time_a.group(5)
        time_S = time_a.group(6)
    # 匹配时间格式20210201135059
    elif (time_str.isdigit()) and (len(time_str) == 14):
        time_y = time_str[0:4]
        time_m = time_str[4:6]
        time_d = time_str[6:8]
        time_H = time_str[8:10]
        time_M = time_str[10:12]
        time_S = time_str[12:]
    else:
        return
    # 筛选格式
    if (not len(time_y) == 4) or (not (int(time_m) in range(1, 13))) or (not (int(time_d) in range(1, 32))):
        return
    # 判断月份取值范围是否正常
    if (time_m in ['4', '6', '9', '11']) and (time_d == "31"):
        return
    if time_m == '2':
        if time_d in ['30', '31']:
            return
        if (time_d == '29') and ((int(time_y) % 4) != 0):
            return
    # 判断时间取值范围是否正常
    for item in [time_H, time_M, time_S]:
        if int(item) not in range(0, 60):
            return
    # 将"2021-2-1" 转为 "2021-02-01"
    # if len(time_m) < 2:
    #     time_m = '0' + time_m
    time_m = time_m.zfill(2)
    time_d = time_d.zfill(2)
    time_H = time_H.zfill(2)
    time_M = time_M.zfill(2)
    time_S = time_S.zfill(2)
    new_time_str = "%s-%s-%s %s:%s:%s" % (time_y, time_m, time_d, time_H, time_M, time_S)  # '%Y-%m-%d %H:%M:%S'
    return new_time_str


def get_safe_del_dir(dir_path):
    """
    用于获取safe_del目录路径，之前是在程序所在目录生成，现在换成在文件所在目录生成
    :param dir_path:
    :return:
    """
    if settings.SAFE_DEL_LOCAL:
        dir_path = os.path.abspath(dir_path)
        while True:
            if dir_path == os.path.dirname(dir_path):
                return os.path.join(dir_path, settings.SAFE_DEL_DIR)
            dir_path = os.path.dirname(dir_path)
    else:
        return os.path.join(settings.BASE_DIR, settings.SAFE_DEL_DIR)


def check_path(dir_path, create_flag=False):
    """用于检测输入路径是否正确,
        dir_path        目录路径
        create_flag     标记是否新建目录
                        True如果目录不存在则新建
                        False不新建
    """
    if dir_path:  # 有输入内容
        dir_path = dir_path.strip()  # 防止出现输入' '
        if os.path.exists(dir_path):  # 检查路径是否存在
            # 当输入'/home/'时获取文件名就是''，所以加处理
            dir_path = os.path.abspath(dir_path)
            return dir_path
        else:
            if create_flag:
                os.makedirs(dir_path)
                dir_path = os.path.abspath(dir_path)
                return dir_path
            else:
                return
    else:
        print("输入路径有误，请重新输入！")
        return


def filter_dict(old_dict):
    """用于过滤字典中value的值是单个的"""
    new_dict = {}
    count = 0
    for item in old_dict:
        if len(old_dict[item]) == 1:
            continue
        new_dict[item] = old_dict[item]
        count += len(old_dict[item])
    return new_dict, count


def get_md5(file_path, read_bytes=1024):
    """
    用于计算文件的md5值
    :param file_path: 文件地址
    :param read_bytes: 一次读取的字节数
    :return: 文件md5值
    """
    hashObj = hashlib.md5()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(read_bytes)
            if data:
                hashObj.update(data)
            else:
                break
    ret = hashObj.hexdigest()
    return ret


def calc_hash(file_path, alg, read_bytes=1024):
    """
    计算文件的hash值
    :param file_path:  文件路径
    :param alg:  算法
    :return:
    """
    FUNC_DICT = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha224': hashlib.sha224,
        'sha256': hashlib.sha256,
        'sha384': hashlib.sha384,
        'sha512':  hashlib.sha512,
        'sha3_224': hashlib.sha3_224,
        'sha3_256': hashlib.sha3_256,
        'sha3_384': hashlib.sha3_384,
        'sha3_512': hashlib.sha3_512,
        }
    func = FUNC_DICT.get(alg)
    if not func:
        return
    hashObj = func()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(read_bytes)
            if data:
                hashObj.update(data)
            else:
                break
    ret = hashObj.hexdigest()
    return ret


def copy_file(src_path, dst_path, del_flag=False):
    """
    用于拷贝文件
    :param src_path:  源路径
    :param dst_path:  目的路径
    :param del_flag:   标记是否要删除 True 删除源文件 False 不删除
    :return:
    """
    if os.path.isdir(src_path):  # 如果是文件夹
        try:
            shutil.copytree(src_path, dst_path)
        except Exception as e:
            # 如果目标目录不存在则会报此错误，比如shutil.copy2(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.copytree(src_path, dst_path)
            else:
                logger.error(e)
        if del_flag:  # 判断是否要删除
            shutil.rmtree(src_path)
    else:
        try:
            shutil.copy2(src_path, dst_path)
        except Exception as e:
            # 如果目标目录不存在则会报此错误，比如shutil.copy2(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.copy2(src_path, dst_path)
            else:
                logger.error(e)
        if del_flag:  # 判断是否要删除
            os.remove(src_path)


def copy_file_force(src_path, dst_path):
    """
    用于拷贝文件, 遇同名文件直接覆盖
    :param src_path:  源路径
    :param dst_path:  目的路径
    :param del_flag:   标记是否要删除 True 删除源文件 False 不删除
    :return: 0 失败 1 成功 2 跳过
    """
    flag = 0
    if os.path.isdir(src_path):  # 如果是文件夹
        try:
            shutil.copytree(src_path, dst_path)
            flag = 1
        except Exception as e:
            # 如果目标目录不存在则会报此错误，比如shutil.copy2(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.copytree(src_path, dst_path)
                flag = 1
            else:
                logger.error(e)
    else:
        try:
            shutil.copy2(src_path, dst_path)
            flag = 1
        except Exception as e:
            # 如果目标目录不存在则会报此错误，比如shutil.copy2(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.copy2(src_path, dst_path)
                flag = 1
            else:
                logger.error(e)

    return flag


def copy_file_skip(src_path, dst_path):
    """
    用于拷贝文件, 遇同名文件直接跳过
    :param src_path:  源路径
    :param dst_path:  目的路径
    :return:0 失败 1 成功 2 跳过
    """
    flag = 0
    if os.path.exists(dst_path):
        logger.debug("dst_path: %s 已存在，已跳过该项目！" % dst_path)
        return 2
    if os.path.isdir(src_path):  # 如果是文件夹
        try:
            shutil.copytree(src_path, dst_path)
            flag = 1
        except Exception as e:
            # 如果目标目录不存在则会报此错误，比如shutil.copy2(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.copytree(src_path, dst_path)
                flag = 1
            else:
                logger.error(e)
    else:
        try:
            shutil.copy2(src_path, dst_path)
            flag = 1
        except Exception as e:
            # 如果目标目录不存在则会报此错误，比如shutil.copy2(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.copy2(src_path, dst_path)
                flag = 1
            else:
                logger.error(e)

    return flag


def get_pathlist(dir_path):
    """
    遍历目录路径获取所有文件的路径列表
    :param dir_path: 要遍历的路径
    :return: path_list
    """
    path_list = []
    if os.path.isfile(dir_path):
        return [dir_path, ]
    elif os.path.isdir(dir_path):
        for root, dirs, files in os.walk(dir_path):
            for filename in files:
                img_path = os.path.join(root, filename)
                path_list.append(img_path)
    return path_list


def move_file(src_path, dst_path):
    """
    用于剪切文件
    :param src_path:  源路径
    :param dst_path:  目的路径
    :return:
    """
    try:
        shutil.move(src_path, dst_path)
    except Exception as e:
        # 如果目标目录不存在则会报错，比如shutil.move(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
        dst_dir = os.path.dirname(dst_path)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
            shutil.move(src_path, dst_path)
        else:
            logger.error(e)


def move_file_force(src_path, dst_path):
    """
    用于剪切文件, 遇到同名文件则会覆盖
    :param src_path:  源路径
    :param dst_path:  目的路径
    :return:0 失败 1 成功 2 跳过
    """
    flag = 0
    try:
        shutil.move(src_path, dst_path)
        flag = 1
    except Exception as e:
        # 如果目标目录不存在则会报错，比如shutil.move(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
        dst_dir = os.path.dirname(dst_path)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
            shutil.move(src_path, dst_path)
            flag = 1
        else:
            logger.error(e)
    return flag


def move_file_skip(src_path, dst_path):
    """
    用于剪切文件, 遇到同名文件则会跳过
    :param src_path:  源路径
    :param dst_path:  目的路径
    :return:0 失败 1 成功 2 跳过
    """
    flag = 0
    if os.path.exists(dst_path):
        logger.debug("dst_path: %s 已存在，已跳过该文件！" % dst_path)
        return 2
    try:
        shutil.move(src_path, dst_path)
        flag = 1
    except Exception as e:
        # 如果目标目录不存在则会报错，比如shutil.move(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
        dst_dir = os.path.dirname(dst_path)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
            shutil.move(src_path, dst_path)
            flag = 1
        else:
            logger.error(e)
    return flag


def update_file(src_path, dst_path, safe_del_path):
    """
    用于更新文件
    :param src_path:  源路径
    :param dst_path:  目的路径
    :param safe_del_path:  safe_del文件路径
    :return:
    """
    # copy_file(dst_path, safe_del_path, del_flag=True)
    move_file(dst_path, safe_del_path)
    copy_file(src_path, dst_path)


def makedir4safe_del(dir_path):
    """用于创建safe_del文件夹，将同步或恢复操作中删除的文件保存到该文件夹，以防误操作导致文件数据损失"""
    safe_del_dir = os.path.abspath("%s/del_from_%s_%s" % (get_safe_del_dir(dir_path), os.path.basename(dir_path), time.strftime(r"%Y%m%d%H%M%S", time.localtime())))
    if not os.path.exists(safe_del_dir):
        os.makedirs(safe_del_dir)
    return safe_del_dir


def get_dir_str(dir_path):
    """用于获取一个路径的字符串描述"""
    # 例如：C:\Users\b\c 变为C_Users_b_c
    dir_str = os.path.abspath(dir_path)
    dir_str = dir_str.replace(':', '').replace("\\", '_').replace("/", "_")  # replace(":", "")去除盘符后面的 "："
    return dir_str


def make_new_path(file_path, old_dir_path, new_dir_path, name_simple=True):
    """用于将原来的file_path进行处理并拼接为new_dir_path下绝对路径
        文件名处理为原文件名（含后缀）_[原目录层次结构].文件后缀名
    :param file_path: 原路径
    :param old_dir_path: 原目录路径
    :param new_dir_path: 新目录路径
    :param name_simple: 文件重命名模式  True 简单目录结构  False 绝对目录结构
    :return: new_path
    """
    # 例如 :原文件为C:\Users\b\c\a.jpg ，old_dir_path 为 C:\Users， new_dir_path为D:\backup时
    #     dir_str 为''  新文件名为a.jpg_[b_c].jpg  新路径为D:\backup\a.jpg_[b_c].jpg
    # 先获取原路径在源目录下的目录层次结构
    file_path = os.path.abspath(file_path)
    file_name = os.path.basename(file_path)
    # 获取目录结构
    if name_simple:  # 简单目录结构
        old_dir_path = os.path.abspath(old_dir_path)
        # 判断是否同级目录,第一级目录结构值为''，第二级为/xx/xxx
        dir_str = os.path.dirname(file_path).replace(old_dir_path, '')
        # 比如 old_dir_path 为 C:\Users时
        # C:\Users\a.jpg    dir_str 为''  而C:\Users\b\a.jpg    dir_str 为'\b'
        if dir_str:  # 判断是否是多级目录 ，如果是需要修改文件名
            dir_str = dir_str[1:]  # 去除dir_str 为'\b' 前面的'\'
        else:  # 单级目录直接拼接文件名返回
            return os.path.join(new_dir_path, file_name)
    else:  # 绝对目录结构 C:\Users\pro\PycharmProjects 改为 C_Users_pro_PycharmProjects 然后拼接新目录路径
        dir_str = os.path.dirname(file_path)
    dir_str = dir_str.replace(':', '').replace("/", "_").replace("\\", '_')  # 用来记录原文件的目录结构 格式"C_Users_pro_PycharmProjects"
    if file_name.count('.'):
        # 防止出现'_[].mp4'的情况，当目录层次一样时文件名不变
        new_file_name = "%s_[%s].%s" % (file_name, dir_str, file_name.split('.')[-1]) if len(dir_str) else file_name
    else:
        new_file_name = "%s_[%s]" % (file_name, dir_str) if len(dir_str) else file_name
    new_path = os.path.join(new_dir_path, new_file_name)
    return new_path


def deal_files(files, old_dir_path, new_dir_path, deal_mode="move", same_file_option='skip', export_mode=1):
    """
    用于移动或者复制文件，并将新旧文件名记录到new_old_record,并导出文件   
    :param files: 保存文件信息的集合，可以是dict {name|size|name_size : [path1,path2]} 可以是list [path1,path2]
    :param old_dir_path: 原目录路径
    :param new_dir_path: 新目录路径
    :param deal_mode: 文件处理模式  "move" 剪切  "copy" 复制
    :param same_file_option: 同名文件处理模式  "overwrite" 覆盖  "skip" 跳过
    :param export_mode: 导出模式 1.导出到单级目录并附带目录结构描述 2.导出到单级目录 3.保持源目录结构
    :return:  result = {}  # 返回的结果 数据格式 {"record_path": record_path, 'new_old_record'：new_old_record,'skip_list':skip_list, 'failed_list':failed_list}
    """""
    new_old_record = {}  # 用于保存新旧文件名信息，格式为"{new_file: old_file, }"
    record_path = None  # 用来记录导出的新旧文件名记录路径 用于返回
    failed_path = None  # 用来记录导出失败的文件名记录路径
    failed_list = []  # 用于记录拷贝或剪切失败的文件信息
    skip_list = []  # 用来记录跳过的文件信息
    total_count = 0  # 项目总数，目录数+文件数
    if deal_mode == "copy":
        deal_func = copy_file_force if same_file_option == 'overwrite' else copy_file_skip  # 根据模式将函数名赋值给deal_func变量
    else:
        deal_func = move_file_force if same_file_option == 'overwrite' else move_file_skip
    if export_mode == 1:  # 看是否需要对文件进行重命名，即是否需要加上目录描述
        # 从多级目录往单级目录里面拷贝或者移动文件时可能会出现同名文件，所有加上对应目录层级描述
        # 格式：当name_simple为True 为相对目标目录的目录层级  为False 为原文件的绝对目录层级
        get_new_path_func = make_new_path
    elif export_mode == 2:
        # 将一个目录的文件剪切或拷贝到另一目录，将源目录下子文件全部导出到目标目录单级目录下（此操作有重名文件覆盖风险）
        # 其中none_para 是无用参数 只为参数占位 方便后面统一传参使用
        get_new_path_func = lambda file_path, old_dir, new_dir, none_para: os.path.join(new_dir, os.path.basename(file_path))
    else:
        # 简单的将一个目录的文件剪切或拷贝到另一目录,保持原目录结构层次
        # 匿名函数实现文件目录替换  其中none_para 是无用参数 只为参数占位 方便后面统一传参使用
        get_new_path_func = lambda file_path, old_dir, new_dir, none_para: file_path.replace(old_dir, new_dir)
    if isinstance(files, dict):
        for item in files:
            total_count += len(files[item])
            for old_path in files[item]:
                new_path = get_new_path_func(old_path, old_dir_path, new_dir_path, True)  # 调用make_new_path方法 获得新路径
                try:
                    res_flag = deal_func(old_path, new_path)  # 由上面赋值的函数名变量调用函数代码
                except Exception as e:
                    failed_list.append(old_path)
                    logger.debug("操作%s文件失败，详情请查看错误日志！" % old_path)
                    logger.error(e)
                else:
                    if res_flag == 0:
                        failed_list.append(old_path)
                    elif res_flag == 2:
                        skip_list.append(old_path)
                    else:
                        new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
    elif isinstance(files, list):
        total_count += len(files)
        for old_path in files:
            new_path = get_new_path_func(old_path, old_dir_path, new_dir_path, True)  # 调用make_new_path方法 获得新路径
            try:
                res_flag = deal_func(old_path, new_path)
            except Exception as e:
                failed_list.append(old_path)
                logger.debug("操作%s文件失败，详情请查看错误日志！" % old_path)
                logger.error(e)
            else:
                if res_flag == 0:
                    failed_list.append(old_path)
                elif res_flag == 2:
                    skip_list.append(old_path)
                else:
                    new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
    # 写出到记录文件和日志
    if len(new_old_record):
        time_res = get_times_now()  # 获取当前时间的两种格式
        write_time = time_res.get('time_num_str')
        log_time = time_res.get('time_str')
        record_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("new_old_record", write_time))
        export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        if deal_mode == 'copy':
            msg = "【操作文件】  从 %s 拷贝 %s 个项目到 %s,新旧文件名导出到 %s" % (old_dir_path, len(new_old_record), new_dir_path, record_path)
        else:
            msg = "【操作文件】  从 %s 剪切 %s 个项目到 %s,新旧文件名导出到 %s" % (old_dir_path, len(new_old_record), new_dir_path, record_path)
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("failed", write_time))
            msg += "\n\t\t%s个文件操作失败，文件信息导出到%s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for item in failed_list:
                    f.write('%s\n' % item)
        logger.info(msg)
    result = {"record_path": record_path, 'failed_path': failed_path, 'total_count': total_count, 'new_old_record': new_old_record,'skip_list': skip_list, 'failed_list': failed_list}
    return result


def check_files_overwrite_danger(files, old_dir_path, new_dir_path, export_mode=1):
    """用来检测目标目录路径是否存在同名文件，防止数据覆盖损失
    :param files: 保存文件信息的集合,可以是dict {name|size|name_size : [path1,path2]} 可以是list [path1,path2]
    :param old_dir_path: 原目录路径
    :param new_dir_path: 新目录路径
    :param export_mode: 导出模式 1.导出到单级目录并附带目录结构描述 2.导出到单级目录 3.保持源目录结构
    :return: danger_dict # 有数据覆盖风险的文件  数据格式{"src_path" : "dst_path"}
    """
    danger_dict = {}  # 有数据覆盖风险的文件  数据格式{"src_path" : "dst_path"}
    name_simple = True
    if export_mode == 1:  # 看是否需要对文件进行重命名，即是否需要加上目录描述
        # 从多级目录往单级目录里面拷贝或者移动文件时可能会出现同名文件，所有加上对应目录层级描述
        # 格式：当name_simple为True 为相对目标目录的目录层级  为False 为原文件的绝对目录层级
        get_new_path_func = make_new_path
    elif export_mode == 2:
        # 将一个目录的文件剪切或拷贝到另一目录，将源目录下子文件全部导出到目标目录单级目录下（此操作有重名文件覆盖风险）
        # 其中none_para 是无用参数 只为参数占位 方便后面统一传参使用
        get_new_path_func = lambda file_path, old_dir, new_dir, none_para: os.path.join(new_dir, os.path.basename(file_path))
    else:
        # 简单的将一个目录的文件剪切或拷贝到另一目录,保持原目录结构层次
        # 匿名函数实现文件目录替换  其中none_para 是无用参数 只为参数占位 方便后面统一传参使用
        get_new_path_func = lambda file_path, old_dir, new_dir, none_para: file_path.replace(old_dir, new_dir)
    if isinstance(files, dict):
        new_path_list = []  # 记录拼接的新文件路径，用于避免目标目录当前未存在但是开始执行文件移动之后出现同名文件的bug
        for item in files:
            for old_path in files[item]:
                new_path = get_new_path_func(old_path, old_dir_path, new_dir_path, name_simple)  # 调用make_new_path方法 获得新路径
                if os.path.exists(new_path):
                    logger.debug("src_path: %s 在目标路径已存在同名项目 %s 有数据覆盖风险！" % (old_path, new_path))
                    danger_dict[old_path] = new_path
                if new_path in new_path_list:
                    logger.debug("src_path: %s 在移动过程中目标路径将会出现同名项目 %s 有数据覆盖风险！" % (old_path, new_path))
                    danger_dict[old_path] = new_path
                new_path_list.append(new_path)

    elif isinstance(files, list):
        new_path_list = []  # 记录拼接的新文件路径，用于避免目标目录当前未存在但是开始执行文件移动之后出现同名文件的bug
        for old_path in files:
            new_path = get_new_path_func(old_path, old_dir_path, new_dir_path, name_simple)  # 调用make_new_path方法 获得新路径
            if os.path.exists(new_path):  # 判断目标目录是否已存在同名文件
                logger.debug("src_path: %s 在目标路径已存在同名项目 %s 有数据覆盖风险！" % (old_path, new_path))
                danger_dict[old_path] = new_path
            if new_path in new_path_list:
                logger.debug("src_path: %s 在移动过程中目标路径将会出现同名项目 %s 有数据覆盖风险！" % (old_path, new_path))
                danger_dict[old_path] = new_path
            new_path_list.append(new_path)

    return danger_dict


def restore_file_by_record(record_path, same_file_option='overwrite', log_flag=True):
    """  带重名跳过
    用于从record_path读取new_old_record记录来还原文件
    :param record_path: new_old_record记录文件路径
    :param log_flag: 标记是否记录日志  True 记录  False 不记录
    :param same_file_option: 同名文件处理模式  "overwrite" 覆盖  "skip" 跳过
    :return: {'record_path': restore_record_path,
           'sucess_list': restore_list,
           'failed_list': failed_list,
           'skip_list': skip_list}
    """
    restore_list = []  # 用于记录还原文件信息 格式["now_file -> restore_file",]
    failed_list = []  # 操作失败的文件
    skip_list = []  # 重名跳过的文件
    restore_record_path = os.path.join(settings.RECORD_DIR, '还原记录_%s.txt' % get_times_now().get('time_num_str')) # 用于导出还原记录
    new_old_record = import_new_old_record(record_path)  # 导入new_old_record记录
    deal_func = move_file_force if same_file_option == 'overwrite' else move_file_skip
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        if os.path.exists(new_file):
            flag = deal_func(new_file, old_file)
            if flag == 0:
                failed_list.append(new_file)
            if flag == 2:
                skip_list.append(new_file)
            if flag == 1:
                restore_list.append("%s  ->  %s" % (new_file, old_file))
    if len(restore_list):
        # print_str = "【文件还原】  根据记录 %s 还原了 %s 个文件，还原文件信息记录到%s" % (record_path, len(restore_list), restore_record_path)
        if log_flag:
            with open(restore_record_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(restore_list))
            # logger.info(print_str)
    else:
        logger.debug("未找到可以还原的文件！")
    res = {'record_path': restore_record_path,
           'sucess_list': restore_list,
           'failed_list': failed_list,
           'skip_list': skip_list}
    return res


def undo_restore_file_by_record(record_path, move_flag=True):
    """
    用于从record_path读取new_old_record记录来撤销还原文件，即根据new_old_record 重做一次文件移动操作
    :param record_path: new_old_record记录文件路径
    :param move_flag: 是否剪切文件  True 剪切 False 复制
    """
    count = 0  # 用来统计操作了多少个文件
    new_old_record = import_new_old_record(record_path)  # 导入new_old_record记录
    skip_flag = settings.SKIP_FLAG
    if move_flag:
        func = move_file_skip if skip_flag else move_file_force
    else:
        func = copy_file_skip if skip_flag else copy_file_force
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        if os.path.exists(old_file):
            func(old_file, new_file)
            count += 1
    else:
        logger.debug("未找到可以还原的文件！")

    return count


def undo_restore_file_by_record2(record_path, same_file_option):
    """  带重名跳过
    用于从record_path读取new_old_record记录来还原文件
    :param record_path: new_old_record记录文件路径
    :param log_flag: 标记是否记录日志  True 记录  False 不记录
    :param same_file_option: 同名文件处理模式  "overwrite" 覆盖  "skip" 跳过
    :return: {
           'sucess_list': restore_list,
           'failed_list': failed_list,
           'skip_list': skip_list}
    """
    restore_list = []  # 用于记录还原文件信息 格式["now_file -> restore_file",]
    failed_list = []  # 操作失败的文件
    skip_list = []  # 重名跳过的文件
    new_old_record = import_new_old_record(record_path)  # 导入new_old_record记录
    deal_func = move_file_force if same_file_option == 'overwrite' else move_file_skip
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        if os.path.exists(old_file):
            flag = deal_func(old_file, new_file)
            if flag == 0:
                failed_list.append(old_file)
            if flag == 2:
                skip_list.append(old_file)
            if flag == 1:
                restore_list.append("%s  ->  %s" % (old_file, new_file))
    res = {
           'sucess_list': restore_list,
           'failed_list': failed_list,
           'skip_list': skip_list}
    return res


def remove_empty_dir(dir_path):
    """
    用于一次性删除路径下所有空文件夹
    :param dir_path: 要清空空文件夹的目录路径
    :return:
    """
    dir_list = []  # 用于记录被清空的空文件夹信息
    for root, dirs, files in os.walk(dir_path):  # 遍历所有文件夹
        for temp_dir in dirs:
            dir_list.append(os.path.join(root, temp_dir))
    dir_list = dir_list[::-1]  # 取倒序
    del_list = []
    for item in dir_list:
        if not os.listdir(item):  # 判断是否空文件夹
            os.rmdir(item)
            del_list.append(item)
    return del_list


def export_path_record(path_list, record_path):
    """
     用于将路径记录导出到文件
    :param path_list: 新旧文件名信息字典 [path1,....]
    :param record_path  记录文件的路径
    :return:
    """
    with open(record_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(path_list))


def export_new_old_record(new_old_record, record_path):
    """
     用于将新旧文件名导出到文件
    :param new_old_record: 新旧文件名信息字典 {newname: oldname,}
    :param record_path  记录新旧文件名记录文件的路径
    :return:
    """
    with open(record_path, 'a', encoding='utf-8') as f:
        for new_file in new_old_record:
            f.write("%s\t%s\n" % (new_file, new_old_record[new_file]))


def import_new_old_record(record_path):
    """用于从文件获取之前导出的新旧文件记录"""
    new_old_record = {}  # 用于记录还原文件的信息 格式{new_file: old_file,}
    if os.path.isfile(record_path):
        with open(record_path, 'r', encoding="utf-8") as f:
            read_list = f.readlines()
            for item in read_list:
                if item.strip():
                    new_file = item.strip().split("\t")[0]
                    old_file = item.strip().split("\t")[1]
                    new_old_record[new_file] = old_file
    return new_old_record


def get_files_info_by_path(dir_path):
    """用于获取目录下所有文件的信息
    格式：{file_path: {"name": file_name, "size": file_size, "mtime": file_mtime}, }
    """
    file_dict = {}
    # 用于储存文件信息，记录数据格式为{file_path: {"name": file_name, "size": file_size, "mtime": file_mtime}, }
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            # 获取文件信息
            file_path = os.path.join(root, file_name)
            file_size = os.path.getsize(file_path)  # 得到的是int数据
            file_mtimestamp = os.path.getmtime(file_path)
            file_mtime = time.strftime(r"%Y-%m-%d %H:%M:%S", time.localtime(file_mtimestamp))
            file = {"name": file_name, "size": file_size, "mtime": file_mtime, "mtimestamp": file_mtimestamp}
            file_dict[file_path] = file
    return file_dict  # 返回遍历完成的文件信息


def get_files_info_by_list(path_list):
    """用于获取路径list所有文件的信息
    格式：{file_path: {"name": file_name, "size": file_size, "mtime": file_mtime}, }
    """
    file_dict = {}
    # 用于储存文件信息，记录数据格式为{file_path: {"name": file_name, "size": file_size, "mtime": file_mtime}, }
    for file_path in path_list:
        # 获取文件信息
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)  # 得到的是int数据
        file_mtimestamp = os.path.getmtime(file_path)
        file_mtime = time.strftime(r"%Y-%m-%d %H:%M:%S", time.localtime(file_mtimestamp))
        file = {"name": file_name, "size": file_size, "mtime": file_mtime, "mtimestamp": file_mtimestamp}
        file_dict[file_path] = file
    return file_dict  # 返回遍历完成的文件信息


def get_txt_encode(file_path):
    """获取文本文件编码"""
    with open(file_path, 'rb') as f:
        content = f.read()
    # 用于常用的编码格式为GBK UTF8，默认先匹配utf-8和gbk，若匹配失败才调用chardet，节约匹配时间
    for encode in ['utf-8', 'gbk', 'GB18030']:
        try:
            content.decode(encode)
            return encode
        except Exception as e:  # 解码失败
            logger.warning('获取文件编码失败! path: %s , error: %s' % (file_path, e))
            continue

    # 调用chardet匹配
    encode = chardet.detect(content)['encoding']
    if encode.upper() in ['GBK', 'GB2312', 'GB18030']:
        logger.debug('文件：{} ，原编码为：{}, 取GB18030编码'.format(file_path, encode))
        encode = 'GB18030'
    logger.debug('文件：{} ，编码为：{}'.format(file_path, encode))
    return encode


def get_txt_encode_fast(file_path):
    """快速获取文本编码"""
    try:
        with open(file_path, 'rb') as f:
            data = f.read(1024)  # 读取文件的前1024字节
            result = chardet.detect(data)  # 使用chardet库检测编码
            encoding = result['encoding'] if 'encoding' in result else None
            return encoding
    except:
        return None


def is_text_file(file_path):
    """判断一个文件是否为文本"""
    try:
        with open(file_path, 'rb') as f:
            data = f.read(1024)  # 读取文件的前1024字节
            result = chardet.detect(data)  # 使用chardet库检测编码
            encoding = result['encoding'] if 'encoding' in result else None
            return encoding in ['utf-8', 'utf-16', 'ascii', 'gbk', 'GB2312', 'GB18030']  # 假定这几种编码都是文本文件
    except:
        return False  # 如果文件无法打开或读取，则认为不是文本文件


def get_txt_files(dir_path):
    """获取目录下所有文本类型文件路径"""
    file_list = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            if is_text_file(file_path):
                file_list.append(file_path)
    return file_list


def get_txt_content(file_path):
    """读取文本内容"""
    with open(file_path, 'rb') as f:
        data = f.read()
    # for txt_encode in ['utf-8', 'gbk', 'GB2312', 'ascii', 'utf-16']:
    #     try:
    #         return data.decode(txt_encode)
    #     except:
    #         logger.debug('%s 不是 %s 编码！' % (file_path, txt_encode))
    txt_encode = get_txt_encode(file_path)
    try:
        return data.decode(txt_encode)
    except:
        logger.debug('%s 不是 %s 编码！' % (file_path, txt_encode))
    

def get_files_by_encode(src_dir, encode):
    """获取文本文件编码, 使用chardet"""
    path_list = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                file_encode = chardet.detect(f.read())
            file_encode = file_encode['encoding'] if 'encoding' in file_encode else None
            if not file_encode:
                continue
            file_encode = file_encode.upper()
            logger.debug('文件：{} ,编码为：{}'.format(file_path, file_encode))
            if file_encode in ['GBK', 'GB2312', 'GB18030']:
                logger.debug('文件：{} ,原编码为：{}, 取GBK编码'.format(file_path, file_encode))
                file_encode = 'GBK'
            if encode == 'UTF8':
                encode = 'UTF-8'
            if encode == 'UTF-8':
                if file_encode == 'ASCII':  # UTF-8包含ASCII， 如果一个文本为纯英文的ASCII 那就是UTF-8
                    file_encode = 'UTF-8'
            if file_encode == encode:
                path_list.append(file_path)
    return path_list


def get_files_by_encode2(src_dir, encode):
    """获取文本文件编码，尝试使用指定编码解码"""
    path_list = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                content = f.read()
            try:
                content.decode(encode)
                path_list.append(file_path)
            except Exception as e:  # 解码失败
                continue
    return path_list


def read_file(file_path, encode='adapter'):
    """
    读取读取文本文件内容
    :param file_path: 文件路径
    :param encode: 文件编码格式
    :return:
    """
    if encode == 'adapter':  # 自动适配文本编码
        encode = get_txt_encode(file_path)
    try:
        with open(file_path, 'r', encoding=encode) as f:
            text = f.read().splitlines()
        return text
    except IOError as error:
        logger.debug('Read input file Error: {0}'.format(error))
        return


def compare_txt(file1, file2, record_path='', encode='adapter', is_context=True, wrapcolumn=100):
    """
    利用difflib比对两个文本内容
    比较两个文件并把结果生成一份html文本,并返回html文件路径
    :param file1: 文件路径1
    :param file2: 文件路径2
    :param wrapcolumn:  中文栏最大宽度
    :param is_context: True 仅显示差异处上下文 False 全文显示
    :param encode: 文件编码格式
    :return:
    """
    if file1 == "" or file2 == "":
        print('文件路径不能为空：第一个文件的路径：{0}, 第二个文件的路径：{1} .'.format(file1, file2))
    else:
        print("正在比较文件{0} 和 {1}".format(file1, file2))
    text1_lines = read_file(file1, encode)
    text2_lines = read_file(file2, encode)
    if text1_lines == text2_lines:  # 文本内容一致
        return
    diff = difflib.HtmlDiff(tabsize=4, wrapcolumn=wrapcolumn)    # 创建HtmlDiff 对象
    # 通过make_file 方法输出 html 格式的对比结果, context参数可以设置只显示差异行上线多少内容 不会显示大部分相同内容
    # context 为True时，只显示差异的上下文，为false，显示全文，numlines默认为5
    result = diff.make_file(text1_lines, text2_lines, fromdesc=file1, todesc=file2, context=is_context)
    if not record_path:
        record_path = os.path.join(settings.RECORD_DIR, '文本内容差异', get_times_now().get("time_num_str"))  # 建立用于存储本次差异文件的目录
    if not os.path.exists(record_path):  # 输出目录不存在则创建
        os.makedirs(record_path)
    # 将结果写入到diff_xxx.html文件中
    html_path = os.path.join(record_path, "diff_%s.html" % os.path.basename(file1))
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(result)
            logger.debug("0==}==========> Successfully Finished\n")
    except IOError as error:
        logger.debug('写入html文件错误: {0}'.format(error))
    return html_path


def get_new_path(file_path):
    """判断是否目标路径下是否有重名文件，若有则重新规划目标文件名"""
    # 判断是否目标路径下是否有重名文件，若有则重新规划目标文件名
    if os.path.exists(file_path):
        num = 0
        tmp_dst_name, dst_ext = os.path.splitext(file_path)
        while True:
            num += 1
            tmp_dst_path = '{}_{}{}'.format(tmp_dst_name, num, dst_ext)
            if not os.path.exists(tmp_dst_path):
                file_path = tmp_dst_path
                break
    return file_path


def get_image_resolution(file_path):
    """获取图片分辨率"""
    # 打开图片文件
    with Image.open(file_path) as img:
        # 获取图片分辨率
        width, height = img.size
    return {'width': int(width), 'height': int(height)}


def get_video_resolution(file_path):
    """获取视频分辨率"""
    media_data = get_media_meta(file_path)  # 获取媒体文件元数据
    width = media_data['video_data'].get('width')  # 帧宽度
    height = media_data['video_data'].get('height')  # 帧高度
    return {'width': int(width), 'height': int(height)}


def latitude_and_longitude_convert_to_decimal_system(*arg):
    """
    经纬度转为小数, param arg:
    :return: 十进制小数
    """
    return float(arg[0]) + ((float(arg[1]) + (float(arg[2].split('/')[0]) / float(arg[2].split('/')[-1]) / 60)) / 60)


def get_video_encoded_date(file_path):
    """获取视频拍摄时间"""
    media_data = get_media_meta(file_path)  # 获取媒体文件元数据
    encoded_date_utc = media_data['general_data'].get('encoded_date')  # 获取视频拍摄时间
    encoded_date = change_UTC_to_local(encoded_date_utc, r'%Y-%m-%d %H:%M:%S UTC') if encoded_date_utc else None
    return encoded_date


def get_photo_encoded_date(file_path):
    """获取照片拍摄时间"""
    exif_data = get_image_info(file_path)  # 获取照片EXIF数据
    encoded_date = exif_data.get('encoded_date')  # 获取照片拍摄时间
    return encoded_date


def get_media_encoded_date(file_path):
    """获取媒体文件拍摄时间"""
    if check_filetype_extended(file_path, 'video'):
        return get_video_encoded_date(file_path)
    if check_filetype_extended(file_path, 'image'):
        return get_photo_encoded_date(file_path)


def change_UTC_to_local(time_utc_str, time_format):
    """修改UTC时间到本地时间"""
    gm_offset =  get_gmtoff()  # 获取本地时间相对于UTC的偏移秒数
    seconds = time.mktime(time.strptime(time_utc_str, time_format)) + gm_offset  # 将UTC时间的自纪元开始秒数+相对本地时间的偏移量，得到本地时间秒数
    return time.strftime(r"%Y-%m-%d %H:%M:%S", time.localtime(seconds))


def get_gmtoff():
    """获取本地时间相对UTC时间的偏移量"""
    # 方法一：计算秒数
    # t = time.time()
    # gm_offset = time.mktime(time.localtime(t)) - time.mktime(time.gmtime(t))

    # 方法二：使用tm_gmtoff属性， 该属性在python3.3版本中加入，但是直到python 3.6 版本之后才可在所有平台上使用。
    gm_offset =  time.localtime().tm_gmtoff  # 获取本地时间相对于UTC的偏移秒数
    return gm_offset


def get_video_info(file_path):
    """获取视频信息，时长、分辨率、拍摄时间"""
    media_data = get_media_meta(file_path)  # 获取媒体文件元数据
    encoded_date_utc = media_data['general_data'].get('encoded_date')  # 获取视频拍摄时间
    encoded_date = change_UTC_to_local(encoded_date_utc, r'%Y-%m-%d %H:%M:%S UTC') if encoded_date_utc else None
    # 时长--毫秒转换
    duration = media_data['general_data'].get('duration')  # 原始时长为毫秒
    if not duration:  # mediainfo不能读取某些小米手机录音的音频文件
        total = get_media_meta_by_ffmpeg(file_path).get('total')
        duration = total*1000 if total else 0
    # 秒数计算
    duration_sec = duration / 1000
    duration_str = '%.2d:%.2d:%.2f'%(duration_sec // 3600, duration_sec % 3600 // 60, duration_sec % 3600 % 60)
    width = media_data['video_data'].get('width')  # 帧宽度
    height = media_data['video_data'].get('height')  # 帧高度
    format = media_data['general_data'].get('format') # 格式
    file_creation_date = media_data['general_data'].get('file_creation_date')  # 创建日期
    file_last_modification_date =  media_data['general_data'].get('file_last_modification_date')  # 最近修改日期
    # 帧速率
    frame_rate = media_data['general_data'].get('frame_rate')
    frame_rate = '%.2f 帧/秒'%(float(frame_rate)) if frame_rate else None
    # 总比特率
    overall_bit_rate = media_data['general_data'].get('overall_bit_rate')
    overall_bit_rate = '%d kbps'%(overall_bit_rate // 1000) if overall_bit_rate else None
    # 获取厂商信息、位置信息
    location_keys = ["comapplequicktimelocationiso6709", "xyz"]
    hardware_make_keys = ["comapplequicktimemake", "comandroidmanufacturer"]
    hardware_model_keys = ["comapplequicktimemodel", "comandroidmodel"]
    hardware_software_keys = ["comapplequicktimesoftware", "comandroidversion"]
    for item in location_keys:  # 获取视频拍摄经纬度和高度 'comapplequicktimelocationiso6709': '+34.2517+108.9331+411.434/'
        location = media_data['general_data'].get(item)
        if location:
            break
    for item in hardware_make_keys:  # 设备厂商  'comapplequicktimemake': 'Apple'
        hardware_make = media_data['general_data'].get(item)
        if hardware_make:
            break
    for item in hardware_model_keys:  # 设备型号  'comapplequicktimemodel': 'iPhone 12'
        hardware_model = media_data['general_data'].get(item)
        if hardware_model:
            break
    for item in hardware_software_keys:  # 设备固件  'comapplequicktimesoftware': '16.6.1'
        hardware_software = media_data['general_data'].get(item)
        if hardware_software:
            break
    result = {"encoded_date": encoded_date, "duration": duration, "duration_sec": duration_sec, "duration_str": duration_str, 
              "location": location, "hardware_make": hardware_make, "hardware_model": hardware_model, 
              "hardware_software": hardware_software, "width": width, "height": height, 
              "format": format, "frame_rate": frame_rate, "overall_bit_rate": overall_bit_rate,
              "file_creation_date": file_creation_date, "file_last_modification_date": file_last_modification_date,
              }
    logger.debug(result)
    return result


def get_image_info(file_path):
    """获取图片信息 厂商、设备、GPS等信息"""
    GPS = {}
    date = ''
    hardware_make = ''
    hardware_model = ''
    hardware_software = ''
    ExifImageWidth = ''
    ExifImageLength = ''
    location = ''
    # 获取图片分辨率
    res = get_image_resolution(file_path)
    width = res['width']
    height = res['height']
    # 获取图片exif信息
    tags = get_image_meta(file_path)
    if not tags:
        result = {'GPS_information': GPS, 'date_information': date, "hardware_make": hardware_make, "location": location,
              "hardware_model": hardware_model, "hardware_software": hardware_software, "width": width, "height": height,
              "ExifImageWidth": ExifImageWidth, "ExifImageLength": ExifImageLength, "encoded_date": date}
        return result
    # 获取GPS、拍摄日期、设备信息
    for tag, value in tags.items():
        if re.match('GPS GPSLatitudeRef', tag):
            GPS['GPSLatitudeRef'] = str(value)
        elif re.match('GPS GPSLongitudeRef', tag):
            GPS['GPSLongitudeRef'] = str(value)
        elif re.match('GPS GPSAltitudeRef', tag):
            GPS['GPSAltitudeRef'] = str(value)
        elif re.match('GPS GPSLatitude', tag):
            try:
                match_result = re.match(r'\[(\w*),(\w*),(\w.*)/(\w.*)\]', str(value)).groups()
                GPS['GPSLatitude'] = int(match_result[0]), int(match_result[1]), int(match_result[2])
            except:
                deg, min, sec = [x.replace(' ', '') for x in str(value)[1:-1].split(',')]
                GPS['GPSLatitude'] = latitude_and_longitude_convert_to_decimal_system(deg, min, sec)
        elif re.match('GPS GPSLongitude', tag):
            try:
                match_result = re.match(r'\[(\w*),(\w*),(\w.*)/(\w.*)\]', str(value)).groups()
                GPS['GPSLongitude'] = int(match_result[0]), int(match_result[1]), int(match_result[2])
            except:
                deg, min, sec = [x.replace(' ', '') for x in str(value)[1:-1].split(',')]
                GPS['GPSLongitude'] = latitude_and_longitude_convert_to_decimal_system(deg, min, sec)
        elif re.match('GPS GPSAltitude', tag):
            GPS['GPSAltitude'] = str(value)
            try:
                gps_alt = str(value)
                gps_alt = float(gps_alt.split('/')[0]) / float(gps_alt.split('/')[1])
                GPS['GPSAltitude'] = gps_alt
            except:
                GPS['GPSAltitude'] = str(value)
        elif re.match('EXIF DateTimeOriginal', tag):
            date = str(value)
            # 佳能G15相机固件写入照片EXIF信息为：'EXIF DateTimeOriginal': (0x9003) ASCII=2014:10:02 15:37:27 @ 702, 
            matchObj = re.search(r"\d{4}\:\d{2}\:\d{2} \d{2}\:\d{2}\:\d{2}", date)
            if matchObj:
                date = matchObj.group()  # 匹配到的 2014:10:02 15:37:27
            date = "%s-%s-%s %s:%s:%s" % (date[0:4], date[5:7], date[8:10], date[11:13], date[14:16], date[17:])
        elif re.match('Image Make', tag):
            hardware_make = str(value)
        elif re.match('Image Model', tag):
            hardware_model = str(value)
        elif re.match('Image Software', tag):
            hardware_software = str(value)
        elif re.match('EXIF ExifImageWidth', tag):
            ExifImageWidth = str(value)
        elif re.match('EXIF ExifImageLength', tag):
            ExifImageLength = str(value)
    # 拼接GPS位置字符串
    gps_lat_str = '+%.4f'%GPS.get('GPSLatitude') if GPS.get('GPSLatitude') else ''  # 纬度
    gps_lng_str = '+%.4f'%GPS.get('GPSLongitude') if GPS.get('GPSLongitude') else ''  # 经度
    if GPS.get('GPSAltitude'):  # 高度
        gps_alt_str = '+%.4f/'%GPS.get('GPSAltitude') if isinstance(GPS.get('GPSAltitude'), float) else '+%s/'%GPS.get('GPSAltitude')
    else:
        gps_alt_str = ''
    location = gps_lat_str + gps_lng_str + gps_alt_str
    result = {'GPS_information': GPS, 'date_information': date, "hardware_make": hardware_make, "location": location,
              "hardware_model": hardware_model, "hardware_software": hardware_software, "width": width, "height": height,
              "ExifImageWidth": ExifImageWidth, "ExifImageLength": ExifImageLength, "encoded_date": date}
    logger.debug(result)
    return result


def get_audio_info(file_path):
    """获取音频时长、采样率等信息"""
    media_data = get_media_meta(file_path)  # 获取媒体文件元数据
    # 时长--毫秒转换
    duration = media_data['general_data'].get('duration')  # 原始时长为毫秒
    if not duration:  # mediainfo不能读取某些小米手机录音的音频文件
        total = get_media_meta_by_ffmpeg(file_path).get('total')
        duration = total*1000 if total else 0
    duration_sec = duration / 1000  # 秒数计算
    duration_str = '%.2d:%.2d:%.2f'%(duration_sec // 3600, duration_sec % 3600 // 60, duration_sec % 3600 % 60)
    # 音频格式
    audio_format = media_data['audio_data'].get('format')
    # 音频比特率
    bit_rate = media_data['audio_data'].get('bit_rate')
    bit_rate = '%d kbps' % (bit_rate / 1000) if bit_rate else ''
    # 音频通道数
    channel_s = media_data['audio_data'].get('channel_s')
    # 音频输出通道
    channel_layout = media_data['audio_data'].get('channel_layout')
    # 音频采样率
    sampling_rate = media_data['audio_data'].get('sampling_rate')
    sampling_rate = '%.1f kHz' % (sampling_rate / 1000) if sampling_rate else ''
    # 音频帧速率
    frame_rate = media_data['audio_data'].get('frame_rate')
    frame_rate = '%.2f FPS' % float(frame_rate) if frame_rate else ''
    # 音频流大小
    stream_size = media_data['audio_data'].get('stream_size')
    stream_size = '%.2f MiB' % (stream_size / 1024**2) if stream_size else ''
    # 总比特率
    overall_bit_rate = media_data['general_data'].get('overall_bit_rate')
    overall_bit_rate = '%d kbps'%(overall_bit_rate // 1000) if overall_bit_rate else ''
    # 格式
    format = media_data['general_data'].get('format')
    # 创建日期
    file_creation_date = media_data['general_data'].get('file_creation_date')
    # 最近修改日期
    file_last_modification_date =  media_data['general_data'].get('file_last_modification_date')
    result = {"duration": duration, "duration_sec": duration_sec, "duration_str": duration_str, 
              'format':audio_format, 'bit_rate':bit_rate, 'channel_s':channel_s, 'channel_layout':channel_layout, 
              'sampling_rate':sampling_rate, 'frame_rate':frame_rate, 'stream_size':stream_size,
              "format": format, "frame_rate": frame_rate, "overall_bit_rate": overall_bit_rate,
              "file_creation_date": file_creation_date, "file_last_modification_date": file_last_modification_date,
              }
    logger.debug(result)
    return result


def get_image_meta(file_path):
    """获取图片完整EXIF元数据"""
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f)
        return tags
    except Exception as e:
        logger.error('读取 %s EXIF信息出错! ERROR: %s' % (file_path, e))
        return None


def get_media_meta_by_ffmpeg(file, ffmpeg_path=settings.FFMPEG_PATH):
    """
    获取视频的 duration 时长 长 宽
    """
    # 开启静默模式不弹cmd窗口
    # process = subprocess.Popen([self.ffmpeg_path, '-i', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # startupinfo = subprocess.STARTUPINFO()
    # startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
    # startupinfo.wShowWindow = subprocess.SW_HIDE
    process = subprocess.Popen([ffmpeg_path, '-i', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startupinfo)
    stdout, stderr = process.communicate()
    pattern_duration = re.compile(r"Duration:\s(\d+?):(\d+?):(\d+\.\d+?),")
    pattern_size = re.compile(r",\s(\d{3,4})x(\d{3,4})")
    matches = re.search(pattern_duration, stdout.decode('utf-8'))
    size = re.search(pattern_size, stdout.decode('utf-8'))
    result = {
            'total': 0,
            'width': 0,
            'height': 0
        }
    if size:
        size = size.groups()
        width = size[0]
        height = size[1]
        result['width'] = int(width)
        result['height'] = int(height)
    if matches:
        matches = matches.groups()
        # logger.debug(matches)
        hours = Decimal(matches[0])
        minutes = Decimal(matches[1])
        seconds = Decimal(matches[2])  # 处理为十进制，避免小数点报错
        total = 0
        total += 60 * 60 * hours
        total += 60 * minutes
        total += seconds
        result['total'] = total
        result['hours'] = hours
        result['minutes'] = minutes
        result['seconds'] = seconds
        result["duration_sec"] = total
        result["duration"] = total * 1000
    return result


def get_media_meta(file_path):
    """获取媒体文件的元数据"""
    mediainfo = MediaInfo.parse(file_path)
    #通用信息
    general_data = mediainfo.general_tracks[0].to_data()
    #视频信息
    if mediainfo.video_tracks:  # 有些视频去除了视频数据，或者为纯音频，没有这个数据直接取值会报错
        video_data = mediainfo.video_tracks[0].to_data()
    else:
        video_data = dict()
    #音频信息
    if mediainfo.audio_tracks:  # 有些视频去除了音频数据，没有这个数据直接取值会报错
        audio_data = mediainfo.audio_tracks[0].to_data()
    else:
        audio_data = dict()
    return {'general_data': general_data, 'video_data': video_data, 'audio_data': audio_data}


def get_media_meta_sample(file_path):
    """获取媒体文件的元数据,将所有数据汇总到单一dict中,不再区分tracks"""
    mediainfo = MediaInfo.parse(file_path)
    #通用信息
    res = mediainfo.general_tracks[0].to_data()
    #视频信息
    if mediainfo.video_tracks:
        res.update(mediainfo.video_tracks[0].to_data())
    #音频信息
    if mediainfo.audio_tracks:
        res.update(mediainfo.audio_tracks[0].to_data())
    return res


def get_media_info_for_excel(dir_path):
    """获取目录下所有文件的媒体信息"""
    dir_path = os.path.abspath(dir_path)
    files_with_cate = get_files_with_fileCategory_extended(dir_path)
    FUNC_DICT = {
        "video": get_video_info,
        "audio": get_audio_info,
        "image": get_image_info
    }
    STR_DICT = {
        "encoded_date": "拍摄时间", "duration_str": "时长", "format": "媒体格式", "file_creation_date": "创建日期",
        "file_last_modification_date": "最近修改日期", "overall_bit_rate": "总比特率", "frame_rate": "帧速率",
        "location": "GPS定位", "hardware_make": "拍摄设备", "hardware_model": "设备型号", "hardware_software": "固件版本", 
        "width": "分辨率-宽", "height": "分辨率-高", "ExifImageWidth": "ExifImageWidth","ExifImageLength":"ExifImageLength",
        "sampling_rate": "音频采样率", "stream_size": "音频流大小", "channel_layout": "音频输出通道",
        "channel_s": "音频通道数", "bit_rate": "音频比特率",
        }
    res = {'video': [], 'audio': [], 'image': []}
    for file_path, cate in files_with_cate.items():
        file_name = os.path.basename(file_path)
        file_size = get_size_str(os.path.getsize(file_path))
        if cate not in res:
            continue
        logger.debug('\n 正在操作： %s' % file_path)
        info = FUNC_DICT[cate](file_path)  # 获取文件元数据
        info_new = {"文件名": file_name, "文件路径": file_path, "文件大小": file_size}
        for key, val in info.items():
            if key not in STR_DICT:
                logger.debug('key:%s not in SRC_DICT!' % key)
                continue
            info_new[STR_DICT[key]] = val
        res[cate].append(info_new)
    # print(res)
    return res


def get_filetype(file_path):
    """获取文件真实数据类型, 只用filetype识别"""
    kind = filetype.guess(file_path)
    if kind is None:
        logger.debug('Cannot guess file type!  %s' % file_path)
        return
    return kind


def check_filetype(file_path, file_type):
    """检查文件是否为指定数据类型"""
    file_type = file_type.lower()
    if os.path.isdir(file_path):
        return True if file_type == 'dir' else False
    kind = get_filetype(file_path)
    if not kind:
        return False
    if kind.extension == file_type:  # file_type是后缀名 例如 jpg，mp4
        return True
    # if kind.extension in settings.GEN_TYPES.get(file_type, []):  # file_type是数据类型 例如 video, image
    #     return True
    category = kind.mime.split("/")[0]
    if category == file_type:  # file_type是文件类别 例如 video, image
        return True
    return False


def check_filetype_extended(file_path, file_type):
    """检查文件是否为指定数据类型,并自定义一些filetype模块无法识别的文件类型"""
    file_type = file_type.lower()
    if os.path.isdir(file_path):
        return True if file_type == 'dir' else False
    res = get_type_extended(file_path)
    if not res:
        return False
    mime = res.get('mime')
    category = mime.split("/")[0]
    extension = res.get('extension')
    if extension == file_type:  # file_type是后缀名 例如 jpg，mp4
        return True
    if category == file_type:  # file_type是文件类别 例如 video, image
        return True
    return False


def check_filetypes(file_path, *_types):
    """检查文件是否为指定数据类型"""
    file_types = [file_type.lower() for file_type in _types]
    if os.path.isdir(file_path):
        return True if 'dir' in file_types else False
    kind = get_filetype(file_path)
    if not kind:
        return False
    if kind.extension in file_types:  # file_type是后缀名 例如 jpg，mp4
        return True
    if kind.mime.split("/")[0] in file_types:  # file_type是数据类型 例如 video, image
        return True
    return False


def check_filetypes_extended(file_path, *_types):
    """检查文件是否为指定数据类型,并自定义一些filetype模块无法识别的文件类型"""
    file_types = [file_type.lower() for file_type in _types]
    if os.path.isdir(file_path):
        return True if 'dir' in file_types else False
    res = get_type_extended(file_path)
    if not res:
        return False
    mime = res.get('mime')
    category = mime.split("/")[0]
    extension = res.get('extension')
    if extension in file_types:  # file_type是后缀名 例如 jpg，mp4
        return True
    if category in file_types:  # file_type是文件类别 例如 video, image
        return True
    return False


def get_files_by_filetype(dir_path, file_type):
    """
    遍历目录路径获取所有指定类型文件的路径列表
    :param dir_path: 要遍历的路径
    :param file_type: 指定的数据类型
    :return: path_list
    """
    path_list = []
    if os.path.isfile(dir_path):
        if check_filetype_extended(dir_path, file_type):
            path_list.append(dir_path)
    elif os.path.isdir(dir_path):
        for root, dirs, files in os.walk(dir_path):
            for filename in files:
                img_path = os.path.join(root, filename)
                if check_filetype_extended(img_path, file_type):
                    path_list.append(img_path)
    return path_list


def get_mime_by_mimetypes(file_path):
    """调用mimetypes模块判断文件类型,可以判断文本类型"""
    mime_type, encoding = mimetypes.guess_type(file_path)
    return mime_type


def get_type(file_path):
    """获取文件真实数据类型
    只用filetype识别"""
    kind = filetype.guess(file_path)
    if kind:
        return {'extension': kind.extension, 'mime': kind.mime}


def get_type_extended(file_path):
    """获取文件数据类型描述
    先用filetype模块识别文件字节码,
    再用mimetypes模块识别文件后缀名,
    最后再用自己添加的数据映射表识别
    """
    kind = get_filetype(file_path)
    if kind:
        return {'extension': kind.extension, 'mime': kind.mime}
    else:
        return get_type_by_ext(file_path)


def get_type_by_ext(file_path):
    """根据文件后缀名识别数据类型,
    先用mimetypes模块识别,
    最后再用自己添加的数据识别"""
    mime_type = get_mime_by_mimetypes(file_path)
    ext = os.path.splitext(file_path)[-1][1:].lower()
    if mime_type:
        # return {'extension': mime_type.split('/')[-1], 'mime': mime_type}
        return {'extension': ext, 'mime': mime_type}
    else:
        mime_type = settings.MIME_TYPES_EXTEND.get(ext)
        if mime_type:
        #   return {'extension': mime_type.split('/')[-1], 'mime': mime_type}
            return {'extension': ext, 'mime': mime_type}


def get_file_category(file_path):
    """获取文件类型 video image audio, 只用filetype识别
    """
    kind = filetype.guess(file_path)
    if kind:
        return kind.mime.split("/")[0]


def get_file_category_extended(file_path):
    """获取文件类型 video image audio
    先用filetype模块识别文件字节码,
    再用mimetypes模块识别文件后缀名,
    最后再用自己添加的数据映射表识别
    """
    file_type_desc = get_type_extended(file_path)
    if file_type_desc:
        mime = file_type_desc.get('mime')
        if mime:
            return mime.split("/")[0]


def get_files_with_fileCategory(_path):
    """获取文件路径和文件类别信息  例如 {'1.jpg': 'image'}
    仅用filetype识别文件字节码
    """
    res = {}
    if os.path.isfile(_path):
        cate = get_file_category(_path)
        if cate:
            res[_path] = cate
    elif os.path.isdir(_path):
        for root, dirs, files in os.walk(_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                cate = get_file_category(file_path)
                if cate:
                    res[file_path] = cate
    return res


def get_files_with_fileCategory_extended(_path):
    """获取文件路径和文件类别信息  例如 {'1.jpg': 'image'}
    先用filetype模块识别文件字节码,
    再用mimetypes模块识别文件后缀名,
    最后再用自己添加的数据映射表识别
    """
    res = {}
    if os.path.isfile(_path):
        cate = get_file_category_extended(_path)
        if cate:
            res[_path] = cate
    elif os.path.isdir(_path):
        for root, dirs, files in os.walk(_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                cate = get_file_category_extended(file_path)
                if cate:
                    res[file_path] = cate
    return res


def get_files_with_filetype(_path):
    """获取文件路径和文件数据类型信息,只用filetype模块识别"""
    res = {}
    if os.path.isfile(_path):
        res[_path] = get_type(_path)
    elif os.path.isdir(_path):
        for root, dirs, files in os.walk(_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                res[file_path] = get_type(file_path)
    return res


def get_files_with_filetype_extended(_path):
    """获取文件路径和文件数据类型信息,对于不能用文件字节码识别的文件,用后缀名识别"""
    res = {}
    if os.path.isfile(_path):
        res[_path] = get_type_extended(_path)
    elif os.path.isdir(_path):
        for root, dirs, files in os.walk(_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                res[file_path] = get_type_extended(file_path)
    return res


def make_duration_str(num, _format):
    """"根据指定格式,将时长秒数转变为3min2s这种格式"""
    res = ''
    hours = 0
    mins = 0
    seconds = 0
    if re.search(r'%H%M%S', _format, re.I):
        hours = num // 3600 
        mins = num % 3600 // 60
        seconds = int(num % 60)
    elif re.search(r'%H%M', _format, re.I):
        hours = num // 3600 
        mins = num % 3600 // 60
    elif re.search(r'%H', _format, re.I):
        hours = num // 3600       
    elif re.search(r'%M', _format, re.I):
        mins = num // 60           
    elif re.search(r'%S', _format, re.I):
        seconds = num
    if hours:
        res += '%shour' % hours
    if mins:
        res += '%smin' % mins
    if seconds:
        res += '%ssec' % seconds
    return res


def make_size_str(num, _format):
    """"根据指定格式,将文件大小转变为1.2GB,2.5MB这种格式"""
    res = ''
    if re.search(r'%MB|%M', _format, re.I):
        res = r'%.1fMB' % (num / 1024 ** 2)
    elif re.search(r'%GB|%G', _format, re.I):
        res = r'%.1fGB' % (num / 1024 ** 3)
    elif re.search(r'%KB|%K', _format, re.I):
        res = r'%.1fkB' % (num / 1024)
    elif re.search(r'%B', _format, re.I):
        res = '%skB' % num
    return res


def get_size_str(size):
    """根据文件大小返回1.2GiB 格式"""
    size = int(size)
    if size >= 1073741824:  # 1024**3
        return '%.2f GiB' % (size / 1073741824)
    if size >= 1048576:  # 1024**2
        return '%.2f MiB' % (size / 1048576)
    if size >= 1024:  # 1024
        return '%.2f KiB' % (size / 1024)
    return '%.2f Byte' % size


def get_image_from_video_by_ffmpeg(pathIn='', pathOut='', extract_time_point='0', continue_flag=False):
    '''
    从视频提取单张图片
    :param pathIn: 视频路径
    :param pathOut: 图片路径
    :param continue_flag: 是否覆盖， False 覆盖， True 跳过
    '''
    if continue_flag is True:
        if os.path.exists(pathOut):  # 继续之前进度
            print(pathOut, "已存在,跳过！")
            return
    pathOutDir = os.path.dirname(pathOut)
    if not os.path.exists(pathOutDir):
        os.makedirs(pathOutDir)
    # 提取视频帧图像
    # command = [ffmpeg_path, '-ss', extract_time_point, '-i', pathIn, '-frames:v', '1', pathOut]
    command = [settings.FFMPEG_PATH, '-ss', str(extract_time_point), '-i', pathIn, '-frames:v', '1', pathOut]  # 命令
    subprocess.call(command, shell=True)


