#! /usr/bin/python3
# __author__:"surfread"
import os
import logging
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 默认配置信息
default_config = {"RECORD_DIR": "dir",
                  "SAFE_DEL_DIR": "safe_del",
                  "DB_DIR": "db",
                  "LOG_DIR": "log",
                  "SAFE_DEL_LOCAL": True,
                  "SAFE_FLAG": True,
                  "SKIP_FLAG": False,
                  "SYSTEM_CODE_TYPE": "gbk",
                  "RESTORE_RECORD_PATH": "restore_record.txt",
                  "DEL_RECORD_PATH": "del_record.txt",
                  "CHANGE_TIMESTAMP_RECORD_PATH": "change_timestamp_record.txt",
                  "FFMPEG_PATH": os.path.join(BASE_DIR, "imageio_ffmpeg/binaries/ffmpeg-win64-v4.2.2.exe")
                  }

# 读取配置信息
configFile = os.path.join(BASE_DIR, 'conf', 'config.json')  # 配置文件路径
lastest_config = ''  # 用于保存当前配置，即修改前的最新配置信息
if os.path.exists(configFile):  # 已有配置文件，则从配置文件中导入配置
    try:
        with open(os.path.join(BASE_DIR, 'conf', 'config.json'), 'r', encoding='utf-8') as f:
            config = json.load(f)  # 记录配置信息
    except Exception:
        os.remove(configFile)
        config = default_config
else:  # 无配置文件，则使用默认配置
    config = default_config

RECORD_DIR = os.path.join(BASE_DIR, config["RECORD_DIR"])  # 保存记录的目录
DB_DIR = os.path.join(BASE_DIR, config["DB_DIR"])  # 保存数据相关的目录
LOG_DIR = os.path.join(BASE_DIR, config["LOG_DIR"])  # 保存日志的目录
SAFE_DEL_LOCAL = config["SAFE_DEL_LOCAL"]  # 标记是否在文件所在分区创建safe_del文件夹，False 在程序目录下创建safe_del文件夹
SAFE_FLAG = config["SAFE_FLAG"]  # 标记执行文件删除操作时是否使用安全删除选项(安全删除选项会将被删除的文件剪切到safe_del目录下)
SKIP_FLAG = config["SKIP_FLAG"]  # 标记执行文件复制或者粘贴操作时是否遇见同名同路径文件是否跳过选项(True跳过 False覆盖)
if SAFE_DEL_LOCAL:
    SAFE_DEL_DIR = config["SAFE_DEL_DIR"]  # 保存删除文件备份的目录
else:
    SAFE_DEL_DIR = os.path.join(BASE_DIR, "SAFE_DEL_DIR")  # 保存删除文件备份的目录
SYSTEM_CODE_TYPE = config["SYSTEM_CODE_TYPE"]  # 系统的编码格式，用于跟windnd配合解码拖拽的文件名
RESTORE_RECORD_PATH = os.path.join(RECORD_DIR, config["RESTORE_RECORD_PATH"])  # 文件还原记录
DEL_RECORD_PATH = os.path.join(RECORD_DIR, config["DEL_RECORD_PATH"])  # 文件删除记录
CHANGE_TIMESTAMP_RECORD_PATH = os.path.join(RECORD_DIR, config["CHANGE_TIMESTAMP_RECORD_PATH"])  # 修改时间戳
FFMPEG_PATH = os.path.abspath(os.path.join(BASE_DIR, "imageio_ffmpeg/binaries/ffmpeg-win64-v4.2.2.exe"))
if config.get('FFMPEG_PATH'):
    FFMPEG_PATH = config.get('FFMPEG_PATH')
JPG_TYPE = ['.jpg', '.cr2', '.jpeg']  # 照片类型

# 日志类型
LOG_PATH = {
    'backup_info': os.path.join(LOG_DIR, "backup_info.log"),  # 文件同步备份详情日志
    'process': os.path.join(LOG_DIR, "process.log"),  # 程序运行进程信息详情
    'operate': os.path.join(LOG_DIR, "operate.log"),  # 所有操作日志
    'dialog': os.path.join(LOG_DIR, "dialog.log"),  # 聊天机器人对话记录日志
    'update': os.path.join(LOG_DIR, "update.log"),  # 聊天机器人语料库更新日志
    'error': os.path.join(LOG_DIR, "error.log"),  # 程序运行错误日志
    'file_error': os.path.join(LOG_DIR, "file_error.log")  # 拷贝或复制文件错误日志
}

DATABASE = {
    'engine': 'mysql',
    'name': 'accounts',
    'path': os.path.join(DB_DIR, "mysql")
}


LOG_LEVEL = logging.WARNING
LOG_TYPES = {
    'backup_info': 'backup_info.log',
    'process': 'process.log',
    'operate': 'operate.log',
    'dialog.log': 'dialog.log',
    'update': 'update.log',
    'error': 'error.log'
}


def save_lastest_config():
    """用于保存修改前的最新配置信息"""
    global lastest_config
    lastest_config = config


def get_config_list():
    """用于获取修改前后的设置信息，并返回一个list"""
    return [lastest_config, config]


def export_config():
    """用于保存配置到文件"""
    source_config()
    conf_dir = os.path.dirname(configFile)
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)
    with open(configFile, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)  # 记录配置信息
        print(config)


def reset_config():
    """用于恢复默认设置"""
    global config
    config = default_config  # 重置config
    source_settings()  # 更新所有设置的值
    if os.path.exists(configFile):
        os.remove(configFile)


def source_config():
    """用于重新生成config数据"""
    global config
    config = {"RECORD_DIR": os.path.basename(RECORD_DIR),
              "SAFE_DEL_DIR": SAFE_DEL_DIR,
              "DB_DIR": os.path.basename(DB_DIR),
              "LOG_DIR": os.path.basename(LOG_DIR),
              "SAFE_DEL_LOCAL": SAFE_DEL_LOCAL,
              "SAFE_FLAG": SAFE_FLAG,
              "SKIP_FLAG": SKIP_FLAG,
              "SYSTEM_CODE_TYPE": SYSTEM_CODE_TYPE,
              "RESTORE_RECORD_PATH": os.path.basename(RESTORE_RECORD_PATH),
              "DEL_RECORD_PATH": os.path.basename(DEL_RECORD_PATH),
              "CHANGE_TIMESTAMP_RECORD_PATH": os.path.basename(CHANGE_TIMESTAMP_RECORD_PATH),
              "FFMPEG_PATH": FFMPEG_PATH
              }


def source_settings():
    """用于重新更新设置参数"""
    global RECORD_DIR, RESTORE_RECORD_PATH, SYSTEM_CODE_TYPE, SAFE_FLAG, SKIP_FLAG, SAFE_DEL_LOCAL, SAFE_DEL_DIR, DB_DIR, LOG_DIR, DEL_RECORD_PATH, CHANGE_TIMESTAMP_RECORD_PATH, FFMPEG_PATH
    RECORD_DIR = os.path.join(BASE_DIR, config["RECORD_DIR"])  # 保存记录的目录
    DB_DIR = os.path.join(BASE_DIR, config["DB_DIR"])  # 保存数据相关的目录
    LOG_DIR = os.path.join(BASE_DIR, config["LOG_DIR"])  # 保存日志的目录
    SAFE_DEL_LOCAL = config["SAFE_DEL_LOCAL"]  # 标记是否在文件所在分区创建safe_del文件夹，False 在程序目录下创建safe_del文件夹
    SAFE_FLAG = config["SAFE_FLAG"]  # 标记执行文件删除操作时是否使用安全删除选项(安全删除选项会将被删除的文件剪切到safe_del目录下)
    SKIP_FLAG = config["SKIP_FLAG"]  # 标记执行文件复制或者粘贴操作时是否遇见同名同路径文件是否跳过选项(True跳过 False覆盖)
    if SAFE_DEL_LOCAL:
        SAFE_DEL_DIR = config["SAFE_DEL_DIR"]  # 保存删除文件备份的目录
    else:
        SAFE_DEL_DIR = os.path.join(BASE_DIR, "SAFE_DEL_DIR")  # 保存删除文件备份的目录
    SYSTEM_CODE_TYPE = config["SYSTEM_CODE_TYPE"]  # 系统的编码格式，用于跟windnd配合解码拖拽的文件名
    RESTORE_RECORD_PATH = os.path.join(RECORD_DIR, config["RESTORE_RECORD_PATH"])  # 文件还原记录
    DEL_RECORD_PATH = os.path.join(RECORD_DIR, config["DEL_RECORD_PATH"])  # 文件删除记录
    CHANGE_TIMESTAMP_RECORD_PATH = os.path.join(RECORD_DIR, config["CHANGE_TIMESTAMP_RECORD_PATH"])  # 修改时间戳
    FFMPEG_PATH = config["FFMPEG_PATH"]
