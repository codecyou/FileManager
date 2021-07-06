#!/usr/bin/python3
"""用于搜索文件"""

from core import Mytools
import os
import re


def find_same(search_path, mode, filter_flag, filter_str, filter_mode=1):
    """#用walk函数实现遍历目录下所有文件，  加过滤功能
    根据mode搜索同名文件或者相同大小文件
    mode    "name" 同名
            "size" 相同大小
            "mtime" 相同修改时间
            "name_mtime" 同名且修改时间相同
            "name_size"  同名且大小相同
            "size_mtime" 大小相同且修改时间相同
            "filter_flag"  是否过滤 True 过滤
            "filter_str"  过滤内容
            "filter_mode"  过滤模式 1排除 2选中
    """

    file_dict = {}  # 用于储存相同文件,格式"{"name"或者"size": [file_path1,file_path1,],...}"
    count = 0  # 用于记录相同文件的个数
    filter_exts = filter_str.lower().replace('.', '').replace('，', ',').split(',')  # 文件后缀名列表

    if mode == "size":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        if filter_mode == 1:
                            continue
                    else:
                        if filter_mode == 2:
                            continue
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                if file_size in file_dict:
                    file_dict[file_size].append(file_path)
                else:
                    file_dict[file_size] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个相同大小文件" % count)
    elif mode == "name":  # 默认查询同名文件
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        if filter_mode == 1:
                            continue
                    else:
                        if filter_mode == 2:
                            continue
                file_path = os.path.join(root, file_name)
                if file_name in file_dict:
                    file_dict[file_name].append(file_path)
                else:
                    file_dict[file_name] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个同名文件" % count)
    elif mode == "mtime":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        if filter_mode == 1:
                            continue
                    else:
                        if filter_mode == 2:
                            continue
                file_path = os.path.join(root, file_name)
                file_mtime = os.path.getmtime(file_path)
                if file_mtime in file_dict:
                    file_dict[file_mtime].append(file_path)
                else:
                    file_dict[file_mtime] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个修改时间相同文件" % count)
    elif mode == "name_size":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        if filter_mode == 1:
                            continue
                    else:
                        if filter_mode == 2:
                            continue
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                file_info = "%s_%s" % (file_name, file_size)
                if file_info in file_dict:
                    file_dict[file_info].append(file_path)
                else:
                    file_dict[file_info] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个同名且大小相同的文件" % count)
    elif mode == "name_mtime":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        if filter_mode == 1:
                            continue
                    else:
                        if filter_mode == 2:
                            continue
                file_path = os.path.join(root, file_name)
                file_mtime = os.path.getmtime(file_path)
                file_info = "%s_%s" % (file_name, file_mtime)
                if file_info in file_dict:
                    file_dict[file_info].append(file_path)
                else:
                    file_dict[file_info] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个同名且修改时间相同的文件" % count)
    elif mode == "size_mtime":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        if filter_mode == 1:
                            continue
                    else:
                        if filter_mode == 2:
                            continue
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                file_mtime = os.path.getmtime(file_path)
                file_info = "%s_%s" % (file_mtime, file_size)
                if file_info in file_dict:
                    file_dict[file_info].append(file_path)
                else:
                    file_dict[file_info] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个相同大小且修改时间相同的文件" % count)
    elif mode == "name_size_mtime":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                # 过滤
                if filter_flag:
                    # print("文件名：{}".format(os.path.splitext(file_name)))
                    # print("文件后缀名：{}, 输入过滤项：{}".format(os.path.splitext(file_name)[-1][1:].lower(), filter_exts))
                    if os.path.splitext(file_name)[-1][1:].lower() in filter_exts:
                        # print('在输入过滤项中！')
                        if filter_mode == 1:
                            continue
                    else:
                        # print('不在输入过滤项中！')
                        if filter_mode == 2:
                            continue
                # print('继续！')
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                file_mtime = os.path.getmtime(file_path)
                file_info = "%s_%s_%s" % (file_name, file_size, file_mtime)
                if file_info in file_dict:
                    file_dict[file_info].append(file_path)
                else:
                    file_dict[file_info] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个同名且大小相同且修改时间相同的文件" % count)

    return file_dict, count


def get_file_by_path(search_path):
    """
    用于根据路径遍历所有文件和目录
    :param search_path: 要遍历的路径
    :return:
            file_dict = {name1:[file1,file2], name2:[file1,file2]}  # 用于储存搜索匹配的文件路径
            dir_dict = {name1:[dir1,dir2], name2:[dir1,dir2]}  # 用于储存搜索匹配的文件夹路径
    """
    file_dict = {}  # 用于储存搜索匹配的文件路径
    dir_dict = {}  # 用于储存搜索匹配的文件夹路径
    for root, dirs, files in os.walk(search_path):
        for file_name in files:
            # 获取文件信息
            file_path = os.path.join(root, file_name)
            if file_name in file_dict:
                file_dict[file_name].append(file_path)
            else:
                file_dict[file_name] = list((file_path,))
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if dir_name in dir_dict:
                dir_dict[dir_name].append(dir_path)
            else:
                dir_dict[dir_name] = list((dir_path,))

    return file_dict, dir_dict


def search_file_by_size(search_path, search_str, search_mode=False):
    """
    用于根据文件大小搜索文件
    :param search_path: 要搜索的路径
    :param search_str:  要搜索的文件大小或者条件表达式
    :param search_mode: 搜索的模式
                        True  条件匹配
                        False 精确匹配
    :return: result 数据格式{"files": [], "dirs": [],}
    """
    file_dict = {}  # 用于储存文件信息,格式"{"file_path": size,...}"
    dir_dict = {}  # 用于储存目录信息,格式"{"dir_path":dir_size,...}"
    size_to_file = {}  # 用于储存相同大小的文件,格式"{"size": [file_path1,],...}"
    size_to_dir = {}  # 用于储存相同大小目录,格式"{"size": [dir_path1,],...}"
    result = {"files": [], "dirs": []}  # 用于储存搜索的结果，格式{"files": {size:[],}, "dirs": {size:[],},}
    # 遍历获取文件和目录大小
    for root, dirs, files in os.walk(search_path):
        for file_name in files:
            # 获取文件信息
            file_path = os.path.join(root, file_name)
            file_size = os.path.getsize(file_path)
            dir_path = os.path.dirname(file_path)
            file_dict[file_path] = file_size
            # 计算文件夹大小
            if dir_path == search_path:  # 防止将自身根目录算进去
                continue
            if dir_path in dir_dict:
                dir_dict[dir_path] += file_size
            else:
                dir_dict[dir_path] = file_size

    # 整理数据，将相同大小的文件和目录统计到一起
    for file_path in file_dict:
        file_size = file_dict[file_path]
        if file_size in size_to_file:
            size_to_file[file_size].append(file_path)
        else:
            size_to_file[file_size] = list((file_path,))
    for dir_path in dir_dict:
        dir_size = dir_dict[dir_path]
        if dir_size in size_to_dir:
            size_to_dir[dir_size].append(dir_path)
        else:
            size_to_dir[dir_size] = list((dir_path,))

    # 匹配文件大小
    if not search_mode:
        # 精确匹配
        search_str = search_str.strip()
        if re.match(r"\d+$", search_str):  # 正则匹配纯数字
            search_str = int(search_str)
            if search_str in size_to_file:
                result["files"] = size_to_file[search_str]
            if search_str in size_to_dir:
                result["dirs"] = size_to_dir[search_str]

    else:
        # 条件匹配
        if search_str.strip():  # 有输入
            # re_str = re_str.strip().replace('\\', "\\\\")  # 需要转义
            math_str = search_str.strip()
            print("math_str:%s" % math_str)
            search_obj = re.search(r"(gt|gte|lt|lte|eq|neq|between)\s?(\d+)\s?(and)?\s?(\d+)?$", math_str)
            search_size = int(search_obj.group(2))
            # print(search_size)
            # 匹配文件
            for item in size_to_file:
                if search_obj.group(1) == "gt":
                    if item > search_size:
                        result["files"].extend(size_to_file[item])
                elif search_obj.group(1) == "gte":
                    if item >= search_size:
                        result["files"].extend(size_to_file[item])
                elif search_obj.group(1) == "lt":
                    if item < search_size:
                        result["files"].extend(size_to_file[item])
                elif search_obj.group(1) == "lte":
                    if item <= search_size:
                        result["files"].extend(size_to_file[item])
                elif search_obj.group(1) == "eq":
                    if item == search_size:
                        result["files"] = size_to_file[item]
                elif search_obj.group(1) == "neq":
                    if item != search_size:
                        result["files"] = size_to_file[item]
                elif search_obj.group(1) == "between" and search_obj.group(3) == "and":
                    search_size_up = int(search_obj.group(4))
                    if item >= search_size:
                        if item <= search_size_up:
                            result["files"].extend(size_to_file[item])
            # 匹配目录
            for item in size_to_dir:
                if search_obj.group(1) == "gt":
                    if item > search_size:
                        result["dirs"].extend(size_to_dir[item])
                elif search_obj.group(1) == "gte":
                    if item >= search_size:
                        result["dirs"].extend(size_to_dir[item])
                elif search_obj.group(1) == "lt":
                    if item < search_size:
                        result["dirs"].extend(size_to_dir[item])
                elif search_obj.group(1) == "lte":
                    if item <= search_size:
                        result["dirs"].extend(size_to_dir[item])
                elif search_obj.group(1) == "eq":
                    if item == search_size:
                        result["dirs"] = size_to_dir[item]
                elif search_obj.group(1) == "between" and search_obj.group(3) == "and":
                    search_size_up = int(search_obj.group(4))
                    if item >= search_size:
                        if item <= search_size_up:
                            result["dirs"].extend(size_to_dir[item])
            # print(result)
            # show_result_by_size(result)
    return result


def get_times(search_size):
    """用于计算MB,KB,GB 大小"""

    search_obj = re.search(r"^(\d+\.?\d+)(MB|KB|GB)$", search_size)
    if search_obj:  # 正则匹配MB KB GB
        times = search_obj.group(2)  # 倍数
        if times == "KB":
            search_size = float(search_obj.group(1)) * 1024
        elif times == "MB":
            search_size = float(search_obj.group(1)) * 1024 * 1024
        elif times == "GB":
            search_size = float(search_obj.group(1)) * 1024 * 1024 * 1024
    return int(search_size)


def search_file_by_name(search_path, search_str, search_mode=False):
    """
    用于根据文件名搜索文件和目录，会默认同时搜索文件和目录，比较费时
    :param search_path: 要搜索的路径
    :param search_str:  要搜索的文件名或者正则表达式
    :param search_mode: 搜索的模式
                        True  正则匹配
                        False 精确匹配
    :return: result ,数据格式{"files":[file1,file2,],
                            "dirs":[dir1,dir2,]}

    """
    result = {"files": [], "dirs": []}  # 用于储存搜索的结果，格式{"files":[],"dirs":[]}
    if search_mode:
        # 正则匹配
        if search_str.strip():  # 有输入
            # search_str = search_str.strip().replace('\\', "\\\\")  # 需要转义
            search_str = search_str.strip()
            print("search_str:%s" % search_str)
            file_dict, dir_dict = get_file_by_path(search_path)  # 遍历路径获取文件信息和文件夹信息
            for item in file_dict:
                if re.search(search_str, item, flags=re.I):  # flags修饰，re.I 忽略大小写
                    result["files"].extend(file_dict[item])
            for item in dir_dict:
                if re.search(search_str, item, flags=re.I):
                    result["dirs"].extend(dir_dict[item])

    else:
        # 精确匹配
        search_str = search_str.strip()
        if search_str:
            file_dict, dir_dict = get_file_by_path(search_path)  # 遍历路径获取文件信息和文件夹信息
            if search_str in file_dict:
                result["files"] = file_dict[search_str]
            if search_str in dir_dict:
                result["dirs"] = dir_dict[search_str]

    return result


def deal_file(result, old_dir, deal_mode):
    """用于处理文件导出操作"""
    new_dir = Mytools.input_path("要导出的路径", create_flag=True)
    option = input("是否原样导出？【Y原样导出，N导出到单级目录并附带目录描述（默认导出到单级目录！）】").strip()
    rename_flag = True
    if option:
        if option.upper() == 'Y':
            rename_flag = False
    Mytools.deal_files(result, old_dir, new_dir, deal_mode=deal_mode, rename_flag=rename_flag)


