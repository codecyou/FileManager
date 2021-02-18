"""通用工具模块"""
from conf import settings
from core import logger
import os
import shutil
import time
import platform


def my_init():
    """检查工作环境，初始化工作环境"""
    if not os.path.exists(settings.RECORD_DIR):
        os.mkdir(settings.RECORD_DIR)
    if not os.path.exists(settings.DB_DIR):
        os.mkdir(settings.DB_DIR)
    if not os.path.exists(settings.LOG_DIR):
        os.mkdir(settings.LOG_DIR)


def get_system_info():
    """
    用于获取当前操作系统的类型 windows linux mac
        platform.uname()
            uname_result(system='Linux', node='work', release='3.10-3-amd64', version='#1 SMP
                Debian 3.10.11-1 (2013-09-10)', machine='x86_64', processor='')
                # python 3.3.2+64 bits on debian jessie 64 bits
        platform.uname()[0] 可以获取系统类型
    :return:
    """
    system_str = platform.uname()[0]  # 获取系统类型

    return system_str


def get_local_time(strf_str, timestamp=None):
    """
    根据给定的时间格式返回格式化后的当前时间
    :param strf_str: 时间格式
    :param timestamp: 时间戳
    :return:
    """
    if timestamp:
        return time.strftime(strf_str, time.gmtime(timestamp))
    return time.strftime(strf_str, time.localtime())


def get_times():
    """
    用于获取当前时间的两种格式， 保证日志记录时间和文件记录文件名同步
    :return: local_time1 用于拼接文件名， local_time2 用于传递给日志
    """
    local_time = time.localtime()  # 当前时间元组
    local_time1 = time.strftime("%Y%m%d%H%M%S", local_time)  # 用来生成文件名
    local_time2 = time.strftime("%Y-%m-%d %H:%M:%S", local_time)  # 用来记录传递给日志函数的时间
    return local_time1, local_time2


def make_str(temp_str, *args):
    """
    用于拼接字符串
    :param temp_str:  模板字符串
    :param args:  待填入字符串的值
    :return:
    """
    #

    return temp_str % args


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


def show_menu(msg):
    """用于打印操作菜单"""
    print("-" * 60)
    print(msg)
    print("-" * 60)


def input_path(path_str="目录路径", create_flag=False):
    """用于获取用户输入路径并检测输入路径是否正确,
        create_flag     标记是否新建目录
                        True如果目录不存在则新建
                        False不新建
    """
    while True:
        dir_path = input("请输入%s:" % path_str)
        if dir_path:  # 有输入内容
            dir_path = dir_path.strip()  # 防止出现输入' '
            if os.path.exists(dir_path):  # 检查路径是否存在
                # 当输入'/home/'时获取文件名就是''，所以加处理
                dir_path = os.path.abspath(dir_path)
                print("%s:\t%s" % (path_str, dir_path))  # 输出"文件路径： XXXXX"
                return dir_path
            else:
                if create_flag:
                    print("输入目录不存在！已为您新建该目录！")
                    os.makedirs(dir_path)
                    dir_path = os.path.abspath(dir_path)
                    return dir_path
        else:
            print("输入路径有误，请重新输入！")


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
                # print("输入目录不存在！已为您新建该目录！")
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


def filter_4_list(base_path, result_list):
    """
    用于从list中过滤出文件列表和目录列表，配合backup.py使用
    :param base_path: 文件完整父路径
    :param result_list: 保存文件在base_path下的相对路径的列表，即C:\a\b.txt, base_path为C:\a,result_list中保存b.txt，非绝对路径
    :return: file_list, dir_list 文件和文件夹列表，存储的都是相对路径
    """
    file_list = []  # 用于存放文件路径
    dir_list = []  # 用于存放目录路径
    for item in result_list:  # 过滤出文件列表和目录列表
        full_path = os.path.join(base_path, item)
        if os.path.isdir(full_path):
            dir_list.append(item)
        else:
            file_list.append(item)
    return file_list, dir_list


def filter_4_dict(src_path, dst_path, result_dict):
    """
    用于从dict中过滤出文件列表和目录列表，配合backup.py使用
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param result_dict: 保存文件信息的字典 {"only_in_src": [], "only_in_dst": [], "diff_files": [],"common_funny": []}
    :return: result 字典 保存的是文件的相对路径
            {"file_only_in_src": [], "file_only_in_dst": [], "dir_only_in_src": [],
                    "dir_only_in_dst": [], "diff_files": [],"common_funny": []}
    """
    result = dict()
    result["file_only_in_src"], result["dir_only_in_src"] = filter_4_list(src_path, result_dict["only_in_src"])
    result["file_only_in_dst"], result["dir_only_in_dst"] = filter_4_list(dst_path, result_dict["only_in_dst"])
    result["diff_files"] = result_dict["diff_files"]
    result["common_funny"] = result_dict["common_funny"]
    return result


def make_dirs(src_path, dst_path):
    """
    用于根据目录或者记录目录结构的文件，创建目录结构
    :param src_path: 目录路径或者记录目录结构的文件路径
    :param dst_path: 将要创建目录结构的路径
    :return:
    """
    if os.path.isfile(src_path):
        with open(src_path, 'r', encoding='utf-8') as f:
            dir_str_list = f.readlines()
        for item in dir_str_list:
            new_dir = os.path.join(dst_path, item.strip())
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
    else:
        # 如果是根据目录拷贝 需要判断dst_path是否是src_path的子目录，如果是 有可能会出现逻辑
        # 遍历文件目录
        dir_str_list = []
        # 遍历文件夹，在dst_path 下新建和src_path一样的目录结构
        for root, dirs, files in os.walk(src_path):
            # 遍历文件夹，添加到dir_str_list
            for file_dir in dirs:
                new_dir = os.path.join(root, file_dir).replace(src_path, dst_path)
                dir_str_list.append("%s" % new_dir)

        # 创建文件目录
        for new_dir in dir_str_list:
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
    msg = "拷贝%s 的目录结构到%s 完成！" % (src_path, dst_path)
    logger.operate_logger(msg)
    return msg, dir_str_list


def export_dirs(dir_path):
    """
    用于导出相对目录结构  即 D:\a\b\c 若 dir_path 为D:\a 则 相对目录结构为b\c
    :param dir_path: 要导出文件信息的目录路径
    :return: 记录文件路径，目录个数
    """

    dir_list = []
    record_path = ''  # 记录导出信息的文件的路径
    if not os.path.isdir(dir_path):  # 判断是否为目录
        print("输入的目录不是文件夹！")
        return None, dir_list
    print("正在导出目录结构信息...")
    # 遍历目录获取目录路径信息
    for root, dirs, files in os.walk(dir_path):
        for file_dir in dirs:
            # 获取相对目录结构 即 D:\a\b\c 若 dir_path 为D:\a 则 相对目录结构为b\c
            new_dir = os.path.join(root, file_dir).replace(dir_path, '')[1:]  # 去掉第一个路径分割符
            dir_list.append(new_dir)
    if len(dir_list):
        # 拼接目录结构得到导出文件名，若 dir_path 为D:\a 则 目录结构为D_a 导出文件名为目录结构_[D_a].txt
        if dir_path.count('\\'):
            file_dir = dir_path.replace(':', '').replace('\\', '_')
        else:  # 因为windows的路径分隔符也可以使用/
            file_dir = dir_path.replace(':', '').replace('/', '_')
        record_path = os.path.join(settings.RECORD_DIR, '目录结构_[%s].txt' % file_dir)  # 构造保存详细文件信息文件的文件名
        with open(record_path, "w", encoding="utf-8") as f:
            for item in dir_list:
                f.write("%s\n" % item)
        logger.operate_logger("导出%s 的目录结构信息到%s 完成！" % (dir_path, record_path))
        return record_path, dir_list
    else:
        print("该目录没有子目录！")
        return record_path, dir_list


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
                logger.error_logger(e)
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
                logger.error_logger(e)
        if del_flag:  # 判断是否要删除
            os.remove(src_path)


def copy_file2(src_path, dst_path, failed_list):
    """
    用于拷贝文件
    :param src_path:  源路径
    :param dst_path:  目的路径
    :param failed_list: 用于记录剪切失败的文件，主要是目标目录下已存在的同名文件
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
                failed_list.append(src_path)
                if not os.path.exists(src_path):
                    logger.file_error_logger(src_path, '源文件不存在！')
                else:
                    logger.file_error_logger(src_path, e)
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
                failed_list.append(src_path)
                if not os.path.exists(src_path):
                    logger.file_error_logger(src_path, '源文件不存在！')
                else:
                    logger.file_error_logger(src_path, e)


def get_pathlist(dir_path):
    """
    遍历目录路径获取所有文件的路径列表
    :param dir_path: 要遍历的路径
    :return: path_list
    """
    path_list = []
    if os.path.isfile(dir_path):
        # print(dir_path, 'isfile!')
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
            # logger.file_error_logger(src_path, e)
            logger.error_logger(e)


def move_file2(src_path, dst_path, failed_list):
    """
    用于剪切文件
    :param src_path:  源路径
    :param dst_path:  目的路径
    :param failed_list: 用于记录剪切失败的文件，主要是目标目录下已存在的同名文件
    :return:
    """
    if os.path.isdir(src_path):
        # dst_dir = os.path.join(dst_path, os.path.basename(src_path))
        # if not os.path.exists(dst_dir):
        #     os.makedirs(dst_dir)
        file_list = get_pathlist(src_path)
        for item in file_list:
            new_dst_path = item.replace(src_path, dst_path)
            move_file2(item, new_dst_path, failed_list)
    else:
        try:
            shutil.move(src_path, dst_path)
        except Exception as e:
            # 如果目标目录不存在则会报错，比如shutil.move(r'C:1\1.jpg', r'd:1\1.jpg'),而D盘不存在1文件夹
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(src_path):
                # 原文件不存在
                logger.file_error_logger(src_path, '源文件不存在！')
                failed_list.append(src_path)
            elif not os.path.exists(dst_dir):
                # 原文件存在，目标文件所在目录不存在
                os.makedirs(dst_dir)  # os.makedirs可递归创建文件夹
                shutil.move(src_path, dst_path)
            else:
                failed_list.append(src_path)
                logger.file_error_logger(src_path, e)


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
    safe_del_dir = os.path.abspath("%s/del_from_%s_%s" % (get_safe_del_dir(dir_path), os.path.basename(dir_path), time.strftime("%Y%m%d%H%M%S", time.localtime())))
    if not os.path.exists(safe_del_dir):
        os.makedirs(safe_del_dir)
    return safe_del_dir


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
    file_basename = os.path.basename(file_path)
    # 获取目录结构
    if name_simple:
        # 简单目录结构
        old_dir_path = os.path.abspath(old_dir_path)
        # 判断是否同级目录,第一级目录结构值为''，第二级为/xx/xxx
        dir_str = os.path.dirname(file_path).replace(old_dir_path, '')
        # 比如 old_dir_path 为 C:\Users时
        # C:\Users\a.jpg    dir_str 为''  而C:\Users\b\a.jpg    dir_str 为'\b'
        if dir_str:
            # 判断是否是多级目录 ，如果是需要修改文件名
            dir_str = dir_str[1:]  # 去除dir_str 为'\b' 前面的'\'
        else:
            # 单级目录直接拼接文件名返回
            return os.path.join(new_dir_path, file_basename)
    else:
        # 绝对目录结构 C:\Users\pro\PycharmProjects 改为 C_Users_pro_PycharmProjects 然后拼接新目录路径
        dir_str = os.path.dirname(file_path)

    if dir_str.count('\\'):  # 判断是否是windows
        dir_str = dir_str.replace(':', '').replace("\\", '_')  # replace(":", "")去除盘符后面的 "："
    else:  # 是linux  因为windows的路径分隔符也可以使用/
        dir_str = dir_str.replace(':', '').replace("/", "_")  # 用来记录原文件的目录结构 格式"C_Users_pro_PycharmProjects"
    if file_basename.count('.'):
        new_file_name = "%s_[%s].%s" % (file_basename, dir_str, file_basename.split('.')[-1])
    else:
        new_file_name = "%s_[%s]" % (file_basename, dir_str)
    new_path = os.path.join(new_dir_path, new_file_name)

    return new_path


def move_or_copy_file(files, old_dir_path, new_dir_path, deal_mode="move", name_simple=True, log_flag=True):
    """
    用于移动或者复制文件，并将新旧文件名记录到new_old_record,并导出文件
    :param files: 保存文件信息的集合，可以是dict {name|size|name_size : [path1,path2]} 可以是list [path1,path2]
    :param old_dir_path: 原目录路径
    :param new_dir_path: 新目录路径
    :param deal_mode: 文件处理模式  "move" 剪切  "copy" 复制
    :param name_simple: 文件重命名模式  True 简单目录结构  False 绝对目录结构
    :param log_flag: 标记是否记录日志  True 记录  False 不记录
    :return: 
    """""
    new_old_record = {}  # 用于保存新旧文件名信息，格式为"{new_file: old_file, }"
    record_path = None  # 用来记录导出的新旧文件名记录路径 用于返回
    failed_list = []  # 用于记录拷贝或剪切失败的文件信息
    if deal_mode == "copy":
        deal_func = copy_file  # 根据模式将函数名赋值给deal_func变量
    else:
        deal_func = move_file
    if isinstance(files, dict):
        for item in files:
            for old_path in files[item]:
                # 从多级目录往单级目录里面拷贝或者移动文件时可能会出现同名文件，所有加上对应目录层级描述
                # 格式：当name_simple为True 为相对目标目录的目录层级  为False 为原文件的绝对目录层级
                new_path = make_new_path(old_path, old_dir_path, new_dir_path, name_simple)  # 调用make_new_path方法 获得新路径
                try:
                    deal_func(old_path, new_path)  # 由上面赋值的函数名变量调用函数代码
                except Exception as e:
                    failed_list.append(old_path)
                    print("操作%s文件失败，详情请查看错误日志！" % old_path)
                    # logger.error_logger(e)
                    logger.file_error_logger(old_path, e)
                else:
                    new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
    elif isinstance(files, list):
        for old_path in files:
            new_path = make_new_path(old_path, old_dir_path, new_dir_path, name_simple)  # 调用make_new_path方法 获得新路径
            try:
                deal_func(old_path, new_path)
            except Exception as e:
                failed_list.append(old_path)
                print("操作%s文件失败，详情请查看错误日志！" % old_path)
                # logger.error_logger(e)
                logger.file_error_logger(old_path, e)
            else:
                new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
    # 写出到记录文件和日志
    if len(new_old_record):
        write_time, log_time = get_times()  # 获取当前时间的两种格式
        record_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("new_old_record", write_time))
        export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        if deal_mode == 'copy':
            msg = "从%s 拷贝%s个文件到%s，新旧文件名导出到%s" % (old_dir_path, len(new_old_record), new_dir_path, record_path)
        else:
            msg = "从%s 剪切%s个文件到%s，新旧文件名导出到%s" % (old_dir_path, len(new_old_record), new_dir_path, record_path)
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("failed", write_time))
            msg += "\n\t\t%s个文件操作失败，文件信息导出到%s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for item in failed_list:
                    f.write('%s\n' % item)
        if log_flag:
            logger.operate_logger(msg, log_time)

    return record_path


def deal_files(files, old_dir_path, new_dir_path, deal_mode="move", rename_flag=True, name_simple=True, log_flag=True):
    """
    用于移动或者复制文件，并将新旧文件名记录到new_old_record,并导出文件   
    :param files: 保存文件信息的集合，可以是dict {name|size|name_size : [path1,path2]} 可以是list [path1,path2]
    :param old_dir_path: 原目录路径
    :param new_dir_path: 新目录路径
    :param deal_mode: 文件处理模式  "move" 剪切  "copy" 复制
    :param rename_flag: 标记是否对文件进行重命名  True 重命名  False 不重命名        主要用在是否原样复制文件 还是加入目录结构
    :param name_simple: 文件重命名模式  True 简单目录结构  False 绝对目录结构
    :param log_flag: 标记是否记录日志  True 记录  False 不记录
    :return: 
    """""
    new_old_record = {}  # 用于保存新旧文件名信息，格式为"{new_file: old_file, }"
    record_path = None  # 用来记录导出的新旧文件名记录路径 用于返回
    failed_list = []  # 用于记录拷贝或剪切失败的文件信息
    if deal_mode == "copy":
        deal_func = copy_file  # 根据模式将函数名赋值给deal_func变量
    else:
        deal_func = move_file
    if rename_flag:  # 看是否需要对文件进行重命名，即是否需要加上目录描述
        # 从多级目录往单级目录里面拷贝或者移动文件时可能会出现同名文件，所有加上对应目录层级描述
        # 格式：当name_simple为True 为相对目标目录的目录层级  为False 为原文件的绝对目录层级
        get_new_path_func = make_new_path
    else:
        # 简单的将一个目录的文件剪切或拷贝到另一目录
        # 匿名函数实现文件目录替换  其中none_para 是无用参数 只为参数占位 方便后面统一传参使用
        get_new_path_func = lambda file_path, old_dir, new_dir, none_para: file_path.replace(old_dir, new_dir)
    if isinstance(files, dict):
        for item in files:
            for old_path in files[item]:
                new_path = get_new_path_func(old_path, old_dir_path, new_dir_path, name_simple)  # 调用make_new_path方法 获得新路径
                try:
                    deal_func(old_path, new_path)  # 由上面赋值的函数名变量调用函数代码
                except Exception as e:
                    failed_list.append(old_path)
                    print("操作%s文件失败，详情请查看错误日志！" % old_path)
                    # logger.error_logger(e)
                    logger.file_error_logger(old_path, e)
                else:
                    new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
    elif isinstance(files, list):
        for old_path in files:
            new_path = get_new_path_func(old_path, old_dir_path, new_dir_path, name_simple)  # 调用make_new_path方法 获得新路径
            try:
                deal_func(old_path, new_path)
            except Exception as e:
                failed_list.append(old_path)
                print("操作%s文件失败，详情请查看错误日志！" % old_path)
                # logger.error_logger(e)
                logger.file_error_logger(old_path, e)
            else:
                new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
    # 写出到记录文件和日志
    if len(new_old_record):
        write_time, log_time = get_times()  # 获取当前时间的两种格式
        record_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("new_old_record", write_time))
        export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        if deal_mode == 'copy':
            msg = "从%s 拷贝%s个项目到%s，新旧文件名导出到%s" % (old_dir_path, len(new_old_record), new_dir_path, record_path)
        else:
            msg = "从%s 剪切%s个项目到%s，新旧文件名导出到%s" % (old_dir_path, len(new_old_record), new_dir_path, record_path)
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("failed", write_time))
            msg += "\n\t\t%s个文件操作失败，文件信息导出到%s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for item in failed_list:
                    f.write('%s\n' % item)
        if log_flag:
            logger.operate_logger(msg, log_time)

    return record_path


def restore_file_by_record(record_path, log_flag=True):
    """
    用于从record_path读取new_old_record记录来还原文件
    :param record_path: new_old_record记录文件路径
    :param log_flag: 标记是否记录日志  True 记录  False 不记录
    :return: restore_record_path, len(restore_list) 还原记录文件路径，还原文件的个数
    """
    restore_list = []  # 用于记录还原文件信息 格式["now_file -> restore_file",]
    restore_record_path = settings.RESTORE_RECORD_PATH  # 用于导出还原记录
    new_old_record = import_new_old_record(record_path)  # 导入new_old_record记录
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        # print(old_file)
        if os.path.exists(new_file):
            # copy_file(new_file, old_file, True)
            move_file(new_file, old_file)
            restore_list.append("%s  ->  %s" % (new_file, old_file))
    if len(restore_list):
        print_str = "根据记录%s 还原了%s个文件，还原文件信息记录到%s" % (record_path, len(restore_list), restore_record_path)
        if log_flag:
            logger.record_logger(restore_list, restore_record_path, print_str)
    else:
        print("未找到可以还原的文件！")

    return restore_record_path, len(restore_list)


def remove_file_by_info(dir_path, record_path, safe_flag=settings.SAFE_FLAG):
    """
    根据样本或者文件相信信息删除文件
    用于从输入样本目录路径或样本记录文件路径，删除dir_path对应文件
    :param dir_path: 要进行文件删除的目录路径
    :param record_path: 样本路径 ，或记录文件信息的文件路径
    :param safe_flag: 标志是否安全删除，True 会将删除文件拷贝到safe_del文件夹下  False 会直接删除
    :return: del_record_path, del_count  记录导出路径，删除个数
    """
    del_list = []
    del_record_path = None  # 记录删除记录导出文件路径
    # 用于存储文件信息数据，格式为[{"name": file_name, "size": file_size, "mtime": file_mtime, "path": file_path},]
    safe_del_record = {}  # 记录安全删除文件文件名前后对应信息，即回收站文件夹内新名字和文件原名字的记录
    if os.path.isfile(record_path):  # 获取要被删除的文件信息
        del_file_list = import_file_info(record_path)
    else:
        del_file_list = get_file_info(record_path)
    src_file_list = get_file_info(dir_path)  # 获取要进行删除操作的目录的文件信息
    # safe_del_dir = os.path.join(settings.SAFE_DEL_DIR, get_local_time("%Y%m%d%H%M%S"))
    # safe_del_dir = makedir4safe_del(dir_path)
    safe_del_dir = os.path.join(get_safe_del_dir(dir_path), get_local_time("%Y%m%d%H%M%S"))
    for src_file in src_file_list:
        for del_file in del_file_list:
            if src_file["name"] == del_file["name"] and src_file["size"] == del_file["size"]:
                if safe_flag:
                    # 安全删除
                    safe_del_file = make_new_path(src_file["path"], os.path.dirname(src_file["path"]), safe_del_dir, False)
                    # shutil.move(src_file["path"], safe_del_file)
                    # copy_file(src_file["path"], safe_del_file, True)
                    move_file(src_file["path"], safe_del_file)
                    safe_del_record[safe_del_file] = src_file["path"]
                else:
                    os.remove(src_file["path"])  # 在要删除的目录中找到该文件并删除
                    src_file_info = "%s\t%s\t%s" % (src_file["size"], src_file["mtime"], src_file["path"])
                    del_list.append(src_file_info)  # 记录删除的文件信息
    if safe_flag:
        # 写出到安全删除记录文件
        del_count = len(safe_del_record)
        if del_count:
            del_record_path = os.path.join(settings.RECORD_DIR, 'safe_del %s.txt' % os.path.basename(safe_del_dir))
            export_new_old_record(safe_del_record, del_record_path)
            msg = "删除了%s 记录中的%s个文件！被删除文件信息记录到%s" % (record_path, len(safe_del_record), del_record_path)
            logger.operate_logger(msg)
        else:
            print("没有找到要删除的样本对应的文件！")
    else:
        del_count = len(del_list)
        if del_count:
            del_record_path = settings.DEL_RECORD_PATH
            msg = "删除了%s 下%s个文件！被删除文件信息记录到%s" % (dir_path, len(del_list), del_record_path)
            logger.record_logger(del_list, settings.DEL_RECORD_PATH, msg)  # 记录日志
        else:
            print("没有找到要删除的样本对应的文件！")

    return del_record_path, del_count


def remove_file_by_record(record_path, safe_flag=settings.SAFE_FLAG):
    """
    根据文件名记录new_old_record文件删除文件
    用于获取要删除的文件的new_old_record，
    拷贝导出的文件经人工审核后留下要保留的文件或者要删除的文件，调用这个方法更新记录，然后可以用新记录删除原文件
    :param record_path: 新旧文件名记录文件路径  new_old_record
    :param safe_flag: safe_flag: 标志是否安全删除，True 会将删除文件拷贝到safe_del文件夹下  False 会直接删除
    :return: del_record_path, del_count
    """
    del_dict = import_new_old_record(record_path)  # 记录要删除的文件名记录信息  new_old_record
    del_record_path = None
    if safe_flag:
        # 安全删除
        safe_del_record = {}  # 记录安全删除文件文件名前后对应信息，即回收站文件夹内新名字和文件原名字的记录
        # 保存到safe_del的目录名路径
        # safe_del_dir = os.path.join(settings.SAFE_DEL_DIR, get_local_time("%Y%m%d%H%M%S"))
        safe_del_dir = None
        for src_path in del_dict.values():
            if os.path.exists(src_path):
                if safe_del_dir is None:
                    safe_del_dir = os.path.join(get_safe_del_dir(src_path), get_local_time("%Y%m%d%H%M%S"))
                safe_del_file = make_new_path(src_path, os.path.dirname(src_path), safe_del_dir, False)
                # shutil.move(src_path, safe_del_file)
                # copy_file(src_path, safe_del_file, True)
                move_file(src_path, safe_del_file)
                safe_del_record[safe_del_file] = src_path
        # 写出到安全删除记录文件
        del_count = len(safe_del_record)
        if del_count:
            del_record_path = os.path.join(settings.RECORD_DIR, 'safe_del %s.txt' % os.path.basename(safe_del_dir))
            export_new_old_record(safe_del_record, del_record_path)
            msg = "删除了%s 记录中的%s个文件！被删除文件信息记录到%s" % (record_path, len(safe_del_record), del_record_path)
            logger.operate_logger(msg)
    else:
        # 直接删除
        del_list = []  # 记录被删除文件信息
        for src_path in del_dict.values():
            if os.path.exists(src_path):
                os.remove(src_path)
                del_list.append(src_path)
        del_count = len(del_list)
        if del_count:
            del_record_path = settings.DEL_RECORD_PATH
            msg = "删除了%s记录中的%s个文件！被删除文件信息记录到%s" % (record_path, len(del_list), del_record_path)
            logger.record_logger(del_list, settings.DEL_RECORD_PATH, msg)  # 记录日志

    return del_record_path, del_count


def get_del_record(record_path, dir_path, save_flag=True):
    """
    用于获取要删除的文件的new_old_record，
    拷贝导出的文件经人工审核后留下要保留的文件或者要删除的文件，调用这个方法更新记录，然后可以用新记录删除原文件
    :param record_path: 新旧文件名记录文件路径  new_old_record
    :param dir_path: 导出的文件所在目录
    :param save_flag: 标记目录下的文件是要保留的还是要删除的 True 保留 False 删除
    :return:
    """
    record_dict = import_new_old_record(record_path)  # 记录要删除的文件名记录信息  new_old_record
    file_list = []  # 记录遍历dir_path文件路径信息
    del_dict = {}  # 记录要删除的文件名记录信息

    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            # 获取文件信息
            file_list.append(os.path.join(root, file_name))

    if save_flag:  # 为True,则表示该文件目录下的文件是要保留的
        for item in record_dict:
            if item not in file_list:
                del_dict[item] = record_dict[item]
    else:  # 为False，则表示该文件目录下的文件是要删除的
        for item in record_dict:
            if item in file_list:
                del_dict[item] = record_dict[item]
    new_record_path = '[del]'.join(os.path.splitext(record_path))
    with open(new_record_path, 'w', encoding='utf-8') as f:
        for new_file in del_dict:
            f.write("%s\t%s\n" % (new_file, del_dict[new_file]))

    print("更新文件名记录到%s" % new_record_path)
    return new_record_path


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
    # print(dir_list)
    dir_list = dir_list[::-1]  # 取倒序
    del_list = []
    # print(dir_list)
    for item in dir_list:
        if not os.listdir(item):  # 判断是否空文件夹
            os.rmdir(item)
            del_list.append(item)
    if len(del_list):
        msg = "清除了%s  下%s个空文件夹!删除的空文件夹信息记录到%s" % (dir_path, len(del_list), settings.DEL_RECORD_PATH)
        logger.record_logger(del_list, settings.DEL_RECORD_PATH, msg)  # 记录日志
    else:
        msg = "%s  下没有找到空文件夹！" % dir_path
        print("没有找到空文件夹！")
    return msg


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


def get_file_info(dir_path):
    """
    用walk函数实现遍历目录下所有文件
    :param dir_path: 要遍历的目录路径
    :return: file_list
    数据格式为[{"name": file_name, "size": file_size, "mtime": file_mtime, "path": file_path},]
    """
    file_list = []
    # 用于储存文件信息，记录数据格式为[{"name": file_name, "size": file_size, "mtime": file_mtime, "path": file_path}]
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            # 获取文件信息
            file_path = os.path.join(root, file_name)
            file_size = os.path.getsize(file_path)  # 得到的是int数据
            file_mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(os.path.getmtime(file_path)))
            file = {"name": file_name, "size": file_size, "mtime": file_mtime, "path": file_path}
            file_list.append(file)
    return file_list  # 返回遍历完成的文件信息


def get_files_info(dir_path):
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
            file_mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(os.path.getmtime(file_path)))
            file = {"name": file_name, "size": file_size, "mtime": file_mtime}
            file_dict[file_path] = file
    return file_dict  # 返回遍历完成的文件信息


def export_file_info(dir_path):
    """
    用于导出文件信息    # file_info : "file_size\tfile_mtime\tfile_path"
    :param dir_path: 要导出文件信息的目录路径
    :return: 信息文件路径，文件个数
    """
    if not os.path.isdir(dir_path):  # 判断是否为目录
        print("输入的目录不是文件夹！")
        # raise TypeError("输入的目录不是文件夹！")
        return
    print("正在导出文件信息...")
    file_list = get_file_info(dir_path)  # 调用get_file_info函数获取文件信息列表
    # file_list: [{"name": file_name, "size": file_size, "mtime": file_mtime, "path": file_path}, ]
    file_dir = os.path.basename(dir_path)  # 获取目录名
    if not file_dir:  # 如果遍历"C:\"  那获取目录名为None
        file_dir = os.path.dirname(dir_path)[0]  # 取盘符做目录名
    # file_name_record = file_dir + '.txt'  # 保存文件名
    record_path = os.path.join(settings.RECORD_DIR, '%s_info.txt' % file_dir)  # 构造保存详细文件信息文件的文件名
    with open(record_path, "a", encoding="utf-8") as f:
        for item in file_list:
            f.write("%s\t%s\t%s\n" % (item["size"], item['mtime'], item["path"]))
    print("导出%s个文件信息到%s完成！" % (len(file_list), record_path))
    return record_path, len(file_list)


def import_file_info(file_path):
    """
    用于从记录文件导入文件信息  # file_info : "file_size\tfile_mtime\tfile_path"
    :param file_path: 之前导出的记录文件信息的记录文件路径
    :return:
    """
    file_list = []  # 用于存储从之前导出文件读取的文件信息
    with open(file_path, 'r', encoding='utf-8') as f:
        while True:
            read_str = f.readline()
            if read_str:  # 只有在为None和''时才不成立，文本里即使什么都没有也会是'\n'
                read_str = read_str.strip()
                if read_str:  # 846074	2020-02-01 08:56:00	C:\Users\pro\Desktop\s\P136.png
                    file_size = int(read_str.split("\t")[0])
                    file_mtime = read_str.split("\t")[1]
                    file_path = read_str.split("\t")[2]
                    file_name = os.path.basename(file_path)
                    file = {"name": file_name, "size": file_size, "mtime": file_mtime, "path": file_path}
                    file_list.append(file)
            else:  # 判断是否有内容，没有内容则返回
                break
    return file_list  # 返回遍历完成的文件信息


