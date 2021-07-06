# 提供所有的日志方法
import os
import time
from conf import settings


def error_logger(error_msg):
    """
    用于保存错误日志
    :param error_msg: 错误信息
    :return:
    """
    error_msg = str(error_msg)
    f = open(settings.LOG_PATH["error"], 'a', encoding='utf-8')
    f.write("%s\t error:%s \n" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), error_msg))
    f.close()


def file_error_logger(file_path, error_msg):
    """
    用于保存错误日志
    :param file_path: 文件路径
    :param error_msg: 错误信息
    :return:
    """
    error_msg = str(error_msg)
    f = open(settings.LOG_PATH["file_error"], 'a', encoding='utf-8')
    f.write("%s\t %s:\t error:%s \n" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), file_path, error_msg))
    f.close()


def update_logger(ask, answer):
    """
    用于保存update答案集日志
    :param ask: 问题
    :param answer: 答复
    :return:
    """
    f = open(settings.LOG_PATH["update"], 'a', encoding='utf-8')
    f.write("%s\t ask:%s \t answer:%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), ask, answer))
    f.close()


def operate_logger(msg, has_time=''):
    """
    用于保存操作日志，供外部程序使用
    :param msg: 操作信息，进行了什么操作
    :param has_time: 携带时间信息  为了保证所有日志记录所有时间的时间信息是一致的
    :return:
    """
    with open(settings.LOG_PATH["operate"], 'a', encoding='utf-8') as f:
        if has_time:
            # 携带时间信息
            msg = "%s\t%s\n" % (has_time, msg)
        else:
            # 加入实时时间
            local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            msg = "%s\t%s\n" % (local_time, msg)
        f.write(msg)
        print(msg)  # 输出到屏幕


def backup_logger(result, src_path, dst_path, safe_del_dirname, option):
    """
    用于保存操作日志
    update:
        更改日志结构和数据格式 以配合backup_V1.py
    :param result: 差异文件结果集，dict，保存着两个目录下文件差异信息
    :param src_path: 源目录
    :param dst_path: 目标目录
    :param safe_del_dirname: 存放被删除文件的safe_del目录
    :param option: 操作模式
            backup_full   全备份
            backup_update 增量备份
            recovery      备份还原
    :return:
    """
    # print(result)
    # 加入实时时间
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    only_in_src_count = len(result["file_only_in_src"]) + len(result["dir_only_in_src"])
    only_in_dst_count = len(result["file_only_in_dst"]) + len(result["dir_only_in_dst"])
    if "move_dict" in result:
        # 判断是否是Mybackup传进来的result
        update_count = len(result["diff_files"]) + len(result["common_funny"]) + len(result["move_dict"])
    else:
        update_count = len(result["diff_files"]) + len(result["common_funny"])
    add_file = "file_only_in_src"
    add_dir = "dir_only_in_src"
    del_file = "file_only_in_dst"
    del_dir = "dir_only_in_dst"

    msg = '【文件同步与备份】  '
    if "backup_full" == option:
        msg += "同步备份完成！新增%s个项目,删除%s个项目,更新%s个项目" % (only_in_src_count, only_in_dst_count, update_count)
    if "backup_update" == option:
        msg += "增量备份完成！新增%s个项目,删除0个项目,更新%s个项目" % (only_in_src_count, update_count)
    if "recovery" == option:
        msg += "同步还原完成！新增%s个项目,删除%s个项目,更新%s个项目" % (only_in_dst_count, only_in_src_count, update_count)
        # src_path, dst_path = dst_path, src_path  # 传进来的实参已经置换过
        add_file, del_file = del_file, add_file
        add_dir, del_dir = del_dir, add_dir
    if "only_add" == option:
        msg += "仅新增文件完成！新增%s个项目" % only_in_src_count

    # 将操作记录保存到操作日志'log/operate.log'文件
    if safe_del_dirname:
        safe_del_msg = "删除和更新文件原文件导出到%s目录下!" % safe_del_dirname
        operate_msg = "%s\t%s\t%s  -->  %s" % (msg, safe_del_msg, src_path, dst_path)
    else:
        operate_msg = "%s\t%s  -->  %s" % (msg, src_path, dst_path)
    operate_logger(operate_msg, local_time)
    print(operate_msg)
    # 将备份或同步详细记录保存到日志'log/backup_info.log'文件
    with open(settings.LOG_PATH["backup_info"], 'a', encoding='utf-8') as f:
        f.write("-" * 100)
        f.write("\n%s\t %s\n" % (local_time, msg))
        if safe_del_dirname:
            f.write("删除和更新文件原文件导出到%s目录下!\n" % safe_del_dirname)
        f.write("%s  -->  %s\n" % (src_path, dst_path))
        # 记录新增
        if len(result[add_file]) + len(result[add_dir]):
            if "move_dict" in result:
                f.write("新增(文件%s个,文件夹%s个)：\n" % (len(result[add_file]) + len(result["move_dict"]), len(result[add_dir])))
            else:
                f.write("新增(文件%s个,文件夹%s个)：\n" % (len(result[add_file]), len(result[add_dir])))
            if len(result[add_file]):
                f.write("->文件：\n")
                for item in result[add_file]:
                    f.write("%s\n" % item)
            if "move_dict" in result:
                if len(result["move_dict"]):
                    f.write("->备份端自拷贝：\n")
                    for dst_item, item in result["move_dict"].items():
                        f.write("%s  -->  %s\n" % (item, dst_item))
            if len(result[add_dir]):
                f.write("->文件夹：\n")
                for item in result[add_dir]:
                    f.write("%s\n" % item)
        # 记录更新
        if "only_add" != option:
            if update_count:
                f.write("更新(文件%s个)：\n" % update_count)
                for item in result["diff_files"]:
                    f.write("%s\n" % item)
                for item in result["common_funny"]:
                    f.write("%s\n" % item)

        # 记录删除
        if "backup_update" != option:
            if len(result[del_file]) + len(result[del_dir]):
                f.write("删除(文件%s个,文件夹%s个)：\n" % (len(result[del_file]), len(result[del_dir])))
                if len(result[del_file]):
                    f.write("->文件：\n")
                    for item in result[del_file]:
                        f.write("%s\n" % item)
                if len(result[del_dir]):
                    f.write("->文件夹：\n")
                    for item in result[del_dir]:
                        f.write("%s\n" % item)
        f.write("\n")

    return operate_msg


def record_logger(file_list, record_path, msg):
    """
    用于保存删除记录操作日志
    :param file_list: 已被删除的文件列表
    :param record_path: 要导出记录地址
    :param msg要记录到日志的信息
    :return:
    """
    # 加入实时时间
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 向日志文件中记录详情
    operate_logger(msg, local_time)
    with open(record_path, 'a', encoding='utf-8') as f:
        f.write("-" * 100)
        f.write("\n%s\n" % msg)
        for item in file_list:
            f.write("%s\n" % item)
        f.write("\n")


def record_logger2(file_list, record_path, msg):
    """
    用于保存删除记录操作日志, 不调用operate_logger
    :param file_list: 已被删除的文件列表
    :param record_path: 要导出记录地址
    :param msg要记录到日志的信息
    :return:
    """
    with open(record_path, 'a', encoding='utf-8') as f:
        f.write("-" * 100)
        f.write("\n%s\n" % msg)
        for item in file_list:
            f.write("%s\n" % item)
        f.write("\n")


def proces_logger(msg, has_time=''):
    """
    用于保存操作日志，供外部程序使用
    :param msg: 操作信息，进行了什么操作
    :param has_time: 携带时间信息  为了保证所有日志记录所有时间的时间信息是一致的
    :return:
    """
    with open(settings.LOG_PATH["process"], 'a', encoding='utf-8') as f:
        if has_time:
            # f.write("%s\t %s\n" % (has_time, msg))
            f.write("\t%s\n" % msg)
        else:
            # 加入实时时间
            local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            f.write('-' * 80)
            f.write('\n')
            f.write("%s\t %s\n" % (local_time, msg))


def setting_logger(setting_list, msg):
    """
    用于保存设置修改的操作日志
    :param setting_list: 已被删除的文件列表
    :param msg要记录到日志的信息
    :return:
    """
    # 加入实时时间
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 向日志文件中记录详情
    operate_logger(msg, local_time)
    record_path = os.path.join(settings.LOG_DIR, 'settings.log')
    with open(record_path, 'a', encoding='utf-8') as f:
        f.write("-" * 100)
        f.write("\n%s\t%s\n" % (local_time, msg))
        f.write("%s\n->\n%s" % (str(setting_list[0]), str(setting_list[1])))
        f.write("\n")
