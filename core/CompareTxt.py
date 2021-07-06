"""用于比对文本文件内容"""
import difflib
import sys
import os
from core import Mytools, hash_core, logger

try:
    # 避免setting模块无法导入时本模块不能独立工作
    from conf import settings
    RECORD_DIR = os.path.join(settings.RECORD_DIR, "文本内容差异")
except Exception:
    RECORD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dir', "文本内容差异")

# path_record = ''  # 用于记录当前差异文件输出的文件夹路径

wrapcolumn = 100  # 中文栏最大宽度

if not os.path.exists(RECORD_DIR):  # 输出目录不存在则创建
    os.makedirs(RECORD_DIR)


# 读取建表语句或配置文件
def read_file(file_path):
    """
    读取读取文本文件内容
    :param file_path: 文件路径
    :return:
    """
    try:
        file_desc = open(file_path, 'r', encoding='utf-8')
        # 读取后按行分割
        text = file_desc.read().splitlines()
        file_desc.close()
        return text
    except IOError as error:
        print('Read input file Error: {0}'.format(error))
        sys.exit()


# 比较两个文件并把结果生成一份html文本
def compare_file(file1, file2, path_record):
    """
    比较两个文件并把结果生成一份html文本,并返回html文件路径
    :param file1: 文件路径1
    :param file2: 文件路径2
    :param path_record:  输出记录文件路径
    :return:
    """
    if file1 == "" or file2 == "":
        print('文件路径不能为空：第一个文件的路径：{0}, 第二个文件的路径：{1} .'.format(file1, file2))
        sys.exit()
    else:
        print("正在比较文件{0} 和 {1}".format(file1, file2))
    text1_lines = read_file(file1)
    text2_lines = read_file(file2)
    diff = difflib.HtmlDiff(tabsize=4, wrapcolumn=wrapcolumn)    # 创建HtmlDiff 对象
    # result = diff.make_file(text1_lines, text2_lines, fromdesc=file1, todesc=file2)  # 通过make_file 方法输出 html 格式的对比结果
    # 通过make_file 方法输出 html 格式的对比结果, context参数可以设置只显示差异行上线多少内容 不会显示大部分相同内容
    # context 为True时，只显示差异的上下文，为false，显示全文，numlines默认为5
    result = diff.make_file(text1_lines, text2_lines, fromdesc=file1, todesc=file2, context=True)
    if not os.path.exists(path_record):  # 输出目录不存在则创建
        os.makedirs(path_record)
    # 将结果写入到diff_xxx.html文件中
    html_path = os.path.join(path_record, "diff_%s.html" % os.path.basename(file1))
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(result)
            print("0==}==========> Successfully Finished\n")
    except IOError as error:
        print('写入html文件错误：{0}'.format(error))
    return html_path


def compare_file_list(src_path, dst_path):
    """
    用于比对列表中的文件的内容差异
    :param src_path: 源目录路径
    :param dst_path: 目标目录路径
    :return:
    """

    file_list1 = Mytools.get_pathlist(src_path)
    file_list2 = Mytools.get_pathlist(dst_path)
    # print(file_list1, file_list2)
    compare_list = []  # 要比对的文件路径
    # 获取要比对的文件列表
    for item in file_list1:
        if item.replace(src_path, dst_path) in file_list2:
            compare_list.append(item)
    # 比对文件内容
    write_time, log_time = Mytools.get_times()  # 输出时间（用于命名文件夹），记录日志时间
    result = {"only_in_src": [], "only_in_dst": [], "common_files": [], "diff_files": []}  # 记录比对结果
    path_record = os.path.join(RECORD_DIR, write_time)  # 建立用于存储本次差异文件的目录
    if not os.path.exists(path_record):  # 输出目录不存在则创建
        os.makedirs(path_record)
    for file1 in file_list1:
        file2 = file1.replace(src_path, dst_path)
        if file2 in file_list2:
            if hash_core.get_md5(file1) == hash_core.get_md5(file2):  # 文件内容一致则直接进入下一个文件比较
                result["common_files"].append((file1, file2))
                continue
            try:
                html_path = compare_file(file1, file2, path_record)
                print("文件内容差异导出到 %s" % html_path)
                result["diff_files"].append((file1, file2))
            except UnicodeDecodeError:
                print("文件不是文本类型文件！")
        else:
            result["only_in_src"].append(file1)
    for file2 in file_list2:
        file1 = file2.replace(dst_path, src_path)
        if file1 not in file_list1:
            result["only_in_dst"].append(file2)

    logger.operate_logger("%s 比对 %s 和 %s 文件内容，文件文本差异导出到 %s" % (log_time, src_path, dst_path, path_record))
    return path_record, result


def compare_file_list2(src_path, dst_path, path_record):
    """
    用于比对列表中的文件的内容差异
    :param src_path: 源目录路径
    :param dst_path: 目标目录路径
    :param path_record:  输出记录文件路径
    :return:
    """
    file_list1 = Mytools.get_pathlist(src_path)
    file_list2 = Mytools.get_pathlist(dst_path)
    # print(file_list1, file_list2)
    compare_list = []  # 要比对的文件路径
    # 获取要比对的文件列表
    for item in file_list1:
        if item.replace(src_path, dst_path) in file_list2:
            compare_list.append(item)
    # 比对文件内容
    result = {"only_in_src": [], "only_in_dst": [], "common_files": [], "diff_files": []}  # 记录比对结果
    if not os.path.exists(path_record):  # 输出目录不存在则创建
        os.makedirs(path_record)
    for file1 in file_list1:
        file2 = file1.replace(src_path, dst_path)
        if file2 in file_list2:
            if hash_core.get_md5(file1) == hash_core.get_md5(file2):  # 文件内容一致则直接进入下一个文件比较
                result["common_files"].append((file1, file2))
                continue
            try:
                html_path = compare_file(file1, file2, path_record)
                print("文件内容差异导出到 %s" % html_path)
                result["diff_files"].append((file1, file2))
            except UnicodeDecodeError:
                print("文件不是文本类型文件！")
        else:
            result["only_in_src"].append(file1)
    for file2 in file_list2:
        file1 = file2.replace(dst_path, src_path)
        if file1 not in file_list1:
            result["only_in_dst"].append(file2)
    return path_record, result
