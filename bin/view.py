import tkinter
import tkinter as tk
import traceback
import webbrowser
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.simpledialog import askstring
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
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
from natsort import natsorted
import logging
import subprocess
from decimal import Decimal

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from conf import settings
from core import SynTools, hash_core, SearchFiles, Mytools, CompareTxt, ImageTools, VideoTools, logger, ModifyTimestamp
from core.Check import *
from core.VideoTools import *


g_auth_flag = False  # 权限标志位， True允许修改配置， False 不允许修改
g_password = None  # 用于获取用户输入的密码，校验权限
mutex = threading.Lock()  # 创建互斥锁


def checkPassword(frameObj):
    """用于校验密码"""
    input_str = askstring('权限验证 ', '为确保数据安全！请勿在程序执行任务的时候修改配置信息！\n\n请输入暗号：\n\n两情若是久长时,__________________\n')
    if not input_str:
        mBox.showinfo("权限验证", "权限验证未通过，授权失败!")
        return
    password = '又岂在朝朝暮暮'
    if password in input_str:
        mBox.showinfo("权限验证", "权限验证通过，授权本次操作，授权时长1min!")
        t = threading.Thread(target=authManager, args=(frameObj,))
        t.setDaemon(True)
        t.start()
    else:
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


def refuse(func):
    """这是一个装饰器用于拒绝用户执行一些危险操作"""

    def wrapped_func(*args, **kwargs):
        if g_auth_flag is False:
            mBox.showwarning("权限拒绝！", "为了安全起见，软件作者设定目前用户不能执行该操作！\n若需要执行操作请进行权限验证！")
            return
        func(*args, **kwargs)

    return wrapped_func


running_task = []  # 正在进行的任务 用于关闭程序时提醒


def deal_running_task_arg(task_info):
    """装饰器，用于退出程序时检测当前是否有正在执行的任务, 有输入组件控制"""
    def deal_running_task(func):
        """用于操作正在运行的任务集合，防止多线程数据错误
        running_task  正在进行的任务集合, task_info 任务内容
        """
        def wrapped_func(*args, **kwargs):
            # 添加任务到running_task
            mutex.acquire()
            running_task.append(task_info)
            mutex.release()
            # 执行任务
            # 锁定输入组件
            args[0].disable_all_elements()  # 实例方法第一个参数是self 故可以直接用args[0]调用
            args[0].is_locked = True
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error_logger(traceback.format_exc())
                mBox.showerror("程序运行出错！", "执行 《{}》 任务出错！详情请查看日志！".format(task_info))
            # 移除任务
            # 释放输入组件
            args[0].enable_all_elements()
            args[0].is_locked = False
            mutex.acquire()
            running_task.remove(task_info)
            mutex.release()
            # print(running_task)
        return wrapped_func
    return deal_running_task


def deal_running_task_arg2(task_info):
    """装饰器，用于退出程序时检测当前是否有正在执行的任务，无输入组件控制"""
    def deal_running_task(func):
        """用于操作正在运行的任务集合，防止多线程数据错误
        running_task  正在进行的任务集合, task_info 任务内容
        """
        def wrapped_func(*args, **kwargs):
            # 添加任务到running_task
            mutex.acquire()
            running_task.append(task_info)
            mutex.release()
            # 执行任务
            func(*args, **kwargs)
            # 移除任务
            mutex.acquire()
            running_task.remove(task_info)
            mutex.release()
            # print(running_task)
        return wrapped_func
    return deal_running_task


def dragged_locked(func):
    """程序执行任务中，锁定文件拖拽功能"""
    def wrapped_func(*args, **kwargs):
        if args[0].is_locked:  # 程序正在执行任务中，锁定文件拖拽功能
            print('文件拖拽功能锁定！')
            return
        func(*args, **kwargs)
    return wrapped_func


class BaseFrame(tk.Frame):  # 继承Frame类
    """所有页面的基类"""
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.root.protocol('WM_DELETE_WINDOW', self.closeWindow)  # 绑定窗口关闭事件，防止计时器正在工作导致数据丢失
        self.record_path = None  # 导出的记录文件路径
        self.lock_elements = []  # 记录程序运行时锁定的子组件
        self.is_locked = False  # 程序是否锁定，当前程序已有正在执行的相同任务，则锁定文件拖拽，即执行任务时锁定子组件同时锁定文件拖拽功能
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
        self.src_dir = tk.StringVar()  # 源目录
        self.dst_dir = tk.StringVar()  # 目标目录
        self.l_title = tk.Label(self.f_title, text='页面', font=('Arial', 12), width=50, height=2)
        self.l_title.pack()

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.record_path = None
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def selectPath1(self):
        path_ = askdirectory()
        self.src_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_dir.set(path_)

    def closeWindow(self):
        """用来处理关闭窗口按钮在退出系统前的询问"""
        if len(running_task) != 0:
            msg = '现有 %s 个任务正在进行：' % len(running_task)
            for item in running_task:
                msg += '\n%s' % item
            msg += '\n是否退出？'
            ans = mBox.askyesno(title="Warning", message=msg)
            if not ans:
                # 选择否/no 不退出
                return
        # 退出程序
        self.root.destroy()

    def all_children(self, wid, finList):
        """递归获取所有子组件"""
        _list = wid.winfo_children()
        for item in _list:
            # print('{} is {}'.format(item, type(item)))
            if isinstance(item, tkinter.ttk.Label):
                # print('{} is label'.format(element))
                continue
            # print('state for {}:{}'.format(item, item.state()))
            #结果： state: ('disabled',)
            if item.state() == ('disabled',):  # 原本锁定的组件元素我们就不去动它
                continue
            if isinstance(item, tkinter.ttk.Frame):
                self.all_children(item, finList)
            else:
                finList.append(item)

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        """        
        elements = self.f_input.winfo_children()
        # print(elements)"""
        # 递归方式获取
        # print(len(self.lock_elements))
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        # print('len({}):{}'.format(len(self.lock_elements), self.lock_elements))
        for element in self.lock_elements:
            # print('{} is {}'.format(element, type(element)))
            # .!exportframe.!frame2.!label is <class 'tkinter.ttk.Label'>
            element.config(state=tk.DISABLED)

    def enable_all_elements(self):
        '''用来释放所有锁定的输入组件'''
        for element in self.lock_elements:
            element.config(state=tk.NORMAL)


class ExportFrame(BaseFrame):  # 继承Frame类
    """导出文件信息"""
    def __init__(self, master=None):
        super().__init__(master)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "导出文件信息"
        ttk.Label(self.f_input, text='文件目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=3, stick=tk.EW)
        ttk.Button(self.f_input, text='导出', command=self.run).grid(row=2, column=3, stick=tk.EW)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)
        self.button_show = ttk.Button(self.f_bottom, text='查看导出文件', command=self.showResult, state=tk.DISABLED)
        self.button_show.grid(row=8, column=0, sticky=tk.W, pady=10)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def selectPath(self):
        path_ = askdirectory()
        self.src_dir.set(path_)

    def showResult(self):
        """用于显示导出文件内容"""
        # 打开文件
        webbrowser.open_new_tab(self.record_path)
        # 还原状态信息
        self.record_path = None
        self.button_show.config(state=tk.DISABLED)

    @deal_running_task_arg('导出文件信息')
    def deal_export_file(self, dir_path):
        """处理导出操作"""
        time_res = Mytools.get_time_now()
        time_str = time_res.get('time_str')
        self.scr.insert('end', '%s  正在导出 %s 目录下的文件信息...\n' % (time_str, dir_path))
        self.record_path, count = Mytools.export_file_info(dir_path)
        time_str = Mytools.get_time_now().get('time_str')
        msg = "导出 %s 个文件信息到%s完成！" % (count, self.record_path)
        logger.operate_logger("【文件信息导出操作】  从 %s 下导出 %s 个文件信息到 %s" % (dir_path, count, self.record_path), time_str)
        self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
        self.scr.see(tk.END)
        mBox.showinfo('导出文件信息完成！', msg)
        self.button_show.config(state=tk.NORMAL)

    def run(self):
        self.scr.delete(1.0, 'end')
        src_dir = Mytools.check_path(self.src_dir.get())
        if src_dir:
            t = threading.Thread(target=self.deal_export_file, args=(src_dir,))
            t.setDaemon(True)
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())


class FindSameFrame(BaseFrame):  # 继承Frame类
    """查找重复文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_path = tk.StringVar()
        self.record_path = None  # 导出的记录文件路径
        self.mode_dict = {
            "同名": "name",
            "相同大小": "size",
            "相同修改时间": "mtime",
            "同名且大小相同": "name_size",
            "同名且修改时间相同": "name_mtime",
            "大小相同且修改时间相同": "size_mtime",
            "同名且大小相同且修改时间相同": "name_size_mtime"
        }
        self.optionDict = {"拷贝": "copy", "剪切": "move"}  # 文件操作模式
        self.mode = tk.StringVar()  # 查询模式
        self.option = tk.StringVar()
        self.pre_record_path = None  # 保存上一次的记录文件路径，用于误点还原按钮后撤销还原操作
        self.filter_flag = tk.BooleanVar()  # 是否启用过滤排除功能True 启用
        self.filter_mode = tk.IntVar()  # 过滤模式 1 排除 2 选中
        self.filter_str = tk.StringVar()  # 过滤内容
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "查找重复文件"
        ttk.Label(self.f_input, text='源目录路径:').grid(row=0, stick=tk.EW, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1, columnspan=3, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, stick=tk.EW, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1, columnspan=3, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='查询模式: ').grid(row=0, stick=tk.EW, pady=10)
        modeChosen = ttk.Combobox(self.f_input_option, width=35, textvariable=self.mode)
        modeChosen['values'] = list(self.mode_dict.keys())
        modeChosen.grid(row=0, column=1, sticky=tk.W, padx=5)
        modeChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        modeChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_input_option, text='  操作模式: ').grid(row=0, column=2, stick=tk.W, pady=10)
        col = 3
        for item in self.optionDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.option, value=item).grid(column=col, row=0,
                                                                                                   sticky=tk.W)
            col += 1
        self.option.set("拷贝")  # 设置默认值
        # 过滤功能
        self.f_filter = ttk.Frame(self.f_input)  # 容器
        self.f_filter.grid(row=3, columnspan=3, stick=tk.EW)
        ttk.Checkbutton(self.f_filter, text="过滤：", variable=self.filter_flag, onvalue=True, offvalue=False,
                        command=self.invoke_filter_input).grid(row=0, sticky=tk.W)
        self.f_filter_elements = ttk.Frame(self.f_filter)  # 容器
        self.f_filter_elements.grid(row=0, column=1, columnspan=3, stick=tk.EW)
        ttk.Radiobutton(self.f_filter_elements, text="排除", variable=self.filter_mode, value=1, state=tk.DISABLED).grid(column=1, row=0)
        ttk.Radiobutton(self.f_filter_elements, text="选中", variable=self.filter_mode, value=2, state=tk.DISABLED).grid(column=2, row=0)
        self.filter_flag.set(False)
        self.filter_mode.set(2)
        ttk.Entry(self.f_filter_elements, textvariable=self.filter_str, width=45, state=tk.DISABLED).grid(row=0, column=3, padx=5)
        ttk.Label(self.f_filter, text="(后缀名用英文逗号','分隔)", state=tk.DISABLED).grid(row=0, column=4)
        ttk.Button(self.f_input, text="执行", command=self.deal_search).grid(row=3, column=4)
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
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        self.pb1["value"] = 0
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + 's'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def invoke_filter_input(self):
        """用于切换是否激活过滤输入框"""
        elements = self.f_filter_elements.winfo_children()  # 获取该组件的子元素
        if self.filter_flag.get() is True:  # 将过滤组件设置为可用或禁用状态
            for item in elements:
                item.config(state=tk.NORMAL)
        else:
            for item in elements:
                item.config(state=tk.DISABLED)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @deal_running_task_arg('还原文件')
    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
            self.pre_record_path = self.record_path  # 记录new_old_record路径方便撤销还原
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            self.btn_undo_restore.config(state=tk.NORMAL)
            mBox.showinfo('还原文件完成！', msg)

    @deal_running_task_arg('撤销还原')
    def undoRestoreFiles(self):
        """撤销还原文件"""
        if self.pre_record_path:
            move_flag = False if (self.option.get() in ["拷贝", "copy"]) else True
            count = Mytools.undo_restore_file_by_record(self.pre_record_path, move_flag)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "%s 根据%s,重新移动了 %s 个文件" % (time_str, self.pre_record_path, count)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【撤销文件还原操作】  %s' % msg, time_str)
            self.pre_record_path = None  # 重置为None 以免影响后续数据
            self.btn_undo_restore.config(state=tk.DISABLED)
            # self.btn_restore.config(state=tk.NORMAL)
            mBox.showinfo('撤销还原文件完成！', msg)

    def clear(self):
        """清空信息"""
        self.scr.delete(1.0, 'end')
        self.record_path = None
        self.pre_record_path = None
        self.pb1["value"] = 0
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_undo_restore.config(state=tk.DISABLED)

    @deal_running_task_arg('查找重复文件')
    def do_search(self):
        """搜索重复文件"""
        self.clear()
        search_dir = Mytools.check_path(self.src_dir.get())
        save_dir = Mytools.check_path(self.dst_dir.get(), True)
        if search_dir and save_dir:
            if search_dir == save_dir:
                mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
                return
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        search_mode = self.mode_dict[self.mode.get()]
        deal_mode = self.optionDict[self.option.get()]
        filter_flag = self.filter_flag.get()
        filter_str = self.filter_str.get()
        filter_mode = self.filter_mode.get()
        self.pb1["value"] = 0
        self.pb1["maximum"] = 3  # 总项目数 1/3为遍历文件完成， 2/3 为比对完成， 3/3为操作文件完成
        print("filter_flag: %s, filter_str: %s" % (filter_flag, filter_str))
        write_time, log_time = Mytools.get_times()  # 获取当前时间的两种格式
        self.scr.insert("end", "%s  正在遍历文件目录...\n" % log_time)
        self.pb1["value"] = 1  # 模拟遍历完成
        file_dict, count = SearchFiles.find_same(search_dir, search_mode, filter_flag, filter_str, filter_mode)
        if len(file_dict):  # 如果有相同文件再进行后续动作
            time_str = Mytools.get_time_now().get('time_str')
            self.scr.insert("end", "\n%s  检索%s\n\t共发现 “%s” 的文件 %s 个！\n" % (time_str, search_dir, self.mode.get(), len(file_dict)))
            self.pb1["value"] = 2  # 比对完成
            self.scr.insert("end", "\t正在将 “%s” 的文件由 %s %s 到 %s ！\n" % (self.mode.get(), search_dir, self.option.get(), save_dir))
            # self.record_path = Mytools.move_or_copy_file(file_dict, search_dir, save_dir, deal_mode, name_simple=True)
            self.record_path = os.path.join(settings.RECORD_DIR, 'new_old_record_%s.txt' % write_time)
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
                    self.scr.insert("end", "error[%s] 程序操作文件出错：  %s\n%s  ->  %s\n\n" % (error_count, e, old_file, new_file))
            self.btn_restore.config(state=tk.NORMAL)
            # 将新旧文件名记录写出到文件
            Mytools.export_new_old_record(new_old_record, self.record_path)  # 将文件剪切前后文件信息导出到new_old_record
            print_msg = "%s 中发现 %s 个 “%s” 的文件，已 %s 到 %s，\n新旧文件名记录到 %s" % (
                search_dir, count, self.mode.get(), self.option.get(), save_dir, self.record_path)
            log_msg = "【文件查重操作】  %s 中发现 %s 个 %s 的文件，已 %s 到 %s，新旧文件名记录到 %s" % (
                search_dir, count, self.mode.get(), self.option.get(), save_dir, self.record_path)
        else:
            print_msg = "%s 中未发现%s的文件！" % (search_dir, self.mode.get())
            log_msg = '【文件查重操作】  %s' % print_msg
        time_str = Mytools.get_time_now().get('time_str')
        logger.operate_logger(log_msg, time_str)  # 记录到日志
        self.scr.insert("end", "\n\n%s  %s\n" % (time_str, print_msg))
        self.scr.see(tk.END)
        self.pb1["value"] = 3  # 操作文件完成
        mBox.showinfo('查找相同文件完成！', print_msg)

    def deal_search(self):
        """调度搜索重复文件方法"""
        t = threading.Thread(target=self.do_search)
        t.setDaemon(True)
        t.start()


class FindSameByHashFrame(BaseFrame):  # 继承Frame类
    """根据文件hash值去重"""
    def __init__(self, master=None):
        super().__init__(master)
        self.optionDict = {"拷贝": "copy", "剪切": "move"}
        self.mode = tk.StringVar()
        self.option = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.pre_record_path = None  # 保存上一次的记录文件路径，用于误点还原按钮后撤销还原操作
        self.same_record_path = None  # 记录重复文件的same_record 路径
        self.failed_record_path = None  # 记录操作文件失败的failed_record 路径
        self.sort_reverse = tk.BooleanVar()  # 记录排序方式 True 倒序 False正序
        self.sort_mode = tk.BooleanVar()  # 是否根据修改时间排序 True 根据修改时间排序 False 不操作
        self.move_all_flag = tk.BooleanVar()  # 是否导出所有hash相同的文件 True 导出所有 False 仅导出重复的
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "查找重复文件(hash值)"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=1, column=0, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="根据修改时间排序", variable=self.sort_mode, onvalue=True, offvalue=False, command=self.invoke_time_sort).grid(column=1, row=1, sticky=tk.W)
        self.sort_mode.set(False)
        self.f_sort_elements = ttk.Frame(self.f_input_option)  # 排序单选框区域
        self.f_sort_elements.grid(row=1, column=2, columnspan=2, stick=tk.EW)
        ttk.Radiobutton(self.f_sort_elements, text="正序", variable=self.sort_reverse, value=False, state=tk.DISABLED).grid(row=1, column=1,
                                                                                                sticky=tk.E)
        ttk.Radiobutton(self.f_sort_elements, text="倒序", variable=self.sort_reverse, value=True, state=tk.DISABLED).grid(row=1, column=2,
                                                                                               sticky=tk.E)
        self.sort_mode.set(False)  # 默认按修改时间正序排序
        ttk.Checkbutton(self.f_input_option, text="导出所有hash值相同的文件", variable=self.move_all_flag, onvalue=True, offvalue=False).grid(
            column=4, row=1, sticky=tk.W, padx=5)
        self.move_all_flag.set(False)
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
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=8, column=2, pady=10)
        self.btn_showSameRecord = ttk.Button(self.f_bottom, text="查看重复记录", command=self.showSameRecord, state=tk.DISABLED)
        self.btn_showSameRecord.grid(row=8, column=3, pady=10)
        self.btn_showFailedRecord = ttk.Button(self.f_bottom, text="查看操作失败记录", command=self.showfailedRecord, state=tk.DISABLED)
        self.btn_showFailedRecord.grid(row=8, column=4, pady=10)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def clear(self):
        """清空信息"""
        self.scr.delete(1.0, 'end')
        self.record_path = None
        self.pre_record_path = None
        self.pb1["value"] = 0
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_undo_restore.config(state=tk.DISABLED)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[hashs]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def invoke_time_sort(self):
        """用于切换是否激活按时间排序单选框"""
        elements = self.f_sort_elements.winfo_children()  # 获取该组件的子元素
        if self.sort_mode.get() is True:  # 将过滤组件设置为可用或禁用状态
            for item in elements:
                item.config(state=tk.NORMAL)
        else:
            for item in elements:
                item.config(state=tk.DISABLED)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    def showSameRecord(self):
        """查看相同文件记录"""
        if self.same_record_path:
            webbrowser.open(self.same_record_path)

    def showfailedRecord(self):
        """查看操作失败记录"""
        if self.failed_record_path:
            webbrowser.open(self.failed_record_path)

    @deal_running_task_arg('还原文件')
    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
            self.pre_record_path = self.record_path  # 记录new_old_record路径方便撤销还原
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            self.btn_undo_restore.config(state=tk.NORMAL)
            mBox.showinfo('还原文件完成！', msg)

    @deal_running_task_arg('撤销还原')
    def undoRestoreFiles(self):
        """撤销还原文件"""
        if self.pre_record_path:
            move_flag = False if (self.option.get() in ["拷贝", "copy"]) else True
            count = Mytools.undo_restore_file_by_record(self.pre_record_path, move_flag)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "%s 根据%s,重新移动了 %s 个文件" % (time_str, self.pre_record_path, count)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【撤销文件还原操作】  %s' % msg, time_str)
            self.pre_record_path = None  # 重置为None 以免影响后续数据
            self.btn_undo_restore.config(state=tk.DISABLED)
            # self.btn_restore.config(state=tk.NORMAL)
            mBox.showinfo('撤销还原文件完成！', msg)

    @deal_running_task_arg('校验hash值方式查找重复文件')
    def deal_query_same(self):
        src_path = self.src_dir.get()
        dst_path = self.dst_dir.get()
        deal_str = self.option.get()
        deal_mode = self.optionDict[deal_str]
        sort_reverse = self.sort_reverse.get()
        sort_mode = self.sort_mode.get()
        move_all_flag = self.move_all_flag.get()
        time_res = Mytools.get_time_now()
        time_str = time_res.get('time_str')
        start_time = time_res.get('timestamp')  # 开始时间
        self.scr.insert("end", "%s  正在遍历文件目录...\n" % time_str)
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
            time_str = Mytools.get_time_now().get('time_str')
            self.scr.insert("end", "%s  正在使用冒泡排序根据文件修改时间对文件进行排序...\n" % time_str)
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
        # print(file_list)
        self.scr.insert("end", "文件列表为：\n")
        for item in file_list:
            self.scr.insert("end", "%s\n" % item)
        self.pb1["maximum"] = len(file_list)  # 总项目数
        self.scr.see(tk.END)
        print("\n一共有%s个文件，正在进行hash计算找出重复文件..." % len(file_list))
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", "\n\n%s  共有%s个文件，正在进行hash计算找出重复文件...\n" % (time_str, len(file_list)))
        # 计算文件hash值，并找出重复文件
        hash_dict = {}  # 用于储存文件的hash信息， 数据格式{hash_value:[same_path1,samepath2,],}
        failed_files = []  # 记录移动失败的文件
        new_old_record = {}  # 记录新旧文件名 格式{new_path:old_path,}
        count = 0  # 标记重复文件个数
        time_now_str = time.strftime("%Y%m%d%H%M%S", time.localtime())
        dir_basename = os.path.basename(src_path)
        # print("time_now_str:", time_now_str)
        path_failed_files_record = os.path.join(settings.RECORD_DIR, '%s_moveFailed_%s.txt' % (dir_basename, time_now_str))  # 移动失败的文件的记录路径
        path_new_old_record = os.path.join(settings.RECORD_DIR, '%s_new_old_record_%s.txt' % (dir_basename, time_now_str))  # 移动成功的文件的新旧文件名记录路径
        path_same_record = os.path.join(settings.RECORD_DIR, '%s_same_record_%s.txt' % (dir_basename, time_now_str))  # 移动成功的文件的新旧文件名记录路径
        # 计算文件hash值
        for item in file_list:
            self.pb1["value"] += 1
            hash_value = hash_core.get_md5(item)
            if hash_value not in hash_dict:
                hash_dict[hash_value] = [item, ]  # 创建新记录
            else:
                count += 1
                hash_dict[hash_value].append(item)
                self.scr.insert("end", "发现重复文件 %s ！\n" % item)
                self.scr.see('end')
        # 移动文件
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", "\n\n%s  开始操作文件！\n" % time_str)
        num = 0
        self.pb1["maximum"] = len(hash_dict)  # 总项目数
        self.pb1["value"] = 0
        for i in hash_dict:
            self.pb1["value"] += 1
            if len(hash_dict[i]) > 1:
                deal_files = hash_dict[i] if move_all_flag else hash_dict[i][1:]
                for item in deal_files:
                    try:
                        self.scr.insert("end", "%s 重复，将%s到%s\n" % (item, deal_str, dst_path))
                        self.scr.see("end")
                        new_file_name = os.path.basename(item)
                        new_file_name = 'H%s__%s' % (num, new_file_name) if move_all_flag else new_file_name
                        new_item = os.path.join(dst_path, new_file_name)
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
                num += 1

        msg = "hash去重完成！共有 %s 个重复文件！\n" % count
        log_msg = "【HASH去重操作】  hash去重完成！ %s 下共有文件 %s 个，共有 %s 个重复文件！" % (src_path, len(file_list), count)
        if count:
            # print(len(same_record))
            with open(path_same_record, 'a', encoding='utf-8') as f:
                for item in hash_dict:
                    same_list = hash_dict[item]
                    if len(same_list) > 1:
                        f.write("%s:\n" % item)
                        for i in same_list:
                            f.write("\t%s\n" % i)
                    else:
                        continue
            self.same_record_path = path_same_record
            self.btn_showSameRecord.config(state=tk.NORMAL)
            msg += "重复文件 %s 到%s\n重复文件信息记录到%s\n" % (deal_str, dst_path, path_same_record)
            log_msg += "重复文件 %s 到 %s，重复文件信息记录到 %s" % (deal_str, dst_path, path_same_record)
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
        time_res = Mytools.get_time_now()
        time_str = time_res.get('time_str')
        end_time = time_res.get('timestamp')  # 结束时间
        self.scr.insert("end", '\n\n%s  %s' % (time_str, msg))
        self.scr.insert("end", "用时%ss\n" % (end_time - start_time))
        self.scr.see("end")
        logger.operate_logger(log_msg, time_str)
        mBox.showinfo('hash方式查找相同文件完成！', msg)

    def run(self):
        self.record_path = None
        self.pre_record_path = None
        self.same_record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_undo_restore.config(state=tk.DISABLED)
        self.btn_showSameRecord.config(state=tk.DISABLED)
        self.btn_showFailedRecord.config(state=tk.DISABLED)
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        search_dir = Mytools.check_path(self.src_dir.get())
        save_dir = Mytools.check_path(self.dst_dir.get(), True)
        if search_dir and save_dir:
            if search_dir == save_dir:
                mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
                return
            t = threading.Thread(target=self.deal_query_same)
            t.setDaemon(True)
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
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
        self.result = None  # 用于存储两个目录比较结果
        self.modeDict = {
            "基于filecmp模块": 1,
            "自己实现的Mybackup,节省IO资源占用": 2,
            "备份端目录变更同步": 3}
        self.optionDict = {
            1: ["同步备份", "同步还原", "新增和更新", "仅新增"],
            2: ["同步备份", "新增和更新", "仅新增"],
            3: ["目录变更", ]}
        # 描述结果的字段对应关系
        self.strDict = {
            "only_in_src_count": '仅存在于源目录的项目数',
            "only_in_dst_count": '仅存在于备份端的项目数',
            "update_count": '内容有更新的项目数',
            "move_count": '备份端目录变更的项目数',
            "common_funny_count": '无法比较的项目数',
            "only_in_src": '仅存在于源目录的项目',
            "only_in_dst": '仅存在于备份端的项目',
            "diff_files": '内容有更新的项目',
            "common_funny": '无法比较的项目',
            "file_only_in_src": '仅存在于源目录的文件',
            "file_only_in_dst": '仅存在于备份端的文件',
            "dir_only_in_src": '仅存在于源目录的目录',
            "dir_only_in_dst": '仅存在于备份端的目录',
            "move_dict": '备份端目录变更的项目',
        }
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
        self.optionChosen["value"] = self.optionDict[self.modeDict[self.mode.get()]]  # 联动下拉框
        self.optionChosen.current(0)
        self.scr.delete(1.0, 'end')  # 清空原内容
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""
        self.result = None
        self.btn_run.config(state=tk.DISABLED)

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        """        
        elements = self.f_input.winfo_children()
        # print(elements)"""
        # 递归方式获取
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        self.lock_elements.append(self.optionChosen)
        # print('len({}):{}'.format(len(self.lock_elements), self.lock_elements))
        for element in self.lock_elements:
            element.config(state=tk.DISABLED)

    @deal_running_task_arg('文件备份与同步-校对文件')
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
            if self.modeDict[self.mode.get()] == 2:  # 基于Mybackup
                    self.result = SynTools.find_difference2(src_path, dst_path)
            elif self.modeDict[self.mode.get()] == 3:  # 仅进行备份端目录变更
                    self.result = SynTools.find_difference3(src_path, dst_path)
            else:  # 基于filecmp返回的数据，文件和文件夹统计在一起
                self.result = {"only_in_src": [], "only_in_dst": [], "diff_files": [],
                               "common_funny": []}  # 用于存储两个目录比较结果
                self.result = SynTools.do_compare(src_path, dst_path, self.result)
                self.result["count"] = {
                    "only_in_src_count": len(self.result["only_in_src"]),
                    "only_in_dst_count": len(self.result["only_in_dst"]),
                    "update_count": len(self.result["diff_files"]),
                    "common_funny_count": len(self.result["common_funny"])}
        except Exception as e:
            self.exeStateLabel["text"] = "程序运行出错,详情请查看错误日志!"
            self.proStateLabel["text"] = "error!!!"
            raise e
        # 显示详情：
        msg = []
        # print(str(self.result))
        count_detial = self.result.pop("count")
        # print(count_detial)
        msg.append("%s    ->    %s\n" % (src_path, dst_path))
        count = 0  # 用于记录有多少文件差异
        for item in count_detial:
            count += count_detial[item]
            item_total = self.strDict.get(item)
            if not item_total:
                item_total = item
            msg.append("%s: %s\n" % (item_total, count_detial[item]))
        msg_str = ''.join(msg)
        self.scr.insert('end', msg_str)
        if count != 0:
            self.scr.insert('end', "\n详情：", "title")
        else:
            self.scr.insert('end', "\n文件内容无变化！", "title")
        for item in self.result:
            tmp_msg = []
            if len(self.result[item]) == 0:
                continue
            item_str = self.strDict.get(item)
            self.scr.insert(tk.END, '\n%s: \n' % item_str, "title")  # 对分类标题 “title”标签标记后面做格式
            for elem in self.result[item]:
                if item == 'move_dict':  # 显示备份端目录变更文件的变更情况
                    tmp_msg.append('\t%s\n\t-> %s\n' % (self.result[item][elem], elem))
                else:
                    tmp_msg.append('\t%s\n' % elem)
            msg_str = ''.join(tmp_msg)
            self.scr.insert('end', msg_str)
        self.scr.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.exeStateLabel["text"] = "比对文件完成！"
        self.proStateLabel["text"] = "complete！"
        self.btn_run.config(state=tk.NORMAL)

    def findDiffRun(self):
        """"执行比对文件的主程序，调用实际执行子进程"""
        t = threading.Thread(target=self.findDiff)
        t.setDaemon(True)
        t.start()

    @deal_running_task_arg('文件备份与同步-同步文件')
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
        elif option in ["3", "新增和更新"]:
            option = "backup_update"
        elif option in ["4", "仅新增"]:
            option = "only_add"

        if self.modeDict[self.mode.get()] == 2:  # 基于Mybackup
            msg = SynTools.deal_file2(self, src_path, dst_path, self.result, option)
        elif self.modeDict[self.mode.get()] == 3:  # 仅进行备份端目录变更
            msg = SynTools.deal_file3(self, src_path, dst_path, self.result, option)
        else:  # 基于filecmp返回的数据，文件和文件夹统计在一起
            msg = SynTools.deal_file(self, src_path, dst_path, self.result, option)
        self.exeStateLabel["text"] = "文件同步完成!"
        self.proStateLabel["text"] = "complete!"
        self.btn_run.config(state=tk.DISABLED)
        mBox.showinfo('文件同步操作完成！', msg)

    def run(self):
        src_path = Mytools.check_path(self.src_path.get())
        dst_path = Mytools.check_path(self.dst_path.get(), True)
        if src_path and dst_path:
            t = threading.Thread(target=self.deal_syn, args=(src_path, dst_path))
            t.setDaemon(True)
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
            self.optionChosen['values'] = self.optionDict[self.modeDict[self.mode.get()]]
        else:
            self.optionChosen['values'] = self.optionDict[1]
        self.optionChosen.grid(row=0, column=1, pady=10)
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        self.optionChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_bottom, text="", width=70).grid(row=0, column=3)
        self.btn_run = ttk.Button(self.f_bottom, text="执行", command=self.run, state=tk.DISABLED)
        self.btn_run.grid(row=0, column=4, sticky=tk.EW)
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
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "还原文件"
        ttk.Label(self.f_input, text='new_old_record文件: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=90).grid(row=0, column=1, columnspan=2, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=3)
        ttk.Button(self.f_input, text='重做', command=self.deal_undo_restore).grid(row=1, column=2, stick=tk.E, pady=10)
        ttk.Button(self.f_input, text='还原', command=self.run).grid(row=1, column=3, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=5)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def selectPath(self):
        path_ = askopenfilename()
        self.src_dir.set(path_)

    @deal_running_task_arg('还原文件')
    def deal_restore(self, dir_path):
        print(self.src_dir.get())
        # self.scr.delete(1.0, 'end')
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert('end', '%s  正在还原%s记录中的文件...\n' % (time_str, dir_path))
        restore_path, count = Mytools.restore_file_by_record(dir_path)
        time_str = Mytools.get_time_now().get('time_str')
        msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (dir_path, count, restore_path)
        logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
        self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
        self.scr.see(tk.END)
        mBox.showinfo('还原文件完成！', msg)

    @deal_running_task_arg('撤销还原')
    def deal_undo_restore(self):
        """根据记录重新移动文件，即重做 即撤销还原"""
        print(self.src_dir.get())
        # self.scr.delete(1.0, 'end')
        record_path = self.src_dir.get()
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert('end', '%s  正在根据%s记录重新操作文件...\n' % (time_str, record_path))
        count = Mytools.undo_restore_file_by_record(record_path)
        time_str = Mytools.get_time_now().get('time_str')
        msg = "根据 %s,重新操作了 %s 个文件" % (record_path, count)
        logger.operate_logger('【撤销文件还原操作】  %s' % msg, time_str)
        self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
        self.scr.see(tk.END)
        mBox.showinfo('重新操作文件完成！', msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.src_dir.get())
        if dir_path:
            t = threading.Thread(target=self.deal_restore, args=(dir_path,))
            t.setDaemon(True)
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
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

    @deal_running_task_arg('删除文件')
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

    @deal_running_task_arg('删除文件-过滤记录')
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


class CleanEmptyDirFrame(BaseFrame):  # 继承Frame类
    """清除空文件夹"""
    def __init__(self, master=None):
        super().__init__(master)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "清除空文件夹"
        ttk.Label(self.f_input, text='要清除空文件夹的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=90).grid(row=1, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=1, column=3)
        ttk.Button(self.f_input, text='清空', command=self.run).grid(row=2, column=3, stick=tk.E, pady=10)
        ttk.Label(self.f_state, text='结果进度: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE')
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @deal_running_task_arg('清空空文件夹')
    def deal_clear_empty_dir(self, dir_path):
        print(self.src_dir.get())
        # self.scr.delete(1.0, 'end')
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert('end', '%s  正在清空%s目录下的空文件夹...\n' % (time_str, dir_path))
        del_list = Mytools.remove_empty_dir(dir_path)
        time_str = Mytools.get_time_now().get('time_str')
        if len(del_list):
            msg = "清除了 %s 下 %s 个空文件夹!\n删除的空文件夹信息记录到%s" % (dir_path, len(del_list), settings.DEL_RECORD_PATH)
            log_msg = "清除了 %s 下 %s 个空文件夹!删除的空文件夹信息记录到 %s" % (dir_path, len(del_list), settings.DEL_RECORD_PATH)
            # 输出显示
            self.scr.insert('end', "\n%s  清除了 %s 个空文件夹!\n" % (time_str, len(del_list)))
            self.scr.insert('end', "\n空文件夹如下：\n", 'info')
            for item in del_list:
                self.scr.insert(tk.END, '%s\n' % item)
            logger.record_logger(del_list, settings.DEL_RECORD_PATH, '【清除空文件夹】  %s' % log_msg)  # 记录日志
            # logger.operate_logger('【清除空文件夹】  %s' % log_msg, time_str)
        else:
            msg = "%s  下没有找到空文件夹！" % dir_path
            print("没有找到空文件夹！")
        self.scr.insert('end', "\n\n%s  %s\n" % (time_str, msg), 'info')
        self.scr.tag_config('info', font=('microsoft yahei', 16, 'bold'))
        self.scr.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr.see(tk.END)
        mBox.showinfo('清空空文件夹完成！', "%s\n" % msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.src_dir.get())
        if dir_path:
            t = threading.Thread(target=self.deal_clear_empty_dir, args=(dir_path,))
            t.setDaemon(True)
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return


class SearchFrame(BaseFrame):  # 继承Frame类
    """搜索文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_flag = tk.BooleanVar()  # True 操作文件夹 False 不操作
        self.file_flag = tk.BooleanVar()  # True 操作文件 False 不操作
        self.search_mode = tk.StringVar()
        self.search_option = tk.BooleanVar()  # True 正则匹配/条件匹配， False 精确搜索
        self.search_str = tk.StringVar()  # 搜索语句
        self.rename_flag = tk.BooleanVar()  # 原样导出还是导出到单级目录并附带目录层级说明
        self.deal_mode = tk.StringVar()
        self.filter_mode = tk.StringVar()  # 过滤模式 选中 select 排除 exclude
        self.filter_str = tk.StringVar()  # 过滤语句  正则语句
        self.same_file_option = tk.StringVar()  # 遇到已存在同名文件处理方式  'ask'询问，'overwrite' 覆盖，'skip' 跳过
        self.meta_result = {'files': [], 'dirs': []}  # 完整搜索的结果，即最全的搜索集  搜索到的结果
        self.result = {'files': [], 'dirs': []}  # 用于储存文件操作的搜索结果  过滤之后进行文件复制移动的文件信息
        self.tmp_result = {'files': [], 'dirs': []}  # 用于储存按时间过滤切换前的 文件的搜索结果
        self.time_flag = tk.BooleanVar()  # True 按时间搜索过滤结果 False 不按时间搜索
        self.mtime_flag = tk.BooleanVar()  # True 修改时间 False 创建时间
        self.time_start = tk.StringVar()  # 开始时间
        self.time_end = tk.StringVar()  # 结束时间
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "搜索文件"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=5, stick=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=5)
        ttk.Radiobutton(self.f_input_option, text="文件名", variable=self.search_mode, value="filename").grid(row=0, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_input_option, text="文件大小", variable=self.search_mode, value="filesize").grid(row=0, column=2, stick=tk.W)
        self.search_mode.set("filename")
        ttk.Checkbutton(self.f_input_option, text="操作文件夹", variable=self.dir_flag, onvalue=True, offvalue=False, command=self.switch_selection2).grid(
            row=0, column=3, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="操作文件", variable=self.file_flag, onvalue=True, offvalue=False, command=self.switch_selection2).grid(
            row=0, column=4, sticky=tk.W)
        self.dir_flag.set(True)
        self.file_flag.set(True)
        ttk.Radiobutton(self.f_input_option, text="精确搜索", variable=self.search_option, value=False).grid(row=1, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_input_option, text="正则/条件搜索", variable=self.search_option, value=True).grid(row=1, column=2, stick=tk.W)
        self.search_option.set(False)
        ttk.Button(self.f_input_option, text="使用说明", command=self.showTip).grid(row=1, column=3, stick=tk.W)
        ttk.Checkbutton(self.f_input_option, text="按时间搜索", variable=self.time_flag, onvalue=True, offvalue=False, command=self.switch_selection2).grid(
            row=2, column=1, pady=5)
        self.f_time_elements = ttk.Frame(self.f_input_option)  # 按时间过滤的容器
        self.f_time_elements.grid(row=2, column=2, columnspan=10, stick=tk.EW)
        ttk.Radiobutton(self.f_time_elements, text="创建时间", variable=self.mtime_flag, value=False, state=tk.DISABLED).grid(row=0, column=0)
        ttk.Radiobutton(self.f_time_elements, text="修改时间  ", variable=self.mtime_flag, value=True, state=tk.DISABLED).grid(row=0, column=1)
        ttk.Label(self.f_time_elements, text='开始时间:', state=tk.DISABLED).grid(row=0, column=2)
        ttk.Entry(self.f_time_elements, textvariable=self.time_start, width=18, state=tk.DISABLED).grid(row=0, column=3)
        ttk.Label(self.f_time_elements, text='结束时间:', state=tk.DISABLED).grid(row=0, column=4, padx=5)
        ttk.Entry(self.f_time_elements, textvariable=self.time_end, width=18, state=tk.DISABLED).grid(row=0, column=5)
        ttk.Label(self.f_input, text='搜索语句: ').grid(row=3, stick=tk.W, pady=5)
        ttk.Entry(self.f_input, textvariable=self.search_str, width=80).grid(row=3, column=1, stick=tk.W)
        ttk.Button(self.f_input, text="搜索", command=self.deal_search).grid(row=3, column=4)

        # 展示结果
        ttk.Label(self.f_state, text='搜索结果: ').grid(row=0, stick=tk.W)
        scrolW = 120
        scrolH = 25
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, column=0, sticky='WE', columnspan=5)
        self.f_filter = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_filter.grid(row=1, columnspan=3, stick=tk.EW)
        self.f_bottom_option = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_bottom_option.grid(row=2, columnspan=3, stick=tk.EW)

        # 过滤功能
        ttk.Label(self.f_filter, text='过滤: ').grid(row=0, stick=tk.EW, pady=5)
        ttk.Radiobutton(self.f_filter, text="选中", variable=self.filter_mode, value="select").grid(row=0, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_filter, text="排除", variable=self.filter_mode, value="exclude").grid(row=0, column=2, stick=tk.W)
        self.filter_mode.set("exclude")
        ttk.Entry(self.f_filter, textvariable=self.filter_str, width=78).grid(row=0, column=3, stick=tk.W)
        ttk.Button(self.f_filter, text="过滤", command=self.do_filter).grid(row=0, column=4)
        ttk.Button(self.f_filter, text="使用说明", command=self.showTip_filter).grid(row=0, column=5, stick=tk.W)
        ttk.Label(self.f_bottom_option, text='导出方式: ').grid(row=0, stick=tk.EW)
        ttk.Radiobutton(self.f_bottom_option, text="复制", variable=self.deal_mode, value="copy").grid(row=0, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_bottom_option, text="剪切", variable=self.deal_mode, value="move").grid(row=0, column=2, stick=tk.W)
        self.deal_mode.set("copy")
        self.btn_restore_meta = ttk.Button(self.f_bottom_option, text="重置搜索结果", command=self.restore_meta_result, state=tk.DISABLED)
        self.btn_restore_meta.grid(row=0, column=4, stick=tk.EW)
        ttk.Label(self.f_bottom_option, text='是否原样导出？: ').grid(row=1, stick=tk.EW)
        ttk.Radiobutton(self.f_bottom_option, text="导出到单级目录并附带目录描述", variable=self.rename_flag, value=True).grid(row=1, column=1, stick=tk.W)
        ttk.Radiobutton(self.f_bottom_option, text="原样导出", variable=self.rename_flag, value=False).grid(row=1, column=2, stick=tk.W)
        self.rename_flag.set(True)
        self.f_bottom_option_2 = ttk.Frame(self.f_bottom_option)  # 选项容器
        self.f_bottom_option_2.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_bottom_option_2, text='已存在重名文件，处理方式？: ').grid(row=2, column=0, stick=tk.EW)
        # ttk.Radiobutton(self.f_bottom_option_2, text="询问", variable=self.same_file_option, value='ask').grid(row=2, column=1, padx=5)
        ttk.Radiobutton(self.f_bottom_option_2, text="覆盖", variable=self.same_file_option, value='overwrite').grid(row=2, column=2, padx=5)
        ttk.Radiobutton(self.f_bottom_option_2, text="跳过", variable=self.same_file_option, value='skip').grid(row=2, column=3, padx=5)
        self.same_file_option.set('skip')
        ttk.Label(self.f_bottom_option, text='要导出的路径: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Entry(self.f_bottom_option, textvariable=self.dst_dir, width=95).grid(row=3, column=1, columnspan=3)
        ttk.Button(self.f_bottom_option, text="浏览", command=self.selectPath2).grid(row=3, column=4)
        ttk.Button(self.f_bottom_option, text="文件覆盖风险检测", command=self.check_files_overwrite).grid(row=4, column=3,stick=tk.E)
        ttk.Button(self.f_bottom_option, text="导出", command=self.run).grid(row=4, column=4)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        # 递归方式获取
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        self.all_children(self.f_bottom, self.lock_elements)
        # print(len(self.lock_elements))
        for element in self.lock_elements:
            element.config(state=tk.DISABLED)

    def selectPath1(self):
        self.clear()
        path_ = askdirectory()
        self.src_dir.set(path_)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def clear(self):
        self.record_path = None
        self.scr.delete(1.0, tk.END)
        self.meta_result = {'files': [], 'dirs': []}  # 完整搜索的结果，即最全的搜索集  搜索到的结果
        self.result = {'files': [], 'dirs': []}  # 用于储存文件操作的搜索结果  过滤之后进行文件复制移动的文件信息

    @log_error
    def check_files_overwrite(self):
        """用来检测目标目录路径是否存在同名文件，防止数据覆盖损失"""
        search_path = Mytools.check_path(self.src_dir.get())
        if search_path is None:
            mBox.showerror("路径不存在！", "路径： %s 不存在！请检查！" % self.src_dir.get())
            return
        save_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        if save_path is None:
            mBox.showerror("路径不存在！", "输出路径为空")
            return
        if search_path == save_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        rename_flag = self.rename_flag.get()
        danger_dict = Mytools.check_files_overwrite_danger(self.result, search_path, save_path, rename_flag=rename_flag)
        if len(danger_dict):
            self.scr.insert(tk.END, '\n检测到共有 %s 个文件/目录有数据覆盖风险！该文件源路径如下：\n' % len(danger_dict))
            for old_path in danger_dict:
                self.scr.insert(tk.END, '\t%s\n' % old_path)
            mBox.showwarning("警告", '检测到共有 %s 个文件/目录有数据覆盖风险！' % len(danger_dict))
        else:
            mBox.showinfo("正常", "本次文件操作无数据覆盖风险！")

    def showTip(self):
        tip = """
        “正则搜索”直接输入正则语句即可
        
        “条件搜索”请输入条件语句：数值为文件大小字节数（纯数字不写B）
            gt 大于 
            gte 大于等于 
            lt 小于 
            lte 小于等于 
            eq 等于
            neq 不等于
            between and 在中间
            例如： gt 2816665 或者 between 1024000 and 2048000
            
        使用“按时间过滤”功能 请输入标准时间格式,例如 ‘2022-06-07 10:00:00’
            """
        showinfo("正则/条件语句使用说明", tip)

    def showTip_filter(self):
        """显示过滤使用说明"""
        tip = """
        输入过滤语句即可，过滤语句请使用标准正则语句
            """
        showinfo("过滤语句使用说明", tip)

    @deal_running_task_arg('搜索文件或目录')
    def do_search(self):
        """实际搜索操作"""
        self.scr.delete(1.0, tk.END)  # 清空文本框
        self.meta_result = None
        self.result = {'files': [], 'dirs': []}
        search_path = Mytools.check_path(self.src_dir.get())
        if search_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        search_str = self.search_str.get()
        search_mode = self.search_mode.get()
        search_option = self.search_option.get()
        dir_flag = self.dir_flag.get()
        file_flag = self.file_flag.get()
        # print(search_path,search_str,search_mode,search_option)
        if search_mode == "filename":
            self.meta_result = SearchFiles.search_file_by_name(search_path, search_str, search_option)
        else:
            # 检测输入是否合规
            try:
                if search_option is True:
                    search_obj = re.search(r"(gt|gte|lt|lte|neq|eq|between)\s?(\d+)\s?(and)?\s?(\d+)?$", search_str)
                    int(search_obj.group(2))
            except:
                mBox.showwarning("输入格式警告", "文件大小 输入格式有误，请查看使用说明！")
                return
            self.meta_result = SearchFiles.search_file_by_size(search_path, search_str, search_option)
        # 按时间过滤结果
        self.do_time_filter()
        # 显示结果
        self.show_result()

    def deal_search(self):
        """为搜索操作新开一个线程，避免高耗时操作阻塞GUI主线程"""
        t = threading.Thread(target=self.do_search)
        t.setDaemon(True)
        t.start()

    @log_error
    def do_filter(self):
        """过滤结果"""
        filter_mode = self.filter_mode.get()
        filter_str = self.filter_str.get()
        # print('type(filter_str):', type(filter_str))
        # print('filter_str:', filter_str)
        # print('filter_str.strip():', filter_str.strip())
        if not filter_str:  # 当过滤输入框无内容时直接跳出过滤函数
            self.show_result()
            return
        filter_result = {"files": [], "dirs": []}
        file_list = self.result["files"]
        dir_list = self.result["dirs"]
        for item in file_list:
            if re.search(filter_str, item, flags=re.I):  # flags修饰，re.I 忽略大小写
                if filter_mode == 'select':
                    filter_result["files"].append(item)
            else:
                if filter_mode == 'exclude':
                    filter_result["files"].append(item)

        for item in dir_list:
            if re.search(filter_str, item, flags=re.I):
                if filter_mode == 'select':
                    filter_result["dirs"].append(item)
            else:
                if filter_mode == 'exclude':
                    filter_result["dirs"].append(item)
        self.result = filter_result
        # 显示结果
        self.show_result()
        self.btn_restore_meta.config(state=tk.NORMAL)

    def do_time_filter(self):
        """用于按时间过滤"""
        time_flag = self.time_flag.get()  # 是否按时间过滤
        file_flag = self.file_flag.get()
        dir_flag = self.dir_flag.get()
        if time_flag is False:
            self.result["files"] = self.meta_result['files'] if file_flag else []
            self.result["dirs"] = self.meta_result['dirs'] if dir_flag else []
            return
        mtime_flag = self.mtime_flag.get()  # True 修改时间 False 创建时间
        time_start = self.time_start.get()
        time_end = self.time_end.get()
        time_start = Mytools.changeStrToTime(time_start)
        time_end = Mytools.changeStrToTime(time_end)
        if time_start is None:
            time_start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        if time_end is None:
            time_end = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        self.time_start.set(time_start)
        self.time_end.set(time_end)
        time_start = time.mktime(time.strptime(time_start, '%Y-%m-%d %H:%M:%S'))
        time_end = time.mktime(time.strptime(time_end, '%Y-%m-%d %H:%M:%S'))
        # 清空结果集
        self.result["files"] = []
        self.result["dirs"] = []
        # 按时间过滤结果集
        if file_flag is True:
            for _path in self.meta_result['files']:
                timestamp = os.path.getmtime(_path) if mtime_flag else os.path.getctime(_path)
                if time_start <= timestamp <= time_end:
                    self.result['files'].append(_path)
        if dir_flag is True:
            for _path in self.meta_result['dirs']:
                timestamp = os.path.getmtime(_path) if mtime_flag else os.path.getctime(_path)
                if time_start <= timestamp <= time_end:
                    self.result['dirs'].append(_path)

    @log_error
    def show_result(self):
        """显示结果"""
        self.scr.delete(1.0, "end")
        search_mode = self.search_mode.get()
        search_option = self.search_option.get()
        search_str = self.search_str.get()
        file_flag = self.file_flag.get()
        dir_flag = self.dir_flag.get()
        time_flag = self.time_flag.get()  # 是否按时间过滤
        mtime_flag = self.mtime_flag.get()  # True 修改时间 False 创建时间
        time_start = self.time_start.get()
        time_end = self.time_end.get()
        time_start = Mytools.changeStrToTime(time_start)
        time_end = Mytools.changeStrToTime(time_end)
        file_count = len(self.result["files"]) if file_flag else 0  # 文件数
        dir_count = len(self.result["dirs"]) if dir_flag else 0  # 文件夹数
        print("file_flag: %s, dir_flag: %s" % (file_flag, dir_flag))
        tmp_msg = '搜索模式：'
        if search_mode == 'filename':
            tmp_msg += '"按文件名搜索", 匹配方式："正则匹配", ' if search_option else '"按文件名搜索", 匹配方式："精确匹配", '
        else:
            tmp_msg += '"按文件大小搜索", 匹配方式："条件匹配", ' if search_option else '"按文件大小搜索", 匹配方式："精确匹配", '
        tmp_msg += '搜索语句："%s"' % search_str
        if time_flag:
            tmp_msg += ', 修改' if mtime_flag else ', 创建'
            tmp_msg += '时间："%s" ~ "%s" ' % (time_start, time_end)
        self.scr.insert("end", '%s\n' % tmp_msg)
        if file_count + dir_count:
            if file_flag and dir_flag:
                tmp_msg = "搜索结果：(%s个文件, %s个文件夹)\n" % (file_count, dir_count)
            elif file_flag:
                tmp_msg = "搜索结果：(%s个文件)\n" % file_count
            else:
                tmp_msg = "搜索结果：(%s个文件夹)\n" % dir_count
            self.scr.insert("end", tmp_msg, "info")
            if file_count:
                self.scr.insert("end", "文件:\n", "title")
                for item in self.result["files"]:
                    self.scr.insert("end", "\t%s\n" % item)
            if dir_count:
                self.scr.insert("end", "文件夹:\n", "title")
                for item in self.result["dirs"]:
                    self.scr.insert("end", "\t%s\n" % item)
            self.scr.insert("end", "搜索结果：共匹配到(%s个文件, %s个目录)\n" % (file_count, dir_count), "info")
        else:
            self.scr.insert("end", "搜索结果：未找到匹配的文件或目录！\n", "info")
        self.scr.tag_config('info', font=('microsoft yahei', 16, 'bold'))
        self.scr.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))

    def restore_meta_result(self):
        """用于重置过滤操作，将搜索结果重置为最初状态"""
        self.result["files"] = self.meta_result['files']
        self.result["dirs"] = self.meta_result['dirs']
        self.btn_restore_meta.config(state=tk.DISABLED)
        # 3.刷新显示
        self.show_result()

    def switch_selection(self):
        """用于处理选中以及取消选中目录和文件时候 搜索结果的变化"""
        # 1.获取目录和文件复选框状态
        file_flag = self.file_flag.get()
        dir_flag = self.dir_flag.get()
        # 2.处理结果集
        if file_flag is False:
            self.result["files"] = []
        else:
            self.result["files"] = self.meta_result['files']
        if dir_flag is False:
            self.result["dirs"] = []
        else:
            self.result["dirs"] = self.meta_result['dirs']
        # 3.刷新显示
        self.show_result()

    def switch_selection2(self):
        """用于处理选中以及取消选中按时间过滤时候 搜索结果的变化"""
        # 过滤结果
        self.invoke_filter_time()  # 激活或者禁用按时间过滤组件
        self.do_time_filter()
        self.show_result()
        # self.do_filter()

    def invoke_filter_time(self):
        """用于切换是否激活按时间过滤的组件"""
        elements = self.f_time_elements.winfo_children()  # 获取该组件的子元素
        if self.time_flag.get() is True:  # 将过滤组件设置为可用或禁用状态
            for item in elements:
                item.config(state=tk.NORMAL)
        else:
            for item in elements:
                item.config(state=tk.DISABLED)

    @deal_running_task_arg('搜索文件或目录-操作文件')
    def deal_files(self):
        """处理文件操作"""
        # self.scr.delete(1.0, "end")
        search_path = Mytools.check_path(self.src_dir.get())
        save_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        if search_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if save_path is None:
            mBox.showerror("路径不存在！", "输出路径为空")
            return
        if search_path == save_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        search_str = self.search_str.get()
        search_mode = self.search_mode.get()
        deal_mode = self.deal_mode.get()
        rename_flag = self.rename_flag.get()
        same_file_option = self.same_file_option.get()
        # print(search_path,save_path,search_str,search_mode,search_option, deal_mode,rename_flag)
        # 重新检查是否有取消对目录或者文件的选中
        file_flag = self.file_flag.get()
        dir_flag = self.dir_flag.get()
        if file_flag is False:
            self.result["files"] = []
        if dir_flag is False:
            self.result["dirs"] = []
        # 操作文件
        if len(self.result["files"]) + len(self.result["dirs"]):
            res = Mytools.deal_files(self.result, search_path, save_path, deal_mode=deal_mode, same_file_option=same_file_option,
                                             rename_flag=rename_flag)
            msg = "导出完成！项目总数： %s ,成功 %s 个，跳过 %s 个， 失败 %s 个， 文件new_old_record记录到%s" % (
                res.get('total_count'), len(res.get('new_old_record')), len(res.get('skip_list')), len(res.get('failed_list')), res.get("record_path"))
            if res.get("failed_path"):
                msg += '，操作失败的文件信息记录到 %s' % res.get("failed_path")
            mBox.showinfo("完成！", msg)
            self.scr.insert('end', "\n%s\n" % msg)
            self.scr.see('end')
        else:
            print("未找到匹配 %s的文件和目录！" % search_str)
            mBox.showinfo("完成！", "未找到匹配 %s的文件和目录！" % search_str)
            self.scr.insert('end', "\n未找到匹配 %s的文件和目录！\n" % search_str)
            self.scr.see('end')

    def run(self):
        """为操作文件新开一个线程，避免高耗时操作阻塞GUI主线程"""
        t = threading.Thread(target=self.deal_files)
        t.setDaemon(True)
        t.start()


class CopyDirTreeFrame(BaseFrame):
    """拷贝或导出目录结构"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()
        self.option = tk.StringVar()
        # self.src_dir = tk.StringVar()
        # self.dst_dir = tk.StringVar()
        self.path_ok_flag = True  # 用于标记用户输入的路径是否经过安全验证 True 路径存在 False 路径不存在
        self.createPage()

    def selectPath1(self):
        if self.option.get() == 'fromfile':
            path_ = askopenfilename()
        else:
            path_ = askdirectory()
        self.src_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.dst_dir.set(path_)

    def selectOption(self):
        # 从文件信息拷贝目录结构还是 从目录拷贝目录结构
        self.scr.delete(1.0, "end")  # 每次切换选项时都进行结果显示区域清屏

    def createPage(self):
        self.l_title["text"] = "拷贝目录结构"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标目录路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)

        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="从目录拷贝", variable=self.option, value="fromdir", command=self.selectOption).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="从文件拷贝", variable=self.option, value="fromfile", command=self.selectOption).grid(
            row=0, column=2, sticky=tk.W)
        self.option.set("fromdir")  # 设置单选默认值
        ttk.Button(self.f_input, text="导出目录结构", command=self.exportDirTree).grid(row=3, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="拷贝目录结构", command=self.copyDirTree).grid(row=3, column=2, stick=tk.E)
        # 展示结果
        ttk.Label(self.f_state, text='目录结构信息: ').grid(row=0, stick=tk.W, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE')
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @deal_running_task_arg('拷贝目录结构')
    def copyDirTree(self):
        self.scr.delete(1.0, "end")
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", '%s  正在拷贝目录结构，请稍候...\n' % time_str)
        src_path = Mytools.check_path(self.src_dir.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        msg, dir_str_list = Mytools.make_dirs(src_path, dst_path)
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", '\n%s  拷贝目录结构完成，目录结构如下:\n' % time_str)
        self.scr.insert("end", '\n'.join(dir_str_list))
        self.scr.see(tk.END)
        mBox.showinfo('完成！', msg)

    @deal_running_task_arg('拷贝目录结构')
    def exportDirTree(self):
        self.scr.delete(1.0, "end")
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", '%s  正在导出目录结构信息，请稍候...\n' % time_str)
        src_path = Mytools.check_path(self.src_dir.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        record_path, dir_list = Mytools.export_dirs(src_path)
        if len(dir_list):
            time_str = Mytools.get_time_now().get('time_str')
            self.scr.insert("end", '%s  导出目录结构信息完成，目录结构如下:\n' % time_str)
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
            self.scr.see(tk.END)
            mBox.showinfo("完成", "%s  下并无子目录结构！" % src_path)


class CompareTxtFrame(BaseFrame):  # 继承Frame类
    """比较文本文件内容差异"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_flag = tk.BooleanVar()  # 是否操作目录 True 对比目录 False 对比文件
        self.option = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.record_dir_path = None  # 用来记录文本差异结果文件目录路径
        self.createPage()

    def selectPath1(self):
        if self.dir_flag.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.src_path.set(path_)

    def selectPath2(self):
        if self.dir_flag.get():
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
        ttk.Radiobutton(self.f_input_option, text="对比目录", variable=self.dir_flag, value=True).grid(row=0, column=1)
        ttk.Radiobutton(self.f_input_option, text="对比文件", variable=self.dir_flag, value=False).grid(row=0, column=2)
        self.dir_flag.set(True)  # 设置单选默认值
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

    @deal_running_task_arg('比对文本文件内容')
    def do_compare(self, src_path, dst_path):
        """比对两个目录下同名文本文件内容"""
        write_time, log_time = Mytools.get_times()  # 输出时间（用于命名文件夹），记录日志时间
        self.scr.insert("end", "%s  开始比对文件...\n" % log_time)
        self.record_dir_path = os.path.join(settings.RECORD_DIR, '文本内容差异', write_time)  # 建立用于存储本次差异文件的目录
        if self.dir_flag.get() is False:
            # 对比两个文件内容
            self.record_dir_path = CompareTxt.compare_file(src_path, dst_path, self.record_dir_path)
            time_str = Mytools.get_time_now().get('time_str')
            self.scr.insert("end", "\n\n%s  比对完成！文件文本差异导出到 %s\n" % (time_str, self.record_dir_path))
            mBox.showinfo("完成！", "比对完成！")
        else:  # 比对两个目录下同名文件内容
            self.record_dir_path, result = CompareTxt.compare_file_list2(src_path, dst_path, self.record_dir_path)
            time_str = Mytools.get_time_now().get('time_str')
            total_msg = "\n\n%s  比对完成！详情如下:\n" % time_str
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
            self.scr.see(tk.END)
            mBox.showinfo("完成！", "比对完成！总共有%s个文件文本内容发生变化！" % len(diff_list))
        logger.operate_logger("【比对文本文件内容】  比对 %s 和 %s 下文件内容，文件文本差异导出到 %s" % (src_path, dst_path, self.record_dir_path), log_time)

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
        t.setDaemon(True)
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

    @deal_running_task_arg('计算hash值')
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

    @dragged_locked
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
        if content.endswith('\n'):  # 用于去除每次搜索后多出来的一个换行
            content = content[:-1]
        search_str = self.search_str.get()  # 要搜索的字符串
        if not search_str:  # 无字符
            return
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
        scrolH = 32
        self.scr1 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr1.grid(row=1, column=0, sticky='WE', columnspan=5)
        ttk.Label(self.f_content, text='字符串2: ').grid(row=0, column=5, stick=tk.W, pady=5)
        scrolW = 58
        scrolH = 32
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
        t.setDaemon(True)
        t.start()


class RenameFrame(BaseFrame):
    """递归批量重命名"""
    def __init__(self, master=None):
        super().__init__(master)
        self.option = tk.StringVar()  # 标记是精确匹配还是正则匹配
        self.dir_flag = tk.BooleanVar()  # True 操作文件夹 False 不操作
        self.file_flag = tk.BooleanVar()  # True 操作文件 False 不操作
        self.search_mode = tk.StringVar()  # 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        self.rename_mode = tk.StringVar()  # 重命名模式 1 替换字符 2 增加前缀 3 增加后缀  4 递增重命名
        self.search_str = tk.StringVar()  # 要搜索的字符串
        self.replace_str = tk.StringVar()  # 要替换的新内容
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.ignore_case_flag = tk.BooleanVar()  # 决定是否忽略大小写，正则表达式匹配模式 re.I
        self.natsort_flag = tk.BooleanVar()  # 决定是否以自然数排序，True按自然数排序   正常程序处理字符串顺序是按字符串排序 也就是 1 11 111 2  ，自然数排序则为1 2 11 111
        self.natsort_flag.set(True)
        self.light_flag = tk.BooleanVar()  # 是否高亮显示匹配到的内容，True高亮显示   因为tkinter效率很低，高亮显示要不停输出阻塞，故默认不高亮显示
        self.light_flag.set(False)
        self.start_num = tk.IntVar()  # 初始值
        self.zero_num = tk.IntVar()  # 零位数，左边填充零个数
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.createPage()

    def do_search_regex(self):
        """搜索满足条件的目录或文件(正则模式)"""
        src_path = Mytools.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        if self.ignore_case_flag.get() is True:
            flags = re.I
        else:
            flags = 0
        # 遍历获取全部匹配的路径信息
        if self.dir_flag.get():
            for root, dirs, files in os.walk(src_path):
                for item in dirs:
                    searchObj = re.search(search_str, item, flags)
                    if searchObj:
                        self.result['dirs'].append(os.path.join(root, item))
        if self.file_flag.get():
            for root, dirs, files in os.walk(src_path):
                for item in files:
                    searchObj = re.search(search_str, item, flags)
                    if searchObj:
                        self.result['files'].append(os.path.join(root, item))
        self.deal_show_search_result()

    def do_search_normal(self):
        """搜索满足条件的目录或文件(普通模式 不支持正则语法)"""
        src_path = Mytools.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        # 遍历获取全部匹配的路径信息
        if self.dir_flag.get():
            for root, dirs, files in os.walk(src_path):
                for item in dirs:
                    if search_str in item:
                        self.result['dirs'].append(os.path.join(root, item))
        if self.file_flag.get():
            for root, dirs, files in os.walk(src_path):
                for item in files:
                    if search_str in item:
                        self.result['files'].append(os.path.join(root, item))
        self.deal_show_search_result()

    def do_search_exact(self):
        """搜索满足条件的目录或文件(精确模式 不支持正则语法)"""
        src_path = Mytools.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        # 遍历获取全部匹配的路径信息
        if self.dir_flag.get():
            for root, dirs, files in os.walk(src_path):
                for item in dirs:
                    if search_str == item:
                        self.result['dirs'].append(os.path.join(root, item))
        if self.file_flag.get():
            for root, dirs, files in os.walk(src_path):
                for item in files:
                    if search_str == item:
                        self.result['files'].append(os.path.join(root, item))
        self.deal_show_search_result()

    def show_search_result_regex(self):
        """用于实际显示搜索到的结果
        src_path: 搜索的根目录路径
        search_str: 搜索的内容
        """
        src_path = Mytools.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        if self.ignore_case_flag.get() is True:
            flags = re.I
        else:
            flags = 0
        for item in self.result:
            if len(self.result[item]):
                if item == 'dirs':
                    msg = '文件夹( %s 个):\n' % len(self.result[item])
                else:
                    msg = '文件( %s 个):\n' % len(self.result[item])
                self.scr1.insert('end', msg, 'title')
                for full_path in self.result[item]:
                    tmp_dir = os.path.dirname(full_path).replace(src_path, '')  # 相对于根目录的相对目录层次
                    tmp_name = os.path.basename(full_path)
                    if tmp_dir:
                        self.scr1.insert('end', "%s\\" % tmp_dir[1:])
                    in_strs = re.split(search_str, tmp_name, flags=flags)  # 除去匹配到内容之外的内容
                    all_strs = re.split(r'(%s)' % search_str, tmp_name, flags=flags)  # 所有内容
                    for i in all_strs:
                        if i in in_strs:
                            self.scr1.insert(tk.END, i)  # 匹配到的部分用特殊标记后面设置显示样式
                        else:
                            self.scr1.insert(tk.END, i, "tag")
                    self.scr1.insert('end', "\n")
        print('%s 打印完成！' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')

    def show_search_result_normal(self):
        """用于实际显示搜索到的结果
        src_path: 搜索的根目录路径
        search_str: 搜索的内容
        """
        src_path = Mytools.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        for item in self.result:
            if len(self.result[item]):
                if item == 'dirs':
                    msg = '文件夹( %s 个):\n' % len(self.result[item])
                else:
                    msg = '文件( %s 个):\n' % len(self.result[item])
                self.scr1.insert('end', msg, 'title')
                for full_path in self.result[item]:
                    tmp_dir = os.path.dirname(full_path).replace(src_path, '')  # 相对于根目录的相对目录层次
                    tmp_name = os.path.basename(full_path)
                    if tmp_dir:
                        self.scr1.insert('end', "%s\\" % tmp_dir[1:])
                    # search_str 切割后的列表 若字符串首尾出现search_str则列表首尾为''
                    # strs = item.split(old_str)  # 当old_str 为 '' 会报ValueError: empty separator错误五
                    if search_str:
                        strs = tmp_name.split(search_str)
                        count = tmp_name.count(search_str)  # 共有多少个匹配项
                        i = 0
                        for tmp_str in strs:
                            self.scr1.insert(tk.END, tmp_str)
                            i += 1
                            if i <= count:
                                self.scr1.insert(tk.END, search_str, "tag")  # 匹配到的内容 “tag”标签标记后面做格式
                    else:
                        strs = list(tmp_name)
                        for tmp_str in strs:
                            self.scr1.insert(tk.END, tmp_str, "tag")  # 匹配到的内容 “tag”标签标记后面做格式
                    self.scr1.insert('end', "\n")
        print('%s 打印完成！' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')

    def show_search_result_exact(self):
        """用于实际显示搜索到的结果
        src_path: 搜索的根目录路径
        """
        src_path = Mytools.check_path(self.src_dir.get())
        for item in self.result:
            if len(self.result[item]):
                if item == 'dirs':
                    msg = '文件夹( %s 个):\n' % len(self.result[item])
                else:
                    msg = '文件( %s 个):\n' % len(self.result[item])
                self.scr1.insert('end', msg, 'title')
                for full_path in self.result[item]:
                    tmp_dir = os.path.dirname(full_path).replace(src_path, '')  # 相对于根目录的相对目录层次
                    tmp_name = os.path.basename(full_path)
                    if tmp_dir:
                        self.scr1.insert('end', "%s\\" % tmp_dir[1:])
                    self.scr1.insert(tk.END, tmp_name, "tag")
                    self.scr1.insert('end', "\n")
        self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')

    def deal_show_search_result(self):
        """用于调度显示搜索到的结果
        """
        print('%s 搜索完成！' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        src_path = Mytools.check_path(self.src_dir.get())
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        natsort_flag = self.natsort_flag.get()  # 是否按自然数排序
        light_flag = self.light_flag.get()  # 是否高亮显示匹配道德内容
        # 进行自然数排序并匹配搜索关键字
        if natsort_flag is True:
            self.result['dirs'] = natsorted(self.result['dirs'])  # 按自然数顺序排序
            self.result['files'] = natsorted(self.result['files'])  # 按自然数顺序排序
        # 显示搜索结果
        if light_flag is True:
            if search_mode == '1':  # 简单匹配
                func = self.show_search_result_normal
            elif search_mode == '3':  # 正则匹配
                func = self.show_search_result_regex
            else:  # 精确匹配
                func = self.show_search_result_exact
            t = threading.Thread(target=func)
            t.setDaemon(True)
            t.start()
        else:  # 不高亮显示
            for item in self.result:
                msg = ''
                if len(self.result[item]):
                    if item == 'dirs':
                        self.scr1.insert('end', '文件夹( %s 个):\n' % len(self.result[item]), 'title')
                    else:
                        self.scr1.insert('end', '文件( %s 个):\n' % len(self.result[item]), 'title')
                    for full_path in self.result[item]:
                        msg += '%s\n' % full_path.replace(src_path, '')[1:]  # 去除 \a\c\c.txt 相对路径最开始那个分隔符
                self.scr1.insert(tk.END, '%s\n' % msg)
            print('%s 打印完成！' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
            self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')
        print('%s ok' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        self.scr1.tag_config('tag', background='RoyalBlue', foreground="white")
        # self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')
        self.scr1.tag_config('info', font=('microsoft yahei', 16, 'bold'))
        self.scr1.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr1.see("end")

    def do_search(self):
        """用于调度搜索方法"""
        print('%s 开始' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        self.scr1.delete(1.0, 'end')  # 清空文本区
        self.scr2.delete(1.0, 'end')  # 清空文本区
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.pb1["value"] = 0
        self.record_path = None
        self.btn_undo_rename.config(state=tk.DISABLED)
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        src_path = Mytools.check_path(self.src_dir.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "路径: %s 不存在！请检查！" % self.src_dir.get())
            return
        if search_mode == '1':  # 简单匹配
            self.do_search_normal()
        elif search_mode == '3':  # 正则匹配
            self.do_search_regex()
        else:  # 精确匹配
            self.do_search_exact()

    def deal_search(self):
        """为搜索操作新开一个线程，避免高耗时操作阻塞GUI主线程"""
        t = threading.Thread(target=self.do_search)
        t.setDaemon(True)
        t.start()

    def rename_preview(self):
        """效果预览"""
        rename_mode = self.rename_mode.get()
        if rename_mode == '1':
            self.rename_preview_replace()
        elif rename_mode == '4':
            self.rename_preview_increase()
        else:
            self.rename_preview_pre_ext()

    def rename_preview_replace(self):
        """效果预览 替换字符重命名"""
        self.scr1.delete(1.0, 'end')
        self.scr2.delete(1.0, 'end')
        src_path = self.src_dir.get()
        old_str = self.search_str.get()
        new_str = self.replace_str.get()
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        dir_flag = self.dir_flag.get()  # 是否操作文件夹
        file_flag = self.file_flag.get()  # 是否操作文件
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        flags = re.I if self.ignore_case_flag.get() else 0
        for item in self.result:
            if len(self.result[item]):
                if item == 'dirs':
                    if dir_flag is False:
                        return
                    self.scr1.insert('end', "文件夹:\n", 'title')
                    self.scr2.insert('end', "文件夹:\n", 'title')
                else:
                    if file_flag is False:
                        return
                    self.scr1.insert('end', "文件:\n", 'title')
                    self.scr2.insert('end', "文件:\n", 'title')
                for old_path in self.result[item]:
                    old_dir = os.path.dirname(old_path)
                    old_name = os.path.basename(old_path)
                    new_name = None
                    if search_mode == '1':  # 简单匹配
                        if old_str in old_name:
                            new_name = old_name.replace(old_str, new_str)
                    elif search_mode == '3':  # 正则匹配
                        if re.search(old_str, old_name, flags=re.I):
                            new_name = re.sub(old_str, new_str, old_name, flags=re.I)
                    else:  # 精确模式
                        if old_str == old_name:
                            new_name = old_name.replace(old_str, new_str)
                    if new_name:
                        new_path = os.path.join(old_dir, new_name)
                        old_sub_path = old_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                        new_sub_path = new_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                        self.scr1.insert('end', "%s\n" % old_sub_path)
                        self.scr2.insert('end', "%s\n" % new_sub_path)
                        self.new_old_tuple_list.append((new_path, old_path))
        self.scr1.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr2.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.btn_rename.config(state=tk.NORMAL)

    def rename_preview_pre_ext(self):
        """效果预览  增加前后缀"""
        self.scr1.delete(1.0, 'end')
        self.scr2.delete(1.0, 'end')
        src_path = self.src_dir.get()
        new_str = self.replace_str.get()
        rename_mode = self.rename_mode.get()
        dir_flag = self.dir_flag.get()  # 是否操作文件夹
        file_flag = self.file_flag.get()  # 是否操作文件
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        if new_str:  # 排除空字符串和空格
            new_str = new_str.strip()
            if not new_str:
                return
        else:
            return
        if rename_mode == '3':  # 检查并过滤非法后缀格式
            new_str = re.sub(r'^\.+', '.', new_str)
            new_str = re.sub(r'\.+$', '', new_str)
            if not new_str.startswith('.'):
                new_str = '.' + new_str
        elif rename_mode == '2':
            new_str = re.sub(r'^\.+', '', new_str)
        for item in self.result:
            if len(self.result[item]):
                if item == 'dirs':
                    if dir_flag is False:
                        return
                    self.scr1.insert('end', "文件夹:\n", 'title')
                    self.scr2.insert('end', "文件夹:\n", 'title')
                else:
                    if file_flag is False:
                        return
                    self.scr1.insert('end', "文件:\n", 'title')
                    self.scr2.insert('end', "文件:\n", 'title')
                for old_path in self.result[item]:
                    old_dir = os.path.dirname(old_path)
                    old_name = os.path.basename(old_path)  # 原文件名
                    if rename_mode == '2':
                        new_name = new_str + old_name
                    else:
                        new_name = old_name + new_str
                    if new_name:
                        new_path = os.path.join(old_dir, new_name)
                        old_sub_path = old_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                        new_sub_path = new_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                        self.scr1.insert('end', "\t%s\n" % old_sub_path)
                        self.scr2.insert('end', "\t%s\n" % new_sub_path)
                        self.new_old_tuple_list.append((new_path, old_path))
        self.scr1.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr2.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.btn_rename.config(state=tk.NORMAL)

    def rename_preview_increase(self):
        """效果预览  递增重命名"""
        self.scr1.delete(1.0, 'end')
        self.scr2.delete(1.0, 'end')
        src_path = self.src_dir.get()
        new_str = self.replace_str.get()
        dir_flag = self.dir_flag.get()  # 是否操作文件夹
        file_flag = self.file_flag.get()  # 是否操作文件
        start_num = self.start_num.get()
        zero_num = self.zero_num.get()
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        # 检查并过滤可能导致报错的小数点
        new_str = re.sub(r'^\.+', '', new_str)
        for item in self.result:
            if len(self.result[item]):
                if item == 'dirs':
                    if dir_flag is False:
                        return
                    self.scr1.insert('end', "文件夹:\n", 'title')
                    self.scr2.insert('end', "文件夹:\n", 'title')
                else:
                    if file_flag is False:
                        return
                    self.scr1.insert('end', "文件:\n", 'title')
                    self.scr2.insert('end', "文件:\n", 'title')
                for old_path in self.result[item]:
                    old_dir = os.path.dirname(old_path)
                    old_name = os.path.basename(old_path)  # 原文件名
                    old_ext = os.path.splitext(old_name)[1]
                    if old_ext == '':  # 避免源文件名为'.gitignore' 但是os.path.splitext(old_name) 结果为['.gitignore','']的bug
                        if old_name.startswith('.'):
                            old_ext = old_name
                    new_name = new_str + str(start_num).zfill(zero_num) + old_ext
                    start_num += 1
                    if new_name:
                        new_path = os.path.join(old_dir, new_name)
                        old_sub_path = old_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                        new_sub_path = new_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                        self.scr1.insert('end', "\t%s\n" % old_sub_path)
                        self.scr2.insert('end', "\t%s\n" % new_sub_path)
                        self.new_old_tuple_list.append((new_path, old_path))
        self.scr1.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr2.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.btn_rename.config(state=tk.NORMAL)

    @dragged_locked
    def dragged_files(self, files):
        super().dragged_files(files)
        self.scr1.delete(1.0, 'end')  # 清空文本区
        self.scr2.delete(1.0, 'end')  # 清空文本区
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.pb1["value"] = 0
        self.record_path = None
        self.btn_undo_rename.config(state=tk.DISABLED)
        self.btn_rename.config(state=tk.DISABLED)

    @deal_running_task_arg('批量重命名')
    def do_rename(self):
        """重命名"""
        src_path = Mytools.check_path(self.src_dir.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        self.pb1["maximum"] = len(self.result["dirs"]) + len(self.result["files"])
        new_old_record = {}  # 记录新旧文件名 格式{new_path:old_path,}
        failed_list = []  # 记录重命名失败
        time_now = time.localtime()
        time_now_str = time.strftime("%Y%m%d%H%M%S", time_now)
        time_now_str_log = time.strftime("%Y-%m-%d %H:%M:%S", time_now)
        dirName = os.path.basename(src_path)
        path_failed_record = os.path.join(settings.RECORD_DIR, '%s_renameFailed_%s.txt' % (dirName, time_now_str))  # 移动失败的文件的记录路径
        path_new_old_record = os.path.join(settings.RECORD_DIR, '%s_new_old_record_%s.txt' % (dirName, time_now_str))  # 移动成功的文件的新旧文件名记录路径
        had_existed_count = 0  # 已有重名重复路径文件计数
        # 方式一：重新遍历文件获取文件名/目录名信息进行重命名
        # if file_flag:  # 操作文件
        #     for root, dirs, files in os.walk(src_path, topdown=False):
        #         for file in files:
        #             old_file = os.path.join(root, file)
        #             if search_mode == '1':  # 简单匹配
        #                 if old_str in file:
        #                     new_name = file.replace(old_str, new_str)
        #                 else:
        #                     continue
        #             elif search_mode == '3':  # 正则匹配
        #                 if re.search(old_str, file):
        #                     new_name = re.sub(old_str, new_str, file)
        #                 else:
        #                     continue
        #             else:  # 精确匹配
        #                 if old_str == file:
        #                     new_name = file.replace(old_str, new_str)
        #                 else:
        #                     continue
        #             new_file = os.path.join(root, new_name)
        #             try:
        #                 os.rename(old_file, new_file)
        #                 new_old_record[new_file] = old_file
        #             except Exception:
        #                 failed_list.append(old_file)
        #             self.pb1["value"] += 1
        # if dir_flag:  # 操作目录
        #     for root, dirs, files in os.walk(src_path, topdown=False):
        #         for dir in dirs:
        #             old_dir = os.path.join(root, dir)
        #             if search_mode == '1':  # 简单匹配
        #                 if old_str in dir:
        #                     new_name = dir.replace(old_str, new_str)
        #                 else:
        #                     continue
        #             elif search_mode == '3':  # 正则匹配
        #                 if re.search(old_str, dir):
        #                     new_name = re.sub(old_str, new_str, dir)
        #                 else:
        #                     continue
        #             else:  # 精确匹配
        #                 if old_str == dir:
        #                     new_name = dir.replace(old_str, new_str)
        #                 else:
        #                     continue
        #             new_dir = os.path.join(root, new_name)
        #             try:
        #                 os.rename(old_dir, new_dir)
        #                 new_old_record[new_dir] = old_dir
        #             except Exception:
        #                 failed_list.append(old_dir)
        #             self.pb1["value"] += 1

        # 方式二：直接用之前rename_preview得到的self.new_old_tuple_list进行重命名操作
        self.new_old_tuple_list.reverse()  # 反转目录列表 避免先修改顶级目录名导致子目录路径无法找到
        # print(self.new_old_tuple_list)
        for new_path, old_path in self.new_old_tuple_list:
            try:
                print(old_path + '  >>>  ' + new_path)
                os.rename(old_path, new_path)
                new_old_record[new_path] = old_path
            except Exception as e:
                if os.path.exists(new_path):
                    had_existed_count += 1
                print("Error: " + str(e))
                failed_list.append(old_path)
            self.pb1["value"] += 1

        log_msg = ""
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
            self.btn_undo_rename.config(state=tk.NORMAL)
        else:
            msg = "无重命名操作！ "
        if len(failed_list):
            log_msg += " %s 个项目重命名失败，其中 %s 个项目在该路径下已有同名项目存在无法重命名，重命名失败记录到%s" % (len(failed_list), had_existed_count, path_failed_record)
            msg += "\n %s 个项目重命名失败，其中 %s 个项目在该路径下已有同名项目存在无法重命名，重命名失败记录到%s" % (len(failed_list), had_existed_count, path_failed_record)
            with open(path_failed_record, 'a', encoding='utf-8') as f:
                for item in failed_list:
                    f.write("%s\n" % item)
        if log_msg:
            logger.operate_logger('【重命名操作】  %s' % log_msg, has_time=time_now_str_log)
        self.scr2.insert(tk.END, '\n\n\n\n%s' % msg)
        self.scr2.see(tk.END)
        self.record_path = path_new_old_record  # 记录重命名记录
        mBox.showinfo("完成", msg)

    @deal_running_task_arg('撤销重命名')
    def undo_rename(self):
        """撤销重命名"""
        # 读取记录
        if self.record_path is None:
            return
        with open(self.record_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
        failed_list = []  # 记录重命名失败
        time_now_str = time.strftime('%Y%m%d%H%M%S', time.localtime())
        path_failed_record = os.path.join(settings.RECORD_DIR, 'undo_renameFailed_%s.txt' % time_now_str)  # 撤销重命名失败
        succ_count = 0  # 撤销重命名成功数
        for item in content:
            new_path, old_path = item.strip().split('\t')
            try:
                os.rename(new_path, old_path)
                succ_count += 1
            except Exception as e:
                failed_list.append(new_path)

        log_msg = "根据%s ，撤销重命名操作完成！" % self.record_path
        time_str = Mytools.get_time_now().get('time_str')
        logger.operate_logger('【撤销重命名操作】  %s' % log_msg, has_time=time_str)
        self.scr2.insert(tk.END, '\n\n\n\n%s  %s\n' % (time_str, log_msg))
        self.scr2.see(tk.END)
        self.btn_undo_rename.config(state=tk.DISABLED)
        self.btn_rename.config(state=tk.NORMAL)
        mBox.showinfo("完成", log_msg)

    def createPage(self):
        self.l_title["text"] = "批量重命名"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1, columnspan=3)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=4)
        ttk.Label(self.f_input, text='搜索语句: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.search_str, width=80).grid(row=1, column=1, columnspan=3,stick=tk.W)
        ttk.Button(self.f_input, text="搜索", command=self.deal_search).grid(row=1, column=4)
        ttk.Label(self.f_input, text='新字符串: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.replace_str, width=80).grid(row=2, column=1, columnspan=3,stick=tk.W)
        ttk.Button(self.f_input, text="预览", command=self.rename_preview).grid(row=2, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=5, stick=tk.EW)
        ttk.Label(self.f_input_option, text='设置模式: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="操作文件夹", variable=self.dir_flag, onvalue=True, offvalue=False).grid(
            row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="操作文件", variable=self.file_flag, onvalue=True, offvalue=False).grid(
            row=0, column=2, sticky=tk.W)
        self.dir_flag.set(True)
        self.file_flag.set(True)
        ttk.Label(self.f_input_option, text="匹配模式:").grid(row=0, column=4, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="简单匹配(子集)", variable=self.search_mode, value='1', command=self.invoke_ingorecase).grid(row=0, column=5, sticky=tk.E)
        ttk.Radiobutton(self.f_input_option, text="精确匹配(完全一致)", variable=self.search_mode, value='2', command=self.invoke_ingorecase).grid(row=0, column=6, sticky=tk.E)
        ttk.Radiobutton(self.f_input_option, text="正则匹配", variable=self.search_mode, value='3', command=self.invoke_ingorecase).grid(row=0, column=7, sticky=tk.E)
        self.search_mode.set('1')
        self.btn_chk_ignore_case = ttk.Checkbutton(self.f_input_option, text="忽略大小写差异", variable=self.ignore_case_flag, onvalue=True, offvalue=False, state=tk.DISABLED)
        self.btn_chk_ignore_case.grid(row=0, column=8, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="按自然数排序", variable=self.natsort_flag, onvalue=True, offvalue=False).grid(row=0, column=9, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="高亮显示", variable=self.light_flag, onvalue=True, offvalue=False).grid(row=0, column=10, sticky=tk.W)
        self.f_input_option2 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option2.grid(row=4, column=0, columnspan=2, stick=tk.EW)
        ttk.Label(self.f_input_option2, text='重命名模式: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option2, text="替换字符", variable=self.rename_mode, value='1').grid(
            row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="添加前缀", variable=self.rename_mode, value='2').grid(
            row=1, column=2, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="添加后缀", variable=self.rename_mode, value='3').grid(
            row=1, column=3, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="递增编号", variable=self.rename_mode, value='4').grid(
            row=1, column=4, sticky=tk.W)
        self.rename_mode.set('1')
        ttk.Label(self.f_input_option2, text='初始值:').grid(row=1, column=5, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option2, textvariable=self.start_num, width=8).grid(row=1, column=6, stick=tk.W)
        ttk.Label(self.f_input_option2, text='零位数:').grid(row=1, column=7, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option2, textvariable=self.zero_num, width=8).grid(row=1, column=8, stick=tk.W)
        self.f_input_option3 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option3.grid(row=4, column=2, columnspan=3, stick=tk.E)
        self.btn_undo_rename = ttk.Button(self.f_input_option3, text='撤销重命名', command=self.undo_rename, state=tk.DISABLED)
        self.btn_undo_rename.grid(row=0, column=0, stick=tk.E, pady=10)
        ttk.Button(self.f_input_option3, text='清除', command=self.clear).grid(row=0, column=1, stick=tk.E)
        self.btn_rename = ttk.Button(self.f_input_option3, text='重命名', command=self.run, state=tk.DISABLED)
        self.btn_rename.grid(row=0, column=2, stick=tk.E)
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
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def invoke_ingorecase(self):
        """激活忽略大小写单选框"""
        if self.search_mode.get() == '3':
            self.btn_chk_ignore_case.config(state=tk.NORMAL)
        else:
            self.btn_chk_ignore_case.config(state=tk.DISABLED)

    def selectPath(self):
        path_ = askdirectory()
        self.src_dir.set(path_)
        self.btn_rename.config(state=tk.DISABLED)

    def clear(self):
        """用于清除数据"""
        self.scr1.delete(1.0, 'end')  # 清空文本区
        self.scr2.delete(1.0, 'end')  # 清空文本区
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.pb1["value"] = 0
        self.src_dir.set('')
        self.dst_dir.set('')
        self.search_str.set('')
        self.replace_str.set('')
        self.record_path = None
        self.btn_undo_rename.config(state=tk.DISABLED)

    def run(self):
        # self.clear()
        t = threading.Thread(target=self.do_rename)
        t.setDaemon(True)
        t.start()


class GetImgFrame(BaseFrame):
    """提取视频帧图像"""
    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()  # 帧率或者秒数
        self.continue_flag = tk.BooleanVar()  # 是否继续上次进度
        self.src_dir = tk.StringVar()  # 视频路径
        self.dst_dir = tk.StringVar()  # 图像路径
        self.get_photo_by_sec_flag = tk.BooleanVar()  # 是否按秒数提取图片，True 按秒 False 按帧数
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "提取视频帧图像"
        ttk.Label(self.f_input, text='源视频目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=95).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='图片保存路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=95).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        self.get_photo_by_sec_flag.set(True)  # 默认按时间点提取图像
        ttk.Label(self.f_input_option, text='提取第 ').grid(row=0, column=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=8, justify=tk.CENTER).grid(row=0, column=1, stick=tk.W)
        self.inputNum.set(3)  # 设置默认值
        ttk.Label(self.f_input_option, text=' 秒图像(负值为倒数时间，即倒数第三秒为-3)').grid(row=0, column=2, stick=tk.W, pady=10)
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=6, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看提取完成帧图像", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.scr.delete(1.0, tk.END)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[Img]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    @deal_running_task_arg('提取视频帧图像')
    def deal_get_img(self):
        extract_time_point = self.inputNum.get()
        continue_flag = self.continue_flag.get()
        video_dir = Mytools.check_path(self.src_dir.get())
        img_dir = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        if video_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        flag = check_floatNum(extract_time_point)
        print("flag:", flag)
        if flag is False:
            mBox.showerror("错误！", "输入秒数有误！请检查是否包含非数学字符！")
            return
        extract_time_point = float(extract_time_point)
        VideoTools.get_img_by_sec(self, video_dir, img_dir, extract_time_point, continue_flag)  # 单线程
        # VideoTools.get_img_from_video(self, video_dir, img_dir, extract_time_point, continue_flag)  # 多线程

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        # print(self.video_dir.get(), self.img_dir.get(), self.inputNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_get_img)
        t.setDaemon(True)
        t.start()


class CalImgSimFrame(BaseFrame):
    """计算图片相似度"""
    def __init__(self, master=None):
        super().__init__(master)
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        # self.phash = {}  # 记录计算好的图片phash
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "计算图片相似度"
        ttk.Label(self.f_input, text='源图片目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1): ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=8, justify=tk.CENTER).grid(row=0, column=1, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='  导出方式: ').grid(row=0, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row= 0, column=3, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row= 0, column=4, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否
        # ttk.Button(self.f_input, text="导出phash记录", command=self.export_phash).grid(row=3, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似图片", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.record_path = None
        self.scr.delete(1.0, tk.END)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            mBox.showinfo('还原文件完成！', msg)

    @deal_running_task_arg('查找相似图片')
    def deal_image_similarity(self):
        # print(self.src_path.get(), self.dst_path.get(), self.threshold.get(), self.option.get())
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        threshold = self.threshold.get()
        option = self.option.get()
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if src_path == dst_path:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if check_threNum(threshold) is not True:
            mBox.showerror("相似度阈值错误！", "相似度阈值须为0~1之间的小数!")
            return
        threshold = float(threshold)
        record, msg, self.record_path = ImageTools.find_sim_img(self, src_path, dst_path, threshold, option,log_flag=True)
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
        t.setDaemon(True)
        t.start()


class CalVideoSimFrame(BaseFrame):
    """计算视频相似度"""

    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()  # 输入秒数或者帧数
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "查找相似视频"
        ttk.Label(self.f_input, text='源视频目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Label(self.f_input_option, text='比对第 ').grid(row=0, column=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=8, justify=tk.CENTER).grid(row=0, column=1, stick=tk.W)
        self.inputNum.set(3)  # 设置默认值为3
        ttk.Label(self.f_input_option, text=' 秒图像(负值为倒数时间，即倒数第三秒为-3) ').grid(row=0, column=2, stick=tk.W, pady=10)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1): ').grid(row=0, column=3, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=5, justify=tk.CENTER).grid(row=0, column=4, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='导出方式: ').grid(row=0, column=5, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row=0, column=6, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row=0, column=7, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=8, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似视频", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            mBox.showinfo('还原文件完成！', msg)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.record_path = None
        self.scr.delete(1.0, tk.END)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    @deal_running_task_arg('查找相似视频')
    def deal_video_similarity(self, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
        msg, self.record_path = VideoTools.find_sim_video(self, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold,
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
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        continue_flag = self.continue_flag.get()
        option = self.option.get()
        inputNum = self.inputNum.get()
        threshold = self.threshold.get()
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
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
        t.setDaemon(True)
        t.start()


class SearchImgFrame(BaseFrame):
    """以图搜图"""

    def __init__(self, master=None):
        super().__init__(master)
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()  # 操作文件的方式 复制或者剪切
        self.src_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()
        self.eg_path = tk.StringVar()  # 原有图片路径或者phash json
        self.mode = tk.BooleanVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def selectPath3(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.eg_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "以图搜图"
        ttk.Label(self.f_input, text='图片样品路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=98).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=98).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='原有图片目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.eg_path, width=98).grid(row=2, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, stick=tk.EW)
        # ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, stick=tk.W, pady=10)
        # ttk.Radiobutton(self.f_input_option, text="根据原有图片目录", variable=self.mode, value=True).grid(row=0, column=1, sticky=tk.EW)
        # ttk.Radiobutton(self.f_input_option, text="根据原有图片phash信息", variable=self.mode, value=False).grid(row=0, column=2, sticky=tk.EW)
        self.mode.set(True)  # 设置默认值

        ttk.Label(self.f_input_option, text='相似度阈值(0~1):').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=8, justify=tk.CENTER).grid(row=1, column=1, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='导出方式:').grid(row=1, column=3, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row=1, column=4, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row=1, column=5, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 31
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似图片", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @deal_running_task_arg('还原文件')
    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            mBox.showinfo('还原文件完成！', msg)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.scr.delete(1.0, tk.END)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    @deal_running_task_arg('以图搜图')
    def deal_image_similarity(self):
        # print(self.search_dir.get(), self.save_dir.get(), self.threshold.get(), self.option.get())
        search_dir = Mytools.check_path(self.src_dir.get())
        eg_dir = Mytools.check_path(self.eg_path.get())
        save_dir = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        option = self.option.get()
        threshold = self.threshold.get()
        if search_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if eg_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.eg_path.get())
            return
        if (search_dir == save_dir) or (eg_dir == save_dir):
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        if check_threNum(threshold) is not True:
            mBox.showerror("相似度阈值错误！", "相似度阈值须为0~1之间的小数!")
            return
        threshold = float(threshold)
        record, msg, self.record_path = ImageTools.search_img_by_img(self, search_dir, eg_dir, save_dir, threshold, option)
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
        t.setDaemon(True)
        t.start()


class SearchVideoFrame(BaseFrame):
    """以视频搜索相似视频"""

    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.src_dir = tk.StringVar()
        self.eg_path = tk.StringVar()  # 原有视频路径或者phash json
        self.mode = tk.StringVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.dst_dir = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.createPage()

    def selectPath3(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.eg_path.set(path_)

    def createPage(self):
        self.l_title["text"] = "以视频搜索视频"
        ttk.Label(self.f_input, text='视频样本目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=98).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=98).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='原有视频目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.eg_path, width=98).grid(row=2, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)

        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, stick=tk.EW)
        # ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        # ttk.Radiobutton(self, text="根据原有视频目录", variable=self.mode, value="原有视频目录", command=self.changeMode).grid(column=1, row=4, sticky=tk.EW)
        # ttk.Radiobutton(self, text="根据原有视频导出帧图片目录", variable=self.mode, value="原有视频导出帧图片目录", command=self.changeMode).grid(column=2, row=4, sticky=tk.EW)
        # ttk.Radiobutton(self, text="根据原有视频导出帧图片phash信息", variable=self.mode, value="原有视频导出帧图片目录", command=self.changeMode).grid(column=3, row=4, sticky=tk.EW)
        self.mode.set("原有视频目录")  # 设置默认值
        ttk.Label(self.f_input_option, text='比对第 ').grid(row=0, column=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=8, justify=tk.CENTER).grid(row=0, column=1, stick=tk.W)
        ttk.Label(self.f_input_option, text='秒图像(负值为倒数时间，即倒数第三秒为-3) ').grid(row=0, column=2, stick=tk.W, pady=10)
        self.inputNum.set(3)  # 设置默认值为3
        ttk.Label(self.f_input_option, text='相似度阈值(0~1):').grid(row=0, column=3, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=8, justify=tk.CENTER).grid(row=0, column=4, stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='导出方式:').grid(row=0, column=5, stick=tk.W, padx=10, pady=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.option, value="copy").grid(row=0, column=6,
                                                                                                 sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.option, value="move").grid(row=0, column=7,
                                                                                                 sticky=tk.W)
        self.option.set("copy")  # 设置默认选中剪切
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=8, sticky=tk.W, padx=10)
        self.continue_flag.set(False)  # 设置默认选中否

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 31
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看相似视频", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @deal_running_task_arg('还原文件')
    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            restore_path, count = Mytools.restore_file_by_record(self.record_path)
            time_str = Mytools.get_time_now().get('time_str')
            msg = "根据%s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.operate_logger('【文件还原操作】  %s' % msg, time_str)
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            mBox.showinfo('还原文件完成！', msg)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.scr.delete(1.0, tk.END)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    @deal_running_task_arg('以视频搜相似视频')
    def deal_video_similarity(self, src_dir, eg_path, dst_dir, frame_num, continue_flag, threshold, deal_video_mode):
        msg, self.record_path = VideoTools.search_video(self, src_dir, eg_path, dst_dir, frame_num, continue_flag, threshold, deal_video_mode)
        if self.record_path:
            self.btn_restore.config(state=tk.NORMAL)
        mBox.showinfo("查找相似视频完成!", msg)

    def run(self):
        self.record_path = None
        self.btn_restore.config(state=tk.DISABLED)
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        search_dir = Mytools.check_path(self.src_dir.get())
        eg_path = Mytools.check_path(self.eg_path.get())
        save_dir = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        option = self.option.get()
        continue_flag = self.continue_flag.get()
        inputNum = self.inputNum.get()
        threshold = self.threshold.get()
        if search_dir is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if eg_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % eg_path)
            return
        if (search_dir == save_dir) or (eg_path == save_dir):
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
        args = (search_dir, eg_path, save_dir, inputNum, continue_flag, threshold, option)
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.setDaemon(True)
        t.start()


class GetAudioFrame(BaseFrame):
    """从视频中提取音频或者转换音频格式"""

    def __init__(self, master=None):
        super().__init__(master)
        self.continue_flag = tk.BooleanVar()
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.sub_start_time_h = tk.StringVar()  # 获取开始剪切时间 小时
        self.sub_start_time_m = tk.StringVar()  # 获取开始剪切时间 分钟
        self.sub_start_time_s = tk.StringVar()  # 获取开始剪切时间 秒
        self.sub_stop_time_h = tk.StringVar()  # 获取剪切结束时间
        self.sub_stop_time_m = tk.StringVar()  # 获取剪切结束时间
        self.sub_stop_time_s = tk.StringVar()  # 获取剪切结束时间
        self.time_input_entrys = []  # 储存时间输入框组件
        self.time_inputs = [self.sub_start_time_h,
                            self.sub_start_time_m,
                            self.sub_start_time_s,
                            self.sub_stop_time_h,
                            self.sub_stop_time_m,
                            self.sub_stop_time_s]  # 储存时间输入tk变量
        self.file_type = tk.StringVar()  # 视频格式
        self.file_type.set('mp3')  # 音频格式  mp3 aac
        self.frameNum = tk.StringVar()  # 音频采样率 44100
        self.bitrate = tk.StringVar()  # 音频码率/比特率  128k 192k
        self.invoke_fps_flag = tk.BooleanVar()  # 是否激活帧率/采样率输入框
        self.invoke_type_flag = tk.BooleanVar()  # 是否激活音频格式输入框
        self.cut_time_flag = tk.BooleanVar()  # 是否按时间截取  True按时间截取
        self.cut_time_flag.set(False)
        self.invoke_bitrate_flag = tk.BooleanVar()  # 是否修改码率/比特率
        self.clear_time_input_flag = tk.BooleanVar()  # 是否清空时间输入框内容
        self.deal_exists_mode = tk.StringVar()  # 处理已存在目标路径的同名文件方式 0.跳过 1.覆盖 2.询问
        self.deal_exists_mode.set('2')
        self.copy_codec_flag = tk.BooleanVar()  # 采用原编码，注意比如视频中音频编码为aac,导出成aac的时候才能勾选，否则会出错，必须保证原音频编码和导出后的音频编码一致否则不能勾选！！！
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "提取/转换音频"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Checkbutton(self.f_input_option, text="修改格式", variable=self.invoke_type_flag, onvalue=True,
                        offvalue=False, command=self.invoke_type).grid(row=0, column=0, stick=tk.W)
        self.e_type = ttk.Entry(self.f_input_option, textvariable=self.file_type, width=10, state=tk.DISABLED)
        self.e_type.grid(row=0, column=1, stick=tk.W, padx=5)
        ttk.Checkbutton(self.f_input_option, text="修改采样率", variable=self.invoke_fps_flag, onvalue=True,
                        offvalue=False, command=self.invoke_fps).grid(row=0, column=2, sticky=tk.EW, padx=5)
        self.e_fps = ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=8, state=tk.DISABLED)  # 视频帧率输入框
        self.e_fps.grid(row=0, column=3, stick=tk.W)
        ttk.Checkbutton(self.f_input_option, text="修改码率", variable=self.invoke_bitrate_flag, onvalue=True,
                        offvalue=False, command=self.invoke_bitrate).grid(row=0, column=4, sticky=tk.EW, padx=5)
        self.e_bitrate = ttk.Entry(self.f_input_option, textvariable=self.bitrate, width=8, state=tk.DISABLED)  # 视频帧率输入框
        self.e_bitrate.grid(row=0, column=5, stick=tk.W)
        ttk.Checkbutton(self.f_input_option, text="清空时间输入框内容", variable=self.clear_time_input_flag, onvalue=True,
                        offvalue=False, command=self.clear_time_input).grid(row=0, column=6, sticky=tk.EW, padx=5)
        self.clear_time_input_flag.set(True)  # 设置默认选中
        ttk.Checkbutton(self.f_input_option, text="采用原编码", variable=self.copy_codec_flag, onvalue=True, offvalue=False).grid(row=0, column=7, sticky=tk.W, padx=10)
        self.copy_codec_flag.set(False)  # 设置默认选中否
        self.f_time_option = ttk.Frame(self.f_input)  # 时间输入容器
        self.f_time_option.grid(row=3, columnspan=3, stick=tk.EW)
        ttk.Checkbutton(self.f_time_option, text='按时间截取，从: ', variable=self.cut_time_flag, onvalue=True, offvalue=False, command=self.invoke_time).grid(row=1, column=0, stick=tk.W, pady=10)
        self.e_sub_start_time_h = ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_h, width=5)
        self.e_sub_start_time_h.grid(row=1, column=1, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=2, stick=tk.W, pady=10)
        self.e_sub_start_time_m = ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_m, width=5)
        self.e_sub_start_time_m.grid(row=1, column=3, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=4, stick=tk.W, pady=10)
        self.e_sub_start_time_s = ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_s, width=5)
        self.e_sub_start_time_s.grid(row=1, column=5, stick=tk.W)
        ttk.Label(self.f_time_option, text='   至: ').grid(row=1, column=6, stick=tk.W, pady=10)
        self.e_sub_stop_time_h = ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_h, width=5)
        self.e_sub_stop_time_h.grid(row=1, column=7, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=8, stick=tk.W, pady=10)
        self.e_sub_stop_time_m = ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_m, width=5)
        self.e_sub_stop_time_m.grid(row=1, column=9, stick=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=10, stick=tk.W, pady=10)
        self.e_sub_stop_time_s = ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_s, width=5)
        self.e_sub_stop_time_s.grid(row=1, column=11, stick=tk.W)
        self.time_input_entrys = [self.e_sub_start_time_h, self.e_sub_start_time_m, self.e_sub_start_time_s,
                                  self.e_sub_stop_time_h, self.e_sub_stop_time_m, self.e_sub_stop_time_s]
        # 设置默认锁定时间输入框
        for enrty_time in self.time_input_entrys:
            enrty_time.config(state=tk.DISABLED)
        ttk.Label(self.f_time_option, text='目标路径已存在同名文件：').grid(row=1, column=12, stick=tk.W, padx=5)
        ttk.Radiobutton(self.f_time_option, text='跳过', variable=self.deal_exists_mode, value=0).grid(row=1, column=13, sticky=tk.EW)
        ttk.Radiobutton(self.f_time_option, text='覆盖', variable=self.deal_exists_mode, value=1).grid(row=1, column=14, sticky=tk.EW)
        ttk.Radiobutton(self.f_time_option, text='询问', variable=self.deal_exists_mode, value=2).grid(row=1, column=15, sticky=tk.EW)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        ttk.Label(self.f_state, text='完成进度: ').grid(row=0, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=800, value=0, mode="determinate")
        self.pb1.grid(row=0, column=1, columnspan=5, stick=tk.EW)
        scrolW = 120
        scrolH = 34
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def clear_time_input(self):
        """清除时间输入框内容"""
        # self.sub_start_time_h.set('')
        # self.sub_start_time_m.set('')
        # self.sub_start_time_s.set('')
        # self.sub_stop_time_h.set('')
        # self.sub_stop_time_m.set('')
        # self.sub_stop_time_s.set('')
        for item in self.time_inputs:
            item.set('')

    def invoke_time(self):
        """激活时间输入框"""
        if self.cut_time_flag.get():  # 按时间截取
            # 设置默认解锁时间输入框
            for enrty_time in self.time_input_entrys:
                enrty_time.config(state=tk.NORMAL)
        else:
            # 清除时间输入框内容
            for item in self.time_inputs:
                item.set('')
            # 设置默认锁定时间输入框
            for enrty_time in self.time_input_entrys:
                enrty_time.config(state=tk.DISABLED)

    def invoke_fps(self):
        """激活音频采样率输入框"""
        if self.invoke_fps_flag.get():
            self.e_fps.config(state=tk.NORMAL)
        else:
            self.frameNum.set('')
            self.e_fps.config(state=tk.DISABLED)

    def invoke_bitrate(self):
        """激活音频比特率输入框"""
        if self.invoke_bitrate_flag.get():
            self.e_bitrate.config(state=tk.NORMAL)
        else:
            self.bitrate.set('')
            self.e_bitrate.config(state=tk.DISABLED)

    def invoke_type(self):
        """激活音频格式输入框"""
        if self.invoke_type_flag.get():
            self.e_type.config(state=tk.NORMAL)
        else:
            self.file_type.set('mp3')
            self.e_type.config(state=tk.DISABLED)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.scr.delete(1.0, tk.END)
        if self.clear_time_input_flag.get() is True:
            self.clear_time_input()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
        src_dir = self.src_dir.get().strip()
        if os.path.isfile(src_dir):
            self.dst_dir.set(os.path.join(os.path.dirname(src_dir), 'audios'))
        else:
            self.dst_dir.set(os.path.abspath(src_dir) + '[audio]')

    @deal_running_task_arg('提取|转换音频')
    def deal_get_audio(self):
        """提取音频"""
        src_dir = Mytools.check_path(self.src_dir.get())
        dst_dir = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        if src_dir is None:
            mBox.showerror("路径不存在！", "输入路径 %s 不存在！请检查！" % self.src_dir.get())
            return
        if src_dir == dst_dir:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        fps = get_int_value(self.frameNum.get().strip(), None)
        bitrate = self.bitrate.get().strip()
        audio_type = self.file_type.get().strip()
        audio_type = re.sub(r'^\.+', '', audio_type)
        sub_start_time_h = self.sub_start_time_h.get().strip()  # 获取开始剪切时间
        sub_start_time_m = self.sub_start_time_m.get().strip()  # 获取开始剪切时间
        sub_start_time_s = self.sub_start_time_s.get().strip()  # 获取开始剪切时间
        sub_stop_time_h = self.sub_stop_time_h.get().strip()  # 获取剪切的结束时间
        sub_stop_time_m = self.sub_stop_time_m.get().strip()  # 获取剪切的结束时间
        sub_stop_time_s = self.sub_stop_time_s.get().strip()  # 获取剪切的结束时间
        sub_start_time_h = get_int_value(sub_start_time_h, 0)  # 获取开始剪切时间
        sub_start_time_m = get_int_value(sub_start_time_m, 0)  # 获取开始剪切时间
        sub_start_time_s = get_float_value(sub_start_time_s, 0)  # 获取开始剪切时间
        sub_stop_time_h = get_int_value(sub_stop_time_h, 0)  # 获取剪切的结束时间
        sub_stop_time_m = get_int_value(sub_stop_time_m, 0)  # 获取剪切的结束时间
        sub_stop_time_s = get_float_value(sub_stop_time_s, 0)  # 获取剪切的结束时间
        startPoint = sub_start_time_h * 3600 + sub_start_time_m * 60 + sub_start_time_s
        endPoint = sub_stop_time_h * 3600 + sub_stop_time_m * 60 + sub_stop_time_s
        path_list = []  # 要操作的文件路径
        time_res = Mytools.get_time_now()  # 记录程序开始操作时间
        time_str = time_res.get('time_str')
        start_time = time_res.get('timestamp')  # 开始时间
        self.scr.insert('end', "%s  开始遍历文件目录....\n" % time_str)
        # 遍历文件目录
        if os.path.isfile(src_dir):  # 操作单个视频文件
            path_list.append(src_dir)
        else:  # 操作目录
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    path_list.append(os.path.join(root, file))
        get_video_time_msg = "遍历%s 完成！总共%s个文件,用时%ss\n" % (src_dir, len(path_list), (time.time() - start_time))
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert('end', '\n%s  %s\n\t开始处理音频...\n' % (time_str, get_video_time_msg))
        self.pb1["maximum"] = len(path_list)  # 总项目数
        # 开始处理音频
        for pathIn in path_list:
            dst_name = "%s.%s" % (os.path.splitext(os.path.basename(pathIn))[0], audio_type)
            if os.path.abspath(pathIn) == os.path.abspath(src_dir):
                pathOut = os.path.join(dst_dir, dst_name)
            else:
                pathOut = os.path.join(os.path.dirname(pathIn).replace(src_dir, dst_dir), dst_name)
            # print(pathIn, pathOut, startPoint, endPoint, fps, bitrate)
            self.do_get_audio(pathIn, pathOut, startPoint, endPoint, fps, bitrate)
            self.pb1["value"] += 1
        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
        total_msg = "  处理 %s 的音频到 %s 完成！用时%.3fs" % (src_dir, dst_dir, time.time() - start_time)
        print(local_time + total_msg)
        mBox.showinfo('完成！', total_msg)
        self.scr.insert('end', '\n\n%s  %s\n' % (local_time, total_msg))
        self.scr.see(tk.END)
        if self.clear_time_input_flag.get():
            self.clear_time_input()
        logger.operate_logger('【音频处理操作】  %s' % total_msg, local_time)

    def do_get_audio(self, pathIn, pathOut, startPoint, endPoint, fps, bitrate):
        """实际处理音频的函数"""
        audio_type = self.file_type.get().strip()
        audio_type = re.sub(r'^\.+', '', audio_type)
        # command = [self.ffmpeg_path, '-ss', sub_start_time, '-i', pathIn, '-acodec', 'copy', '-t',sub_stop_time, pathOut]
        command = [self.ffmpeg_path, '-i', pathIn]  # 命令
        dst_dir = os.path.dirname(pathOut)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        if self.cut_time_flag.get():
            # command.extend(['-ss', startPoint, '-t', endPoint])  # 放在这里有负数时会报错 命令 负数横杠会跟命令参数混淆
            # 获取音视频信息
            duration = 0
            audio_info = get_video_length(self.ffmpeg_path, pathIn)  # 视频信息
            if audio_info:
                duration = float(audio_info.get('total'))  # 时长 秒  ,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
            if endPoint <= 0:  # 结束时间点为0或者负数
                endPoint = duration + endPoint
            if startPoint < 0:
                startPoint = duration + startPoint
            dst_name = "%s_(%ss_to_%ss).%s" % (os.path.splitext(os.path.basename(pathIn))[0], startPoint, endPoint, audio_type)
            pathOut = os.path.join(dst_dir, dst_name)
            sub_stop_time = millisecToAssFormat(endPoint)
            sub_start_time = millisecToAssFormat(startPoint)
            # command.extend(['-ss', startPoint, '-t', endPoint])  # 一直报错 TypeError: expected str, bytes or os.PathLike object, not int
            # 怀疑是不能直接填数字, 试试用时间字符
            # sub_start_time = millisecToAssFormat(startPoint)
            # sub_stop_time = millisecToAssFormat(endPoint)
            # command.extend(['-ss', sub_start_time, '-t', sub_stop_time])
            command.extend(['-ss', str(startPoint), '-t', str(endPoint)])  # 直接填字符串的数值也可以
            msg = "处理 %s 从 %s 至 %s 的音频到 %s 完成！" % (pathIn, sub_start_time, sub_stop_time, pathOut)
        else:
            msg = "处理 %s 的音频到 %s 完成！" % (pathIn, pathOut)
        if os.path.exists(pathOut):  # 目标路径已存在同名文件
            print('{}已存在！'.format(pathOut))
            deal_exists_mode = self.deal_exists_mode.get()  # 处理已存在同名文件
            if deal_exists_mode == '0':  # 跳过
                return
            elif deal_exists_mode == '1':  # 覆盖
                command.append('-y')
            else:  # 询问
                write_option = mBox.askyesno('覆盖前询问', '{} 已存在！是否覆盖？'.format(pathOut))
                if write_option:
                    command.append('-y')
                else:
                    return
        # 操作文件
        if fps:
            command.extend(['-ar', fps])
        if bitrate:
            command.extend(['-b:a', bitrate])
        if self.copy_codec_flag.get():
            command.extend(['-acodec', 'copy'])
        command.append(pathOut)
        # print(command)
        subprocess.call(command, shell=True)
        print(msg)
        self.scr.insert('end', '\n\n%s\n' % msg)
        self.scr.see(tk.END)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        # print(self.src_dir.get(), self.dst_dir.get(), self.frameNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_get_audio)
        t.setDaemon(True)
        t.start()


class VideoMergeFrame(BaseFrame):
    """视频合并"""

    def __init__(self, master=None):
        super().__init__(master)
        self.format = tk.StringVar()  # 视频格式
        self.frameNum = tk.StringVar()  # 视频帧率 ， 不填则为原视频帧率
        self.continue_flag = tk.BooleanVar()
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.createPage()

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
        ttk.Entry(self.f_input_option, textvariable=self.format, width=8, justify=tk.CENTER).grid(row=0, column=1, stick=tk.W)
        self.format.set("mp4")  # 设置默认值为MP4
        ttk.Label(self.f_input_option, text='视频帧率:').grid(row=0, column=2, stick=tk.W, padx=10, pady=10)
        ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=8, justify=tk.CENTER).grid(row=0, column=3, stick=tk.W)
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
        scrolH = 34
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles).grid(row=0, column=0, pady=10, sticky=tk.W)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.scr.delete(1.0, tk.END)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

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

    @deal_running_task_arg('视频合并')
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
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert('end', '%s  开始遍历文件目录...\n' % time_str)
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
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert('end', '\n%s  开始合并视频...\n' % time_str)
        self.do_merge(dst_path, src_path, video_type, frame_num)  # 合并src_path本身目录下的视频

        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 记录完成时间
        total_msg = "合并目录%s 下视频（帧率：%s）到%s 下,用时%.3fs" % (src_path, frame_num, dst_path, time.time() - start_time)
        print(local_time + total_msg)
        self.scr.insert('end', '\n\n%s  %s\n' % (local_time, total_msg))
        self.scr.see(tk.END)
        logger.operate_logger('【视频合并操作】  %s' % total_msg, local_time)
        mBox.showinfo('完成！', total_msg)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        print(self.src_dir.get(), self.dst_dir.get(), self.frameNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_video_merge)
        t.setDaemon(True)
        t.start()


class Task(object):
    """任务对象类, 用于搭配VideoCutFrame使用"""
    def __init__(self, tid, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag=False,
                 original_mtime_flag=False):
        super().__init__()
        self.tid = tid  # 任务id
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
        self.dst_dir = None  # 视频导出地址
        self.log_path = os.path.join(settings.LOG_DIR, "videoCutLog.txt")  # 日志地址
        self.task_list = []  # 任务列表
        self.has_running_task_thread = False  # 是否已有正在进行的监听任务子线程
        self.task_status_dict = {0: "进行中", 1: "已完成", 2: "错误"}  # 状态码
        self.task_status_color_dict = {0: "blue", 1: "green", 2: "red"}  # 状态码对应颜色
        self.sub_start_time_h = tk.StringVar()  # 获取开始剪切时间 小时
        self.sub_start_time_m = tk.StringVar()  # 获取开始剪切时间 分钟
        self.sub_start_time_s = tk.StringVar()  # 获取开始剪切时间 秒
        self.sub_stop_time_h = tk.StringVar()  # 获取剪切结束时间
        self.sub_stop_time_m = tk.StringVar()  # 获取剪切结束时间
        self.sub_stop_time_s = tk.StringVar()  # 获取剪切结束时间
        self.time_inputs = [self.sub_start_time_h,
                            self.sub_start_time_m,
                            self.sub_start_time_s,
                            self.sub_stop_time_h,
                            self.sub_stop_time_m,
                            self.sub_stop_time_s]  # 储存时间输入tk变量
        self.frameNum = tk.StringVar()  # 视频帧率
        self.file_type = tk.StringVar()  # 视频格式
        self.file_type.set('mp4')
        self.invoke_fps_flag = tk.BooleanVar()  # 是否激活帧率输入框
        self.invoke_type_flag = tk.BooleanVar()  # 是否激活视频格式输入框
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.clear_time_input_flag = tk.BooleanVar()  # 是否清空时间输入框内容
        self.del_audio_flag = tk.BooleanVar()  # 是否去除视频中的音频  True输出视频无声音
        self.tid = 0  # 任务id计数
        # self.src_dir = tk.StringVar()
        # self.dst_dir = tk.StringVar()
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.sort_flag = tk.BooleanVar()  # 任务显示升序排列 True 升序 False降序排列
        self.createPage()
        self.getLogger()  # 获取日志对象
        # self.run()  # 启动一个子线程用来监听并执行self.task_list 任务列表中的任务

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
        fh = logging.FileHandler(logfile, mode='a', encoding='utf-8')  # open的打开模式这里可以进行参考
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

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir = None
        if self.clear_time_input_flag.get() is True:
            self.clear_time_input()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def selectPath(self):
        self.src_dir.set(askopenfilename())
        self.dst_dir = None
        if self.clear_time_input_flag.get() is True:
            self.clear_time_input()

    def createPage(self):
        """页面布局"""
        self.l_title["text"] = "视频截取"
        ttk.Label(self.f_input, text='源视频:').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=100).grid(row=0, column=1)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=2)
        # ttk.Label(self.f_input, text='导出至: ').grid(row=1, stick=tk.W, pady=10)
        # ttk.Entry(self.f_input, textvariable=self.dst_dir, width=100).grid(row=1, column=1)
        # ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, stick=tk.EW)
        ttk.Checkbutton(self.f_input_option, text="修改格式", variable=self.invoke_type_flag, onvalue=True,
                        offvalue=False, command=self.invoke_type).grid(row=0, column=0, stick=tk.W)
        self.e_type = ttk.Entry(self.f_input_option, textvariable=self.file_type, width=10, state=tk.DISABLED)
        self.e_type.grid(row=0, column=1, stick=tk.W, padx=5)
        ttk.Checkbutton(self.f_input_option, text="修改帧率", variable=self.invoke_fps_flag, onvalue=True,
                        offvalue=False, command=self.invoke_fps).grid(row=0, column=2, sticky=tk.EW, padx=5)
        self.e_fps = ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=8, state=tk.DISABLED)  # 视频帧率输入框
        self.e_fps.grid(row=0, column=3, stick=tk.W)
        self.frameNum.set("")  # 设置默认值
        ttk.Checkbutton(self.f_input_option, text="继承原修改时间", variable=self.original_mtime_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=4, sticky=tk.EW, padx=5)
        self.original_mtime_flag.set(False)  # 设置默认选中否
        ttk.Checkbutton(self.f_input_option, text="清空时间输入框内容", variable=self.clear_time_input_flag, onvalue=True,
                        offvalue=False, command=self.clear_time_input).grid(row=0, column=5, sticky=tk.EW, padx=5)
        self.clear_time_input_flag.set(True)  # 设置默认选中
        ttk.Checkbutton(self.f_input_option, text="去除音频", variable=self.del_audio_flag, onvalue=True,
                        offvalue=False, command=self.del_audio_flag).grid(row=0, column=6, sticky=tk.EW, padx=5)
        self.del_audio_flag.set(False)
        ttk.Label(self.f_input_option, text='任务排序： ').grid(row=0, column=7, stick=tk.W)
        ttk.Radiobutton(self.f_input_option, text='升序', variable=self.sort_flag, value=True, command=self.show_tasks).grid(row=0, column=8, sticky=tk.EW)
        ttk.Radiobutton(self.f_input_option, text='降序', variable=self.sort_flag, value=False, command=self.show_tasks).grid(row=0, column=9, sticky=tk.EW)
        self.sort_flag.set(False)
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
        # ttk.Label(self.f_time_option, text='', width=20).grid(row=1, column=12)  # 占位，无意义
        ttk.Button(self.f_input, text="查看日志", command=self.showLog).grid(row=3, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="添加任务", command=self.create_task).grid(row=3, column=2, stick=tk.E)
        self.l_task_state = ttk.Label(self.f_state, text="当前任务：", font=('微软雅黑', 16))
        self.l_task_state.pack()
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=2, columnspan=2, sticky='WE')
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def invoke_type(self):
        """激活视频格式输入框"""
        if self.invoke_type_flag.get():
            self.e_type.config(state=tk.NORMAL)
        else:
            self.file_type.set('mp4')
            self.e_type.config(state=tk.DISABLED)

    def invoke_fps(self):
        """激活帧率输入框"""
        if self.invoke_fps_flag.get():
            self.e_fps.config(state=tk.NORMAL)
        else:
            self.frameNum.set('')
            self.e_fps.config(state=tk.DISABLED)

    def clear_time_input(self):
        """清除时间输入框内容"""
        for item in self.time_inputs:
            item.set('')

    def showLog(self):
        """查看日志"""
        if self.log_path:
            webbrowser.open(self.log_path)

    def create_task(self):
        """创建任务"""
        if not os.path.exists(self.ffmpeg_path):
            mBox.showerror('缺失ffmpeg！', '程序缺失ffmpeg.exe！')
            return
        src_dir = self.check_path(self.src_dir.get())
        fps = get_int_value(self.frameNum.get().strip(), None)  # 帧率
        video_type = re.sub(r'^\.+', '', self.file_type.get().strip())  # 去除'.mp4' 最左边'.'
        original_mtime_flag = self.original_mtime_flag.get()  # 继承原文件修改时间信息
        continue_flag = False
        # 获取截取时间段
        sub_start_time_h = self.sub_start_time_h.get().strip()  # 获取开始剪切时间
        sub_start_time_m = self.sub_start_time_m.get().strip()  # 获取开始剪切时间
        sub_start_time_s = self.sub_start_time_s.get().strip()  # 获取开始剪切时间
        sub_stop_time_h = self.sub_stop_time_h.get().strip()  # 获取剪切的结束时间
        sub_stop_time_m = self.sub_stop_time_m.get().strip()  # 获取剪切的结束时间
        sub_stop_time_s = self.sub_stop_time_s.get().strip()  # 获取剪切的结束时间
        sub_start_time_h = get_int_value(sub_start_time_h, 0)  # 获取开始剪切时间
        sub_start_time_m = get_int_value(sub_start_time_m, 0)  # 获取开始剪切时间
        sub_start_time_s = get_float_value(sub_start_time_s, 0)  # 获取开始剪切时间
        sub_stop_time_h = get_int_value(sub_stop_time_h, 0)  # 获取剪切的结束时间
        sub_stop_time_m = get_int_value(sub_stop_time_m, 0)  # 获取剪切的结束时间
        sub_stop_time_s = get_float_value(sub_stop_time_s, 0)  # 获取剪切的结束时间
        startPoint = sub_start_time_h * 3600 + sub_start_time_m * 60 + sub_start_time_s
        endPoint = sub_stop_time_h * 3600 + sub_stop_time_m * 60 + sub_stop_time_s
        try:
            if os.path.isfile(src_dir):  # 操作单个视频文件
                pathIn = src_dir
                file_name = os.path.basename(pathIn)
                self.dst_dir = os.path.join(os.path.dirname(pathIn), "videoCut")
                dst_name = "%s_(%ss_to_%ss).%s" % (file_name, startPoint, endPoint, video_type)
                pathOut = os.path.join(self.dst_dir, dst_name)
                self.do_create_task(pathIn, pathOut, startPoint, endPoint, fps, continue_flag, original_mtime_flag)
            else:  # 操作目录
                for root, dirs, files in os.walk(src_dir):
                    for file in files:
                        pathIn = os.path.join(root, file)
                        self.dst_dir = os.path.abspath(src_dir) + "[videoCut]"
                        dst_name = "%s_(%ss_to_%ss).%s" % (os.path.basename(pathIn), startPoint, endPoint, video_type)
                        pathOut = os.path.join(self.dst_dir, dst_name)
                        self.do_create_task(pathIn, pathOut, startPoint, endPoint, fps, continue_flag, original_mtime_flag)
            mBox.showinfo("ok", "创建任务成功！")
        except Exception as e:
            self.dst_dir = None
            mBox.showerror("错误！", '%s' % e)
            return

    def do_create_task(self, pathIn, pathOut, startPoint, endPoint, fps, continue_flag, original_mtime_flag):
        """实际创建任务的函数"""
        if pathIn is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if pathIn == pathOut:
            mBox.showwarning("警告", "源路径与目标路径一致，有数据混乱风险！请重新规划路径！")
            return
        video_type = self.file_type.get().strip()
        video_type = re.sub(r'^\.+', '', video_type)
        # 获取视频信息
        duration = 0
        videoInfo = get_video_length(self.ffmpeg_path, pathIn)  # 视频信息
        # print(videoInfo)
        if videoInfo:
            duration = float(videoInfo.get('total'))  # 时长 秒  ,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
        if endPoint <= 0:  # 结束时间点为0或者负数
            endPoint = duration + endPoint
        if startPoint < 0:
            startPoint = duration + startPoint
        dst_name = "%s_(%ss_to_%ss).%s" % (os.path.basename(pathIn), startPoint, endPoint, video_type)
        pathOut = os.path.join(os.path.dirname(pathOut), dst_name)
        sub_stop_time = millisecToAssFormat(endPoint)
        sub_start_time = millisecToAssFormat(startPoint)
        # 创建任务信息
        self.tid += 1
        task = Task(self.tid, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
        if self.clear_time_input_flag.get():
            self.clear_time_input()
        msg = "【新增任务】 裁剪 %s 第 %s 秒至第 %s 秒视频任务，保存视频名：%s" % (pathIn, sub_start_time, sub_stop_time, pathOut)
        print(msg)
        self.logger.info(msg)
        self.task_list.append(task)
        self.run()  # 判断self.has_running_task是否已有正在进行的监听任务子线程，若无则启动一个子线程用来监听并执行self.task_list 任务列表中的任务
        # self.show_tasks()  # 刷新任务列表状态
        self.l_task_state["text"] = "当前任务：(总共：%s)" % (len(self.task_list))  # 更新任务状态标签

    def show_tasks(self):
        """用于展示所有任务信息"""
        self.scr.delete(1.0, "end")
        done_count = 0  # 完成任务数
        todo_count = 0  # 等待中的任务数
        error_count = 0  # 错误的任务数
        task_list = self.task_list[:]
        if not self.sort_flag.get():  # 降序，反向排序
            task_list.reverse()
        total_count = len(task_list)  # 总任务数
        for task in task_list:
            tid = task.tid
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
            msg = "任务编号: %s\n" % tid
            msg += "PathIn: %s\n" % pathIn
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
        # ffmpeg.exe -ss 48 -to 244 -i pathIn -vcodec copy -acodec copy pathOut
        if fps:
            if self.del_audio_flag.get():  # 是否去除音频
                cmd_str = '"%s" -y -ss %s -to %s -i "%s" -an -r %s "%s"' % (self.ffmpeg_path, sub_start_time, sub_stop_time, pathIn, fps, pathOut)
            else:
                cmd_str = '"%s" -y -ss %s -to %s -i "%s" -r %s "%s"' % (self.ffmpeg_path, sub_start_time, sub_stop_time, pathIn, fps, pathOut)
        else:
            if self.del_audio_flag.get():  # 是否去除音频
                cmd_str = '"%s" -y -ss %s -to %s -i "%s" -an -vcodec copy -acodec copy "%s"' % (self.ffmpeg_path, sub_start_time, sub_stop_time, pathIn, pathOut)
            else:
                cmd_str = '"%s" -y -ss %s -to %s -i "%s" -vcodec copy -acodec copy "%s"' % (self.ffmpeg_path, sub_start_time, sub_stop_time, pathIn, pathOut)
        # cmd_str = '"%s" -y -ss %s -to %s -i "%s" -vcodec copy -acodec copy "%s"' % (self.ffmpeg_path, sub_start_time, sub_stop_time, pathIn, pathOut)
        # os.system(cmd_str)  # 直接os.system() 会不停弹出关闭cmd窗口
        # 用subprocess隐藏反复弹出的cmd窗口, 直接os.system() 会不停弹出关闭cmd窗口
        subprocess.call(cmd_str, shell=True)
        if not os.path.exists(pathOut):
            raise Exception('视频裁剪失败！')
        # 将裁剪后视频修改时间变更为源视频修改时间
        if original_mtime_flag is True:
            timestamp = os.path.getmtime(pathIn)
            os.utime(pathOut, (timestamp, timestamp))
        msg = "【剪辑完成】 裁剪 %s 第 %s 秒至第 %s 秒视频完成!" % (pathIn, sub_start_time, sub_stop_time)
        print(msg)
        msg += "总用时%.3fs" % (time.time() - start_time)
        self.logger.info(msg)
        # mBox.showinfo('完成！', msg)

    @deal_running_task_arg2('视频裁剪')
    def run_task(self):
        """循环检测并执行任务列表里的任务"""
        end_flag = False  # 是否退出本子线程，任务列表中的任务都已完成时退出本子线程
        while True:
            if len(self.task_list):
                for task in self.task_list:
                    if not (task.status == 0):  # 已完成任务
                        end_flag = True
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
                        msg = "裁剪 %s 第 %s 秒至第 %s 秒视频出错!" % (pathIn, sub_start_time, sub_stop_time)
                        msg += " 错误：%s" % e
                        self.logger.error(msg)
                    finally:
                        self.show_tasks()  # 刷新任务列表状态
                    # time.sleep(5)
                    # print('\n\n\n\n\nlen(self.task_list):{}\n\n\n\n\n'.format(len(self.task_list)))
                # time.sleep(3)  # 防止不停刷新页面浪费程序资源
                if end_flag is True:
                    self.has_running_task_thread = False
                    print('视频裁剪子线程已结束！！！')
                    break

    def run(self):
        """创建子进程实时监听任务信息，并执行任务"""
        if self.has_running_task_thread is False:
            self.has_running_task_thread = True
            t = threading.Thread(target=self.run_task)
            t.setDaemon(True)
            t.start()


class TimestampFrame(BaseFrame):  # 继承Frame类
    """获取时间戳"""
    def __init__(self, master=None):
        super().__init__(master)
        self.input_time = tk.StringVar()
        self.input_timestamp = tk.StringVar()
        self.modify_mode = tk.IntVar()  # 修改文件时间方式 1 os.utime 2.win32file
        self.change_file_ctime_flag = tk.BooleanVar()  # 修改文件创建时间  True 是  False 否
        self.change_file_mtime_flag = tk.BooleanVar()  # 修改文件修改时间  True 是  False 否
        self.change_file_atime_flag = tk.BooleanVar()  # 修改文件访问时间  True 是  False 否
        self.chg_photo_flag = tk.BooleanVar()  # True 修改照片文件时间为拍摄时间
        self.chg_bat_flag = tk.BooleanVar()  # True 批量操作
        self.chg_files = []  # 要批量操作的文件
        self.chg_dir_flag = tk.BooleanVar()  # True 递归操作文件夹下子文件
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "时间戳操作"
        self.f_input0 = ttk.Frame(self.f_input)
        self.f_input0.grid(row=0, columnspan=4, stick=tk.EW)
        self.f_input1 = ttk.Frame(self.f_input)
        self.f_input1.grid(row=1, columnspan=4, stick=tk.EW)
        self.f_input2 = ttk.Frame(self.f_input)
        self.f_input2.grid(row=2, columnspan=4, stick=tk.EW)
        ttk.Label(self.f_input0, text="文件路径: ").grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input0, textvariable=self.src_dir, width=90).grid(row=0, column=1, stick=tk.EW)
        ttk.Button(self.f_input0, text="浏览", command=self.selectPath).grid(row=0, column=2, stick=tk.EW)
        ttk.Label(self.f_input1, text="输入时间: ").grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input1, textvariable=self.input_time, width=30, validate='focusout', validatecommand=self.time_to_timestamp).grid(row=1, column=1, stick=tk.E)
        ttk.Label(self.f_input1, text="输入时间戳: ").grid(row=1, column=2, stick=tk.W, padx=5)
        ttk.Entry(self.f_input1, textvariable=self.input_timestamp, width=30, validate="focusout", validatecommand=self.timestamp_to_time).grid(row=1, column=3, columnspan=2,stick=tk.E)
        ttk.Label(self.f_input2, text="修改文件: ").grid(row=0, stick=tk.W)
        self.btn_chk_ctime = ttk.Checkbutton(self.f_input2, text="创建时间", variable=self.change_file_ctime_flag, onvalue=True, offvalue=False)
        self.btn_chk_ctime.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.change_file_ctime_flag.set(True)  # 设置默认选中是
        ttk.Checkbutton(self.f_input2, text="修改时间", variable=self.change_file_mtime_flag, onvalue=True, offvalue=False).grid(row=0, column=2, sticky=tk.W, padx=5)
        self.change_file_mtime_flag.set(True)  # 设置默认选中是
        ttk.Checkbutton(self.f_input2, text="访问时间", variable=self.change_file_atime_flag, onvalue=True, offvalue=False).grid(row=0, column=3, sticky=tk.W, padx=5)
        self.change_file_atime_flag.set(True)  # 设置默认选中是
        ttk.Label(self.f_input2, text="方式: ").grid(row=0, column=4, stick=tk.W, padx=5)
        ttk.Radiobutton(self.f_input2, text="os.utime", variable=self.modify_mode, value=1, command=self.invoke_timecheckbtn).grid(row=0, column=5)
        ttk.Radiobutton(self.f_input2, text="win32file", variable=self.modify_mode, value=2, command=self.invoke_timecheckbtn).grid(row=0, column=6)
        self.modify_mode.set(2)
        ttk.Checkbutton(self.f_input2, text="批量操作", variable=self.chg_bat_flag, onvalue=True, offvalue=False).grid(row=0, column=7, sticky=tk.W)
        self.chg_bat_flag.set(False)  # 设置默认选中
        ttk.Checkbutton(self.f_input2, text="递归操作", variable=self.chg_dir_flag, onvalue=True, offvalue=False).grid(row=0, column=8, sticky=tk.W)
        self.chg_dir_flag.set(False)  # 设置默认选中
        ttk.Checkbutton(self.f_input2, text="修改照片时间为拍摄时间", variable=self.chg_photo_flag, onvalue=True, offvalue=False).grid(row=0, column=9, sticky=tk.W)
        self.chg_photo_flag.set(False)  # 设置默认选中
        ttk.Button(self.f_option, text="获取当前时间", command=self.get_current_time).grid(row=1, pady=10)
        ttk.Button(self.f_option, text="查看文件时间戳", command=self.get_file_timestamp).grid(row=1, column=1, padx=5)
        ttk.Button(self.f_option, text="修改文件时间戳", command=self.change_file_timestamp).grid(row=1, column=2, pady=10)
        self.f_input_option = ttk.Frame(self.f_option)  # 选项容器
        self.f_input_option.grid(row=0, columnspan=5, stick=tk.EW)
        ttk.Label(self.f_content, text='结果: ').grid(row=0, stick=tk.W)
        scrolW = 110
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=1, sticky='WE', columnspan=5)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def selectPath(self):
        file_path = askopenfilename()
        self.src_dir.set(file_path)

    def invoke_timecheckbtn(self):
        """激活显示时间复选框"""
        if self.modify_mode.get() == 1:
            self.change_file_ctime_flag.set(False)
            self.btn_chk_ctime.config(state=tk.DISABLED)
        else:
            self.btn_chk_ctime.config(state=tk.NORMAL)
            self.change_file_ctime_flag.set(True)

    def get_current_time(self):
        self.input_time.set(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        self.input_timestamp.set(time.time())

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.scr.delete(1.0, 'end')
        for item in files:
            file_path = item.decode(settings.SYSTEM_CODE_TYPE)
            if self.chg_bat_flag.get():  # 批量操作记录文件列表
                self.chg_files.append(file_path)
            self.src_dir.set(file_path)
            self.do_get_file_timestamp(file_path)

    def get_file_timestamp(self):
        """获取文件时间戳"""
        file_path = self.src_dir.get()
        self.do_get_file_timestamp(file_path)

    def do_get_file_timestamp(self, file_path):
        """获取文件时间戳操作"""
        if self.chg_bat_flag.get() is False:  # 批量操作时不清屏
            self.scr.delete(1.0, 'end')
        if not os.path.exists(file_path):
            self.scr.insert('end', "您输入的路径：%s 不存在！" % file_path)
            return
        file_timestampc = os.path.getctime(file_path)
        file_timestampa = os.path.getatime(file_path)
        file_timestampm = os.path.getmtime(file_path)
        msg = "path：%s 的时间戳为\n" % file_path
        msg += "\t创建时间戳：%s\n" % file_timestampc
        msg += "\t修改时间戳：%s\n" % file_timestampm
        msg += "\t最后访问时间戳：%s\n" % file_timestampa
        msg += "\t创建本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampc))
        msg += "\t修改本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampm))
        msg += "\t最后访问本地时间为：%s\n" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_timestampa))
        # 如果是照片则尝试获取该照片的exif信息
        file_type = os.path.splitext(file_path)[-1]  # 文件扩展名
        # print('file_type: %s' % file_type)
        if file_type.lower() in settings.JPG_TYPE:
            res = Mytools.get_image_exif(file_path)  # 获取照片exif信息
            # print(res)
            gps_information = res['GPS_information']
            date_information = res['date_information']
            if gps_information:
                gps_lng = gps_information['GPSLongitude']  # 经度
                gps_lat = gps_information['GPSLatitude']  # 纬度
                msg += '\n\tGPS信息: 纬度:%s, 经度:%s' % (gps_lat, gps_lng)
            if date_information:
                msg += '\n\t拍摄时间:%s' % date_information
        self.scr.insert("end", msg + '\n\n')

    def do_change_file_timestamp(self, file_path):
        # 用于修改单个文件的时间戳
        # 获取修改时间的时间戳
        modify_mode = self.modify_mode.get()
        change_file_ctime_flag = self.change_file_ctime_flag.get()
        change_file_mtime_flag = self.change_file_mtime_flag.get()
        change_file_atime_flag = self.change_file_atime_flag.get()
        m_timestamp = float(self.input_timestamp.get())
        if not os.path.exists(file_path):
            self.scr.insert('end', "您输入的路径：%s 不存在！" % file_path)
            return
        old_ctime = os.path.getctime(file_path)
        old_mtime = os.path.getmtime(file_path)
        old_atime = os.path.getatime(file_path)
        new_ctime = m_timestamp if change_file_ctime_flag else old_ctime
        new_mtime = m_timestamp if change_file_mtime_flag else old_mtime
        new_atime = m_timestamp if change_file_atime_flag else old_atime
        if self.chg_photo_flag.get():
            # 如果是照片则尝试获取该照片的exif信息
            file_type = os.path.splitext(file_path)[-1]  # 文件扩展名
            if file_type.lower() in settings.JPG_TYPE:
                res = Mytools.get_photo_time(file_path)  # 获取照片exif信息
                date_information = res['photo_time']
                if date_information:
                    date_information = time.mktime(time.strptime(date_information, '%Y-%m-%d %H:%M:%S'))  # 转换为时间戳
                    new_ctime, new_mtime, new_atime = (date_information, date_information, date_information)
        # 修改文件时间戳
        if modify_mode == 1:
            os.utime(file_path, (m_timestamp, m_timestamp))
        else:
            # 改用win32api 修改时间  可以修改文件创建时间
            ModifyTimestamp.modifyFileTimeByTimestamp(file_path, new_ctime, new_mtime, new_atime)
        res = {'ctime': (old_ctime, new_ctime), 'mtime': (old_mtime, new_mtime), 'atime': (old_atime, new_atime)}
        return res

    def change_file_timestamp(self):
        """修改文件时间戳"""
        chg_bat_flag = self.chg_bat_flag.get()  # 是否批量操作
        if chg_bat_flag is False:  # 批量操作时不清屏
            self.scr.delete(1.0, 'end')
            tmp_paths = [self.src_dir.get(), ]
        else:
            # 获取文件路径
            tmp_paths = self.chg_files
        # 判断输入时间戳是否正常，不正确则置为当前时间
        try:
            float(self.input_timestamp.get())
        except Exception:
            mBox.showerror("输入有误！", "输入的时间戳有误，请检查！")
            return
        msg = ''
        # 递归操作时，会操作文件夹下所有文件
        if self.chg_dir_flag.get():
            file_paths = []
            for _path in tmp_paths:  # 获取所有子文件
                if os.path.isdir(_path):
                    for root, dirs, files in os.walk(_path):
                        for file in files:
                            file_paths.append(os.path.join(root, file))
        else:
            file_paths = tmp_paths
        for file_path in file_paths:
            res = self.do_change_file_timestamp(file_path)
            time_str_c_old = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res['ctime'][0]))
            time_str_a_old = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res['atime'][0]))
            time_str_m_old = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res['mtime'][0]))
            time_str_c_new = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res['ctime'][1]))
            time_str_a_new = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res['atime'][1]))
            time_str_m_new = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(res['mtime'][1]))
            # 显示文件时间戳信息
            msg += "文件：%s 的时间戳修改为\n\n" % file_path
            msg += "\t创建时间戳：\t %s    >>>    %s\n" % (res['ctime'][0], res['ctime'][1])
            msg += "\t修改时间戳：\t %s    >>>    %s\n" % (res['mtime'][0], res['mtime'][1])
            msg += "\t访问时间戳：\t %s    >>>    %s\n" % (res['atime'][0], res['atime'][1])
            msg += "\t创建 时间：\t %s    >>>    %s\n" % (time_str_c_old, time_str_c_new)
            msg += "\t修改 时间：\t %s    >>>    %s\n" % (time_str_m_old, time_str_m_new)
            msg += "\t访问 时间：\t %s    >>>    %s\n" % (time_str_a_old, time_str_a_new)
        if msg:
            self.scr.insert("end", msg)
            # 写出记录
            time_now_str = time.strftime("%Y%m%d%H%M%S", time.localtime())
            self.record_path = os.path.join(settings.RECORD_DIR, 'change_timestamp_record_%s.txt' % time_now_str)
            with open(self.record_path, 'a', encoding='utf-8') as f:
                f.write(msg+'\n')
            logger.operate_logger('【修改文件时间戳操作】  修改文件时间戳，时间戳修改记录到%s ' % self.record_path)

    def time_to_timestamp(self):
        """时间转换为时间戳"""
        self.scr.delete(1.0, 'end')
        input_time = self.input_time.get()
        input_time = Mytools.changeStrToTime(input_time)
        # print('input_time: %s' % input_time)
        if input_time:
            try:
                timestamp = time.mktime(time.strptime(input_time, '%Y-%m-%d %H:%M:%S'))
                msg = "时间：'%s' \n-->时间戳为: '%s'\n" % (input_time, timestamp)
                self.scr.insert("end", msg)
                self.input_timestamp.set(timestamp)
                return True
            except ValueError:
                mBox.showerror("错误", "时间格式输入错误！请使用标准格式(yyyy-mm-dd HH:MM:SS)输入！")
                return False
        else:
            mBox.showerror("错误", "请使用标准格式(yyyy-mm-dd HH:MM:SS)输入时间字符串！")
            return False

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
                self.input_time.set(get_time)
                return True
            except Exception:
                mBox.showerror("错误", "输入时间戳格式有误！须为纯数字或小数")
                return False
        else:
            mBox.showerror("错误", "输入时间戳格式有误！须为纯数字或小数")
            return False


class FindBadVideoFrame(BaseFrame):  # 继承Frame类
    """查找损坏视频文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()  # 模式 "基于filecmp模块", "自己实现的Mybackup,节省IO资源占用", "备份端目录变更同步"
        self.option = tk.StringVar()
        self.ffmpeg_path = tk.StringVar()  # ffmpeg程序所在目录
        # self.exeState = tk.StringVar()  # 用于动态更新程序执行任务状态
        # self.proState = tk.StringVar()  # 用于动态更新程序运行状态，running
        self.createPage()

    def selectPath1(self):
        self.src_dir.set(askdirectory())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def selectPath2(self):
        self.dst_dir.set(askdirectory())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    def selectPath3(self):
        self.ffmpeg_path.set(askopenfilename())
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.record_path = None
        self.dst_dir.set("")
        self.pb1["value"] = 0
        self.btn_show_result.config(state=tk.DISABLED)
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            save_path = dir_path + '_[bad]'
            if not os.path.exists(save_path):
                self.dst_dir.set(save_path)

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @deal_running_task_arg('查找损坏的视频')
    def findBadVideos(self):
        """找出损坏的视频文件"""
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), create_flag=True)
        ffmpeg_path = Mytools.check_path(self.ffmpeg_path.get())
        if src_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
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
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", "%s  开始遍历文件目录...\n" % time_str)
        self.exeStateLabel["text"] = "遍历文件目录..."
        self.proStateLabel["text"] = "running..."
        video_list = []  # 文件列表
        for root, dirs, files in os.walk(src_path):
            for file in files:
                file_path = os.path.join(root, file)
                # if not file.endswith(".mp4"):
                #     continue
                # if file.count(" "):
                #     new_file_path = os.path.join(root, file.replace(" ", "_"))
                #     os.rename(file_path, new_file_path)
                #     file_path = new_file_path
                ext_name = os.path.splitext(file)[-1]  # 文件后缀名
                if ext_name.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.ts', '.rmvb', '.flv', '']:  # '' 用于匹配无后缀名文件
                    video_list.append(file_path)
        # print(len(video_list))

        # 设置进度条
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", "\n%s  遍历目录完成！\n" % time_str)
        self.pb1["maximum"] = len(video_list)  # 总项目数

        # 调用命令快速校验视频文件
        # 拼接命令列表
        self.exeStateLabel["text"] = "校验视频文件..."
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", "\n%s  开始校验视频文件...\n" % time_str)
        # 运行ffmpeg命令检验视频文件
        for file_path in video_list:
            log_path = file_path+'.log'
            cmd_str = '"%s" -v error -i "%s" -f null - >"%s" 2>&1' % (ffmpeg_path, file_path, log_path)
            subprocess.call(cmd_str, shell=True)   # 用subprocess隐藏反复弹出的cmd窗口, 直接os.system() 会不停弹出关闭cmd窗口
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
        time_str = Mytools.get_time_now().get('time_str')
        self.scr.insert("end", "\n\n%s  %s\n" % (time_str, msg))
        self.scr.see(tk.END)
        self.btn_show_result.config(state=tk.NORMAL)

    def run(self):
        """主进程主函数"""
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""
        self.scr.delete(1.0, 'end')  # 清空文本区
        src_path = Mytools.check_path(self.src_dir.get())
        dst_path = Mytools.check_path(self.dst_dir.get(), True)
        ffmpeg_path = Mytools.check_path(self.ffmpeg_path.get())
        if src_path and dst_path and ffmpeg_path:
            t = threading.Thread(target=self.findBadVideos)
            t.setDaemon(True)
            t.start()
        else:
            mBox.showerror("路径不存在！", "输入的路径不存在！请检查！")
            return

    def createPage(self):
        self.l_title["text"] = "找出损坏/不完整的视频文件"
        ttk.Label(self.f_input, text='视频目录路径: ').grid(row=0, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir, width=95).grid(row=0, column=1, stick=tk.E)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='损坏视频导出路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir, width=95).grid(row=1, column=1, stick=tk.E)
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
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky='WE', columnspan=6)
        self.btn_show_result = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show_result.grid(row=0, column=0, pady=10, sticky=tk.W)
        # self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        # self.btn_restore.grid(row=0, column=1, pady=10, sticky=tk.W)
        ttk.Label(self.f_bottom, text="", width=70).grid(row=0, column=3)
        ttk.Label(self.f_bottom, text='程序运行状态: ').grid(row=2, stick=tk.W, pady=10)
        self.exeStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序执行任务状态
        self.exeStateLabel.grid(row=2, column=1, columnspan=2, stick=tk.W, pady=10)
        self.proStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序总运行状态
        self.proStateLabel.grid(row=2, column=4, stick=tk.W, pady=10)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作


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
        self.FFMPEG_PATH = tk.StringVar()  # ffmpeg路径
        self.SAFE_DEL_LOCAL = tk.BooleanVar()  # 标记是否在文件所在分区创建safe_del文件夹，False 在程序目录下创建safe_del文件夹
        self.SAFE_FLAG = tk.BooleanVar()  # 标记执行文件删除操作时是否使用安全删除选项(安全删除选项会将被删除的文件剪切到safe_del目录下)
        self.SKIP_FLAG = tk.BooleanVar()  # 标记执行文件复制或者粘贴操作时是否遇见同名同路径文件是否跳过选项(True跳过 False覆盖)
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
        self.SYSTEM_CODE_TYPE.set(settings.SYSTEM_CODE_TYPE)
        self.SAFE_DEL_LOCAL.set(settings.SAFE_DEL_LOCAL)
        self.SAFE_FLAG.set(settings.SAFE_FLAG)
        self.SKIP_FLAG.set(settings.SKIP_FLAG)
        self.FFMPEG_PATH.set(settings.FFMPEG_PATH)

    def open_path(self, pathObj):
        temp_path = pathObj.get()
        if os.path.exists(temp_path):
            webbrowser.open(temp_path)

    def open_path2(self, pathObj):
        temp_path = pathObj.get()
        temp_path = os.path.dirname(temp_path)
        if os.path.exists(temp_path):
            webbrowser.open(temp_path)

    def chmodElement(self):
        """用于设置Entry和Radiobutton只读和可读写状态"""
        elements = [self.e1, self.e2, self.e3, self.e4, self.e5, self.e6, self.e7, self.e8, self.r1, self.r2, self.r3, self.r4]
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
        ttk.Label(self, text='FFMPEG路径: ').grid(row=6, stick=tk.W, pady=10)
        self.e8 = ttk.Entry(self, textvariable=self.FFMPEG_PATH, width=80)
        self.e8.grid(row=6, column=1, columnspan=3, stick=tk.W)
        ttk.Button(self, text="查看", command=lambda: self.open_path2(self.FFMPEG_PATH)).grid(row=6, column=4)
        ttk.Label(self, text='保存删除文件备份的目录: ').grid(row=7, stick=tk.W, pady=10)
        self.e6 = ttk.Entry(self, textvariable=self.SAFE_DEL_DIR, width=15)
        self.e6.grid(row=7, column=1, stick=tk.W)
        ttk.Label(self, text='系统的编码格式: ').grid(row=8, column=0, stick=tk.W, pady=10)
        self.e7 = ttk.Entry(self, textvariable=self.SYSTEM_CODE_TYPE, width=15)
        self.e7.grid(row=8, column=1, stick=tk.W)
        self.f_option = ttk.Frame(self)  # 选项容器
        self.f_option.grid(row=9, columnspan=3, stick=tk.EW)
        self.r1 = ttk.Checkbutton(self.f_option, text="在文件所在分区创建safe_del文件夹", variable=self.SAFE_DEL_LOCAL, onvalue=True,offvalue=False)
        self.r1.grid(row=0, column=0, sticky=tk.W, padx=10)
        self.r2 = ttk.Checkbutton(self.f_option, text="使用安全删除", variable=self.SAFE_FLAG, onvalue=True,offvalue=False)
        self.r2.grid(row=0, column=1, sticky=tk.W, padx=10)
        ttk.Label(self.f_option, text='遇到路径重复的文件操作: ').grid(row=0, column=2, stick=tk.W, pady=10, padx=5)
        self.r3 = ttk.Radiobutton(self.f_option, text="跳过", variable=self.SKIP_FLAG, value=True)
        self.r3.grid(row=0, column=3, sticky=tk.W, padx=5)
        self.r4 = ttk.Radiobutton(self.f_option, text="覆盖", variable=self.SKIP_FLAG, value=False)
        self.r4.grid(row=0, column=4, sticky=tk.W, padx=5)
        ttk.Button(self, text="权限验证！", command=lambda: checkPassword(self)).grid(row=11, column=0, pady=20)
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
        settings.SKIP_FLAG = self.SKIP_FLAG.get()  # 设置默认选中是
        settings.FFMPEG_PATH = self.FFMPEG_PATH.get()
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
        ttk.Label(self, text='VERSION:  3.8.1.0').pack()
        link = tk.Label(self, text="GitHub:  https://github.com/codecyou/FileManager", fg="blue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/codecyou/FileManager"))
        ttk.Label(self, text='这是一个多功能的小程序，').pack()
        tk.Label(self, text='功能：', font=("微软雅黑", 18)).pack()
        ttk.Label(self, text='导出文件信息、查找重复文件、文件同步备份、还原文件、删除文件、清除空文件夹、搜索文件、拷贝目录层次结构、').pack()
        ttk.Label(self, text='计算文件hash值、比对文本文件内容、提取视频帧图像、计算图片相似度、查找相似视频、视频裁剪、视频合并、提取音频').pack()
        ttk.Label(self, text='批量重命名、时间戳转换、修改文件时间戳、获取图片文件EXIF信息（GPS信息、拍摄信息）').pack()
