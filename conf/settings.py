import os
import logging
import json
import sqlite3


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 默认配置信息
default_config = {"RECORD_DIR": "Record",
                  "SAFE_DEL_DIR": "SAFE_DEL",
                  "DB_DIR": "db",
                  "LOG_DIR": "log",
                  "SAFE_DEL_LOCAL": True,
                  "SAFE_FLAG": True,
                  "SKIP_FLAG": False,
                  "SYSTEM_CODE_TYPE": "GBK",
                  "FFMPEG_PATH": os.path.join(BASE_DIR, r"binaries\ffmpeg.exe"),
                  "IO_THREAD_NUM": 4,
                  "CALC_THREAD_NUM": 4
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
SAFE_DEL_DIR = config["SAFE_DEL_DIR"]  # 保存删除文件备份的目录
SYSTEM_CODE_TYPE = config["SYSTEM_CODE_TYPE"]  # 系统的编码格式，用于跟windnd配合解码拖拽的文件名
FFMPEG_PATH = os.path.abspath(os.path.join(BASE_DIR, r"binaries\ffmpeg.exe"))
if config.get('FFMPEG_PATH'):
    FFMPEG_PATH = config.get('FFMPEG_PATH')
IO_THREAD_NUM = config["IO_THREAD_NUM"]  # IO线程数，即提取视频帧图像时开启的线程数
CALC_THREAD_NUM = config["CALC_THREAD_NUM"]  # 计算线程数，即计算图片视频相似度时开启的线程数


# 创建目录
for _dir_path in [RECORD_DIR, DB_DIR, LOG_DIR]:
    if not os.path.exists(_dir_path):
        os.makedirs(_dir_path)


# 用于定义一些filetype没有收录的数据类型，根据文件名后缀判断
MIME_TYPES_EXTEND = {
    'ape': 'audio/ape',
    'md': 'text/markdown',
}

LOG_LEVEL = logging.WARNING  # 日志级别
LOG_TYPES = {
    'operate': 'operate.log',
    'error': 'error.log'
}

# 日志类型
LOG_PATH = {
    'operate': os.path.join(LOG_DIR, "operate.log"),  # 所有操作日志
    'error': os.path.join(LOG_DIR, "error.log"),  # 程序运行错误日志
}

DATABASE = {
    'engine': 'sqlite3',
    'name': 'accounts',
    'path': os.path.join(DB_DIR, "source.db")
}

# 创建图片表
image_table = '''CREATE TABLE if not exists images(
        id INTEGER PRIMARY KEY   AUTOINCREMENT NOT NULL,
        filename VARCHAR(260) NOT NULL,
        filesize INT,
        mtime FLOAT,
        phash VARCHAR(200),
        is_delete bit default 0
        );'''

# 创建视频表
video_table = '''CREATE TABLE if not exists videos(
        id INTEGER PRIMARY KEY   AUTOINCREMENT NOT NULL,
        filename VARCHAR(260) NOT NULL,
        filesize INT,
        mtime FLOAT,
        image_sec FLOAT,
        phash VARCHAR(200),
        is_delete bit default 0
        );'''

conn = sqlite3.connect(DATABASE['path'])
cur = conn.cursor()
# 创建表结构
for item in [image_table, video_table]:
    cur.execute(item)
conn.commit()
cur.close()  # 关闭数据库
conn.close()  # 关闭数据库


def export_config():
    """用于保存配置到文件"""
    conf_dir = os.path.dirname(configFile)
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)
    with open(configFile, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)  # 记录配置信息
        print(config)


def reset_config():
    if os.path.exists(configFile):  # 已有配置文件，则从配置文件中导入配置
        os.remove(configFile)
