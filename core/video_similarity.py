from core import Mytools
from core import logger
from core import image_similarity_thread
from conf import settings
import os
import time
import shutil
import cv2


def video2frames(window, pathIn='', pathOut='', extract_time_point=None, output_prefix='frame', continue_flag=False,
                 isColor=True):
    '''
    window： tk窗口对想
    pathIn：视频的路径，比如：F:\python_tutorials\test.mp4
    pathOut：设定提取的图片保存在哪个文件夹下，比如：F:\python_tutorials\frames1\。如果该文件夹不存在，函数将自动创建它
    extract_time_point：提取的时间点
    output_prefix：图片的前缀名，默认为frame，图片的名称将为frame_000001.jpg、frame_000002.jpg、frame_000003.jpg......
    isColor：如果为False，输出的将是黑白图片
    continue_flag: 是否继续之前进度
    '''
    input_extract_time_point = extract_time_point
    if input_extract_time_point < 0:  # 提取视频倒数第几秒图像
        img_path = os.path.join(pathOut, "{}_last{}sec.jpg".format(output_prefix, 0 - input_extract_time_point))
    else:
        img_path = os.path.join(pathOut, "{}_{}sec.jpg".format(output_prefix, extract_time_point))
    if continue_flag is True:
        if os.path.exists(img_path):  # 继续之前进度
            print(img_path, "已存在,跳过！")
            window.scr.insert("end", "%s 已存在,跳过！\n" % img_path)
            return

    cap = cv2.VideoCapture(pathIn)  # 打开视频文件
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # 视频的帧数
    fps = cap.get(cv2.CAP_PROP_FPS)  # 视频的帧率
    # dur = n_frames / fps  # 视频的时间
    try:
        dur = n_frames / fps  # 视频的时间
    except ZeroDivisionError:  # 如果文件不是视频文件或已损坏会报除0错误
        raise NameError('文件并非视频文件，或者文件损坏！!')

    if extract_time_point is not None:
        if extract_time_point < 0:  # 提取视频倒数第几秒图像
            extract_time_point = dur + extract_time_point
        if extract_time_point > dur:  # 判断时间点是否符合要求
            # raise NameError('the max time point is larger than the video duration....')
            raise NameError('截取时间点超过视频总时长!')
        try:
            if not os.path.exists(pathOut):
                os.makedirs(pathOut)
        except OSError:
            pass
        cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * extract_time_point))
        success, image = cap.read()
        if success:
            if not isColor:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转化为黑白图片
            print('Write a new frame: {}'.format(success))
            cv2.imencode('.jpg', image)[1].tofile(img_path)
            window.scr.insert("end", "%s 提取完成！\n" % img_path)
        else:
            raise NameError('文件数据异常!')


def get_img_by_sec(window, src_path, dst_path, extract_time_point, continue_flag):
    src_path = src_path.strip()
    dst_path = dst_path.strip()
    if isinstance(extract_time_point, str):
        extract_time_point = float(extract_time_point.strip())
    start_time = time.time()  # 程序开始时间

    # 遍历获取所有视频路径
    video_list = []
    for root, dirs, files in os.walk(src_path):
        for file in files:
            video_list.append(os.path.join(root, file))
    tmp_time = time.time()
    msg1 = "遍历%s完成，共发现文件%s个，用时%ss" % (src_path, len(video_list), tmp_time - start_time)
    print(msg1)
    window.scr.insert("end", "%s\n" % msg1)
    window.pb1["value"] = 0  # 重置进度条
    window.pb1["maximum"] = len(video_list)  # 总项目数

    # 提取所有视频的第n秒图像,单线程完成
    error_count = 0  # 记录操作失败个数
    for pathIn in video_list:
        pathOut = os.path.dirname(pathIn.replace(src_path, dst_path))
        try:
            video2frames(window, pathIn, pathOut, extract_time_point=extract_time_point,
                                output_prefix=os.path.basename(pathIn), continue_flag=continue_flag)
        except NameError as e:
            error_count += 1
            # print(pathIn, "the max time point is larger than the video duration!")
            error_msg = "【error:%s】%s,%s" % (error_count, pathIn, e)
            print(error_msg)
            window.scr.insert("end", "%s\n" % error_msg, "error_tag")
            window.scr.tag_config('error_tag', foreground="Crimson")
        window.pb1["value"] += 1
    complete_time = time.time()
    msg = "单线程提取图片完成，总文件数:%s" % len(video_list)
    if error_count:
        msg += "失败数:%s" % error_count
    msg += "提取图片用时%ss，总用时%ss" % (complete_time - tmp_time, complete_time - start_time)
    print(msg)
    window.scr.insert("end", "%s\n" % msg)


def run(window, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
    print("video_similarity.py.run worked!")
    start_time = time.time()
    new_old_record = {}  # 新旧文件路径记录
    record_path = None  # 记录new_old_path路径
    img_dir_path = os.path.join(dst_dir_path, "videoPhotos")  # 提取的视频帧图像
    same_img_path = os.path.join(dst_dir_path, "similarityPhoto")  # 相似图片目录
    # get_img_thread.run(window, src_dir_path, img_dir_path, frame_num, continue_flag, log_flag=False)
    get_img_by_sec(window, src_dir_path, img_dir_path, frame_num, continue_flag)
    # 比对视频帧图像相似度，并将符合相似度阈值的图片
    photo_video_record, msg, photo_video_record_path = image_similarity_thread.run(window, img_dir_path, same_img_path, threshold, "copy", log_flag=False)
    print(photo_video_record)
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
        msg = "比对视频目录%s 总共发现相似视频%s个,用时%.3fs" % (src_dir_path, len(new_old_record), end_time - start_time)
        total_msg = "比对视频目录%s 总共发现相似视频%s个,相似视频%s到%s,视频新旧文件名记录到%s" % (src_dir_path, len(new_old_record), deal_video_mode, dst_dir_path, record_path)
    else:
        msg = "比对视频目录%s 未发现相似视频！,用时%.3fs" % (src_dir_path, end_time - start_time)
        total_msg = "比对视频目录%s 未发现相似视频！" % src_dir_path

    logger.proces_logger(msg)
    logger.operate_logger(total_msg, log_time)
    window.scr.insert("end", "%s\n%s\n" % (msg, total_msg))
    window.scr.see("end")
    return msg, record_path
