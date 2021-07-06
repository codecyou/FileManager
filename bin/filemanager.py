import os
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from bin.MainPage import *


Mytools.my_init()  # 初始化程序运行环境，创建对应的文件目录
# 创建GUI窗体
root = tk.Tk()
root.title('FileManager')
MainPage(root)
root.mainloop()
