#!/usr/bin/python3
"""
单进程实现， 用于实现文件目录结构同步
即将备份端的文件目录结构同步成跟源目录一致，备份端自己移动，主要处理备份端目录结构有调整或者文件夹有重命名的情况
"""
from core import logger
from core import Mytools
from conf import settings
import os
import time


def find_difference(src_path, dst_path):
    """
    用于比对两个目录下文件，result中记录的是文件或文件夹的绝对路径
    :param src_path: 源路径
    :param dst_path: 目标路径(备份端)
    :return: "move_dict":{拷贝路径：样本路径}
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
            move_dict[dst_item] = dst_file_path_list[dst_file_info_list.index(item_info)]

    count = {"move_count": len(move_dict), }
    result = {"move_dict": move_dict, "count": count}
    return result


def deal_file(window, src_path, dst_path, result, deal_option):
    """
    用于移动或者复制文件，并将新旧文件名记录到new_old_record,并导出文件"
    :param window: GUI窗口对象
    :param result: 保存文件目录变更信息 格式{newpath1: oldpath1,}
    :param dst_path: 备份端路径
    :param src_path: 源目录   占位
    :param deal_option: 操作模式   占位
    :return: 
    """""
    record_path = None  # 用来记录导出的新旧文件名记录路径 用于返回
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
    if len(move_dict):
        write_time, log_time = Mytools.get_times()  # 获取当前时间的两种格式
        record_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("new_old_record", write_time))
        Mytools.export_new_old_record(move_dict, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        msg = "备份端%s 目录变更%s个文件成功，新旧文件名导出到%s" % (dst_path, len(move_dict), record_path)
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("failed", write_time))
            msg += "\n\t\t%s个文件操作失败，文件信息导出到%s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for item in failed_list:
                    f.write('%s\n' % item)
        logger.operate_logger(msg, log_time)
        return msg

    return record_path


def deal_syn():
    """用于处理备份端文件目录变更操作"""
    src_path = Mytools.input_path("源目录路径")
    dst_path = Mytools.input_path("备份端路径")
    move_dict = find_difference(src_path, dst_path)
    move_count = len(move_dict)
    print("\n比对结果：")

    if move_count == 0:
        print("无可同步文件！")
        return
    print("%s    ---->    %s" % (src_path, dst_path))  # 打印输出源路径和目标路径
    print("备份端目录变更文件%s个" % move_count)
    option_menu = """请输入要进行的操作：
    1.查看详情
    2.执行同步操作
    Q.返回上级菜单"""
    while True:
        Mytools.show_menu(option_menu)
        option = input(">>> ").strip()
        if option in ["1", "查看详情"]:
            print("%s    ---->    %s" % (src_path, dst_path))  # 打印输出源路径和目标路径
            print("备份端%s目录变更：" % dst_path)
            for dst_item, item in move_dict.items():
                print("%s  -->  %s" % (item, dst_item))
        elif option in ["2", "同步"]:
            start_time = time.time()  # 开始时间
            print("正在同步文件...")
            # 执行目录变更文件移动
            deal_file(src_path, dst_path, move_dict, None)
            print("同步用时：%s" % (time.time() - start_time))  # 打印拷贝用时
            break
        elif option in ["q", "Q", "退出", "返回上级菜单"]:
            print("取消本次操作，返回上级菜单！")
            return
        else:
            print("您的输入有误！请重新输入！")


def main():
    Mytools.my_init()
    while True:
        try:
            deal_syn()
        except Exception as e:
            logger.error_logger(e)


if __name__ == '__main__':
    main()
