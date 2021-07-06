import tkinter as tk
import webbrowser
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.messagebox import *
from tkinter import messagebox as mBox
from tkinter import scrolledtext
import os
import windnd
import sys
import threading
import time
import shutil
import re
import cv2
from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips
from conf import settings
from natsort import natsorted
import logging


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from core import backup, Mybackup, file_dir_syn, hash_core, search, Mytools, compare_file, get_img_thread, \
    image_similarity_thread, video_similarity, logger, search_image, search_video
from core.check import *
# style = ttk.Style()  # 设计页面界面Label
# style.configure("BW.TLabel", font=('Arial', 12), width=50, height=2)

g_auth_flag = False  # 权限标志位， True允许修改配置， False 不允许修改
g_password = None  # 用于获取用户输入的密码，校验权限


def checkPassword(authWin, password, frameObj):
    """用于校验密码"""
    try:
        print("ok")
        print(password, password.get())
        if password.get().strip() == "此生也算共白头":
            mBox.showinfo("权限验证", "权限验证通过，授权本次操作，授权时长1min!")
            threading.Thread(target=authManager, args=(frameObj,)).start()
            authWin.destroy()
            return
    except Exception as e:
        print(e)
    authWin.destroy()
    mBox.showinfo("权限验证", "权限验证未通过，授权失败!")


def authManager(frameObj):
    """这是一个授权管理函数，用于在授权时长结束后，终结授权状态"""
    global g_auth_flag
    g_auth_flag = True
    print("授权开始!")
    frameObj.chmodElement()  # 修改Entry, Radiobutton状态
    time.sleep(60)
    g_auth_flag = False
    frameObj.chmodElement()  # 修改Entry, Radiobutton状态
    print("授权结束!")


def authCheck(frameObj):
    # AuthFrame()
    authWin = tk.Tk()
    authWin.title('权限验证！')
    # 设置窗口大小
    winWidth = 400
    winHeight = 200
    # 获取屏幕分辨率
    screenWidth = authWin.winfo_screenwidth()
    screenHeight = authWin.winfo_screenheight()
    x = int((screenWidth - winWidth) / 2)
    y = int((screenHeight - winHeight) / 2)
    password = tk.StringVar()
    # 设置窗口初始位置在屏幕居中
    authWin.geometry("%sx%s+%s+%s" % (winWidth, winHeight, x, y))

    ttk.Label(authWin, text='修改程序配置信息，有高风险，请在程序没有执行子任务的时候进行！').pack(pady=15)
    ttk.Label(authWin, text="请问：两处相思同淋雪？").pack(pady=10)
    # g_password = tk.StringVar()
    e1 = ttk.Entry(authWin, textvariable=password, width=20)
    e1.pack(pady=10)
    ttk.Button(authWin, text="验证", command=lambda: checkPassword(authWin, e1, frameObj)).pack()

    authWin.mainloop()


def refuse(func):
    """这是一个装饰器用于拒绝用户执行一些危险操作"""

    def wrapped_func(*args, **kwargs):
        if g_auth_flag is False:
            mBox.showwarning("权限拒绝！", "为了安全起见，软件作者设定目前用户不能执行该操作！\n若需要执行操作请进行权限验证！")
            return
        func(*args, **kwargs)

    return wrapped_func


class BaseFrame(tk.Frame):  # 继承Frame类
    """所有页面的基类"""
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.record_path = None  # 导出的记录文件路径
        self.f_title = ttk.Frame(self)  # 页面标题
        self.f_input = ttk.Frame(self)  # 输入部分
        self.f_option = ttk.Frame(self)
        # self.f_option = ttk.Frame(self.f_input)
        # self.f_button = ttk.Frame(self)
        self.f_state = ttk.Frame(self)  # 进度条
        self.f_content = ttk.Frame(self)  # 显示结果
        self.f_bottom = ttk.Frame(self)  # 页面底部
        self.f_title.pack(fill=tk.BOTH, expand=True)
        self.f_input.pack(fill=tk.BOTH, expand=True)
        self.f_option.pack(fill=tk.BOTH, expand=True)
        # self.f_button.pack(fill=tk.BOTH, expand=True)
        self.f_state.pack(fill=tk.BOTH, expand=True)
        self.f_content.pack(fill=tk.BOTH, expand=True)
        self.f_bottom.pack(fill=tk.BOTH, expand=True)

        self.l_title = tk.Label(self.f_title, text='页面', font=('Arial', 12), width=50, height=2)
        self.l_title.pack()


class ExportFrame(BaseFrame):  # 继承Frame类
    """导出文件信息"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_path = tk.StringVar()
        self.record_path = None  # 导出的记录文件路径
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "导出文件信息"
        ttk.Label(self.f_input, text='文件目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dir_path, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=3, stick=tk.EW)
        ttk.Button(self.f_input, text='导出', command=self.run).grid(row=2, column=3, stick=tk.EW)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)
        self.button_show = ttk.Button(self.f_bottom, text='查看导出文件', command=self.showResult, state=tk.DISABLED)
        self.button_show.grid(row=8, column=0, sticky=tk.W, pady=10)

    def selectPath(self):
        path_ = askdirectory()
        self.dir_path.set(path_)

    def showResult(self):
        """用于显示导出文件内容"""
        # 打开文件
        webbrowser.open_new_tab(self.record_path)
        # 还原状态信息
        self.record_path = None
        self.button_show.config(state=tk.DISABLED)

    @log_error
    def deal_export_file(self, dir_path):
        """处理导出操作"""
        self.scr.insert('end', '\n正在导出%s目录下的文件信息...\n' % dir_path)
        self.record_path, count = Mytools.export_file_info(dir_path)
        msg = "导出%s个文件信息到%s完成！" % (count, self.record_path)
        logger.operate_logger("从%s 下导出%s个文件信息到%s" % (dir_path, count, self.record_path))
        self.scr.insert('end', msg + '\n')
        mBox.showinfo('导出文件信息完成！', msg)
        self.button_show.config(state=tk.NORMAL)

    def run(self):
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.dir_path.get())
        if dir_path:
            t = threading.Thread(target=self.deal_export_file, args=(dir_path,))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dir_path.get())


class QuerySameFrame(BaseFrame):  # 继承Frame类
    """查找重复文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_path = tk.StringVar()
        self.record_path = None  # 导出的记录文件路径
        self.mode_dict = {
            "同名文件": "name",
            "相同大小文件": "size",
            "同名且大小相同文件": "name_size",
            "大小相同且修改时间相同文件": "size_mtime",
            "同名且大小相同且修改时间相同文件": "name_size_mtime"
        }
        self.optionDict = {"拷贝": "copy", "剪切": "move"}  # 文件操作模式
        self.mode = tk.StringVar()  # 查询模式
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()  # 重复文件导出目录路径
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.src_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "查找相同文件"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.EW, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1, columnspan=3, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, stick=tk.EW, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1, columnspan=3, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='查询模式: ').grid(row=0, stick=tk.EW, pady=10)
        modeChosen = ttk.Combobox(self.f_input_option, width=35, textvariable=self.mode)
        modeChosen['values'] = list(self.mode_dict.keys())
        modeChosen.grid(row=0, column=1, sticky=tk.W)
        modeChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        modeChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_input_option, text='  操作模式: ').grid(row=0, column=2, stick=tk.W, pady=10)
        col = 3
        for item in self.optionDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.option, value=item).grid(column=col, row=0, sticky=tk.W)
            col += 1
        self.option.set("拷贝")  # 设置默认值

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=4)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, column=0, sticky='WE', columnspan=5)

        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_path.get():
            webbrowser.open(self.dst_path.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            msg = "根据%s,还原了%s个文件，还原文件信息记录到%s" % (self.record_path, count, restore_path)
            mBox.showinfo('还原文件完成！', msg)
            self.scr.insert("end", "%s\n" % msg)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)

    @log_error
    def deal_query_same(self, search_dir, save_dir):
        # search_dir = self.search_path.get()
        # save_dir = self.save_path.get()
        search_mode = self.mode_dict[self.mode.get()]
        deal_mode = self.optionDict[self.option.get()]
        write_time, log_time = Mytools.get_times()  # 获取当前时间的两种格式
        self.scr.insert("end", "正在遍历文件目录，请稍候！\n")
        self.pb1["value"] = 1  # 模拟遍历完成
        file_dict, count = search.find_same(search_dir, search_mode)
        if len(file_dict):  # 如果有相同文件再进行后续动作
            self.scr.insert("end", "检索%s\n  共发现%s %s个！\n" % (search_dir, search_mode, len(file_dict)))
            self.pb1["value"] = 2  # 比对完成
            self.scr.insert("end", "正在将%s 由%s %s到%s！\n" % (self.mode.get(), search_dir, deal_mode, save_dir))
            # self.record_path = Mytools.move_or_copy_file(file_dict, search_dir, save_dir, deal_mode, name_simple=True)
            self.record_path = os.path.join(settings.RECORD_DIR, '%s %s.txt' % ("new_old_record", write_time))
            # 组装new_old_record
            num = 0  # 用于记录重复组编号
            new_old_record = {}  # 用于保存新旧文件名信息，格式为"{new_file: old_file, }"
            for info in file_dict:  # 用于储存相同文件,格式"{"name"或者"size": [file_path1,file_path1,],...}"
                for item in file_dict[info]:
                    new_file = os.path.basename(Mytools.make_new_path(item, search_dir, save_dir, name_simple=True))
                    new_file = 'S%s__%s' % (num, new_file)
                    new_file = os.path.join(save_dir, new_file)
                    new_old_record[new_file] = item
                num += 1  # 编号+1

            # 操作文件
            error_count = 0  # 用于记录操作失败数
            for new_file in new_old_record:
                old_file = new_old_record[new_file]
                # print(old_file)
                try:
                    if deal_mode == "copy":
                        Mytools.copy_file(old_file, new_file)
                    else:
                        Mytools.move_file(old_file, new_file)
                except Exception as e:
                    error_count += 1
                    self.scr.insert("end",
                                      "error[%s] 程序操作文件出错：  %s\n%s  ->  %s\n\n" % (error_count, e, old_file, new_file))

            self.btn_restore.config(state=tk.NORMAL)
            # 将新旧文件名记录写出到文件
            Mytools.export_new_old_record(new_old_record, self.record_path)  # 将文件剪切前后文件信息导出到new_old_record
            print_msg = "%s  中发现%s个%s的文件\t已%s到%s\n新旧文件名记录到%s" % (
                search_dir, count, self.mode.get(), self.option.get(), save_dir, self.record_path)
            log_msg = "%s  中发现%s个%s的文件，已%s到%s，新旧文件名记录到%s" % (
                search_dir, count, self.mode.get(), self.option.get(), save_dir, self.record_path)
        else:
            print_msg = "%s  中未发现%s的文件！" % (search_dir, self.mode.get())
            log_msg = print_msg
        logger.operate_logger(log_msg, log_time)  # 记录到日志
        self.scr.insert("end", "%s\n" % print_msg)
        self.pb1["value"] = 3  # 操作文件完成
        mBox.showinfo('查找相同文件完成！', print_msg)

    def run(self):
        self.record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 3  # 总项目数 1/3为遍历文件完成， 2/3 为比对完成， 3/3为操作文件完成
        search_dir = Mytools.check_path(self.src_path.get())
        save_dir = Mytools.check_path(self.dst_path.get(), True)
        if search_dir and save_dir:
            if search_dir == save_dir:
                mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
                return
            t = threading.Thread(target=self.deal_query_same, args=(search_dir, save_dir))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return


class FindSameFilesByHashFrame(BaseFrame):  # 继承Frame类
    """根据文件hash值去重"""
    def __init__(self, master=None):
        super().__init__(master)
        self.optionDict = {"拷贝": "copy", "剪切": "move"}
        self.mode = tk.StringVar()
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()  # 重复文件导出目录路径
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.same_record_path = None  # 记录重复文件的same_record 路径
        self.failed_record_path = None  # 记录操作文件失败的failed_record 路径
        self.sort_reverse = tk.BooleanVar()  # 记录排序方式 True 倒序 False正序
        self.sort_mode = tk.BooleanVar()  # 是否根据修改时间排序 True 根据修改时间排序 False 不操作
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.src_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "查找相同文件(hash值)"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=1, column=0, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="根据修改时间排序", variable=self.sort_mode, onvalue=True, offvalue=False).grid(
            column=1, row=1, sticky=tk.W)
        self.sort_mode.set(False)
        ttk.Radiobutton(self.f_input_option, text="正序", variable=self.sort_reverse, value=False).grid(row=1, column=2,
                                                                                                sticky=tk.E)
        ttk.Radiobutton(self.f_input_option, text="倒序", variable=self.sort_reverse, value=True).grid(row=1, column=3,
                                                                                               sticky=tk.E)
        self.sort_mode.set(False)  # 默认按修改时间正序排序
        ttk.Label(self.f_input_option, text="文件操作：").grid(row=2, column=1)
        col = 2
        for item in self.optionDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.option, value=item).grid(column=col, row=2, sticky=tk.W)
            col += 1
        self.option.set("拷贝")  # 设置默认值
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=4, sticky=tk.E)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=1, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=1, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 32
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE')

        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=8, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=8, column=1, pady=10)
        self.btn_showSameRecord = ttk.Button(self.f_bottom, text="查看重复记录", command=self.showSameRecord, state=tk.DISABLED)
        self.btn_showSameRecord.grid(row=8, column=2, pady=10)
        self.btn_showFailedRecord = ttk.Button(self.f_bottom, text="查看操作失败记录", command=self.showfailedRecord, state=tk.DISABLED)
        self.btn_showFailedRecord.grid(row=8, column=3, pady=10)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_path.get():
            webbrowser.open(self.dst_path.get())

    def showSameRecord(self):
        """查看相同文件记录"""
        if self.same_record_path:
            webbrowser.open(self.same_record_path)

    def showfailedRecord(self):
        """查看操作失败记录"""
        if self.failed_record_path:
            webbrowser.open(self.failed_record_path)

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            msg = "根据%s,还原了%s个文件，还原文件信息记录到%s" % (self.record_path, count, restore_path)
            self.scr.insert('end', msg + '\n')
            self.scr.see("end")
            mBox.showinfo('还原文件完成！', msg)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)

    @log_error
    def deal_query_same(self):
        src_path = self.src_path.get()
        dst_path = self.dst_path.get()
        deal_str = self.option.get()
        deal_mode = self.optionDict[deal_str]
        start_time = time.time()  # 开始时间
        sort_reverse = self.sort_reverse.get()
        sort_mode = self.sort_mode.get()
        self.scr.insert("end", "正在遍历文件目录，请稍候！\n")
        print("sort_reverse:", sort_reverse, "sort_bymtime:", sort_mode)
        # 获取文件列表
        file_list = []
        if sort_mode:  # 根据修改时间排序
            # 获取文件的路径和对应修改时间
            temp_list = []  # 储存文件路径和修改时间
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_mtime = os.path.getmtime(file_path)
                    temp_list.append((file_mtime, file_path))
            # 冒泡排序
            n = len(temp_list)
            if sort_reverse is False:  # 正序
                for i in range(n):
                    for j in range(0, n - i - 1):
                        if temp_list[j][0] > temp_list[j + 1][0]:
                            temp_list[j], temp_list[j + 1] = temp_list[j + 1], temp_list[j]
            else:
                # 倒序
                for i in range(n):
                    for j in range(0, n-i-1):
                        if temp_list[j][0] < temp_list[j+1][0]:
                            temp_list[j], temp_list[j+1] = temp_list[j+1], temp_list[j]
            # 组装file_list
            for item in temp_list:
                file_list.append(item[1])
        else:  # 不根据修改时间排序
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    file_list.append(os.path.join(root, file))
        print(file_list)
        self.scr.insert("end", "文件列表为：\n")
        for item in file_list:
            self.scr.insert("end", "%s\n" % item)
        self.pb1["maximum"] = len(file_list)  # 总项目数
        self.scr.see(tk.END)
        print("一共有%s个文件，正在进行hash计算找出重复文件" % len(file_list))
        self.scr.insert("end", "一共有%s个文件，正在进行hash计算找出重复文件\n" % len(file_list))
        # 计算文件hash值，并找出重复文件
        hash_dict = {}  # 用于储存文件的hash信息， 数据格式{hash_value:filename,}
        failed_files = []  # 记录移动失败的文件
        new_old_record = {}  # 记录新旧文件名 格式{new_path:old_path,}
        same_record = {}  # 记录文件重复信息 格式{same_path:[same_path1,samepath2,],}
        count = 0  # 标记重复文件个数
        time_now_str = time.strftime("%Y%m%d%H%M%S", time.localtime())
        dir_basename = os.path.basename(src_path)
        # print("time_now_str:", time_now_str)
        path_failed_files_record = os.path.join(settings.RECORD_DIR, '%s_moveFailed_%s.txt' % (dir_basename, time_now_str))  # 移动失败的文件的记录路径
        path_new_old_record = os.path.join(settings.RECORD_DIR, '%s_new_old_record_%s.txt' % (dir_basename, time_now_str))  # 移动成功的文件的新旧文件名记录路径
        path_same_record = os.path.join(settings.RECORD_DIR, '%s_same_record_%s.txt' % (dir_basename, time_now_str))  # 移动成功的文件的新旧文件名记录路径
        for item in file_list:
            self.pb1["value"] += 1
            hash_value = hash_core.get_md5(item)
            if hash_value not in hash_dict:
                hash_dict[hash_value] = item
                same_record[item] = []  # 创建新记录
            else:
                count += 1
                same_record[hash_dict[hash_value]].append(item)
                try:
                    print("%s 重复，将移动到%s" % (item, dst_path))
                    self.scr.insert("end", "%s 重复，将%s到%s\n" % (item, deal_str, dst_path))
                    self.scr.see("end")
                    new_item = os.path.join(dst_path, os.path.basename(item))
                    if os.path.exists(new_item):
                        print(new_item, "is exists at %s,program will not move it!" % dst_path)
                        self.scr.insert("end", "%s 已存在同名文件，移动失败！\n" % dst_path)
                        failed_files.append(item)
                        continue
                    new_old_record[new_item] = item
                    if deal_mode == 'copy':
                        Mytools.copy_file(item, new_item)
                    else:
                        Mytools.move_file(item, new_item)
                except Exception as e:
                    failed_files.append(item)
                    print("moving %s failed!,Exception:%s " % (item, e))
                    self.scr.insert("end", "%s 移动失败！\n" % dst_path)

        msg = "hash去重完成！共有%s个重复文件！\n" % count
        log_msg = "hash去重完成！%s 下共有文件%s个，共有%s个重复文件！" % (src_path, len(file_list), count)
        if count:
            # print(len(same_record))
            with open(path_same_record, 'a', encoding='utf-8') as f:
                for item in same_record:
                    same_list = same_record[item]
                    if same_list:
                        f.write("%s\n" % item)
                        for i in same_list:
                            f.write("\t%s\n" % i)
                    else:
                        continue
            self.same_record_path = path_same_record
            self.btn_showSameRecord.config(state=tk.NORMAL)
            msg += "重复文件 %s 到%s\n重复文件信息记录到%s\n" % (deal_str, dst_path, path_same_record)
            log_msg += "重复文件 %s 到%s，重复文件信息记录到%s" % (deal_str, dst_path, path_same_record)
        if len(failed_files):
            self.failed_record_path = path_failed_files_record
            self.btn_showFailedRecord.config(state=tk.NORMAL)
            with open(path_failed_files_record, 'w', encoding='utf-8') as f:
                for item in failed_files:
                    f.write("%s\n" % item)
            msg += "%s个文件移动失败，移动失败文件记录到%s\n" % (len(failed_files), path_failed_files_record)
            log_msg += "，%s个文件移动失败，移动失败文件记录到%s" % (len(failed_files), path_failed_files_record)
        if len(new_old_record):
            self.record_path = path_new_old_record
            self.btn_restore.config(state=tk.NORMAL)
            with open(path_new_old_record, 'a', encoding='utf-8') as f:
                for new_file in new_old_record:
                    f.write("%s\t%s\n" % (new_file, new_old_record[new_file]))
            msg += "移动成功文件新旧文件名记录保存到%s\n" % path_new_old_record
            log_msg += "，移动成功文件新旧文件名记录保存到%s" % path_new_old_record

        print(msg)
        self.scr.insert("end", msg)
        self.scr.insert("end", "用时%ss\n" % (time.time() - start_time))
        self.scr.see("end")
        logger.operate_logger(log_msg)
        mBox.showinfo('hash方式查找相同文件完成！', msg)

    def run(self):
        self.record_path = None
        self.same_record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_showSameRecord.config(state=tk.DISABLED)
        self.btn_showFailedRecord.config(state=tk.DISABLED)
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        search_dir = Mytools.check_path(self.src_path.get())
        save_dir = Mytools.check_path(self.dst_path.get(), True)
        if search_dir and save_dir:
            if search_dir == save_dir:
                mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
                return
            t = threading.Thread(target=self.deal_query_same)
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return


class SynFrame(BaseFrame):  # 继承Frame类
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()  # 模式 "基于filecmp模块", "自己实现的Mybackup,节省IO资源占用", "备份端目录变更同步"
        self.src_path = tk.StringVar()  # 源目录
        self.dst_path = tk.StringVar()  # 备份端
        self.option = tk.StringVar()
        # self.exeState = tk.StringVar()  # 用于动态更新程序执行任务状态
        # self.proState = tk.StringVar()  # 用于动态更新程序运行状态，running
        self.modeDict = {
            "基于filecmp模块": backup,
            "自己实现的Mybackup,节省IO资源占用": Mybackup,
            "备份端目录变更同步": file_dir_syn}
        self.optionDict = {
            "基于filecmp模块": ["同步备份", "同步还原", "增量备份"],
            "自己实现的Mybackup,节省IO资源占用": ["同步备份", "增量备份"],
            "备份端目录变更同步": ["目录变更", ]}
        self.createPage()

    def selectPath1(self):
        self.src_path.set(askdirectory())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def selectPath2(self):
        self.dst_path.set(askdirectory())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def selectOption(self):
        print(self.mode.get())
        # self.createPage()  # 重新加载页面在tkinter不创建子线程时可以，如果当前页创建子线程则会使用默认配置，于是这就失效无法联动下拉框
        self.optionChosen["value"] = self.optionDict[self.mode.get()]  # 联动下拉框
        self.optionChosen.current(0)
        self.scr.delete(1.0, 'end')  # 清空原内容
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    @log_error
    def findDiff(self):
        """用于实际进行文件比对操作"""
        self.scr.delete(1.0, 'end')  # 清空原内容
        self.exeStateLabel["text"] = "比对文件中..."
        self.proStateLabel["text"] = "running..."
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), True)
        if not (src_path and dst_path):
            mBox.showwarning("输入路径有误！", "输入路径有误，请检查！")
            return
        try:
            if self.mode.get() == "基于filecmp模块":  # 基于filecmp返回的数据，文件和文件夹统计在一起
                self.result = {"only_in_src": [], "only_in_dst": [], "diff_files": [],
                               "common_funny": []}  # 用于存储两个目录比较结果
                self.result = self.modeDict[self.mode.get()].do_compare(src_path, dst_path, self.result)
                self.result["count"] = {
                    "only_in_src_count": len(self.result["only_in_src"]),
                    "only_in_dst_count": len(self.result["only_in_dst"]),
                    "update_count": len(self.result["diff_files"]),
                    "common_funny_count": len(self.result["common_funny"])}
            else:
                self.result = self.modeDict[self.mode.get()].find_difference(src_path, dst_path)
        except Exception as e:
            self.exeStateLabel["text"] = "程序运行出错,详情请查看错误日志!"
            self.proStateLabel["text"] = "error!!!"
            raise e

        msg = []
        # print(str(self.result))
        count_detial = self.result.pop("count")
        # print(count_detial)
        msg.append("%s    ->    %s\n" % (src_path, dst_path))
        for item in count_detial:
            msg.append("%s: %s\n" % (item, count_detial[item]))
        for item in self.result:
            if len(self.result[item]) == 0:
                continue
            msg.append('\n%s: \n' % item)
            for elem in self.result[item]:
                msg.append('\t%s\n' % elem)
        msg_str = ''.join(msg)
        self.scr.insert('end', msg_str)
        self.exeStateLabel["text"] = "比对文件完成！"
        self.proStateLabel["text"] = "complete！"

    def findDiffRun(self):
        """"执行比对文件的主程序，调用实际执行子进程"""
        t = threading.Thread(target=self.findDiff)
        t.start()

    @log_error
    def deal_syn(self, src_path, dst_path):
        """用于处理文件同步类操作"""
        # print(self.option.get())
        # print(self.src_path.get())
        # print(self.dst_path.get())
        self.proStateLabel["text"] = "running..."
        option = self.option.get()
        if option in ["1", "同步备份"]:
            option = "backup_full"
        elif option in ["2", "同步还原"]:
            option = "recovery"
        elif option in ["3", "增量备份"]:
            option = "backup_update"
        msg = self.modeDict[self.mode.get()].deal_file(self, src_path, dst_path, self.result, option)
        self.exeStateLabel["text"] = "文件同步完成!"
        self.proStateLabel["text"] = "complete!"
        mBox.showinfo('文件同步操作完成！', msg)

    def run(self):
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), True)
        if src_path and dst_path:
            t = threading.Thread(target=self.deal_syn, args=(src_path, dst_path))
            t.start()
        else:
            mBox.showerror("路径不存在！", "输入路径有误！请检查！")
            return

    def createPage(self):
        self.l_title["text"] = "文件同步备份"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='备份端路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        col = 1
        for item in self.modeDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.mode, value=item, command=self.selectOption).grid(column=col,
                                                                                                             row=0)
            col += 1
        self.mode.set("基于filecmp模块")
        ttk.Button(self.f_input, text="比对差异", command=self.findDiffRun).grid(row=3, column=4)
        # 展示结果
        ttk.Label(self.f_state, text='比对结果: ').grid(row=0, stick=tk.W, pady=10)
        # self.pbrun = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="indeterminate")  # 用于展示程序运行中的状态
        # self.pbrun.grid(row=6, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 32
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)

        ttk.Label(self.f_bottom, text='请选择操作: ').grid(row=0, column=0, pady=10)
        self.optionChosen = ttk.Combobox(self.f_bottom, width=20, textvariable=self.option)
        if self.mode.get():
            self.optionChosen['values'] = self.optionDict[self.mode.get()]
        else:
            self.optionChosen['values'] = self.optionDict["基于filecmp模块"]
        self.optionChosen.grid(row=0, column=1, pady=10)
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        self.optionChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_bottom, text="", width=70).grid(row=0, column=3)
        ttk.Button(self.f_bottom, text="执行", command=self.run).grid(row=0, column=4, sticky=tk.EW)
        # ttk.Label(self, text='完成进度: ').grid(row=9, stick=tk.W, pady=10)
        # self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        # self.pb1.grid(row=9, column=1, columnspan=5, stick=tk.EW)
        ttk.Label(self.f_bottom, text='程序运行状态: ').grid(row=2, stick=tk.W, pady=10)
        self.exeStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序执行任务状态
        self.exeStateLabel.grid(row=2, column=1, columnspan=2, stick=tk.W, pady=10)
        self.proStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序总运行状态
        self.proStateLabel.grid(row=2, column=4, stick=tk.W, pady=10)


class RestoreFrame(BaseFrame):  # 继承Frame类
    """还原文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.src_path = tk.StringVar()
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "还原文件"
        ttk.Label(self.f_input, text='new_old_record文件: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=90).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=3)
        ttk.Button(self.f_input, text='还原', command=self.run).grid(row=1, column=3, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=5)

    def selectPath(self):
        path_ = askopenfilename()
        self.src_path.set(path_)

    @log_error
    def deal_restore(self, dir_path):
        print(self.src_path.get())
        # self.scr.delete(1.0, 'end')
        self.scr.insert('end', '\n正在还原%s记录中的文件...\n' % dir_path)
        restore_path, count = Mytools.restore_file_by_record(dir_path)
        msg = "还原了%s个文件，还原文件信息记录到%s" % (count, restore_path)
        self.scr.insert('end', msg + '\n')
        mBox.showinfo('还原文件完成！', msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.src_path.get())
        if dir_path:
            t = threading.Thread(target=self.deal_restore, args=(dir_path,))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return


class DelFileFrame(BaseFrame):
    """删除文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()
        self.dir_path = tk.StringVar()  # 源文件路径，即要执行删除操作的目录路径
        self.eg_path = tk.StringVar()  # 样本路径
        self.record_path = tk.StringVar()  # 记录文件的路径
        self.newdir_path = tk.StringVar()  # 之前导出的，并且已经审核后的文件的目录路径
        self.save_flag = tk.BooleanVar()  # 标记文件夹中的文件是要保留还是要删除，True保留
        self.del_record = tk.StringVar()  # 用于展示获取到的del_record
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.dir_path.set(path_)

    def selectPath2(self):
        if self.mode.get() in ["frominfo", "fromrecord"]:
            path_ = askopenfilename()
        else:
            path_ = askdirectory()
        self.eg_path.set(path_)

    def selectPath3(self):
        path_ = askdirectory()
        self.newdir_path.set(path_)

    def selectPath4(self):
        path_ = askopenfilename()
        self.record_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "删除文件"
        ttk.Label(self.f_input, text='源文件目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dir_path, width=100).grid(row=0, column=1, stick=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='要删除的样本: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.eg_path, width=100).grid(row=1, column=1, stick=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="根据样本目录", variable=self.mode, value="fromdir").grid(row=0, column=1)
        ttk.Radiobutton(self.f_input_option, text="根据导出的文件信息", variable=self.mode, value="frominfo").grid(row=0, column=2)
        ttk.Radiobutton(self.f_input_option, text="根据new_old_record", variable=self.mode, value="fromrecord").grid(row=0, column=3)
        self.mode.set("fromdir")  # 设置默认值
        ttk.Button(self.f_input, text="执行删除", command=self.delFile).grid(row=3, column=4)

        tk.Label(self.f_state, text='获取要删除的文件new_old_record', font=('Arial', 12), width=50, height=2).pack()
        ttk.Label(self.f_content, text="过滤new_old_record,获取要删除的文件的new_old_record: ").grid(row=0, columnspan=3,
                                                                                            stick=tk.W, pady=10)
        ttk.Label(self.f_content, text="已审核后的目录路径: ").grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_content, textvariable=self.newdir_path, width=90).grid(row=1, column=1, columnspan=3, stick=tk.EW)
        ttk.Button(self.f_content, text="浏览", command=self.selectPath3).grid(row=1, column=4)
        ttk.Label(self.f_content, text='new_old_record路径：').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_content, textvariable=self.record_path, width=90).grid(row=2, column=1, columnspan=3, stick=tk.EW)
        ttk.Button(self.f_content, text="浏览", command=self.selectPath4).grid(row=2, column=4)

        ttk.Label(self.f_content, text='目录中的文件是否要保留: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_content, text="保留", variable=self.save_flag, value=True).grid(row=3, column=1, sticky=tk.E)
        ttk.Radiobutton(self.f_content, text="删除", variable=self.save_flag, value=False).grid(row=3, column=2, sticky=tk.E)
        self.save_flag.set(True)  # 设置默认值True 保留
        ttk.Button(self.f_content, text="获取记录", command=self.getDelRecord).grid(row=3, column=4)
        ttk.Label(self.f_content, text='del_record: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Entry(self.f_content, textvariable=self.del_record, width=90).grid(row=4, column=1, columnspan=3, stick=tk.EW)
        ttk.Button(self.f_content, text="查看", command=self.showFile).grid(row=4, column=4)

    def showFile(self):
        """查看结果目录"""
        if self.del_record.get():
            webbrowser.open(self.del_record.get())

    @log_error
    def delFile(self):
        """用于执行删除文件操作"""
        mode = self.mode.get()  # 获取删除模式
        dir_path = Mytools.check_path(self.dir_path.get())
        eg_path = Mytools.check_path(self.eg_path.get())
        if dir_path and eg_path:
            if mode == "fromrecord":
                del_record_path, del_count = Mytools.remove_file_by_record(eg_path, safe_flag=True)
            else:
                del_record_path, del_count = Mytools.remove_file_by_info(dir_path, eg_path, safe_flag=True)
            mBox.showinfo("删除文件完成！", "删除了%s个文件！被删除文件信息记录到%s" % (del_count, del_record_path))
        else:
            mBox.showerror("路径不存在！", "输入路径有误！请检查！")

    @log_error
    def getDelRecord(self):
        """用于获取要删除的文件的new_old_record"""
        newdir_path = Mytools.check_path(self.newdir_path.get())
        record_path = Mytools.check_path(self.record_path.get())
        if newdir_path and record_path:
            save_flag = self.save_flag.get()
            del_record_path = Mytools.get_del_record(record_path, newdir_path, save_flag)
            self.del_record.set(del_record_path)
            logger.operate_logger("获取要del_record记录完成，del_record路径为： %s" % del_record_path)
            mBox.showinfo("获取要del_record记录完成！", "del_record路径为： %s" % del_record_path)
        else:
            mBox.showerror("路径不存在！", "输入路径有误！请检查！")


class ClearEmptyDirFrame(BaseFrame):  # 继承Frame类
    """清空空文件夹"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_path = tk.StringVar()
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "清空空文件夹"
        ttk.Label(self.f_input, text='要清空空文件夹的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dir_path, width=90).grid(row=1, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=1, column=3)
        ttk.Button(self.f_input, text='清空', command=self.run).grid(row=2, column=3, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE')

    def selectPath(self):
        path_ = askdirectory()
        self.dir_path.set(path_)

    @log_error
    def deal_clear_empty_dir(self, dir_path):
        print(self.dir_path.get())
        # self.scr.delete(1.0, 'end')
        self.scr.insert('end', '\n正在清空%s目录下的空文件夹...\n' % dir_path)
        msg = Mytools.remove_empty_dir(dir_path)
        self.scr.insert('end', "%s\n" % msg)
        mBox.showinfo('清空空文件夹完成！', "%s\n" % msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.dir_path.get())
        if dir_path:
            t = threading.Thread(target=self.deal_clear_empty_dir, args=(dir_path,))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dir_path.get())
            return


class QueryFrame(BaseFrame):  # 继承Frame类
    """搜索文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.search_mode = tk.StringVar()
        self.search_option = tk.BooleanVar()
        self.search_str = tk.StringVar()  # 搜索语句
        self.rename_flag = tk.BooleanVar()  # 原样导出还是导出到单级目录并附带目录层级说明
        self.deal_mode = tk.StringVar()
        self.result = {}  # 用于储存查询结果
        self.createPage()

    def selectPath1(self):
        self.src_path.set(askdirectory())

    def selectPath2(self):
        self.dst_path.set(askdirectory())

    def createPage(self):
        self.l_title["text"] = "搜索文件"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="文件名", variable=self.search_mode, value="filename").grid(row=0, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_input_option, text="文件大小", variable=self.search_mode, value="filesize").grid(row=0, column=2, stick=tk.W)
        self.search_mode.set("filename")
        ttk.Radiobutton(self.f_input_option, text="精确搜索", variable=self.search_option, value=False).grid(row=1, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_input_option, text="正则搜索/条件搜索", variable=self.search_option, value=True).grid(row=1, column=2, stick=tk.W)
        self.search_option.set(False)
        ttk.Button(self.f_input_option, text="使用说明", command=self.showTip).grid(row=1, column=3, stick=tk.W)
        ttk.Label(self.f_input, text='搜索语句: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.search_str, width=80).grid(row=3, column=1, stick=tk.W)
        ttk.Button(self.f_input, text="搜索", command=self.do_search).grid(row=3, column=4)

        # 展示结果
        ttk.Label(self.f_state, text='搜索结果: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 25
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, column=0, sticky='WE', columnspan=5)

        ttk.Label(self.f_bottom, text='导出方式: ').grid(row=0, stick=tk.EW, pady=10)
        ttk.Radiobutton(self.f_bottom, text="复制", variable=self.deal_mode, value="copy").grid(row=0, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_bottom, text="剪切", variable=self.deal_mode, value="move").grid(row=0, column=2, stick=tk.W)
        self.deal_mode.set("copy")
        ttk.Label(self.f_bottom, text='是否原样导出？: ').grid(row=1, stick=tk.EW, pady=10)
        ttk.Radiobutton(self.f_bottom, text="导出到单级目录并附带目录描述", variable=self.rename_flag, value=True).grid(row=1, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_bottom, text="原样导出", variable=self.rename_flag, value=False).grid(row=1, column=2, stick=tk.W)
        self.rename_flag.set(True)
        ttk.Label(self.f_bottom, text='要导出的路径: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_bottom, textvariable=self.dst_path, width=95).grid(row=2, column=1, columnspan=3)
        ttk.Button(self.f_bottom, text="浏览", command=self.selectPath2).grid(row=2, column=4)
        ttk.Button(self.f_bottom, text="导出", command=self.run).grid(row=3, column=4)

    def showTip(self):
        tip = """
        正则搜索直接输入正则语句即可
        条件搜索请输入条件语句：
            gt 大于 
            gte 大于等于 
            lt 小于 
            lte 小于等于 
            between and 在中间
            例如： gt 2816665 或者 between 1024000 and 2048000
            """
        showinfo("正则/条件语句使用说明", tip)

    @log_error
    def do_search(self):
        self.scr.delete(1.0, "end")
        search_path = Mytools.check_path(self.src_path.get())
        if search_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        search_str = self.search_str.get()
        search_mode = self.search_mode.get()
        search_option = self.search_option.get()
        # print(search_path,search_str,search_mode,search_option)
        if search_mode == "filename":
            self.result = search.search_file_by_name(search_path, search_str, search_option)
            # print(self.result)
            file_count = len(self.result["files"])  # 文件数
            dir_count = len(self.result["dirs"])  # 文件夹数
            if file_count + dir_count:
                self.scr.insert("end", "搜索结果：(%s个文件, %s个文件夹)\n" % (file_count, dir_count))
                if len(self.result["files"]):
                    self.scr.insert("end", "文件:\n")
                    for item in self.result["files"]:
                        self.scr.insert("end", "\t%s\n" % item)
                if len(self.result["dirs"]):
                    self.scr.insert("end", "文件夹:\n")
                    for item in self.result["dirs"]:
                        self.scr.insert("end", "\t%s\n" % item)
            else:
                self.scr.insert("end", "未找到匹配 %s的文件和目录！" % search_str)
        else:
            self.result = search.search_file_by_size(search_path, search_str, search_option)
            if len(self.result):
                self.scr.insert("end", "搜索结果：(共匹配到符合条件的结果%s组,具体文件个数请查看结尾)\n" % len(self.result))
                count = 0  # 用以记录找到的文件数
                for item in self.result:
                    self.scr.insert("end", "size=%sB:\n" % item)
                    for file in self.result[item]:
                        self.scr.insert("end", "\t%s\n" % file)
                        count += 1
                self.scr.insert("end", "\n\n共匹配到符合条件的文件个数为%s组\n" % count)

            else:
                self.scr.insert("end", "未找到匹配 %s的文件和目录！" % search_str)

    @log_error
    def run(self):
        self.scr.delete(1.0, "end")
        search_path = Mytools.check_path(self.src_path.get())
        if search_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        save_path = Mytools.check_path(self.dst_path.get(), create_flag=True)
        if search_path == save_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        search_str = self.search_str.get()
        search_mode = self.search_mode.get()
        deal_mode = self.deal_mode.get()
        rename_flag = self.rename_flag.get()
        # print(search_path,save_path,search_str,search_mode,search_option, deal_mode,rename_flag)
        if search_mode == "filename":
            if len(self.result["files"]) + len(self.result["dirs"]):
                record_path = Mytools.deal_files(self.result, search_path, save_path, deal_mode=deal_mode,
                                                 rename_flag=rename_flag)
                mBox.showinfo("完成！", "导出完成！文件new_old_record记录到%s" % record_path)
            else:
                print("未找到匹配 %s的文件和目录！" % search_str)
                mBox.showinfo("完成！", "未找到匹配 %s的文件和目录！" % search_str)
        else:
            if len(self.result):
                record_path = Mytools.deal_files(self.result, search_path, save_path, deal_mode=deal_mode,
                                                 rename_flag=rename_flag)
                mBox.showinfo("完成！", "导出完成！文件new_old_record记录到%s" % record_path)
            else:
                mBox.showinfo("完成！", "未找到匹配 %s的文件和目录！" % search_str)
                print("未找到匹配 %s的文件和目录！" % search_str)


class CopyDirTreeFrame(BaseFrame):
    """拷贝或导出目录结构"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.path_ok_flag = True  # 用于标记用户输入的路径是否经过安全验证 True 路径存在 False 路径不存在
        self.createPage()

    def selectPath1(self):
        if self.option.get() == 'fromfile':
            path_ = askopenfilename()
        else:
            path_ = askdirectory()
        self.src_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_path.set(path_)

    def selectOption(self):
        # 从文件信息拷贝目录结构还是 从目录拷贝目录结构
        self.scr.delete(1.0, "end")  # 每次切换选项时都进行结果显示区域清屏

    def createPage(self):
        self.l_title["text"] = "拷贝目录结构"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标目录路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)

        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="从目录拷贝", variable=self.option, value="fromdir", command=self.selectOption).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="从文件拷贝", variable=self.option, value="fromfile", command=self.selectOption).grid(
            row=0, column=2, sticky=tk.W)
        self.option.set("fromdir")  # 设置单选默认值
        ttk.Button(self.f_input, text="拷贝目录结构", command=self.copyDirTree).grid(row=3, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="导出目录结构", command=self.exportDirTree).grid(row=3, column=2, stick=tk.E)

        # 展示结果
        ttk.Label(self.f_state, text='目录结构信息: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE')

    @log_error
    def copyDirTree(self):
        self.scr.delete(1.0, "end")
        self.scr.insert("end", '正在拷贝目录结构，请稍候...\n')
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        dst_path = Mytools.check_path(self.dst_path.get(), create_flag=True)
        msg, dir_str_list = Mytools.make_dirs(src_path, dst_path)
        self.scr.insert("end", '拷贝目录结构完成，目录结构如下:\n')
        self.scr.insert("end", '\n'.join(dir_str_list))
        mBox.showinfo('完成！', msg)

    @log_error
    def exportDirTree(self):
        self.scr.delete(1.0, "end")
        self.scr.insert("end", '正在导出目录结构信息，请稍候...\n')
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        record_path, dir_list = Mytools.export_dirs(src_path)
        if len(dir_list):
            self.scr.insert("end", '导出目录结构信息完成，目录结构如下:\n')
            for item in dir_list:
                self.scr.insert("end", "%s\n" % item)
            self.scr.insert("end", "导出%s 的目录结构信息到%s 完成！" % (src_path, record_path))
            self.scr.see("end")
            mBox.showinfo('完成！', "导出%s 的目录结构信息到%s 完成！" % (src_path, record_path))
        else:
            if record_path is None:
                self.scr.insert("end", "您输入的是文件，暂不支持从文件导出目录结构到文件！\n若需备份该文件，您可直接复制该文件！\n")
                mBox.showwarning("warning！", "您输入的是文件，暂不支持从文件导出目录结构到文件！\n若需备份该文件，您可直接复制该文件！")
                return
            self.scr.insert("end", "%s  下并无子目录结构！" % src_path)
            showinfo("完成", "%s  下并无子目录结构！" % src_path)


class CompareTxtFrame(BaseFrame):  # 继承Frame类
    """比较文本文件内容差异"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.BooleanVar()  # True 对比目录 False 对比文件
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.record_dir_path = None  # 用来记录文本差异结果文件目录路径
        self.createPage()

    def selectPath1(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.src_path.set(path_)

    def selectPath2(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.dst_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "对比文本文件内容差异"
        ttk.Label(self.f_input, text='源路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0,column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="对比目录", variable=self.mode, value=True).grid(row=0, column=1)
        ttk.Radiobutton(self.f_input_option, text="对比文件", variable=self.mode, value=False).grid(row=0, column=2)
        self.mode.set(True)  # 设置单选默认值
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)

        # 展示结果
        ttk.Label(self.f_state, text='比对结果: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=5)
        ttk.Button(self.f_bottom, text="查看详情", command=self.showDiff).grid(row=0, pady=10)

    @log_error
    def showDiff(self):
        """用于查看文件差异"""
        if self.record_dir_path:
            webbrowser.open(self.record_dir_path)

    def do_compare(self, src_path, dst_path):
        self.record_dir_path, result = compare_file.compare_file_list(src_path, dst_path)
        total_msg = "比对完成！详情如下:\n"
        only_in_src_list = result["only_in_src"]
        only_in_dst_list = result["only_in_dst"]
        common_list = result["common_files"]
        diff_list = result["diff_files"]

        if len(only_in_src_list):
            msg = "总共有%s个文件仅存在于%s ！\n" % (len(only_in_src_list), src_path)
            self.scr.insert("end", msg)
            total_msg += "\n%s" % msg
            for item in only_in_src_list:
                total_msg += "\t%s\n" % item
        if len(only_in_dst_list):
            msg = "总共有%s个文件仅存在于%s ！\n" % (len(only_in_dst_list), dst_path)
            self.scr.insert("end", msg)
            total_msg += "\n%s" % msg
            for item in only_in_dst_list:
                total_msg += "\t%s\n" % item
        if len(diff_list):
            msg = "总共有%s个文件文本内容发生变化！\n" % len(diff_list)
            self.scr.insert("end", msg)
            total_msg += "\n%s" % msg
            for item in diff_list:
                total_msg += "\t%s\n0==}==========>%s\n" % (item[0], item[1])
        if len(only_in_src_list) + len(only_in_dst_list) + len(diff_list):
            self.scr.insert("end", total_msg)
        else:
            self.scr.insert("end", "未发现文本内容有变化的同名文件！\n")

        with open(os.path.join(self.record_dir_path, "result.txt"), 'w', encoding='utf-8') as f:
            f.write(total_msg)
        mBox.showinfo("完成！", "比对完成！总共有%s个文件文本内容发生变化！" % len(diff_list))

    def run(self):
        self.scr.delete(1.0, "end")
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        dst_path = Mytools.check_path(self.dst_path.get())
        if dst_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dst_path.get())
            return
        self.scr.insert("end", "正在比对%s 与%s 下的文本文件内容...\n" % (src_path, dst_path))
        t = threading.Thread(target=self.do_compare, args=(src_path, dst_path))
        t.start()


class CalHashFrame(BaseFrame):  # 继承Frame类
    """计算文件hash值"""
    def __init__(self, master=None):
        super().__init__(master)
        self.src_path = tk.StringVar()
        self.mode = tk.BooleanVar()  # True 对比目录 False 对比文件
        self.upper = tk.BooleanVar()  # True 大写 False 小写
        self.CODE_TYPE = settings.SYSTEM_CODE_TYPE  # 系统的编码格式，用于处理后面拖拽文件，文件名解码
        self.vars = []
        self.result = {}
        self.algors = ['sha1', 'sha256', 'md5', "sha224", "sha512", "sha384"]  # 算法
        self.search_str = tk.StringVar()  # 搜索字符串
        for i in range(len(self.algors)):
            self.vars.append(tk.StringVar())  # 获取复选框变量
        self.createPage()

    @log_error
    def cal_hash(self, path_list):
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.pb2["value"] = 0
        self.pb2["maximum"] = 0  # 总项目数

        args = []  # 存放要计算的算法
        for temp in self.vars:
            if temp.get():
                args.append(temp.get())
        self.pb2["maximum"] = len(path_list)  # 总项目数
        for item in path_list:
            temp_result = hash_core.cal_hash_by_path(item, args, self)
            self.pb2["value"] += 1
            self.result.update(temp_result)
        print("所有项目计算完成！")

    def dragged_files(self, files):
        path_list = []
        for item in files:
            # dir_path = item.decode("gbk")
            # dir_path = item.decode(self.CODE_TYPE)  # 修改配置之后不会马上更新
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)  # 修改配置之后下次就会用新的配置
            path_list.append(dir_path)
        t = threading.Thread(target=self.cal_hash, args=(path_list,))
        t.setDaemon(True)
        t.start()

    def selectPath(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.src_path.set(path_)

    def run(self):
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % src_path)
            return
        t = threading.Thread(target=self.cal_hash, args=([src_path, ],))
        t.setDaemon(True)
        t.start()

    def toupper(self):
        # content = self.scr.get(1.0, "end")
        # self.scr.delete(1.0, "end")
        # self.scr.insert("end", content.upper())
        self.scr.delete(1.0, "end")
        for file in self.result:
            self.scr.insert("end", '%s:\t%s\n' % ("文件", file))
            for item in self.result[file]:
                if item == "size":
                    info_str = "%s:\t%s" % ("大小", self.result[file][item])
                elif item == "mtime":
                    info_str = "%s:\t%s" % ("修改时间", self.result[file][item])
                elif item == "version":
                    info_str = "%s:\t%s" % ("文件版本", self.result[file][item])
                else:
                    info_str = "%s:\t%s" % (item, self.result[file][item])
                self.scr.insert("end", '%s\n' % info_str.upper())
            self.scr.insert("end", "\n")
        self.scr.see("end")

    def tolower(self):
        self.scr.delete(1.0, "end")
        for file in self.result:
            self.scr.insert("end", '%s:\t%s\n' % ("文件", file))
            for item in self.result[file]:
                if item == "size":
                    info_str = "%s:\t%s" % ("大小", self.result[file][item])
                elif item == "mtime":
                    info_str = "%s:\t%s" % ("修改时间", self.result[file][item])
                elif item == "version":
                    info_str = "%s:\t%s" % ("文件版本", self.result[file][item])
                else:
                    info_str = "%s:\t%s" % (item, self.result[file][item])
                self.scr.insert("end", '%s\n' % info_str.lower())
            self.scr.insert("end", "\n")
            self.scr.see("end")

    def writehash(self):
        hash_path = asksaveasfilename()
        hash_core.writeHash(hash_path, self.scr.get(1.0, "end"))

    def clear(self):
        """用于清除数据"""
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.pb2["value"] = 0
        self.pb2["maximum"] = 0  # 总项目数
        self.scr.delete(1.0, 'end')  # 清空文本区
        self.result.clear()

    def search(self):
        """用于从计算结果中搜索指定字符串"""
        content = self.scr.get(1.0, tk.END)
        search_str = self.search_str.get()  # 要搜索的字符串
        if self.upper.get() is True:
            search_str = search_str.upper()
        else:
            search_str = search_str.lower()
        print("search_str", search_str)
        count = content.count(search_str)

        if not count:
            # 未搜索到
            self.scr.delete(1.0, "end")
            self.scr.insert(tk.END, content)
            # print("tk.END: ", tk.END)
            self.scr.see(tk.END)
            mBox.showinfo("完成", "未搜索到匹配结果！")
        else:
            # 搜索字符串在content中
            if content:
                self.scr.delete(1.0, tk.END)
                strs = content.split(search_str)
                i = 0
                for item in strs:
                    self.scr.insert(tk.END, item)
                    i += 1
                    if i <= count:
                        self.scr.insert(tk.END, search_str, "tag")  # 匹配到的内容 “tag”标签标记后面做格式
                self.scr.tag_config('tag', background='RoyalBlue', foreground="white")
                self.scr.see(tk.END)
                mBox.showinfo("完成", "一共搜索到%s处！" % count)

    def createPage(self):
        self.l_title["text"] = "计算hash值"
        ttk.Label(self.f_input, text='文件路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='浏览模式: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="目录", variable=self.mode, value=True).grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="文件", variable=self.mode, value=False).grid(row=0, column=2, sticky=tk.W)
        self.mode.set(True)
        ttk.Label(self.f_input_option, text='算法: ').grid(row=1, stick=tk.W)
        col = 1
        row = 1
        for index, item in enumerate(self.vars):
            value = self.algors[index]
            if index < 3:
                item.set(value)
            else:
                item.set('')
            cb = ttk.Checkbutton(self.f_input_option, text=value, variable=item, onvalue=value, offvalue='')
            cb.grid(column=col, row=row, stick=tk.W, ipadx=5)
            col += 1

        ttk.Radiobutton(self.f_input_option, text="大写", variable=self.upper, value=True, command=self.toupper).grid(row=0, column=5,
                                                                                                     sticky=tk.EW)
        ttk.Radiobutton(self.f_input_option, text="小写", variable=self.upper, value=False, command=self.tolower).grid(row=0, column=6,
                                                                                                      sticky=tk.W)
        self.upper.set(False)
        ttk.Label(self.f_option, width=80).grid(row=3)
        ttk.Button(self.f_option, text='清除', command=self.clear).grid(row=3, column=1, stick=tk.E, pady=10)
        ttk.Button(self.f_option, text='保存', command=self.writehash).grid(row=3, column=2, stick=tk.E, pady=10)
        ttk.Button(self.f_option, text='计算', command=self.run).grid(row=3, column=3, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='进度: ').grid(row=0, stick=tk.W)
        ttk.Label(self.f_state, text='完成: ').grid(row=1, stick=tk.W, pady=5)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, stick=tk.EW)
        self.pb2 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb2.grid(row=1, column=1, stick=tk.EW, pady=5)

        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', pady=10)

        ttk.Entry(self.f_bottom, textvariable=self.search_str, width=110).grid(row=2, column=0, stick=tk.EW, pady=10)
        ttk.Button(self.f_bottom, text="查找", command=self.search).grid(row=2, column=1, sticky='E')

        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作


class CompStrFrame(BaseFrame):
    """用于比对字符串是否一致"""
    def __init__(self, master=None):
        super().__init__(master)
        self.str1 = tk.StringVar()
        self.str2 = tk.StringVar()
        self.ignore_case_flag = tk.BooleanVar()  # True 忽略大小写 False 严格大小写
        self.ignore_space_flag = tk.BooleanVar()  # True 忽略空格 False 严格空格
        self.only_char_flag = tk.BooleanVar()  # True 只匹配字符内容，忽略所有空格换行，包括字符串中的 False 严格空格
        self.case_flag = tk.BooleanVar()  # True 大写 False 小写
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "校对字符串"
        ttk.Label(self.f_input, text='字符串1: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.str1, width=110).grid(row=0, column=1, columnspan=2, stick=tk.EW)
        ttk.Label(self.f_input, text='字符串2: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.str2, width=110).grid(row=1, column=1, columnspan=2,stick=tk.EW)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='设置模式: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="忽略大小写差异", variable=self.ignore_case_flag, onvalue=True, offvalue=False).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="忽略字符串前后空格", variable=self.ignore_space_flag, onvalue=True, offvalue=False).grid(
            row=0, column=2, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="忽略所有空格", variable=self.only_char_flag, onvalue=True, offvalue=False).grid(
            row=0, column=3, sticky=tk.W)
        self.ignore_case_flag.set(False)
        self.ignore_space_flag.set(False)
        self.only_char_flag.set(False)
        ttk.Label(self.f_input_option, text="  大小写: ").grid(row=0, column=4)
        ttk.Radiobutton(self.f_input_option, text="大写", variable=self.case_flag, value=True, command=self.toupper).grid(
            row=0, column=5, sticky=tk.E)
        ttk.Radiobutton(self.f_input_option, text="小写", variable=self.case_flag, value=False, command=self.tolower).grid(
            row=0, column=6, sticky=tk.E)
        self.case_flag.set(False)
        ttk.Label(self.f_option, text="", width=95).grid(row=0)
        ttk.Button(self.f_option, text='清除', command=self.clear).grid(row=0, column=1, stick=tk.E, pady=10)
        ttk.Button(self.f_option, text='比对', command=self.run).grid(row=0, column=2, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='比对结果：').grid(row=0, stick=tk.W, pady=15)  # 用于展示比对结果
        self.l_result = tk.Label(self.f_state, text='待比对！', background="white", width=110)  # 用于展示比对结果
        self.l_result.grid(row=0, column=1, stick=tk.EW, pady=15)
        ttk.Label(self.f_content, text='字符串1: ').grid(row=0, stick=tk.W, pady=5)
        scrolW = 58
        scrolH = 30
        self.scr1 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr1.grid(row=1, column=0, sticky='WE', columnspan=5)
        ttk.Label(self.f_content, text='字符串2: ').grid(row=0, column=5, stick=tk.W, pady=5)
        scrolW = 58
        scrolH = 30
        self.scr2 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr2.grid(row=1, column=5, sticky='WE', columnspan=5)

    def toupper(self):
        scr_list = [self.scr1, self.scr2]
        for scr in scr_list:
            content = scr.get(1.0, "end")
            scr.delete(1.0, "end")
            scr.insert("end", content.upper())

    def tolower(self):
        scr_list = [self.scr1, self.scr2]
        for scr in scr_list:
            content = scr.get(1.0, "end")
            scr.delete(1.0, "end")
            scr.insert("end", content.lower())

    def clear(self):
        """用于清除数据"""
        self.scr1.delete(1.0, 'end')  # 清空文本区
        self.scr2.delete(1.0, 'end')  # 清空文本区
        self.l_result["background"] = "white"
        self.l_result["text"] = "待比对！"

    def check_txt(self):
        """
        用于比较文本内容
        :return: True 内容一致  False 内容不一致
        """
        text1 = self.str1.get()
        text2 = self.str2.get()
        new_text1 = text1
        new_text2 = text2
        if self.ignore_space_flag.get():
            new_text1 = text1.strip()
            new_text2 = text2.strip()
        if self.ignore_case_flag.get():
            try:
                if self.case_flag.get():
                    new_text1 = new_text1.upper()
                    new_text2 = new_text2.upper()
                else:
                    new_text1 = new_text1.lower()
                    new_text2 = new_text2.lower()
            except Exception as e:
                print(e)
        if self.only_char_flag.get():
            new_text1 = ''.join(new_text1.split())  # 不设置切割符的话默认是按照所有空字符切
            new_text2 = ''.join(new_text2.split())
        print(text1, '>>>', new_text1)
        print(text2, '>>>', new_text2)
        if new_text1 == new_text2:
            print("内容一致！")
            self.l_result["background"] = "green"
            self.l_result["text"] = "字符串内容一致！"
            self.scr1.insert("end", "原字符串：\n%s\n\n->\n\n新字符串：\n%s\n" % (repr(text1), repr(new_text1)))
            self.scr2.insert("end", "原字符串：\n%s\n\n->\n\n新字符串：\n%s\n" % (repr(text2), repr(new_text2)))
            return True
        else:
            # self.t1["background"] = "red"
            self.l_result["background"] = "#ff5151"
            self.l_result["text"] = "字符串内容不一致！"
            self.scr1.insert("end", "原来字符串：%s\n->\n新字符串：%s\n" % (repr(text1), repr(new_text1)))
            self.scr2.insert("end", "原来字符串：%s\n->\n新字符串：%s\n" % (repr(text2), repr(new_text2)))
            print("内容不一致！")
            return False

    def run(self):
        self.clear()
        t = threading.Thread(target=self.check_txt)
        t.start()


class RenameFrame(BaseFrame):
    """递归批量重命名"""
    def __init__(self, master=None):
        super().__init__(master)
        self.option = tk.StringVar()  # 标记是精确匹配还是正则匹配
        self.src_path = tk.StringVar()
        self.dir_flag = tk.BooleanVar()  # True 操作文件夹 False 不操作
        self.file_flag = tk.BooleanVar()  # True 操作文件 False 不操作
        self.search_mode = tk.StringVar()  # 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        self.search_str = tk.StringVar()  # 要搜索的字符串
        self.replace_str = tk.StringVar()  # 要替换的新内容
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.createPage()

    def do_search_regex(self):
        """搜索满足条件的目录或文件(正则模式)"""
        self.clear()
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        old_str = self.search_str.get()
        if self.dir_flag.get():
            self.scr1.insert('end', "dirs:\n")
            for root, dirs, files in os.walk(src_path):
                for dir in dirs:
                    if re.search(old_str, dir):
                        tmp_dir = os.path.join(root, dir).replace(src_path, '')
                        print("find dir:%s " % tmp_dir)
                        self.scr1.insert('end', "\t%s\n" % tmp_dir)
                        self.result["dirs"].append(tmp_dir)
        if self.file_flag.get():
            self.scr1.insert('end', "files:\n")
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    if re.search(old_str, file):
                        tmp_file = os.path.join(root, file).replace(src_path, '')
                        print("find file:%s " % tmp_file)
                        self.scr1.insert('end', "\t%s\n" % tmp_file)
                        self.result["files"].append(tmp_file)

    def do_search_normal(self):
        """搜索满足条件的目录或文件(普通模式 不支持正则语法)"""
        self.clear()
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        old_str = self.search_str.get()
        if self.dir_flag.get():
            self.scr1.insert('end', "dirs:\n")
            for root, dirs, files in os.walk(src_path):
                for dir in dirs:
                    if old_str in dir:
                        tmp_dir = os.path.join(root, dir).replace(src_path, '')
                        print("find dir:%s " % tmp_dir)
                        self.scr1.insert('end', "\t%s\n" % tmp_dir)
                        self.result["dirs"].append(tmp_dir)
        if self.file_flag.get():
            self.scr1.insert('end', "files:\n")
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    if old_str in file:
                        tmp_file = os.path.join(root, file).replace(src_path, '')
                        print("find file:%s " % tmp_file)
                        self.scr1.insert('end', "\t%s\n" % tmp_file)
                        self.result["files"].append(tmp_file)

    def do_search_exact(self):
        """搜索满足条件的目录或文件(精确模式 不支持正则语法)"""
        self.clear()
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        old_str = self.search_str.get()
        if self.dir_flag.get():
            self.scr1.insert('end', "dirs:\n")
            for root, dirs, files in os.walk(src_path):
                for dir in dirs:
                    if old_str == dir:
                        tmp_dir = os.path.join(root, dir).replace(src_path, '')
                        print("find dir:%s " % tmp_dir)
                        self.scr1.insert('end', "\t%s\n" % tmp_dir)
                        self.result["dirs"].append(tmp_dir)
        if self.file_flag.get():
            self.scr1.insert('end', "files:\n")
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    if old_str == file:
                        tmp_file = os.path.join(root, file).replace(src_path, '')
                        print("find file:%s " % tmp_file)
                        self.scr1.insert('end', "\t%s\n" % tmp_file)
                        self.result["files"].append(tmp_file)

    def do_search(self):
        """用于调度搜索方法"""
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        if search_mode == '1':  # 简单匹配
            self.do_search_normal()
        elif search_mode == '3':  # 正则匹配
            self.do_search_regex()
        else:  # 精确匹配
            self.do_search_exact()
        self.scr1.insert("end", "共有符合条件目录%s个，文件%s个" % (len(self.result["dirs"]), len(self.result["files"])))
        self.scr1.see("end")

    def rename_preview(self):
        """效果预览"""
        self.scr1.delete(1.0, 'end')
        self.scr2.delete(1.0, 'end')
        old_str = self.search_str.get()
        new_str = self.replace_str.get()
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        dir_flag = self.dir_flag.get()  # 是否操作文件夹
        file_flag = self.file_flag.get()  # 是否操作文件
        if dir_flag:
            if len(self.result["dirs"]):
                self.scr1.insert('end', "dirs:\n")
                self.scr2.insert('end', "dirs:\n")
            for item in self.result["dirs"]:
                old_dir = os.path.dirname(item)
                old_name = os.path.basename(item)
                self.scr1.insert('end', "\t%s\n" % item)
                if search_mode == '1':  # 简单匹配
                    if old_str in old_name:
                        new_name = old_name.replace(old_str, new_str)
                        new_path = os.path.join(old_dir, new_name)
                        self.scr2.insert('end', "\t%s\n" % new_path)
                elif search_mode == '3':  # 正则匹配
                    if re.search(old_str, old_name):
                        new_name = re.sub(old_str, new_str, old_name)
                        new_path = os.path.join(old_dir, new_name)
                        self.scr2.insert('end', "\t%s\n" % new_path)
                else:  # 精确模式
                    if old_str == old_name:
                        new_name = old_name.replace(old_str, new_str)
                        new_path = os.path.join(old_dir, new_name)
                        self.scr2.insert('end', "\t%s\n" % new_path)
        if file_flag:
            if len(self.result["files"]):
                self.scr1.insert('end', "files:\n")
                self.scr2.insert('end', "files:\n")
            for item in self.result["files"]:
                old_dir = os.path.dirname(item)
                old_name = os.path.basename(item)
                self.scr1.insert('end', "\t%s\n" % item)
                if search_mode == '1':  # 简单匹配
                    if old_str in old_name:
                        new_name = old_name.replace(old_str, new_str)
                        new_path = os.path.join(old_dir, new_name)
                        self.scr2.insert('end', "\t%s\n" % new_path)
                elif search_mode == '3':  # 正则匹配
                    if re.search(old_str, old_name):
                        new_name = re.sub(old_str, new_str, old_name)
                        new_path = os.path.join(old_dir, new_name)
                        self.scr2.insert('end', "\t%s\n" % new_path)
                else:  # 精确模式
                    if old_str == old_name:
                        new_name = old_name.replace(old_str, new_str)
                        new_path = os.path.join(old_dir, new_name)
                        self.scr2.insert('end', "\t%s\n" % new_path)

    def do_rename(self):
        """重命名"""
        src_path = Mytools.check_path(self.src_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        old_str = self.search_str.get()
        new_str = self.replace_str.get()
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        dir_flag = self.dir_flag.get()  # 是否操作文件夹
        file_flag = self.file_flag.get()  # 是否操作文件
        self.pb1["maximum"] = len(self.result["dirs"]) + len(self.result["files"])
        new_old_record = {}  # 记录新旧文件名 格式{new_path:old_path,}
        failed_list = []  # 记录重命名失败
        time_now = time.localtime()
        time_now_str = time.strftime("%Y%m%d%H%M%S", time_now)
        time_now_str_log = time.strftime("%Y-%m-%d %H:%M:%S", time_now)
        dirName = os.path.basename(src_path)
        path_failed_record = os.path.join(settings.RECORD_DIR, '%s_renameFailed_%s.txt' % (dirName, time_now_str))  # 移动失败的文件的记录路径
        path_new_old_record = os.path.join(settings.RECORD_DIR, '%s_new_old_record_%s.txt' % (dirName, time_now_str))  # 移动成功的文件的新旧文件名记录路径

        if file_flag:  # 操作文件
            for root, dirs, files in os.walk(src_path, topdown=False):
                for file in files:
                    old_file = os.path.join(root, file)
                    if search_mode == '1':  # 简单匹配
                        if old_str in file:
                            new_name = file.replace(old_str, new_str)
                        else:
                            continue
                    elif search_mode == '3':  # 正则匹配
                        if re.search(old_str, file):
                            new_name = re.sub(old_str, new_str, file)
                        else:
                            continue
                    else:  # 精确匹配
                        if old_str == file:
                            new_name = file.replace(old_str, new_str)
                        else:
                            continue
                    new_file = os.path.join(root, new_name)
                    try:
                        os.rename(old_file, new_file)
                        new_old_record[new_file] = old_file
                    except Exception:
                        failed_list.append(old_file)
                    self.pb1["value"] += 1
        if dir_flag:  # 操作目录
            for root, dirs, files in os.walk(src_path, topdown=False):
                for dir in dirs:
                    old_dir = os.path.join(root, dir)
                    if search_mode == '1':  # 简单匹配
                        if old_str in dir:
                            new_name = dir.replace(old_str, new_str)
                        else:
                            continue
                    elif search_mode == '3':  # 正则匹配
                        if re.search(old_str, dir):
                            new_name = re.sub(old_str, new_str, dir)
                        else:
                            continue
                    else:  # 精确匹配
                        if old_str == dir:
                            new_name = dir.replace(old_str, new_str)
                        else:
                            continue
                    new_dir = os.path.join(root, new_name)
                    try:
                        os.rename(old_dir, new_dir)
                        new_old_record[new_dir] = old_dir
                    except Exception:
                        failed_list.append(old_dir)
                    self.pb1["value"] += 1
        log_msg = None
        if len(new_old_record):
            msg = '共重命名'
            if len(self.result["dirs"]):
                msg += "%s个目录！" % len(self.result["dirs"])
            if len(self.result["files"]):
                msg += "%s个文件！" % len(self.result["files"])
            print(msg)
            with open(path_new_old_record, 'a', encoding='utf-8') as f:
                for key, value in new_old_record.items():
                    f.write("%s\t%s\n" % (key, value))
            print("记录写出到%s" % path_new_old_record)
            log_msg = msg + "记录写出到%s" % path_new_old_record
            msg += "\n记录写出到%s" % path_new_old_record
        else:
            msg = "无重命名操作"
        if len(failed_list):
            log_msg += "%s个项目重命名失败，记录到%s" % (len(path_failed_record), path_failed_record)
            msg += "\n%s个项目重命名失败，记录到%s" % (len(path_failed_record), path_failed_record)
        if log_msg:
            logger.operate_logger(log_msg, has_time=time_now_str_log)
        mBox.showinfo("完成", msg)

    def createPage(self):
        self.l_title["text"] = "批量重命名"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=2)
        ttk.Label(self.f_input, text='搜索语句: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.search_str, width=80).grid(row=1, column=1, stick=tk.W)
        ttk.Button(self.f_input, text="搜索", command=self.do_search).grid(row=1, column=2)
        ttk.Label(self.f_input, text='替换字符串: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.replace_str, width=80).grid(row=2, column=1, stick=tk.W)
        ttk.Button(self.f_input, text="预览", command=self.rename_preview).grid(row=2, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='设置模式: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="操作文件夹", variable=self.dir_flag, onvalue=True, offvalue=False).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="操作文件", variable=self.file_flag, onvalue=True, offvalue=False).grid(
            row=0, column=2, sticky=tk.W)

        self.dir_flag.set(False)
        self.file_flag.set(False)
        ttk.Label(self.f_input_option, text="匹配模式: ").grid(row=0, column=4, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="简单匹配(子集)", variable=self.search_mode, value='1').grid(row=0, column=5, sticky=tk.E)
        ttk.Radiobutton(self.f_input_option, text="精确匹配(完全一致)", variable=self.search_mode, value='2').grid(row=0, column=6, sticky=tk.E)
        ttk.Radiobutton(self.f_input_option, text="正则匹配", variable=self.search_mode, value='3').grid(row=0, column=7, sticky=tk.E)
        self.search_mode.set('1')
        ttk.Button(self.f_input, text='清除', command=self.clear).grid(row=4, column=1, stick=tk.E, pady=10)
        ttk.Button(self.f_input, text='重命名', command=self.run).grid(row=4, column=2, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, stick=tk.EW)

        ttk.Label(self.f_content, text='原文件名: ').grid(row=1, stick=tk.W, pady=5)
        scrolW = 58
        scrolH = 30
        self.scr1 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr1.grid(column=0, row=2, sticky='WE')
        ttk.Label(self.f_content, text='新文件名: ').grid(row=1, column=1, stick=tk.W, pady=5)
        self.scr2 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr2.grid(column=1, row=2, sticky='WE')

    def selectPath(self):
        path_ = askdirectory()
        self.src_path.set(path_)

    def clear(self):
        """用于清除数据"""
        self.scr1.delete(1.0, 'end')  # 清空文本区
        self.scr2.delete(1.0, 'end')  # 清空文本区
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.pb1["value"] = 0

    def run(self):
        # self.clear()
        t = threading.Thread(target=self.do_rename)
        t.start()


class GetImgFrame(BaseFrame):
    """提取视频帧图像"""
    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()  # 帧率或者秒数
        self.continue_flag = tk.BooleanVar()  # 是否继续上次进度
        self.video_dir = tk.StringVar()  # 视频路径
        self.img_dir = tk.StringVar()
        self.get_photo_by_sec_flag = tk.BooleanVar()  # 是否按秒数提取图片，True 按秒 False 按帧数
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.video_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.img_dir.set(path_)

    def change_img_label(self):
        """用于切换按时间点提取视频帧图像还是按帧数提取视频帧图像"""
        if self.get_photo_by_sec_flag.get() is False:
            self.label_img["text"] = "帧图像"
            self.inputNum.set(90)
        else:
            self.label_img["text"] = "秒图像(倒数为负，即倒数第三秒则为-3)"
            self.inputNum.set(3)

    def createPage(self):
        self.l_title["text"] = "提取视频帧图像"
        ttk.Label(self.f_input, text='源视频目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.video_dir, width=95).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='图片保存路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.img_dir, width=95).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="按时间", variable=self.get_photo_by_sec_flag, value=True, command=self.change_img_label).grid(row=0, column=1, sticky=tk.W)
        # ttk.Radiobutton(self.f_input_option, text="按帧数", variable=self.get_photo_by_sec_flag, value=False, command=self.change_img_label).grid(row=0, column=2, sticky=tk.W)
        self.get_photo_by_sec_flag.set(True)  # 默认按时间点提取图像
        ttk.Label(self.f_input_option, text='提取第').grid(row=0, column=3, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=10).grid(row=0, column=4, stick=tk.W)
        self.inputNum.set(3)  # 设置默认值为90
        self.label_img = ttk.Label(self.f_input_option, text='秒图像(倒数为负，即倒数第三秒则为-3)')
        self.label_img.grid(row=0, column=5, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=6, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看提取完成帧图像", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.img_dir.get():
            webbrowser.open(self.img_dir.get())

    def video2frames(self, pathIn='', pathOut='', extract_time_point=None, output_prefix='frame', continue_flag=False,
                     isColor=True):
        '''
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
                self.scr.insert("end", "%s 已存在,跳过！\n" % img_path)
                return

        cap = cv2.VideoCapture(pathIn)  # 打开视频文件
        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # 视频的帧数
        fps = cap.get(cv2.CAP_PROP_FPS)  # 视频的帧率
        # dur = n_frames / fps  # 视频的时间
        try:
            dur = n_frames / fps  # 视频的时间
        except ZeroDivisionError:  # 如果文件不是视频文件或已损坏会报除0错误
            raise NameError('文件并非视频文件，或者文件损坏！!')
        #
        # 如果only_output_video_info=True, 只输出视频信息，不提取图片
        print('only output the video information (without extract frames)::::::')
        print(pathIn)
        print("Duration of the video: {} seconds".format(dur))
        print("Number of frames: {}".format(n_frames))
        print("Frames per second (FPS): {}".format(fps))

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
                self.scr.insert("end", "%s 提取完成！\n" % img_path)
            else:
                # 如果opencv框架提取失败，尝试用moviepy框架再提取一次
                total_sec = VideoFileClip(pathIn).duration
                if input_extract_time_point < 0:  # 提取视频倒数第几秒图像
                    extract_time_point = total_sec + input_extract_time_point
                else:
                    extract_time_point = input_extract_time_point
                cap.set(cv2.CAP_PROP_POS_MSEC, (1000 * extract_time_point))
                success, image = cap.read()
                if success:
                    if not isColor:
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # 转化为黑白图片
                    print('Write a new frame: {}'.format(success))
                    cv2.imencode('.jpg', image)[1].tofile(img_path)
                    self.scr.insert("end", "%s 提取完成！\n" % img_path)
                else:
                    raise NameError('文件数据异常!')

    def get_img_by_sec(self, src_path, dst_path, extract_time_point, continue_flag):
        src_path = src_path.strip()
        dst_path = dst_path.strip()
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
        self.scr.insert("end", "%s\n" % msg1)
        self.pb1["maximum"] = len(video_list)  # 总项目数

        # 提取所有视频的第n秒图像,单线程完成
        error_count = 0  # 记录操作失败个数
        for pathIn in video_list:
            pathOut = os.path.dirname(pathIn.replace(src_path, dst_path))
            try:
                self.video2frames(pathIn, pathOut, extract_time_point=extract_time_point, output_prefix=os.path.basename(pathIn), continue_flag=continue_flag)
            except NameError as e:
                error_count += 1
                # print(pathIn, "the max time point is larger than the video duration!")
                error_msg = "【error:%s】%s,%s" % (error_count, pathIn, e)
                print(error_msg)
                self.scr.insert("end", "%s\n" % error_msg)
            self.pb1["value"] += 1
        complete_time = time.time()
        msg = "单线程提取图片完成，总文件数:%s" % len(video_list)
        if error_count:
            msg += "失败数:%s" % error_count
        msg += "提取图片用时%ss，总用时%ss" % (complete_time - tmp_time, complete_time - start_time)
        print(msg)
        self.scr.insert("end", "%s\n" % msg)
        logger.operate_logger(msg, has_time=False)
        mBox.showinfo('完成！', msg)

    @log_error
    def deal_get_img(self):
        get_photo_by_sec_flag = self.get_photo_by_sec_flag.get()
        inputNum = self.inputNum.get()
        continue_flag = self.continue_flag.get()
        video_dir = Mytools.check_path(self.video_dir.get())
        img_dir = Mytools.check_path(self.img_dir.get(), create_flag=True)
        if video_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.video_dir.get())
            return
        if get_photo_by_sec_flag is False:
            if check_positiveIntNum(inputNum) is not True:
                mBox.showerror("错误！", "输入帧数必须为整数")
                return
            msg = get_img_thread.run(self, video_dir, img_dir, inputNum, continue_flag)
            mBox.showinfo('完成！', msg)
        else:
            flag = check_floatNum(inputNum)
            print("flag:", flag)
            if flag is False:
                mBox.showerror("错误！", "输入秒数有误！请检查是否包含非数学字符！")
                return
            self.get_img_by_sec(video_dir, img_dir, inputNum, continue_flag)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        # print(self.video_dir.get(), self.img_dir.get(), self.inputNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_get_img)
        t.start()


class CalImgSimFrame(BaseFrame):
    """计算图片相似度"""
    def __init__(self, master=None):
        super().__init__(master)
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.src_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "计算图片相似度"
        ttk.Label(self.f_input, text='源图片目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1): ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=15).grid(row=0, column=1, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='  导出方式: ').grid(row=0, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row= 0, column=3, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row= 0, column=4, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似图片", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_path.get():
            webbrowser.open(self.dst_path.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            msg = "根据%s,还原了%s个文件，还原文件信息记录到%s" % (self.record_path, count, restore_path)
            mBox.showinfo('还原文件完成！', msg)
            self.scr.insert("end", "%s\n" % msg)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)

    @log_error
    def deal_image_similarity(self):
        # print(self.src_path.get(), self.dst_path.get(), self.threshold.get(), self.option.get())
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), create_flag=True)
        threshold = self.threshold.get()
        option = self.option.get()
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if check_threNum(threshold) is not True:
            mBox.showerror("相似度阈值错误！", "相似度阈值须为0~1之间的小数!")
            return
        threshold = float(threshold)
        record, msg, self.record_path = image_similarity_thread.run(self, src_path, dst_path, threshold, option)
        if len(record):
            self.btn_restore.config(state=tk.NORMAL)
        mBox.showinfo('完成！', msg)

    def run(self):
        self.record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        t = threading.Thread(target=self.deal_image_similarity)
        t.start()


class CalVideoSimFrame(BaseFrame):
    """计算视频相似度"""

    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()  # 输入秒数或者帧数
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.src_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "查找相似视频"
        ttk.Label(self.f_input, text='源视频目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='比对第几秒图像: ').grid(row=0, column=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=15).grid(row=0, column=1, stick=tk.W)
        self.inputNum.set(3)  # 设置默认值为3
        ttk.Label(self.f_input_option, text='相似度阈值(0~1): ').grid(row=0, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=15).grid(row=0, column=3, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='导出方式: ').grid(row=0, column=4, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row=0, column=5, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row=0, column=6, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=7, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似视频", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_path.get():
            webbrowser.open(self.dst_path.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            msg = "根据%s,还原了%s个文件，还原文件信息记录到%s" % (self.record_path, count, restore_path)
            mBox.showinfo('还原文件完成！', msg)
            self.scr.insert("end", "%s\n" % msg)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)

    @log_error
    def deal_video_similarity(self, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
        msg, self.record_path = video_similarity.run(self, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold,
                                   deal_video_mode)
        if self.record_path:
            self.btn_restore.config(state=tk.NORMAL)
        mBox.showinfo("查找相似视频完成!", msg)

    def run(self):
        self.record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), create_flag=True)
        continue_flag = self.continue_flag.get()
        option = self.option.get()
        inputNum = self.inputNum.get()
        threshold = self.threshold.get()
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if check_threNum(threshold) is not True:
            mBox.showerror("相似度阈值错误！", "相似度阈值须为0~1之间的小数!")
            return
        if check_floatNum(inputNum) is not True:
            mBox.showerror("错误！", "输入秒数有误！请检查是否包含非数学字符！")
            return
        threshold = float(threshold)
        inputNum = float(inputNum)
        print(src_path, dst_path, inputNum, continue_flag, threshold, option)
        args = (src_path, dst_path, inputNum, continue_flag, threshold, option)
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.start()


class SearchImgFrame(BaseFrame):
    """以图搜图"""

    def __init__(self, master=None):
        super().__init__(master)
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()  # 操作文件的方式 复制或者剪切
        self.search_dir = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()  # 原有图片路径或者phash json
        self.mode = tk.BooleanVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.search_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.save_dir.set(path_)

    def selectPath3(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.dst_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "以图搜图"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.search_dir, width=92).grid(row=0,  column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.save_dir, width=92).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='原有图片目录或phash: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=92).grid(row=2, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="根据原有图片目录", variable=self.mode, value=True).grid(row=0, column=1, sticky=tk.EW)
        ttk.Radiobutton(self.f_input_option, text="根据原有图片phash信息", variable=self.mode, value=False).grid(row=0, column=2, sticky=tk.EW)
        self.mode.set(True)  # 设置默认值

        ttk.Label(self.f_input_option, text='相似度阈值(0~1):').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=15).grid(row=1, column=1, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='导出方式:').grid(row=0, column=3, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row=0, column=4, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row=0, column=5, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 28
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似图片", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.save_dir.get():
            webbrowser.open(self.save_dir.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            msg = "根据%s,还原了%s个文件，还原文件信息记录到%s" % (self.record_path, count, restore_path)
            mBox.showinfo('还原文件完成！', msg)
            self.scr.insert("end", "%s\n" % msg)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)

    @log_error
    def deal_image_similarity(self):
        # print(self.search_dir.get(), self.save_dir.get(), self.threshold.get(), self.option.get())
        search_dir = Mytools.check_path(self.search_dir.get())
        dst_dir = Mytools.check_path(self.dst_dir.get())
        save_dir = Mytools.check_path(self.save_dir.get(), create_flag=True)
        option = self.option.get()
        threshold = self.threshold.get()
        if search_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.search_dir.get())
            return
        if dst_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dst_dir.get())
            return
        if (search_dir == save_dir) or (dst_dir == save_dir):
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if check_threNum(threshold) is not True:
            mBox.showerror("相似度阈值错误！", "相似度阈值须为0~1之间的小数!")
            return
        threshold = float(threshold)
        record, msg, self.record_path = search_image.run(self, search_dir, dst_dir, save_dir, threshold, option)
        if len(record):
            self.btn_restore.config(state=tk.NORMAL)
        mBox.showinfo('完成！', msg)

    def run(self):
        self.record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        t = threading.Thread(target=self.deal_image_similarity)
        t.start()


class SearchVideoFrame(BaseFrame):
    """以视频搜索相似视频"""

    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.search_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()  # 原有视频路径或者phash json
        self.mode = tk.StringVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.save_dir = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.search_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.save_dir.set(path_)

    def selectPath3(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.dst_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "以视频搜索视频"
        ttk.Label(self.f_input, text='视频样本目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.search_dir, width=92).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='相似视频导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.save_dir, width=92).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='原有视频目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=92).grid(row=2, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)

        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, stick=tk.EW)

        # ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        # ttk.Radiobutton(self, text="根据原有视频目录", variable=self.mode, value="原有视频目录", command=self.changeMode).grid(column=1, row=4, sticky=tk.EW)
        # ttk.Radiobutton(self, text="根据原有视频导出帧图片目录", variable=self.mode, value="原有视频导出帧图片目录", command=self.changeMode).grid(column=2, row=4, sticky=tk.EW)
        # ttk.Radiobutton(self, text="根据原有视频导出帧图片phash信息", variable=self.mode, value="原有视频导出帧图片目录", command=self.changeMode).grid(column=3, row=4, sticky=tk.EW)
        self.mode.set("原有视频目录")  # 设置默认值ttk.Label(self, text='比对第几帧图像: ').grid(row=4, column=0, stick=tk.W, pady=10)
        ttk.Label(self.f_input_option, text='比对第几秒图像:').grid(row=0, column=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=15).grid(row=0, column=1, stick=tk.W)
        self.inputNum.set(3)  # 设置默认值为3
        ttk.Label(self.f_input_option, text='相似度阈值(0~1):').grid(row=0, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=15).grid(row=0, column=3, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='导出方式:').grid(row=0, column=4, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row=0, column=5,
                                                                                                 sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row=0, column=6,
                                                                                                 sticky=tk.W)
        self.option.set("copy")  # 设置默认选中剪切
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=7, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 28
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似视频", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.save_dir.get():
            webbrowser.open(self.save_dir.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            msg = "根据%s,还原了%s个文件，还原文件信息记录到%s" % (self.record_path, count, restore_path)
            mBox.showinfo('还原文件完成！', msg)
            self.scr.insert("end", "%s\n" % msg)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)

    @log_error
    def deal_video_similarity(self, src_dir_path, dst_dir_path, save_dir_path, frame_num, continue_flag, threshold,
                              deal_video_mode):
        msg, self.record_path = search_video.run(self, src_dir_path, dst_dir_path, save_dir_path, frame_num, continue_flag, threshold,
                               deal_video_mode)
        if self.record_path:
            self.btn_restore.config(state=tk.NORMAL)
        mBox.showinfo("查找相似视频完成!", msg)

    def run(self):
        self.record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        # print(self.search_dir.get(), self.dst_dir.get(), self.save_dir.get(), self.inputNum.get(), self.continue_flag.get(), self.threshold.get(), self.option.get())
        search_dir = Mytools.check_path(self.search_dir.get())
        dst_dir = Mytools.check_path(self.dst_dir.get())
        save_dir = Mytools.check_path(self.save_dir.get(), create_flag=True)
        option = self.option.get()
        continue_flag = self.continue_flag.get()
        inputNum = self.inputNum.get()
        threshold = self.threshold.get()
        if search_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.search_dir.get())
            return
        if dst_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dst_dir.get())
            return
        if (search_dir == save_dir) or (dst_dir == save_dir):
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if check_threNum(threshold) is not True:
            mBox.showerror("相似度阈值错误！", "相似度阈值须为0~1之间的小数!")
            return
        if check_floatNum(inputNum) is not True:
            mBox.showerror("错误！", "输入秒数有误！请检查是否包含非数学字符！")
            return
        threshold = float(threshold)
        inputNum = float(inputNum)
        args = (search_dir, dst_dir, save_dir, inputNum, continue_flag, threshold, option)
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.start()


class GetAudioFrame(BaseFrame):
    """从视频中提取音频或者转换音频格式"""

    def __init__(self, master=None):
        super().__init__(master)
        self.format = tk.StringVar()  # 音频格式
        self.frameNum = tk.StringVar()  # 音频帧率
        self.continue_flag = tk.BooleanVar()
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.src_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "提取音频/转换音频"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='保存音频格式: ').grid(row=0, stick=tk.W, column=0, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.format, width=15).grid(row=0, column=1, stick=tk.W)
        self.format.set("wav")  # 设置默认值为wav
        ttk.Label(self.f_input_option, text='音频帧率: ').grid(row=0, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=15).grid(row=0, column=3, stick=tk.W)
        self.frameNum.set(44100)  # 设置默认值为44100
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=4, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @log_error
    def deal_get_audio(self):
        """提取音频"""
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        audio_type = self.format.get()
        if not audio_type.count('.'):
            audio_type = ".%s" % audio_type
        frame_num = self.frameNum.get()
        if frame_num is not None:
            try:
                if check_positiveIntNum(frame_num) is not True:
                    mBox.showerror("错误！", "输入帧率有误！请检查是否包含非数学字符！")
                    return
                frame_num = int(frame_num)
            except Exception:
                mBox.showerror("错误！", "输入帧率有误！请检查是否包含非数学字符！视频帧率须为正整数或者置空，置空则按原帧率")
                return
        else:
            frame_num = None
        start_time = time.time()  # 记录开始时间
        video_list = []  # 用来保存目录下所有视频的路径
        # 遍历文件目录
        for root, dirs, files in os.walk(src_path):
            # 遍历文件夹，在dst_path 下新建和src_path 一样的目录结构
            for file_dir in dirs:
                new_dir = os.path.join(root, file_dir).replace(src_path, dst_path)
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
            for item in files:
                video_list.append(os.path.join(root, item))
        get_video_time_msg = "遍历%s 完成！总共%s个文件,用时%ss\n" % (src_path, len(video_list), (time.time() - start_time))
        print(get_video_time_msg)
        self.scr.insert('end', get_video_time_msg)
        self.pb1["maximum"] = len(video_list)  # 总项目数
        for video_path in video_list:
            audio_path = os.path.splitext(video_path)[0] + audio_type
            audio_path = audio_path.replace(src_path, dst_path)
            print("from:%s, to:%s" % (video_path, audio_path))
            self.scr.insert('end', "from:%s, \n\tto:%s\n" % (video_path, audio_path))
            self.scr.see(tk.END)
            my_audio_clip = AudioFileClip(video_path)
            my_audio_clip.write_audiofile(audio_path, fps=frame_num)
            self.pb1["value"] += 1

        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
        total_msg = "提取目录%s 下视频的音频（帧率：%s）到目录%s 下,用时%.3fs" % (src_path, frame_num, dst_path, time.time() - start_time)
        print(local_time + total_msg)
        mBox.showinfo('完成！', total_msg)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        # print(self.src_dir.get(), self.dst_dir.get(), self.frameNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_get_audio)
        t.start()


class VideoMergeFrame(BaseFrame):
    """视频合并"""

    def __init__(self, master=None):
        super().__init__(master)
        self.format = tk.StringVar()  # 视频格式
        self.frameNum = tk.StringVar()  # 视频帧率 ， 不填则为原视频帧率
        self.continue_flag = tk.BooleanVar()
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.src_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "视频合并"
        ttk.Label(self.f_input, text='源视频目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)

        ttk.Label(self.f_input_option, text='视频输出格式:').grid(row=0, stick=tk.W, column=0, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.format, width=15).grid(row=0, column=1, stick=tk.W)
        self.format.set("mp4")  # 设置默认值为MP4
        ttk.Label(self.f_input_option, text='视频帧率:').grid(row=0, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=15).grid(row=0, column=3, stick=tk.W)
        self.frameNum.set(24)  # 设置默认值为24
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=4, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Checkbutton(self.f_input_option, text="继承原文件修改时间", variable=self.original_mtime_flag, onvalue=True, offvalue=False).grid(row=0, column=5, sticky=tk.W, padx=10)
        self.original_mtime_flag.set(True)  # 设置默认选中是
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    def do_merge(self, new_dir, old_dir, video_type, frame_num):
        """进行视频合并操作"""
        video_list = []  # 存储每个目录下视频路径
        time_str = None  # 时间字符串
        timestamp = None  # 时间戳
        original_mtime_flag = self.original_mtime_flag.get()
        # 遍历文件目录获取每个目录下的视频文件
        file_list = natsorted(os.listdir(old_dir))  # 按文件名自然数顺序排序
        for file in file_list:
            # 拼接成完整路径
            file_path = os.path.join(old_dir, file)
            if os.path.isdir(file_path):
                continue
            # 输出信息到GUI界面
            self.scr.insert('end', "video: \t%s\n" % file)
            self.scr.see(tk.END)
            # 载入视频
            # print('current_file:', file)
            timestamp = os.path.getmtime(file_path)
            # print("timestamp:", timestamp)
            time_str = time.strftime("%Y%m%d%H%M%S", time.localtime(timestamp))
            # print("modify_time of %s is: %s" % (file_path, time_str))
            video = VideoFileClip(file_path)
            video_list.append(video)

        if len(video_list):
            # 拼接视频
            final_clip = concatenate_videoclips(video_list)
            # 生成目标视频文件
            dir_name = os.path.basename(old_dir)
            new_file = os.path.join(new_dir, dir_name + time_str + video_type)
            self.scr.insert('end', "正在合并 目录%s 下的视频到 %s\n" % (old_dir, new_file))
            final_clip.write_videofile(new_file, fps=frame_num, remove_temp=True)
            # 修改文件的修改时间和创建时间
            if original_mtime_flag is True:
                os.utime(new_file, (timestamp, timestamp))

    @log_error
    def deal_video_merge(self):
        """合并视频"""
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        video_type = self.format.get()
        if not video_type.count('.'):
            video_type = ".%s" % video_type  # 类型前加. 拼接文件后缀名
        frame_num = self.frameNum.get()  # 帧率
        if frame_num is not None:
            try:
                if check_positiveIntNum(frame_num) is not True:
                    mBox.showerror("错误！", "输入帧率有误！请检查是否包含非数学字符！")
                    return
                frame_num = int(frame_num)
            except Exception:
                mBox.showerror("错误！", "输入帧率有误！请检查是否包含非数学字符！视频帧率须为正整数或者置空，置空则按原帧率")
                return
        else:
            frame_num = None
        start_time = time.time()  # 记录开始时间
        # 访问 video 文件夹 (假设视频都放在这里面)
        # 遍历文件目录
        for root, dirs, files in os.walk(src_path):
            self.pb1["maximum"] = len(dirs)  # 总项目数
            for src_dir in dirs:
                # 遍历文件夹，在dst_path 下新建和src_path 一样的目录结构
                old_dir = os.path.join(root, src_dir)
                new_dir = old_dir.replace(src_path, dst_path)
                self.scr.insert('end', "正在遍历 目录%s \n" % old_dir)
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                self.do_merge(new_dir, old_dir, video_type, frame_num)  # 合并src_path下子目录中的视频
        self.do_merge(dst_path, src_path, video_type, frame_num)  # 合并src_path本身目录下的视频

        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
        total_msg = "合并目录%s 下视频（帧率：%s）到%s 下,用时%.3fs" % (src_path, frame_num, dst_path, time.time() - start_time)
        print(local_time + total_msg)
        mBox.showinfo('完成！', total_msg)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        print(self.src_dir.get(), self.dst_dir.get(), self.frameNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_video_merge)
        t.start()


class Task(object):
    """任务对象类, 用于搭配VideoCutFrame使用"""
    def __init__(self, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag=False, original_mtime_flag=False):
        super().__init__()
        self.pathIn = pathIn
        self.pathOut = pathOut
        self.sub_start_time = sub_start_time
        self.sub_stop_time = sub_stop_time
        self.fps = fps
        self.continue_flag = continue_flag
        self.original_mtime_flag = original_mtime_flag
        self.status = 0  # 'status':状态，0：未完成，1：已完成，2：错误


class VideoCutFrame(BaseFrame):
    """视频裁剪"""

    def __init__(self, master=None):
        super().__init__(master)
        self.record_path = None  # 视频导出地址
        self.log_path = os.path.join(settings.LOG_DIR, "videoCutLog.txt")  # 日志地址
        self.task_list = []  # 任务列表
        self.task_status_dict = {0: "进行中", 1: "已完成", 2: "错误"}  # 状态码
        self.task_status_color_dict = {0: "blue", 1: "green", 2: "red"}  # 状态码对应颜色
        self.sub_start_time_h = tk.StringVar()  # 获取开始剪切时间 小时
        self.sub_start_time_m = tk.StringVar()  # 获取开始剪切时间 分钟
        self.sub_start_time_s = tk.StringVar()  # 获取开始剪切时间 秒
        self.sub_stop_time_h = tk.StringVar()  # 获取剪切结束时间
        self.sub_stop_time_m = tk.StringVar()  # 获取剪切结束时间
        self.sub_stop_time_s = tk.StringVar()  # 获取剪切结束时间
        self.frameNum = tk.StringVar()  # 视频帧率
        self.invoke_fps_flag = tk.BooleanVar()  # 是否激活帧率输入框
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.createPage()
        self.getLogger()  # 获取日志对象
        self.run()  # 启动一个子线程用来监听并执行self.task_list 任务列表中的任务

    def getLogger(self):
        """创建日志对象"""
        # 第一步，创建一个logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)  # Log等级总开关

        # 第二步，创建一个handler，用于写入日志文件
        log_dir = settings.LOG_DIR
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        logfile = os.path.join(log_dir, "videoCutLog.txt")
        fh = logging.FileHandler(logfile, mode='a')  # open的打开模式这里可以进行参考
        fh.setLevel(logging.DEBUG)  # 输出到file的log等级的开关

        # 第三步，再创建一个handler，用于输出到控制台
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)  # 输出到console的log等级的开关

        # 第四步，定义handler的输出格式
        formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # 第五步，将logger添加到handler里面
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def check_path(self, dir_path, create_flag=False):
        """用于检测输入路径是否正确,
            dir_path        目录路径
            create_flag     标记是否新建目录
                            True如果目录不存在则新建
                            False不新建
        """
        if dir_path:  # 有输入内容
            dir_path = dir_path.strip()  # 防止出现输入' '
            if os.path.exists(dir_path):  # 检查路径是否存在
                # 当输入'/home/'时获取文件名就是''，所以加处理
                dir_path = os.path.abspath(dir_path)
                return dir_path
            else:
                if create_flag:
                    # print("输入目录不存在！已为您新建该目录！")
                    os.makedirs(dir_path)
                    dir_path = os.path.abspath(dir_path)
                    return dir_path
                else:
                    return
        else:
            print("输入路径有误，请重新输入！")
            return

    def get_float_value(self, key, default_value):
        """用于获取输入框中的值，如果不输入则返回默认值"""
        if key:
            try:
                key = float(key)
            except Exception:
                key = default_value
        else:
            key = default_value
        return key

    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.record_path = None
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def selectPath(self):
        self.src_dir.set(askopenfilename())
        self.record_path = None
        self.dst_dir.set("")

    def createPage(self):
        """页面布局"""
        self.l_title["text"] = "视频裁剪"
        ttk.Label(self.f_input, text='源视频:').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=2)

        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='输出格式:').grid(row=0, column=0, stick=tk.W, pady=10)
        ttk.Label(self.f_input_option, text='MP4  ').grid(row=0, column=1, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="修改帧率", variable=self.invoke_fps_flag, onvalue=True,
                        offvalue=False, command=self.invoke_fps).grid(row=0, column=2, sticky=tk.EW, padx=10)
        self.e_fps = ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=10, state=tk.DISABLED)  # 视频帧率输入框
        self.e_fps.grid(row=0, column=3, stick=tk.W)
        self.frameNum.set("")  # 设置默认值
        ttk.Checkbutton(self.f_input_option, text="继承原修改时间", variable=self.original_mtime_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=4, sticky=tk.EW, padx=10)
        self.original_mtime_flag.set(False)  # 设置默认选中否
        self.f_time_option = ttk.Frame(self.f_input)  # 时间输入容器
        self.f_time_option.grid(row=3, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_time_option, text='开始时间: ').grid(row=1, column=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_h, width=5).grid(row=1, column=1, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_m, width=5).grid(row=1, column=3, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=4, stick=tk.W, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_s, width=5).grid(row=1, column=5, stick=tk.W)
        ttk.Label(self.f_time_option, text='    结束时间: ').grid(row=1, column=6, stick=tk.W, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_h, width=5).grid(row=1, column=7, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=8, stick=tk.W, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_m, width=5).grid(row=1, column=9, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=10, stick=tk.W, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_s, width=5).grid(row=1, column=11, stick=tk.W)
        ttk.Label(self.f_time_option, text='', width=20).grid(row=1, column=12)  # 占位，无意义
        ttk.Button(self.f_time_option, text="查看日志", command=self.showLog).grid(row=1, column=13)
        ttk.Button(self.f_time_option, text="添加任务", command=self.create_task).grid(row=1, column=14)
        self.l_task_state = ttk.Label(self.f_state, text="当前任务：", font=('微软雅黑', 16))
        self.l_task_state.pack()
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=2, columnspan=2, sticky='WE')
        windnd.hook_dropfiles(self.root, func=self.dragged_files)  # 监听文件拖拽操作

    def invoke_fps(self):
        """激活帧率输入框"""
        invoke_fps_flag = self.invoke_fps_flag.get()
        if invoke_fps_flag:
            self.e_fps.config(state=tk.NORMAL)
        else:
            self.frameNum.set('')
            self.e_fps.config(state=tk.DISABLED)

    def showLog(self):
        """查看日志"""
        if self.log_path:
            webbrowser.open(self.log_path)

    def create_task(self):
        """创建任务"""
        pathIn = self.check_path(self.src_dir.get())
        fps = self.frameNum.get().strip()  # 帧率
        if fps:
            try:
                fps = float(fps)
            except Exception:
                fps = None
        else:
            fps = None

        # 获取截取时间段
        sub_start_time_h = self.sub_start_time_h.get().strip()  # 获取开始剪切时间
        sub_start_time_m = self.sub_start_time_m.get().strip()  # 获取开始剪切时间
        sub_start_time_s = self.sub_start_time_s.get().strip()  # 获取开始剪切时间
        sub_stop_time_h = self.sub_stop_time_h.get().strip()  # 获取剪切的结束时间
        sub_stop_time_m = self.sub_stop_time_m.get().strip()  # 获取剪切的结束时间
        sub_stop_time_s = self.sub_stop_time_s.get().strip()  # 获取剪切的结束时间

        try:
            sub_start_time_h = self.get_float_value(sub_start_time_h, 0)  # 获取开始剪切时间
            sub_start_time_m = self.get_float_value(sub_start_time_m, 0)  # 获取开始剪切时间
            sub_start_time_s = self.get_float_value(sub_start_time_s, 0)  # 获取开始剪切时间
            sub_stop_time_h = self.get_float_value(sub_stop_time_h, 0)  # 获取剪切的结束时间
            sub_stop_time_m = self.get_float_value(sub_stop_time_m, 0)  # 获取剪切的结束时间
            sub_stop_time_s = self.get_float_value(sub_stop_time_s, 0)  # 获取剪切的结束时间
            sub_start_time = sub_start_time_h*3600 + sub_start_time_m*60 + sub_start_time_s
            sub_stop_time = sub_stop_time_h*3600 + sub_stop_time_m*60 + sub_stop_time_s
            file_name = os.path.basename(pathIn)
            self.record_path = os.path.join(os.path.dirname(pathIn), "videoCut")
            pathOut = os.path.join(self.record_path, "%s_(%ss_to_%ss).mp4" % (file_name, sub_start_time, sub_stop_time))
            self.dst_dir.set(pathOut)  # 显示导出路径到界面
            original_mtime_flag = self.original_mtime_flag.get()  # 继承原文件修改时间信息
            if pathIn is None:
                mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
                return
            if pathIn == pathOut:
                mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
                return
            continue_flag = False

            # 创建任务信息
            task = Task(pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
            self.task_list.append(task)
            self.show_tasks()  # 刷新任务列表状态
            mBox.showinfo("ok", "创建任务成功！")
        except Exception as e:
            self.record_path = None
            mBox.showerror("错误！", e)
            return

    def show_tasks(self):
        """用于展示所有任务信息"""
        self.scr.delete(1.0, "end")
        total_count = len(self.task_list)  # 总任务数
        done_count = 0  # 完成任务数
        todo_count = 0  # 等待中的任务数
        error_count = 0  # 错误的任务数
        for task in self.task_list:
            pathIn = task.pathIn
            pathOut = task.pathOut
            sub_start_time = task.sub_start_time
            sub_stop_time = task.sub_stop_time
            fps = task.fps
            continue_flag = task.continue_flag
            original_mtime_flag = task.original_mtime_flag
            status = task.status
            if status == 0:
                todo_count += 1
            elif status == 1:
                done_count += 1
            else:
                error_count += 1
            status = self.task_status_dict.get(status)
            status_color = self.task_status_color_dict.get(task.status)
            if status is None:  # 状态码异常
                status = "状态异常"
                status_color = "orange"
            msg = "PathIn: %s\n" % pathIn
            msg += "PathOut: %s\n" % pathOut
            msg += "截取开始: %s秒\n" % sub_start_time
            msg += "截取结束: %s秒\n" % sub_stop_time
            msg += "帧率: %s\n" % fps
            msg += "还原修改时间: %s\n" % original_mtime_flag
            msg += "状态: "
            self.scr.insert("end", msg)
            self.scr.insert("end", status, status_color)  # 插入任务状态，附带标签
            self.scr.tag_config(status_color, foreground=status_color)
            self.scr.insert("end", "\n\n\n")
        # 更新任务状态标签
        self.l_task_state["text"] = "当前任务：(总共：%s，%s进行中，%s已完成，%s错误)" % (total_count, todo_count, done_count, error_count)

    def do_video_cut_single(self, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag=False,
                            original_mtime_flag=False):
        """裁剪视频，处理单个文件"""
        start_time = time.time()  # 记录开始时间
        if not os.path.exists(pathIn):
            return
        if pathIn == pathOut:
            print("源路径与目标路径一致！")
            return
        if os.path.isdir(pathOut):
            pathOut = os.path.join(pathOut, os.path.basename(pathIn))
        if continue_flag is True:
            if os.path.exists(pathOut):
                return
        print(pathIn, ">>>", pathOut)
        pathOutDir = os.path.dirname(pathOut)
        if not os.path.exists(pathOutDir):
            os.makedirs(pathOutDir)
        total_sec = VideoFileClip(pathIn).duration
        print("moviepy get totalsec: ", total_sec)
        if sub_stop_time < 0:  # 截取倒数第几秒
            sub_stop_time = total_sec + sub_stop_time
        video = VideoFileClip(pathIn)  # 视频文件加载
        video = video.subclip(sub_start_time, sub_stop_time)  # 执行剪切操作

        # video.write_videofile(pathOut, fps=fps, remove_temp=True)  # 输出文件
        video.write_videofile(pathOut, fps=fps, audio_codec='aac', remove_temp=True)  # 输出文件

        # 将裁剪后视频修改时间变更为源视频修改时间
        if original_mtime_flag is True:
            timestamp = os.path.getmtime(pathIn)
            os.utime(pathOut, (timestamp, timestamp))
        msg = "裁剪%s 第%s秒至第%s秒视频完成!" % (pathIn, sub_start_time, sub_stop_time)
        print(msg)
        msg += "总用时%.3fs" % (time.time() - start_time)
        self.logger.info(msg)
        # mBox.showinfo('完成！', msg)

    def run_task(self):
        """循环检测并执行任务列表里的任务"""
        while True:
            if len(self.task_list):
                for task in self.task_list:
                    if not (task.status == 0):
                        continue
                    pathIn = task.pathIn
                    pathOut = task.pathOut
                    sub_start_time = task.sub_start_time
                    sub_stop_time = task.sub_stop_time
                    fps = task.fps
                    continue_flag = task.continue_flag
                    original_mtime_flag = task.original_mtime_flag
                    args = (pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
                    try:
                        self.do_video_cut_single(*args)  # 自动拆包传参
                        task.status = 1
                        print("task:%s complete!" % str(task))
                    except Exception as e:
                        task.status = 2
                        print("出错了：", e)
                        msg = "裁剪%s 第%s秒至第%s秒视频出错!" % (pathIn, sub_start_time, sub_stop_time)
                        msg += " 错误：%s" % e
                        self.logger.error(msg)
                    finally:
                        self.show_tasks()  # 刷新任务列表状态
            time.sleep(1)

    def run(self):
        """运行程序"""
        t = threading.Thread(target=self.run_task)
        t.setDaemon(True)
        t.start()


class VideosCutFrame(BaseFrame):
    """批量视频裁剪"""

    def __init__(self, master=None):
        super().__init__(master)
        self.format = tk.StringVar()  # 视频格式
        self.sub_start_time = tk.StringVar()  # 获取开始剪切时间
        self.sub_stop_time = tk.StringVar()  # 获取剪切结束时间
        self.frameNum = tk.StringVar()  # 视频帧率
        self.continue_flag = tk.BooleanVar()  # 是否继续上次进度
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.bat_flag = tk.BooleanVar()  # 是否批量操作， True 操作目录， False操作单个文件
        self.createPage()

    def selectPath1(self):
        if self.bat_flag.get():
            self.src_dir.set(askdirectory())
        else:
            self.src_dir.set(askopenfilename())

    def selectPath2(self):
        # if self.bat_flag.get():
        #     self.dst_dir.set(askdirectory())
        # else:
        #     self.dst_dir.set(asksaveasfilename())
        self.dst_dir.set(askdirectory())

    def createPage(self):
        self.l_title["text"] = "批量视频裁剪"
        ttk.Label(self.f_input, text='源视频目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)

        ttk.Label(self.f_input_option, text='视频输出格式:').grid(row=0, stick=tk.W, column=0, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.format, width=15).grid(row=0, column=1, stick=tk.W)
        self.format.set("mp4")  # 设置默认值为MP4
        ttk.Label(self.f_input_option, text='视频帧率:').grid(row=0, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=15).grid(row=0, column=3, stick=tk.W)
        self.frameNum.set(24)  # 设置默认值为24
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=4, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Checkbutton(self.f_input_option, text="继承原文件修改时间", variable=self.original_mtime_flag, onvalue=True, offvalue=False).grid(row=0, column=5, sticky=tk.W, padx=10)
        self.original_mtime_flag.set(False)  # 设置默认选中否
        ttk.Label(self.f_input_option, text='截取开始时间(s): ').grid(row=1, stick=tk.W, column=0, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.sub_start_time, width=15).grid(row=1, column=1, stick=tk.W)
        ttk.Label(self.f_input_option, text='截取结束时间(s): ').grid(row=1, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.sub_stop_time, width=15).grid(row=1, column=3, stick=tk.W)
        ttk.Label(self.f_input_option, text='是否批量操作: ').grid(row=1, column=4, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="操作目录", variable=self.bat_flag, value=True).grid(row=1, column=5,
                                                                                                     sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="操作文件", variable=self.bat_flag, value=False).grid(row=1, column=6,
                                                                                                      sticky=tk.W)
        self.bat_flag.set(True)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @log_error
    def deal_video_cut(self):
        """批量裁剪一个目录下所有视频"""
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        continue_flag = self.continue_flag.get()
        original_mtime_flag = self.original_mtime_flag.get()  # 继承原文件修改时间信息
        fps = self.frameNum.get().strip()  # 帧率
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if fps:
            try:
                fps = float(fps)
            except Exception:
                fps = None
        else:
            fps = None
        start_time = time.time()  # 记录开始时间
        # 访问 video 文件夹 (假设视频都放在这里面)
        sub_start_time = float(self.sub_start_time.get().strip())  # 获取开始剪切时间
        sub_stop_time = float(self.sub_stop_time.get().strip())  # 获取剪切的结束时间

        # 遍历获取所有视频路径
        video_list = []
        if os.path.isfile(src_path):
            self.do_video_cut_single(src_path, dst_path, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
            local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
            total_msg = "总用时%.3fs" % (time.time() - start_time)
            print(local_time + total_msg)
            self.scr.insert("end", "%s \n" % (local_time + total_msg))
            mBox.showinfo('完成！', total_msg)
            return
        else:
            # 是目录
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    video_list.append(os.path.join(root, file))

        msg = "遍历%s完成，共发现文件%s个，用时%ss" % (src_path, len(video_list), time.time() - start_time)
        print(msg)
        self.scr.insert("end", "%s！\n" % msg)
        self.pb1["maximum"] = len(video_list)  # 总项目数
        for item in video_list:
            try:
                self.do_video_cut(item, src_path, dst_path, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
                self.scr.insert("end", "%s 剪辑完成！\n" % item)
            except Exception as e:
                self.scr.insert("end", "%s 剪辑过程出错！错误：%s\n" % (item, e))
            self.pb1["value"] += 1

        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
        total_msg = "总用时%.3fs" % (time.time() - start_time)
        print(local_time + total_msg)
        self.scr.insert("end", "%s \n" % (local_time + total_msg))
        mBox.showinfo('完成！', total_msg)

    def do_video_cut_single(self, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag=False, original_mtime_flag=False):
        """裁剪视频，处理单个文件"""
        # 访问 video 文件夹 (假设视频都放在这里面)
        if not os.path.exists(pathIn):
            return
        if pathIn == pathOut:
            print("源路径与目标路径一致！")
            self.scr.insert("end", "%s 源路径与目标路径一致, 已跳过！" % pathIn)
            return
        if os.path.isdir(pathOut):
            pathOut = os.path.join(pathOut, os.path.basename(pathIn))
        if continue_flag is True:
            if os.path.exists(pathOut):
                return
        print(pathIn, ">>>", pathOut)
        pathOutDir = os.path.dirname(pathOut)
        if not os.path.exists(pathOutDir):
            os.makedirs(pathOutDir)
        total_sec = VideoFileClip(pathIn).duration
        print("moviepy get totalsec: ", total_sec)
        if sub_stop_time < 0:  # 截取倒数第几秒
            sub_stop_time = total_sec + sub_stop_time
        video = VideoFileClip(pathIn)  # 视频文件加载
        video = video.subclip(sub_start_time, sub_stop_time)  # 执行剪切操作
        video.write_videofile(pathOut, fps=fps, remove_temp=True)  # 输出文件

        # 将裁剪后视频修改时间变更为源视频修改时间
        if original_mtime_flag is True:
            timestamp = os.path.getmtime(pathIn)
            os.utime(pathOut, (timestamp, timestamp))
        print("裁剪%s 第%s秒至第%s秒视频完成" % (pathIn, sub_start_time, sub_stop_time))

    def do_video_cut(self, pathIn, src_path, dst_path, sub_start_time, sub_stop_time, fps, continue_flag=False, original_mtime_flag=False):
        """裁剪视频, 处理目录下多个文件"""
        # 访问 video 文件夹 (假设视频都放在这里面)
        print(pathIn, src_path, dst_path, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
        if not os.path.exists(pathIn):
            return
        pathOut = pathIn.replace(src_path, dst_path)
        if pathIn == pathOut:
            print("源路径与目标路径一致！")
            self.scr.insert("end", "%s 源路径与目标路径一致, 已跳过！" % pathIn)
            return
        if continue_flag is True:
            if os.path.exists(pathOut):
                return
        print(pathIn, ">>>", pathOut)
        pathOutDir = os.path.dirname(pathOut)
        if not os.path.exists(pathOutDir):
            os.makedirs(pathOutDir)
        total_sec = VideoFileClip(pathIn).duration
        print("moviepy get totalsec: ", total_sec)
        if sub_stop_time < 0:  # 截取倒数第几秒
            sub_stop_time = total_sec + sub_stop_time
        video = VideoFileClip(pathIn)  # 视频文件加载
        video = video.subclip(sub_start_time, sub_stop_time)  # 执行剪切操作

        video.write_videofile(pathOut, fps=fps, remove_temp=True)  # 输出文件

        # 将裁剪后视频修改时间变更为源视频修改时间
        if original_mtime_flag is True:
            timestamp = os.path.getmtime(pathIn)
            os.utime(pathOut, (timestamp, timestamp))
        print("裁剪%s 第%s秒至第%s秒视频完成" % (pathIn, sub_start_time, sub_stop_time))

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        print(self.src_dir.get(), self.dst_dir.get(), self.frameNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_video_cut)
        t.start()


class GetTimestampFrame(BaseFrame):  # 继承Frame类
    """获取时间戳"""
    def __init__(self, master=None):
        super().__init__(master)
        self.input_time = tk.StringVar()
        self.input_timestamp = tk.StringVar()
        self.select_file = None
        self.record_path = None  # 导出的记录文件路径
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "获取时间戳"
        ttk.Label(self.f_input, text="输入时间标准格式(例如：'2021-03-19 09:28:00'): ").grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.input_time, width=80).grid(row=1, column=0, stick=tk.E)
        ttk.Button(self.f_input, text="当前时间", command=self.get_current_time).grid(row=1, column=1)
        ttk.Label(self.f_input, text="输入时间戳: ").grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.input_timestamp, width=80).grid(row=3, column=0, stick=tk.E)
        ttk.Button(self.f_input, text="当前时间戳", command=self.get_current_timestamp).grid(row=3, column=1)

        ttk.Button(self.f_option, text="读取文件时间戳", command=self.get_file_timestamp).grid(row=0, column=1)
        ttk.Button(self.f_option, text="时间转换为时间戳", command=self.time_to_timestamp).grid(row=0, column=2)
        ttk.Button(self.f_option, text="时间戳转换为时间", command=self.timestamp_to_time).grid(row=0, column=3)

        ttk.Label(self.f_content, text='结果: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 90
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=1, sticky='WE', columnspan=5)

    def selectPath(self):
        self.select_file = askopenfilename()

    def get_current_timestamp(self):
        """获取当时时间戳"""
        self.input_timestamp.set(time.time())

    def get_current_time(self):
        self.input_time.set(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))

    def get_file_timestamp(self):
        """获取文件时间戳"""
        self.selectPath()
        self.scr.delete(1.0, 'end')
        file_path = self.select_file
        if not os.path.exists(file_path):
            self.scr.insert('end', "您输入的路径：%s 不存在！" % file_path)
            return
        file_timestampc = os.path.getctime(self.select_file)
        file_timestampa = os.path.getatime(self.select_file)
        file_timestampm = os.path.getmtime(self.select_file)
        msg = "文件：%s 的时间戳为\n" % self.select_file
        msg += "文件创建时间戳：%s\n" % file_timestampc
        msg += "文件创建本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampc))
        msg += "文件修改时间戳：%s\n" % file_timestampm
        msg += "文件修改本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampm))
        msg += "文件最后访问时间戳：%s\n" % file_timestampa
        msg += "文件最后访问本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampa))
        self.scr.insert("end", msg)

    def time_to_timestamp(self):
        """时间转换为时间戳"""
        self.scr.delete(1.0, 'end')
        input_time = self.input_time.get()
        if input_time:
            try:
                msg = "时间：'%s' \n-->时间戳为: '%s'\n" % (input_time, time.mktime(time.strptime(input_time, '%Y-%m-%d %H:%M:%S')))
                self.scr.insert("end", msg)
            except ValueError:
                mBox.showerror("错误", "时间格式输入错误！")

    def timestamp_to_time(self):
        """时间戳转换为时间"""
        self.scr.delete(1.0, 'end')
        input_timestamp = self.input_timestamp.get()
        if input_timestamp:
            try:
                input_timestamp = float(self.input_timestamp.get())
                get_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(input_timestamp))
                msg = "时间戳：'%s' \n-->时间为: '%s'\n" % (input_timestamp, get_time)
                self.scr.insert("end", msg)
            except Exception:
                mBox.showerror("错误", "输入时间戳格式有误！须为纯数字或小数")


class ChangeTimestampFrame(BaseFrame):  # 继承Frame类
    """修改文件时间戳"""
    def __init__(self, master=None):
        super().__init__(master)
        self.file_path = tk.StringVar()  # 文件所在路径
        self.m_timestamp = tk.StringVar()  # 修改时间的时间戳
        # self.a_timestamp = tk.StringVar()  # 最后一次时间的时间戳
        # self.select_file = None
        self.record_path = None  # 导出的记录文件路径
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "修改文件时间戳"
        ttk.Label(self.f_input, text="文件路径: (或者直接拖拽文件进入程序界面)").grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.file_path, width=110).grid(row=1, column=0, stick=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=1, column=1)
        ttk.Label(self.f_input, text="输入修改时间的时间戳:(置空则为当前时间戳) ").grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.m_timestamp, width=110).grid(row=3, column=0, stick=tk.EW)
        ttk.Button(self.f_input, text="查看文件时间戳", command=self.get_file_timestamp).grid(row=3, column=1)
        ttk.Button(self.f_input, text="修改文件时间戳", command=self.change_file_timestamp).grid(row=7, column=1, pady=10)
        ttk.Label(self.f_content, text='结果: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=1, sticky='WE', columnspan=5)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def selectPath(self):
        self.file_path.set(askopenfilename())

    def dragged_files(self, files):
        """拖拽到程序，获取文件路径"""
        # path_list = []
        # for item in files:
        #     dir_path = item.decode(settings.SYSTEM_CODE_TYPE)  # 修改配置之后下次就会用新的配置
        #     path_list.append(dir_path)

        # 设为获取单文件路径
        for item in files:
            file_path = item.decode(settings.SYSTEM_CODE_TYPE)  # 修改配置之后下次就会用新的配置
            self.file_path.set(file_path)

    def get_file_timestamp(self):
        """获取文件时间戳"""
        self.scr.delete(1.0, 'end')
        # 获取文件路径
        file_path = self.file_path.get()

        # 显示文件时间戳信息
        file_timestampc = os.path.getctime(file_path)
        file_timestampa = os.path.getatime(file_path)
        file_timestampm = os.path.getmtime(file_path)
        msg = "文件：%s 的时间戳为\n" % file_path
        msg += "文件创建时间戳：%s\n" % file_timestampc
        msg += "文件创建本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampc))
        msg += "文件修改时间戳：%s\n" % file_timestampm
        msg += "文件修改本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampm))
        msg += "文件最后访问时间戳：%s\n" % file_timestampa
        msg += "文件最后访问本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampa))
        self.scr.insert("end", msg)

    def change_file_timestamp(self):
        """修改文件时间戳"""
        self.scr.delete(1.0, 'end')

        # 获取文件路径
        file_path = self.file_path.get()
        # 获取修改时间的时间戳
        now_timestamp = time.time()
        m_timestamp = self.m_timestamp.get()

        # 判断输入时间戳是否正常，不正确则置为当前时间
        try:
            m_timestamp = float(m_timestamp)
        except Exception:
            m_timestamp = now_timestamp

        # 修改文件时间戳
        os.utime(file_path, (m_timestamp, m_timestamp))
        # 显示文件时间戳信息
        file_timestampc = os.path.getctime(file_path)
        file_timestampa = os.path.getatime(file_path)
        file_timestampm = os.path.getmtime(file_path)
        msg = "文件：%s 的时间戳修改为\n" % file_path
        msg += "文件创建时间戳：%s\n" % file_timestampc
        msg += "文件创建本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampc))
        msg += "文件修改时间戳：%s\n" % file_timestampm
        msg += "文件修改本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampm))
        msg += "文件最后访问时间戳：%s\n" % file_timestampa
        msg += "文件最后访问本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampa))
        self.scr.insert("end", msg)


class FindBadVideoFrame(BaseFrame):  # 继承Frame类
    """查找损坏视频文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()  # 模式 "基于filecmp模块", "自己实现的Mybackup,节省IO资源占用", "备份端目录变更同步"
        self.src_path = tk.StringVar()  # 源目录
        self.dst_path = tk.StringVar()  # 目的目录
        self.option = tk.StringVar()
        self.ffmpeg_path = tk.StringVar()  # ffmpeg程序所在目录
        # self.exeState = tk.StringVar()  # 用于动态更新程序执行任务状态
        # self.proState = tk.StringVar()  # 用于动态更新程序运行状态，running

        self.createPage()

    def selectPath1(self):
        self.src_path.set(askdirectory())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def selectPath2(self):
        self.dst_path.set(askdirectory())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def selectPath3(self):
        self.ffmpeg_path.set(askopenfilename())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def showFiles(self):
        """查看结果目录"""
        if self.dst_path.get():
            webbrowser.open(self.dst_path.get())

    def findBadVideos(self):
        """找出损坏的视频文件"""
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), create_flag=True)
        ffmpeg_path = Mytools.check_path(self.ffmpeg_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if ffmpeg_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.ffmpeg_path.get())
            return
        start_time = time.time()  # 程序开始时间
        # src_path = os.path.abspath(src_path)
        # dst_path = os.path.abspath(dst_path)
        # ffmpeg_path = os.path.abspath(ffmpeg_path)

        # 遍历获取文件路径列表
        self.scr.insert("end", "%s\n" % "开始遍历文件目录...")
        self.exeStateLabel["text"] = "遍历文件目录..."
        self.proStateLabel["text"] = "running..."
        video_list = []  # 文件列表
        for root, dirs, files in os.walk(src_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not file.endswith(".mp4"):
                    continue
                if file.count(" "):
                    new_file_path = os.path.join(root, file.replace(" ", "_"))
                    os.rename(file_path, new_file_path)
                    file_path = new_file_path
                video_list.append(file_path)

        # 设置进度条
        self.scr.insert("end", "%s\n" % "遍历目录完成！")
        self.pb1["maximum"] = len(video_list)  # 总项目数

        # 调用命令快速校验视频文件
        # 拼接命令列表
        self.exeStateLabel["text"] = "校验视频文件..."
        self.scr.insert("end", "%s\n" % "开始校验视频文件...")
        for file_path in video_list:
            log_path = file_path+'.log'
            cmd_str = "%s -v error -i %s -f null - >%s 2>&1" % (ffmpeg_path, file_path, log_path)
            os.system(cmd_str)
            self.pb1["value"] += 1

        # 排除无错的log
        self.exeStateLabel["text"] = "统计结果..."
        self.pb1["value"] = 0
        bad_videos = []  # 不完整视频列表
        for root, dirs, files in os.walk(src_path):
            for file in files:
                if file.endswith(".log"):
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        os.remove(file_path)
                    else:
                        video_path = os.path.splitext(file_path)[0]
                        print(video_path, " 文件不完整！")
                        self.scr.insert("end", "%s  %s\n" % (video_path, "文件不完整！"))
                        bad_videos.append(video_path)
                        dst_video = video_path.replace(src_path, dst_path)
                        dst_dir = os.path.dirname(dst_video)
                        if not os.path.exists(dst_dir):
                            os.makedirs(dst_dir)
                        shutil.move(video_path, dst_video)
                        shutil.move(file_path, file_path.replace(src_path, dst_path))
                    self.pb1["value"] += 1
        tmp_time = time.time()
        self.exeStateLabel["text"] = "操作完成!"
        self.proStateLabel["text"] = "complete!"
        msg = "遍历%s完成，总共%s个视频文件，共发现不完整视频文件%s个，用时%ss" % (src_path, len(video_list), len(bad_videos), tmp_time - start_time)
        print(msg)
        self.scr.insert("end", msg)

    def run(self):
        """主进程主函数"""
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""
        self.scr.delete(1.0, 'end')  # 清空文本区
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), True)
        ffmpeg_path = Mytools.check_path(self.ffmpeg_path.get())
        if src_path and dst_path and ffmpeg_path:
            t = threading.Thread(target=self.findBadVideos)
            t.start()
        else:
            mBox.showerror("路径不存在！", "输入的路径不存在！请检查！")
            return

    def createPage(self):
        self.l_title["text"] = "找出损坏/不完整的视频文件"
        ttk.Label(self.f_input, text='视频目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_path, width=95).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='损坏视频导出路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_path, width=95).grid(row=1, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='ffmpeg exe程序: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.ffmpeg_path, width=95).grid(row=2, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)
        # 打包exe 在程序目录下会有一个ffmpeg exe程序， I:\Programs\filemanager\imageio_ffmpeg\binaries\ffmpeg-win64-v4.2.2.exe
        tmp_ffmpeg_path = os.path.abspath(os.path.join(settings.BASE_DIR, "imageio_ffmpeg/binaries/ffmpeg-win64-v4.2.2.exe"))
        if os.path.exists(tmp_ffmpeg_path):
            self.ffmpeg_path.set(tmp_ffmpeg_path)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, stick=tk.EW)

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        # 展示结果
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 28
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        # self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        # self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)
        ttk.Label(self.f_bottom, text="", width=70).grid(row=0, column=3)
        ttk.Label(self.f_bottom, text='程序运行状态: ').grid(row=2, stick=tk.W, pady=10)
        self.exeStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序执行任务状态
        self.exeStateLabel.grid(row=2, column=1, columnspan=2, stick=tk.W, pady=10)
        self.proStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序总运行状态
        self.proStateLabel.grid(row=2, column=4, stick=tk.W, pady=10)


class SettingFrame(tk.Frame):
    """计算视频相似度"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.BASE_DIR = tk.StringVar()
        self.RECORD_DIR = tk.StringVar()  # 保存记录的目录
        self.SAFE_DEL_DIR = tk.StringVar()  # 保存删除文件备份的目录
        self.DB_DIR = tk.StringVar()  # 保存数据相关的目录
        self.LOG_DIR = tk.StringVar()  # 保存日志的目录
        self.RESTORE_RECORD_PATH = tk.StringVar()  # 文件还原记录
        self.DEL_RECORD_PATH = tk.StringVar()  # 文件删除记录
        self.SAFE_DEL_LOCAL = tk.BooleanVar()  # 标记是否在文件所在分区创建safe_del文件夹，False 在程序目录下创建safe_del文件夹
        self.SAFE_FLAG = tk.BooleanVar()  # 标记执行文件删除操作时是否使用安全删除选项(安全删除选项会将被删除的文件剪切到safe_del目录下)
        self.SYSTEM_CODE_TYPE = tk.StringVar()  # 系统的编码格式，用于跟windnd配合解码拖拽的文件名
        self.init_setting()
        self.createPage()

    def init_setting(self):
        """用于导入或者更新设置界面的设置信息"""
        self.BASE_DIR.set(settings.BASE_DIR)
        self.RECORD_DIR.set(settings.RECORD_DIR)
        self.DB_DIR.set(settings.DB_DIR)
        self.LOG_DIR.set(settings.LOG_DIR)
        self.RESTORE_RECORD_PATH.set(settings.RESTORE_RECORD_PATH)
        self.DEL_RECORD_PATH.set(settings.DEL_RECORD_PATH)
        self.SAFE_DEL_DIR.set(settings.SAFE_DEL_DIR)
        self.SYSTEM_CODE_TYPE.set(settings.SYSTEM_CODE_TYPE)  # 设置默认值为90
        self.SAFE_DEL_LOCAL.set(settings.SAFE_DEL_LOCAL)  # 设置默认选中是
        self.SAFE_FLAG.set(settings.SAFE_FLAG)  # 设置默认选中是

    def open_path(self, pathObj):
        temp_path = pathObj.get()
        if os.path.exists(temp_path):
            webbrowser.open(temp_path)

    def chmodElement(self):
        """用于设置Entry和Radiobutton只读和可读写状态"""
        elements = [self.e1, self.e2, self.e3, self.e4, self.e5, self.e6, self.e7, self.r1, self.r2, self.r3, self.r4]
        if g_auth_flag:
            for item in elements:
                item["state"] = "normal"
        else:
            for item in elements:
                item["state"] = "disabled"

    def createPage(self):
        tk.Label(self, text='设置界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=0, columnspan=5, pady=10)
        ttk.Label(self, text='保存记录的目录: ').grid(row=1, stick=tk.W, pady=10)
        self.e1 = ttk.Entry(self, textvariable=self.RECORD_DIR, width=80)
        self.e1.grid(row=1, column=1, columnspan=3, stick=tk.W)
        ttk.Button(self, text="查看", command=lambda: self.open_path(self.RECORD_DIR)).grid(row=1, column=4)
        ttk.Label(self, text='保存数据相关的目录: ').grid(row=2, stick=tk.W, pady=10)
        self.e2 = ttk.Entry(self, textvariable=self.DB_DIR, width=80)
        self.e2.grid(row=2, column=1, columnspan=3, stick=tk.W)
        ttk.Button(self, text="查看", command=lambda: self.open_path(self.DB_DIR)).grid(row=2, column=4)
        ttk.Label(self, text='保存日志的目录: ').grid(row=3, stick=tk.W, pady=10)
        self.e3 = ttk.Entry(self, textvariable=self.LOG_DIR, width=80)
        self.e3.grid(row=3, column=1, columnspan=3, stick=tk.W)
        ttk.Button(self, text="查看", command=lambda: self.open_path(self.LOG_DIR)).grid(row=3, column=4)
        ttk.Label(self, text='删除操作记录路径: ').grid(row=4, stick=tk.W, pady=10)
        self.e4 = ttk.Entry(self, textvariable=self.DEL_RECORD_PATH, width=80)
        self.e4.grid(row=4, column=1, columnspan=3, stick=tk.W)
        ttk.Button(self, text="查看", command=lambda: self.open_path(self.DEL_RECORD_PATH)).grid(row=4, column=4)
        ttk.Label(self, text='还原操作记录路径: ').grid(row=5, stick=tk.W, pady=10)
        self.e5 = ttk.Entry(self, textvariable=self.RESTORE_RECORD_PATH, width=80)
        self.e5.grid(row=5, column=1, columnspan=3, stick=tk.W)
        ttk.Button(self, text="查看", command=lambda: self.open_path(self.RESTORE_RECORD_PATH)).grid(row=5, column=4)
        ttk.Label(self, text='保存删除文件备份的目录: ').grid(row=6, stick=tk.W, pady=10)
        self.e6 = ttk.Entry(self, textvariable=self.SAFE_DEL_DIR, width=15)
        self.e6.grid(row=6, column=1, stick=tk.W)
        ttk.Label(self, text='系统的编码格式: ').grid(row=7, column=0, stick=tk.W, pady=10)
        self.e7 = ttk.Entry(self, textvariable=self.SYSTEM_CODE_TYPE, width=15)
        self.e7.grid(row=7, column=1, stick=tk.W)
        ttk.Label(self, text='是否在文件所在分区创建safe_del文件夹: ').grid(row=8, column=0, stick=tk.W, pady=10)
        self.r1 = ttk.Radiobutton(self, text="是", variable=self.SAFE_DEL_LOCAL, value=True)
        self.r1.grid(column=1, row=8, sticky=tk.W)
        self.r2 = ttk.Radiobutton(self, text="否", variable=self.SAFE_DEL_LOCAL, value=False)
        self.r2.grid(column=2, row=8, sticky=tk.W)
        ttk.Label(self, text='是否使用安全删除选项: ').grid(row=9, column=0, stick=tk.W, pady=10)
        self.r3 = ttk.Radiobutton(self, text="是", variable=self.SAFE_FLAG, value=True)
        self.r3.grid(column=1, row=9, sticky=tk.W)
        self.r4 = ttk.Radiobutton(self, text="否", variable=self.SAFE_FLAG, value=False)
        self.r4.grid(column=2, row=9, sticky=tk.W)
        ttk.Button(self, text="权限验证！", command=lambda: authCheck(self)).grid(row=11, column=0)
        # ttk.Button(self, text="修改生效", command=self.load_config).grid(row=11, column=2)
        ttk.Button(self, text="保存到设置", command=self.export_config).grid(row=11, column=3)
        ttk.Button(self, text="恢复默认设置", command=self.reset_config).grid(row=11, column=4)
        self.chmodElement()  # 修改Entry和Radiobutton只读或者可读写状态

    @refuse
    def load_config(self, log_flag=True):
        """用于加载配置信息，程序初始化时或者修改配置后"""
        settings.save_lastest_config()  # 保存当前配置信息
        # 修改配置信息
        settings.BASE_DIR = self.BASE_DIR.get()
        settings.RECORD_DIR = self.RECORD_DIR.get()
        settings.DB_DIR = self.DB_DIR.get()
        settings.LOG_DIR = self.LOG_DIR.get()
        settings.RESTORE_RECORD_PATH = self.RESTORE_RECORD_PATH.get()
        settings.DEL_RECORD_PATH = self.DEL_RECORD_PATH.get()
        settings.SAFE_DEL_DIR = self.SAFE_DEL_DIR.get()
        settings.SYSTEM_CODE_TYPE = self.SYSTEM_CODE_TYPE.get()  # 设置默认值为90
        settings.SAFE_DEL_LOCAL = self.SAFE_DEL_LOCAL.get()  # 设置默认选中是
        settings.SAFE_FLAG = self.SAFE_FLAG.get()  # 设置默认选中是
        Mytools.my_init()  # 重新初始化，生成各个新目录
        if log_flag:
            # logger.operate_logger("修改了设置！")
            config_list = settings.get_config_list()
            logger.setting_logger(config_list, "修改了设置！")

    @refuse
    def export_config(self):
        """用于保存设置信息到配置文件"""
        self.load_config(log_flag=False)
        settings.export_config()
        # logger.operate_logger("修改了设置并保存！")
        config_list = settings.get_config_list()
        logger.setting_logger(config_list, "修改了设置并保存！")
        mBox.showinfo("保存配置信息完成！", "保存配置信息成功！")

    @refuse
    def reset_config(self):
        """用于恢复默认配置"""
        settings.save_lastest_config()  # 保存当前配置信息
        # 修改配置信息
        settings.reset_config()
        Mytools.my_init()  # 重新初始化，生成各个新目录
        self.init_setting()
        # logger.operate_logger("恢复默认设置！")
        config_list = settings.get_config_list()
        logger.setting_logger(config_list, "恢复默认设置！")
        mBox.showinfo("恢复默认设置！", "恢复默认设置成功！")


class AboutFrame(tk.Frame):  # 继承Frame类
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.createPage()

    def createPage(self):
        tk.Label(self, text='关于界面', font=("微软雅黑", 12)).pack()
        tk.Label(self, text='FileManager', font=("微软雅黑", 20), fg="green").pack()
        ttk.Label(self, text='by yunlong').pack()
        ttk.Label(self, text='这是一个多功能的小程序，').pack()
        ttk.Label(self, text=' 包含导出文件信息 、查找重复文件、文件同步备份、还原文件、删除文件、清除空文件夹、搜索文件、拷贝目录层次结构、').pack()
        ttk.Label(self, text='计算文件hash值、比对文本文件内容、提取视频帧图像、计算图片相似度、查找相似视频等功能').pack()
