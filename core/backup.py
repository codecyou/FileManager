#! /usr/bin/python3
"""
单进程实现，源目录和备份目录两个目录下所有文件差异比对，并提供备份和还原函数
日志记录函数为：logger.backup_logger
差异结果集：
result = {"only_in_src": [], "only_in_dst": [], "diff_files": [],"common_funny": []}
仅保存目录下的文件名，如果多级路径则会保存带父目录路径的文件名 即 "only_in_src": [a.jpg,b/c.jpg]

"""
from core import logger
from core import Mytools
import filecmp
import os
import time


def do_compare(src, dst, result, child_flag=False, parent_dir=''):
    """
    用于比对两个目录下文件，result中记录的是文件或文件夹的相对路径
    :param src: 源路径
    :param dst: 目标路径(备份端)
    :param result: 用于接收结果集，方便递归记录
    :param child_flag: 用于标记是否是递归调用
    :param parent_dir: 用于记录父目录
    :return: result {"only_in_src": [], "only_in_dst": [], "diff_files": [],"common_funny": []}
    """

    dir_cmp = filecmp.dircmp(src, dst)  # 获取dircmp对象
    # dir_cmp.report_partial_closure()  # 格式化打印到控制面板
    diff_files = dir_cmp.diff_files  # 文件内容有变化
    only_in_src = dir_cmp.left_only  # 新增
    only_in_dst = dir_cmp.right_only  # 删除
    common_dirs = dir_cmp.common_dirs  # 同名文件夹
    # funny_files = dir_cmp.funny_files
    # common = dir_cmp.common
    common_funny = dir_cmp.common_funny  # 用来记录同名但是不能比较的文件，比如a文件夹下1.txt文件 但是b文件夹下也有一个名为1.txt的文件夹

    if child_flag:  # child_flag 用于标记是否是递归调用,如果是递归调用就要在路径加上父目录
        parent_dir_path = os.path.join(parent_dir, os.path.basename(src))
    else:
        parent_dir_path = ''  # 如果不是递归调用父目录置为空字符串，不可置为None否则会报错

    if only_in_src:
        [result["only_in_src"].append(os.path.join(parent_dir_path, item)) for item in only_in_src]

    if only_in_dst:
        [result["only_in_dst"].append(os.path.join(parent_dir_path, item)) for item in only_in_dst]

    if common_dirs:
        for item in common_dirs:
            new_src = os.path.join(src, item)
            new_dst = os.path.join(dst, item)
            do_compare(new_src, new_dst, result, child_flag=True, parent_dir=parent_dir_path)

    if diff_files:
        [result["diff_files"].append(os.path.join(parent_dir_path, item)) for item in diff_files]

    if common_funny:
        [result["common_funny"].append(os.path.join(parent_dir_path, item)) for item in common_funny]

    # print(str(result))
    # print(result)
    return result


def show_difference(src_path, dst_path, result_dict):
    """
    用于显示两个目录下文件所有差异
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param result_dict 差异文件结果集，dict，保存着两个目录下文件差异信息
    :return:
    """
    print("%s    ---->    %s" % (src_path, dst_path))  # 打印输出源路径和目标路径
    result = Mytools.filter_4_dict(src_path, dst_path, result_dict)  # 调用过滤函数得到文件列表和目录列表
    file_only_in_src_count = len(result["file_only_in_src"])
    dir_only_in_src_count = len(result["dir_only_in_src"])
    file_only_in_dst_count = len(result["file_only_in_dst"])
    dir_only_in_dst_count = len(result["dir_only_in_dst"])
    update_count = len(result["diff_files"]) + len(result["common_funny"])
    if file_only_in_src_count or dir_only_in_src_count:
        print("新增(文件%s个,文件夹%s个)：" % (file_only_in_src_count, dir_only_in_src_count))
        if len(result["file_only_in_src"]):
            print("->文件：")
            for item in result["file_only_in_src"]:
                print(item)
        if len(result["dir_only_in_src"]):
            print("->文件夹：")
            for item in result["dir_only_in_src"]:
                print(item)
    if file_only_in_dst_count or dir_only_in_dst_count:
        print("删除(文件%s个,文件夹%s个)：" % (file_only_in_dst_count, dir_only_in_dst_count))
        if file_only_in_dst_count:
            print("->文件：")
            for item in result["file_only_in_dst"]:
                print(item)
        if dir_only_in_dst_count:
            print("->文件夹：")
            for item in result["dir_only_in_dst"]:
                print(item)
    if update_count:
        print("更新(项目%s个)：" % update_count)
        for item in result["diff_files"]:
            print(item)
        for item in result["common_funny"]:
            # print("  %s" % os.path.join(src_path, item))
            print(item)


def deal_backup():
    """用于处理文件同步备份和恢复操作"""
    src_path = Mytools.input_path("源目录路径")
    dst_path = Mytools.input_path("备份端路径", create_flag=True)
    result_dict = {"only_in_src": [], "only_in_dst": [], "diff_files": [], "common_funny": []}  # 用于存储两个目录比较结果
    # {"only_in_src": [new_src,], "ony_in_dst": [new_dst,], "diff_files": [new_src,], "common_funny": [new_src,]}
    do_compare(src_path, dst_path, result_dict)  # 调用比对函数
    only_in_src_count = len(result_dict["only_in_src"])
    only_in_dst_count = len(result_dict["only_in_dst"])
    diff_files_count = len(result_dict["diff_files"])
    common_funny_count = len(result_dict["common_funny"])
    print("\n比对结果：")

    if only_in_src_count == 0 and only_in_dst_count == 0 and diff_files_count == 0 and common_funny_count == 0:
        print("目录内容一致，未有变化，无需同步！")
        return
    print("%s    ---->    %s" % (src_path, dst_path))  # 打印输出源路径和目标路径
    print("新增%s个项目,删除%s个项目,更新%s个项目,无法比对项目%s个" %
          (only_in_src_count, only_in_dst_count, diff_files_count, common_funny_count))
    if common_funny_count:
        print("同名但类型不同，无法比对项目如下：")
        for item in result_dict["common_funny"]:
            # 打印输出同名但类型不同的项目：
            print("\t%s    <---->    %s" % (os.path.join(src_path, item), os.path.join(dst_path, item)))

    option_menu = """请输入要进行的操作：
    1.同步备份(备份目录内容将与源目录完全一致)
    2.同步还原(源目录内容将与备份目录完全一致)
    3.增量备份(只同步源目录中新增和修改的内容到备份目录)
    4.查看详情
    Q.返回上级菜单"""
    while True:
        Mytools.show_menu(option_menu)
        option = input(">>> ")
        if option in ["1", "同步备份"]:
            deal_file(src_path, dst_path, result_dict, "backup_full")
            break
        elif option in ["2", "同步还原"]:
            deal_file(src_path, dst_path, result_dict, "recovery")
            break
        elif option in ["3", "增量备份"]:
            deal_file(src_path, dst_path, result_dict, "backup_update")
            break
        elif option in ["4", "查看详情"]:
            show_difference(src_path, dst_path, result_dict)
        elif option in ["q", "Q", "退出", "返回上级菜单"]:
            print("取消本次操作，返回上级菜单！")
            return
        else:
            print("您的输入有误！")
            return


def deal_file(window, src_path, dst_path, result, deal_option):
    """用于进行文件备份或者同步还原操作文件的函数
    :param window: GUI窗口对象
    :param result: 差异文件结果集，dict，保存着两个目录下文件差异信息
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param deal_option: 操作模式
            backup_full   全备份
            backup_update 增量备份
            recovery      备份还原
    """
    start_time = time.time()  # 记录同步操作开始时间
    print(deal_option)
    safe_del_dirname = None  # 用于记录safe_del目录
    add_element = "only_in_src"
    del_element = "only_in_dst"
    if "backup_full" == deal_option:
        if len(result["only_in_dst"]) or len(result["diff_files"]) or len(result["common_funny"]):
            safe_del_dirname = Mytools.makedir4safe_del(dst_path)
    if "backup_update" == deal_option:
        if len(result["diff_files"]) or len(result["common_funny"]):
            safe_del_dirname = Mytools.makedir4safe_del(dst_path)
    if "recovery" == deal_option:
        if len(result["only_in_src"]) or len(result["diff_files"]) or len(result["common_funny"]):
            safe_del_dirname = Mytools.makedir4safe_del(src_path)
        src_path, dst_path = dst_path, src_path
        add_element, del_element = del_element, add_element
    # 执行新增
    if len(result[add_element]):
        window.exeStateLabel["text"] = "执行文件新增..."
    for item in result[add_element]:
        new_src = os.path.join(src_path, item)
        new_dst = os.path.join(dst_path, item)
        Mytools.copy_file(new_src, new_dst)
    # 执行删除
    if "backup_update" != deal_option:  # 增量备份不执行删除
        if len(result[del_element]):
            window.exeStateLabel["text"] = "执行文件删除..."
        for item in result[del_element]:
            new_dst = os.path.join(dst_path, item)
            safe_del_file = os.path.join(safe_del_dirname, item)
            Mytools.move_file(new_dst, safe_del_file)
    # 执行文件内容变更的文件更新
    if len(result["diff_files"]) or len(result["common_funny"]):
        window.exeStateLabel["text"] = "执行文件更新..."
    for item in result["diff_files"]:
        print(item, safe_del_dirname)
        new_src = os.path.join(src_path, item)
        new_dst = os.path.join(dst_path, item)
        safe_del_file = os.path.join(safe_del_dirname, item)
        Mytools.update_file(new_src, new_dst, safe_del_file)
    # 执行文件名相同但无法比对（即文件名相同但一个是文件一个是文件夹）的更新
    for item in result["common_funny"]:
        new_src = os.path.join(src_path, item)
        new_dst = os.path.join(dst_path, item)
        safe_del_file = os.path.join(safe_del_dirname, item)
        Mytools.update_file(new_src, new_dst, safe_del_file)

    result = Mytools.filter_4_dict(src_path, dst_path, result)  # 调用过滤函数得到文件列表和目录列表
    msg = logger.backup_logger(result, src_path, dst_path, safe_del_dirname, deal_option)
    syn_time = time.time() - start_time
    print("同步用时：%ss" % syn_time)  # 打印拷贝用时
    window.scr.insert('end', '\n本次同步用时：%ss\n' % syn_time)
    return msg


def main():
    while True:
        try:
            deal_backup()
        except Exception as e:
            logger.error_logger(e)


if __name__ == '__main__':
    main()
