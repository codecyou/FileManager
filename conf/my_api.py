# 此模块为所有方法接口/路由层，为了使程序界面和实际执行函数解耦
# 新增myApi模块，用于对view模块中调用的函数进行映射，以实现代码解耦
from core import common_utils, extension_utils, image_utils, search_utils, syn_utils, video_utils


def changeStrToTime(*args, **kwargs):
    """用于将字符串转为时间 三种时间格式20210201135059,2021.2.1.13.05.59,2021-2-1-13-6-59"""
    return common_utils.changeStrToTime(*args, **kwargs)

def getFileVersion(*args, **kwargs):
    """获取文件版本信息"""
    return extension_utils.getFileVersion(*args, **kwargs)

def modifyFileTimeByTimestamp(*args, **kwargs):
    """修改时间戳"""
    return extension_utils.modifyFileTimeByTimestamp(*args, **kwargs)

def export_media_info_as_excel(*args, **kwargs):
    """导出到excel"""
    return extension_utils.export_media_info_as_excel_by_openpyxl(*args, **kwargs)


