""""用于以视频搜索相似视频"""
from conf import settings
from core import Mytools
from core import get_img_thread
from core import logger
from core import search_image
import os
import time
from core.video_similarity import video2frames, get_img_by_sec


def run(window, src_dir_path, dst_dir_path, save_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
    print("it worked!")
    record_path = None  # 记录new_old_record 路径
    start_time = time.time()
    src_img_dir = os.path.join(save_dir_path, "SearchPhotos")
    dst_img_dir = os.path.join(save_dir_path, "DstPhotos")
    same_img_path = os.path.join(save_dir_path, "similarityPhoto")
    # 按帧获取图像
    # get_img_thread.run(window, src_dir_path, src_img_dir, frame_num, continue_flag, log_flag=False)
    # get_img_thread.run(window, dst_dir_path, dst_img_dir, frame_num, continue_flag, log_flag=False)
    # 按秒数获取图像
    get_img_by_sec(window, src_dir_path, src_img_dir, frame_num, continue_flag)
    get_img_by_sec(window, dst_dir_path, dst_img_dir, frame_num, continue_flag)
    # 比对视频帧图像相似度，并将符合相似度阈值的图片
    photo_video_record, msg, photo_video_record_path = search_image.run(window, src_img_dir, dst_img_dir, same_img_path, threshold, "copy", log_flag=False)
    if deal_video_mode == "copy":
        func = Mytools.copy_file  # 拷贝方法
    else:
        func = Mytools.move_file
    new_old_record = {}  # 用于记录视频文件移动或者复制前后文件名
    failed_list = []  # 用于记录操作失败的文件信息
    print("photo_video_record:", photo_video_record)

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
    msg = "比对视频目录%s 总共发现相似视频%s个,用时%.3fs" % (src_dir_path, len(new_old_record), end_time - start_time)
    logger.proces_logger("%s\t%s\n" % (log_time, msg))
    window.scr.insert("end", "%s\n" % msg)
    if len(new_old_record):
        record_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("new_old_record", write_time))
        total_msg = "以视频搜视频完成！总共发现相似视频%s个,相似视频%s到%s,视频新旧文件名记录到%s" % (len(new_old_record), deal_video_mode, save_dir_path, record_path)
        Mytools.export_new_old_record(new_old_record, record_path)  # 将文件剪切前后文件信息导出到new_old_record
        if len(failed_list):
            failed_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("failed", write_time))
            total_msg += "\n\t\t%s个文件操作失败，文件信息导出到%s" % (len(failed_list), failed_path)
            with open(failed_path, 'a', encoding="utf-8") as f:
                for photo_path in failed_list:
                    f.write('%s\n' % photo_path)
    else:
        total_msg = "以视频搜视频完成！未发现相似视频！"
    logger.operate_logger(total_msg, log_time)
    window.scr.insert("end", "%s\n" % total_msg)
    window.scr.see("end")
    return total_msg, record_path
