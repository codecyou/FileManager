from core import Mytools
from core import logger
from core import ImageTools
from conf import settings
import os
import time
import shutil
import subprocess
import re
import threading
import cv2
from decimal import Decimal
from tkinter import messagebox as mBox
# 开启静默模式不弹cmd窗口
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE


def get_float_value(key, default_value):
    """用于获取输入框中的值，如果不输入则返回默认值"""
    if key:
        try:
            key = float(key)
        except Exception:
            key = default_value
    else:
        key = default_value
    return key


def get_int_value(key, default_value):
    """用于获取输入框中的值，如果不输入则返回默认值"""
    if key:
        try:
            key = int(key)
        except Exception:
            key = default_value
    else:
        key = default_value
    return key


def millisecToAssFormat(t):  # 取时间
    if t < 3600:
        h = 00
    else:
        h = t // 3600
    s = t % 60
    m = t // 60 - h * 60
    # return '%02d:%02d:%02d' % (h, m, s)
    return '%02d:%02d:%05.2f' % (h, m, s)  # 小数点占一位


def get_video_length(ffmpeg_path, file):
    """
    获取视频的 duration 时长 长 宽
    """
    # 开启静默模式不弹cmd窗口
    # process = subprocess.Popen([self.ffmpeg_path, '-i', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # startupinfo = subprocess.STARTUPINFO()
    # startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
    # startupinfo.wShowWindow = subprocess.SW_HIDE
    process = subprocess.Popen([ffmpeg_path, '-i', file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startupinfo)
    stdout, stderr = process.communicate()
    # print(stdout)
    pattern_duration = re.compile(r"Duration:\s(\d+?):(\d+?):(\d+\.\d+?),")
    pattern_size = re.compile(r",\s(\d{3,4})x(\d{3,4})")
    matches = re.search(pattern_duration, stdout.decode('utf-8'))
    size = re.search(pattern_size, stdout.decode('utf-8'))
    result = {
            'total': 0,
            'width': 0,
            'height': 0
        }
    if size:
        size = size.groups()
        # print(size)
        width = size[0]
        height = size[1]
        result['width'] = width
        result['height'] = height
    if matches:
        matches = matches.groups()
        # print(matches)
        hours = Decimal(matches[0])
        minutes = Decimal(matches[1])
        seconds = Decimal(matches[2])  # 处理为十进制，避免小数点报错
        total = 0
        total += 60 * 60 * hours
        total += 60 * minutes
        total += seconds
        result['total'] = total
    return result


def show_rate_calc(win, cal_res, total_count):
    """
    显示计算进度或者操作文件进度进度条
    :param win: GUI窗口对象
    :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    :param total_count: 总文件数
    """
    win.pb1["maximum"] = total_count
    win.pb1["value"] = 0
    while True:
        finished_num = cal_res['count']
        # print("now finish %s" % finished_num)
        win.pb1["value"] = finished_num
        print('finished_num: {}, total_count: {}'.format(finished_num, total_count))
        if finished_num >= total_count:  # 通过判断计算次数
            win.pb1["value"] = total_count
            break
        time.sleep(0.05)
    print('显示计算进度条子线程退出！')


def video2frames(win, pathIn='', pathOut='', extract_time_point=0, output_prefix='frame', continue_flag=False,
                 isColor=True):
    '''
    从视频提取单张图片
    :param win: tk窗口对想
    :param pathIn: pathIn：视频文件的路径
    :param pathOut: 图片保存路径包含图片名
    :param extract_time_point: 提取的时间点
    :param output_prefix: 图片的前缀名，默认为frame，图片的名称将为frame_000001.jpg、frame_000002.jpg、frame_000003.jpg......
    :param isColor: 如果为False，输出的将是黑白图片
    :param continue_flag: 是否继续之前进度
    '''
    input_extract_time_point = extract_time_point
    pathOutDir = os.path.dirname(pathOut)
    if input_extract_time_point < 0:  # 提取视频倒数第几秒图像
        img_path = os.path.join(pathOutDir, "{}_last{}sec.jpg".format(output_prefix, 0 - input_extract_time_point))
    else:
        img_path = os.path.join(pathOutDir, "{}_{}sec.jpg".format(output_prefix, extract_time_point))
    if continue_flag is True:
        if os.path.exists(img_path):  # 继续之前进度
            print(img_path, "已存在,跳过！")
            win.scr.insert("end", "%s 已存在,跳过！\n" % img_path)
            return
    cap = cv2.VideoCapture(pathIn)  # 打开视频文件
    # 使用opencv计算视频时长，较慢
    # n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # 视频的帧数
    # fps = cap.get(cv2.CAP_PROP_FPS)  # 视频的帧率
    # try:
    #     dur = n_frames / fps  # 视频的时间
    # except ZeroDivisionError:  # 如果文件不是视频文件或已损坏会报除0错误
    #     raise NameError('文件并非视频文件，或者文件损坏！!')
    # 使用ffmpeg获取视频时长
    dur = 0
    videoInfo = get_video_length(settings.FFMPEG_PATH, pathIn)  # 视频信息
    if videoInfo:
        # 时长 秒,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
        dur = float(videoInfo.get('total'))
    if extract_time_point is not None:
        if extract_time_point < 0:  # 提取视频倒数第几秒图像
            extract_time_point = dur + extract_time_point
        if extract_time_point > dur:  # 判断时间点是否符合要求
            # raise NameError('the max time point is larger than the video duration....')
            raise NameError('截取时间点超过视频总时长!')
        try:
            if not os.path.exists(pathOutDir):
                os.makedirs(pathOutDir)
        except OSError:
            pass
        cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * extract_time_point))
        success, image = cap.read()
        if success:
            if not isColor:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转化为黑白图片
            print('Write a new frame: {}'.format(success))
            cv2.imencode('.jpg', image)[1].tofile(img_path)
            win.scr.insert("end", "%s 提取完成！\n" % img_path)
        else:
            raise NameError('文件数据异常!')


def get_img_by_sec(win, src_dir, dst_dir, extract_time_point, continue_flag):
    """单线程从视频提取图片"""
    src_dir = src_dir.strip()
    dst_dir = dst_dir.strip()
    if isinstance(extract_time_point, str):
        extract_time_point = float(extract_time_point.strip())
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_time = time_res.get('timestamp')
    win.scr.insert("end", "%s  开始遍历文件目录....\n" % time_str)
    # 遍历获取所有视频路径
    video_list = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            video_list.append(os.path.join(root, file))
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    tmp_time = time_res.get('timestamp')
    msg1 = "遍历%s完成，共发现文件%s个，用时%ss" % (src_dir, len(video_list), tmp_time - start_time)
    # print(msg1)
    win.scr.insert("end", "\n%s  %s\n\t开始提取视频图像....\n" % (time_str, msg1))
    win.pb1["value"] = 0  # 重置进度条
    win.pb1["maximum"] = len(video_list)  # 总项目数
    # 提取所有视频的第n秒图像,单线程完成
    error_count = 0  # 记录操作失败个数
    failed_dict = {}  # 记录失败文件信息 ， 数据格式 {filepath: errormsg,}
    for pathIn in video_list:
        pathOut = pathIn.replace(src_dir, dst_dir)
        output_prefix = os.path.basename(pathIn)
        try:
            video2frames(win, pathIn, pathOut, extract_time_point=extract_time_point, output_prefix=output_prefix, continue_flag=continue_flag)
        except NameError as e:
            error_count += 1
            failed_dict[pathIn] = e
            error_msg = "【error:%s】%s,%s" % (error_count, pathIn, e)
            print(error_msg)
            win.scr.insert("end", "%s\n" % error_msg, "error_tag")
            win.scr.tag_config('error_tag', foreground="Crimson")
        win.pb1["value"] += 1
        win.scr.see('end')
    # 输出显示操作失败信息
    if len(failed_dict):
        win.scr.insert("end", "\n操作 %s 个文件失败，失败信息如下：\n" % error_count, 'info')
        i = 0  # 记录文件编号
        for filepath in failed_dict:
            i += 1
            win.scr.insert("end","ERROR:(%s/%s)  %s 操作过程出错！错误：%s\n" % (i, error_count, filepath, failed_dict[filepath]),'error')
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    complete_time = time_res.get('timestamp')
    msg = "单线程提取图片完成，总文件数: %s" % len(video_list)
    if error_count:
        msg += "失败数:%s" % error_count
    msg += "提取图片用时%ss，总用时%ss" % (complete_time - tmp_time, complete_time - start_time)
    print(msg)
    total_msg = "提取目录 %s 下视频第 %s 秒图像到目录 %s 下完成！用时%.3fs" % (src_dir, extract_time_point, dst_dir, time.time() - start_time)
    win.scr.insert("end", "\n\n%s  %s\n" % (time_str, msg))
    win.scr.tag_config('info', font=('microsoft yahei', 16, 'bold'))
    win.scr.tag_config('error', foreground="FireBrick")
    win.scr.see('end')
    logger.operate_logger('【提取视频帧图像操作】  %s' % total_msg, time_str)
    mBox.showinfo('完成！', msg)


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
        pathOut = pathIn.replace(src_path, dst_path) + '_{}sec.jpg'.format(extract_time_point)
        if extract_time_point < 0:  # 截取时间点输入为负值则表示倒数时间
            pathOut = pathIn.replace(src_path, dst_path) + '_last{}sec.jpg'.format(0-extract_time_point)
            # 获取视频信息， 实测多线程使用ffmpeg获取视频时长反而更快
            duration = 0
            videoInfo = get_video_length(settings.FFMPEG_PATH, pathIn)  # 视频信息
            if videoInfo:
                # 时长 秒,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
                duration = float(videoInfo.get('total'))
            extract_time_point += duration
        try:
            if continue_flag:  # 如果选中继续上次进度，则目标目录已有同名图片时会跳过，否则会覆盖
                if os.path.exists(pathOut):
                    continue
            cap = cv2.VideoCapture(pathIn)  # 打开视频文件
            cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * extract_time_point))
            success, image = cap.read()
            if success:
                cv2.imencode('.jpg', image)[1].tofile(pathOut)
                # window.scr.insert("end", "%s 提取完成！\n" % img_path)
            else:
                raise NameError('文件数据异常!')
        except Exception as e:
            print(e)
            failed_list.append(pathIn)
    if len(failed_list):
        mutex.acquire()
        cal_res['failed_files'].extend(failed_list)
        mutex.release()
    print('子线程结束！')


def get_img_from_video(win, src_dir, dst_dir, extract_time_point, continue_flag, log_flag=True):
    """从视频中提取图片
    """
    mutex = threading.Lock()  # 创建互斥锁
    cal_res = {'count': 0, 'failed_files': []}  # 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
    # 判断是否图片保存目录路径是否存在，不存在新建
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    time_str = Mytools.get_time_now().get('time_str')
    win.scr.insert("end", "%s  正在遍历%s  ......\n" % (time_str, src_dir))
    start_time = time.time()  # 记录开始时间
    video_list = []  # 用来保存目录下所有视频的路径
    for root, dirs, files in os.walk(src_dir):
        # 遍历文件夹，在img_dir_path 下新建和video_dir_path 一样的目录结构
        for file_dir in dirs:
            new_dir = os.path.join(root, file_dir).replace(src_dir, dst_dir)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
        for item in files:
            video_list.append(os.path.join(root, item))
    total_count = len(video_list)
    win.pb1["maximum"] = total_count
    win.pb1["value"] = 0
    t0 = threading.Thread(target=show_rate_calc, args=(win, cal_res, total_count))  # 创建子进程用于更新进度条
    t0.setDaemon(True)
    t0.start()
    time_str = Mytools.get_time_now().get('time_str')
    get_video_time_msg = "%s  遍历%s 完成！总共 %s 个文件,用时%.3fs" % (time_str, src_dir, total_count, (time.time() - start_time))
    win.scr.insert('end', '{}\n正在提取视频帧图像...'.format(get_video_time_msg))
    if len(video_list) > 20:
        sub_count = total_count // 5
        t1 = threading.Thread(target=get_img_thread, args=(video_list[: sub_count], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex))
        t2 = threading.Thread(target=get_img_thread, args=(video_list[sub_count: sub_count * 2], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex))
        t3 = threading.Thread(target=get_img_thread, args=(video_list[sub_count * 2: sub_count * 3], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex))
        t4 = threading.Thread(target=get_img_thread, args=(video_list[sub_count * 3: sub_count * 4], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex))
        get_img_thread(video_list[sub_count * 4:], src_dir, dst_dir, extract_time_point, continue_flag, cal_res, mutex)
        thread_list = [t1, t2, t3, t4]   # 线程列表 用来后面判断是否都结束了
        for t in thread_list:
            t.setDaemon(True)
            t.start()
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
    local_time = Mytools.get_time_now().get('time_str')
    total_msg = "提取目录 %s 下视频第 %s 秒图像到目录 %s 下完成！用时%.3fs" % (src_dir, extract_time_point, dst_dir, time.time() - start_time)
    print(total_msg)
    win.scr.insert("end", "\n\n%s  %s\n" % (time_str, total_msg))
    win.scr.see('end')
    # 将失败文件信息记录到日志
    if len(cal_res['failed_files']):
        failed_msg = "\t%s\n" % "总共有 %s 个视频提取图片失败!" % len(cal_res['failed_files'])
        win.scr.insert("end", failed_msg)
        for item in cal_res['failed_files']:
            win.scr.insert("end", "\t%s\n" % str(item))
    win.scr.see('end')
    if log_flag:
        logger.operate_logger('【提取视频帧图像操作】  %s' % total_msg, local_time)
    return total_msg


def find_sim_video(window, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
    """查找相似视频"""
    new_old_record = {}  # 新旧文件路径记录
    record_path = None  # 记录new_old_path路径
    img_dir_path = os.path.join(dst_dir_path, "videoPhotos")  # 提取的视频帧图像
    same_img_path = os.path.join(dst_dir_path, "similarityPhoto")  # 相似图片目录
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_time = time_res.get('timestamp')  # 开始时间
    window.scr.insert('end', '%s  开始提取视频图像...\n' % time_str)
    get_img_from_video(window, src_dir_path, img_dir_path, frame_num, continue_flag, log_flag=False)
    # 比对视频帧图像相似度，并将符合相似度阈值的图片
    time_str = Mytools.get_time_now().get('time_str')
    window.scr.insert('end', '\n%s  比对视频帧图像相似度...\n' % time_str)
    if not os.path.exists(img_dir_path):  # 防止视频目录无视频时，提取不到图片导致后续计算图片相似度时找不到图片目录出错
        os.makedirs(img_dir_path)
    photo_video_record, msg, photo_video_record_path = ImageTools.find_sim_img(window, img_dir_path, same_img_path, threshold, "copy", log_flag=False)
    print(photo_video_record)
    time_str = Mytools.get_time_now().get('time_str')
    window.scr.insert('end', '\n%s  比对视频帧图像相似度完成，开始操作文件...\n' % time_str)
    # 根据photo_video_record 数据生成new_old_record
    for photo_path in photo_video_record:  # c:\xxx\1.mp4.jpg
        # 去除"_3sec"
        video_path = photo_path.replace("_%ssec.jpg" % frame_num, "")
        # 拼接新video路径c:\xxx\S1__1[xx].mp4
        new_path = os.path.splitext(video_path)[0].replace(same_img_path, dst_dir_path)
        # 避免出现 new20210326080616.mp4.jpg_[new - 副本]
        if not new_path.endswith(".mp4"):
            new_path += ".mp4"
        # 获得原video路径c:\xxx\1.mp4
        old_video_path = photo_video_record[photo_path].replace("_%ssec.jpg" % frame_num, "")
        new_old_record[new_path] = old_video_path.replace(img_dir_path, src_dir_path)

    # 拷贝或剪切相似视频
    for new_file in new_old_record:
        old_file = new_old_record[new_file]
        # print(old_file)
        if deal_video_mode == "copy":
            shutil.copy2(old_file, new_file)
        else:
            shutil.move(old_file, new_file)

    log_time = ''  # 记录操作时间
    end_time = time.time()
    if len(new_old_record):
        write_time, log_time = Mytools.get_times()  # 获取两种当前时间字符串
        record_path = os.path.join(settings.RECORD_DIR, 'new_old_record %s.txt' % write_time)
        Mytools.export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        msg = "比对视频目录 %s 总共发现相似视频 %s 个,用时%.3fs" % (src_dir_path, len(new_old_record), end_time - start_time)
        total_msg = "比对视频目录 %s 总共发现相似视频 %s 个,相似视频 %s 到 %s,视频新旧文件名记录到%s" % (src_dir_path, len(new_old_record), deal_video_mode, dst_dir_path, record_path)
    else:
        msg = "比对视频目录 %s 未发现相似视频！,用时%.3fs" % (src_dir_path, end_time - start_time)
        total_msg = "比对视频目录 %s 未发现相似视频！" % src_dir_path

    logger.proces_logger(msg)
    logger.operate_logger('【查找相似视频】  %s' % total_msg, log_time)
    window.scr.insert("end", "\n\n%s  %s\n%s\n" % (log_time, msg, total_msg))
    window.scr.see("end")
    return msg, record_path


def search_video(window, src_dir_path, dst_dir_path, save_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
    """以视频搜相似视频"""
    record_path = None  # 记录new_old_record 路径
    time_res = Mytools.get_time_now()
    time_str = time_res.get('time_str')
    start_time = time_res.get('timestamp')  # 开始时间
    src_img_dir = os.path.join(save_dir_path, "SearchPhotos")
    dst_img_dir = os.path.join(save_dir_path, "DstPhotos")
    same_img_path = os.path.join(save_dir_path, "similarityPhoto")
    # 按秒数获取图像
    window.scr.insert("end", "%s  开始提取视频帧图像...\n" % time_str)
    get_img_from_video(window, src_dir_path, src_img_dir, frame_num, continue_flag, log_flag=False)
    get_img_from_video(window, dst_dir_path, dst_img_dir, frame_num, continue_flag, log_flag=False)
    # 比对视频帧图像相似度，并将符合相似度阈值的图片
    time_str = Mytools.get_time_now().get('time_str')
    window.scr.insert("end", "\n%s  开始比对视频帧图像相似度...\n" % time_str)
    for item in [src_img_dir, dst_img_dir]:
        if not os.path.exists(item):  # 防止视频目录无视频时，提取不到图片导致后续计算图片相似度时找不到图片目录出错
            os.makedirs(item)
    photo_video_record, msg, photo_video_record_path = ImageTools.search_img_by_img(window, src_img_dir, dst_img_dir, same_img_path, threshold, "copy", log_flag=False)
    if deal_video_mode == "copy":
        func = Mytools.copy_file  # 拷贝方法
    else:
        func = Mytools.move_file
    new_old_record = {}  # 用于记录视频文件移动或者复制前后文件名
    failed_list = []  # 用于记录操作失败的文件信息
    print("photo_video_record:", photo_video_record)
    time_str = Mytools.get_time_now().get('time_str')
    window.scr.insert("end", "\n%s  比对视频帧图像相似度完成，开始操作文件...\n" % time_str)
    # 根据photo_video_record 数据生成new_old_record
    # 获取原视频目录描述字符串，用来记录原文件的目录结构 格式"C_Users_pro_PycharmProjects"
    src_dir_str = Mytools.get_dir_str(src_dir_path)
    dst_dir_str = Mytools.get_dir_str(dst_dir_path)
    src_img_dir_str = Mytools.get_dir_str(src_img_dir)
    dst_img_dir_str = Mytools.get_dir_str(dst_img_dir)
    for photo_path in photo_video_record:  # c:\xxx\1.mp4.jpg
        # 拼接新video路径c:\xxx\S1__1[xx].mp4
        new_path = photo_path.replace("_%ssec.jpg" % frame_num, "")
        new_path = os.path.splitext(new_path)[0].replace(same_img_path, save_dir_path)
        # 拼接原video路径
        old_path = photo_video_record[photo_path].replace("_%ssec.jpg" % frame_num, "")
        if old_path.startswith(src_img_dir):
            # 替换目录描述字符串
            new_path = new_path.replace(src_img_dir_str, src_dir_str)
            # 获得原video路径c:\xxx\1.mp4
            old_path = old_path.replace(src_img_dir, src_dir_path)
        else:
            new_path = new_path.replace(dst_img_dir_str, dst_dir_str)
            # 获得原video路径c:\xxx\1.mp4
            old_path = old_path.replace(dst_img_dir, dst_dir_path)
        # 避免出现 new20210326080616.mp4.jpg_[new - 副本]
        if not new_path.endswith(".mp4"):
            new_path += ".mp4"

        # 操作文件
        try:
            func(old_path, new_path)
        except Exception as e:
            failed_list.append(old_path)
            print("操作%s文件失败，详情请查看错误日志！" % old_path)
            # logger.error_logger(e)
            logger.file_error_logger(old_path, e)
        else:
            new_old_record[new_path] = old_path

    end_time = time.time()
    write_time, log_time = Mytools.get_times()  # 获取当前时间的两种格式
    msg = "比对视频目录 %s 总共发现相似视频 %s 个,用时%.3fs" % (src_dir_path, len(new_old_record), end_time - start_time)
    logger.proces_logger("%s\t%s\n" % (log_time, msg))
    window.scr.insert("end", "\n%s  %s\n" % (log_time, msg))
    if len(new_old_record):
        record_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("new_old_record", write_time))
        total_msg = "以视频搜视频完成！总共发现相似视频 %s 个,相似视频 %s 到 %s,视频新旧文件名记录到 %s" % (len(new_old_record), deal_video_mode, save_dir_path, record_path)
        Mytools.export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("failed", write_time))
            total_msg += "\n\t\t%s 个文件操作失败，文件信息导出到 %s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for photo_path in failed_list:
                    f.write('%s\n' % photo_path)
    else:
        total_msg = "以视频搜视频完成！未发现相似视频！"
    logger.operate_logger('【以视频搜相似视频】  %s' % total_msg, log_time)
    window.scr.insert("end", "\n\n%s  %s\n" % (log_time, total_msg))
    window.scr.see("end")
    return total_msg, record_path
