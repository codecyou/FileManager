#!/usr/bin/python3
"""
单进程实现， 新增copy_file和update_file函数
"""
from core import logger
from core import Mytools
import os
import time
import shutil


def get_file_dir(dir_path):
    """获取路径下所有文件和文件夹
    """
    # 用walk函数实现遍历目录下所有文件

    file_list = []  # 用于储存所有文件路径
    dir_list = []  # 用于储存所有文件夹路径
    # 用于储存文件信息，记录数据格式为{file_info:[path1,path2,],}
    for root, dirs, files in os.walk(dir_path):
        for file_name in files:
            # 获取文件信息
            file_path = os.path.join(root, file_name)
            file_list.append(file_path)
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            dir_list.append(dir_path)
    return file_list, dir_list  # 返回遍历完成的文件信息


def filter_dir(dir_list):
    """用于过滤目录列表，找到列表中的父目录 和空目录 并返回，
        找到列表中的父目录  ['a/b/c', 'a/b', 'a']  过滤得到顶级父目录
        用于过滤目录列表，找到空目录并返回
    """
    dir_dict = {"empty_dir": [], "parent_dir": []}
    for item in dir_list:
        parent_item = os.path.dirname(item)
        if not os.listdir(item):  # 目录为空
            dir_dict["empty_dir"].append(item)
        if parent_item in dir_list:  # 找出顶级父目录
            continue
        else:
            dir_dict["parent_dir"].append(item)

    return dir_dict


def find_difference(src_path, dst_path):
    """
    用于比对两个目录下文件，result中记录的是文件或文件夹的绝对路径
    :param src_path: 源路径
    :param dst_path: 目标路径(备份端)
    :return: result {"file_only_in_src": [], "file_only_in_dst": [], "dir_only_in_src": [],
                    "dir_only_in_dst": [], "diff_files": [],"common_funny": [], "move_dict":{拷贝路径：样本路径}}
    """
    src_file_list, src_dir_list = get_file_dir(src_path)  # 遍历获取文件和文件夹
    dst_file_list, dst_dir_list = get_file_dir(dst_path)
    src_file_only_info_dict = Mytools.get_files_info(src_path)  # 遍历获取文件信息,仅在src的文件信息
    dst_file_only_info_dict = Mytools.get_files_info(dst_path)

    file_only_in_src = []
    file_only_in_dst = dst_file_list[:]  # 引用类型是址传递必须拷贝数据
    move_dict = {}  # 用于记录移动或者复制文件，{拷贝路径：样本路径}
    # 格式{new_dst_file1:old_dst_file1, new_dst_file2:old_dst_file1, }
    diff_files = []  # 用于记录文件内容发生变化文件
    result = {}  # 用于记录结果
    common_funny = []  # 用于记录同名但类型不同的文件，即 与文件同名的文件夹
    dir_only_in_src = []

    # 比对文件
    # 1.找出相同文件，内容有更新的文件，以及同级目录文件夹和文件出现同名导致无法比较的情况
    for item in src_file_list:
        dst_item = item.replace(src_path, dst_path)
        if dst_item in dst_file_list:  # 判断文件目录结构是否一致
            if src_file_only_info_dict[item] == dst_file_only_info_dict[dst_item]:
                file_only_in_dst.remove(dst_item)
            else:  # 同名但信息不一致，文件内容有更新！
                diff_files.append(item)
                file_only_in_dst.remove(dst_item)
            # 将同名文件和相同文件从仅在src和dst的文件信息dict删除，方便后面比对仅目录变更的文件
            src_file_only_info_dict.pop(item)
            dst_file_only_info_dict.pop(dst_item)
        elif dst_item in dst_dir_list:  # 判断相同层次下源目录文件是否和备份端目录重名
            common_funny.append(item)
            dst_dir_list.remove(dst_item)
        else:
            # 只在源目录存在的文件
            file_only_in_src.append(item)

    # 2.在file_only_in_src 和 file_only_in_dst 的文件中找出仅目录变更但文件内容一致的文件
    # 遍历获取仅目录变更文件
    dst_file_only_info_list = []  # 用于记录备份目录所有文件的信息
    dst_file_only_path_list = []  # 用于记录备份目录所有文件的路径
    for item, info in dst_file_only_info_dict.items():
        dst_file_only_path_list.append(item)
        dst_file_only_info_list.append(info)

    for item in file_only_in_src:
        item_info = src_file_only_info_dict[item]
        if item_info in dst_file_only_info_list:
            dst_item = item.replace(src_path, dst_path)  # 变更目录后的文件名
            move_dict[dst_item] = dst_file_only_path_list[dst_file_only_info_list.index(item_info)]
            file_only_in_src.remove(item)

    # 比对文件夹
    for item in src_dir_list:
        dst_item = item.replace(src_path, dst_path)
        if dst_item in dst_dir_list:  # 判断是否是同名目录
            dst_dir_list.remove(dst_item)
        elif dst_item in dst_file_list:  # 判断相同层次下源目录下目录是否和备份端文件重名
            common_funny.append(item)
            file_only_in_dst.remove(dst_item)
            # 注意！当common_funny在源目录是目录而备份端是文件时一定注意如果该同名不同类的文件夹下有文件千万不能用备份端自拷贝，
            # 不然拷贝文件的时候会因为备份端的文件类型文件还没删除，无法创建其同名文件夹而而出错
            # 解决方法就是将对该common_funny目录进行的自拷贝操作换做新增操作，（其实受影响的只是不能写，读是没问题的）
            # 然后把新增文件的操作放在自拷贝和更新操作之后尤其是更新无法比对文件操作之后
            if os.listdir(item):  # 判断该common_funny文件夹是否为空
                for root, dirs, files in os.walk(item):  # 遍历将自拷贝换成新建
                    for item in files:
                        temp = os.path.join(root, item)
                        dst_temp = temp.replace(src_path, dst_path)
                        if dst_temp in move_dict:
                            move_dict.pop(dst_temp)
                            file_only_in_src.append(temp)
        else:
            dir_only_in_src.append(item)

    dir_only_in_dst = dst_dir_list

    count = {
        "only_in_src_count": len(file_only_in_src) + len(dir_only_in_src),
        "only_in_dst_count": len(file_only_in_dst) + len(dir_only_in_dst),
        "update_count": len(diff_files),
        "move_count": len(move_dict),
        "common_funny_count": len(common_funny)}

    result["file_only_in_src"] = file_only_in_src
    result["file_only_in_dst"] = file_only_in_dst
    result["dir_only_in_src"] = dir_only_in_src
    result["dir_only_in_dst"] = dir_only_in_dst
    result["move_dict"] = move_dict
    result["diff_files"] = diff_files
    result["common_funny"] = common_funny
    result["count"] = count
    return result


def show_difference(src_path, dst_path, result):
    """
    用于显示两个目录下文件所有差异
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param result: 差异文件结果集，dict，保存着两个目录下文件差异信息
    :return:
    """
    print("%s    ---->    %s" % (src_path, dst_path))  # 打印输出源路径和目标路径
    file_src_count = len(result["file_only_in_src"])
    dir_src_count = len(result["dir_only_in_src"])
    file_dst_count = len(result["file_only_in_dst"])
    dir_dst_count = len(result["dir_only_in_dst"])
    update_count = len(result["diff_files"])
    common_funny_count = len(result["common_funny"])
    move_count = len(result["move_dict"])

    if file_src_count + dir_src_count:
        print("新增(文件%s个,文件夹%s个)：" % (file_src_count, dir_src_count))
        if file_src_count:
            print("->文件：")
            for item in result["file_only_in_src"]:
                print(item)
        if dir_src_count:
            print("->文件夹：")
            for item in result["dir_only_in_src"]:
                print(item)
    if file_dst_count + dir_dst_count:
        print("删除(文件%s个,文件夹%s个)：" % (file_dst_count, dir_dst_count))
        if file_dst_count:
            print("->文件：")
            for item in result["file_only_in_dst"]:
                print(item)
        if dir_dst_count:
            print("->文件夹：")
            for item in result["dir_only_in_dst"]:
                print(item)
    if update_count + common_funny_count:
        print("更新：")
        if update_count:
            for item in result["diff_files"]:
                print(item)
        if common_funny_count:
            for item in result["common_funny"]:
                print(item)
    if move_count:
        print("备份端自拷贝：")
        for dst_item, item in result["move_dict"].items():
            print("%s  -->  %s" % (item, dst_item))


def deal_find_diff(src_path, dst_path):
    """用于处理文件同步备份和恢复操作"""
    src_path = Mytools.check_path(src_path)
    dst_path = Mytools.check_path(dst_path, create_flag=True)
    result_dict = find_difference(src_path, dst_path)

    # print(result_dict)
    option_menu = """请输入要进行的操作：
    1.同步备份(备份目录内容将与源目录完全一致)
    2.增量备份(只同步源目录中新增和修改的内容到备份目录)
    3.查看详情
    Q.返回上级菜单"""
    while True:
        Mytools.show_menu(option_menu)
        option = input(">>> ")
        if option in ["1", "同步备份"]:
            deal_file(src_path, dst_path, result_dict, "backup_full")
            break
        elif option in ["2", "增量备份"]:
            deal_file(src_path, dst_path, result_dict, "backup_update")
            break
        elif option in ["3", "查看详情"]:
            show_difference(src_path, dst_path, result_dict)
        elif option in ["q", "Q", "退出", "返回上级菜单"]:
            print("取消本次操作，返回上级菜单！")
            return
        else:
            print("您的输入有误！请重新输入！")


def deal_file(window, src_path, dst_path, result, deal_option):
    """
    用于进行实际操作文件的函数
    :param window: GUI窗口对象
    :param result: 差异文件结果集，dict，保存着两个目录下文件差异信息, 绝对路径
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param deal_option: 操作模式
            backup_full   全备份
            backup_update 增量备份
            # 先新增，再移动变更目录，再更新文件，再更新无法比对，再删除 顺序不能乱，不然有可能出现数据出错
    """
    # print(result)
    start_time = time.time()  # 开始时间
    print(deal_option)
    safe_del_dirname = None  # 用于记录safe_del目录
    add_file = "file_only_in_src"
    add_dir = "dir_only_in_src"
    del_file = "file_only_in_dst"
    del_dir = "dir_only_in_dst"
    # only_in_src_count = len(result["file_only_in_src"]) + len(result["dir_only_in_src"])
    only_in_dst_count = len(result["file_only_in_dst"]) + len(result["dir_only_in_dst"])
    update_count = len(result["diff_files"]) + len(result["common_funny"])  # 会有文件内容变化
    if "backup_full" == deal_option:
        if only_in_dst_count or update_count:
            safe_del_dirname = Mytools.makedir4safe_del(dst_path)
    if "backup_update" == deal_option:
        if update_count:
            safe_del_dirname = Mytools.makedir4safe_del(dst_path)

    print("正在同步文件...")

    # 先备份端自拷贝，再更新文件，再更新无法比对，再新增，再删除 顺序不能乱，不然有可能出现数据出错
    # 执行目录变更文件移动即备份端自拷贝
    move_dict = result["move_dict"]
    if move_dict:
        window.exeStateLabel["text"] = "执行目录变更中(备份端自拷贝)..."
        for item in move_dict:
            new_dst = item
            new_src = move_dict[item]
            Mytools.copy_file(new_src, new_dst)
    # 执行文件内容变更的文件更新
    if len(result["diff_files"]) or len(result["common_funny"]):
        window.exeStateLabel["text"] = "执行文件更新..."
    if len(result["diff_files"]):
        for item in result["diff_files"]:
            new_src = item
            new_dst = item.replace(src_path, dst_path)
            safe_del_file = item.replace(src_path, safe_del_dirname)
            Mytools.update_file(new_src, new_dst, safe_del_file)
    # 执行文件名相同但无法比对（即文件名相同但一个是文件一个是文件夹）的更新
    if len(result["common_funny"]):
        for item in result["common_funny"]:
            new_src = item
            new_dst = item.replace(src_path, dst_path)
            safe_del_file = item.replace(src_path, safe_del_dirname)
            Mytools.update_file(new_src, new_dst, safe_del_file)

    # 执行新增
    if len(result[add_file]) or len(result[add_dir]):
        window.exeStateLabel["text"] = "执行文件新增..."
    if len(result[add_file]):
        for item in result[add_file]:
            new_src = item
            new_dst = item.replace(src_path, dst_path)
            Mytools.copy_file(new_src, new_dst)
    if len(result[add_dir]):
        dir_dict = filter_dir(result[del_dir])  # 过滤获取顶级父目录和空目录
        for item in dir_dict["empty_dir"]:
            new_src = item
            new_dst = item.replace(src_path, dst_path)
            Mytools.copy_file(new_src, new_dst)

    # 执行删除
    if "backup_update" != deal_option:  # 增量备份不执行删除操作
        if len(result[del_file]) or len(result[del_dir]):  # 有要删除的文件
            window.exeStateLabel["text"] = "执行文件删除..."
        if len(result[del_file]):
            for item in result[del_file]:
                safe_del_file = item.replace(dst_path, safe_del_dirname)
                # 为了避免重复删除导致报错，即如果common_funny目录下有文件，原来更新时候删除一次后来删除的时候又删除一次就会出错
                if not os.path.exists(safe_del_file):
                    Mytools.move_file(item, safe_del_file)
        if len(result[del_dir]):
            dir_dict = filter_dir(result[del_dir])  # 过滤获取顶级父目录和空目录
            for item in dir_dict["empty_dir"]:
                safe_del_file = item.replace(dst_path, safe_del_dirname)
                if not os.path.exists(safe_del_file):  # 空文件夹未被拷贝到safe_del目录下
                    Mytools.move_file(item, safe_del_file)
            for item in dir_dict["parent_dir"]:  # 删除顶级父目录
                if os.path.exists(item):
                    shutil.rmtree(item)

    msg = logger.backup_logger(result, src_path, dst_path, safe_del_dirname, deal_option)
    syn_time = time.time() - start_time
    print("同步用时：%ss" % syn_time)  # 打印拷贝用时
    window.scr.insert('end', '\n本次同步用时：%ss\n' % syn_time)
    return msg

