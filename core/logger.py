# 提供所有的日志方法
import logging
import os
from conf import settings


log_dir = settings.LOG_DIR
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

"""创建日志对象"""
# 第一步，创建一个logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Log等级总开关

# 第二步，创建一个handler，用于写入日志文件
logfile = os.path.join(log_dir, "operate.log")
fh = logging.FileHandler(logfile, mode='a', encoding='utf-8')  # open的打开模式这里可以进行参考
fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关

# 第三步，再创建一个handler，用于输出到控制台
ch = logging.StreamHandler()
# ch.setLevel(logging.WARNING)  # 输出到console的log等级的开关
ch.setLevel(settings.LOG_LEVEL)  # 输出到console的log等级的开关

# 第四步，定义handler的输出格式
formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")

fh.setFormatter(formatter)
ch.setFormatter(formatter)

# 第五步，将logger添加到handler里面
logger.addHandler(fh)
logger.addHandler(ch)
