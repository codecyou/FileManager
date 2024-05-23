# 扩展工具模块，存放已经不再使用的功能函数，作为储备代码备用
import os
from win32com.client import Dispatch
import cv2
import pandas as pd


def get_version_number(file_path):
    ''' 获取文件版本信息，这个兼容性强 '''
    information_parser = Dispatch("Scripting.FileSystemObject")
    version = information_parser.GetFileVersion(file_path)
    return version


def get_image_from_video_by_opencv(pathIn='', pathOut='', extract_time_point='0', continue_flag=False):
    '''
    从视频提取单张图片
    :param pathIn: 视频路径
    :param pathOut: 图片路径
    :param continue_flag: 是否覆盖， False 覆盖， True 跳过
    '''
    if continue_flag is True:
        if os.path.exists(pathOut):  # 继续之前进度
            print(pathOut, "已存在,跳过！")
            return
    cap = cv2.VideoCapture(pathIn)  # 打开视频文件
    cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * int(extract_time_point)))
    success, image = cap.read()
    if success:
        cv2.imencode('.jpg', image)[1].tofile(pathOut)
    else:
        raise NameError('文件数据异常!')


def export_media_info_as_excel_by_pandas(excel_path, res):
    """使用pandas写出excel文件
    :param excel_path: excel路径
    :param res: 要写出的数据
    """
    # 将给定路径下的所有视频/音频/图像文件的信息整合到excel表
    with pd.ExcelWriter(excel_path) as writer:
        #输出电影文件的重要信息到film_info.xlsx文件
        film_info = pd.DataFrame([])
        for cate in res:
            film_info = pd.DataFrame([])
            columns = []
            for item in res[cate]:
                columns.append(item.get('文件名'))
                print(item)
                film_info = pd.concat([film_info, pd.Series(item)], axis=1)
            film_info.columns = columns
            film_info.to_excel(writer, sheet_name='%s_info' % cate)


