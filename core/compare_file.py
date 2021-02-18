"""用于比对文本文件内容"""
import difflib
import sys
import argparse
import webbrowser
import os
from core import Mytools, hash_core, logger

try:
    # 避免setting模块无法导入时本模块不能独立工作
    from conf import settings
    RECORD_DIR = os.path.join(settings.RECORD_DIR, "文本内容差异")
except Exception:
    RECORD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dir', "文本内容差异")

current_record_dir = ''  # 用于记录当前差异文件输出的文件夹路径

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
def compare_file(file1, file2):
    """
    比较两个文件并把结果生成一份html文本,并返回html文件路径
    :param file1: 文件路径1
    :param file2: 文件路径2
    :return:
    """
    global current_record_dir
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

    # 将结果写入到result_comparation.html文件中
    # html_path = "result_comparation.html"
    html_path = os.path.join(current_record_dir, "diff_%s.html" % os.path.basename(file1))
    try:
        with open(html_path, 'w', encoding='utf-8') as result_file:
            result_file.write(result)
            print("0==}==========> Successfully Finished\n")
    except IOError as error:
        print('写入html文件错误：{0}'.format(error))
    return html_path


def compare_file_list(src_path, dst_path, file_list):
    """
    用于比对列表中的文件的内容差异
    :param src_path: 源目录路径
    :param dst_path: 目标目录路径
    :param file_list: 两个目录中相同目录层次的同名文件列表
    :return:
    """
    global current_record_dir
    # 比对文件内容
    write_time, log_time = Mytools.get_times()  # 输出时间（用于命名文件夹），记录日志时间
    diff_file_list = []  # 记录差异文件的列表
    current_record_dir = os.path.join(RECORD_DIR, write_time)  # 建立用于存储本次差异文件的目录
    if not os.path.exists(current_record_dir):  # 输出目录不存在则创建
        os.makedirs(current_record_dir)
    for item in file_list:
        file1 = item
        file2 = item.replace(src_path, dst_path)
        if hash_core.get_md5(file1) == hash_core.get_md5(file2):  # 文件内容一致则直接进入下一个文件比较
            continue
        try:
            html_path = compare_file(file1, file2)
            print("文件内容差异导出到%s" % html_path)
            diff_file_list.append(html_path)
        except UnicodeDecodeError:
            print("文件不是文本类型文件！")

    logger.operate_logger("%s 比对%s  和%s  文件内容，文件文本差异导出到%s" % (log_time, src_path, dst_path, current_record_dir))
    return current_record_dir, diff_file_list


if __name__ == "__main__":
    # To define two arguments should be passed in, and usage: -f1 fname1 -f2 fname2
    my_parser = argparse.ArgumentParser(description="传入两个文件参数")
    my_parser.add_argument('-f1', action='store', dest='fname1', required=True)
    my_parser.add_argument('-f2', action='store', dest='fname2', required=True)
    # retrieve all input arguments
    given_args = my_parser.parse_args()
    file1 = given_args.fname1
    file2 = given_args.fname2
    html_path = compare_file(file1, file2)
    webbrowser.open_new_tab(html_path)
