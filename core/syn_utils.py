from core import common_utils
import filecmp
import os


def filter_4_list(base_path, result_list):
    r"""
    用于从list中过滤出文件列表和目录列表
    :param base_path: 文件完整父路径
    :param result_list: 保存文件在base_path下的相对路径的列表,即C:\a\b.txt, base_path为C:\a,result_list中保存b.txt，非绝对路径
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
    用于从dict中过滤出文件列表和目录列表
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


def do_compare(src_dir, dst_dir, result, child_flag=False, parent_dir=''):
    """
    适配基于filecmp模块的文件同步功能
    用于比对两个目录下文件, result中记录的是文件或文件夹的相对路径
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
    src_file_only_info_dict = common_utils.get_files_info_by_path(src_path)  # 遍历获取文件信息,仅在src的文件信息
    dst_file_only_info_dict = common_utils.get_files_info_by_path(dst_path)
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
    src_file_dict = common_utils.get_files_info_by_path(src_path)  # 遍历获取文件信息
    src_file_path_list = list(src_file_dict.keys())  # 获取源目录下所有文件路径
    dst_file_dict = common_utils.get_files_info_by_path(dst_path)
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


def find_difference4(src_path, dst_path, time_fix, hash_flag):
    """
    适配自己实现的Mybackup方式，支持时间偏移，hash比对
    用于比对两个目录下文件，result中记录的是文件或文件夹的绝对路径
    :param src_path: 源路径
    :param dst_path: 目标路径(备份端)
    :param time_fix: 时间偏移修正，不同的文件系统会有时间精度丢失，比如NTFS时间戳记录到小数点，FAT32则会取整到整数，这样就会导致同一个文件时间有偏移
    :param hash_flag: 是否校验文件hash值 True 校验
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
    src_file_only_info_dict = common_utils.get_files_info_by_path(src_path)  # 遍历获取文件信息,仅在src的文件信息
    dst_file_only_info_dict = common_utils.get_files_info_by_path(dst_path)
    file_only_in_src = []
    file_only_in_dst = dst_file_list[:]  # 引用类型是址传递必须拷贝数据，但是切片操作也仅是浅拷贝而已
    move_dict = {}  # 用于记录移动或者复制文件，{拷贝路径：样本路径}
    # 格式{new_dst_file1:old_dst_file1, new_dst_file2:old_dst_file1, }
    diff_files = []  # 用于记录文件内容发生变化文件
    result = {}  # 用于记录结果
    common_funny = []  # 用于记录同名但类型不同的文件，即 与文件同名的文件夹
    dir_only_in_src = []
    time_fix = float(time_fix)
    # 比对文件
    # 1.找出相同文件，内容有更新的文件，以及同级目录文件夹和文件出现同名导致无法比较的情况
    for item in src_file_list:
        dst_item = item.replace(src_path, dst_path)
        if dst_item in dst_file_list:  # 判断文件目录结构是否一致
            _src_size = src_file_only_info_dict[item]['size']
            _src_mtime = src_file_only_info_dict[item]['mtimestamp']
            _dst_size = dst_file_only_info_dict[dst_item]['size']
            _dst_mtime = dst_file_only_info_dict[dst_item]['mtimestamp']
            flag = False  # True文件为相同文件, False 为内容有变化
            # 文件名和文件大小相同，时间戳在偏移修正范围内，视为相同文件
            if _src_size == _dst_size:
                if hash_flag is True:  # 如果选中校验hash值则不用在比对时间偏移结果了
                    if common_utils.get_md5(item) == common_utils.get_md5(dst_item):
                        flag = True
                else:
                    if abs(_src_mtime - _dst_mtime) <= time_fix:
                        flag = True
            if flag is False:
                # 文件信息不一致，且时间戳不在偏移修正范围内，视为文件内容有变化！
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
            dst_old_item = dst_file_only_path_list[dst_file_only_info_list.index(item_info)]  # 备份端要进行目录变更前的路径
            if hash_flag is True:  # 如果选中校验hash值
                if common_utils.get_md5(item) != common_utils.get_md5(dst_old_item):
                    continue
            dst_item = item.replace(src_path, dst_path)  # 变更目录后的文件名
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


def find_difference5(src_path, dst_path, time_fix, hash_flag):
    """
    适配备份端目录变更模式，支持时间偏移，hash比对
    用于比对两个目录下文件，result中记录的是文件或文件夹的绝对路径
    :param src_path: 源路径
    :param dst_path: 目标路径(备份端)
    :param time_fix: 时间偏移修正，不同的文件系统会有时间精度丢失，比如NTFS时间戳记录到小数点，FAT32则会取整到整数，这样就会导致同一个文件时间有偏移
    :param hash_flag: 是否校验文件hash值 True校验
    :return: result
            数据格式：
            {"move_dict":{拷贝路径：样本路径},
            "count":{"move_count": len(result["move_dict"])}
    """
    src_file_dict = common_utils.get_files_info_by_path(src_path)  # 遍历获取文件信息
    src_file_path_list = list(src_file_dict.keys())  # 获取源目录下所有文件路径
    dst_file_dict = common_utils.get_files_info_by_path(dst_path)
    move_dict = {}  # 用于记录移动或者复制文件，{拷贝路径：样本路径}
    time_fix = float(time_fix)
    # 比对文件
    # 先过滤掉相同文件和同名文件
    for item in src_file_path_list:
        dst_item = item.replace(src_path, dst_path)
        if dst_item in dst_file_dict:  # 判断文件目录结构是否一致
            dst_file_dict.pop(dst_item)  # 过滤相同文件和同名文件
            src_file_dict.pop(item)
    print("过滤相同文件和同名文件完成！")
    # 再遍历获取仅目录变更文件
    dst_info_to_path_dict = {}  # 格式 {(name, size): path,}
    for _path, info in dst_file_dict.items():
        dst_info_to_path_dict[(info['name'], info['size'])] = _path
    for item in src_file_dict:
        item_info = (src_file_dict[item]['name'], src_file_dict[item]['size'])
        if item_info in dst_info_to_path_dict:
            src_mtime = src_file_dict[item]['mtimestamp']
            dst_old_item = dst_info_to_path_dict[item_info]
            dst_mtime = dst_file_dict[dst_old_item]['mtimestamp']
            if hash_flag is True:  # 如果选中校验hash值
                if common_utils.get_md5(item) != common_utils.get_md5(dst_old_item):
                    continue
            else:
                if abs(src_mtime - dst_mtime) > time_fix:  # 时间戳差值在偏移修正范围内
                    continue
            dst_item = item.replace(src_path, dst_path)  # 变更目录后的文件名
            move_dict[dst_item] = dst_old_item
            dst_info_to_path_dict.pop(item_info)

    count = {"move_count": len(move_dict), }
    result = {"move_dict": move_dict, "count": count}
    return result


