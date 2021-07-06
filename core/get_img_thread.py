import cv2
import os
import time
import threading
import sys
from core import logger


video_dir_path = r""
img_dir_path = r""
frame_num = 90  # 记录要提取第几帧的图像
continue_flag = False  # 用来标记是否是继续上一次的工作
mutex = threading.Lock()  # 线程互斥锁
# 记录失败文件信息 数据为时间，错误信息，文件名 ，文件的帧数
failed_list = []  # 格式[(time, error, filename, frame_num),]
finished_num = 0  # 用来记录已经完成的个数


def get_img_by_list(video_list):
    """
    用于提取视频指定帧图像，并保存为图片
    :param video_list: 视频路径列表
    :return:
    """
    global finished_num
    for video_path in video_list:
        # 拼接图片保存路径
        save_path = video_path.replace(video_dir_path, img_dir_path)
        # save_path = os.path.splitext(save_path)[0] + '.jpg'  # 修改文件后缀
        save_path = save_path + '.jpg'  # 修改文件后缀
        if continue_flag:
            # 判断是否已有图像，有则提取下一个，用于继续上一次进度而不用从头覆盖
            if os.path.exists(save_path):
                continue
        # print(save_path)
        video_capture = cv2.VideoCapture(video_path)
        success, image = video_capture.read()  # 是否成功，帧图像数据
        n = 1  # n 用来标记目前读取到第几帧
        while n < frame_num:
            success, image = video_capture.read()
            n += 1
            if not success:
                print("视频:%s 只有%s帧，帧数不够！" % (video_path, n - 1))
                break

        # imwrite 保存中文路径和中文文件名会出现乱码
        # imag = cv2.imwrite(save_path, image)
        # if imag:
        #     print(save_path, "ok")

        try:
            cv2.imencode('.jpg', image)[1].tofile(save_path)
        except Exception as e:
            # print("image_type is %s " % type(image))
            # print("%s\n%s\n%s\n" % (e, save_path, video_path))
            local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            mutex.acquire()
            failed_list.append((local_time, e, video_path, n - 1))
            mutex.release()

        mutex.acquire()
        finished_num += 1  # 记录操作数
        mutex.release()


def init():
    global video_dir_path, img_dir_path, frame_num, continue_flag, failed_list, finished_num
    video_dir_path = ''
    img_dir_path = ''
    frame_num = 90
    continue_flag = False
    failed_list = []
    finished_num = 0


def show_rate(frame, total_count):
    global finished_num
    while True:
        print("now finish %s" % finished_num)
        frame.pb1["value"] = finished_num
        # print(rate_value)
        if finished_num >= total_count:
            frame.pb1["value"] = finished_num
            break


def run(window, videoDirPath, imgDirPath, frameNum, continueFlag, log_flag=True):
    init()
    global video_dir_path, img_dir_path, frame_num, continue_flag
    video_dir_path = videoDirPath
    img_dir_path = imgDirPath
    frame_num = frameNum
    continue_flag = continueFlag
    # 判断是否图片保存目录路径是否存在，不存在新建
    if not os.path.exists(img_dir_path):
        os.makedirs(img_dir_path)
    window.scr.insert("end", "正在遍历%s  ......\n" % video_dir_path)
    start_time = time.time()  # 记录开始时间
    video_list = []  # 用来保存目录下所有视频的路径
    for root, dirs, files in os.walk(video_dir_path):
        # 遍历文件夹，在img_dir_path 下新建和video_dir_path 一样的目录结构
        for file_dir in dirs:
            new_dir = os.path.join(root, file_dir).replace(video_dir_path, img_dir_path)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
        for item in files:
            video_list.append(os.path.join(root, item))
    total_count = len(video_list)
    window.pb1["maximum"] = total_count
    window.pb1["value"] = 0
    t0 = threading.Thread(target=show_rate, args=(window, total_count))  # 创建子进程用于更新进度条
    t0.start()
    get_video_time_msg = "遍历%s 完成！总共%s个文件,用时%.3fs" % (video_dir_path, total_count, (time.time() - start_time))
    print(get_video_time_msg)
    window.scr.insert("end", "%s\n正在提取视频第%s 帧图像......\n" % (get_video_time_msg, frame_num))
    process_name = sys.argv[0]  # 当前程序名称
    logger.proces_logger("%s\n\t%s" % (process_name, get_video_time_msg))
    sub_count = total_count // 5
    t1 = threading.Thread(target=get_img_by_list, args=(video_list[: sub_count],))
    t2 = threading.Thread(target=get_img_by_list, args=(video_list[sub_count: sub_count * 2],))
    t3 = threading.Thread(target=get_img_by_list, args=(video_list[sub_count * 2: sub_count * 3],))
    t4 = threading.Thread(target=get_img_by_list, args=(video_list[sub_count * 3: sub_count * 4],))

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    get_img_by_list(video_list[sub_count * 4:])
    threading_list = [t0, t1, t2, t3, t4]   # 线程列表 用来后面判断是否都结束了
    # while len(threading.enumerate()) > 1:
    while True:  # 因为在tkinter 里面加了一个多线程所以在这里数量变为2 否则会一直死循环 因为主线程是tkinter，然后一号子线程才是本模块的主线程
        # print("现有线程：", str(threading.enumerate()))   # 但是如果在tkinter中多创建几次子线程 这里还是会有问题
        if len(threading_list) == 0:
            break
        temp_list = threading_list[:]
        for item in threading_list:
            if item.is_alive():
                continue
            else:
                temp_list.remove(item)
                break
        threading_list = temp_list

    # 记录到日志文件
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
    total_msg = "提取目录%s 下视频第%s帧图像到目录%s 下,用时%.3fs" % (video_dir_path, frame_num, img_dir_path, time.time() - start_time)
    print(total_msg)
    window.scr.insert("end", "%s\n" % total_msg)
    # 将失败文件信息记录到日志
    if len(failed_list):
        failed_msg = "\t%s\n" % "总共有%s个视频提取图片失败!(格式:(time, error, filename, frame_num))：" % len(failed_list)
        window.scr.insert("end", failed_msg)
        if log_flag:
            logger.proces_logger(failed_msg)
        for item in failed_list:
            window.scr.insert("end", "\t%s\n" % str(item))
            if log_flag:
                logger.proces_logger("\t%s\n" % str(item), has_time=True)
    if log_flag:
        logger.proces_logger("\t%s\t%s" % (local_time, total_msg), has_time=True)
    return total_msg

