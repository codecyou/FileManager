from core import Mytools
from core import get_img_thread
from core import logger
from core import image_similarity_thread
import os
import time


def run(window, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
    print("video_similarity.py.run worked!")
    start_time = time.time()
    img_dir_path = os.path.join(dst_dir_path, "videoPhotos")
    same_img_path = os.path.join(dst_dir_path, "similarityPhoto")
    get_img_thread.run(window, src_dir_path, img_dir_path, frame_num, continue_flag, log_flag=False)
    # 比对视频帧图像相似度，并将符合相似度阈值的图片
    photo_video_record, msg = image_similarity_thread.run(window, img_dir_path, same_img_path, threshold, "copy", log_flag=False)
    src_list = []  # 用于记录相似视频原路径
    for src_path in photo_video_record.values():
        # src_list.append(os.path.splitext(src_path)[0].replace(img_dir_path, src_dir_path) + '.mp4')
        src_list.append(os.path.splitext(src_path)[0].replace(img_dir_path, src_dir_path))
    # print(src_list)
    record_path = Mytools.move_or_copy_file(src_list, src_dir_path, dst_dir_path, deal_video_mode, name_simple=False, log_flag=False)
    end_time = time.time()
    msg = "比对视频目录%s 总共发现相似视频%s个,用时%.3fs" % (src_dir_path, len(src_list), end_time - start_time)
    logger.proces_logger(msg)
    total_msg = "比对视频目录%s 总共发现相似视频%s个,相似视频%s到%s,视频新旧文件名记录到%s" % (src_dir_path, len(src_list), deal_video_mode, dst_dir_path, record_path)
    logger.operate_logger(total_msg)
    window.scr.insert("end", "%s\n%s\n" % (msg, total_msg))
    return msg
