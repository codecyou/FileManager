import os
import sys
import threading
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from bin.MainPage import *


# def show_childThread():
# 	"""显示当前线程数"""
# 	while True:
# 		print("当前线程数：%s" % threading.active_count())
#
#
# threading.Thread(target=show_childThread).start()

Mytools.my_init()  # 初始化程序运行环境，创建对应的文件目录
# 创建GUI窗体
root = tk.Tk()
root.title('FileManager     design by wyl')
MainPage(root)
root.mainloop()
