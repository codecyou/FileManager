"""用于搜索文件"""
from core import common_utils
import os


def find_same(search_path, mode, filter_flag, filter_str, filter_mode=1):
    """#用walk函数实现遍历目录下所有文件  加过滤功能
    根据mode搜索同名文件或者相同大小文件
    mode    "name" 同名
            "size" 相同大小
            "mtime" 相同修改时间
            "name_mtime" 同名且修改时间相同
            "name_size"  同名且大小相同
            "size_mtime" 大小相同且修改时间相同
            "v_duration" 视频时长相同
            "v_resolution" 视频分辨率相同
            "i_resolution" 图片分辨率相同

            "filter_flag"  是否过滤 True 过滤
            "filter_str"  过滤内容
            "filter_mode"  过滤模式 1排除 2选中
    """

    file_dict = {}  # 用于储存相同文件,格式"{"name"或者"size": [file_path1,file_path1,],...}"
    count = 0  # 用于记录相同文件的个数
    filter_exts = filter_str.lower().replace('.', '').replace('，', ',').split(',')  # 文件后缀名列表
    file_list = get_file_list_after_filter(search_path, filter_flag, filter_exts, filter_mode)  # 根据过滤规则先过滤文件路径
    func_dict = {
        'name': find_same_by_name,
        'size': find_same_by_size,
        'mtime': find_same_by_mtime,
        'name_mtime': find_same_by_name_mtime,
        'name_size': find_same_by_name_size,
        'size_mtime': find_same_by_size_mtime,
        'name_size_mtime': find_same_by_name_size_mtime,
        'v_duration': find_same_by_v_duration,
        'v_resolution': find_same_by_v_resolution,
        'i_resolution': find_same_by_i_resolution,
    }
    file_dict = find_same_by_option(file_list, func_dict[mode])  # 执行查重
    file_dict, count = common_utils.filter_dict(file_dict)  # 过滤去除字典中只有一个路径的key
    return file_dict, count


def get_file_list_after_filter(search_path, filter_flag, filter_exts, filter_mode=1):
    """遍历目录，并根据需要排除或者选中的过滤要求，过滤后的文件路径列表"""
    file_list = []
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
            file_list.append(os.path.join(root, file_name))
    return file_list
        

def find_same_by_name(file_path):
    """查找文件名相同"""
    return os.path.basename(file_path)


def find_same_by_size(file_path):
    """查找文件大小相同"""
    return os.path.getsize(file_path)


def find_same_by_mtime(file_path):
    """查找修改时间相同"""
    return os.path.getmtime(file_path)


def find_same_by_name_size(file_path):
    return '%s_%s' % (os.path.basename(file_path), os.path.getsize(file_path))


def find_same_by_name_mtime(file_path):
    return '%s_%s' % (os.path.basename(file_path), os.path.getmtime(file_path))


def find_same_by_size_mtime(file_path):
    return '%s_%s' % (os.path.getsize(file_path), os.path.getmtime(file_path))


def find_same_by_name_size_mtime(file_path):
    return '%s_%s_%s' % (os.path.basename(file_path), os.path.getsize(file_path), os.path.getmtime(file_path))


def find_same_by_v_duration(file_path):
    """查找视频时长相同的文件"""
    if common_utils.check_filetype(file_path, 'video'):
        res = common_utils.get_video_info(file_path)
        return str(res['duration_sec'])


def find_same_by_v_resolution(file_path):
    """查找视频分辨率相同的文件"""
    if common_utils.check_filetype(file_path, 'video'):
        res = common_utils.get_video_info(file_path)
        return str(res['width']) + 'x' +  str(res['height'])


def find_same_by_i_resolution(file_path):
    """查找图片分辨率相同的文件"""
    if common_utils.check_filetype(file_path, 'image'):
        res = common_utils.get_image_resolution(file_path)
        return str(res['width']) + 'x' +  str(res['height'])


def find_same_by_option(file_list, func):
    """根据指定的选项要求查找重复文件
    :param file_list: 文件的路径集合
    :param func: 获取选项要求信息的方法
    """
    file_dict = {}  # 用于储存相同文件
    for file_path in file_list:
        option = func(file_path)
        if option is None:
            continue
        if option in file_dict:
            file_dict[option].append(file_path)
        else:
            file_dict[option] = list((file_path,))
    return file_dict
