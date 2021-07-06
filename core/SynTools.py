from core import logger
from core import Mytools
from conf import settings
import filecmp
import os
import time
import shutil


def do_compare(src_dir, dst_dir, result, child_flag=False, parent_dir=''):
    """
    适配基于filecmp模块的文件同步功能
    用于比对两个目录下文件，result中记录的是文件或文件夹的相对路径
    :param src_dir: 源路径
    :param dst_dir: 目标路径(备份端)
    :param result: 用于接收结果集，方便递归记录
    :param child_flag: 用于标记是否是递归调用
    :param parent_dir: 用于记录父目录
    :return: result
    数据格式：{"only_in_src": [],
            "only_in_dst": [],
            "diff_files": [],
            "common_funny": []}
    仅保存目录下的文件名，如果多级路径则会保存带父目录路径的文件名 即 "only_in_src": [a.jpg,b/c.jpg]
    """

    dir_cmp = filecmp.dircmp(src_dir, dst_dir)  # 获取dircmp对象
    diff_files = dir_cmp.diff_files  # 文件内容有变化
    only_in_src = dir_cmp.left_only  # 新增
    only_in_dst = dir_cmp.right_only  # 删除
    common_dirs = dir_cmp.common_dirs  # 同名文件夹
    common_funny = dir_cmp.common_funny  # 用来记录同名但是不能比较的文件，比如a文件夹下1.txt文件 但是b文件夹下也有一个名为1.txt的文件夹

    if child_flag:  # child_flag 用于标记是否是递归调用,如果是递归调用就要在路径加上父目录
        parent_dir_path = os.path.join(parent_dir, os.path.basename(src_dir))
    else:
        parent_dir_path = ''  # 如果不是递归调用父目录置为空字符串，不可置为None否则会报错

    if only_in_src:
        [result["only_in_src"].append(os.path.join(parent_dir_path, item)) for item in only_in_src]

    if only_in_dst:
        [result["only_in_dst"].append(os.path.join(parent_dir_path, item)) for item in only_in_dst]

    if common_dirs:
        for item in common_dirs:
            new_src = os.path.join(src_dir, item)
            new_dst = os.path.join(dst_dir, item)
            do_compare(new_src, new_dst, result, child_flag=True, parent_dir=parent_dir_path)

    if diff_files:
        [result["diff_files"].append(os.path.join(parent_dir_path, item)) for item in diff_files]

    if common_funny:
        [result["common_funny"].append(os.path.join(parent_dir_path, item)) for item in common_funny]

    return result


def deal_file(window, src_path, dst_path, result, deal_option):
    """
    适配基于filecmp模块的文件同步功能
    用于进行文件备份或者同步还原操作文件的函数
    :param window: GUI窗口对象
    :param result: 差异文件结果集，dict，保存着两个目录下文件差异信息
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param deal_option: 操作模式
            backup_full   全备份
            backup_update 增量备份, 新增和更新
            recovery      备份还原
            only_add   仅新增
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
    if deal_option not in ["backup_update", "only_add"]:  # 增量备份不执行删除
        if len(result[del_element]):
            window.exeStateLabel["text"] = "执行文件删除..."
        for item in result[del_element]:
            new_dst = os.path.join(dst_path, item)
            safe_del_file = os.path.join(safe_del_dirname, item)
            Mytools.move_file(new_dst, safe_del_file)
    # 执行文件内容变更的文件更新
    if "only_add" != deal_option:  # 仅新增 不执行文件更新
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
    window.scr.insert('end', '\n\n\n\n{}\n本次同步用时：{}s\n'.format(msg, syn_time))
    return msg


def get_file_dir(dir_path):
    """
    适配自己实现的Mybackup方式
    获取路径下所有文件和文件夹
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
    """
    适配自己实现的Mybackup方式
    用于过滤目录列表，找到列表中的父目录 和空目录 并返回，
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


def find_difference2(src_path, dst_path):
    """
    适配自己实现的Mybackup方式
    用于比对两个目录下文件，result中记录的是文件或文件夹的绝对路径
    :param src_path: 源路径
    :param dst_path: 目标路径(备份端)
    :return: result
            数据格式：
            {"file_only_in_src": [],
            "file_only_in_dst": [],
            "dir_only_in_src": [],
            "dir_only_in_dst": [],
            "diff_files": [],
            "common_funny": [],
            "move_dict":{拷贝路径：样本路径}
            "count": {"only_in_src_count": len(result["file_only_in_src"]) + len(result["dir_only_in_src"]),
            "only_in_dst_count": len(result["file_only_in_dst"]) + len(result["dir_only_in_dst"]),
            "update_count": len(result["diff_files"]),
            "move_count": len(result["move_dict"]),
            "common_funny_count": len(result["common_funny"])}}
            }
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
    src_need_del = []  # 记录已经匹配为备份端目录变更的文件
    for item in file_only_in_src:
        item_info = src_file_only_info_dict[item]
        if item_info in dst_file_only_info_list:
            dst_item = item.replace(src_path, dst_path)  # 变更目录后的文件名
            dst_old_item = dst_file_only_path_list[dst_file_only_info_list.index(item_info)]  # 备份端要进行目录变更前的路径
            move_dict[dst_item] = dst_old_item
            src_need_del.append(item)
            dst_file_only_path_list.remove(dst_old_item)  # 避免出现一对多的情况
            dst_file_only_info_list.remove(item_info)  # 避免出现一对多的情况
            file_only_in_dst.remove(dst_old_item)  # 防止将已经归到备份端目录变更的项目重复记录到仅存在于备份端列表中
    # 从file_only_in_src删除已经匹配为备份端目录变更的文件
    for item in src_need_del:
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


def deal_file2(window, src_path, dst_path, result, deal_option):
    """
    适配自己实现的Mybackup方式
    用于进行实际操作文件的函数
    :param window: GUI窗口对象
    :param result: 差异文件结果集，dict，保存着两个目录下文件差异信息, 绝对路径
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param deal_option: 操作模式
            backup_full   全备份
            backup_update 新增和更新
            only_add 仅新增

    """
    # print(result)
    start_time = time.time()  # 开始时间
    print(deal_option)
    safe_del_dirname = Mytools.makedir4safe_del(dst_path)  # 用于记录safe_del目录
    add_file = "file_only_in_src"
    add_dir = "dir_only_in_src"
    del_file = "file_only_in_dst"
    del_dir = "dir_only_in_dst"
    print("正在同步文件...")
    # 先备份端自拷贝，再更新文件，再更新无法比对，再新增，再删除
    # 执行目录变更文件移动即备份端目录变更
    move_dict = result["move_dict"]
    if move_dict:
        window.exeStateLabel["text"] = "执行目录变更中(备份端自拷贝)..."
        for item in move_dict:
            new_dst = item
            new_src = move_dict[item]
            Mytools.move_file(new_src, new_dst)
    # 执行文件内容变更的文件更新
    if deal_option in ['backup_update', 'backup_full']:  # 同步备份、新增和更新的时候才会执行更新操作
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
    if deal_option == 'backup_full':  # 只有同步备份的时候会删除操作
        if len(result[del_file]) or len(result[del_dir]):  # 有要删除的文件
            window.exeStateLabel["text"] = "执行文件删除..."
        if len(result[del_file]):
            for item in result[del_file]:
                if not os.path.exists(item):
                    continue
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
    window.scr.insert('end', '\n\n\n\n{}\n本次同步用时：{}s\n'.format(msg, syn_time))
    return msg


def find_difference3(src_path, dst_path):
    """
    适配备份端目录变更模式
    用于比对两个目录下文件，result中记录的是文件或文件夹的绝对路径
    :param src_path: 源路径
    :param dst_path: 目标路径(备份端)
    :return: result
            数据格式：
            {"move_dict":{拷贝路径：样本路径},
            "count":{"move_count": len(result["move_dict"])}
    """
    src_file_dict = Mytools.get_files_info(src_path)  # 遍历获取文件信息
    src_file_path_list = list(src_file_dict.keys())  # 获取源目录下所有文件路径
    dst_file_dict = Mytools.get_files_info(dst_path)
    move_dict = {}  # 用于记录移动或者复制文件，{拷贝路径：样本路径}
    # 比对文件
    # 先过滤掉相同文件和同名文件
    for item in src_file_path_list:
        dst_item = item.replace(src_path, dst_path)
        if dst_item in dst_file_dict:  # 判断文件目录结构是否一致
            dst_file_dict.pop(dst_item)  # 过滤相同文件和同名文件
            src_file_dict.pop(item)
    print("过滤相同文件和同名文件完成！")
    # 再遍历获取仅目录变更文件
    dst_file_info_list = []  # 用于记录备份目录所有文件的信息
    dst_file_path_list = []  # 用于记录备份目录所有文件的路径
    for item, info in dst_file_dict.items():
        dst_file_path_list.append(item)
        dst_file_info_list.append(info)

    for item in src_file_dict:
        item_info = src_file_dict[item]
        if item_info in dst_file_info_list:
            dst_item = item.replace(src_path, dst_path)  # 变更目录后的文件名
            dst_old_item = dst_file_path_list[dst_file_info_list.index(item_info)]  # 备份端要进行目录变更前的路径
            move_dict[dst_item] = dst_old_item
            dst_file_path_list.remove(dst_old_item)  # 避免出现一对多的情况
            dst_file_info_list.remove(item_info)  # 避免出现一对多的情况

    count = {"move_count": len(move_dict), }
    result = {"move_dict": move_dict, "count": count}
    return result


def deal_file3(window, src_path, dst_path, result, deal_option):
    """
    适配备份端目录变更模式
    用于移动或者复制文件，并将新旧文件名记录到new_old_record,并导出文件"
    :param window: GUI窗口对象
    :param result: 保存文件目录变更信息 格式{newpath1: oldpath1,}
    :param dst_path: 备份端路径
    :param src_path: 源目录   占位
    :param deal_option: 操作模式   占位
    :return: 
    """""
    start_time = time.time()  # 记录同步操作开始时间
    failed_list = []  # 用于记录拷贝或剪切失败的文件信息
    move_dict = result["move_dict"]
    window.exeStateLabel["text"] = "执行目录变更中..."
    for new_path in move_dict:
        try:
            Mytools.move_file(move_dict[new_path], new_path)  # 剪切文件
        except Exception as e:
            failed_list.append(move_dict[new_path])
            print("操作%s文件失败，详情请查看错误日志！" % move_dict[new_path])
            logger.error_logger(e)
            logger.file_error_logger(move_dict[new_path], e)

    window.exeStateLabel["text"] = "目录变更完成!"
    # 写出到记录文件和日志
    write_time, log_time = Mytools.get_times()  # 获取当前时间的两种格式
    msg = "【文件同步与备份】  备份端 %s 目录变更 %s 个文件成功" % (dst_path, len(move_dict))
    if len(move_dict):
        record_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("new_old_record", write_time))
        Mytools.export_new_old_record(move_dict, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        msg += "，新旧文件名导出到%s" % record_path
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("failed", write_time))
            msg += "\n\t\t%s个文件操作失败，文件信息导出到%s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for item in failed_list:
                    f.write('%s\n' % item)
    logger.operate_logger(msg, log_time)
    syn_time = time.time() - start_time
    print("同步用时：%ss" % syn_time)  # 打印拷贝用时
    window.scr.insert('end', '\n\n\n\n{}\n本次同步用时：{}s\n'.format(msg, syn_time))
    return msg
