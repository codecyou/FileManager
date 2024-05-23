from core import common_utils
from core.logger import logger
from core import image_utils
from conf import settings
import os
import time
import subprocess
import threading
from tkinter import messagebox as mBox
# 开启静默模式不弹cmd窗口
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE


def millisecToAssFormat(t):  # 取时间
    if t < 3600:
        h = 00
    else:
        h = t // 3600
    s = t % 60
    m = t // 60 - h * 60
    # return '%02d:%02d:%02d' % (h, m, s)
    return '%02d:%02d:%05.2f' % (h, m, s)  # 小数点占一位


def get_img_thread(path_list, src_path, dst_path, extract_time_point, continue_flag, cal_res, mutex):
    """
    多线程-子线程提取视频图像
    :param path_list: 图片文件路径列表
    :param src_path: 原视频目录
    :param dst_path: 要保存图片的目录
    :param extract_time_point: 截取时间点
    :param continue_flag: 是否继续上次进度
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0, 'failed_files': []}
    :param mutex: 互斥锁
    """
    failed_list = []
    for pathIn in path_list:
        mutex.acquire()
        cal_res['count'] += 1
        mutex.release()
        pathOut = pathIn.replace(src_path, dst_path) + '_{}sec.jpg'.format(extract_time_point)  # 图片路径
        extract_time = float(extract_time_point)
        if extract_time < 0:  # 截取时间点输入为负值则表示倒数时间
            # 获取视频信息， 实测多线程使用ffmpeg获取视频时长反而更快
            duration = 0
            videoInfo = common_utils.get_video_info(pathIn)  # 视频信息
            if videoInfo:
                # 时长 秒,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
                duration = float(videoInfo.get('duration_sec'))
            extract_time += duration
        pathOutDir = os.path.dirname(pathOut)
        try:
            if continue_flag:  # 如果选中继续上次进度，则目标目录已有同名图片时会跳过，否则会覆盖
                if os.path.exists(pathOut):
                    continue
            if not os.path.exists(pathOutDir):
                os.makedirs(pathOutDir)
            # 方式一： opencv 提取
            # 方式二： ffmpeg提取
            # command = [settings.FFMPEG_PATH, '-ss', str(extract_time), '-i', pathIn, '-frames:v', '1', pathOut]  # 命令
            command = [settings.FFMPEG_PATH, '-y', '-ss', str(extract_time), '-i', pathIn, '-frames:v', '1', pathOut]  # 命令
            # print(command)
            subprocess.call(command, shell=True)
        except Exception as e:
            logger.error('提取 %s 出错,error: %s' % (pathOut, e))
            failed_list.append(pathIn)
    if len(failed_list):
        mutex.acquire()
        cal_res['failed_files'].extend(failed_list)
        mutex.release()
    print('提取视频帧图像子线程结束！')


def get_img_from_video(self, src_dir, dst_dir, extract_time_point, continue_flag):
    """从视频中提取图片  多线程,遍历src_dir,提取该目录下所有视频帧图像到dst_dir
    """
    # 遍历文件获取视频路径集合
    time_str = common_utils.get_times_now().get('time_str')
    self.scr.insert("end", "%s  正在遍历文件...\n" % (time_str, src_dir))
    start_time = time.time()  # 记录开始时间
    video_list = common_utils.get_files_by_filetype(src_dir, 'video')  # 用来保存目录下所有视频的路径
    total_count = len(video_list)
    time_str = common_utils.get_times_now().get('time_str')
    get_video_time_msg = "%s  遍历 %s 完成！总共 %s 个视频文件,用时 %.3f 秒" % (time_str, src_dir, total_count, (time.time() - start_time))
    self.scr.insert('end', '{}\n'.format(get_video_time_msg))
    
    # 提取视频帧图像
    total_msg = get_img_from_video_list(self, src_dir, dst_dir, video_list, extract_time_point, continue_flag)
    logger.info('【提取视频帧图像】  %s' % total_msg)
    return total_msg


def get_img_from_video_list(self, src_dir, dst_dir, video_list, extract_time_point, continue_flag):
    """从视频中提取图片  多线程, 根据记录需要提取的视频路径的video_list 提取
    """
    mutex = threading.Lock()  # 创建互斥锁
    cal_res = {'count': 0, 'failed_files': []}  # 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    # 判断是否图片保存目录路径是否存在，不存在新建
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    start_time = time.time()  # 记录开始时间
    total_count = len(video_list)
    self.is_complete = False  # 重置任务进度状态
    t = threading.Thread(target=self.show_rate_calc, args=(cal_res, total_count))  # 创建子进程用于更新进度条
    t.daemon = True
    t.start()
    self.scr.insert('end', '\n{}  正在提取视频帧图像...'.format(common_utils.get_times_now().get('time_str')))
    if (total_count, total_count)  > (40, settings.IO_THREAD_NUM):  # 视频数大于40个并且大于线程数
        sub_count = total_count // settings.IO_THREAD_NUM
        thread_list = []
        for i in range(settings.IO_THREAD_NUM-1):
            t = threading.Thread(target=get_img_thread, args=(video_list[sub_count*i: sub_count*(i+1)], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex))
            t.daemon = True
            t.start()
            thread_list.append(t)
        get_img_thread(video_list[sub_count*(settings.IO_THREAD_NUM-1):], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex)
        # 判断是否所有文件已计算完成
        while True:
            flag = True  # 是否可以所有子线程已结束
            for item in thread_list:
                if item.is_alive():
                    flag = False
            if flag is True:
                print('子线程已全部结束')
                break
            time.sleep(0.5)
    else:
        get_img_thread(video_list, src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex)
    
    # 记录到日志文件
    self.is_complete = True  # 任务完成标记
    total_msg = "提取目录 %s 下视频第 %s 秒图像到目录 %s 下完成！用时 %.3f 秒" % (src_dir, extract_time_point, dst_dir, time.time() - start_time)
    self.scr.insert("end", "\n\n%s  %s\n" % (common_utils.get_times_now().get('time_str'), total_msg))
    self.scr.see('end')
    # 将失败文件信息记录到日志
    failed_msg = ''
    if len(cal_res['failed_files']):
        failed_msg = "\t%s\n" % "总共有 %s 个视频提取图片失败!" % len(cal_res['failed_files'])
        self.scr.insert("end", failed_msg)
        for item in cal_res['failed_files']:
            failed_msg += "\t%s\n" % str(item)
    self.scr.insert("end", failed_msg)
    self.scr.see('end')

    return total_msg


def get_videos_phash(self, src_dir_path, img_dir_path, extract_time_point, continue_flag, db_flag):
    """获取视频phash值
    :param src_dir_path: 视频路径
    :param img_dir_path: 提取视频帧图像保存路径
    :param extract_time_point: 提取第几秒帧图像
    :param continue_flag: 是否继续上次进度 True 遇已存在图像则跳过  False 遇已存在图像则覆盖
    :param db_flag: 是否使用数据库数据 True 使用数据库数据  False 重新计算
    :return: video2phash_dict 视频文件和phash值对应信息,数据格式{video:phash,...}
    """
    video2phash_dict = {}  # 文件和phash值对应信息，数据格式{video:phash,...}
    if not os.path.exists(img_dir_path):  # 防止视频目录无视频时，提取不到图片导致后续计算图片相似度时找不到图片目录出错
        os.makedirs(img_dir_path)

    time_res = common_utils.get_times_now()
    time_str = time_res.get('time_str')
    time_start = time_res.get('timestamp')  # 开始时间
    self.scr.insert("end", "\n%s  计算视频phash值...\n" % time_str)

    # 获取数据库信息
    if db_flag:
        sql_video2phash_dict = image_utils.get_sql_res("videos")
    else:
        sql_video2phash_dict = {}

    # 获取视频文件信息
    video_list = common_utils.get_files_by_filetype(src_dir_path, 'video')
    file_infos = common_utils.get_files_info_by_list(video_list) 

    # 过滤数据库已有记录
    need_phash_file_infos = image_utils.get_need_phash(file_infos, sql_video2phash_dict, video2phash_dict)
    need_phash_video_list = list(need_phash_file_infos.keys())
    self.scr.insert("end", "\n%s  遍历完成，共有 %s 个视频文件 ( %s 个文件需要计算)\n" % (common_utils.get_times_now().get('time_str'), len(video_list), len(need_phash_file_infos)))
    # 有数据库没有的新视频信息才计算，如果视频目录都是数据库已有的视频文件，则不再提取视频帧，计算视频帧
    if len(need_phash_video_list):
        # 提取视频帧图像
        get_img_from_video_list(self, src_dir_path, img_dir_path, need_phash_video_list, extract_time_point, continue_flag)
        # 计算图片phash值
        img2phash_dict = image_utils.get_images_phash(self, img_dir_path, db_flag)
        # 通过获取的图片phash解析视频phash
        for photo_path in img2phash_dict:  # c:\xxx\1.mp4.jpg
            video_path = photo_path.replace("_%ssec.jpg" % extract_time_point, "")  # 'C:\\Users\\Na\\Pictures\\video_[相似视频]\\videoPhotos\\20240507_184539_00321【720p】.mp4'
            video_path = video_path.replace(img_dir_path, src_dir_path)
            video2phash_dict[video_path] = img2phash_dict[photo_path]
            need_phash_file_infos[video_path]['phash'] = img2phash_dict[photo_path]
    # logger.debug(need_phash_file_infos)
    # logger.debug("video2phash_dict:%s\n, need_phash_video_list:%s\n, sql_video2phash_dict:%s" % (video2phash_dict, need_phash_video_list, sql_video2phash_dict))
    msg = "\n%s  计算视频phash值完成!总共 %s 个文件,用时 %.3f 秒\n" % (common_utils.get_times_now().get('time_str'), len(video2phash_dict), time.time() - time_start)
    self.scr.insert("end", msg)
    # 记录到数据库
    if db_flag:
        image_utils.insert_db(need_phash_file_infos, 'videos')
    return video2phash_dict


def calc_video_sim(self, video2phash_dict, threshold):
    """计算视频相似度,带GUI组件交互"""
    time_res = common_utils.get_times_now()
    time_str = time_res.get('time_str')
    time_start = time_res.get('timestamp')
    self.scr.insert("end", "\n%s  开始计算相似度...\n" % time_str)
    # 新建进度条显示子线程
    self.is_complete = False  # 重置任务进度状态
    t = threading.Thread(target=self.show_rate_sim, args=(video2phash_dict,))
    t.daemon = True
    t.start()
    # 新建进度条显示子线程
    sim_dict = image_utils.calc_image_similarity(video2phash_dict, threshold)
    self.is_complete = True
    msg = "\n%s  计算相似度完成!用时 %.3f 秒\n" % (common_utils.get_times_now().get('time_str'), time.time() - time_start)
    self.scr.insert("end", msg)
    return sim_dict


def calc_video_sim4search(self, eg_video2phash_dict, dst_video2phash_dict, threshold):
    """计算视频相似度,适配以视频搜视频,带GUI组件交互"""
    time_res = common_utils.get_times_now()
    time_str = time_res.get('time_str')
    time_start = time_res.get('timestamp')
    self.scr.insert("end", "%s  开始计算相似度...\n" % time_str)
    # 新建进度条显示子线程
    self.is_complete = False  # 重置任务进度状态
    t = threading.Thread(target=self.show_rate_sim, args=(eg_video2phash_dict,))
    t.daemon = True
    t.start()
    # 计算相似度
    sim_dict = image_utils.calc_image_similarity4searchImg(eg_video2phash_dict, dst_video2phash_dict, threshold)
    self.is_complete = True
    msg = "\n%s  计算相似度完成!用时 %.3f 秒\n" % (common_utils.get_times_now().get('time_str'), time.time() - time_start)
    self.scr.insert("end", msg)
    return sim_dict


def find_sim_video(self, src_dir_path, dst_dir_path, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag):
    """查找相似视频"""
    start_time = common_utils.get_times_now().get('timestamp')  # 开始时间

    # 计算视频phash
    img_dir_path = os.path.join(dst_dir_path, "VideoImages")  # 提取的视频帧图像
    video2phash_dict = get_videos_phash(self, src_dir_path, img_dir_path, extract_time_point, continue_flag, db_flag)

    # 计算视频相似度
    sim_dict = calc_video_sim(self, video2phash_dict, threshold)
    
    self.scr.insert('end', '\n%s  开始操作文件...\n' % common_utils.get_times_now().get('time_str'))

    # 生成new_old_record
    new_old_record = image_utils.deal_image(sim_dict, src_dir_path, dst_dir_path)

    # 操作文件
    res = image_utils.move_files(deal_video_mode, new_old_record, dst_dir_path)
    total_msg = res['msg']
    self.record_path = res['record_path']
    msg = "查找相似视频完成!比对视频目录 %s ,总共发现相似视频 %s 个,用时 %.3f 秒" % (src_dir_path, len(new_old_record), time.time() - start_time)
    logger.info('【查找相似视频】  %s %s' % (msg, total_msg))
    self.scr.insert("end", "\n%s  %s\n\t%s\n" % (common_utils.get_times_now().get('time_str'), msg, total_msg))
    self.scr.see("end")
    if self.record_path:
        self.btn_restore.config(state='normal')
    self.btn_show.config(state='normal')
    mBox.showinfo("任务完成", "查找相似视频完成!")


def search_video(self, eg_dir_path, src_dir_path, save_dir_path, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag):
    """以视频搜相似视频"""
    start_time = common_utils.get_times_now().get('timestamp')  # 开始时间

    # 计算视频phash
    eg_img_dir = os.path.join(save_dir_path, "EgImages")
    src_img_dir = os.path.join(save_dir_path, "SrcImages")
    eg_video2phash_dict = get_videos_phash(self, eg_dir_path, eg_img_dir, extract_time_point, continue_flag, db_flag)
    dst_video2phash_dict = get_videos_phash(self, src_dir_path, src_img_dir, extract_time_point, continue_flag, db_flag)

    # 计算视频相似度
    sim_dict = calc_video_sim4search(self, eg_video2phash_dict, dst_video2phash_dict, threshold)

    self.scr.insert('end', '\n%s  开始操作文件...\n' % common_utils.get_times_now().get('time_str'))

    # 生成new_old_record
    new_old_record = image_utils.deal_image4SearchImg(sim_dict, save_dir_path)

    # 操作文件
    res = image_utils.move_files(deal_video_mode, new_old_record, save_dir_path)
    total_msg = res['msg']
    self.record_path = res['record_path']
    msg = "以视频搜相似视频完成!样本目录: %s ,源目录: %s ,总共发现相似视频 %s 个,用时 %.3f 秒" % (eg_dir_path, src_dir_path, len(new_old_record), time.time() - start_time)
    logger.info('【以视频搜相似视频】  %s %s' % (msg, total_msg))
    self.scr.insert("end", "\n\n%s  %s\n\t%s\n" % (common_utils.get_times_now().get('time_str'), msg, total_msg))
    self.scr.see("end")
    if self.record_path:
        self.btn_restore.config(state='normal')
    self.btn_show.config(state='normal')
    mBox.showinfo("任务完成", "以视频搜相似视频完成!")


def get_img_from_video_by_ffmpeg(pathIn='', pathOut='', extract_time_point=0, continue_flag=False):
    '''
    从视频提取单张图片
    :param pathIn: pathIn:视频文件的路径
    :param pathOut: 图片保存路径包含图片名
    :param extract_time_point: 提取的时间点
    :param continue_flag: 是否继续之前进度
    '''
    if continue_flag is True:
        if os.path.exists(pathOut):  # 继续之前进度
            return {'path': pathOut, 'flag': '已存在,跳过！'}
    # 使用ffmpeg获取视频时长
    dur = 0
    videoInfo = common_utils.get_video_info(pathIn)  # 视频信息
    if videoInfo:
        # 时长 秒,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
        dur = float(videoInfo.get('duration_sec'))
    if extract_time_point is not None:
        extract_time_point = float(extract_time_point)
        if extract_time_point < 0:  # 提取视频倒数第几秒图像
            extract_time_point += dur
        if extract_time_point > dur:  # 判断时间点是否符合要求
            # raise NameError('the max time point is larger than the video duration....')
            raise NameError('截取时间点超过视频总时长!')
            # return {'path': pathOut, 'flag': '截取时间点超过视频总时长！'}
        pathOutDir = os.path.dirname(pathOut)
        if not os.path.exists(pathOutDir):
            os.makedirs(pathOutDir)
        # 提取视频帧图像
        # command = [ffmpeg_path, '-ss', extract_time_point, '-i', pathIn, '-frames:v', '1', pathOut]
        command = [settings.FFMPEG_PATH, '-y', '-ss', str(extract_time_point), '-i', pathIn, '-frames:v', '1', pathOut]  # 命令
        subprocess.call(command, shell=True)

