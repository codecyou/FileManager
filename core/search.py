#!/usr/bin/python3
"""用于搜索文件"""

from core import Mytools
import os
import re


def find_same(search_path, mode):
    """#用walk函数实现遍历目录下所有文件，
    根据mode搜索同名文件或者相同大小文件
    mode    "name" 同名
            "size" 相同大小
            "name_size"  同名且大小相同
            "size_mtime" 大小相同且修改时间相同
    """

    file_dict = {}  # 用于储存相同文件,格式"{"name"或者"size": [file_path1,file_path1,],...}"
    count = 0  # 用于记录相同文件的个数
    if mode == "size":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
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
                file_path = os.path.join(root, file_name)
                if file_name in file_dict:
                    file_dict[file_name].append(file_path)
                else:
                    file_dict[file_name] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个同名文件" % count)
    elif mode == "name_size":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
                file_path = os.path.join(root, file_name)
                file_size = os.path.getsize(file_path)
                file_info = "%s_%s" % (file_name, file_size)
                if file_info in file_dict:
                    file_dict[file_info].append(file_path)
                else:
                    file_dict[file_info] = list((file_path,))

        file_dict, count = Mytools.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
        print("共发现%s个同名且大小相同的文件" % count)
    elif mode == "size_mtime":
        for root, dirs, files in os.walk(search_path):
            for file_name in files:
                # 获取文件信息
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


def show_result_by_name(result):
    """用于显示搜索结果"""
    if len(result["files"]) or len(result["dirs"]):
        print("搜索结果：")
        if len(result["files"]):
            print("文件:")
            for item in result["files"]:
                print(item)
        if len(result["dirs"]):
            print("文件夹:")
            for item in result["dirs"]:
                print(item)
    else:
        print("未搜索到文件！")


def show_result_by_size(result):
    """用于显示根据文件大小搜索的结果"""
    if len(result):
        print("搜索结果：")
        for item in result:
            print(item, result[item])
    else:
        print("未搜索到文件！")


def search_file_by_size(search_path, search_str, search_mode=False):
    """
    用于根据文件大小搜索文件
    :param search_path: 要搜索的路径
    :param search_str:  要搜索的文件大小或者条件表达式
    :param search_mode: 搜索的模式
                        True  条件匹配
                        False 精确匹配
    :return: result 数据格式{"size": [file_path1,file_path1,],...}
    """
    file_dict = {}  # 用于储存相同文件,格式"{"size": [file_path1,file_path1,],...}"
    result = {}  # 用来记录结果
    # search_path = r"C:\Users\pro\Desktop\Resource\photo"
    for root, dirs, files in os.walk(search_path):
        for file_name in files:
            # 获取文件信息
            file_path = os.path.join(root, file_name)
            file_size = os.path.getsize(file_path)
            if file_size in file_dict:
                file_dict[file_size].append(file_path)
            else:
                file_dict[file_size] = list((file_path,))

    if not search_mode:
        # 精确匹配
        search_str = search_str.strip()
        if re.match(r"\d+$", search_str):  # 正则匹配纯数字
            search_str = int(search_str)
            if search_str in file_dict:
                result[search_str] = file_dict[search_str]
        # print(result)
        # show_result_by_size(result)
    else:
        # 条件匹配
        if search_str.strip():  # 有输入
            # re_str = re_str.strip().replace('\\', "\\\\")  # 需要转义
            math_str = search_str.strip()
            print("math_str:%s" % math_str)
            search_obj = re.search(r"(gt|gte|lt|lte|between)\s?(\d+)\s?(and)?\s?(\d+)?$", math_str)
            search_size = int(search_obj.group(2))
            # print(search_size)
            for item in file_dict:
                if search_obj.group(1) == "gt":
                    if item > search_size:
                        result[item] = file_dict[item]
                elif search_obj.group(1) == "gte":
                    if item >= search_size:
                        result[item] = file_dict[item]
                elif search_obj.group(1) == "lt":
                    if item < search_size:
                        result[item] = file_dict[item]
                elif search_obj.group(1) == "lte":
                    if item <= search_size:
                        result[item] = file_dict[item]
                elif search_obj.group(1) == "between" and search_obj.group(3) == "and":
                    search_size_up = int(search_obj.group(4))
                    if item >= search_size:
                        if item <= search_size_up:
                            result[item] = file_dict[item]
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
    用于根据文件名搜索文件
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


def run():
    """用于搜索文件"""
    menu = """请选择搜索模式：\n\t1.根据文件名搜索\n\t2.根据文件大小搜索\n\tQ.返回上一层"""
    Mytools.show_menu(menu)
    option = input(">>> ")
    option = option.strip()
    if option in ["1", "文件名"]:
        search_path = Mytools.input_path("要搜索的路径范围")
        search_mode = input("请选择搜索模式：1.精确匹配(默认) 2.正则匹配\n>>> ")
        search_mode = search_mode.strip()  # 用来记录搜索模式
        if search_mode in ["2", "正则匹配", "正则"]:
            search_mode = True  # 用来记录搜索模式，True 表示开启正则匹配
            search_str = input("请输入正则语句：")
        else:
            search_mode = False
            search_str = input("请输入要搜索的文件名：")
        result = search_file_by_name(search_path, search_str, search_mode)
        if len(result["files"]) + len(result["dirs"]):
            deal_result(result, search_path, show_result_by_name)
        else:
            print("未找到匹配 %s的文件和目录！" % search_str)

    elif option in ["2", "文件大小"]:
        search_path = Mytools.input_path("要搜索的路径范围")
        search_mode = input("请选择搜索模式：1.精确匹配(默认) 2.条件匹配\n>>> ")
        if search_mode in ["2", "条件匹配", "条件"]:
            search_mode = True  # 用来记录搜索模式，True 表示开启条件匹配
            menu = """请输入条件语句：
            gt 大于 
            gte 大于等于 
            lt 小于 
            lte 小于等于 
            between and 在中间
            例如： gt 2816665 或者 between 1024000 and 2048000
            """
            Mytools.show_menu(menu)
            search_str = input(">>> ")
        else:
            search_mode = False
            search_str = input("请输入要搜索的文件大小：")
        result = search_file_by_size(search_path, search_str, search_mode)
        if len(result):
            deal_result(result, search_path, show_result_by_size)
        else:
            print("未找到匹配 %s的文件和目录！" % search_str)


def deal_result(result, search_path, show_func):
    """用于查找到文件后的操作
    :param result: 查询结果集
    :param search_path: 查询的目录路径
    :param show_func: 显示结果集的函数名
    :return:
    """
    while True:
        menu = """请选择操作：\n\t1.查看详情\n\t2.拷贝\n\t3.剪切\n\tQ.返回上一层"""
        Mytools.show_menu(menu)
        option = input(">>> ")
        option = option.strip()
        if option in ['1', '查看详情']:
            show_func(result)   # 根据传入的方法指向运行结果显示函数
        elif option in ['2', '拷贝', 'copy']:
            deal_file(result, search_path, 'copy')
            break
        elif option in ['3', '剪切', 'move']:
            deal_file(result, search_path, 'move')
            break
        elif option in ["Q", "q", "返回上一层"]:
            return


def deal_file(result, old_dir, deal_mode):
    """用于处理文件导出操作"""
    new_dir = Mytools.input_path("要导出的路径", create_flag=True)
    option = input("是否原样导出？【Y原样导出，N导出到单级目录并附带目录描述（默认导出到单级目录！）】").strip()
    rename_flag = True
    if option:
        if option.upper() == 'Y':
            rename_flag = False
    Mytools.deal_files(result, old_dir, new_dir, deal_mode=deal_mode, rename_flag=rename_flag)


def main():
    # result = search_file_by_name(r'E:\超级正能量', r'[^\.mp4]$', True)
    # Mytools.move_or_copy_file(result["files"], r'E:\超级正能量', r'C:\Users\pro\Desktop\name', 'copy')
    run()


if __name__ == '__main__':
    main()
