import tkinter
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.messagebox import *
from tkinter import messagebox as mBox
from tkinter import scrolledtext
from natsort import natsorted
import traceback
import webbrowser
import os
import sys
import threading
import time
import shutil
import re
import os
import subprocess
import random
import hashlib
import windnd


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from conf import my_api, settings
from core import common_utils, image_utils, search_utils, syn_utils, video_utils
from core.logger import logger


mutex = threading.Lock()  # 创建互斥锁
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
                logger.error(traceback.format_exc())
                mBox.showerror("错误", "执行 《{}》 任务出错！详情请查看日志！".format(task_info))
            # 移除任务
            # 释放输入组件
            args[0].enable_all_elements()
            args[0].is_locked = False
            mutex.acquire()
            running_task.remove(task_info)
            mutex.release()
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
        return wrapped_func
    return deal_running_task


def dragged_locked(func):
    """程序执行任务中，锁定文件拖拽功能"""
    def wrapped_func(*args, **kwargs):
        if args[0].is_locked:  # 程序正在执行任务中，锁定文件拖拽功能
            logger.debug('文件拖拽功能锁定！')
            return
        func(*args, **kwargs)
    return wrapped_func


def log_error(func):
    """装饰器用于装饰各个模块页面的run方法来捕获异常"""
    def wrapped_func(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            mBox.showerror("错误", "程序运行出错! 详情请查看日志!")

    return wrapped_func


class BaseFrame(tk.Frame):
    """所有页面的基类"""
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.root.protocol('WM_DELETE_WINDOW', self.closeWindow)  # 绑定窗口关闭事件，防止计时器正在工作导致数据丢失
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.pre_record_path = None  # 保存上一次的记录文件路径，用于误点还原按钮后撤销还原操作
        self.lock_elements = []  # 记录程序运行时锁定的子组件
        self.is_locked = False  # 程序是否锁定，当前程序已有正在执行的相同任务，则锁定文件拖拽，即执行任务时锁定子组件同时锁定文件拖拽功能
        self.f_title = ttk.Frame(self)  # 页面标题
        self.f_input = ttk.Frame(self)  # 输入部分
        self.f_option = ttk.Frame(self)
        self.f_state = ttk.Frame(self)  # 进度条
        self.f_content = ttk.Frame(self)  # 显示结果
        self.f_bottom = ttk.Frame(self)  # 页面底部
        self.f_title.pack(fill=tk.X, expand=True)
        self.f_input.pack(fill=tk.X, expand=True)
        self.f_option.pack(fill=tk.X, expand=True)
        self.f_state.pack(fill=tk.X, expand=True)
        self.f_content.pack(fill=tk.BOTH, expand=True)
        self.f_bottom.pack(fill=tk.X, expand=True)

        self.f_input.grid_columnconfigure(1, weight=1)
        self.f_state.grid_columnconfigure(0, weight=1)
        self.f_content.grid_rowconfigure(0, weight=1)
        self.f_content.grid_columnconfigure(0, weight=1)
        # self.l_title = tk.Label(self.f_title, text='页面', font=('Arial', 12), height=2, bg='blue')
        self.l_title = tk.Label(self.f_title, text='页面', font=('Arial', 12))
        self.l_title.pack(fill=tk.X, expand=True)
        self.scr = scrolledtext.ScrolledText(self.f_content)
        self.btn_show = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)

        self.src_dir = tk.StringVar()  # 源目录
        self.dst_dir = tk.StringVar()  # 目标目录
        self.move_option = tk.StringVar()  # 移动文件的模式 copy 拷贝 move 移动
        self.move_option.set('move')
        self.is_complete = False  # 用来标记所有计算任务是否完成，以防止进度条子线程陷入死循环

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()  # 清空数据
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def clear(self):
        """清空相关输入和显示数据"""
        self.record_path = None
        self.dst_dir.set('')
        self.scr.delete(1.0, tk.END)

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
            msg += '\n是否退出?'
            ans = mBox.askyesno(title="Warning", message=msg)
            if not ans:
                # 选择否/no 不退出
                return
        # 退出程序
        self.root.destroy()

    def all_children(self, wid, finList):
        """递归获取所有子组件"""
        _list = wid.winfo_children()
        for element in _list:
            # logger.debug('{} is {}'.format(element, type(element)))
            if isinstance(element, tkinter.ttk.Label):
                # logger.debug('{} is label'.format(element))
                # .!exportframe.!frame2.!label is <class 'tkinter.ttk.Label'>
                continue
            # logger.debug('{} , type:{}, state:{}'.format(element, type(element), element.state()))
            # 结果： state: ('disabled',) state:('disabled', 'selected') state:('active', 'focus', 'hover') state:('readonly',)
            if 'disabled' in element.state():  # 原本锁定的组件元素我们就不去动它
                continue
            if isinstance(element, tkinter.ttk.Frame):
                self.all_children(element, finList)
            else:
                finList.append(element)

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        # elements = self.f_input.winfo_children()
        # logger.debug(elements)

        # 递归方式获取
        # logger.debug(len(self.lock_elements))
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        # logger.debug('锁定组件状态！')
        # logger.debug('len({}):{}'.format(len(self.lock_elements), self.lock_elements))
        for element in self.lock_elements:
            # element['state'] = tk.DISABLED
            element.config(state=tk.DISABLED)

    def enable_all_elements(self):
        '''用来释放所有锁定的输入组件'''
        # logger.debug(len(self.lock_elements))
        # logger.debug("解锁组件状态")
        for element in self.lock_elements:
            element.config(state=tk.NORMAL)
            if isinstance(element, tkinter.ttk.Combobox):  # 下拉框都设置只读
                element.config(state='readonly')

    def showFiles(self):
        """查看结果目录"""
        if self.dst_dir.get():
            webbrowser.open(self.dst_dir.get())

    @deal_running_task_arg('还原文件')
    def restoreFiles(self):
        """还原文件"""
        if self.record_path:
            res = common_utils.restore_file_by_record(self.record_path)
            restore_path = res.get('record_path')
            count = len(res.get('sucess_list'))
            time_str = common_utils.get_times_now().get('time_str')
            msg = "根据 %s,还原了 %s 个项目，还原文件信息记录到 %s" % (self.record_path, count, restore_path)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.info('【文件还原】  %s' % msg)
            self.pre_record_path = self.record_path  # 记录new_old_record路径方便撤销还原
            self.record_path = None  # 重置为None 以免影响后续数据
            self.btn_restore.config(state=tk.DISABLED)
            self.btn_undo_restore.config(state=tk.NORMAL)
            mBox.showinfo('任务完成', "还原文件完成!")
    
    @deal_running_task_arg('撤销还原')
    def undoRestoreFiles(self):
        """撤销还原文件"""
        if self.pre_record_path:
            move_option = False if (self.move_option.get() in ["拷贝", "copy"]) else True
            count = common_utils.undo_restore_file_by_record(self.pre_record_path, move_option)
            time_str = common_utils.get_times_now().get('time_str')
            msg = "根据 %s,重新移动了 %s 个文件" % (self.pre_record_path, count)
            self.scr.insert('end', '\n%s  %s\n' % (time_str, msg))
            self.scr.see(tk.END)
            logger.info('【撤销还原】  %s' % msg)
            self.pre_record_path = None  # 重置为None 以免影响后续数据
            self.btn_undo_restore.config(state=tk.DISABLED)
            # self.btn_restore.config(state=tk.NORMAL)
            mBox.showinfo('任务完成', "撤销还原文件完成!")

    def show_rate_calc(self, cal_res, total_count):
        """
        显示计算图片phash进度或者操作文件进度进度条
        :param cal_res: 记录计算计数的变量，由于子线程和址传递的关系故该变量格式为{'count':0}
        :param total_count: 总文件数
        """
        self.pb1["maximum"] = total_count
        self.pb1["value"] = 0
        while True:
            # 如果检测到所有计算任务已完成则退出
            if self.is_complete:
                self.pb1["value"] = self.pb1["maximum"] if self.pb1["maximum"] > 0 else 1
                break
            finished_num = cal_res['count']
            # print("now finish %s" % finished_num)
            self.pb1["value"] = finished_num
            print('finished_num: {}, total_count: {}'.format(finished_num, total_count))
            if finished_num >= total_count:  # 通过判断计算次数
                self.pb1["value"] = total_count
                break
            time.sleep(0.05)
        print('显示计算进度条子线程退出！')
    
    def show_rate_sim(self, img2phash_dict):
        """
        显示计算图片相似度的进度条
        :param img2phash_dict: 样品图片文件和phash值对应信息,数据格式{img:phash,...}
        """
        total_count = len(img2phash_dict)
        self.pb1["maximum"] = total_count
        self.pb1['value'] = 0
        while True:
            # 如果检测到所有计算任务已完成则退出
            if self.is_complete:
                self.pb1["value"] = self.pb1["maximum"] if self.pb1["maximum"] > 0 else 1
                break
            print(total_count)
            print(len(img2phash_dict))
            finished_num = total_count - len(img2phash_dict)
            print("now finish %s" % finished_num)
            self.pb1["value"] = finished_num
            if finished_num >= total_count:
                print('total_count:{}'.format(total_count))
                print(len(img2phash_dict))
                self.pb1["value"] = total_count
                break
            time.sleep(0.1)
        print('显示计算相似度进度条子线程退出！')

    @staticmethod
    def check_paths(*tkObjs):
        """用于检查多个输入路径是否存在,并且这些路径是否重复,在此过程中会将输入路径设置为标准绝对路径格式
        :param tkObjs:  路径输入框 tk变量集合, 第一个值为源目录路径
        """
        paths = set()
        for tkObj in tkObjs:
            create_flag = False if (tkObj == tkObjs[0]) else True
            abs_path = common_utils.check_path(tkObj.get(), create_flag)
            if abs_path:
                tkObj.set(abs_path)
                paths.add(abs_path)
            else:
                mBox.showerror("错误", "路径: %s 不存在! 请检查!" % tkObj.get())
                return False
        if len(paths) != len(tkObjs):
            mBox.showwarning("警告", "源路径与目标路径一致,有数据混乱风险! 请重新规划路径!")
            return False
        return True

    @staticmethod
    def check_path_exists(tkObj, makeFlag=False):
        """用于检查单个输入路径是否存在,在此过程中会将输入路径设置为标准绝对路径格式"""
        abs_path = common_utils.check_path(tkObj.get(), makeFlag)
        if abs_path:
            tkObj.set(abs_path)
            return True
        else:
            mBox.showerror("错误", "路径: %s 不存在! 请检查!" % tkObj.get())
            return False
        
    @staticmethod
    def check_paths_same(*tkObjs):
        """用于检查多个输入路径是否重复,在此过程中会将输入路径设置为标准绝对路径格式"""
        paths = set()
        for tkObj in tkObjs:
            abs_path = os.path.abspath(tkObj.get())
            print(abs_path)
            if abs_path:
                tkObj.set(abs_path)
                paths.add(abs_path)
        if len(paths) != len(tkObjs):
            mBox.showwarning("警告", "源路径与目标路径一致,有数据混乱风险! 请重新规划路径!")
            return False
        return True


class FindSameFrame(BaseFrame):
    """查找重复文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.record_path = None  # 导出的记录文件路径
        self.mode_dict = {
            "同名": "name",
            "相同大小": "size",
            "相同修改时间": "mtime",
            "同名且大小相同": "name_size",
            "同名且修改时间相同": "name_mtime",
            "大小相同且修改时间相同": "size_mtime",
            "同名且大小相同且修改时间相同": "name_size_mtime",
            "视频时长相同": "v_duration",
            "视频分辨率相同": "v_resolution",
            "图片分辨率相同": "i_resolution"
        }
        self.optionDict = {"拷贝": "copy", "剪切": "move"}  # 文件操作模式
        self.mode = tk.StringVar()  # 查询模式
        self.move_option = tk.StringVar()  # 移动文件的模式
        self.filter_flag = tk.BooleanVar()  # 是否启用过滤排除功能True 启用
        self.filter_mode = tk.IntVar()  # 过滤模式 1 排除 2 选中
        self.filter_str = tk.StringVar()  # 过滤内容
        self.move_option.set("拷贝")  # 设置默认值
        self.filter_flag.set(False)
        self.filter_mode.set(2)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "查找重复文件"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='查询模式: ').grid(row=0, pady=10)
        modeChosen = ttk.Combobox(self.f_input_option, width=30, textvariable=self.mode)
        modeChosen['values'] = list(self.mode_dict.keys())
        modeChosen.grid(row=0, column=1)
        modeChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        modeChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_input_option, text='  操作模式: ').grid(row=0, column=2, pady=10)
        col = 3
        for item in self.optionDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.move_option, value=item).grid(column=col, row=0)
            col += 1
        # 过滤功能
        self.f_filter = ttk.Frame(self.f_input)  # 容器
        self.f_filter.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Checkbutton(self.f_filter, text="过滤：", variable=self.filter_flag, onvalue=True, offvalue=False,
                        command=self.invoke_filter_input).grid(row=0)
        self.f_filter_elements = ttk.Frame(self.f_filter)  # 容器
        self.f_filter_elements.grid(row=0, column=1, columnspan=3, sticky=tk.EW)
        ttk.Radiobutton(self.f_filter_elements, text="排除", variable=self.filter_mode, value=1, state=tk.DISABLED).grid(column=1, row=0)
        ttk.Radiobutton(self.f_filter_elements, text="选中", variable=self.filter_mode, value=2, state=tk.DISABLED).grid(column=2, row=0)
        ttk.Entry(self.f_filter_elements, textvariable=self.filter_str, width=55, state=tk.DISABLED).grid(row=0, column=3, padx=5)
        ttk.Label(self.f_filter, text="(后缀名用逗号','分隔)", state=tk.DISABLED).grid(row=0, column=4)
        ttk.Button(self.f_input, text="执行", command=self.deal_search).grid(row=3, column=4)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH,  wrap=tk.WORD)
        self.scr.grid(row=0, column=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1)
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[same]'
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

    def clear(self):
        """清空信息"""
        self.scr.delete(1.0, 'end')
        self.record_path = None
        self.pre_record_path = None
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_undo_restore.config(state=tk.DISABLED)

    @deal_running_task_arg('查找重复文件')
    def do_search(self):
        """搜索重复文件"""
        search_dir = self.src_dir.get()
        save_dir = self.dst_dir.get()
        search_mode = self.mode_dict[self.mode.get()]
        deal_mode = self.optionDict[self.move_option.get()]
        filter_flag = self.filter_flag.get()
        filter_str = self.filter_str.get()
        filter_mode = self.filter_mode.get()
        self.pb1["value"] = 0
        self.pb1["maximum"] = 3  # 总项目数 1/3为遍历文件完成， 2/3 为比对完成， 3/3为操作文件完成
        logger.debug("filter_flag: %s, filter_str: %s" % (filter_flag, filter_str))
        self.scr.insert("end", "%s  正在遍历文件目录...\n" % common_utils.get_times_now().get('time_str'))
        self.pb1["value"] = 1  # 模拟遍历完成
        file_dict, count = search_utils.find_same(search_dir, search_mode, filter_flag, filter_str, filter_mode)
        if len(file_dict):  # 如果有相同文件再进行后续动作
            time_str = common_utils.get_times_now().get('time_str')
            self.scr.insert("end", "\n%s  检索%s\n\t共发现 “%s” 的文件 %s 个!\n" % (time_str, search_dir, self.mode.get(), len(file_dict)))
            self.pb1["value"] = 2  # 比对完成
            self.scr.insert("end", "\t正在将 “%s” 的文件由 %s %s 到 %s !\n" % (self.mode.get(), search_dir, self.move_option.get(), save_dir))
            self.record_path = os.path.join(settings.RECORD_DIR, 'new_old_record_%s.txt' % common_utils.get_times_now().get('time_num_str'))
            # 组装new_old_record
            num = 0  # 用于记录重复组编号
            new_old_record = {}  # 用于保存新旧文件名信息，格式为"{new_file: old_file, }"
            for info in file_dict:  # 用于储存相同文件,格式"{"name"或者"size": [file_path1,file_path1,],...}"
                for item in file_dict[info]:
                    new_file = os.path.basename(common_utils.make_new_path(item, search_dir, save_dir, name_simple=True))
                    new_file = 'S%s__%s' % (num, new_file)
                    new_file = os.path.join(save_dir, new_file)
                    new_old_record[new_file] = item
                num += 1  # 编号+1

            # 操作文件
            error_count = 0  # 用于记录操作失败数
            for new_file in new_old_record:
                old_file = new_old_record[new_file]
                # logger.debug(old_file)
                try:
                    if deal_mode == "copy":
                        common_utils.copy_file(old_file, new_file)
                    else:
                        common_utils.move_file(old_file, new_file)
                except Exception as e:
                    error_count += 1
                    self.scr.insert("end", "error[%s] 程序操作文件出错：  %s\n%s  ->  %s\n\n" % (error_count, e, old_file, new_file))
            self.btn_restore.config(state=tk.NORMAL)
            # 将新旧文件名记录写出到文件
            common_utils.export_new_old_record(new_old_record, self.record_path)  # 将文件剪切前后文件信息导出到new_old_record
            print_msg = "%s 中发现 %s 个 “%s” 的文件,已 %s 到 %s,\n新旧文件名记录到 %s" % (
                search_dir, count, self.mode.get(), self.move_option.get(), save_dir, self.record_path)
            log_msg = "【文件查重】  %s 中发现 %s 个 %s 的文件,已 %s 到 %s,新旧文件名记录到 %s" % (
                search_dir, count, self.mode.get(), self.move_option.get(), save_dir, self.record_path)
        else:
            print_msg = "%s 中未发现 %s 的文件！" % (search_dir, self.mode.get())
            log_msg = '【文件查重】  %s' % print_msg
        time_str = common_utils.get_times_now().get('time_str')
        logger.info(log_msg)  # 记录到日志
        self.scr.insert("end", "\n\n%s  %s\n" % (time_str, print_msg))
        self.scr.see(tk.END)
        self.pb1["value"] = 3  # 操作文件完成
        self.btn_show.config(state=tk.NORMAL)
        mBox.showinfo('任务完成', "查找相同文件完成!")

    def deal_search(self):
        """调度搜索重复文件方法"""
        self.clear()
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        t = threading.Thread(target=self.do_search)
        t.daemon = True
        t.start()


class FindSameByHashFrame(BaseFrame):
    """根据文件hash值去重"""
    def __init__(self, master=None):
        super().__init__(master)
        self.optionDict = {"拷贝": "copy", "剪切": "move"}
        self.mode = tk.StringVar()
        self.move_option = tk.StringVar()  # 移动文件的模式
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.pre_record_path = None  # 保存上一次的记录文件路径，用于误点还原按钮后撤销还原操作
        self.same_record_path = None  # 记录重复文件的same_record 路径
        self.failed_record_path = None  # 记录操作文件失败的failed_record 路径
        self.sort_reverse = tk.BooleanVar()  # 记录排序方式 True 倒序 False正序
        self.sort_mode = tk.BooleanVar()  # 是否根据修改时间排序 True 根据修改时间排序 False 不操作
        self.move_all_flag = tk.BooleanVar()  # 是否导出所有hash相同的文件 True 导出所有 False 仅导出重复的
        self.sort_mode.set(False)  # 默认按修改时间正序排序
        self.move_option.set("拷贝")  # 设置默认值
        self.move_all_flag.set(False)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "查找重复文件(hash值)"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=1, column=0, pady=10)
        ttk.Checkbutton(self.f_input_option, text="根据修改时间排序", variable=self.sort_mode, onvalue=True, offvalue=False, command=self.invoke_time_sort).grid(column=1, row=1)
        self.f_sort_elements = ttk.Frame(self.f_input_option)  # 排序单选框区域
        self.f_sort_elements.grid(row=1, column=2, columnspan=2, sticky=tk.EW)
        ttk.Radiobutton(self.f_sort_elements, text="正序", variable=self.sort_reverse, value=False, state=tk.DISABLED).grid(row=0, column=0)
        ttk.Radiobutton(self.f_sort_elements, text="倒序", variable=self.sort_reverse, value=True, state=tk.DISABLED).grid(row=0, column=1)
        ttk.Label(self.f_input_option, text="文件操作：").grid(row=1, column=4)
        col = 5
        for item in self.optionDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.move_option, value=item).grid(column=col, row=1)
            col += 1
        ttk.Checkbutton(self.f_input_option, text="导出所有hash值相同的文件", variable=self.move_all_flag, onvalue=True, offvalue=False).grid(column=7, row=1, padx=5)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=4, sticky=tk.E)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=8, column=0, pady=10)
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
        self.same_record_path = None
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_undo_restore.config(state=tk.DISABLED)
        self.btn_showSameRecord.config(state=tk.DISABLED)
        self.btn_showFailedRecord.config(state=tk.DISABLED)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[sameHash]'
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

    def showSameRecord(self):
        """查看相同文件记录"""
        if self.same_record_path:
            webbrowser.open(self.same_record_path)

    def showfailedRecord(self):
        """查看操作失败记录"""
        if self.failed_record_path:
            webbrowser.open(self.failed_record_path)

    def get_files(self):
        """获取文件路径集合"""
        file_list = []
        src_dir = self.src_dir.get()
        sort_reverse = self.sort_reverse.get()
        sort_mode = self.sort_mode.get()
        logger.debug("sort_reverse: %s, sort_bymtime: %s" % (sort_reverse, sort_mode))
        if sort_mode:  # 根据修改时间排序
            # 获取文件的路径和对应修改时间
            temp_list = []  # 储存文件路径和修改时间
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_mtime = os.path.getmtime(file_path)
                    temp_list.append((file_mtime, file_path))
            # 冒泡排序
            time_str = common_utils.get_times_now().get('time_str')
            self.scr.insert("end", "%s  正在使用冒泡排序根据文件修改时间对文件进行排序...\n" % time_str)
            n = len(temp_list)
            if sort_reverse is False:  # 正序
                for i in range(n):
                    for j in range(0, n-i-1):
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
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_list.append(os.path.join(root, file))
        # logger.debug(file_list)
        return file_list

    def calc_hash(self, file_list):
        """计算hash值"""
        hash_dict = {}  # 用于储存文件的hash信息， 数据格式{hash_value:[same_path1,samepath2,],}
        same_count = 0  # 重复文件个数
        for item in file_list:
            self.pb1["value"] += 1
            hash_value = common_utils.get_md5(item)
            if hash_value not in hash_dict:
                hash_dict[hash_value] = [item, ]  # 创建新记录
            else:
                same_count += 1
                hash_dict[hash_value].append(item)
                self.scr.insert("end", "发现重复文件 %s !\n" % item)
                self.scr.see('end')
        return {"same_count": same_count, "hash_dict": hash_dict}

    @staticmethod
    def make_new_name(file_path, src_dir_path):
        """构造新文件名"""
        # 获取新文件名
        old_file_dir = os.path.dirname(file_path)  # 原文件目录
        if old_file_dir == src_dir_path:
            new_file_name = os.path.basename(file_path)
        else:
            # 拼接带相对目录结构的文件名
            sub_dir_str = old_file_dir.replace(src_dir_path, '').replace('\\', '_').replace("/", "_")[1:]
            old_name = os.path.basename(file_path)
            old_ext = os.path.splitext(old_name)[-1]
            old_ext = '' if (old_ext==old_name) else old_ext
            new_file_name = old_name + "_[{}]{}".format(sub_dir_str, old_ext)
        return new_file_name

    def move_files(self, hash_dict):
        """移动文件"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        move_all_flag = self.move_all_flag.get()
        deal_str = self.move_option.get()
        deal_mode = self.optionDict[deal_str]
        failed_files = []  # 记录移动失败的文件
        new_old_record = {}  # 记录新旧文件名 格式{new_path:old_path,}
        num = 0  # 编号
        self.pb1["maximum"] = len(hash_dict)  # 总项目数
        self.pb1["value"] = 0
        move_func = common_utils.copy_file if deal_mode == 'copy' else common_utils.move_file
        # 操作文件
        for file_list in hash_dict.values():
            self.pb1["value"] += 1
            if len(file_list) <= 1:
                continue
            deal_files = file_list if move_all_flag else file_list[1:]
            num += 1
            for old_path in deal_files:
                # 获取新文件名
                new_file_name = self.make_new_name(old_path, src_dir)
                new_file_name = 'H%s__%s' % (num, new_file_name) if move_all_flag else new_file_name
                new_path = os.path.join(dst_dir, new_file_name)

                # 移动文件
                if os.path.exists(new_path):
                    self.scr.insert("end", "%s 已存在同名文件，移动失败！\n" % new_path)
                    failed_files.append(old_path)
                    continue
                try:
                    move_func(old_path, new_path)
                    new_old_record[new_path] = old_path
                except Exception as e:
                    failed_files.append(old_path)
                    print("moving %s failed!,Exception:%s " % (old_path, e))
                    self.scr.insert("end", "%s 移动失败！\n" % old_path)
        return {"failed_files": failed_files, "new_old_record": new_old_record}

    def export_record(self, same_count, hash_dict, new_old_record, failed_files):
        """导出记录文件"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        deal_str = self.move_option.get()
        time_now_str = time.strftime(r"%Y%m%d%H%M%S", time.localtime())
        path_failed_files_record = os.path.join(settings.RECORD_DIR, 'moveFailed_%s.txt' % time_now_str)  # 移动失败的文件的记录路径
        path_new_old_record = os.path.join(settings.RECORD_DIR, 'new_old_record_%s.txt' % time_now_str)  # 移动成功的文件的新旧文件名记录路径
        path_same_record = os.path.join(settings.RECORD_DIR, 'same_record_%s.txt' % time_now_str)  # 移动成功的文件的新旧文件名记录路径
        msg = "hash去重完成! 共找到 %s 个重复文件！\n" % same_count
        log_msg = "【HASH查重】  hash去重完成! %s 共找到 %s 个重复文件！" % (src_dir, same_count)
        if same_count:
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
            msg += "重复文件 %s 到 %s\n重复文件信息记录到 %s\n" % (deal_str, dst_dir, path_same_record)
            log_msg += "重复文件 %s 到 %s,重复文件信息记录到 %s" % (deal_str, dst_dir, path_same_record)
        if len(failed_files):
            self.failed_record_path = path_failed_files_record
            self.btn_showFailedRecord.config(state=tk.NORMAL)
            with open(path_failed_files_record, 'w', encoding='utf-8') as f:
                for item in failed_files:
                    f.write("%s\n" % item)
            msg += " %s 个文件移动失败,记录到 %s\n" % (len(failed_files), path_failed_files_record)
            log_msg += ", %s 个文件移动失败,记录到 %s" % (len(failed_files), path_failed_files_record)
        if len(new_old_record):
            self.record_path = path_new_old_record
            self.btn_restore.config(state=tk.NORMAL)
            with open(path_new_old_record, 'a', encoding='utf-8') as f:
                for new_file in new_old_record:
                    f.write("%s\t%s\n" % (new_file, new_old_record[new_file]))
            msg += "新旧文件名记录保存到%s\n" % path_new_old_record
            log_msg += ",新旧文件名记录保存到%s" % path_new_old_record

        logger.debug(msg)
        logger.info(log_msg)
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert("end", '\n\n%s  %s' % (time_str, msg))

    @deal_running_task_arg('校验hash值方式查找重复文件')
    def deal_query_same(self):
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        start_time = time_res.get('timestamp')  # 开始时间
        self.scr.insert("end", "%s  正在遍历文件目录...\n" % time_str)

        # 获取文件列表
        file_list = self.get_files()
        tmp_msg = "文件列表为：\n"
        for item in file_list:
            tmp_msg += "%s\n" % item
        self.scr.insert("end", tmp_msg)
        self.scr.see(tk.END)
        self.pb1["maximum"] = len(file_list)  # 总项目数
        # logger.debug("\n一共有 %s 个文件,正在进行hash计算找出重复文件..." % len(file_list))
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert("end", "\n\n%s 共有 %s 个文件,正在进行hash计算找出重复文件...\n" % (time_str, len(file_list)))
        
        # 计算文件hash值
        res = self.calc_hash(file_list)
        same_count = res["same_count"]
        hash_dict = res["hash_dict"]
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert("end", "\n\n%s  共找到 %s 个重复文件,开始操作文件...\n" % (time_str, same_count))

        # 移动文件
        res = self.move_files(hash_dict)
        new_old_record = res["new_old_record"]
        failed_files = res["failed_files"]
        
        # 导出记录文件
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert("end", "\n\n%s  操作文件完成,正在导出记录...\n" % time_str)
        self.export_record(same_count, hash_dict, new_old_record, failed_files)

        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        end_time = time_res.get('timestamp')  # 结束时间
        self.scr.insert("end", "用时%ss\n" % (end_time - start_time))
        self.scr.see("end")
        self.btn_show.config(state=tk.NORMAL)
        mBox.showinfo('任务完成', "hash方式查找相同文件完成!")

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        t = threading.Thread(target=self.deal_query_same)
        t.daemon = True
        t.start()


class SynFrame(BaseFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()  # 模式 "基于filecmp模块", "自己实现的Mybackup", "备份端目录变更同步"
        self.src_dir = tk.StringVar()  # 源目录
        self.dst_dir = tk.StringVar()  # 备份端
        self.syc_option = tk.StringVar()
        self.result = None  # 用于存储两个目录比较结果
        self.modeDict = {
            "基于filecmp模块": 1,
            "基于Mybackup": 2,
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
        self.time_fix_flag = tk.BooleanVar()  # True 进行时间偏移修正， 用于不同文件系统对文件时间戳精度保留不同导致的问题
        self.time_fix = tk.StringVar()  # 时间修正值 秒数
        self.hash_flag = tk.BooleanVar()  # 是否校验文件hash值
        self.createPage()

    def selectPath1(self):
        self.src_dir.set(askdirectory())
        self.clear()

    def selectPath2(self):
        self.dst_dir.set(askdirectory())
        self.clear()

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            if self.src_dir.get():
                self.dst_dir.set(self.src_dir.get())
            self.src_dir.set(dir_path)

    def clear(self):
        """清空相关输入和显示数据"""
        self.record_path = None
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""
        self.scr.delete(1.0, tk.END)

    def invoke_item(self):
        """设置选项输入框锁定和激活状态"""
        total = [self.btn_time_fix, self.e_time_fix, self.btn_hash]
        invoke_list = []
        if self.modeDict[self.mode.get()] in [2, 3]:
            invoke_list = [self.btn_time_fix, self.btn_hash]
            if self.time_fix_flag.get() is True:
                invoke_list.append(self.e_time_fix)
        for item in total:
            if item in invoke_list:
                item.config(state=tk.NORMAL)
            else:
                item.config(state=tk.DISABLED)

    def selectOption(self):
        self.optionChosen["value"] = self.optionDict[self.modeDict[self.mode.get()]]  # 联动下拉框
        self.optionChosen.current(0)
        # 设置选项输入框锁定和激活状态
        self.invoke_item()
        self.scr.delete(1.0, 'end')  # 清空原内容
        self.exeStateLabel["text"] = ""
        self.proStateLabel["text"] = ""
        self.result = None
        self.btn_run.config(state=tk.DISABLED)

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        self.lock_elements.append(self.optionChosen)
        for element in self.lock_elements:
            element.config(state=tk.DISABLED)

    @deal_running_task_arg('文件备份与同步-校对文件')
    def findDiff(self):
        """用于实际进行文件比对操作"""
        self.exeStateLabel["text"] = "比对文件中..."
        self.proStateLabel["text"] = "running..."
        src_path = self.src_dir.get()
        dst_path = self.dst_dir.get()
        time_fix_flag = self.time_fix_flag.get()  # 是否进行时间偏移修正
        time_fix = float(self.time_fix.get())  # 时间偏移修正值
        hash_flag = self.hash_flag.get()  # 是否校验文件hash值
        try:
            if self.modeDict[self.mode.get()] == 2:  # 基于Mybackup
                if (time_fix_flag, hash_flag) == (False, False):
                    self.result = syn_utils.find_difference2(src_path, dst_path)
                else:
                    self.result = syn_utils.find_difference4(src_path, dst_path, time_fix, hash_flag)
            elif self.modeDict[self.mode.get()] == 3:  # 仅进行备份端目录变更
                if (time_fix_flag, hash_flag) == (False, False):
                    self.result = syn_utils.find_difference3(src_path, dst_path)
                else:
                    self.result = syn_utils.find_difference5(src_path, dst_path, time_fix, hash_flag)
            else:  # 基于filecmp返回的数据，文件和文件夹统计在一起
                self.result = {"only_in_src": [], "only_in_dst": [], "diff_files": [],
                               "common_funny": []}  # 用于存储两个目录比较结果
                self.result = syn_utils.do_compare(src_path, dst_path, self.result)
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
        # logger.debug(str(self.result))
        count_detial = self.result.pop("count")
        # logger.debug(count_detial)
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
            self.scr.insert('end', "\n详情:", "title")
        else:
            self.scr.insert('end', "\n文件内容无变化!", "title")
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
        self.proStateLabel["text"] = "complete!"
        self.btn_run.config(state=tk.NORMAL)

    def findDiffRun(self):
        """"执行比对文件的主程序，调用实际执行子进程"""
        self.clear()
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        flag = common_utils.check_floatNum(self.time_fix.get())
        if not flag:  # 输入的时间偏移值不是数值，则默认置0
            self.time_fix.set(0)
        t = threading.Thread(target=self.findDiff)
        t.daemon = True
        t.start()

    @staticmethod
    def backup_logger(result, src_path, dst_path, safe_del_dirname, option):
        """
        用于保存操作日志
        update:
            更改日志结构和数据格式 以配合backup_V1.py
        :param result: 差异文件结果集 dict 保存着两个目录下文件差异信息
        :param src_path: 源目录
        :param dst_path: 目标目录
        :param safe_del_dirname: 存放被删除文件的safe_del目录
        :param option: 操作模式
                backup_full   全备份
                backup_update 增量备份
                recovery      备份还原
        :return:
        """
        only_in_src_count = len(result["file_only_in_src"]) + len(result["dir_only_in_src"])
        only_in_dst_count = len(result["file_only_in_dst"]) + len(result["dir_only_in_dst"])
        if "move_dict" in result:
            # 判断是否是Mybackup传进来的result
            update_count = len(result["diff_files"]) + len(result["common_funny"]) + len(result["move_dict"])
        else:
            update_count = len(result["diff_files"]) + len(result["common_funny"])
        add_file = "file_only_in_src"
        add_dir = "dir_only_in_src"
        del_file = "file_only_in_dst"
        del_dir = "dir_only_in_dst"

        msg = '【文件同步与备份】  '
        if "backup_full" == option:
            msg += "同步备份完成！ FROM: %s TO: %s ,新增 %s 个项目,删除 %s 个项目,更新 %s 个项目" % (src_path, dst_path, only_in_src_count, only_in_dst_count, update_count)
        if "backup_update" == option:
            msg += "增量备份完成！ FROM: %s TO: %s ,新增 %s 个项目,删除 0 个项目,更新 %s 个项目" % (src_path, dst_path, only_in_src_count, update_count)
        if "recovery" == option:
            msg += "同步还原完成！ FROM: %s TO: %s ,新增 %s 个项目,删除 %s 个项目,更新 %s 个项目" % (src_path, dst_path, only_in_dst_count, only_in_src_count, update_count)
            add_file, del_file = del_file, add_file
            add_dir, del_dir = del_dir, add_dir
        if "only_add" == option:
            msg += "仅新增文件完成！ FROM: %s TO: %s ,新增 %s 个项目" % (src_path, dst_path, only_in_src_count)

        # 将操作记录保存到操作日志
        if safe_del_dirname:
            msg += ",删除和更新文件原文件导出到 %s 目录下!" % safe_del_dirname
        logger.info(msg)
        local_time = time.strftime(r"%Y-%m-%d %H:%M:%S", time.localtime())
        # 将备份或同步详细记录保存到日志'log/backup_info.log'文件
        record_path = os.path.join(settings.LOG_DIR, "backup_info.log")
        with open(record_path, 'a', encoding='utf-8') as f:
            f.write("-" * 100)
            f.write("\n%s\t %s\n" % (local_time, msg))
            if safe_del_dirname:
                f.write("删除和更新文件原文件导出到 %s 目录下!\n" % safe_del_dirname)
            f.write("%s  -->  %s\n" % (src_path, dst_path))
            # 记录新增
            if len(result[add_file]) + len(result[add_dir]):
                if "move_dict" in result:
                    f.write("新增(文件 %s 个,文件夹 %s 个):\n" % (len(result[add_file]) + len(result["move_dict"]), len(result[add_dir])))
                else:
                    f.write("新增(文件 %s 个,文件夹 %s 个):\n" % (len(result[add_file]), len(result[add_dir])))
                if len(result[add_file]):
                    f.write("->文件:\n")
                    for item in result[add_file]:
                        f.write("%s\n" % item)
                if "move_dict" in result:
                    if len(result["move_dict"]):
                        f.write("->备份端自拷贝:\n")
                        for dst_item, item in result["move_dict"].items():
                            f.write("%s  -->  %s\n" % (item, dst_item))
                if len(result[add_dir]):
                    f.write("->文件夹:\n")
                    for item in result[add_dir]:
                        f.write("%s\n" % item)
            # 记录更新
            if "only_add" != option:
                if update_count:
                    f.write("更新(文件 %s 个):\n" % update_count)
                    for item in result["diff_files"]:
                        f.write("%s\n" % item)
                    for item in result["common_funny"]:
                        f.write("%s\n" % item)
            # 记录删除
            if "backup_update" != option:
                if len(result[del_file]) + len(result[del_dir]):
                    f.write("删除(文件 %s 个,文件夹 %s 个):\n" % (len(result[del_file]), len(result[del_dir])))
                    if len(result[del_file]):
                        f.write("->文件:\n")
                        for item in result[del_file]:
                            f.write("%s\n" % item)
                    if len(result[del_dir]):
                        f.write("->文件夹:\n")
                        for item in result[del_dir]:
                            f.write("%s\n" % item)
            f.write("\n")

        return msg

    def deal_file(self, src_path, dst_path, result, deal_option):
        """
        适配基于filecmp模块的文件同步功能
        用于进行文件备份或者同步还原操作文件的函数
        :param result: 差异文件结果集 dict 保存着两个目录下文件差异信息
        :param src_path: 源目录
        :param dst_path: 目标目录
        :param deal_option: 操作模式
                backup_full   全备份
                backup_update 增量备份, 新增和更新
                recovery      备份还原
                only_add   仅新增
        """
        start_time = time.time()  # 记录同步操作开始时间
        logger.debug(deal_option)
        safe_del_dirname = None  # 用于记录safe_del目录
        add_element = "only_in_src"
        del_element = "only_in_dst"
        if "backup_full" == deal_option:
            if len(result["only_in_dst"]) or len(result["diff_files"]) or len(result["common_funny"]):
                safe_del_dirname = common_utils.makedir4safe_del(dst_path)
        if "backup_update" == deal_option:
            if len(result["diff_files"]) or len(result["common_funny"]):
                safe_del_dirname = common_utils.makedir4safe_del(dst_path)
        if "recovery" == deal_option:
            if len(result["only_in_src"]) or len(result["diff_files"]) or len(result["common_funny"]):
                safe_del_dirname = common_utils.makedir4safe_del(src_path)
            src_path, dst_path = dst_path, src_path
            add_element, del_element = del_element, add_element
        # 执行新增
        if len(result[add_element]):
            self.exeStateLabel["text"] = "执行文件新增..."
        for item in result[add_element]:
            new_src = os.path.join(src_path, item)
            new_dst = os.path.join(dst_path, item)
            common_utils.copy_file(new_src, new_dst)
        # 执行删除
        if deal_option not in ["backup_update", "only_add"]:  # 增量备份不执行删除
            if len(result[del_element]):
                self.exeStateLabel["text"] = "执行文件删除..."
            for item in result[del_element]:
                new_dst = os.path.join(dst_path, item)
                safe_del_file = os.path.join(safe_del_dirname, item)
                common_utils.move_file(new_dst, safe_del_file)
        # 执行文件内容变更的文件更新
        if "only_add" != deal_option:  # 仅新增 不执行文件更新
            if len(result["diff_files"]) or len(result["common_funny"]):
                self.exeStateLabel["text"] = "执行文件更新..."
            for item in result["diff_files"]:
                new_src = os.path.join(src_path, item)
                new_dst = os.path.join(dst_path, item)
                safe_del_file = os.path.join(safe_del_dirname, item)
                common_utils.update_file(new_src, new_dst, safe_del_file)
            # 执行文件名相同但无法比对（即文件名相同但一个是文件一个是文件夹）的更新
            for item in result["common_funny"]:
                new_src = os.path.join(src_path, item)
                new_dst = os.path.join(dst_path, item)
                safe_del_file = os.path.join(safe_del_dirname, item)
                common_utils.update_file(new_src, new_dst, safe_del_file)

        result = syn_utils.filter_4_dict(src_path, dst_path, result)  # 调用过滤函数得到文件列表和目录列表
        msg = self.backup_logger(result, src_path, dst_path, safe_del_dirname, deal_option)
        syn_time = time.time() - start_time
        logger.debug("同步用时：%ss" % syn_time)  # 打印拷贝用时
        self.scr.insert('end', '\n\n\n\n{}\n本次同步用时: {}s\n'.format(msg, syn_time))
        return msg

    def deal_file2(self, src_path, dst_path, result, deal_option):
        """
        适配自己实现的Mybackup方式
        用于进行实际操作文件的函数
        :param window: GUI窗口对象
        :param result: 差异文件结果集 dict 保存着两个目录下文件差异信息, 绝对路径
        :param src_path: 源目录
        :param dst_path: 目标目录
        :param deal_option: 操作模式
                backup_full   全备份
                backup_update 新增和更新
                only_add 仅新增

        """
        start_time = time.time()  # 开始时间
        safe_del_dirname = common_utils.makedir4safe_del(dst_path)  # 用于记录safe_del目录
        add_file = "file_only_in_src"
        add_dir = "dir_only_in_src"
        del_file = "file_only_in_dst"
        del_dir = "dir_only_in_dst"
        # 先备份端自拷贝，再更新文件，再更新无法比对，再新增，再删除
        # 执行目录变更文件移动即备份端目录变更
        move_dict = result["move_dict"]
        if move_dict:
            self.exeStateLabel["text"] = "执行目录变更中(备份端自拷贝)..."
            for item in move_dict:
                new_dst = item
                new_src = move_dict[item]
                common_utils.move_file(new_src, new_dst)
        # 执行文件内容变更的文件更新
        if deal_option in ['backup_update', 'backup_full']:  # 同步备份、新增和更新的时候才会执行更新操作
            if len(result["diff_files"]) or len(result["common_funny"]):
                self.exeStateLabel["text"] = "执行文件更新..."
            if len(result["diff_files"]):
                for item in result["diff_files"]:
                    new_src = item
                    new_dst = item.replace(src_path, dst_path)
                    safe_del_file = item.replace(src_path, safe_del_dirname)
                    common_utils.update_file(new_src, new_dst, safe_del_file)
            # 执行文件名相同但无法比对（即文件名相同但一个是文件一个是文件夹）的更新
            if len(result["common_funny"]):
                for item in result["common_funny"]:
                    new_src = item
                    new_dst = item.replace(src_path, dst_path)
                    safe_del_file = item.replace(src_path, safe_del_dirname)
                    common_utils.update_file(new_src, new_dst, safe_del_file)

        # 执行新增
        if len(result[add_file]) or len(result[add_dir]):
            self.exeStateLabel["text"] = "执行文件新增..."
        if len(result[add_file]):
            for item in result[add_file]:
                new_src = item
                new_dst = item.replace(src_path, dst_path)
                common_utils.copy_file(new_src, new_dst)
        if len(result[add_dir]):
            dir_dict = syn_utils.filter_dir(result[del_dir])  # 过滤获取顶级父目录和空目录
            for item in dir_dict["empty_dir"]:
                new_src = item
                new_dst = item.replace(src_path, dst_path)
                common_utils.copy_file(new_src, new_dst)

        # 执行删除
        if deal_option == 'backup_full':  # 只有同步备份的时候会删除操作
            if len(result[del_file]) or len(result[del_dir]):  # 有要删除的文件
                self.exeStateLabel["text"] = "执行文件删除..."
            if len(result[del_file]):
                for item in result[del_file]:
                    if not os.path.exists(item):
                        continue
                    safe_del_file = item.replace(dst_path, safe_del_dirname)
                    # 为了避免重复删除导致报错，即如果common_funny目录下有文件，原来更新时候删除一次后来删除的时候又删除一次就会出错
                    if not os.path.exists(safe_del_file):
                        common_utils.move_file(item, safe_del_file)
            if len(result[del_dir]):
                dir_dict = syn_utils.filter_dir(result[del_dir])  # 过滤获取顶级父目录和空目录
                for item in dir_dict["empty_dir"]:
                    safe_del_file = item.replace(dst_path, safe_del_dirname)
                    if not os.path.exists(safe_del_file):  # 空文件夹未被拷贝到safe_del目录下
                        common_utils.move_file(item, safe_del_file)
                for item in dir_dict["parent_dir"]:  # 删除顶级父目录
                    if os.path.exists(item):
                        shutil.rmtree(item)

        msg = self.backup_logger(result, src_path, dst_path, safe_del_dirname, deal_option)
        syn_time = time.time() - start_time
        logger.debug("同步用时：%ss" % syn_time)  # 打印拷贝用时
        self.scr.insert('end', '\n\n\n\n{}\n本次同步用时: {}s\n'.format(msg, syn_time))
        return msg

    def deal_file3(self, src_path, dst_path, result, deal_option):
        """
        适配备份端目录变更模式
        用于移动或者复制文件，并将新旧文件名记录到new_old_record,并导出文件"
        :param window: GUI窗口对象
        :param result: 保存文件目录变更信息 格式{newpath1: oldpath1,}
        :param dst_path: 备份端路径
        :param src_path: 源目录   占位
        :param deal_option: 操作模式   占位
        :return: 
        """""
        start_time = time.time()  # 记录同步操作开始时间
        failed_list = []  # 用于记录拷贝或剪切失败的文件信息
        move_dict = result["move_dict"]
        self.exeStateLabel["text"] = "执行目录变更中..."
        for new_path in move_dict:
            try:
                common_utils.move_file(move_dict[new_path], new_path)  # 剪切文件
            except Exception as e:
                failed_list.append(move_dict[new_path])
                print("操作 %s 文件失败,详情请查看错误日志！" % move_dict[new_path])
                logger.error('操作 %s 失败, error: %s' % (new_path, e))

        self.exeStateLabel["text"] = "目录变更完成!"
        # 写出到记录文件和日志
        write_time = common_utils.get_times_now().get('time_num_str')  # 获取当前时间的两种格式
        msg = "【文件同步与备份】  备份端 %s 目录变更 %s 个文件成功" % (dst_path, len(move_dict))
        if len(move_dict):
            record_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("new_old_record", write_time))
            common_utils.export_new_old_record(move_dict, record_path)  # 将文件剪切前后文件信息导出到new_old_record
            msg += "，新旧文件名导出到 %s" % record_path
            if len(failed_list):
                failed_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("failed", write_time))
                msg += "\n\t\t%s 个文件操作失败,文件信息导出到 %s" % (len(failed_list), failed_path)
                with open(failed_path, 'a', encoding="utf-8") as f:
                    f.write('\n'.join(failed_list))
        logger.info(msg)
        syn_time = time.time() - start_time
        logger.debug("同步用时：%ss" % syn_time)  # 打印拷贝用时
        self.scr.insert('end', '\n\n\n\n{}\n本次同步用时: {}s\n'.format(msg, syn_time))
        return msg

    @deal_running_task_arg('文件备份与同步-同步文件')
    def deal_syn(self):
        """用于处理文件同步类操作"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        self.exeStateLabel["text"] = "同步文件中..."
        self.proStateLabel["text"] = "running..."
        option = self.syc_option.get()
        if option in ["1", "同步备份"]:
            option = "backup_full"
        elif option in ["2", "同步还原"]:
            option = "recovery"
        elif option in ["3", "新增和更新"]:
            option = "backup_update"
        elif option in ["4", "仅新增"]:
            option = "only_add"

        if self.modeDict[self.mode.get()] == 2:  # 基于Mybackup
            msg = self.deal_file2(src_dir, dst_dir, self.result, option)
        elif self.modeDict[self.mode.get()] == 3:  # 仅进行备份端目录变更
            msg = self.deal_file3(src_dir, dst_dir, self.result, option)
        else:  # 基于filecmp返回的数据，文件和文件夹统计在一起
            msg = self.deal_file(src_dir, dst_dir, self.result, option)
        self.exeStateLabel["text"] = "文件同步完成!"
        self.proStateLabel["text"] = "complete!"
        self.btn_run.config(state=tk.DISABLED)
        mBox.showinfo('任务完成', "文件同步操作完成!")

    def run(self):
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        t = threading.Thread(target=self.deal_syn)
        t.daemon = True
        t.start()

    def createPage(self):
        self.l_title["text"] = "文件同步备份"
        ttk.Label(self.f_input, text='源目录路径: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        ttk.Label(self.f_input, text='备份端路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, pady=10)
        col = 1
        for item in self.modeDict:
            ttk.Radiobutton(self.f_input_option, text=item, variable=self.mode, value=item, command=self.selectOption).grid(
                column=col, row=0)
            col += 1
        self.mode.set("基于filecmp模块")
        self.btn_time_fix = ttk.Checkbutton(self.f_input_option, text="时间偏移", variable=self.time_fix_flag, onvalue=True, offvalue=False, command=self.invoke_item)
        self.btn_time_fix.grid(row=0, column=4)
        self.e_time_fix = ttk.Entry(self.f_input_option, textvariable=self.time_fix, width=5)
        self.e_time_fix.grid(row=0, column=5)
        ttk.Label(self.f_input_option, text='秒').grid(row=0, column=6)
        self.btn_hash = ttk.Checkbutton(self.f_input_option, text="校验hash值", variable=self.hash_flag, onvalue=True, offvalue=False, command=self.invoke_item)
        self.btn_hash.grid(row=0, column=7, padx=5)
        ttk.Button(self.f_input, text="比对差异", command=self.findDiffRun).grid(row=3, column=4, pady=5)
        # 展示结果
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)
        ttk.Label(self.f_bottom, text='请选择操作: ').grid(row=0, column=0, pady=10)
        self.optionChosen = ttk.Combobox(self.f_bottom, width=20, textvariable=self.syc_option)
        if self.mode.get():
            self.optionChosen['values'] = self.optionDict[self.modeDict[self.mode.get()]]
        else:
            self.optionChosen['values'] = self.optionDict[1]
        self.optionChosen.grid(row=0, column=1, pady=10)
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        self.optionChosen.config(state='readonly')  # 设为只读模式

        self.f_bottom.grid_columnconfigure(3, weight=1)  # 设置自适应
        ttk.Label(self.f_bottom, text="").grid(row=0, column=3)  # 空占位
        self.btn_run = ttk.Button(self.f_bottom, text="执行", command=self.run, state=tk.DISABLED)
        self.btn_run.grid(row=0, column=4, sticky=tk.EW)
        ttk.Label(self.f_bottom, text='程序运行状态: ').grid(row=2, pady=5)
        self.exeStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序执行任务状态
        self.exeStateLabel.grid(row=2, column=1, columnspan=2, sticky=tk.W)
        self.proStateLabel = ttk.Label(self.f_bottom, text='')  # 用于显示程序总运行状态
        self.proStateLabel.grid(row=2, column=4, sticky=tk.W)
        self.invoke_item()  # 设置各选择或输入组件状态
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作


class RestoreFrame(BaseFrame):
    """还原文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.same_file_option = tk.StringVar()  # 同名文件处理方式 overwrite 覆盖 skip 跳过 ask 询问
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "还原文件"
        ttk.Label(self.f_input, text='new_old_record路径: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, columnspan=2, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=3)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=1, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='若目标已存在重名项目，处理方式？: ').grid(row=2, column=0, sticky=tk.EW)
        # ttk.Radiobutton(self.f_input_option, text="询问", variable=self.same_file_option, value='ask').grid(row=2, column=1, padx=5)
        ttk.Radiobutton(self.f_input_option, text="覆盖", variable=self.same_file_option, value='overwrite').grid(row=2, column=2, padx=5)
        ttk.Radiobutton(self.f_input_option, text="跳过", variable=self.same_file_option, value='skip').grid(row=2, column=3, padx=5)
        self.same_file_option.set('skip')
        ttk.Button(self.f_input, text='重做', command=self.deal_undo_restore).grid(row=1, column=2, sticky=tk.E, pady=10)
        ttk.Button(self.f_input, text='还原', command=self.deal_restore).grid(row=1, column=3, sticky=tk.E, pady=10)
        scrolW = 120
        scrolH = 45
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def selectPath(self):
        path_ = askopenfilename()
        self.src_dir.set(path_)

    @deal_running_task_arg('还原文件')
    def do_restore(self, record_path):
        """还原文件"""
        same_file_option = self.same_file_option.get()
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert('end', '%s  正在还原 %s 记录中的文件...\n' % (time_str, record_path))
        res = common_utils.restore_file_by_record(record_path, same_file_option)
        sucess_count = len(res['sucess_list'])
        failed_count = len(res['failed_list'])
        skip_count = len(res['skip_list'])
        write_record_path = res['record_path']
        msg = "根据 {},成功还原了 {} 个项目！".format(record_path, sucess_count)
        msg1 = '操作完成！'
        if failed_count:
            msg += "另有 {}个项目还原失败！".format(failed_count)
            msg1 += '以下文件操作失败：\n'
            for item in res['failed_list']:
                msg1 += '{}\n'.format(item)
        if skip_count:
            msg += ", {} 个项目在目标目录已有重名存在，故跳过！".format(skip_count)
            msg1 += '以下项目在目标目录已有重名存在，故跳过：\n'
            for item in res['skip_list']:
                msg1 += '{}\n'.format(item)
        msg += '还原操作记录到 {}'.format(write_record_path)
        time_str = common_utils.get_times_now().get('time_str')
        logger.info('【文件还原】  %s' % msg)
        self.scr.insert('end', '\n{}\n'.format(msg1))
        self.scr.insert('end', '\n\n%s  %s\n' % (time_str, msg))
        self.scr.see(tk.END)
        mBox.showinfo('任务完成', "还原文件完成!")

    @deal_running_task_arg('撤销还原')
    def undo_restore(self, record_path):
        """根据记录重新移动文件，即重做 即撤销还原"""
        same_file_option = self.same_file_option.get()
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert('end', '%s  正在根据 %s 记录重新操作文件...\n' % (time_str, record_path))
        res = common_utils.undo_restore_file_by_record2(record_path, same_file_option)
        sucess_count = len(res['sucess_list'])
        failed_count = len(res['failed_list'])
        skip_count = len(res['skip_list'])
        msg = "根据 {},重新操作了 {} 个项目！".format(record_path, sucess_count)
        msg1 = '操作完成！'
        if failed_count:
            msg += "另有 {}个项目操作失败！".format(failed_count)
            msg1 += '以下文件操作失败：\n'
            for item in res['failed_list']:
                msg1 += '{}\n'.format(item)
        if skip_count:
            msg += ", {} 个项目在目标目录已有重名存在，故跳过！".format(skip_count)
            msg1 += '以下项目在目标目录已有重名存在，故跳过：\n'
            for item in res['skip_list']:
                msg1 += '{}\n'.format(item)
        time_str = common_utils.get_times_now().get('time_str')
        logger.info('【撤销还原】  %s' % msg)
        self.scr.insert('end', '\n{}\n'.format(msg1))
        self.scr.insert('end', '\n\n%s  %s\n' % (time_str, msg))
        self.scr.see(tk.END)
        mBox.showinfo('任务完成', "重新操作文件完成!")

    def deal_restore(self):
        """还原文件"""
        self.scr.delete(1.0, 'end')
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.do_restore, args=(self.src_dir.get(),))
        t.daemon = True
        t.start()

    def deal_undo_restore(self):
        """撤销还原"""
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.undo_restore, args=(self.src_dir.get(),))
        t.daemon = True
        t.start()


class CleanEmptyDirFrame(BaseFrame):
    """清除空文件夹"""
    def __init__(self, master=None):
        super().__init__(master)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "清除空文件夹"
        ttk.Label(self.f_input, text='目录路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=1, column=3)
        ttk.Button(self.f_input, text='清空', command=self.run).grid(row=2, column=3, sticky=tk.E, pady=10)
        scrolW = 120
        scrolH = 45
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @deal_running_task_arg('清除空文件夹')
    def deal_clear_empty_dir(self, dir_path):
        logger.debug(self.src_dir.get())
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert('end', '%s  正在清除 %s 目录下的空文件夹...\n' % (time_str, dir_path))
        del_list = common_utils.remove_empty_dir(dir_path)
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        record_path = os.path.join(settings.RECORD_DIR, 'del_record_%s.txt' % time_res.get('time_num_str'))
        if len(del_list):
            msg = "清除了 %s 下 %s 个空文件夹!\n删除的空文件夹信息记录到 %s" % (dir_path, len(del_list), record_path)
            log_msg = "清除了 %s 下 %s 个空文件夹!删除的空文件夹信息记录到 %s" % (dir_path, len(del_list), record_path)
            # 输出显示
            self.scr.insert('end', "\n%s  清除了 %s 个空文件夹!\n" % (time_str, len(del_list)))
            self.scr.insert('end', "\n空文件夹如下:\n", 'info')
            for item in del_list:
                self.scr.insert(tk.END, '%s\n' % item)
            common_utils.export_path_record(del_list, record_path)
            logger.info('【清除空文件夹】  %s' % log_msg)  # 记录日志
        else:
            msg = "%s  下没有找到空文件夹！" % dir_path
            logger.debug("没有找到空文件夹！")
        self.scr.insert('end', "\n\n%s  %s\n" % (time_str, msg), 'info')
        self.scr.tag_config('info', font=('microsoft yahei', 16, 'bold'))
        self.scr.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr.see(tk.END)
        mBox.showinfo('任务完成', "清除空文件夹完成!")

    def run(self):
        self.scr.delete(1.0, 'end')
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.deal_clear_empty_dir, args=(self.src_dir.get(),))
        t.daemon = True
        t.start()


class SearchFrame(BaseFrame):
    """搜索文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_flag = tk.BooleanVar()  # True 操作文件夹 False 不操作
        self.file_flag = tk.BooleanVar()  # True 操作文件 False 不操作
        self.search_mode = tk.StringVar()  # 搜索模式 name 文件名 size 文件大小 type 文件数据类型即MIME类型 file 根据记录文件搜索 '5' 视频时长 '6' 视频分辨率 '7' 图片分辨率 '8' 音频时长
        self.reg_flag = tk.BooleanVar()  # True 正则匹配/条件匹配， False 精确搜索
        self.search_str = tk.StringVar()  # 搜索语句
        self.export_mode = tk.IntVar()  # 导出模式 1.导出到单级目录并附带目录结构描述 2.导出到单级目录 3.保持源目录结构
        self.deal_mode = tk.StringVar()
        self.filter_mode = tk.StringVar()  # 过滤模式 选中 select 排除 exclude
        self.filter_str = tk.StringVar()  # 过滤语句  正则语句
        self.same_file_option = tk.StringVar()  # 遇到已存在同名文件处理方式  'ask'询问，'overwrite' 覆盖，'skip' 跳过
        self.meta_result = {'files': [], 'dirs': []}  # 完整搜索的结果，即最全的搜索集  搜索到的结果
        self.result = {'files': [], 'dirs': []}  # 用于储存文件操作的搜索结果  过滤之后进行文件复制移动的文件信息
        self.tmp_result = {'files': [], 'dirs': []}  # 用于储存按时间过滤切换前的 文件的搜索结果
        self.size_up = tk.StringVar()  # 文件大小上限
        self.size_down = tk.StringVar()  # 文件大小下限
        self.size_up_unit = tk.StringVar()  # 文件大小上限的单位  'TB', 'GB', 'MB', 'KB', 'B'
        self.size_down_unit = tk.StringVar()  # 文件大小下限的单位
        self.size_up_sign = tk.StringVar()  # 比较符号 < <=
        self.size_down_sign = tk.StringVar()  # 比较符号 < <=
        self.time_flag = tk.BooleanVar()  # True 按时间搜索过滤结果 False 不按时间搜索
        self.time_option = tk.StringVar()  # 记录选择的时间类型  修改时间   创建时间  照片拍摄时间
        self.time_start = tk.StringVar()  # 开始时间
        self.time_end = tk.StringVar()  # 结束时间
        self.sub_time_h = tk.StringVar()  # 精确输入小时
        self.sub_time_m = tk.StringVar()  # 精确输入分钟
        self.sub_time_s = tk.StringVar()  # 精确输入秒
        self.sub_start_time_h = tk.StringVar()  # 时长条件输入小时
        self.sub_start_time_m = tk.StringVar()  # 条件输入小时
        self.sub_start_time_s = tk.StringVar()
        self.sub_end_time_h = tk.StringVar()
        self.sub_end_time_m = tk.StringVar()
        self.sub_end_time_s = tk.StringVar()
        self.time_up_sign = tk.StringVar()  # 比较符号 < <=
        self.time_down_sign = tk.StringVar()  # 比较符号 < <=
        self.resolution_w = tk.StringVar()  # 分辨率 宽
        self.resolution_h = tk.StringVar()  # 分辨率 高
        self.resolution_min_w = tk.StringVar()  # 分辨率下限宽
        self.resolution_min_h = tk.StringVar()  # 分辨率下限高
        self.resolution_max_w = tk.StringVar()  # 分辨率上限宽
        self.resolution_max_h = tk.StringVar()  # 分辨率上限高
        self.resolution_up_sign = tk.StringVar()  # 比较符号 < <=
        self.resolution_down_sign = tk.StringVar()  # 比较符号 < <=
        self.rec_flag = tk.BooleanVar()  # 是否递归操作子目录和子文件  True 递归
        self.ext_extend_flag = tk.BooleanVar()  # 对不能字节码识别的文件，是否使用后缀名识别 比如md，ape，文本文件等  True 使用后缀名匹配
        self.resolution_postion_flag = tk.BooleanVar()  # 分辨率位置是否严格一致，True 要求比对视频分辨率宽高必须和输入宽高位置一致，例输入1920*1080 则视频为1080*1920则不符合
        self.unkonw_extend_flag = tk.BooleanVar()  # 结果是否包含未知类型，未收录的私有格式等  True 包含未知类型
        self.rec_flag.set(True)
        self.search_mode.set('name')
        self.dir_flag.set(True)
        self.file_flag.set(True)
        self.reg_flag.set(False)
        self.export_mode.set(1)
        self.want_types = {}  # 想要匹配的文件数据类型 {'want':[], 'refuse':[]}
        self.ext_extend_flag.set(False)
        self.unkonw_extend_flag.set(False)
        self.resolution_postion_flag.set(False)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "搜索文件或目录"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=5, sticky=tk.EW)
        self.f_input_option_1 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option_1.grid(row=0, column=1, columnspan=5, sticky=tk.EW)
        self.f_input_option_2 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option_2.grid(row=1, column=1, columnspan=5, sticky=tk.EW)
        self.f_input_option_3 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option_3.grid(row=2, column=1, columnspan=5, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, pady=5)
        ttk.Radiobutton(self.f_input_option_1, text="文件名称", variable=self.search_mode, command=self.chg_search_mode,
                        value='name').grid(row=0, column=1)
        ttk.Radiobutton(self.f_input_option_1, text="文件大小", variable=self.search_mode, command=self.chg_search_mode,
                        value='size').grid(row=0, column=2)
        ttk.Radiobutton(self.f_input_option_1, text="数据类型", variable=self.search_mode, command=self.chg_search_mode,
                        value='type').grid(row=0, column=3)
        ttk.Radiobutton(self.f_input_option_1, text="路径记录", variable=self.search_mode, command=self.chg_search_mode,
                        value='file').grid(row=0, column=4)
        ttk.Radiobutton(self.f_input_option_1, text="视频时长", variable=self.search_mode, command=self.chg_search_mode,
                        value='5').grid(row=0, column=5)
        ttk.Radiobutton(self.f_input_option_1, text="视频分辨率", variable=self.search_mode, command=self.chg_search_mode,
                        value='6').grid(row=0, column=7)
        ttk.Radiobutton(self.f_input_option_1, text="图片分辨率", variable=self.search_mode, command=self.chg_search_mode,
                        value='7').grid(row=0, column=8)
        ttk.Radiobutton(self.f_input_option_1, text="音频时长", variable=self.search_mode, command=self.chg_search_mode,
                        value='8').grid(row=0, column=6, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option_1, text="文本内容", variable=self.search_mode, command=self.chg_search_mode,
                        value='9').grid(row=0, column=9)
        ttk.Checkbutton(self.f_input_option_2, text="操作目录", variable=self.dir_flag, onvalue=True, offvalue=False,
                        command=self.switch_selection2).grid(row=1, column=4)
        ttk.Checkbutton(self.f_input_option_2, text="操作文件", variable=self.file_flag, onvalue=True, offvalue=False,
                        command=self.switch_selection2).grid(row=1, column=5)
        ttk.Checkbutton(self.f_input_option_2, text="递归", variable=self.rec_flag, onvalue=True, offvalue=False).grid(row=1, column=6)
        self.c_ext_extend = ttk.Checkbutton(self.f_input_option_2, text="后缀名识别", variable=self.ext_extend_flag, onvalue=True, offvalue=False)
        self.c_ext_extend.grid(row=1, column=7)
        self.c_unknow_extend = ttk.Checkbutton(self.f_input_option_2, text="包含未知类型", variable=self.unkonw_extend_flag, onvalue=True, offvalue=False)
        self.c_unknow_extend.grid(row=1, column=8)
        self.c_resolution_postion = ttk.Checkbutton(self.f_input_option_2, text="分辨率位置严格一致", variable=self.resolution_postion_flag, onvalue=True, offvalue=False)
        self.c_resolution_postion.grid(row=1, column=9)
        ttk.Radiobutton(self.f_input_option_2, text="精确搜索", variable=self.reg_flag, value=False, command=self.chg_search_mode).grid(row=1, column=1)
        self.btn_s = ttk.Radiobutton(self.f_input_option_2, text="正则搜索", variable=self.reg_flag, value=True, command=self.chg_search_mode)
        self.btn_s.grid(row=1, column=2)
        ttk.Checkbutton(self.f_input_option_3, text="按时间筛选 ", variable=self.time_flag, onvalue=True, offvalue=False, command=self.switch_selection2).grid(
            row=2, column=1, pady=5)
        self.f_time_elements = ttk.Frame(self.f_input_option_3)  # 按时间过滤的容器
        self.f_time_elements.grid(row=2, column=2, columnspan=10, sticky=tk.EW)
        self.optionChosen = ttk.Combobox(self.f_time_elements, width=8, textvariable=self.time_option)
        self.optionChosen['values'] = ['修改时间', '创建时间', '拍摄时间']
        self.optionChosen.grid(row=0, column=1)
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        self.optionChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_time_elements, text='开始时间:', state=tk.DISABLED).grid(row=0, column=2)
        ttk.Entry(self.f_time_elements, textvariable=self.time_start, width=18, state=tk.DISABLED).grid(row=0, column=3)
        ttk.Label(self.f_time_elements, text='结束时间:', state=tk.DISABLED).grid(row=0, column=4, padx=5)
        ttk.Entry(self.f_time_elements, textvariable=self.time_end, width=18, state=tk.DISABLED).grid(row=0, column=5)
        self.l_input_str = ttk.Label(self.f_input, text='搜索语句: ')
        self.l_input_str.grid(row=3, pady=5, sticky=tk.W)
        self.f_str_input = ttk.Frame(self.f_input)  # 输入搜索语句的容器
        self.f_str_input.grid(row=3, column=1, columnspan=10, sticky=tk.EW)
        self.f_str_input1 = ttk.Frame(self.f_str_input)  # 文件名和文件数据类型输入语句框
        self.f_str_input2 = ttk.Frame(self.f_str_input)  # 按文件大小搜索精确搜索输入语句框
        self.f_str_input3 = ttk.Frame(self.f_str_input)  # 按文件大小搜索条件搜索输入语句框
        self.f_str_input4 = ttk.Frame(self.f_str_input)  # 按路径记录搜索输入语句框
        self.f_str_input5 = ttk.Frame(self.f_str_input)  # 按视频时长搜索精确搜索输入语句框
        self.f_str_input6 = ttk.Frame(self.f_str_input)  # 按视频时长搜索条件搜索输入语句框
        self.f_str_input7 = ttk.Frame(self.f_str_input)  # 按分辨率搜索精确搜索输入语句框
        self.f_str_input8 = ttk.Frame(self.f_str_input)  # 按分辨率搜索条件搜索输入语句框
        # 文件名和文件数据类型输入语句框
        ttk.Entry(self.f_str_input1, textvariable=self.search_str, width=100).grid(row=0, column=0, sticky=tk.EW)
        # 按文件大小精确搜索
        ttk.Label(self.f_str_input2, text='项目大小').grid(row=0, column=3)
        ttk.Label(self.f_str_input2, text='=').grid(row=0, column=4, padx=5)
        ttk.Entry(self.f_str_input2, textvariable=self.search_str, width=25).grid(row=0, column=5)
        ttk.Label(self.f_str_input2, text='字节').grid(row=0, column=6, padx=5)
        # 按文件大小条件搜索
        ttk.Entry(self.f_str_input3, textvariable=self.size_down, width=20).grid(row=0, column=0)
        self.c_size_down_unit = ttk.Combobox(self.f_str_input3, width=4, textvariable=self.size_down_unit)  # 单位
        self.c_size_down_unit['values'] = ['TB', 'GB', 'MB', 'KB', '字节']
        self.c_size_down_unit.grid(row=0, column=1, padx=5)
        self.c_size_down_unit.current(2)  # 设置初始显示值，值为元组['values']的下标
        self.c_size_down_unit.config(state='readonly')  # 设为只读模式
        self.c_size_down_sign = ttk.Combobox(self.f_str_input3, width=3, textvariable=self.size_down_sign)
        self.c_size_down_sign['values'] = ['<', '<=']
        self.c_size_down_sign.grid(row=0, column=2, padx=5)
        self.c_size_down_sign.current(1)  # 设置初始显示值，值为元组['values']的下标
        self.c_size_down_sign.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_str_input3, text='项目大小').grid(row=0, column=3, padx=5)
        self.c_size_up_sign = ttk.Combobox(self.f_str_input3, width=3, textvariable=self.size_up_sign)  # 比较符号
        self.c_size_up_sign['values'] = ['<', '<=']
        self.c_size_up_sign.grid(row=0, column=4, padx=5)
        self.c_size_up_sign.current(1)  # 设置初始显示值，值为元组['values']的下标
        self.c_size_up_sign.config(state='readonly')  # 设为只读模式
        ttk.Entry(self.f_str_input3, textvariable=self.size_up, width=20).grid(row=0, column=5, sticky=tk.W)
        self.c_size_up_unit = ttk.Combobox(self.f_str_input3, width=4, textvariable=self.size_up_unit)  # 大小单位
        self.c_size_up_unit['values'] = ['TB', 'GB', 'MB', 'KB', '字节']
        self.c_size_up_unit.grid(row=0, column=6, padx=5)
        self.c_size_up_unit.current(2)  # 设置初始显示值，值为元组['values']的下标
        self.c_size_up_unit.config(state='readonly')  # 设为只读模式
        # 根据路径记录搜索输入语句框
        ttk.Entry(self.f_str_input4, textvariable=self.search_str, width=90).grid(row=0, column=0, sticky=tk.W)
        ttk.Button(self.f_str_input4, text="浏览", command=self.selectPath3).grid(row=0, column=1)
        self.chg_search_mode()  # 设置搜索语句输入框
        # 按视频时长精确搜索
        ttk.Label(self.f_str_input5, text='视频时长').grid(row=0, column=3, sticky=tk.W)
        ttk.Label(self.f_str_input5, text='=').grid(row=0, column=4, padx=5)
        ttk.Entry(self.f_str_input5, textvariable=self.sub_time_h, width=6).grid(row=0, column=5, sticky=tk.W)
        ttk.Label(self.f_str_input5, text=':').grid(row=0, column=6, sticky=tk.W)
        ttk.Entry(self.f_str_input5, textvariable=self.sub_time_m, width=6).grid(row=0, column=7, sticky=tk.W)
        ttk.Label(self.f_str_input5, text=':').grid(row=0, column=8, sticky=tk.W)
        ttk.Entry(self.f_str_input5, textvariable=self.sub_time_s, width=6).grid(row=0, column=9, sticky=tk.W)
        # 按视频时长条件搜索
        ttk.Entry(self.f_str_input6, textvariable=self.sub_start_time_h, width=6).grid(row=0, column=5, sticky=tk.W)
        ttk.Label(self.f_str_input6, text=':').grid(row=0, column=6, sticky=tk.W)
        ttk.Entry(self.f_str_input6, textvariable=self.sub_start_time_m, width=6).grid(row=0, column=7, sticky=tk.W)
        ttk.Label(self.f_str_input6, text=':').grid(row=0, column=8, sticky=tk.W)
        ttk.Entry(self.f_str_input6, textvariable=self.sub_start_time_s, width=6).grid(row=0, column=9, sticky=tk.W)
        self.c_time_down_sign = ttk.Combobox(self.f_str_input6, width=3, textvariable=self.time_down_sign)
        self.c_time_down_sign['values'] = ['<', '<=']
        self.c_time_down_sign.grid(row=0, column=10, padx=5)
        self.c_time_down_sign.current(1)  # 设置初始显示值，值为元组['values']的下标
        self.c_time_down_sign.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_str_input6, text='项目时长').grid(row=0, column=11, sticky=tk.W)
        self.c_time_up_sign = ttk.Combobox(self.f_str_input6, width=3, textvariable=self.time_up_sign)
        self.c_time_up_sign['values'] = ['<', '<=']
        self.c_time_up_sign.grid(row=0, column=12, padx=5)
        self.c_time_up_sign.current(1)  # 设置初始显示值，值为元组['values']的下标
        self.c_time_up_sign.config(state='readonly')  # 设为只读模式
        ttk.Entry(self.f_str_input6, textvariable=self.sub_end_time_h, width=6).grid(row=0, column=13, sticky=tk.W)
        ttk.Label(self.f_str_input6, text=':').grid(row=0, column=14, sticky=tk.W)
        ttk.Entry(self.f_str_input6, textvariable=self.sub_end_time_m, width=6).grid(row=0, column=15, sticky=tk.W)
        ttk.Label(self.f_str_input6, text=':').grid(row=0, column=16, sticky=tk.W)
        ttk.Entry(self.f_str_input6, textvariable=self.sub_end_time_s, width=6).grid(row=0, column=17, sticky=tk.W)
        # 按分辨率精确搜索
        ttk.Label(self.f_str_input7, text='分辨率').grid(row=0, column=3, sticky=tk.W)
        ttk.Label(self.f_str_input7, text='=').grid(row=0, column=4, padx=5)
        ttk.Entry(self.f_str_input7, textvariable=self.resolution_w, width=10).grid(row=0, column=5, sticky=tk.W)
        ttk.Label(self.f_str_input7, text='x').grid(row=0, column=6, sticky=tk.W)
        ttk.Entry(self.f_str_input7, textvariable=self.resolution_h, width=10).grid(row=0, column=7, sticky=tk.W)
        # 按分辨率条件搜索
        ttk.Entry(self.f_str_input8, textvariable=self.resolution_min_w, width=10).grid(row=0, column=5, sticky=tk.W)
        ttk.Label(self.f_str_input8, text='x').grid(row=0, column=6, sticky=tk.W)
        ttk.Entry(self.f_str_input8, textvariable=self.resolution_min_h, width=10).grid(row=0, column=7, sticky=tk.W)
        self.c_resolution_down_sign = ttk.Combobox(self.f_str_input8, width=3, textvariable=self.resolution_down_sign)
        self.c_resolution_down_sign['values'] = ['<', '<=']
        self.c_resolution_down_sign.grid(row=0, column=10, padx=5)
        self.c_resolution_down_sign.current(1)  # 设置初始显示值，值为元组['values']的下标
        self.c_resolution_down_sign.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_str_input8, text='分辨率').grid(row=0, column=11, sticky=tk.W)
        self.c_resolution_up_sign = ttk.Combobox(self.f_str_input8, width=3, textvariable=self.resolution_up_sign)
        self.c_resolution_up_sign['values'] = ['<', '<=']
        self.c_resolution_up_sign.grid(row=0, column=12, padx=5)
        self.c_resolution_up_sign.current(1)  # 设置初始显示值，值为元组['values']的下标
        self.c_resolution_up_sign.config(state='readonly')  # 设为只读模式
        ttk.Entry(self.f_str_input8, textvariable=self.resolution_max_w, width=10).grid(row=0, column=15, sticky=tk.W)
        ttk.Label(self.f_str_input8, text='x').grid(row=0, column=16, sticky=tk.W)
        ttk.Entry(self.f_str_input8, textvariable=self.resolution_max_h, width=10).grid(row=0, column=17, sticky=tk.W)
        ttk.Button(self.f_input, text="搜索", command=self.deal_search).grid(row=3, column=4)
        # 展示结果
        scrolW = 120
        scrolH = 32
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, column=0, sticky=tk.NSEW)
        self.f_filter = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_filter.grid(row=1, sticky=tk.EW)
        self.f_bottom_option = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_bottom_option.grid(row=2, sticky=tk.EW)
        self.f_bottom_option2 = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_bottom_option2.grid(row=3, sticky=tk.EW)
        # 过滤功能
        ttk.Label(self.f_filter, text='过滤:').grid(row=0, sticky=tk.EW, pady=5)
        ttk.Radiobutton(self.f_filter, text="选中", variable=self.filter_mode, value="select").grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_filter, text="排除", variable=self.filter_mode, value="exclude").grid(row=0, column=2, sticky=tk.W)
        self.filter_mode.set("exclude")
        ttk.Entry(self.f_filter, textvariable=self.filter_str).grid(row=0, column=3, sticky=tk.EW)
        ttk.Button(self.f_filter, text="过滤", command=self.do_filter).grid(row=0, column=4)
        self.btn_restore_meta = ttk.Button(self.f_filter, text="撤销过滤", command=self.restore_meta_result, state=tk.DISABLED)
        self.btn_restore_meta.grid(row=0, column=5, sticky=tk.W)
        ttk.Label(self.f_bottom_option, text='导出方式:').grid(row=0, sticky=tk.EW)
        ttk.Radiobutton(self.f_bottom_option, text="复制", variable=self.deal_mode, value="copy").grid(row=0, column=1, padx=2)
        ttk.Radiobutton(self.f_bottom_option, text="剪切", variable=self.deal_mode, value="move").grid(row=0, column=2, padx=2)
        self.deal_mode.set("copy")
        ttk.Label(self.f_bottom_option, text='  导出模式:').grid(row=0, column=3, padx=5)
        ttk.Radiobutton(self.f_bottom_option, text="导出到单级目录并附带目录描述", variable=self.export_mode, value=1).grid(row=0, column=4, padx=2)
        ttk.Radiobutton(self.f_bottom_option, text="导出到单级目录", variable=self.export_mode, value=2).grid(row=0, column=5, padx=2)
        ttk.Radiobutton(self.f_bottom_option, text="保持原目录层次", variable=self.export_mode, value=3).grid(row=0, column=6, padx=2)
        ttk.Label(self.f_bottom_option, text='  遇重名:').grid(row=0, column=7, padx=5)
        # ttk.Radiobutton(self.f_bottom_option_2, text="询问", variable=self.same_file_option, value='ask').grid(row=0, column=8)
        ttk.Radiobutton(self.f_bottom_option, text="覆盖", variable=self.same_file_option, value='overwrite').grid(row=0, column=9, padx=2)
        ttk.Radiobutton(self.f_bottom_option, text="跳过", variable=self.same_file_option, value='skip').grid(row=0, column=10, padx=2)
        self.same_file_option.set('skip')
        # 设置拉伸自适应
        self.f_filter.grid_columnconfigure(3, weight=1)
        self.f_bottom.grid_columnconfigure(0, weight=1)
        self.f_bottom_option2.grid_columnconfigure(1, weight=1)
        ttk.Label(self.f_bottom_option2, text='导出路径: ').grid(row=3, pady=5)
        ttk.Entry(self.f_bottom_option2, textvariable=self.dst_dir).grid(row=3, column=1, columnspan=3,sticky=tk.EW)
        ttk.Button(self.f_bottom_option2, text="浏览", command=self.selectPath2).grid(row=3, column=4)
        ttk.Button(self.f_bottom_option2, text="文件覆盖风险检测", command=self.check_files_overwrite).grid(row=4, column=3,sticky=tk.E)
        ttk.Button(self.f_bottom_option2, text="导出", command=self.run).grid(row=4, column=4)
        self.invoke_filter_time()  # 设置时间过滤组件激活状态
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def chg_search_mode(self):
        """用于修改不同搜索模式的输入组件"""
        for item in [self.f_str_input1, self.f_str_input2, self.f_str_input3, self.f_str_input4, 
                     self.f_str_input5, self.f_str_input6, self.f_str_input7, self.f_str_input8]:  # 先清空原区域的组件，方便设置新布局
            item.grid_forget()
        # self.search_str.set('')
        # self.size_up.set(0)
        # self.size_down.set(0)
        search_mode = self.search_mode.get()  # 搜索模式

        if search_mode == 'type':
            self.c_ext_extend.config(state=tk.NORMAL)
            self.c_unknow_extend.config(state=tk.NORMAL)
        else:
            self.c_ext_extend.config(state=tk.DISABLED)
            self.c_unknow_extend.config(state=tk.DISABLED)
        if search_mode in ('6', '7'):
            self.c_resolution_postion.config(state=tk.NORMAL)
        else:
            self.c_resolution_postion.config(state=tk.DISABLED)
        # 设置单选框按钮内容和搜索语句标签
        if search_mode in ('size', '5', '6', '7'):
            self.btn_s.config(text='条件搜索')
        elif search_mode == "file":
            self.btn_s.config(text="模糊搜索")
        else:
            self.btn_s.config(text='正则搜索')
        if search_mode == 'file':
            self.l_input_str.config(text='文件路径: ')
        else:
            self.l_input_str.config(text='搜索语句: ')
        # 设置搜索语句输入组件
        if search_mode in ['name', 'type', '9']:  # 按文件名搜索
            self.f_str_input1.grid(row=0, column=0, sticky=tk.W)
        elif search_mode == 'file':  # “根据记录文件搜索搜索”
            self.f_str_input4.grid(row=0, column=0, sticky=tk.W)
        elif search_mode == 'size':  # 按文件大小搜索
            if self.reg_flag.get() is True:  # 条件匹配
                self.f_str_input3.grid(row=0, column=0, sticky=tk.W)
            else:  # 精确匹配
                self.f_str_input2.grid(row=0, column=0, sticky=tk.W)
        elif search_mode in ('5', '8'):  # 按视频时长搜索
            if self.reg_flag.get() is True:  # 条件匹配
                self.f_str_input6.grid(row=0, column=0, sticky=tk.W)
            else:  # 精确匹配
                self.f_str_input5.grid(row=0, column=0, sticky=tk.W)
        elif search_mode in ('6', '7'):  # 按分辨率搜索
            if self.reg_flag.get() is True:  # 条件匹配
                self.f_str_input8.grid(row=0, column=0, sticky=tk.W)
            else:  # 精确匹配
                self.f_str_input7.grid(row=0, column=0, sticky=tk.W)

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        self.all_children(self.f_bottom, self.lock_elements)
        for element in self.lock_elements:
            element.config(state=tk.DISABLED)

    def selectPath1(self):
        self.clear()
        path_ = askdirectory()
        self.src_dir.set(path_)

    def selectPath3(self):
        """用于选择记录文件名或路径的txt"""
        path_ = askopenfilename()
        self.search_str.set(path_)

    def clear(self):
        self.record_path = None
        self.scr.delete(1.0, tk.END)
        self.meta_result = {'files': [], 'dirs': []}  # 完整搜索的结果，即最全的搜索集  搜索到的结果
        self.result = {'files': [], 'dirs': []}  # 用于储存文件操作的搜索结果  过滤之后进行文件复制移动的文件信息

    @log_error
    def check_files_overwrite(self):
        """用来检测目标目录路径是否存在同名文件，防止数据覆盖损失"""
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        search_path = self.src_dir.get()
        save_path = self.dst_dir.get()
        export_mode = self.export_mode.get()
        danger_dict = common_utils.check_files_overwrite_danger(self.result, search_path, save_path, export_mode)
        if len(danger_dict):
            self.scr.insert(tk.END, '\n检测到共有 %s 个文件/目录有数据覆盖风险！该文件源路径如下：\n' % len(danger_dict))
            for old_path in danger_dict:
                self.scr.insert(tk.END, '\t%s\n' % old_path)
            mBox.showwarning("警告", '检测到共有 %s 个文件/目录有数据覆盖风险！' % len(danger_dict))
        else:
            mBox.showinfo("检测完成", "本次文件操作无数据覆盖风险！")

    @deal_running_task_arg('搜索文件或目录')
    def do_search(self):
        """实际搜索操作"""
        search_mode = self.search_mode.get()
        if search_mode == "name":  # 按文件名搜索
            self.search_by_name()
        elif search_mode == 'file':
            self.search_by_file()
        elif search_mode == 'type':
            self.search_by_type()
        elif search_mode == 'size':  # 按文件大小搜索
            self.search_by_size()
        elif search_mode == '5':  # 按视频时长搜索
            self.search_by_video_duration()
        elif search_mode == '6':  # 按视频分辨率搜索
            self.search_by_video_resolution()
        elif search_mode == '7':  # 按图片分辨率搜索
            self.search_by_image_resolution()
        elif search_mode == '8':  # 按视频时长搜索
            self.search_by_audio_duration()
        elif search_mode == '9':  # 按视频时长搜索
            self.search_by_txt_content()
        # 按时间过滤结果
        self.do_time_filter()
        # 显示结果
        self.show_result()

    def get_files(self):
        """遍历文件和目录获取路径信息"""
        src_path = common_utils.check_path(self.src_dir.get())
        res = {"dirs": [], "files": []}
        if self.dir_flag.get():
            if self.rec_flag.get() is False:   # 不递归
                tmp_list = os.listdir(src_path)
                for item in tmp_list:
                    _path = os.path.join(src_path, item)
                    if os.path.isdir(_path):
                        res['dirs'].append(_path)
            else:
                for root, dirs, files in os.walk(src_path):
                    for item in dirs:
                        res['dirs'].append(os.path.join(root, item))
        if self.file_flag.get():
            if self.rec_flag.get() is False:  # 不递归
                tmp_list = os.listdir(src_path)
                for item in tmp_list:
                    _path = os.path.join(src_path, item)
                    if os.path.isfile(_path):
                        res['files'].append(_path)
            else:
                for root, dirs, files in os.walk(src_path):
                    for item in files:
                        res['files'].append(os.path.join(root, item))
        return res

    def search_by_name(self):
        """文件名搜索"""
        search_str = self.search_str.get()
        reg_flag = self.reg_flag.get()
        res = self.get_files()  # 遍历路径获取文件信息和文件夹信息
        if reg_flag:
            # 正则匹配
            if search_str:  # 有输入
                search_str = search_str.strip()
                for _path in res['files']:
                    _name = os.path.basename(_path)
                    if re.search(search_str, _name, flags=re.I):  # flags修饰，re.I 忽略大小写
                        self.meta_result["files"].append(_path)
                for _path in res['dirs']:
                    _name = os.path.basename(_path)
                    if re.search(search_str, _name, flags=re.I):  # flags修饰，re.I 忽略大小写
                        self.meta_result["dirs"].append(_path)
        else:
            # 精确匹配
            if search_str:
                search_str = search_str.strip()
                for _path in res['files']:
                    _name = os.path.basename(_path)
                    if search_str in _name:
                        self.meta_result["files"].append(_path)
                for _path in res['dirs']:
                    _name = os.path.basename(_path)
                    if search_str in _name:
                        self.meta_result["dirs"].append(_path)

    def search_by_type(self):
        """文件数据类型搜索"""
        search_str = self.search_str.get().strip()
        self.want_types = {'want':[], 'refuse':[]}  # 清除之前数据
        ext_extend_flag = self.ext_extend_flag.get()  # True 对字节码无法识别的文件按后缀名识别
        unkonw_extend_flag = self.unkonw_extend_flag.get()  # True 包含未知数据类型
        func = common_utils.get_files_with_filetype_extended if ext_extend_flag else common_utils.get_files_with_filetype
        res = func(self.src_dir.get())
        # logger.debug(res)
        if search_str:
            search_str = search_str.replace('，', ',').replace('【', '[').replace('】', ']').replace('.', '')  # 兼容用户输入.jpg 这种格式
            # 想要匹配的数据类型
            # 解析排除项
            is_refuse_all = True if search_str == '^[*]' else False  # 排除所有
            matchObj = re.search(r"\^\[(.+)\]", search_str)
            if matchObj:
                self.want_types['refuse'] = [i.strip().lower() for i in matchObj.group(1).split(',')]
            # 解析匹配项
            want_str = re.sub(r"\^\[.+\]", '', search_str)  # 去除排除项
            self.want_types['want'] = [i.strip().lower() for i in want_str.strip().split(',')]
            is_want_all = True if '*' in want_str else False  # 匹配所有
            logger.debug(self.want_types)
            # 过滤掉排除项
            for _path, type_info in res.items():
                if not type_info:  # 文件时无法识别的数据类型
                    if unkonw_extend_flag:  # 结果是否无法识别数据类型
                        self.meta_result['files'].append(_path)
                else:  # 文件可以识别数据类型
                    if is_refuse_all:  # 排除所有
                        continue
                    _cate = type_info.get('mime').split('/')[0]
                    _extension = type_info.get('extension')
                    _mime_extension = type_info.get('mime').split('/')[-1]
                    for item in [_cate, _extension, _mime_extension]:
                        if item in self.want_types['refuse']:
                            break
                        if is_want_all:  # 匹配所有
                            self.meta_result['files'].append(_path)
                            break
                        if item in self.want_types['want']:
                            self.meta_result['files'].append(_path)
                            break

    def search_by_file(self):
        """根据记录文件名或路径的txt搜索"""
        txt_path = self.search_str.get()
        reg_flag = self.reg_flag.get()
        # with open(txt_path, 'r', encoding='utf-8') as f:
        #     content = f.read().splitlines()
        content = common_utils.read_file(txt_path)  # 可以自动匹配文本编码
        res = self.get_files()  # 遍历路径获取文件信息和文件夹信息
        reg_strs = [i.strip() for i in content]
        if reg_flag:
            # 正则匹配
            for _path in res['files']:
                for reg_str in reg_strs:
                    if re.search(reg_str, _path):
                        self.meta_result["files"].append(_path)
                        continue
            for _path in res['dirs']:
                for reg_str in reg_strs:
                    if re.search(reg_str, _path):
                        self.meta_result["dirs"].append(_path)
                        continue
        else:
            # 精确匹配
            for _path in res['files']:
                if _path in content:
                    self.meta_result["files"].append(_path)
                    continue
                _name = os.path.basename(_path)
                if _name in content:
                    self.meta_result["files"].append(_path)
            for _path in res['dirs']:
                if _path in content:
                    self.meta_result["dirs"].append(_path)
                    continue
                _name = os.path.basename(_path)
                if _name in content:
                    self.meta_result["dirs"].append(_path)

    def search_by_size(self):
        """大小搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        reg_flag = self.reg_flag.get()
        dir_flag = self.dir_flag.get()
        file_flag = self.file_flag.get()
        file_dict = {}  # 用于储存文件信息,格式"{"file_path": size,...}"
        dir_dict = {}  # 用于储存目录信息,格式"{"dir_path":dir_size,...}"
        # 遍历获取文件信息
        if self.rec_flag.get() is False:  # 不递归
            tmp_list = os.listdir(src_path)
            for item in tmp_list:
                _path = os.path.join(src_path, item)
                if os.path.isdir(_path):
                    if dir_flag:
                        _size = 0
                        # 计算文件夹大小
                        for root, dirs, files in os.walk(_path):
                            for file_name in files:
                                # 获取文件信息
                                _size += os.path.getsize(os.path.join(root, file_name))
                        dir_dict[_path] = _size
                else:
                    file_dict[_path] = os.path.getsize(_path)
        else:  # 递归
            for root, dirs, files in os.walk(src_path):
                for item in files:
                    # 获取文件信息
                    _path = os.path.join(root, item)
                    _size = os.path.getsize(_path)
                    file_dict[_path] = _size
                for item in dirs:  # 创建目录统计信息
                    _path = os.path.join(root, item)
                    if _path not in dir_dict:
                        dir_dict[_path] = 0

            # 统计目录大小
            if dir_flag:
                for _path in file_dict:  # 将每个文件的大小统计到它的各级父目录大小中
                    _tmp_dir = _path
                    while True:
                        _par_dir = os.path.dirname(_tmp_dir)
                        _tmp_dir = _par_dir
                        # if os.path.samefile(_par_dir, src_path):  # 是否是同一目录
                        #     break
                        if len(_par_dir) <= len(src_path):  # 判断是否为子目录
                            break
                        if _par_dir in dir_dict:  # 统计父目录文件大小
                            dir_dict[_par_dir] += file_dict[_path]
                        else:
                            dir_dict[_par_dir] = file_dict[_path]
            # logger.debug(dir_dict)

        # 比对匹配结果
        if reg_flag is False:
            # 精确匹配
            search_str = self.search_str.get()  # 输入的大小
            if search_str:  # 有输入
                search_str = search_str.strip().replace(',', '').replace('，', '')
                if re.match(r"\d+$", search_str):  # 正则匹配纯数字
                    search_str = int(search_str)
                    if file_flag:
                        for _path in file_dict:
                            if search_str == file_dict[_path]:
                                self.meta_result['files'].append(_path)
                    if dir_flag:
                        for _path in dir_dict:
                            if search_str == dir_dict[_path]:
                                self.meta_result['dirs'].append(_path)
        else:  # 条件匹配
            # 检查输入
            size_down = self.size_down.get().replace(',', '').replace('，', '')
            size_up = self.size_up.get().replace(',', '').replace('，', '')
            try:
                size_up = float(size_up) if size_up else 0
                size_down = float(size_down) if size_down else 0
            except:
                mBox.showerror('错误', '输入的文件大小格式有误! 请检查!')
                return
            # 匹配文件
            if file_flag:
                self.advance_comp_size('files', file_dict)
            # 匹配目录
            if dir_flag:
                self.advance_comp_size('dirs', dir_dict)

    def search_by_video_duration(self):
        """根据视频时长搜索文件"""
        self.search_by_duration("video")

    def search_by_audio_duration(self):
        """根据音频时长搜索文件"""
        self.search_by_duration("audio")

    def search_by_duration(self, media_type):
        """按视频/音频时长搜索
        media_type 文件类型 'video', 'audio'
        """
        src_path = common_utils.check_path(self.src_dir.get())
        path_list = common_utils.get_files_by_filetype(src_path, media_type)  # 遍历获取文件路径集合
        if media_type == 'video':
            func_get_duration = common_utils.get_video_info
        else:
            func_get_duration = common_utils.get_audio_info

        if self.reg_flag.get() is False:
            # 精确匹配
            sub_time_h = common_utils.get_float(self.sub_time_h.get(), 0)
            sub_time_m = common_utils.get_float(self.sub_time_m.get(), 0)
            sub_time_s = common_utils.get_float(self.sub_time_s.get(), 0)
            duration_input = sub_time_h * 3600 + sub_time_m *60 + sub_time_s 
            for _path in path_list:
                res = func_get_duration(_path)
                if int(duration_input) == int(res["duration_sec"]):
                    self.meta_result["files"].append(_path)
        else:  # 条件匹配
            sub_start_time_h = common_utils.get_float(self.sub_start_time_h.get(), 0)
            sub_start_time_m = common_utils.get_float(self.sub_start_time_m.get(), 0)
            sub_start_time_s = common_utils.get_float(self.sub_start_time_s.get(), 0)
            duration_start_input = sub_start_time_h * 3600 + sub_start_time_m * 60 + sub_start_time_s
            sub_end_time_h = common_utils.get_float(self.sub_end_time_h.get(), 0)
            sub_end_time_m = common_utils.get_float(self.sub_end_time_m.get(), 0)
            sub_end_time_s = common_utils.get_float(self.sub_end_time_s.get(), 0)
            duration_end_input = sub_end_time_h * 3600 + sub_end_time_m * 60 + sub_end_time_s
            time_up_sign = self.time_up_sign.get()
            time_down_sign = self.time_down_sign.get()
            # 设置判断函数
            if duration_end_input == 0:  # 大小上限无输入
                if time_down_sign == '<=':
                    func = lambda x, y, z: x <= y
                else:
                    func = lambda x, y, z: x < y
            else:
                if duration_start_input > duration_end_input:  # 上限有输入，但是下限比上限高
                    return
                if (time_down_sign == '<=') and (time_up_sign == '<='):
                    func = lambda x, y, z: x <= y <= z
                elif (time_down_sign == '<=') and (time_up_sign == '<'):
                    func = lambda x, y, z: x <= y < z
                elif (time_down_sign == '<') and (time_up_sign == '<='):
                    func = lambda x, y, z: x < y <= z
                else:
                    func = lambda x, y, z: x < y < z
            # 进行判断   
            for _path in path_list:
                res = func_get_duration(_path)
                if func(duration_start_input, float(res["duration_sec"]), duration_end_input):
                    self.meta_result["files"].append(_path)

    def search_by_video_resolution(self):
        """按视频分辨率搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        file_list = common_utils.get_files_by_filetype(src_path, 'video')  # 遍历获取视频文件路径集合
        func_get_resolution = common_utils.get_video_resolution
        self.search_by_resolution(file_list, func_get_resolution)

    def search_by_image_resolution(self):
        """按图片分辨率搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        file_list = common_utils.get_files_by_filetype(src_path, 'image')  # 遍历获取视频文件路径集合
        func_get_resolution = common_utils.get_image_resolution
        self.search_by_resolution(file_list, func_get_resolution)

    def search_by_resolution(self, file_list, func_get_resolution):
        """按分辨率搜索"""
        resolution_postion_flag = self.resolution_postion_flag.get()  # True 严格分辨率位置
        if self.reg_flag.get() is False:
            # 精确匹配
            resolution_w = common_utils.get_int(self.resolution_w.get(), 0)
            resolution_h = common_utils.get_int(self.resolution_h.get(), 0)
            # 设置判断函数
            if resolution_postion_flag:
                func = lambda x, y, z, k: (x == z) and (y == k)
            else:
                func = lambda x, y, z, k: (x + y) == (z + k)
            # 判断
            for _path in file_list:
                res = func_get_resolution(_path)  # 获取元数据信息
                if func(res['width'], res['height'], resolution_w, resolution_h):
                    self.meta_result["files"].append(_path)

        else:  # 条件匹配
            resolution_min_w = common_utils.get_int(self.resolution_min_w.get(), 0)
            resolution_min_h = common_utils.get_int(self.resolution_min_h.get(), 0)
            resolution_max_w = common_utils.get_int(self.resolution_max_w.get(), 0)
            resolution_max_h = common_utils.get_int(self.resolution_max_h.get(), 0)
            resolution_up_sign = self.resolution_up_sign.get()
            resolution_down_sign = self.resolution_down_sign.get()
            # 设置判断函数
            if (resolution_max_w + resolution_max_h) == 0:  # 大小上限无输入
                if resolution_down_sign == '<=':
                    if resolution_postion_flag:
                        func = lambda a, b, c, d, e, f: (a <= c) and (b <= d)
                    else:
                        func = lambda a, b, c, d, e, f: (a + b) <= (c + d)
                else:
                    if resolution_postion_flag:
                        func = lambda a, b, c, d, e, f: (a < c) and (b < d)
                    else:
                        func = lambda a, b, c, d, e, f: (a + b) < (c + d)
            else:
                if (resolution_min_w + resolution_min_h) > (resolution_max_w + resolution_max_h):  # 大小上限有输入，但是下限比上限高
                    return
                if (resolution_down_sign == '<=') and (resolution_up_sign == '<='):
                    if resolution_postion_flag:
                        func = lambda a, b, c, d, e, f: (a <= c) and (b <= d) and (c <= e) and (d <= f)
                    else:
                        func = lambda a, b, c, d, e, f: (a + b) <= (c + d) <= (e + f)
                elif (resolution_down_sign == '<=') and (resolution_up_sign == '<'):
                    if resolution_postion_flag:
                        func = lambda a, b, c, d, e, f: (a <= c) and (b <= d) and (c < e) and (d < f)
                    else:
                        func = lambda a, b, c, d, e, f: (a + b) <= (c + d) < (e + f)
                elif (resolution_down_sign == '<') and (resolution_up_sign == '<='):
                    if resolution_postion_flag:
                        func = lambda a, b, c, d, e, f: (a < c) and (b < d) and (c <= e) and (d <= f)
                    else:
                        func = lambda a, b, c, d, e, f: (a + b) < (c + d) <= (e + f)
                else:
                    if resolution_postion_flag:
                        func = lambda a, b, c, d, e, f: (a < c) and (b < d) and (c < e) and (d < f)
                    else:
                        func = lambda a, b, c, d, e, f: (a + b) < (c + d) < (e + f)
            # 判断
            for _path in file_list:
                res = func_get_resolution(_path)  # 获取元数据信息
                if func(resolution_min_w, resolution_min_h, res['width'], res['height'], resolution_max_w, resolution_max_h):
                    self.meta_result["files"].append(_path)

    def search_by_txt_content(self):
        """根据输入搜索符合内容的文本文件"""
        src_path = common_utils.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        reg_flag = self.reg_flag.get()
        file_list = common_utils.get_txt_files(src_path)  # 遍历路径获取文本文件信息
        if not search_str:  # 无输入
            return
        for _path in file_list:
            content = common_utils.get_txt_content(_path)  # 读取文本内容
            if reg_flag:  # 正则匹配
                if re.search(search_str, content, flags=re.I):  # flags修饰，re.I 忽略大小写
                    self.meta_result["files"].append(_path)
            else:  # 精确匹配
                if search_str in content:
                    self.meta_result["files"].append(_path)

    def advance_comp_size(self, obj_str, obj_dict):
        """文件大小条件匹配"""
        size_down = self.size_down.get().replace(',', '').replace('，', '')
        size_up = self.size_up.get().replace(',', '').replace('，', '')
        # logger.debug('size_up: {}\nsize_down: {}'.format(size_up, size_down))
        try:
            size_up = float(size_up) if size_up else 0
            size_down = float(size_down) if size_down else 0
        except:
            # mBox.showerror('格式错误！', '输入的文件大小格式有误！请检查！')
            return
        # logger.debug('size_up: {}\nsize_down: {}'.format(size_up, size_down))
        size_down_unit = self.size_down_unit.get()
        size_up_unit = self.size_up_unit.get()
        size_up_sign = self.size_up_sign.get()
        size_down_sign = self.size_down_sign.get()
        size_unit_dict = {'B': 1, '字节': 1, 'KB': 1024, 'MB': 1024 * 1024, 'GB': 1024 * 1024 * 1024,
                          'TB': 1024 * 1024 * 1024 * 1024}
        size_up *= size_unit_dict[size_up_unit]
        size_down *= size_unit_dict[size_down_unit]
        # 设置判断函数
        if size_up == 0:  # 大小上限无输入
            if size_down_sign == '<=':
                func = lambda x, y, z: x <= y
            else:
                func = lambda x, y, z: x < y
        else:
            if size_down > size_up:  # 大小上限有输入，但是下限比上限高
                return
            if (size_down_sign == '<=') and (size_up_sign == '<='):
                func = lambda x, y, z: x <= y <= z
            elif (size_down_sign == '<=') and (size_up_sign == '<'):
                func = lambda x, y, z: x <= y < z
            elif (size_down_sign == '<') and (size_up_sign == '<='):
                func = lambda x, y, z: x < y <= z
            else:
                func = lambda x, y, z: x < y < z
        # 进行判断
        for _path in obj_dict:
            _size = obj_dict[_path]
            if func(size_down, _size, size_up):
                self.meta_result[obj_str].append(_path)

    def deal_search(self):
        """为搜索操作新开一个线程,避免高耗时操作阻塞GUI主线程"""
        self.scr.delete(1.0, tk.END)  # 清空文本框
        self.meta_result = {'files': [], 'dirs': []}
        self.result = {'files': [], 'dirs': []}
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.do_search)
        t.daemon = True
        t.start()

    @log_error
    def do_filter(self):
        """过滤结果"""
        filter_mode = self.filter_mode.get()
        filter_str = self.filter_str.get()
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
        time_option = self.time_option.get()  # 修改时间   创建时间  照片拍摄时间
        time_start = self.time_start.get()
        time_end = self.time_end.get()
        time_start = common_utils.changeStrToTime(time_start)
        time_end = common_utils.changeStrToTime(time_end)
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
                timestamp = self.get_file_time(_path, time_option)
                if timestamp:
                    if time_start <= timestamp <= time_end:
                        self.result['files'].append(_path)
        if dir_flag is True:
            for _path in self.meta_result['dirs']:
                timestamp = self.get_file_time(_path, time_option)
                if timestamp:
                    if time_start <= timestamp <= time_end:
                        self.result['dirs'].append(_path)

    @staticmethod
    def get_file_time(file_path, time_option):
        """获取文件的修改时间、创建时间、或者拍摄时间
        time_option  # 修改时间   创建时间  照片拍摄时间
        """
        timestamp = None
        if time_option == '修改时间':
            timestamp = os.path.getmtime(file_path)
        elif time_option == '创建时间':
            timestamp = os.path.getctime(file_path)
        else:  # 获取拍摄时间
            date_information = common_utils.get_media_encoded_date(file_path)
            if date_information:  # 转换为时间戳
                timestamp = time.mktime(time.strptime(date_information, r'%Y-%m-%d %H:%M:%S'))
        return timestamp

    @log_error
    def show_result(self):
        """显示结果"""
        self.scr.delete(1.0, "end")
        search_mode = self.search_mode.get()
        reg_flag = self.reg_flag.get()
        search_str = self.search_str.get()
        file_flag = self.file_flag.get()
        dir_flag = self.dir_flag.get()
        time_flag = self.time_flag.get()  # 是否按时间过滤
        time_option = self.time_option.get()  # 修改时间   创建时间  照片拍摄时间
        time_start = self.time_start.get()
        time_end = self.time_end.get()
        time_start = common_utils.changeStrToTime(time_start)
        time_end = common_utils.changeStrToTime(time_end)
        file_count = len(self.result["files"]) if file_flag else 0  # 文件数
        dir_count = len(self.result["dirs"]) if dir_flag else 0  # 文件夹数
        # logger.debug("file_flag: %s, dir_flag: %s" % (file_flag, dir_flag))
        tmp_msg = '搜索模式：'
        if search_mode == 'name':
            tmp_msg += '"按文件名搜索", 匹配方式："正则匹配", ' if reg_flag else '"按文件名搜索", 匹配方式："精确匹配", '
            tmp_msg += '搜索语句："%s"' % search_str
        elif search_mode == 'file':
            tmp_msg += '"根据文件记录搜索"\n'
            tmp_msg += '记录文件路径："%s"' % search_str
        elif search_mode == 'type':
            tmp_msg += '按文件数据类型搜索 \n'
            if re.sub('^[.+]', '', search_str) == '*':
                tmp_msg += "想要匹配所有可以识别的数据类型"
            else:
                tmp_msg += "想要匹配的文件类型和数据类型为: %s" % self.want_types.get('want') if self.want_types.get('want') else ''
            if search_str == '^[*]':
                tmp_msg += "\n排除所有可以识别的数据类型"
            tmp_msg += "\n排除数据类型为: %s" % self.want_types.get('refuse') if self.want_types.get('refuse') else ''
            if self.unkonw_extend_flag.get():
                tmp_msg += "\n结果包含未知数据类型（私有格式等）！"
        elif search_mode == 'size':
            tmp_msg += '"按文件大小搜索", 匹配方式："条件匹配", ' if reg_flag else '"按文件大小搜索", 匹配方式："精确匹配", '
            tmp_msg += '搜索语句：'
            size_down = self.size_down.get().replace(',', '').replace('，', '')
            tmp_msg1 = '“{}{} {} 项目大小'.format(size_down, self.size_down_unit.get(), self.size_down_sign.get())
            size_up = self.size_up.get().replace(',', '').replace('，', '')
            if size_up:  # 上限有输入
                tmp_msg1 += '{} {}{}'.format(self.size_up_sign.get(), size_up, self.size_up_unit.get())
            tmp_msg1 += '”'
            tmp_msg += tmp_msg1 if reg_flag else '“项目大小 = %s 字节”' % search_str.replace(',', '').replace('，', '')
        elif search_mode in ('5', '8'):  # 按视频、音频时长搜索
            if reg_flag:
                tmp_msg += '"按媒体时长搜索", 匹配方式："条件匹配"\n搜索语句: '
                duration_down_str = ''
                duration_down_str += '%sh' % self.sub_start_time_h.get() if self.sub_start_time_h.get() else ''
                duration_down_str += '%smin' % self.sub_start_time_m.get() if self.sub_start_time_m.get() else ''
                duration_down_str += '%ss' % self.sub_start_time_s.get() if self.sub_start_time_s.get() else ''
                tmp_msg += '“{} {} 项目时长'.format(duration_down_str, self.time_down_sign.get())
                duration_up_str = ''
                duration_up_str += '%sh' % self.sub_end_time_h.get() if self.sub_end_time_h.get() else ''
                duration_up_str += '%smin' % self.sub_end_time_m.get() if self.sub_end_time_m.get() else ''
                duration_up_str += '%ss' % self.sub_end_time_s.get() if self.sub_end_time_s.get() else ''
                if duration_up_str:  # 上限有输入
                    tmp_msg += '{} {}'.format(self.time_up_sign.get(), duration_up_str)
                tmp_msg += '”'
            else:
                tmp_msg += '"按媒体时长搜索", 匹配方式："精确匹配"\n搜索语句: “项目时长 = '
                duration_str = '%sh' % self.sub_time_h.get() if self.sub_time_h.get() else ''
                duration_str += '%smin' % self.sub_time_m.get() if self.sub_time_m.get() else ''
                duration_str += '%ss' % self.sub_time_s.get() if self.sub_time_s.get() else ''
                tmp_msg += duration_str if duration_str else '0'
                tmp_msg += '”'
        elif search_mode in ('6', '7'):  # 按分辨率搜索
            if reg_flag:
                tmp_msg += '"按分辨率搜索", 匹配方式："条件匹配"\n搜索语句：'
                resolution_min_str = '("width": %s, "height": %s)' % (self.resolution_min_w.get(), self.resolution_min_h.get())
                tmp_msg += '“{} {} 分辨率'.format(resolution_min_str, self.resolution_down_sign.get())
                if (self.resolution_max_w.get() or self.resolution_max_h.get()):  # 上限有输入
                    resolution_max_str = '("width": %s, "height": %s)' % (self.resolution_max_w.get(), self.resolution_max_h.get())
                    tmp_msg += '{} {}'.format(self.resolution_up_sign.get(), resolution_max_str)
                tmp_msg += '”'
            else:
                tmp_msg += '"按分辨率搜索", 匹配方式："精确匹配"\n搜索语句：“分辨率 = '
                if (self.resolution_w.get() or self.resolution_h.get()):
                    tmp_msg += '("width": %s, "height": %s)”' % (self.resolution_w.get(), self.resolution_h.get())
                else:
                    tmp_msg += '("width": 0, "height": 0)”'
        elif search_mode == '9':  # 搜索文本内容
            tmp_msg += '"文本内容搜索", 匹配方式："正则匹配", ' if reg_flag else '"文本内容搜索", 匹配方式："精确匹配", '
            tmp_msg += '搜索语句："%s"' % search_str

        if time_flag:
            tmp_msg += '{}: "{}" ~ "{}" '.format(time_option, time_start, time_end)
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
                msg = ''
                self.scr.insert("end", "文件:\n", "title")
                for item in self.result["files"]:
                    msg += '\t{}\n'.format(item)
                self.scr.insert("end", msg)
            if dir_count:
                msg = ''
                self.scr.insert("end", "文件夹:\n", "title")
                for item in self.result["dirs"]:
                    msg += '\t{}\n'.format(item)
                self.scr.insert("end", msg)
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
        # 按时间过滤结果
        self.do_time_filter()
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
        search_path = self.src_dir.get()
        save_path = self.dst_dir.get()
        search_str = self.search_str.get()
        deal_mode = self.deal_mode.get()
        export_mode = self.export_mode.get()  # 导出模式 1.导出到单级目录并附带目录结构描述 2.导出到单级目录 3.保持源目录结构
        same_file_option = self.same_file_option.get()
        # 重新检查是否有取消对目录或者文件的选中
        file_flag = self.file_flag.get()
        dir_flag = self.dir_flag.get()
        if file_flag is False:
            self.result["files"] = []
        if dir_flag is False:
            self.result["dirs"] = []
        # 操作文件
        if len(self.result["files"]) + len(self.result["dirs"]):
            res = common_utils.deal_files(self.result, search_path, save_path, deal_mode=deal_mode, same_file_option=same_file_option,
                                             export_mode=export_mode)
            msg = "导出完成！项目总数： %s ,成功 %s 个，跳过 %s 个， 失败 %s 个， 文件new_old_record记录到 %s" % (
                res.get('total_count'), len(res.get('new_old_record')), len(res.get('skip_list')), len(res.get('failed_list')), res.get("record_path"))
            if res.get("failed_path"):
                msg += '，操作失败的文件信息记录到 %s' % res.get("failed_path")
        else:
            msg = "未找到匹配 %s 的文件和目录!" % search_str
        self.scr.insert('end', "\n%s\n" % msg)
        self.scr.see('end')
        mBox.showinfo("任务完成", "搜索-操作文件完成!")

    def run(self):
        """为操作文件新开一个线程,避免高耗时操作阻塞GUI主线程"""
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        t = threading.Thread(target=self.deal_files)
        t.daemon = True
        t.start()


class CopyDirTreeFrame(BaseFrame):
    """拷贝或导出目录结构"""
    def __init__(self, master=None):
        super().__init__(master)
        self.mode = tk.StringVar()
        self.mode_option = tk.StringVar()
        self.createPage()

    def selectPath1(self):
        if self.mode_option.get() == 'fromfile':
            path_ = askopenfilename()
        else:
            path_ = askdirectory()
        self.src_dir.set(path_)

    def selectOption(self):
        # 从文件信息拷贝目录结构还是 从目录拷贝目录结构
        self.scr.delete(1.0, "end")  # 每次切换选项时都进行结果显示区域清屏

    def createPage(self):
        self.l_title["text"] = "拷贝目录结构"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, pady=10)
        ttk.Radiobutton(self.f_input_option, text="从目录拷贝", variable=self.mode_option, value="fromdir", command=self.selectOption).grid(
            row=0, column=1)
        ttk.Radiobutton(self.f_input_option, text="从文件拷贝", variable=self.mode_option, value="fromfile", command=self.selectOption).grid(
            row=0, column=2)
        self.mode_option.set("fromdir")  # 设置单选默认值
        ttk.Button(self.f_input, text="导出目录结构", command=self.exportDirTree).grid(row=3, column=1, sticky=tk.E)
        ttk.Button(self.f_input, text="拷贝目录结构", command=self.copyDirTree).grid(row=3, column=2, pady=5)
        # 展示结果
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @deal_running_task_arg('拷贝目录结构')
    def copyDirTree(self):
        self.scr.delete(1.0, "end")
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert("end", '%s  正在拷贝目录结构，请稍候...\n' % time_str)
        src_path = self.src_dir.get()
        dst_path = self.dst_dir.get()
        copy_dirs = []  # 新建的目录路径
        if os.path.isfile(src_path):  # 从文件拷贝
            with open(src_path, 'r', encoding='utf-8') as f:
                dir_str_list = f.readlines()
            for item in dir_str_list:
                new_dir = os.path.join(dst_path, item.strip())
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                    copy_dirs.append(new_dir)
        else:
            # 如果是根据目录拷贝 需要判断dst_path是否是src_path的子目录，如果是 有可能会出现逻辑
            # 遍历文件夹，在dst_path 下新建和src_path一样的目录结构
            for root, dirs, files in os.walk(src_path):
                for file_dir in dirs:
                    new_dir = os.path.join(root, file_dir).replace(src_path, dst_path)
                    if not os.path.exists(new_dir):
                        os.makedirs(new_dir)
                        copy_dirs.append(new_dir)
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        self.scr.insert("end", '\n%s  拷贝目录结构完成，目录结构如下:\n' % time_str)
        self.scr.insert("end", '\n'.join(copy_dirs))
        self.scr.see(tk.END)
        self.record_path = os.path.join(settings.RECORD_DIR, 'copy_dirs_%s.txt' % time_res.get('time_num_str'))
        common_utils.export_path_record(copy_dirs, self.record_path)
        msg = "【拷贝目录结构】  拷贝 %s 的目录结构到 %s 完成! 拷贝目录信息记录到 %s" % (src_path, dst_path, self.record_path)
        logger.info(msg)
        mBox.showinfo('任务完成', "拷贝目录结构完成!")

    @deal_running_task_arg('拷贝目录结构')
    def exportDirTree(self):
        self.scr.delete(1.0, "end")
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert("end", '%s  正在导出目录结构信息，请稍候...\n' % time_str)
        src_path = self.src_dir.get()
        dir_list = []
        record_path = ''  # 记录导出信息的文件的路径
        if not os.path.isdir(src_path):  # 判断是否为目录
            self.scr.insert("end", "您输入的是文件,暂不支持从文件导出目录结构到文件!\n若需备份该文件,您可直接复制该文件!\n")
            mBox.showwarning("warning", "您输入的是文件,暂不支持从文件导出目录结构到文件!\n若需备份该文件,您可直接复制该文件!")
            return
        # 遍历目录获取目录路径信息
        for root, dirs, files in os.walk(src_path):
            for file_dir in dirs:
                # 获取相对目录结构 即 D:\a\b\c 若 dir_path 为D:\a 则 相对目录结构为b\c
                new_dir = os.path.join(root, file_dir).replace(src_path, '')[1:]  # 去掉第一个路径分割符
                dir_list.append(new_dir)
        if len(dir_list):
            # 拼接目录结构得到导出文件名，若 dir_path 为D:\a 则 目录结构为D_a 导出文件名为目录结构_[D_a].txt
            file_dir = src_path.replace(':', '').replace('\\', '_').replace('/', '_')
            # 构造保存详细文件信息文件的文件名
            record_name = '目录结构_[%s]_%s.txt' % (file_dir, common_utils.get_times_now().get('time_num_str'))
            record_path = os.path.join(settings.RECORD_DIR, record_name)
            time_str = common_utils.get_times_now().get('time_str')
            self.scr.insert("end", '%s  导出目录结构信息完成，目录结构如下:\n' % time_str)
            for item in dir_list:
                self.scr.insert("end", "%s\n" % item)
            self.scr.see("end")
            common_utils.export_path_record(dir_list, record_path)
            msg = "【拷贝目录结构】  导出 %s 的目录结构信息到 %s" % (src_path, record_path)
            logger.info(msg)
        else:
            msg = "%s 下并无子目录结构!" % src_path
        self.scr.insert("end", msg)
        self.scr.see(tk.END)
        mBox.showinfo("任务完成", "导出目录结构完成!")


class CompareTxtFrame(BaseFrame):
    """比较文本文件内容差异"""
    def __init__(self, master=None):
        super().__init__(master)
        self.dir_flag = tk.BooleanVar()  # 是否操作目录 True 对比目录 False 对比文件
        self.is_context = tk.BooleanVar()  # True 仅显示差异行  False 显示全文
        self.chg_wrapcolumn_flag = tk.BooleanVar()  # 是否修改html页面行宽
        self.wrapcolumn = tk.StringVar()  # html结果页面行宽
        self.encode = tk.StringVar()  # 文件编码 UTF-8 GBK
        self.record_path = None  # 用来记录文本差异结果文件目录路径
        self.dir_flag.set(True)  # 设置单选默认值
        self.encode.set('utf-8')
        self.is_context.set(True)
        self.wrapcolumn.set(100)  # 默认100字符
        self.chg_wrapcolumn_flag.set(False)
        self.createPage()

    def selectPath1(self):
        if self.dir_flag.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.src_dir.set(path_)

    def selectPath2(self):
        if self.dir_flag.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.dst_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "比对文本文件内容"
        ttk.Label(self.f_input, text='源路径: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='模式选择: ').grid(row=0, pady=10)
        ttk.Radiobutton(self.f_input_option, text="对比目录", variable=self.dir_flag, value=True).grid(row=0, column=1)
        ttk.Radiobutton(self.f_input_option, text="对比文件", variable=self.dir_flag, value=False).grid(row=0, column=2)
        ttk.Label(self.f_input_option, text='文件编码: ').grid(row=0, column=3, padx=5)
        ttk.Radiobutton(self.f_input_option, text="UTF-8", variable=self.encode, value='utf-8').grid(row=0, column=4)
        ttk.Radiobutton(self.f_input_option, text="GBK", variable=self.encode, value='gbk').grid(row=0, column=5)
        ttk.Radiobutton(self.f_input_option, text="自动适配", variable=self.encode, value='adapter').grid(row=0, column=6)
        ttk.Label(self.f_input_option, text='结果显示: ').grid(row=0, column=7, padx=5)
        ttk.Radiobutton(self.f_input_option, text="全文显示", variable=self.is_context, value=False).grid(row=0, column=8)
        ttk.Radiobutton(self.f_input_option, text="仅显示差异行", variable=self.is_context, value=True).grid(row=0, column=9)
        ttk.Checkbutton(self.f_input_option, text="修改HTML行宽", variable=self.chg_wrapcolumn_flag, onvalue=True, offvalue=False, command=self.chg_wrapcolumn).grid(row=0, column=10)
        self.e_wrapcolumn = ttk.Entry(self.f_input_option, textvariable=self.wrapcolumn, width=6, state=tk.DISABLED)
        self.e_wrapcolumn.grid(row=0, column=11)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2, pady=5)
        # 展示结果
        scrolW = 120
        scrolH = 38
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看详情", command=self.showDiff, state=tk.DISABLED)
        self.btn_show.grid(row=0, pady=10)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def chg_wrapcolumn(self):
        """激活修改HTML结果页面行宽输入框"""
        if self.chg_wrapcolumn_flag.get():
            self.e_wrapcolumn.config(state=tk.NORMAL)
        else:
            self.e_wrapcolumn.config(state=tk.DISABLED)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            if self.src_dir.get():
                self.dst_dir.set(self.src_dir.get())
            self.src_dir.set(dir_path)

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, 'end')
        self.record_path = None
        self.btn_show.config(state=tk.DISABLED)

    @log_error
    def showDiff(self):
        """用于查看文件差异"""
        if self.record_path:
            webbrowser.open(self.record_path)

    def do_compare_files(self, src_path, dst_path):
        """两个文件间的比对"""
        wrapcolumn = common_utils.get_int(self.wrapcolumn.get(), 100)
        self.record_path = os.path.join(settings.RECORD_DIR, '文本内容差异', common_utils.get_times_now().get("time_num_str"))  # 建立用于存储本次差异文件的目录
        html_path = common_utils.compare_txt(src_path, dst_path, self.record_path, self.encode.get(), self.is_context.get(), wrapcolumn)
        time_str = common_utils.get_times_now().get('time_str')
        if html_path:
            self.scr.insert("end", "\n\n%s  比对完成！文件文本差异导出到 %s\n" % (time_str, self.record_path))
        else:
            self.scr.insert("end", "\n\n%s  比对完成！未发现文本内容有变化的同名文件！\n" % time_str)

    def do_compare_dirs(self, src_path, dst_path):
        """两个目录间的比对"""
        is_context = self.is_context.get()
        encode = self.encode.get()
        wrapcolumn = common_utils.get_int(self.wrapcolumn.get(), 100)
        file_list1 = common_utils.get_pathlist(src_path)
        file_list2 = common_utils.get_pathlist(dst_path)
        result = {"only_in_src": [], "only_in_dst": [], "common_files": [], "diff_files": [], "common_funny": []}  # 记录比对结果
        compare_items = []  # 要比对的文件路径
        # 获取要比对的文件列表
        for file1 in file_list1:
            dst_item = file1.replace(src_path, dst_path)
            if dst_item in file_list2:
                compare_items.append((file1, dst_item))
            else:
                result["only_in_src"].append(file1)

        for file2 in file_list2:
            file1 = file2.replace(dst_path, src_path)
            if file1 not in file_list1:
                result["only_in_dst"].append(file2)
        # 比对文件内容
        self.record_path = os.path.join(settings.RECORD_DIR, '文本内容差异', common_utils.get_times_now().get("time_num_str"))  # 建立用于存储本次差异文件的目录
        if not os.path.exists(self.record_path):  # 输出目录不存在则创建
            os.makedirs(self.record_path)
        for file1, file2 in compare_items:
            if common_utils.get_md5(file1) == common_utils.get_md5(file2):  # 文件内容一致
                result["common_files"].append((file1, file2))
                continue
            try:
                html_path = common_utils.compare_txt(file1, file2, self.record_path, encode, is_context, wrapcolumn)
                if html_path:
                    logger.debug("文件内容差异导出到 %s" % html_path)
                    result["diff_files"].append((file1, file2))
                else:
                    result["common_files"].append((file1, file2))
            except UnicodeDecodeError:
                result["common_funny"].append((file1, file2))
                logger.debug("文件无法正确解码或者文件不是文本类型文件！")
        # 输出结果到页面
        time_str = common_utils.get_times_now().get('time_str')
        total_msg = "\n\n%s  比对完成！详情如下:\n" % time_str
        only_in_src_list = result["only_in_src"]
        only_in_dst_list = result["only_in_dst"]
        common_funny = result["common_funny"]
        diff_list = result["diff_files"]
        if len(only_in_src_list):
            total_msg += "\n总共有 %s 个文件仅存在于 %s\n" % (len(only_in_src_list), src_path)
            for item in only_in_src_list:
                total_msg += "\t%s\n" % item
        if len(only_in_dst_list):
            total_msg += "\n总共有 %s 个文件仅存在于 %s\n" % (len(only_in_dst_list), dst_path)
            for item in only_in_dst_list:
                total_msg += "\t%s\n" % item    
        if len(common_funny):
            total_msg += "\n总共有 %s 个文件无法比对（编码格式错误，或者非文本文件）\n" % len(common_funny)
            for item in common_funny:
                total_msg += "\t%s\n0==}==========>%s\n" % (item[0], item[1])
        if len(diff_list):
            total_msg += "\n总共有 %s 个文件文本内容发生变化！\n" % len(diff_list)
            for item in diff_list:
                total_msg += "\t%s\n0==}==========>%s\n" % (item[0], item[1])
        if not(len(only_in_src_list) + len(only_in_dst_list) + len(diff_list) + len(common_funny)):
            total_msg += "未发现文本内容有变化的同名文件!\n"
        self.scr.insert("end", total_msg)
        with open(os.path.join(self.record_path, "result.txt"), 'w', encoding='utf-8') as f:
            f.write(total_msg)
        self.scr.see(tk.END)

    @deal_running_task_arg('比对文本文件内容')
    def do_compare(self, src_path, dst_path):
        """比对两个目录下同名文本文件内容"""
        self.scr.insert("end", "%s  开始比对文件...\n" % common_utils.get_times_now().get("time_str"))
        if self.dir_flag.get() is False:
            # 对比两个文件内容
            self.do_compare_files(src_path, dst_path)
        else:  # 比对两个目录下同名文件内容
            self.do_compare_dirs(src_path, dst_path)
        if self.record_path:
            self.btn_show.config(state=tk.NORMAL)
        mBox.showinfo("任务完成", "比对文本文件内容完成!")
        logger.info("【比对文本文件内容】  比对 %s 和 %s 下文件内容，文件文本差异导出到 %s" % (src_path, dst_path, self.record_path))

    def run(self):
        self.clear()
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        flag = self.check_path_exists(self.dst_dir)
        if not flag:
            return
        src_path = self.src_dir.get()
        dst_path = self.dst_dir.get()
        self.scr.insert("end", "正在比对 %s 与 %s 下的文本文件内容...\n" % (src_path, dst_path))
        t = threading.Thread(target=self.do_compare, args=(src_path, dst_path))
        t.daemon = True
        t.start()


class CalHashFrame(BaseFrame):
    """计算文件hash值"""
    def __init__(self, master=None):
        super().__init__(master)
        self.search_str = tk.StringVar()  # 搜索字符串
        self.mode = tk.BooleanVar()  # True 对比目录 False 对比文件
        self.upper_flag = tk.BooleanVar()  # True 大写 False 小写
        self.result = {}
        self.rate_val = 0  # 进度值，用来记录当前读取的字节数
        self.rate_val_total = 0  # 单个文件进度值范围， 即文件字节数
        self.rate_count = 0  # 进度值，记录当前已经计算的文件数
        self.is_complete = False  # 用来标记所有计算任务是否完成，以防止进度条子线程陷入死循环
        self.FUNC_DICT = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha224': hashlib.sha224,
            'sha256': hashlib.sha256,            
            'sha384': hashlib.sha384,
            'sha512':  hashlib.sha512,
            'sha3_224': hashlib.sha3_224,
            'sha3_256': hashlib.sha3_256,
            'sha3_384': hashlib.sha3_384,
            'sha3_512': hashlib.sha3_512,
            }
        self.algors = tuple(self.FUNC_DICT.keys())  # 算法
        self.algorObjs = []  # 复选框tk变量
        for i in self.algors:
            tkObj = tk.StringVar()
            if i in ('sha1', 'sha256', 'md5'):
                tkObj.set(i)
            else:
                tkObj.set('')
            self.algorObjs.append(tkObj)  # 获取复选框变量
        self.mode.set(True)
        self.upper_flag.set(False)
        self.createPage()

    @deal_running_task_arg('计算hash值')
    def cal_hash(self, path_list):
        self.clear()  # 归零
        args = []  # 存放要计算的算法
        for algorObj in self.algorObjs:
            if algorObj.get():
                args.append(algorObj.get())
        file_list = []  # 所有文件路径
        # 获取所有文件路径信息
        for item in path_list:
            if os.path.isfile(item):  # 是文件
                file_list.append(item)
            else:
                for root, dirs, files in os.walk(item):
                    for file in files:
                        file_list.append(os.path.join(root, file))
        # 计算全部文件hash值
        threading.Thread(target=self.show_rate, args=(len(file_list),)).start()  # 创建进度条显示子线程
        for file_path in file_list:
            file_path = os.path.abspath(file_path)
            size = os.path.getsize(file_path)
            mtime = time.strftime(r"%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(file_path)))
            ret = {"size": size, "mtime": mtime}  # 用于储存单个文件的hash值信息{'size':xxx, "mtime":xxx, 'sha1':xxx,'sha256':xxx,'md5':xxx}
            # 获取文件版本信息, 如果是exe 或者dll则获取文件版本信息
            if os.path.splitext(file_path)[1].lower() in ['.exe', '.dll', '.msi']:
                try:
                    version = my_api.getFileVersion(file_path)
                    ret["version"] = version
                except Exception as e:
                    logger.debug("Exception: %s" % e)
            # 计算文件hash值
            logger.debug("正在计算: %s" % file_path)
            ret.update(self.calc_file_hash(file_path, args))  # 计算单个文件的所有要求的hash值
            result = {file_path: ret}
            self.show_result(result)  # 输出文件hash信息到界面
            self.result.update(result)
            self.rate_count += 1
        self.is_complete = True  # 计算任务已完成
        logger.debug("所有项目计算完成！")

    def calc_file_hash(self, file_path, args, read_bytes=10240):
        """计算hash值"""
        self.rate_val = 0  # 进度值置零还原
        hashObj_list = []  # hash对象集合
        # 创建hash对象
        for item in args:
            if item in self.FUNC_DICT:
                hashObj_list.append(self.FUNC_DICT[item]())
        total_size = os.path.getsize(file_path)
        self.rate_val_total = total_size
        if total_size == 0:
            logger.debug("\r该文件内容为空!", end='')
        with open(file_path, 'rb') as f:
            while True:
                self.rate_val += read_bytes
                data = f.read(read_bytes)
                if data:
                    for hashObj in hashObj_list:
                        hashObj.update(data)
                else:
                    self.rate_val = total_size  # 为防止主线程函数结束，子线程还没运行完，导致进度条出现bug的问题
                    break
        ret = {}
        for index, item in enumerate(args):
            ret[item] = hashObj_list[index].hexdigest()
        return ret
    
    def show_rate(self, total_count):
        """显示计算hash进度条
        total_count: 总文件数
        """
        self.pb2["maximum"] = total_count
        curr_file_size = 0  # 记录单个文件字节数，即为进度条1的范围
        while True:
            # 如果检测到所有计算任务已完成则退出
            if self.is_complete:
                self.pb1["value"] = self.pb1["maximum"] if self.pb1["maximum"] > 0 else 1
                self.pb2["value"] = self.pb2["maximum"] if self.pb2["maximum"] > 0 else 1
                break
            # 当前在读取的文件已变更
            if curr_file_size != self.rate_val_total:
                curr_file_size = self.rate_val_total
                self.pb1["maximum"] = curr_file_size
            self.pb1["value"] = self.rate_val
            self.pb2["value"] = self.rate_count
            # 所有文件都已计算完成
            if self.rate_count >= total_count:
                self.pb1["value"] = self.pb1["maximum"] if self.pb1["maximum"] > 0 else 1
                self.pb2["value"] = self.pb2["maximum"] if self.pb2["maximum"] > 0 else 1
                break
            time.sleep(0.05)

    def show_result(self, result):
        """输出结果到界面"""
        for file in result:
            self.scr.insert("end", '%s:\t%s\n' % ("文件", file))
            for item in result[file]:
                if item == "size":
                    info_str = "%s:\t%s" % ("大小", result[file][item])
                elif item == "mtime":
                    info_str = "%s:\t%s" % ("修改时间", result[file][item])
                elif item == "version":
                    info_str = "%s:\t%s" % ("文件版本", result[file][item])
                else:
                    info_str = "%s:\t%s" % (item, result[file][item])
                if self.upper_flag.get():
                    info_str = info_str.upper()
                self.scr.insert("end", '%s\n' % info_str)
            self.scr.insert("end", "\n")
            self.scr.see("end")

    @dragged_locked
    def dragged_files(self, files):
        path_list = []
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)  # 修改配置之后下次就会用新的配置
            path_list.append(dir_path)
        t = threading.Thread(target=self.cal_hash, args=(path_list,))
        t.daemon = True
        t.start()

    def selectPath(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.src_dir.set(path_)

    def run(self):
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.cal_hash, args=([self.src_dir.get(), ],))
        t.daemon = True
        t.start()

    def toUpper(self):
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

    def toLower(self):
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
        """结果保存到文件"""
        hash_path = asksaveasfilename()
        logger.debug("正在将计算的hash值记录到文件...")
        with open(hash_path, 'w', encoding='utf-8') as f:
            f.write(self.scr.get(1.0, "end"))
        logger.debug("记录hash值到 %s 完成！" % hash_path)

    def clear(self):
        """用于清除数据"""
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.pb2["value"] = 0
        self.pb2["maximum"] = 0  # 总项目数
        self.rate_val = 0
        self.rate_val_total = 0
        self.rate_count = 0
        self.is_complete = False  # 计算任务完成标记归零
    
    def clear_data(self):
        """用于清除本页面的所有数据"""
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.pb2["value"] = 0
        self.pb2["maximum"] = 0  # 总项目数
        self.scr.delete(1.0, 'end')
        self.result.clear()
        self.rate_val = 0
        self.rate_val_total = 0
        self.rate_count = 0
        self.is_complete = False  # 计算任务完成标记归零

    def search(self):
        """用于从计算结果中搜索指定字符串"""
        content = self.scr.get(1.0, tk.END)
        if content.endswith('\n'):  # 用于去除每次搜索后多出来的一个换行
            content = content[:-1]
        search_str = self.search_str.get()  # 要搜索的字符串
        if not search_str:  # 无字符
            return
        if self.upper_flag.get() is True:
            search_str = search_str.upper()
        else:
            search_str = search_str.lower()
        logger.debug("search_str", search_str)
        count = content.count(search_str)
        if not count:
            # 未搜索到
            self.scr.delete(1.0, "end")
            self.scr.insert(tk.END, content)
            # logger.debug("tk.END: ", tk.END)
            self.scr.see(tk.END)
            mBox.showinfo("任务完成", "未搜索到匹配结果!")
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
                mBox.showinfo("任务完成", "一共搜索到 %s 处!" % count)

    def createPage(self):
        self.l_title["text"] = "计算hash值"
        ttk.Label(self.f_input, text='文件路径: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=2)
        self.f_input1 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input1.grid(row=2, columnspan=3, sticky=tk.EW)
        self.f_input2 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input2.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input1, text='浏览模式: ').grid(row=0, pady=10)
        ttk.Radiobutton(self.f_input1, text="目录", variable=self.mode, value=True).grid(row=0, column=1, padx=5)
        ttk.Radiobutton(self.f_input1, text="文件", variable=self.mode, value=False).grid(row=0, column=2)
        ttk.Label(self.f_input1, text=' 切换大小写: ').grid(row=0, column=3, padx=5)
        ttk.Radiobutton(self.f_input1, text="大写", variable=self.upper_flag, value=True, command=self.toUpper).grid(row=0, column=5, padx=5)
        ttk.Radiobutton(self.f_input1, text="小写", variable=self.upper_flag, value=False, command=self.toLower).grid(row=0, column=6)
        ttk.Label(self.f_input2, text='算法选择: ').grid(row=1, sticky=tk.W)
        col = 1
        row = 1
        for index, item in enumerate(self.algorObjs):
            value = self.algors[index]
            ttk.Checkbutton(self.f_input2, text=value, variable=item, onvalue=value, offvalue='').grid(column=col, row=row, padx=5)
            col += 1
        
        ttk.Label(self.f_option).grid(row=3)  # 占位
        self.f_option.grid_columnconfigure(0, weight=1)
        self.f_bottom.grid_columnconfigure(1, weight=1)
        ttk.Button(self.f_option, text='清除', command=self.clear_data).grid(row=3, column=1, sticky=tk.E, pady=6)
        ttk.Button(self.f_option, text='保存', command=self.writehash).grid(row=3, column=2)
        ttk.Button(self.f_option, text='计算', command=self.run).grid(row=3, column=3)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW)
        self.pb2 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb2.grid(row=1, sticky=tk.EW, pady=5)
        scrolW = 120
        scrolH = 34
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        ttk.Entry(self.f_bottom, textvariable=self.search_str, width=110).grid(row=2, column=1, sticky=tk.EW, pady=5)
        ttk.Button(self.f_bottom, text="查找", command=self.search).grid(row=2, column=2, sticky='E')
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作


class RenameFrame(BaseFrame):
    """递归批量重命名"""
    def __init__(self, master=None):
        super().__init__(master)
        self.f_content.grid_columnconfigure(1, weight=1)
        self.search_option = tk.StringVar()  # 标记是精确匹配还是正则匹配
        self.dir_flag = tk.BooleanVar()  # True 操作文件夹 False 不操作
        self.file_flag = tk.BooleanVar()  # True 操作文件 False 不操作
        self.search_mode = tk.StringVar()  # '1' 简单匹配(子集) '2' 精确匹配(完全一致) '3' 正则匹配
        # 重命名模式 '1' 替换字符 '2' 插入字符 '3' 插入编号  '4' 插入时间 '5' 文件名大写 '6' 文件名小写 '7'大小写互换 '8' 删除字符 
        # '9' 重构字符串 '10' 视频时长 '11' 分辨率 '12' 后缀名还原
        self.rename_mode = tk.StringVar()  # 重命名模式
        self.mod_ext_flag = tk.BooleanVar()  # 是否操作后缀名 True 操作后缀名 False 仅操作文件名
        self.index = tk.StringVar()  # 新字符插入位置  索引  -1代表最后一位 end 代表末尾
        self.del_index_start = tk.StringVar()  # 删除字符开始索引
        self.del_index_end = tk.StringVar()  # 删除字符结束索引
        self.time_option = tk.StringVar()  # 记录选择的时间类型 0 修改时间  1 创建时间 2 照片拍摄时间
        self.time_format = tk.StringVar()  # 时间格式 %Y-%m-%d %H:%M:%S
        self.search_str = tk.StringVar()  # 要搜索的字符串
        self.new_str = tk.StringVar()  # 新字符串
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.ignore_case_flag = tk.BooleanVar()  # 决定是否忽略大小写，正则表达式匹配模式 re.I
        # 正常程序处理字符串顺序是按字符串排序，也就是 1 11 111 2  ，自然数排序则为1 2 11 111
        self.natsort_flag = tk.BooleanVar()  # 决定是否以自然数排序，True按自然数排序
        self.light_flag = tk.BooleanVar()  # 是否高亮显示匹配到的内容，True高亮显示   因为tkinter效率很低，高亮显示要不停输出阻塞，故默认不高亮显示
        self.rec_flag = tk.BooleanVar()  # 是否递归操作子目录和子文件  True 递归
        self.start_num = tk.IntVar()  # 初始值
        self.zero_num = tk.IntVar()  # 零位数，左边填充零个数
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.preview_result = {"dirs": [], "files": []}  # 存储重命名到的结果{'dir':[(new_path, old_path)],'files:[]}
        self.search_ext_flag = tk.BooleanVar()  # 匹配时是否包含后缀名 True 包含后缀名的文件名 False 仅文件名不包含后缀名
        self.dir_flag.set(True)
        self.file_flag.set(True)
        self.mod_ext_flag.set(True)
        self.natsort_flag.set(True)
        self.light_flag.set(False)
        self.rec_flag.set(True)
        self.search_ext_flag.set(True)
        self.index.set('0')
        self.rename_mode.set('1')
        self.createPage()

    def get_files(self):
        """遍历文件和目录获取路径信息"""
        src_path = common_utils.check_path(self.src_dir.get())
        res = {"dirs": [], "files": []}
        if self.dir_flag.get():
            if self.rec_flag.get() is False:   # 不递归
                tmp_list = os.listdir(src_path)
                for item in tmp_list:
                    _path = os.path.join(src_path, item)
                    if os.path.isdir(_path):
                        res['dirs'].append(_path)
            else:
                for root, dirs, files in os.walk(src_path):
                    for item in dirs:
                        res['dirs'].append(os.path.join(root, item))
        if self.file_flag.get():
            if self.rec_flag.get() is False:  # 不递归
                tmp_list = os.listdir(src_path)
                for item in tmp_list:
                    _path = os.path.join(src_path, item)
                    if os.path.isfile(_path):
                        res['files'].append(_path)
            else:
                for root, dirs, files in os.walk(src_path):
                    for item in files:
                        res['files'].append(os.path.join(root, item))
        return res

    def do_search_regex(self):
        """搜索满足条件的目录或文件(正则模式)"""
        search_str = self.search_str.get()
        if self.ignore_case_flag.get() is True:
            flags = re.I
        else:
            flags = 0
        # 遍历获取全部匹配的路径信息
        res = self.get_files()
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
        for _path in res['dirs']:
            _name = os.path.basename(_path) 
            searchObj = re.search(search_str, _name, flags)
            if searchObj:
                self.result['dirs'].append(_path)
        for _path in res['files']:
            _name = os.path.basename(_path)
            if search_ext_flag is False:
                _name = os.path.splitext(_name)[0]
            searchObj = re.search(search_str, _name, flags)
            if searchObj:
                self.result['files'].append(_path)

    def do_search_normal(self):
        """搜索满足条件的目录或文件(普通模式 不支持正则语法)"""
        search_str = self.search_str.get()
        # 遍历获取全部匹配的路径信息
        res = self.get_files()
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
        for _path in res['dirs']:
            _name = os.path.basename(_path)
            if search_str in _name:
                self.result['dirs'].append(_path)
        for _path in res['files']:
            _name = os.path.basename(_path)
            if search_ext_flag is False:
                _name = os.path.splitext(_name)[0]
            if search_str in _name:
                self.result['files'].append(_path)

    def do_search_exact(self):
        """搜索满足条件的目录或文件(精确模式 不支持正则语法)"""
        search_str = self.search_str.get()
        # 遍历获取全部匹配的路径信息
        res = self.get_files()
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
        for _path in res['dirs']:
            _name = os.path.basename(_path)
            if search_str == _name:
                self.result['dirs'].append(_path)
        for _path in res['files']:
            _name = os.path.basename(_path)
            if search_ext_flag is False:
                _name = os.path.splitext(_name)[0]
            if search_str == _name:
                self.result['files'].append(_path)

    def show_search_result_regex(self):
        """用于实际显示搜索到的结果
        src_path: 搜索的根目录路径
        search_str: 搜索的内容
        """
        src_path = common_utils.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        if self.ignore_case_flag.get() is True:
            flags = re.I
        else:
            flags = 0
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
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
                    tmp_ext = ''
                    if search_ext_flag is False:  # 不匹配后缀名
                        tmp_name, tmp_ext = os.path.splitext(tmp_name)  # 仅文件名，不含后缀名部分
                    if tmp_dir:
                        self.scr1.insert('end', "%s\\" % tmp_dir[1:])
                    matchObj = re.search(search_str, tmp_name, flags=flags)
                    if matchObj:
                        start = matchObj.start()
                        end = matchObj.end()
                        self.scr1.insert(tk.END, tmp_name[:start])  # 除去匹配到内容之外的内容
                        self.scr1.insert(tk.END, tmp_name[start:end], "tag")  # 匹配到的内容 “tag”标签标记后面做格式
                        self.scr1.insert(tk.END, tmp_name[end:])  # 除去匹配到内容之外的内容
                    self.scr1.insert(tk.END, tmp_ext)
                    self.scr1.insert('end', "\n")
        self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')

    def show_search_result_normal(self):
        """用于实际显示搜索到的结果
        src_path: 搜索的根目录路径
        search_str: 搜索的内容
        """
        src_path = common_utils.check_path(self.src_dir.get())
        search_str = self.search_str.get()
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
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
                    tmp_ext = ''
                    if search_ext_flag is False:  # 不匹配后缀名
                        tmp_name, tmp_ext = os.path.splitext(tmp_name)  # 仅文件名，不含后缀名部分
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
                    self.scr1.insert(tk.END, tmp_ext)
                    self.scr1.insert('end', "\n")
        self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')

    def show_search_result_exact(self):
        """用于实际显示搜索到的结果
        src_path: 搜索的根目录路径
        """
        src_path = common_utils.check_path(self.src_dir.get())
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
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
                    tmp_ext = ''
                    if search_ext_flag is False:  # 不匹配后缀名
                        tmp_name, tmp_ext = os.path.splitext(tmp_name)  # 仅文件名，不含后缀名部分
                    if tmp_dir:
                        self.scr1.insert('end', "%s\\" % tmp_dir[1:])
                    self.scr1.insert(tk.END, tmp_name, "tag")
                    self.scr1.insert(tk.END, tmp_ext)
                    self.scr1.insert('end', "\n")
        self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')

    def deal_show_search_result(self):
        """用于调度显示搜索到的结果
        """
        logger.debug('%s 搜索完成！' % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
        src_path = common_utils.check_path(self.src_dir.get())
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
            t.daemon = True
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
            self.scr1.insert("end", "\n\n共有符合条件目录 %s 个，文件 %s 个" % (len(self.result["dirs"]), len(self.result["files"])),'info')
        self.scr1.tag_config('tag', background='RoyalBlue', foreground="white")
        self.scr1.tag_config('info', font=('microsoft yahei', 16, 'bold'))
        self.scr1.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr1.see("end")
    
    def do_search(self):
        """用于调度搜索方法"""
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        if search_mode == '1':  # 简单匹配
            self.do_search_normal()
        elif search_mode == '3':  # 正则匹配
            self.do_search_regex()
        else:  # 精确匹配
            self.do_search_exact()
        self.deal_show_search_result()  # 显示结果

    def deal_search(self):
        """为搜索操作新开一个线程,避免高耗时操作阻塞GUI主线程"""
        self.clear()
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.do_search)
        t.daemon = True
        t.start()

    @staticmethod
    def get_index(index):
        """用于获取输入的位置索引"""
        index = index.strip()
        if index.upper() in ['END', 'E']:
            return 'END'
        if re.match(r'-?\d+$', index):
            return int(index)

    @staticmethod
    def rename_preview_del_char(old_name, del_index_start, del_index_end):
        """删除字符,输入的是字符在字符串中的索引值"""
        if del_index_start == 'END':
            return old_name
        if del_index_end in ['END', -1, '', None]:
            return old_name[:del_index_start]
        del_index_end += 1
        if old_name[del_index_start: del_index_end]:
            new_name = old_name[:del_index_start] + old_name[del_index_end:]
            if new_name:  # 避免两个索引取值有问题，开始比结束大
                return new_name
            else:
                return old_name
        else:
            return old_name

    def rename_preview(self):
        """构造新文件名，并不执行重命名，只是计算新的文件名"""
        self.scr1.delete(1.0, 'end')
        self.scr2.delete(1.0, 'end')
        old_str = self.search_str.get()
        new_str = self.new_str.get()
        dir_flag = self.dir_flag.get()  # 是否操作文件夹
        file_flag = self.file_flag.get()  # 是否操作文件
        start_num = self.start_num.get()
        zero_num = self.zero_num.get()
        rename_mode = self.rename_mode.get()
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        flags = re.I if self.ignore_case_flag.get() else 0
        del_index_start = self.get_index(self.del_index_start.get())
        del_index_end = self.get_index(self.del_index_end.get())
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.preview_result = {'dirs': [], 'files': []}
        # 检查并过滤可能导致报错的小数点
        mod_ext_flag = self.mod_ext_flag.get()  # 是否操作后缀名
        search_ext_flag = self.search_ext_flag.get()  # 是否匹配后缀名
        for item in self.result:
            if not len(self.result[item]):
                continue
            if item == 'dirs':
                if dir_flag is False:
                    continue
            else:
                if file_flag is False:
                    continue
            for old_path in self.result[item]:
                old_dir = os.path.dirname(old_path)
                old_name = os.path.basename(old_path)  # 原文件名
                old_ext = ''
                new_name = ''
                if item == 'files':  # 如果要对象是文件 则需要重新分析文件名和后缀名
                    # if search_ext_flag is False:  # 不匹配后缀名
                    #     old_name = os.path.splitext(os.path.basename(old_path))[0]  # 仅文件名，不含后缀名部分
                    if mod_ext_flag is False:  # 不操作后缀名
                        old_name, old_ext = os.path.splitext(os.path.basename(old_path))
                # 设计新文件名
                if rename_mode == '1':  # 替换字符
                    if search_mode == '1':  # 简单匹配
                        if old_str in old_name:
                            new_name = old_name.replace(old_str, new_str)
                    elif search_mode == '3':  # 正则匹配
                        if re.search(old_str, old_name, flags=flags):
                            new_name = re.sub(old_str, new_str, old_name, flags=flags)
                    else:  # 精确模式
                        if old_str == old_name:
                            new_name = old_name.replace(old_str, new_str)
                elif rename_mode == '2':  # 插入字符
                    new_name = self.insert_str(old_name, new_str)
                elif rename_mode == '3':  # 插入编号
                    sub_str = new_str + str(start_num).zfill(zero_num)
                    new_name = self.insert_str(old_name, sub_str)
                    start_num += 1
                elif rename_mode == '4':  # 插入时间
                    time_str = self.get_time_str(old_path)
                    sub_str = new_str + time_str
                    new_name = self.insert_str(old_name, sub_str)
                elif rename_mode == '5':  # 文件名大写
                    new_name = old_name.upper()
                elif rename_mode == '6':  # 文件名小写
                    new_name = old_name.lower()
                elif rename_mode == '7':  # 文件名大小写互换
                    new_name = old_name.swapcase()
                elif rename_mode == '8':  # 删除字符
                    new_name = self.rename_preview_del_char(old_name, del_index_start, del_index_end)
                elif rename_mode == '9':  # 文件名重构
                    obj = re.findall(r'(.*?)(%time|%num|%res)(.*?)', new_str)
                    logger.debug('输入的重构字符串模型： {}'.format(new_str))
                    new_name = ''
                    tmp_str = new_str
                    if obj:
                        logger.debug('正则匹配重构字符串模型： {}'.format(obj))
                        for i in obj:
                            if i[1] == r'%time':
                                sub_str = self.get_time_str(old_path)
                            elif i[1] == r'%res':
                                sub_str = self.get_res_str(old_name)
                            else:
                                sub_str = str(start_num).zfill(zero_num)
                                start_num += 1
                            new_name += '{}{}{}'.format(i[0], sub_str, i[2])
                            tmp_str = tmp_str.replace(''.join(i), '')  # 非贪婪匹配总是最后有一些匹配不了
                            # 例如 '.+- ddd%time%num%timetime%num 00 -- '
                            # 匹配到的就是[('.+- ddd', '%time', ''), ('', '%num', ''), ('', '%time', ''), ('time', '%num', '')]
                    new_name += tmp_str  # 用于解决非贪婪匹配模式下末尾有些匹配不到的字符串
                elif rename_mode == '10':  # 插入视频时长
                    tmp_str = self.get_duration_str(new_str, old_path)
                    new_name = self.insert_str(old_name, tmp_str)
                elif rename_mode == '11':  # 插入分辨率
                    item_meta = self.get_resolution_str(old_path)
                    tmp_str = new_str
                    tmp_str = re.sub(r'%width|%w', str(item_meta['width']), tmp_str)
                    tmp_str = re.sub(r'%height|%h', str(item_meta['height']), tmp_str)
                    if tmp_str == new_str:
                        tmp_str = '_[%sx%s]' % (item_meta['width'], item_meta['height'])
                    new_name = self.insert_str(old_name, tmp_str)
                elif rename_mode == '12':  # 后缀名还原
                    if os.path.isfile(old_path):
                        res = common_utils.get_filetype(old_path)
                        if res:
                            # old_ext = ''  # 默认直接去除原后缀名
                            new_ext = res.extension
                            new_name = os.path.splitext(os.path.basename(old_path))[0] + '.' + new_ext
                # 记录
                if new_name:
                    new_name += old_ext
                    new_path = os.path.join(old_dir, new_name)
                    self.new_old_tuple_list.append((new_path, old_path))
                    self.preview_result[item].append((new_path, old_path))
        # 显示结果
        self.show_rename_preview()

    def get_res_str(self, old_name):
        """获取匹配到的字符内容"""
        search_str = self.search_str.get()
        search_mode = self.search_mode.get()  # 匹配模式 1 简单匹配(子集) 2 精确匹配(完全一致) 3 正则匹配
        if search_mode in ('1', '2'):  # 简单匹配或者完整匹配
            res = search_str
        else:
            # 正则匹配
            if self.ignore_case_flag.get() is True:
                flags = re.I
            else:
                flags = 0
            matchObj = re.search(search_str, old_name, flags)
            if not matchObj:  # 没有匹配到内容
                return ''
            if matchObj.groups():  # 正则语句中有()分组，则取第一个
                res = matchObj.group(1)
            else:  # 没有分组则取匹配到的内容
                res = matchObj.group()
        # logger.debug(res)
        return res

    def get_duration_str(self, new_str, old_path):
        """构造插入视频时长信息的str"""
        # 获取视频时长信息
        if common_utils.check_filetype(old_path, 'video'):
            video_meta = common_utils.get_video_info(old_path)
        else:
            return
        duration = video_meta.get('duration_sec')
        tmp_str = new_str
        logger.debug('输入的数据模型： {}'.format(new_str))
        if re.search(r'.*%H.+%M.+%S.*', new_str):
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            tmp_str = re.sub(r'%H', str(hours), tmp_str)
            tmp_str = re.sub(r'%M', str(minutes), tmp_str)
            tmp_str = re.sub(r'%S', str(seconds), tmp_str)
        elif re.search(r'.*(%H).+(%M).*', new_str):
            hours = duration // 3600
            minutes = (duration % 3600) / 60
            tmp_str = re.sub(r'%H', str(hours), tmp_str)
            tmp_str = re.sub(r'%M', str('%.1f' % minutes), tmp_str)
        elif re.search(r'.*%H.+%S.*', new_str):
            hours = duration // 3600
            seconds = duration % 3600
            tmp_str = re.sub(r'%H', str(hours), tmp_str)
            tmp_str = re.sub(r'%S', str(seconds), tmp_str)
        elif re.search(r'.*%H.*', new_str):
            if duration < 3600:
                hours = '%.4f' % (duration / 3600)
            else:
                hours = '%.1f' % (duration / 3600)
            tmp_str = re.sub(r'%H', str(hours), tmp_str)
        elif re.search(r'.*%M.+%S.*', new_str):
            minutes = duration // 60
            seconds = duration % 60
            tmp_str = re.sub(r'%M', str(minutes), tmp_str)
            tmp_str = re.sub(r'%S', str(seconds), tmp_str)
        elif re.search(r'.*%M.*', new_str):
            if duration < 60:
                minutes = '%.4f' % (duration / 60)
            else:
                minutes = duration // 60
            tmp_str = re.sub(r'%M', str(minutes), tmp_str)
        elif re.search(r'.*%S.*', new_str):
            tmp_str = re.sub(r'%S', str(duration), tmp_str)
        else:  # 默认
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            tmp_str = '_[%sh%sm%ss]' % (hours, minutes, seconds)
        return tmp_str

    def get_resolution_str(self, old_path):
        """获取分辨率"""
        if common_utils.check_filetype(old_path, 'video'):
            return common_utils.get_video_resolution(old_path)
        if common_utils.check_filetype(old_path, 'image'):
            return common_utils.get_image_resolution(old_path)

    def show_rename_preview(self):
        """显示重命名预览结果"""
        self.scr1.delete(1.0, 'end')
        self.scr2.delete(1.0, 'end')
        src_path = self.src_dir.get()
        for item in self.preview_result:
            if len(self.preview_result[item]):
                if item == 'dirs':
                    self.scr1.insert('end', "文件夹:\n", 'title')
                    self.scr2.insert('end', "文件夹:\n", 'title')
                else:
                    self.scr1.insert('end', "文件:\n", 'title')
                    self.scr2.insert('end', "文件:\n", 'title')
                for new_path, old_path in self.preview_result[item]:
                    old_sub_path = old_path.replace(src_path, '')[1:]  # 相对于根目录的相对路径
                    new_sub_path = new_path.replace(src_path, '')[1:]
                    self.scr1.insert('end', "\t%s\n" % old_sub_path)
                    self.scr2.insert('end', "\t%s\n" % new_sub_path)
        self.scr1.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.scr2.tag_config('title', foreground="RoyalBlue", font=('microsoft yahei', 16, 'bold'))
        self.btn_rename.config(state=tk.NORMAL)

    def insert_str(self, old_str, sub_str):
        """插入字符串方法"""
        index = self.index.get()  # 要插入的位置
        # 无输入
        if not index:
            return
        # 直接在最末尾添加
        if index.upper() in ['END', 'E']:
            return old_str + sub_str
        # 输入为索引
        try:
            index = int(index)
            new_str = old_str[:index] + sub_str + old_str[index:]
            return new_str
        except:
            logger.debug('输入索引格式有误！')
            return

    def get_time_str(self, file_path):
        """获取时间字符串"""
        time_option = self.time_option.get()  # 修改时间   创建时间  拍摄时间
        # logger.debug('time_option: {}'.format(time_option))
        time_format = self.time_format.get()
        _time = ''
        time_str = ''
        if time_option == '修改时间':
            _time = os.path.getmtime(file_path)
        elif time_option == '创建时间':
            _time = os.path.getctime(file_path)
        elif time_option == '拍摄时间':
            if os.path.isfile(file_path):
                date_information = common_utils.get_media_encoded_date(file_path)
                if date_information:  # 转换为时间戳
                    _time = time.mktime(time.strptime(date_information, r'%Y-%m-%d %H:%M:%S'))
        if _time:
            try:
                time_str = time.strftime(time_format, time.localtime(_time))
            except:
                logger.debug('转换时间格式出错！')
        return time_str

    @deal_running_task_arg('批量重命名')
    def do_rename(self):
        """重命名"""
        src_path = self.src_dir.get()
        self.pb1["maximum"] = len(self.new_old_tuple_list)
        new_old_record = {}  # 记录新旧文件名 格式{new_path:old_path,}
        failed_list = []  # 记录重命名失败
        time_now_str = common_utils.get_times_now().get('time_num_str')
        dirName = os.path.basename(src_path)
        path_failed_record = os.path.join(settings.RECORD_DIR, '%s_renameFailed_%s.txt' % (dirName, time_now_str))  # 移动失败的文件的记录路径
        path_new_old_record = os.path.join(settings.RECORD_DIR, '%s_new_old_record_%s.txt' % (dirName, time_now_str))  # 移动成功的文件的新旧文件名记录路径
        had_existed_count = 0  # 已有重名重复路径文件计数
        # 方式一：重新遍历文件获取文件名/目录名信息进行重命名
        # 方式二：直接用之前rename_preview得到的self.new_old_tuple_list进行重命名操作
        self.new_old_tuple_list.reverse()  # 反转目录列表 避免先修改顶级目录名导致子目录路径无法找到
        # logger.debug(self.new_old_tuple_list)
        for new_path, old_path in self.new_old_tuple_list:
            try:
                logger.debug(old_path + '  >>>  ' + new_path)
                os.rename(old_path, new_path)
                new_old_record[new_path] = old_path
            except Exception as e:
                if os.path.exists(new_path):
                    had_existed_count += 1
                logger.debug("Error: " + str(e))
                failed_list.append(old_path)
            self.pb1["value"] += 1

        log_msg = ""
        if len(new_old_record):
            msg = '共重命名'
            if len(self.result["dirs"]):
                msg += " %s 个目录！" % len(self.result["dirs"])
            if len(self.result["files"]):
                msg += " %s 个文件！" % len(self.result["files"])
            logger.debug(msg)
            with open(path_new_old_record, 'a', encoding='utf-8') as f:
                for key, value in new_old_record.items():
                    f.write("%s\t%s\n" % (key, value))
            logger.debug("记录写出到%s" % path_new_old_record)
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
            logger.info('【重命名】  %s' % log_msg)
        self.scr2.insert(tk.END, '\n\n\n\n%s' % msg)
        self.scr2.see(tk.END)
        self.record_path = path_new_old_record  # 记录重命名记录
        mBox.showinfo("完成", "重命名操作完成!")

    @deal_running_task_arg('撤销重命名')
    def undo_rename(self):
        """撤销重命名"""
        # 读取记录
        if self.record_path is None:
            return
        with open(self.record_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
        failed_list = []  # 记录重命名失败
        time_now_str = common_utils.get_times_now().get('time_num_str')
        path_failed_record = os.path.join(settings.RECORD_DIR, 'undo_renameFailed_%s.txt' % time_now_str)  # 撤销重命名失败
        succ_count = 0  # 撤销重命名成功数
        for item in content:
            new_path, old_path = item.strip().split('\t')
            try:
                os.rename(new_path, old_path)
                succ_count += 1
            except Exception as e:
                logger.debug('撤销重命名失败！ 文件：{}，异常：{}'.format(new_path, e))
                failed_list.append((new_path, old_path))

        log_msg = "根据 {} ，撤销重命名操作完成！ ".format(self.record_path)
        if len(failed_list):
            out_msg = ''
            for new_path, old_path in failed_list:
                out_msg += '{}\t{}\n'.format(new_path, old_path)
            with open(path_failed_record, 'w', encoding='utf-8') as f:
                f.write(out_msg)
            log_msg += ' {} 个文件撤销重命名失败，记录到 {}'.format(len(failed_list), path_failed_record)
        time_str = common_utils.get_times_now().get('time_str')
        logger.info('【撤销重命名】  %s' % log_msg)
        self.scr2.insert(tk.END, '\n\n\n\n%s  %s\n' % (time_str, log_msg))
        self.scr2.see(tk.END)
        self.btn_undo_rename.config(state=tk.DISABLED)
        self.btn_rename.config(state=tk.NORMAL)
        mBox.showinfo("完成", "撤销重命名完成!")

    def createPage(self):
        self.l_title["text"] = "批量重命名"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=4)
        ttk.Label(self.f_input, text='搜索语句:').grid(row=1, pady=5)
        ttk.Entry(self.f_input, textvariable=self.search_str).grid(row=1, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="搜索", command=self.deal_search).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=2, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='设置模式:').grid(row=0, pady=5)
        ttk.Checkbutton(self.f_input_option, text="操作文件夹", variable=self.dir_flag, onvalue=True, offvalue=False).grid(
            row=0, column=1)
        ttk.Checkbutton(self.f_input_option, text="操作文件", variable=self.file_flag, onvalue=True, offvalue=False).grid(
            row=0, column=2)
        ttk.Checkbutton(self.f_input_option, text="操作后缀名", variable=self.mod_ext_flag, onvalue=True, offvalue=False).grid(
            row=0, column=3)
        ttk.Checkbutton(self.f_input_option, text="按自然数排序", variable=self.natsort_flag, onvalue=True, offvalue=False).grid(row=0, column=4)
        ttk.Checkbutton(self.f_input_option, text="递归", variable=self.rec_flag, onvalue=True, offvalue=False).grid(row=0, column=5)
        ttk.Checkbutton(self.f_input_option, text="匹配后缀名", variable=self.search_ext_flag, onvalue=True, offvalue=False).grid(row=0, column=6)
        ttk.Checkbutton(self.f_input_option, text="高亮显示", variable=self.light_flag, onvalue=True, offvalue=False).grid(row=0, column=7)
        ttk.Label(self.f_input_option, text="匹配模式:").grid(row=1, column=0)
        ttk.Radiobutton(self.f_input_option, text="简单匹配", variable=self.search_mode, value='1', command=self.invoke_ingorecase).grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="精确匹配", variable=self.search_mode, value='2', command=self.invoke_ingorecase).grid(row=1, column=2)
        ttk.Radiobutton(self.f_input_option, text="正则匹配", variable=self.search_mode, value='3', command=self.invoke_ingorecase).grid(row=1, column=3, sticky=tk.E)
        self.search_mode.set('1')
        self.btn_chk_ignore_case = ttk.Checkbutton(self.f_input_option, text="忽略大小写差异", variable=self.ignore_case_flag, onvalue=True, offvalue=False, state=tk.DISABLED)
        self.btn_chk_ignore_case.grid(row=1, column=4)
        self.f_input_option2 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option2.grid(row=4, columnspan=2, sticky=tk.EW)
        ttk.Label(self.f_input_option2, text='命名模式:').grid(row=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="替换字符", variable=self.rename_mode, value='1', command=self.invoke_entry).grid(
            row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="插入字符", variable=self.rename_mode, value='2', command=self.invoke_entry).grid(
            row=1, column=2, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="插入编号", variable=self.rename_mode, value='3', command=self.invoke_entry).grid(
            row=1, column=3, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="插入时间", variable=self.rename_mode, value='4', command=self.invoke_entry).grid(
            row=1, column=4, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="删除字符", variable=self.rename_mode, value='8', command=self.invoke_entry).grid(
            row=1, column=5, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="文件名重构", variable=self.rename_mode, value='9', command=self.invoke_entry).grid(
            row=2, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="文件名大写", variable=self.rename_mode, value='5', command=self.invoke_entry).grid(
            row=2, column=2, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="文件名小写", variable=self.rename_mode, value='6', command=self.invoke_entry).grid(
            row=2, column=3, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="大小写互换", variable=self.rename_mode, value='7', command=self.invoke_entry).grid(
            row=2, column=4, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="插入视频时长", variable=self.rename_mode, value='10', command=self.invoke_entry).grid(
            row=1, column=6, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="插入分辨率", variable=self.rename_mode, value='11', command=self.invoke_entry).grid(
            row=1, column=7, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option2, text="后缀名还原", variable=self.rename_mode, value='12', command=self.invoke_entry).grid(
            row=2, column=5, sticky=tk.W)
        self.rename_mode.set('1')
        self.f_input_n_s = ttk.Frame(self.f_input_option2)  # 选项容器
        self.f_input_n_s.grid(row=3, columnspan=9, sticky=tk.EW)
        self.f_input_n = ttk.Frame(self.f_input_option2)  # 选项容器
        self.f_input_n.grid(row=4, column=0, columnspan=12, sticky=tk.EW)
        ttk.Label(self.f_input_n_s, text='新字符串:').grid(row=1, column=0, pady=5)
        self.e_new_str = ttk.Entry(self.f_input_n_s, textvariable=self.new_str, width=80)
        self.e_new_str.grid(row=1, column=1, columnspan=8)
        ttk.Label(self.f_input_n, text='插入位置:').grid(row=2, column=0)
        self.e_index = ttk.Entry(self.f_input_n, textvariable=self.index, width=8)
        self.e_index.grid(row=2, column=1, sticky=tk.EW)
        ttk.Label(self.f_input_n, text='编号初始值:').grid(row=2, column=2)
        self.e_start_num = ttk.Entry(self.f_input_n, textvariable=self.start_num, width=10)
        self.e_start_num.grid(row=2, column=3, sticky=tk.EW)
        ttk.Label(self.f_input_n, text='零位数:').grid(row=2, column=4, sticky=tk.EW)
        self.e_zero_num = ttk.Entry(self.f_input_n, textvariable=self.zero_num, width=10)
        self.e_zero_num.grid(row=2, column=5, sticky=tk.EW)
        ttk.Label(self.f_input_n, text=' 删除[').grid(row=2, column=6)
        self.e_del_index_start = ttk.Entry(self.f_input_n, textvariable=self.del_index_start, width=5)
        self.e_del_index_start.grid(row=2, column=7)
        ttk.Label(self.f_input_n, text='至').grid(row=2, column=8)
        self.e_del_index_end = ttk.Entry(self.f_input_n, textvariable=self.del_index_end, width=5)
        self.e_del_index_end.grid(row=2, column=9)
        ttk.Label(self.f_input_n, text=']').grid(row=2, column=10)
        ttk.Label(self.f_input_n, text='时间类型:').grid(row=3, column=0, sticky=tk.EW, pady=5)
        self.optionChosen = ttk.Combobox(self.f_input_n, width=8, textvariable=self.time_option)
        self.optionChosen['values'] = ['修改时间', '创建时间', '拍摄时间']
        self.optionChosen.grid(row=3, column=1)
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        self.optionChosen.config(state='readonly')  # 设为只读模式
        ttk.Label(self.f_input_n, text='时间格式:').grid(row=3, column=2, sticky=tk.W)
        self.e_time_format = ttk.Entry(self.f_input_n, textvariable=self.time_format, width=30)
        self.e_time_format.grid(row=3, column=3, columnspan=3, sticky=tk.EW)

        self.f_input_option3 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option3.grid(row=4, column=3, sticky=tk.E)
        self.f_input_option4 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option4.grid(row=4, column=4)
        ttk.Button(self.f_input_option3, text='清除', command=self.clear_all).grid(row=0, column=1)
        ttk.Button(self.f_input_option4, text="预览", command=self.rename_preview).grid(row=0, column=2)
        self.btn_undo_rename = ttk.Button(self.f_input_option3, text='撤销重命名', command=self.undo_rename, state=tk.DISABLED)
        self.btn_undo_rename.grid(row=1, column=1)
        self.btn_rename = ttk.Button(self.f_input_option4, text='重命名', command=self.run, state=tk.DISABLED)
        self.btn_rename.grid(row=1, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=5)
        ttk.Label(self.f_content, text='原文件名: ').grid(row=1, pady=5)
        scrolW = 58
        scrolH = 28
        self.scr1 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr1.grid(column=0, row=2, sticky=tk.NSEW)
        ttk.Label(self.f_content, text='新文件名: ').grid(row=1, column=1, pady=5)
        self.scr2 = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr2.grid(column=1, row=2, sticky=tk.NSEW)
        self.invoke_entry()  # 设置输入框状态
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def invoke_ingorecase(self):
        """激活忽略大小写单选框"""
        if self.search_mode.get() == '3':
            self.btn_chk_ignore_case.config(state=tk.NORMAL)
        else:
            self.ignore_case_flag.set(False)
            self.btn_chk_ignore_case.config(state=tk.DISABLED)

    def invoke_entry(self):
        """激活输入框"""
        rename_mode = self.rename_mode.get()
        total = [self.e_new_str, self.e_index, self.e_start_num, self.e_zero_num, self.optionChosen,
                 self.e_del_index_start, self.e_del_index_end, self.e_time_format]
        invoke_list = []
        if rename_mode == '1':  # 替换字符
            invoke_list = [self.e_new_str]
        if rename_mode == '2':  # 插入字符
            invoke_list = [self.e_new_str, self.e_index]
        if rename_mode == '3':  # 插入编号
            invoke_list = [self.e_new_str, self.e_index, self.e_start_num, self.e_zero_num]
        if rename_mode == '4':  # 插入时间
            invoke_list = [self.e_new_str, self.e_index, self.optionChosen, self.e_time_format]
        if rename_mode == '8':  # 删除字符
            invoke_list = [self.e_del_index_start, self.e_del_index_end]
        if rename_mode == '9':  # 文件名重构
            invoke_list = [self.e_new_str, self.e_start_num, self.e_zero_num, self.optionChosen, self.e_time_format]
        if rename_mode in ('10', '11'):  # 插入视频时长、视频、图片分辨率
            invoke_list = [self.e_new_str, self.e_index]
        if rename_mode == '10':  # 设置默认数据
            self.new_str.set(r'_%Hh%Mm%Ss')
        if rename_mode == '11':  # 设置默认数据
            self.new_str.set(r'_%widthx%height')
        if rename_mode in ('4', '9'):  # 设置默认时间格式模型
            self.time_format.set(r'%Y%m%d_%H%M%S')
        # 设置输入框状态
        for item in total:
            if item in invoke_list:
                item.config(state=tk.NORMAL)
            else:
                item.config(state=tk.DISABLED)

    def selectPath(self):
        path_ = askdirectory()
        self.src_dir.set(path_)
        self.btn_rename.config(state=tk.DISABLED)

    def clear(self):
        """用于清除上次计算的数据"""
        self.scr1.delete(1.0, 'end')  # 清空文本区
        self.scr2.delete(1.0, 'end')  # 清空文本区
        self.result = {"dirs": [], "files": []}  # 存储搜索到的结果
        self.new_old_tuple_list = []  # 记录新旧文件名 格式[(new_path, old_path)]
        self.preview_result = {"dirs": [], "files": []}
        self.pb1["value"] = 0
        self.record_path = None
        self.btn_rename.config(state=tk.DISABLED)
        self.btn_undo_rename.config(state=tk.DISABLED)

    def clear_all(self):
        """用于清除所有数据"""
        self.clear()
        self.src_dir.set('')
        self.dst_dir.set('')
        self.search_str.set('')
        self.new_str.set('')
        self.start_num.set('0')  # 初始值
        self.zero_num.set('0')  # 零位数，左边填充零个数
        self.index.set('0')
        self.time_format.set(r'%Y%m%d_%H%M%S')

    def run(self):
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.do_rename)
        t.daemon = True
        t.start()


class GetImgFrame(BaseFrame):
    """提取视频帧图像"""
    def __init__(self, master=None):
        super().__init__(master)
        self.ffmpeg_path = settings.FFMPEG_PATH
        self.inputNum = tk.StringVar()  # 帧率或者秒数
        self.continue_flag = tk.BooleanVar()  # 是否继续上次进度
        self.get_mode_flag = tk.BooleanVar()  # 提取方式 True 按秒提取 False 按帧提取
        self.limit_frame_flag = tk.BooleanVar()  # 是否限定帧范围 True 限制
        self.src_dir = tk.StringVar()  # 视频路径
        self.dst_dir = tk.StringVar()  # 图像路径
        self.frameNum = tk.IntVar()  # 间隔帧数，即每隔n帧提取一次帧图像
        self.frame_start = tk.IntVar()  # 限定帧范围起始
        self.frame_stop = tk.IntVar()  # 限定帧范围结束
        self.get_photo_by_sec_flag = tk.BooleanVar()  # 是否按秒数提取图片，True 按秒 False 按帧数
        self.get_photo_by_sec_flag.set(True)  # 默认按时间点提取图像
        self.inputNum.set(3)  # 设置默认值
        self.continue_flag.set(False)  # 设置默认选中否
        self.get_mode_flag.set(True)
        self.is_thread = tk.BooleanVar()  # 开启多线程加速 True 开启 
        self.is_thread.set(False)  # 设置默认选中否
        self.thread_num = tk.IntVar()  # 线程数
        self.thread_num.set(3)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "提取视频帧图像"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        self.f_input_option1 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option1.grid(row=0, columnspan=3, sticky=tk.EW)
        self.f_input_option2 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option2.grid(row=1, columnspan=3, sticky=tk.EW)
        self.f_input_option3 = ttk.Frame(self.f_input_option2)  # 选项容器
        self.f_input_option3.grid(row=1, column=4, sticky=tk.EW)
        ttk.Radiobutton(self.f_input_option1, text="按秒提取", variable=self.get_mode_flag, value=True, command=self.invoke_num).grid(
            row=0, column=0, pady=5)
        ttk.Label(self.f_input_option1, text='提取第 ').grid(row=0, column=1, sticky=tk.W)
        self.e_num_s = ttk.Entry(self.f_input_option1, textvariable=self.inputNum, width=8, justify=tk.CENTER)
        self.e_num_s.grid(row=0, column=2, sticky=tk.W)
        ttk.Label(self.f_input_option1, text=' 秒图像(负值为倒数时间，即倒数第三秒为-3)').grid(row=0, column=3, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option1, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(row=0, column=6, padx=10)
        ttk.Checkbutton(self.f_input_option1, text="开启多线程", variable=self.is_thread, onvalue=True, offvalue=False).grid(row=0, column=7)
        ttk.Radiobutton(self.f_input_option2, text="按帧提取", variable=self.get_mode_flag, value=False, command=self.invoke_num).grid(
            row=1, column=0, sticky=tk.W)
        ttk.Label(self.f_input_option2, text='每间隔 ').grid(row=1, column=1, sticky=tk.W)
        self.e_num_f = ttk.Entry(self.f_input_option2, textvariable=self.frameNum, width=8, justify=tk.CENTER)
        self.e_num_f.grid(row=1, column=2, sticky=tk.W)
        ttk.Label(self.f_input_option2, text=' 帧提取一帧图像').grid(row=1, column=3, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option3, text='限定帧范围，从: ', variable=self.limit_frame_flag, onvalue=True, offvalue=False, command=self.invoke_type).grid(row=1, column=0, padx=10)
        self.e_sub_start = ttk.Entry(self.f_input_option3, textvariable=self.frame_start, width=8)
        self.e_sub_start.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(self.f_input_option3, text=' <-至-> ').grid(row=1, column=2, sticky=tk.W)
        self.e_sub_stop = ttk.Entry(self.f_input_option3, textvariable=self.frame_stop, width=8)
        self.e_sub_stop.grid(row=1, column=3, sticky=tk.W)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 34
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看帧图像", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.invoke_type()  # 设置限定帧输入框状态
        self.invoke_num()  # 设置帧数秒数输入框状态
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def invoke_num(self):
        """激活输入帧数或者秒数输入框"""
        if self.get_mode_flag.get():
            self.e_num_s.config(state=tk.NORMAL)
            self.e_num_f.config(state=tk.DISABLED)
            # 设置限定帧范围输入框状态
            self.limit_frame_flag.set(False)
            self.invoke_type()
        else:
            self.e_num_f.config(state=tk.NORMAL)
            self.e_num_s.config(state=tk.DISABLED)

    def invoke_type(self):
        """激活限定帧输入框"""
        if self.limit_frame_flag.get():
            self.e_sub_start.config(state=tk.NORMAL)
            self.e_sub_stop.config(state=tk.NORMAL)
        else:
            self.e_sub_start.config(state=tk.DISABLED)
            self.e_sub_stop.config(state=tk.DISABLED)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[Img]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.btn_show.config(state=tk.DISABLED)

    def do_get_img_by_sec(self):
        """单线程从视频提取图片"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        extract_time_point = self.inputNum.get()
        continue_flag = self.continue_flag.get()
        extract_time_point = float(extract_time_point.strip())
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        start_time = time_res.get('timestamp')
        self.scr.insert("end", "%s  开始遍历文件目录....\n" % time_str)
        # 遍历获取所有视频路径
        video_list = common_utils.get_files_by_filetype(src_dir, 'video')
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        tmp_time = time_res.get('timestamp')
        msg1 = "遍历 %s 完成,共发现文件 %s 个,用时 %ss" % (src_dir, len(video_list), tmp_time - start_time)
        self.scr.insert("end", "\n%s  %s\n\t开始提取视频图像....\n" % (time_str, msg1))
        self.pb1["value"] = 0  # 重置进度条
        self.pb1["maximum"] = len(video_list)  # 总项目数
        # 提取所有视频的第n秒图像,单线程完成
        error_count = 0  # 记录操作失败个数
        failed_dict = {}  # 记录失败文件信息 ， 数据格式 {filepath: errormsg,}
        for pathIn in video_list:
            pathOut = pathIn.replace(src_dir, dst_dir) + "_{}sec.jpg".format(extract_time_point)
            try:
                video_utils.get_img_from_video_by_ffmpeg(pathIn, pathOut, extract_time_point, continue_flag)
                self.scr.insert("end", "%s 帧图像提取完成!\n" % pathIn)
            except NameError as e:
                error_count += 1
                failed_dict[pathIn] = e
                error_msg = "【error:%s】%s,%s" % (error_count, pathIn, e)
                self.scr.insert("end", "%s\n" % error_msg, "error_tag")
                self.scr.tag_config('error_tag', foreground="Crimson")
            self.pb1["value"] += 1
        self.scr.see('end')
        # 输出显示操作失败信息
        if len(failed_dict):
            self.scr.insert("end", "\n操作 %s 个文件失败，失败信息如下：\n" % error_count, 'info')
            i = 0  # 记录文件编号
            for filepath in failed_dict:
                i += 1
                self.scr.insert("end","ERROR:(%s/%s)  %s 操作过程出错！错误：%s\n" % (i, error_count, filepath, failed_dict[filepath]),'error')
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        complete_time = time_res.get('timestamp')
        msg = "单线程提取图片完成，总文件数: %s " % len(video_list)
        if error_count:
            msg += "失败数: %s" % error_count
        msg += ",提取图片用时 %.3f 秒,总用时  %.3f 秒" % (complete_time - tmp_time, complete_time - start_time)
        total_msg = "提取目录 %s 下视频第 %s 秒图像到目录 %s 下完成！用时 %.3f 秒" % (src_dir, extract_time_point, dst_dir, time.time() - start_time)
        self.scr.insert("end", "\n\n%s  %s\n" % (time_str, msg))
        self.scr.tag_config('info', font=('microsoft yahei', 16, 'bold'))
        self.scr.tag_config('error', foreground="FireBrick")
        self.scr.see('end')
        logger.info('【提取视频帧图像】  %s' % total_msg)
        mBox.showinfo('任务完成', "提取视频帧图像完成!")

    def get_img_by_sec(self):
        """按秒提取"""
        video_dir = self.src_dir.get()
        img_dir = self.dst_dir.get()
        extract_time_point = float(self.inputNum.get())
        is_continue = self.continue_flag.get()
        if self.is_thread.get() is True:
            video_utils.get_img_from_video(self, video_dir, img_dir, extract_time_point, is_continue)  # 多线程
        else:
            self.do_get_img_by_sec()

    def get_img_by_frame(self):
        """按帧提取"""
        video_dir = self.src_dir.get()
        img_dir = self.dst_dir.get()
        frameNum = self.frameNum.get()
        frame_start = self.frame_start.get()
        frame_stop = self.frame_stop.get()
        vf_str = r"select=not(mod(n\,{}))".format(frameNum)
        time_now = time.localtime()
        time_str = time.strftime(r"%Y-%m-%d %H:%M:%S", time_now)
        self.scr.insert('end', '{}  开始遍历文件目录并提取视频帧图像....'.format(time_str))
        pathOutDir = os.path.join(img_dir, "{}_{}_{}_{}".format(time.strftime(r"%Y%m%d%H%M%S", time_now), frameNum, frame_start, frame_stop))
        if not os.path.exists(pathOutDir):
            os.makedirs(pathOutDir)
        if self.limit_frame_flag.get():
            if frame_stop >= frame_start:
                vf_str = r'select=between(n\,{}\,{})*not(mod(n\,{}))'.format(frame_start, frame_stop, frameNum)
            else:
                vf_str = r"select=(gte(n\,{}))*not(mod(n\,{}))".format(frame_start, frameNum)
        # command = [self.ffmpeg_path, '-i', pathIn, '-vf', 'select=(gte(n\,30))*not(mod(n\,30))', '-vsync', '0', pathOut]
        # command = [self.ffmpeg_path, '-i', pathIn, '-vf', 'select=between(n\,0\,100)*not(mod(n\,30))', '-vsync', '0', pathOut]
        video_list = common_utils.get_files_by_filetype(video_dir, 'video')
        msg1 = "遍历 %s 完成,共发现文件%s个!" % (video_dir, len(video_list))
        self.scr.insert("end", "\n%s  %s\n\t开始提取视频图像....\n" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), msg1))
        self.pb1["value"] = 0  # 重置进度条
        self.pb1["maximum"] = len(video_list)  # 总项目数
        for pathIn in video_list:
            pathOut = os.path.join(pathOutDir, "{}_%05d.jpg".format(os.path.basename(pathIn)))
            command = [self.ffmpeg_path, '-i', pathIn, '-vf', vf_str, '-vsync', '0', pathOut]  # 命令
            subprocess.call(command, shell=True)
            self.pb1['value'] += 1
            self.scr.insert('end', '\n{}'.format(pathIn))
        total_msg = "提取目录 {} 下从第 {} 帧开始,至第 {} 帧,每 {} 帧提取 1 视频帧图像到 {} 完成！".format(video_dir, frame_start, frame_stop, frameNum, pathOutDir)
        self.scr.insert('end', '\n\n{}  {}\n'.format(common_utils.get_times_now().get('time_str'), total_msg))
        self.scr.see(tk.END)
        logger.info('【提取视频帧图像】  ' + total_msg)

    @deal_running_task_arg('提取视频帧图像')
    def deal_get_img(self):
        if self.get_mode_flag.get():
            self.get_img_by_sec()
        else:
            self.get_img_by_frame()
        self.btn_show.config(state=tk.NORMAL)

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        # 校验输入秒数
        if common_utils.check_floatNum(self.inputNum.get()) is False:
            mBox.showerror("错误", "输入秒数有误! 请检查是否包含非数字字符!")
            return
        t = threading.Thread(target=self.deal_get_img)
        t.daemon = True
        t.start()


class CalImgSimFrame(BaseFrame):
    """计算图片相似度"""
    def __init__(self, master=None):
        super().__init__(master)
        self.threshold = tk.DoubleVar()
        self.move_option = tk.StringVar()  # 移动文件的模式
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.db_flag = tk.BooleanVar()  # 使用数据库记录加速， True 使用数据库数据  False 重新计算
        self.db_flag.set(True)
        self.sub_flag = tk.BooleanVar()  # 仅计算相邻图片相似度， True 仅计算相邻图片 False 计算所有图片
        self.sub_flag.set(False)
        self.is_complete = False  # 用来标记所有计算任务是否完成，以防止进度条子线程陷入死循环
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "计算图片相似度"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1): ').grid(row=0, pady=5)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=8, justify=tk.CENTER).grid(row=0, column=1, sticky=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self.f_input_option, text='  导出方式: ').grid(row=0, column=2, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.move_option, value="copy").grid(row= 0, column=3)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.move_option, value="move").grid(row= 0, column=4)
        self.move_option.set("copy")  # 设置默认选中否
        # ttk.Button(self.f_input, text="导出phash记录", command=self.export_phash).grid(row=3, column=1)
        ttk.Checkbutton(self.f_input_option, text="使用数据库加速", variable=self.db_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=5)
        ttk.Checkbutton(self.f_input_option, text="仅计算相邻图片", variable=self.sub_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=6)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 36
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看相似图片", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10)
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[相似图片]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.record_path = None
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restore.config(state=tk.DISABLED)

    @deal_running_task_arg('查找相似图片')
    def deal_image_similarity(self):
        self.record_path = None  # 用于记录相似文件new_old_record文件的路径
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        deal_img_mode = self.move_option.get()
        db_flag = self.db_flag.get()
        threshold = float(self.threshold.get())
        image_utils.find_sim_img(self, src_dir, dst_dir, threshold, deal_img_mode, db_flag)

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        if common_utils.check_threNum(self.threshold.get()) is not True:
            mBox.showerror("错误", "相似度阈值须为0~1之间的小数!")
            return
        t = threading.Thread(target=self.deal_image_similarity)
        t.daemon = True
        t.start()


class CalVideoSimFrame(BaseFrame):
    """计算视频相似度"""

    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()  # 输入秒数或者帧数
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.move_option = tk.StringVar()  # 移动文件的模式
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.db_flag = tk.BooleanVar()  # 使用数据库记录加速， True 使用数据库数据  False 重新计算
        self.db_flag.set(True)
        self.inputNum.set(3)  # 设置默认值为3
        self.threshold.set(0.98)  # 设置默认值为0.98
        self.move_option.set("copy")  # 设置默认选中否
        self.continue_flag.set(False)  # 设置默认选中否
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "查找相似视频"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='比对第 ').grid(row=0, column=0, pady=5)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=8, justify=tk.CENTER).grid(row=0, column=1)
        ttk.Label(self.f_input_option, text=' 秒图像(负值为倒数时间) ').grid(row=0, column=2)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1): ').grid(row=0, column=3, padx=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=5, justify=tk.CENTER).grid(row=0, column=4) 
        ttk.Label(self.f_input_option, text='导出方式: ').grid(row=0, column=5, padx=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.move_option, value="copy").grid(row=0, column=6)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.move_option, value="move").grid(row=0, column=7)
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=8, padx=10)
        ttk.Checkbutton(self.f_input_option, text="使用数据库加速", variable=self.db_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=9)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 36
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看相似视频", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10)
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
            dst_path = dir_path + '_[相似视频]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.record_path = None
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restore.config(state=tk.DISABLED)

    @deal_running_task_arg('查找相似视频')
    def deal_video_similarity(self, src_dir_path, dst_dir_path, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag):
        video_utils.find_sim_video(self, src_dir_path, dst_dir_path, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag)

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        # 校验输入秒数
        if common_utils.check_floatNum(self.inputNum.get()) is False:
            mBox.showerror("错误", "输入秒数有误! 请检查是否包含非数字字符!")
            return
        if common_utils.check_threNum(self.threshold.get()) is not True:
            mBox.showerror("错误", "相似度阈值须为0~1之间的小数!")
            return
        src_path = self.src_dir.get()
        dst_path = self.dst_dir.get()
        continue_flag = self.continue_flag.get()
        deal_video_mode = self.move_option.get()
        extract_time_point = self.inputNum.get()
        db_flag = self.db_flag.get()
        threshold = float(self.threshold.get())
        extract_time_point = float(extract_time_point)
        args = (src_path, dst_path, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag)
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.daemon = True
        t.start()


class SearchImgFrame(BaseFrame):
    """以图搜图"""

    def __init__(self, master=None):
        super().__init__(master)
        self.threshold = tk.DoubleVar()
        self.move_option = tk.StringVar()  # 操作文件的方式 复制或者剪切
        self.eg_dir = tk.StringVar()  # 样本目录
        self.dst_dir = tk.StringVar()  # 保存目录
        self.src_dir = tk.StringVar()  # 原有图片路径
        self.mode = tk.BooleanVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.db_flag = tk.BooleanVar()  # 使用数据库记录加速， True 使用数据库数据  False 重新计算
        self.db_flag.set(True)
        self.mode.set(True)  # 设置默认值
        self.threshold.set(0.98)  # 设置默认值为0.98
        self.move_option.set("copy")  # 设置默认选中否
        self.createPage()

    def selectPath3(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.src_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "以图搜图"
        ttk.Label(self.f_input, text='样品目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.eg_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='原有图片: ').grid(row=2, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=2, column=1,sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1):').grid(row=1, pady=5)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=8, justify=tk.CENTER).grid(row=1, column=1)
        ttk.Label(self.f_input_option, text='导出方式:').grid(row=1, column=3, padx=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.move_option, value="copy").grid(row=1, column=4)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.move_option, value="move").grid(row=1, column=5)
        ttk.Checkbutton(self.f_input_option, text="使用数据库加速", variable=self.db_flag, onvalue=True,
                        offvalue=False).grid(row=1, column=6, padx=10)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 33
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看相似图片", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10)
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.eg_dir.set(dir_path)
            dst_path = dir_path + '_[以图搜图]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.record_path = None
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restore.config(state=tk.DISABLED)

    @deal_running_task_arg('以图搜图')
    def deal_image_similarity(self):
        eg_dir = self.eg_dir.get()
        src_dir = self.src_dir.get()
        save_dir = self.dst_dir.get()
        deal_img_mode = self.move_option.get()
        db_flag = self.db_flag.get()
        threshold = float(self.threshold.get())
        image_utils.search_img_by_img(self, eg_dir, src_dir, save_dir, threshold, deal_img_mode, db_flag)

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.eg_dir, self.src_dir, self.dst_dir)
        if not flag:
            return
        if common_utils.check_threNum(self.threshold.get()) is not True:
            mBox.showerror("错误", "相似度阈值须为0~1之间的小数!")
            return
        t = threading.Thread(target=self.deal_image_similarity)
        t.daemon = True
        t.start()


class SearchVideoFrame(BaseFrame):
    """以视频搜索相似视频"""

    def __init__(self, master=None):
        super().__init__(master)
        self.inputNum = tk.StringVar()
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.move_option = tk.StringVar()  # 移动文件的模式
        self.src_dir = tk.StringVar()
        self.eg_dir = tk.StringVar()  # 原有视频路径或者phash json
        self.mode = tk.StringVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.dst_dir = tk.StringVar()
        self.record_path = None  # 记录导出文件的new_old_record 路径
        self.db_flag = tk.BooleanVar()  # 使用数据库记录加速， True 使用数据库数据  False 重新计算
        self.db_flag.set(True)
        self.mode.set(True)  # 设置默认值
        self.inputNum.set(3)  # 设置默认值为3
        self.threshold.set(0.98)  # 设置默认值为0.98
        self.move_option.set("copy")  # 设置默认选中剪切
        self.continue_flag.set(False)  # 设置默认选中否
        self.createPage()

    def selectPath3(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.eg_dir.set(path_)

    def createPage(self):
        self.l_title["text"] = "以视频搜索视频"
        ttk.Label(self.f_input, text='样本目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.eg_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        ttk.Label(self.f_input, text='原有视频: ').grid(row=2, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=2, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath3).grid(row=2, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_input_option, text='比对第 ').grid(row=0, column=0, pady=5)
        ttk.Entry(self.f_input_option, textvariable=self.inputNum, width=8, justify=tk.CENTER).grid(row=0, column=1)
        ttk.Label(self.f_input_option, text='秒图像(负值为倒数时间) ').grid(row=0, column=2)
        ttk.Label(self.f_input_option, text='相似度阈值(0~1):').grid(row=0, column=3, padx=10)
        ttk.Entry(self.f_input_option, textvariable=self.threshold, width=8, justify=tk.CENTER).grid(row=0, column=4)
        ttk.Label(self.f_input_option, text='导出方式:').grid(row=0, column=5, padx=10)
        ttk.Radiobutton(self.f_input_option, text="复制", variable=self.move_option, value="copy").grid(row=0, column=6)
        ttk.Radiobutton(self.f_input_option, text="剪切", variable=self.move_option, value="move").grid(row=0, column=7)
        ttk.Checkbutton(self.f_input_option, text="继续上次进度", variable=self.continue_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=8, padx=10)
        ttk.Checkbutton(self.f_input_option, text="使用数据库加速", variable=self.db_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=9)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=4, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 33
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看相似视频", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.btn_restore = ttk.Button(self.f_bottom, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1, pady=10)
        self.btn_undo_restore = ttk.Button(self.f_bottom, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.eg_dir.set(dir_path)
            dst_path = dir_path + '_[以视频搜视频]'
            if not os.path.exists(dst_path):
                self.dst_dir.set(dst_path)

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.record_path = None
        self.btn_show.config(state=tk.DISABLED)
        self.btn_restore.config(state=tk.DISABLED)

    @deal_running_task_arg('以视频搜相似视频')
    def deal_video_similarity(self, eg_path, src_dir, dst_dir, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag):
        video_utils.search_video(self, eg_path, src_dir, dst_dir, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag)

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.eg_dir, self.src_dir, self.dst_dir)
        if not flag:
            return
        # 校验输入秒数
        if common_utils.check_floatNum(self.inputNum.get()) is False:
            mBox.showerror("错误", "输入秒数有误! 请检查是否包含非数字字符!")
            return
        if common_utils.check_threNum(self.threshold.get()) is not True:
            mBox.showerror("错误", "相似度阈值须为0~1之间的小数!")
            return
        src_dir = self.src_dir.get()
        eg_dir = self.eg_dir.get()
        save_dir = self.dst_dir.get()
        deal_video_mode = self.move_option.get()
        continue_flag = self.continue_flag.get()
        db_flag = self.db_flag.get()
        threshold = float(self.threshold.get())
        extract_time_point = float(self.inputNum.get())
        args = (eg_dir, src_dir, save_dir, extract_time_point, continue_flag, threshold, deal_video_mode, db_flag)
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.daemon = True
        t.start()


class GetAudioFrame(BaseFrame):
    """从视频中提取音频或者转换音频格式"""

    def __init__(self, master=None):
        super().__init__(master)
        self.continue_flag = tk.BooleanVar()
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
        self.file_type.set('')  # 音频格式  mp3 aac
        self.sampling_rate = tk.StringVar()  # 音频采样率 44100
        self.bitrate = tk.StringVar()  # 音频码率/比特率  128k 192k
        self.chg_fps_flag = tk.BooleanVar()  # 是否修改帧率/采样率输入框
        self.chg_type_flag = tk.BooleanVar()  # 是否修改音频格式
        self.chg_bitrate_flag = tk.BooleanVar()  # 是否修改码率/比特率
        self.cut_time_flag = tk.BooleanVar()  # 是否按时间截取  True按时间截取
        self.cut_time_flag.set(False)
        self.chg_type_flag.set(False)
        self.chg_fps_flag.set(False)
        self.chg_bitrate_flag.set(False)
        self.clear_time_input_flag = tk.BooleanVar()  # 是否清空时间输入框内容
        self.deal_exists_mode = tk.StringVar()  # 处理已存在目标路径的同名文件方式 0.跳过 1.覆盖 2.询问
        self.deal_exists_mode.set('2')
        self.copy_codec_flag = tk.BooleanVar()  # 采用原编码，注意比如视频中音频编码为aac,导出成aac的时候才能勾选，否则会出错，必须保证原音频编码和导出后的音频编码一致否则不能勾选！！！
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.clear_time_input_flag.set(True)  # 设置默认选中
        self.copy_codec_flag.set(False)  # 设置默认选中否
        self.original_mtime_flag.set(True)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "提取/转换音频"
        ttk.Label(self.f_input, text='源目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出目录: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Checkbutton(self.f_input_option, text="修改格式", variable=self.chg_type_flag, onvalue=True,
                        offvalue=False, command=self.invoke_type).grid(row=0, column=0, sticky=tk.W)
        self.e_type = ttk.Entry(self.f_input_option, textvariable=self.file_type, width=10, state=tk.DISABLED)
        self.e_type.grid(row=0, column=1, padx=5)
        ttk.Checkbutton(self.f_input_option, text="修改音频采样率", variable=self.chg_fps_flag, onvalue=True,
                        offvalue=False, command=self.invoke_fps).grid(row=0, column=2, sticky=tk.EW, padx=5)
        self.e_fps = ttk.Entry(self.f_input_option, textvariable=self.sampling_rate, width=8, state=tk.DISABLED)  # 视频帧率输入框
        self.e_fps.grid(row=0, column=3, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="修改音频比特率", variable=self.chg_bitrate_flag, onvalue=True,
                        offvalue=False, command=self.invoke_bitrate).grid(row=0, column=4, sticky=tk.EW, padx=5)
        self.e_bitrate = ttk.Entry(self.f_input_option, textvariable=self.bitrate, width=8, state=tk.DISABLED)  # 视频帧率输入框
        self.e_bitrate.grid(row=0, column=5, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="清空时间输入框内容", variable=self.clear_time_input_flag, onvalue=True,
                        offvalue=False, command=self.clear_time_input).grid(row=0, column=6, sticky=tk.EW, padx=5)
        self.c_copy_codec = ttk.Checkbutton(self.f_input_option, text="采用原编码", variable=self.copy_codec_flag, onvalue=True, offvalue=False)
        self.c_copy_codec.grid(row=0, column=7)
        ttk.Checkbutton(self.f_input_option, text="继承原修改时间", variable=self.original_mtime_flag, onvalue=True, offvalue=False).grid(row=0, column=8)
        self.f_time_option = ttk.Frame(self.f_input)  # 时间输入容器
        self.f_time_option.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Checkbutton(self.f_time_option, text='按时间截取，从: ', variable=self.cut_time_flag, onvalue=True, offvalue=False, command=self.invoke_time).grid(row=1, column=0, pady=10)
        self.e_sub_start_time_h = ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_h, width=5)
        self.e_sub_start_time_h.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=2, pady=10)
        self.e_sub_start_time_m = ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_m, width=5)
        self.e_sub_start_time_m.grid(row=1, column=3, sticky=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=4, pady=10)
        self.e_sub_start_time_s = ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_s, width=5)
        self.e_sub_start_time_s.grid(row=1, column=5, sticky=tk.W)
        ttk.Label(self.f_time_option, text='   至: ').grid(row=1, column=6, pady=10)
        self.e_sub_stop_time_h = ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_h, width=5)
        self.e_sub_stop_time_h.grid(row=1, column=7, sticky=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=8, pady=10)
        self.e_sub_stop_time_m = ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_m, width=5)
        self.e_sub_stop_time_m.grid(row=1, column=9, sticky=tk.W)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=10, pady=10)
        self.e_sub_stop_time_s = ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_s, width=5)
        self.e_sub_stop_time_s.grid(row=1, column=11, sticky=tk.W)
        ttk.Label(self.f_time_option, text='目标路径已存在同名文件：').grid(row=1, column=12, padx=5)
        ttk.Radiobutton(self.f_time_option, text='跳过', variable=self.deal_exists_mode, value=0).grid(row=1, column=13, sticky=tk.EW)
        ttk.Radiobutton(self.f_time_option, text='覆盖', variable=self.deal_exists_mode, value=1).grid(row=1, column=14, sticky=tk.EW)
        ttk.Radiobutton(self.f_time_option, text='询问', variable=self.deal_exists_mode, value=2).grid(row=1, column=15, sticky=tk.EW)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.btn_show = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        self.invoke_time()  # 设置时间输入框锁定状态
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def clear_time_input(self):
        """清除时间输入框内容"""
        for item in self.time_inputs:
            item.set('')

    def invoke_time(self):
        """激活时间输入框"""
        time_input_entrys = [self.e_sub_start_time_h, self.e_sub_start_time_m, self.e_sub_start_time_s,
                            self.e_sub_stop_time_h, self.e_sub_stop_time_m, self.e_sub_stop_time_s]
        if self.cut_time_flag.get():  # 按时间截取
            # 设置默认解锁时间输入框
            for enrty_time in time_input_entrys:
                enrty_time.config(state=tk.NORMAL)
        else:
            # 清除时间输入框内容
            for item in self.time_inputs:
                item.set('')
            # 设置默认锁定时间输入框
            for enrty_time in time_input_entrys:
                enrty_time.config(state=tk.DISABLED)

    def invoke_fps(self):
        """激活音频采样率输入框"""
        if self.chg_fps_flag.get():
            self.sampling_rate.set('44100')
            self.e_fps.config(state=tk.NORMAL)
        else:
            self.sampling_rate.set('')
            self.e_fps.config(state=tk.DISABLED)

    def invoke_bitrate(self):
        """激活音频比特率输入框"""
        if self.chg_bitrate_flag.get():
            self.bitrate.set('192k')
            self.e_bitrate.config(state=tk.NORMAL)
        else:
            self.bitrate.set('')
            self.e_bitrate.config(state=tk.DISABLED)

    def invoke_type(self):
        """激活音频格式输入框"""
        if self.chg_type_flag.get():
            self.e_type.config(state=tk.NORMAL)
            self.file_type.set('mp3')  # 默认修改成mp3格式
            self.copy_codec_flag.set(False)
            self.c_copy_codec.config(state=tk.DISABLED)
        else:
            self.file_type.set('')
            self.e_type.config(state=tk.DISABLED)
            self.copy_codec_flag.set(True)
            self.c_copy_codec.config(state=tk.NORMAL)

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        if self.clear_time_input_flag.get() is True:
            self.clear_time_input()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
        src_dir = self.src_dir.get().strip()
        if os.path.isfile(src_dir):
            self.dst_dir.set(os.path.join(os.path.dirname(src_dir), 'audios'))
        else:
            self.dst_dir.set(os.path.abspath(src_dir) + '_[audio]')

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.btn_show.config(state=tk.DISABLED)

    @deal_running_task_arg('提取|转换音频')
    def deal_get_audio(self):
        """提取音频"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        sampling_rate = common_utils.get_int(self.sampling_rate.get().strip(), None)
        bitrate = self.bitrate.get().strip()
        input_type = self.file_type.get().strip() if self.chg_type_flag.get() else ''  # 输入音频格式
        sub_start_time_h = self.sub_start_time_h.get().strip()  # 获取开始剪切时间
        sub_start_time_m = self.sub_start_time_m.get().strip()  # 获取开始剪切时间
        sub_start_time_s = self.sub_start_time_s.get().strip()  # 获取开始剪切时间
        sub_stop_time_h = self.sub_stop_time_h.get().strip()  # 获取剪切的结束时间
        sub_stop_time_m = self.sub_stop_time_m.get().strip()  # 获取剪切的结束时间
        sub_stop_time_s = self.sub_stop_time_s.get().strip()  # 获取剪切的结束时间
        sub_start_time_h = common_utils.get_int(sub_start_time_h, 0)  # 获取开始剪切时间
        sub_start_time_m = common_utils.get_int(sub_start_time_m, 0)  # 获取开始剪切时间
        sub_start_time_s = common_utils.get_float(sub_start_time_s, 0)  # 获取开始剪切时间
        sub_stop_time_h = common_utils.get_int(sub_stop_time_h, 0)  # 获取剪切的结束时间
        sub_stop_time_m = common_utils.get_int(sub_stop_time_m, 0)  # 获取剪切的结束时间
        sub_stop_time_s = common_utils.get_float(sub_stop_time_s, 0)  # 获取剪切的结束时间
        startPoint = sub_start_time_h * 3600 + sub_start_time_m * 60 + sub_start_time_s
        endPoint = sub_stop_time_h * 3600 + sub_stop_time_m * 60 + sub_stop_time_s
        path_list = []  # 要操作的文件路径
        failed_files = {}  # 操作失败的文件信息 {path: error}
        time_res = common_utils.get_times_now()  # 记录程序开始操作时间
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
        
        get_video_time_msg = "遍历 %s 完成！总共 %s 个文件,用时 %ss\n" % (src_dir, len(path_list), (time.time() - start_time))
        time_str = common_utils.get_times_now().get('time_str')
        self.scr.insert('end', '\n%s  %s\n\t开始处理音频...\n' % (time_str, get_video_time_msg))
        self.pb1["maximum"] = len(path_list)  # 总项目数
        # 开始处理音频
        for pathIn in path_list:
            default_type = os.path.splitext(os.path.basename(pathIn))[-1][1:]
            if common_utils.check_filetype_extended(pathIn, 'video'):  # 若源文件是视频，且未指定输出音频格式，则默认输出mp3
                default_type = 'mp3'
            audio_type = re.sub(r'^\.+', '', input_type) if input_type else default_type
            dst_name = "%s.%s" % (os.path.splitext(os.path.basename(pathIn))[0], audio_type)
            if os.path.abspath(pathIn) == os.path.abspath(src_dir):
                pathOut = os.path.join(dst_dir, dst_name)
            else:
                pathOut = os.path.join(os.path.dirname(pathIn).replace(src_dir, dst_dir), dst_name)
            try:
                self.do_get_audio(pathIn, pathOut, startPoint, endPoint, sampling_rate, bitrate)
            except Exception as e:
                logger.debug(e)
                print(e)
                failed_files[pathIn] = '无法转换 %s 格式,可能缺少编解码器!' % audio_type
            self.pb1["value"] += 1
        local_time = common_utils.get_times_now().get('time_str') # 记录完成时间
        total_msg = "处理 %s 的音频到 %s 完成！用时%.3fs" % (src_dir, dst_dir, time.time() - start_time)
        logger.debug(local_time + total_msg)
        mBox.showinfo('任务完成', "音频处理完成!")
        self.scr.insert('end', '\n\n%s  %s\n' % (local_time, total_msg))
        msg = ''
        if len(failed_files):
            msg += "\n共有 %s 个文件操作失败,详情如下:\n" % len(failed_files)
            msg += '\n'.join(['%s  -->  %s' % (path, failed_files[path]) for path in failed_files])
            self.scr.insert('end', msg)
        self.scr.see(tk.END)
        if self.clear_time_input_flag.get():
            self.clear_time_input()
        self.btn_show.config(state=tk.NORMAL)
        logger.info('【音频处理】  %s' % total_msg)

    def do_get_audio(self, pathIn, pathOut, startPoint, endPoint, sampling_rate, bitrate):
        """实际处理音频的函数"""
        # command = [ffmpeg_path, '-ss', sub_start_time, '-i', pathIn, '-acodec', 'copy', '-t',sub_stop_time, pathOut]
        command = [settings.FFMPEG_PATH, '-i', pathIn]  # 命令
        dst_dir = os.path.dirname(pathOut)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        if self.cut_time_flag.get():
            # command.extend(['-ss', startPoint, '-t', endPoint])  # 放在这里有负数时会报错 命令 负数横杠会跟命令参数混淆
            # 获取音视频信息
            duration = 0
            audio_info = common_utils.get_media_meta_sample(pathIn)  # 视频信息
            if audio_info:
                duration = audio_info.get('duration')  # 读取的是毫秒
                if not duration:  # mediainfo不能读取音频文件时长信息
                    duration = common_utils.get_media_meta_by_ffmpeg(pathIn).get('duration')
                duration = float(duration) / 1000  # 时长 秒  ,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
            if endPoint <= 0:  # 结束时间点为0或者负数
                endPoint = duration + endPoint
            if startPoint < 0:
                startPoint = duration + startPoint
            dst_name, dst_ext = os.path.splitext(os.path.basename(pathOut))
            dst_name = "%s_(%ss_to_%ss)%s" % (dst_name, startPoint, endPoint, dst_ext)
            pathOut = os.path.join(dst_dir, dst_name)
            sub_stop_time = video_utils.millisecToAssFormat(endPoint)
            sub_start_time = video_utils.millisecToAssFormat(startPoint)
            # command.extend(['-ss', startPoint, '-t', endPoint])  # 一直报错 TypeError: expected str, bytes or os.PathLike object, not int
            # 怀疑是不能直接填数字, 试试用时间字符
            # command.extend(['-ss', sub_start_time, '-t', sub_stop_time])
            command.extend(['-ss', str(startPoint), '-t', str(endPoint)])  # 直接填字符串的数值也可以
            msg = "处理 %s 从 %s 至 %s 的音频到 %s 完成！" % (pathIn, sub_start_time, sub_stop_time, pathOut)
        else:
            msg = "处理 %s 的音频到 %s 完成！" % (pathIn, pathOut)
        if os.path.exists(pathOut):  # 目标路径已存在同名文件
            logger.debug('{}已存在！'.format(pathOut))
            deal_exists_mode = self.deal_exists_mode.get()  # 处理已存在同名文件
            if deal_exists_mode == '0':  # 跳过
                return
            elif deal_exists_mode == '1':  # 覆盖
                command.append('-y')
            else:  # 询问
                write_option = mBox.askyesno('覆盖前询问', '{} 已存在! 是否覆盖？'.format(pathOut))
                if write_option:
                    command.append('-y')
                else:
                    return
        # 操作文件
        if sampling_rate:
            command.extend(['-ar', sampling_rate])
        if bitrate:
            command.extend(['-b:a', bitrate])
        if self.copy_codec_flag.get():
            src_ext = os.path.splitext(os.path.basename(pathIn))[-1][1:]
            dst_ext = os.path.splitext(os.path.basename(pathOut))[-1][1:]
            if dst_ext.lower() == src_ext.lower():
                command.extend(['-acodec', 'copy'])
        command.append(pathOut)
        logger.debug(command)
        subprocess.call(command, shell=True)
        if not os.path.exists(pathOut):  # 创建失败代表没有符合的编解码器
            logger.warning('【音频处理】  %s 创建失败!可能是缺失该格式编解码器' % pathOut)
            raise NameError('可能是缺失该格式编解码器!')
        if os.path.getsize(pathOut) == 0:
            logger.warning('【音频处理】  %s 创建失败!可能是缺失该格式编解码器' % pathOut)
            os.remove(pathOut)  # 删除空文件
            raise NameError('可能是缺失该格式编解码器!')
        if self.original_mtime_flag.get():  # 继承原文件时间戳
            _mtime = os.path.getmtime(pathIn)
            os.utime(pathOut, (_mtime, _mtime))
        logger.debug(msg)
        self.scr.insert('end', '\n\n%s\n' % msg)
        self.scr.see(tk.END)
        return {'pathOut': pathOut}

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_paths(self.src_dir, self.dst_dir)
        if not flag:
            return
        t = threading.Thread(target=self.deal_get_audio)
        t.daemon = True
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
        self.task_list = []  # 任务列表
        self.has_done_id = 0  # 已经操作到的最后一个任务id，用于配合run_show_task子线程 防止任务已经全部完成了还在不停刷新
        self.create_task_lock = threading.Lock()  # 创建添加任务的互斥锁，保证数据安全
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
        self.file_type = tk.StringVar()  # 视频格式 mp4 mov mkv
        self.file_type.set('')
        self.invoke_fps_flag = tk.BooleanVar()  # 是否激活帧率输入框
        self.invoke_type_flag = tk.BooleanVar()  # 是否激活视频格式输入框
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.clear_time_input_flag = tk.BooleanVar()  # 是否清空时间输入框内容
        self.del_audio_flag = tk.BooleanVar()  # 是否去除视频中的音频  True输出视频无声音
        self.tid = 0  # 任务id计数
        self.sort_flag = tk.BooleanVar()  # 任务显示升序排列 True 升序 False降序排列
        self.frameNum.set("")  # 设置默认值
        self.original_mtime_flag.set(False)  # 设置默认选中否
        self.clear_time_input_flag.set(True)  # 设置默认选中
        self.del_audio_flag.set(False)
        self.sort_flag.set(False)
        self.createPage()
        # self.run()  # 启动一个子线程用来监听并执行self.task_list 任务列表中的任务

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.dst_dir.set('')
        if self.clear_time_input_flag.get() is True:
            self.clear_time_input()
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)

    def selectPath(self):
        self.src_dir.set(askopenfilename())
        self.dst_dir.set('')
        if self.clear_time_input_flag.get() is True:
            self.clear_time_input()

    def createPage(self):
        """页面布局"""
        self.l_title["text"] = "视频截取"
        ttk.Label(self.f_input, text='视频路径:').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath).grid(row=0, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=2, columnspan=3, sticky=tk.EW)
        ttk.Checkbutton(self.f_input_option, text="修改格式", variable=self.invoke_type_flag, onvalue=True,
                        offvalue=False, command=self.invoke_type).grid(row=0, column=0, sticky=tk.W)
        self.e_type = ttk.Entry(self.f_input_option, textvariable=self.file_type, width=10, state=tk.DISABLED)
        self.e_type.grid(row=0, column=1, padx=5)
        ttk.Checkbutton(self.f_input_option, text="修改帧率", variable=self.invoke_fps_flag, onvalue=True,
                        offvalue=False, command=self.invoke_fps).grid(row=0, column=2, sticky=tk.EW, padx=5)
        self.e_fps = ttk.Entry(self.f_input_option, textvariable=self.frameNum, width=8, state=tk.DISABLED)  # 视频帧率输入框
        self.e_fps.grid(row=0, column=3, sticky=tk.W)
        ttk.Checkbutton(self.f_input_option, text="继承原修改时间", variable=self.original_mtime_flag, onvalue=True,
                        offvalue=False).grid(row=0, column=4, sticky=tk.EW, padx=5)
        ttk.Checkbutton(self.f_input_option, text="清空时间输入框内容", variable=self.clear_time_input_flag, onvalue=True,
                        offvalue=False, command=self.clear_time_input).grid(row=0, column=5, sticky=tk.EW, padx=5)
        ttk.Checkbutton(self.f_input_option, text="去除音频", variable=self.del_audio_flag, onvalue=True,
                        offvalue=False, command=self.del_audio_flag).grid(row=0, column=6, sticky=tk.EW, padx=5)
        ttk.Label(self.f_input_option, text='任务排序： ').grid(row=0, column=7)
        ttk.Radiobutton(self.f_input_option, text='升序', variable=self.sort_flag, value=True, command=self.show_tasks).grid(row=0, column=8, sticky=tk.EW)
        ttk.Radiobutton(self.f_input_option, text='降序', variable=self.sort_flag, value=False, command=self.show_tasks).grid(row=0, column=9, sticky=tk.EW)
        self.f_time_option = ttk.Frame(self.f_input)  # 时间输入容器
        self.f_time_option.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_time_option, text='开始时间: ').grid(row=1, column=0, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_h, width=5).grid(row=1, column=1)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=2, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_m, width=5).grid(row=1, column=3)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=4, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_start_time_s, width=5).grid(row=1, column=5)
        ttk.Label(self.f_time_option, text='    结束时间: ').grid(row=1, column=6, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_h, width=5).grid(row=1, column=7)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=8, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_m, width=5).grid(row=1, column=9)
        ttk.Label(self.f_time_option, text=':').grid(row=1, column=10, pady=10)
        ttk.Entry(self.f_time_option, textvariable=self.sub_stop_time_s, width=5).grid(row=1, column=11)
        ttk.Button(self.f_time_option, text="更改保存路径", command=self.chg_path).grid(row=1, column=12, padx=10)
        # ttk.Button(self.f_input, text="查看日志", command=self.showLog).grid(row=3, column=1, sticky=tk.E)
        ttk.Button(self.f_input, text="添加任务", command=self.run_create_task).grid(row=3, column=2)
        self.l_task_state = ttk.Label(self.f_state, text="当前任务：", font=('微软雅黑', 16))
        self.l_task_state.pack()
        scrolW = 120
        scrolH = 41
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=2, sticky=tk.NSEW)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def invoke_type(self):
        """激活视频格式输入框"""
        if self.invoke_type_flag.get():
            self.e_type.config(state=tk.NORMAL)
        else:
            self.file_type.set('')
            self.e_type.config(state=tk.DISABLED)

    def invoke_fps(self):
        """激活帧率输入框"""
        if self.invoke_fps_flag.get():
            self.e_fps.config(state=tk.NORMAL)
        else:
            self.frameNum.set('')
            self.e_fps.config(state=tk.DISABLED)

    def chg_path(self):
        """修改保存路径"""
        self.dst_dir.set(askdirectory())

    def clear_time_input(self):
        """清除时间输入框内容"""
        for item in self.time_inputs:
            item.set('')

    def run_create_task(self):
        """创建子进程用于创建视频裁剪任务，防止因为批量创建任务时导致程序界面阻塞"""
        if not os.path.exists(settings.FFMPEG_PATH):
            mBox.showerror('缺失ffmpeg!', '程序缺失 %s !' % settings.FFMPEG_PATH)
            return
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.create_task)
        t.daemon = True
        t.start()

    @deal_running_task_arg2('视频裁剪-创建视频剪辑任务')
    def create_task(self):
        """创建任务"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        fps = common_utils.get_int(self.frameNum.get().strip(), None)  # 帧率
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
        sub_start_time_h = common_utils.get_int(sub_start_time_h, 0)  # 获取开始剪切时间
        sub_start_time_m = common_utils.get_int(sub_start_time_m, 0)  # 获取开始剪切时间
        sub_start_time_s = common_utils.get_float(sub_start_time_s, 0)  # 获取开始剪切时间
        sub_stop_time_h = common_utils.get_int(sub_stop_time_h, 0)  # 获取剪切的结束时间
        sub_stop_time_m = common_utils.get_int(sub_stop_time_m, 0)  # 获取剪切的结束时间
        sub_stop_time_s = common_utils.get_float(sub_stop_time_s, 0)  # 获取剪切的结束时间
        startPoint = sub_start_time_h * 3600 + sub_start_time_m * 60 + sub_start_time_s
        endPoint = sub_stop_time_h * 3600 + sub_stop_time_m * 60 + sub_stop_time_s
        try:
            if os.path.isfile(src_dir):  # 操作单个视频文件
                pathIn = src_dir
                file_name = os.path.basename(pathIn)
                if dst_dir:
                    _dst_dir = os.path.join(dst_dir, "videoCut")
                else:
                    _dst_dir = os.path.join(os.path.dirname(pathIn), "videoCut")
                dst_ext = video_type if video_type else os.path.splitext(file_name)[-1][1:].lower()
                dst_name = "%s_(%ss_to_%ss).%s" % (file_name, startPoint, endPoint, dst_ext)
                pathOut = os.path.join(_dst_dir, dst_name)
                self.do_create_task(pathIn, pathOut, startPoint, endPoint, fps, continue_flag, original_mtime_flag)
            else:  # 操作目录
                for root, dirs, files in os.walk(src_dir):
                    for file in files:
                        pathIn = os.path.join(root, file)
                        if dst_dir:
                            _dst_dir = os.path.join(dst_dir, os.path.basename(src_dir) + "[videoCut]")
                        else:
                            _dst_dir = os.path.abspath(src_dir) + "[videoCut]"
                        dst_ext = video_type if video_type else os.path.splitext(file_name)[-1][1:].lower()
                        dst_name = "%s_(%ss_to_%ss).%s" % (file, startPoint, endPoint, dst_ext)
                        pathOut = os.path.join(_dst_dir, dst_name)
                        self.do_create_task(pathIn, pathOut, startPoint, endPoint, fps, continue_flag, original_mtime_flag)
            # mBox.showinfo("ok", "创建任务成功！")
        except Exception as e:
            self.dst_dir.set('')
            mBox.showerror("错误", '%s' % e)
            return

    def do_create_task(self, pathIn, pathOut, startPoint, endPoint, fps, continue_flag, original_mtime_flag):
        """实际创建任务的函数"""
        if pathIn is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_dir.get())
            return
        if pathIn == pathOut:
            mBox.showwarning("警告", "源路径与目标路径一致,有数据混乱风险!请重新规划路径!")
            return
        # video_type = self.file_type.get().strip()
        # video_type = re.sub(r'^\.+', '', video_type)
        # 获取视频信息
        duration = 0
        videoInfo = common_utils.get_media_meta_sample(pathIn)  # 视频信息
        # logger.debug(videoInfo)
        if videoInfo:
            duration = float(videoInfo.get('duration')) / 1000  # 时长 秒  ,get_video_length方法返回的视频时长数据是'decimal.Decimal'而不是float类型
        if endPoint <= 0:  # 结束时间点为0或者负数
            endPoint = duration + endPoint
        if startPoint < 0:
            startPoint = duration + startPoint
        dst_name = "%s_(%ss_to_%ss).%s" % (os.path.basename(pathIn), startPoint, endPoint, os.path.splitext(pathOut)[-1][1:].lower())
        pathOut = os.path.join(os.path.dirname(pathOut), dst_name)
        sub_stop_time = video_utils.millisecToAssFormat(endPoint)
        sub_start_time = video_utils.millisecToAssFormat(startPoint)
        # 创建任务信息
        self.tid += 1
        task = Task(self.tid, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag, original_mtime_flag)
        if self.clear_time_input_flag.get():
            self.clear_time_input()
        msg = "【视频截取-新增任务】 裁剪 %s 第 %s 秒至第 %s 秒视频任务，保存视频名：%s" % (pathIn, sub_start_time, sub_stop_time, pathOut)
        logger.info(msg)
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
            if status != 0:
                if tid > self.has_done_id:
                    self.has_done_id = tid  # 记录当前已经操作的任务id
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
        self.l_task_state["text"] = "当前任务：(总共：%s, %s 进行中, %s 已完成, %s 错误)" % (total_count, todo_count, done_count, error_count)

    def do_video_cut_single(self, pathIn, pathOut, sub_start_time, sub_stop_time, fps, continue_flag=False,
                            original_mtime_flag=False):
        """裁剪视频，处理单个文件"""
        start_time = time.time()  # 记录开始时间
        if not os.path.exists(pathIn):
            return
        if pathIn == pathOut:
            logger.debug("源路径与目标路径一致！")
            return
        if os.path.isdir(pathOut):
            pathOut = os.path.join(pathOut, os.path.basename(pathIn))
        if continue_flag is True:
            if os.path.exists(pathOut):
                return
        logger.debug(" %s  >>>  %s" % (pathIn, pathOut))
        pathOutDir = os.path.dirname(pathOut)
        if not os.path.exists(pathOutDir):
            os.makedirs(pathOutDir)
        # ffmpeg.exe -ss 48 -to 244 -i pathIn -vcodec copy -acodec copy pathOut
        command = [settings.FFMPEG_PATH, '-y', '-ss', str(sub_start_time), '-to', str(sub_stop_time), '-i', pathIn]
        if self.del_audio_flag.get():  # 是否去除音频
            command.append('-an')
        if fps:  # 是否修改帧率
            command.extend(['-r', str(fps)])
        if os.path.splitext(pathIn)[-1].lower() == os.path.splitext(pathOut)[-1].lower():  # 文件类型不变则直接用原来的编解码
            command.extend(['-vcodec', 'copy', '-acodec', 'copy'])
        command.append(pathOut)
        # cmd_str = '"%s" -y -ss %s -to %s -i "%s" -vcodec copy -acodec copy "%s"' % (ffmpeg_path, sub_start_time, sub_stop_time, pathIn, pathOut)
        # os.system(cmd_str)  # 直接os.system() 会不停弹出关闭cmd窗口
        # 用subprocess隐藏反复弹出的cmd窗口, 直接os.system() 会不停弹出关闭cmd窗口
        # print(command)
        subprocess.call(command, shell=True)
        if not os.path.exists(pathOut):
            raise Exception('视频裁剪失败！')
        # 将裁剪后视频修改时间变更为源视频修改时间
        if original_mtime_flag is True:
            timestamp = os.path.getmtime(pathIn)
            os.utime(pathOut, (timestamp, timestamp))
        msg = "【视频截取-剪辑完成】 裁剪 %s 第 %s 秒至第 %s 秒视频完成!" % (pathIn, sub_start_time, sub_stop_time)
        logger.debug(msg)
        msg += "总用时 %.3f 秒" % (time.time() - start_time)
        logger.info(msg)

    @deal_running_task_arg2('视频裁剪-剪辑视频')
    def run_task(self):
        """循环检测并执行任务列表里的任务"""
        while True:
            if self.has_done_id >= len(self.task_list):
                self.has_running_task_thread = False
                break
            if self.has_done_id < len(self.task_list):
                for task in self.task_list:
                    if not (task.status == 0):  # 已完成任务
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
                        logger.debug("task:%s complete!" % str(task))
                    except Exception as e:
                        task.status = 2
                        logger.debug("出错了：%s" % e)
                        msg = "裁剪 %s 第 %s 秒至第 %s 秒视频出错!" % (pathIn, sub_start_time, sub_stop_time)
                        msg += " 错误：%s" % e
                        logger.error(msg)
                    finally:
                        self.show_tasks()  # 刷新任务列表状态
            time.sleep(0.5)  # 防止不停执行无意义操作占用CPU资源

    def run(self):
        """创建子进程实时监听任务信息，并执行任务"""
        if self.has_running_task_thread is False:
            self.has_running_task_thread = True
            t = threading.Thread(target=self.run_task)
            t.daemon = True
            t.start()


class TimestampFrame(BaseFrame):
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
        self.chg_rec_flag = tk.BooleanVar()  # True 递归操作
        self.chg_rec_file_flag = tk.BooleanVar()  # True 递归操作文件夹下子文件
        self.chg_rec_dir_flag = tk.BooleanVar()  # True 递归操作文件夹下子文件夹
        self.show_file_real_type_flag = tk.BooleanVar()  # True 显示文件真实数据类型
        self.offset_flag = tk.BooleanVar()  # True 时间偏移
        self.offset_mode = tk.StringVar()  # 偏移模式 '1' 等差 即时间等差递增递减 '2' 随机 即时间随机增减
        self.offset = tk.StringVar()  # 偏移量 正负数 或者随机值区间
        self.show_media_meta_flag = tk.BooleanVar()  # 显示媒体文件的完整元数据
        self.ext_extend_flag = tk.BooleanVar()  # 对不能字节码识别的文件，是否使用后缀名识别 比如私有格式，文本文件等  True 使用后缀名匹配
        self.use_ori_time = tk.BooleanVar()  # 按原文件时间戳为基准  True 按原文件时间修改 Flase 按输入时间修改
        self.is_clear_scr = tk.BooleanVar()  # 执行新操作前，是否清空显示区 True 清空scr False 不清空 scr
        self.is_clear_scr.set(True)  # 为了方便本页面程序功能使用，默认不清空scr文本区
        self.change_file_ctime_flag.set(True)  # 设置默认选中是
        self.change_file_mtime_flag.set(True)  # 设置默认选中是
        self.change_file_atime_flag.set(True)  # 设置默认选中是
        self.offset_mode.set('1')
        self.modify_mode.set(1)
        self.chg_bat_flag.set(True)  # 设置默认选中
        self.chg_rec_flag.set(False)  # 设置默认选中
        self.chg_rec_file_flag.set(True)  # 设置默认选中
        self.chg_rec_dir_flag.set(False)  # 设置默认值
        self.show_file_real_type_flag.set(True)
        self.offset_flag.set(False)
        self.show_media_meta_flag.set(False)
        self.ext_extend_flag.set(True)
        self.use_ori_time.set(False)  # 默认按输入时间修改文件时间戳
        self.offset_curr = 0  # 记录当前已偏移的量
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "时间戳操作"
        self.f_input0 = ttk.Frame(self.f_input)
        self.f_input0.grid(row=0, columnspan=4, sticky=tk.EW)
        self.f_input1 = ttk.Frame(self.f_input)
        self.f_input1.grid(row=1, columnspan=4, sticky=tk.EW)
        self.f_input2 = ttk.Frame(self.f_input)
        self.f_input2.grid(row=2, columnspan=4, sticky=tk.EW)
        self.f_input3 = ttk.Frame(self.f_input)
        self.f_input3.grid(row=3, columnspan=4, sticky=tk.EW)
        self.f_input0.grid_columnconfigure(1, weight=1)
        ttk.Label(self.f_input0, text="文件路径: ").grid(row=0, pady=10)
        ttk.Entry(self.f_input0, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input0, text="浏览", command=self.selectPath).grid(row=0, column=2, sticky=tk.EW)
        ttk.Label(self.f_input1, text="输入时间: ").grid(row=1, pady=10)
        ttk.Entry(self.f_input1, textvariable=self.input_time, width=30, validate='focusout', validatecommand=self.time_to_timestamp).grid(row=1, column=1)
        ttk.Label(self.f_input1, text="输入时间戳: ").grid(row=1, column=2, padx=5)
        ttk.Entry(self.f_input1, textvariable=self.input_timestamp, width=30, validate="focusout", validatecommand=self.timestamp_to_time).grid(row=1, column=3, columnspan=2,sticky=tk.E)
        ttk.Label(self.f_input2, text="修改: ").grid(row=0, sticky=tk.W)
        self.btn_chk_ctime = ttk.Checkbutton(self.f_input2, text="创建时间", variable=self.change_file_ctime_flag, onvalue=True, offvalue=False)
        self.btn_chk_ctime.grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(self.f_input2, text="修改时间", variable=self.change_file_mtime_flag, onvalue=True, offvalue=False).grid(row=0, column=2, sticky=tk.W)
        ttk.Checkbutton(self.f_input2, text="访问时间", variable=self.change_file_atime_flag, onvalue=True, offvalue=False).grid(row=0, column=3, sticky=tk.W)
        self.c_offset = ttk.Checkbutton(self.f_input2, text="时间偏移", variable=self.offset_flag, onvalue=True, offvalue=False,command=self.invoke_offset)
        self.c_offset.grid(row=0, column=4, sticky=tk.W)
        self.r_offset_mode_1 = ttk.Radiobutton(self.f_input2, text="等差", variable=self.offset_mode, value='1')
        self.r_offset_mode_1.grid(row=0, column=5)
        self.r_offset_mode_2 = ttk.Radiobutton(self.f_input2, text="随机", variable=self.offset_mode, value='2')
        self.r_offset_mode_2.grid(row=0, column=6)
        self.e_offset_entry = ttk.Entry(self.f_input2, textvariable=self.offset, width=10)
        self.e_offset_entry.grid(row=0, column=7)
        ttk.Checkbutton(self.f_input2, text="按原文件时间修改", variable=self.use_ori_time, onvalue=True, offvalue=False).grid(row=0, column=9, padx=5)
        ttk.Label(self.f_input2, text=" 方式: ").grid(row=0, column=10, sticky=tk.W, padx=5)
        ttk.Radiobutton(self.f_input2, text="os.utime", variable=self.modify_mode, value=1, command=self.invoke_timecheckbtn).grid(row=0, column=11)
        ttk.Radiobutton(self.f_input2, text="win32file", variable=self.modify_mode, value=2, command=self.invoke_timecheckbtn).grid(row=0, column=12)
        ttk.Label(self.f_input3, text="高级: ").grid(row=2, column=0)
        ttk.Checkbutton(self.f_input3, text="批量操作", variable=self.chg_bat_flag, onvalue=True, offvalue=False).grid(row=2, column=1, sticky=tk.W)
        ttk.Checkbutton(self.f_input3, text="递归操作", variable=self.chg_rec_flag, onvalue=True, offvalue=False,command=self.invoke_rec_child).grid(row=2, column=2, sticky=tk.W)
        self.cb_rec_file = ttk.Checkbutton(self.f_input3, text="递归子文件", variable=self.chg_rec_file_flag, onvalue=True, offvalue=False, state=tk.DISABLED)
        self.cb_rec_file.grid(row=2, column=3, sticky=tk.W)
        self.cb_rec_dir = ttk.Checkbutton(self.f_input3, text="递归子文件夹", variable=self.chg_rec_dir_flag, onvalue=True, offvalue=False, state=tk.DISABLED)
        self.cb_rec_dir.grid(row=2, column=4, sticky=tk.W)
        ttk.Checkbutton(self.f_input3, text="后缀名识别", variable=self.ext_extend_flag, onvalue=True, offvalue=False).grid(row=2, column=5, sticky=tk.W)
        ttk.Checkbutton(self.f_input3, text="读取文件元数据", variable=self.show_file_real_type_flag, onvalue=True, offvalue=False).grid(row=2, column=6, sticky=tk.W)
        ttk.Checkbutton(self.f_input3, text="读取完整元数据", variable=self.show_media_meta_flag, onvalue=True, offvalue=False).grid(row=2, column=7, sticky=tk.W)
        ttk.Checkbutton(self.f_input3, text="执行新操作前清空显示区", variable=self.is_clear_scr, onvalue=True, offvalue=False).grid(row=2, column=8, sticky=tk.W)
        ttk.Button(self.f_option, text="获取当前时间", command=self.get_current_time).grid(row=1, pady=5)
        ttk.Button(self.f_option, text="查看文件时间戳", command=self.get_file_timestamp).grid(row=1, column=1)
        ttk.Button(self.f_option, text="修改文件时间戳", command=self.deal_change_file_timestamp).grid(row=1, column=2)
        ttk.Button(self.f_option, text="修改媒体文件时间为拍摄时间", command=self.deal_change_media_timestamp).grid(row=1, column=3)
        ttk.Button(self.f_option, text="导出媒体文件信息", command=self.deal_export_media_info).grid(row=1, column=4)
        self.f_input_option = ttk.Frame(self.f_option)  # 选项容器
        self.f_input_option.grid(row=0, columnspan=5, sticky=tk.EW)
        scrolW = 120
        scrolH = 40
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=1, sticky=tk.NSEW)
        self.invoke_timecheckbtn()  # 刷新时间戳复选框状态
        self.invoke_offset()  # 刷新时间偏移选项框状态
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def selectPath(self):
        file_path = askopenfilename()
        self.src_dir.set(file_path)
        self.chg_files = [file_path,]

    def invoke_rec_child(self):
        """用于激活递归子文件和递归子文件夹的复选框"""
        if self.chg_rec_flag.get():
            self.cb_rec_file.config(state=tk.NORMAL)
            self.cb_rec_dir.config(state=tk.NORMAL)
        else:
            self.cb_rec_file.config(state=tk.DISABLED)
            self.cb_rec_dir.config(state=tk.DISABLED)

    def invoke_offset(self):
        """用于激活时间偏移单选框和输入框"""
        if self.offset_flag.get():
            self.r_offset_mode_1.config(state=tk.NORMAL)
            self.r_offset_mode_2.config(state=tk.NORMAL)
            self.e_offset_entry.config(state=tk.NORMAL)
        else:
            self.r_offset_mode_1.config(state=tk.DISABLED)
            self.r_offset_mode_2.config(state=tk.DISABLED)
            self.e_offset_entry.config(state=tk.DISABLED)

    def invoke_timecheckbtn(self):
        """激活显示时间复选框"""
        if self.modify_mode.get() == 1:
            self.change_file_ctime_flag.set(False)
            self.btn_chk_ctime.config(state=tk.DISABLED)
        else:
            self.change_file_ctime_flag.set(True)
            self.btn_chk_ctime.config(state=tk.NORMAL)

    def get_current_time(self):
        time_res = common_utils.get_times_now()
        self.input_time.set(time_res.get('time_str'))
        self.input_timestamp.set(time_res.get('timestamp'))

    def clear_scr(self):
        """清空scr"""
        if self.is_clear_scr.get():
            self.scr.delete(1.0, 'end')

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear_scr()  # 清空scr显示区
        self.chg_files = []
        chg_rec_file_flag = self.chg_rec_file_flag.get()
        chg_rec_dir_flag = self.chg_rec_dir_flag.get()
        if self.chg_bat_flag.get():  # 批量操作记录文件列表
            for item in files:
                file_path = item.decode(settings.SYSTEM_CODE_TYPE)
                self.chg_files.append(file_path)
        else:
            self.chg_files = [files[-1].decode(settings.SYSTEM_CODE_TYPE), ]
        self.src_dir.set(files[-1].decode(settings.SYSTEM_CODE_TYPE),)
        # 获取程序拖拽功能获取到的项目
        file_list = []
        for src_dir in self.chg_files:
            if self.chg_rec_flag.get() is True:  # 递归操作
                if os.path.isdir(src_dir):
                    for root, dirs, files in os.walk(src_dir):
                        if chg_rec_dir_flag:
                            for _dir in dirs:
                                file_list.append(os.path.join(root, _dir))
                        if chg_rec_file_flag:
                            for file in files:
                                file_list.append(os.path.join(root, file))
                else:
                    file_list.append(src_dir)
            else:
                file_list.append(src_dir)
        # 获取每个文件或目录的时间戳信息
        self.chg_files = file_list
        total_count = len(file_list)
        num = 0
        for file_path in file_list:
            num += 1
            self.scr.insert("end", '【{}/{}】'.format(num, total_count))
            self.do_get_file_timestamp(file_path)

    def get_file_timestamp(self):
        """获取文件时间戳"""
        # 获取程序拖拽功能获取到的项目
        self.clear_scr()  # 清空scr显示区
        file_list = []
        src_dir = self.src_dir.get()
        chg_rec_file_flag = self.chg_rec_file_flag.get()
        chg_rec_dir_flag = self.chg_rec_dir_flag.get()
        if self.chg_rec_flag.get() is True:  # 递归操作
            if os.path.isdir(src_dir):
                for root, dirs, files in os.walk(src_dir):
                    if chg_rec_dir_flag:
                        for _dir in dirs:
                            file_list.append(os.path.join(root, _dir))
                    if chg_rec_file_flag:
                        for file in files:
                            # logger.debug(file)
                            file_list.append(os.path.join(root, file))
            else:
                file_list.append(src_dir)
        else:
            file_list.append(src_dir)
        # 获取每个文件或目录的时间戳信息
        self.chg_files = file_list
        total_count = len(file_list)
        num = 0
        for file_path in file_list:
            num += 1
            self.scr.insert("end", '【{}/{}】'.format(num, total_count))
            self.do_get_file_timestamp(file_path)

    def do_get_file_timestamp(self, file_path):
        """获取文件时间戳操作"""
        if (self.chg_bat_flag.get() is False) and (self.chg_rec_flag.get() is False):  # 批量操作和递归操作时不清屏
            self.clear_scr()  # 清空scr显示区
        if not os.path.exists(file_path):
            self.scr.insert('end', "您输入的路径：%s 不存在！" % file_path)
            return
        timestampc = os.path.getctime(file_path)
        timestampa = os.path.getatime(file_path)
        timestampm = os.path.getmtime(file_path)
        msg = "path: %s 的时间戳为\n" % file_path
        msg += "\t创建时间戳: %s\n" % timestampc
        msg += "\t修改时间戳: %s\n" % timestampm
        msg += "\t最后访问时间戳: %s\n" % timestampa
        msg += "\t创建本地时间为: %s\n" % common_utils.get_local_time(timestampc)
        msg += "\t修改本地时间为: %s\n" % common_utils.get_local_time(timestampm)
        msg += "\t最后访问本地时间为: %s\n" % common_utils.get_local_time(timestampa)
        # 获取文件元数据
        if self.show_media_meta_flag.get():
            msg += self.get_full_meta_msg(file_path)
        else:
            if self.show_file_real_type_flag.get():
                msg += self.get_file_meta_msg(file_path)
        self.scr.insert("end", msg + '\n\n')

    def get_file_meta_msg(self, file_path):
        """获取文件元数据，例如文件真实数据类型、视频时长、分辨率、图片分辨率"""
        msg = ''
        if os.path.isdir(file_path):  # 文件夹无法读取具体图片信息，程序会报错
            msg += '\n\t数据类型为: 文件夹'
            return msg
        if self.ext_extend_flag.get():  # 是否按文件后缀名识别filetype无法识别的文件
            file_category = common_utils.get_file_category_extended(file_path)
        else:
            file_category = common_utils.get_file_category(file_path)
        if file_category:
            # 文件为图片
            if file_category.lower() == 'image':
                # 获取图片信息
                res = common_utils.get_image_info(file_path)
                msg += '\n\t图片分辨率为: %s x %s' % (res['width'], res['height'])
                gps_information = res['GPS_information']
                date_information = res['date_information']
                if gps_information:
                    gps_lng = gps_information['GPSLongitude']  # 经度
                    gps_lat = gps_information['GPSLatitude']  # 纬度
                    gps_alt = gps_information.get('GPSAltitude')  # 高度
                    msg += '\n\tGPS信息: 纬度: %s, 经度: %s 高度：%s' % (gps_lat, gps_lng, gps_alt)
                if res.get('location'):
                    msg += "\n\tGPS信息: %s" % res.get('location')
                if date_information:
                    msg += '\n\t拍摄时间: %s' % date_information
                if res.get('hardware_make'):
                    msg += "\n\t设备厂商: %s" % res.get("hardware_make")
                if res.get('hardware_model'):
                    msg += "\n\t设备型号: %s" % res.get("hardware_model")
                if res.get('hardware_software'):
                    msg += "\n\t固件版本: %s" % res.get("hardware_software")
            # 文件为视频
            if file_category.lower() == 'video':
                # 获取视频分辨率、时长、拍摄时间
                res = common_utils.get_video_info(file_path)
                msg += '\n\t视频分辨率为: %s x %s' % (res['width'], res['height'])
                if res.get('frame_rate'):
                    msg += "\n\t帧速率: %s" % res.get("frame_rate")
                if res.get('format'):
                    msg += "\n\t媒体格式: %s" % res.get("format")
                if res.get('duration_str'):
                    msg += "\n\t视频时长为 %s" % res.get('duration_str')
                if res.get('location'):
                    msg += "\n\tGPS信息: %s" % res.get('location')
                if res.get('encoded_date'):
                    msg += "\n\t拍摄时间: %s" % res.get("encoded_date")
                if res.get('hardware_make'):
                    msg += "\n\t设备厂商: %s" % res.get("hardware_make")
                if res.get('hardware_model'):
                    msg += "\n\t设备型号: %s" % res.get("hardware_model")
                if res.get('hardware_software'):
                    msg += "\n\t固件版本: %s" % res.get("hardware_software")
            # 文件为音频
            if file_category.lower() == 'audio':
                # 获取时长
                res = common_utils.get_audio_info(file_path)
                if res.get('duration_str'):
                    msg += "\n\t音频时长为 %s" % res.get('duration_str')
                if res.get('bit_rate'):
                    msg += "\n\t音频比特率: %s" % res.get('bit_rate')
                if res.get('sampling_rate'):
                    msg += "\n\t音频采样率: %s" % res.get("sampling_rate")
                if res.get('frame_rate'):
                    msg += "\n\t音频帧速率: %s" % res.get("frame_rate")
                if res.get('stream_size'):
                    msg += "\n\t音频流大小: %s" % res.get("stream_size")
                if res.get('channel_s'):
                    msg += "\n\t音频通道数: %s" % res.get("channel_s")
        # 展示文件真实数据类型
        if self.show_file_real_type_flag.get():
            func = common_utils.get_type_extended if self.ext_extend_flag.get() else common_utils.get_type
            file_type = func(file_path)
            if file_type:
                msg += '\n\n\t文件类别: {} , 数据类型：{} , MIME类型: {}'.format(file_type['mime'].split('/')[0], file_type['extension'], file_type['mime'])
        return msg

    def get_full_meta_msg(self, file_path):
        """获取完整元数据"""
        msg = ''
        if os.path.isdir(file_path):  # 文件夹无法读取具体图片信息，程序会报错
            msg += '\n\t数据类型为: 文件夹'
            return msg
        file_category = common_utils.get_file_category_extended(file_path)
        if file_category:
            # 文件为图片
            if file_category.lower() == 'image':
                # 获取照片exif信息
                res = common_utils.get_image_meta(file_path)
                for key, value in res.items():
                    msg += '\n%s: %s' % (key, value)
            # 文件为视频或音频
            if file_category.lower() in ('video', 'audio'):
                res = common_utils.get_media_meta(file_path)
                for item in res:
                    msg += '\n\n%s' % item
                    for key, value in res[item].items():
                        msg += '\n%s: %s' % (key, value)
        # 展示文件真实数据类型
        file_type = common_utils.get_type_extended(file_path)
        if file_type:
            msg += '\n\n\t文件类型: {} ,真实数据类型为：{}'.format(file_type['extension'], file_type['mime'])
        return msg

    @deal_running_task_arg('导出媒体文件信息')
    def export_media_info(self):
        """导出视频、音频、照片的元数据信息"""
        src_dir = os.path.abspath(self.src_dir.get())
        path_str = src_dir.replace(':', '').replace('/', '_').replace('\\', '_')
        time_str = common_utils.get_times_now().get("time_num_str")
        excel_path = os.path.join(settings.RECORD_DIR, '%s_%s.xlsx' % (path_str, time_str))  # 输出的excel
        # 获取视频、音频、照片的元数据信息
        res = common_utils.get_media_info_for_excel(src_dir)
        # 导出到excel
        my_api.export_media_info_as_excel(excel_path, res)
        logger.info('【导出媒体文件信息】  导出 %s 媒体文件信息到 %s ' % (src_dir, excel_path))
        self.scr.insert("end", '%s\t导出 %s 媒体文件信息到 %s' % (common_utils.get_times_now().get("time_str"), src_dir, excel_path))
        mBox.showinfo('完成', '导出媒体文件信息完成!')

    def do_change_file_timestamp(self, file_path, func_calc_new_timestamp):
        """用于修改单个文件的时间戳
        func_calc_new_timestamp 用于计算文件新时间戳的方法
        """
        # 获取修改时间的时间戳
        modify_mode = self.modify_mode.get()
        change_file_ctime_flag = self.change_file_ctime_flag.get()
        change_file_mtime_flag = self.change_file_mtime_flag.get()
        change_file_atime_flag = self.change_file_atime_flag.get()
        if not os.path.exists(file_path):
            self.scr.insert('end', "您输入的路径：%s 不存在！" % file_path)
            return
        old_ctime = os.path.getctime(file_path)
        old_mtime = os.path.getmtime(file_path)
        old_atime = os.path.getatime(file_path)
        res = func_calc_new_timestamp(file_path)  # 计算新时间戳
        new_ctime = res['new_ctime'] if change_file_ctime_flag else old_ctime
        new_mtime = res['new_mtime'] if change_file_mtime_flag else old_mtime
        new_atime = res['new_atime'] if change_file_atime_flag else old_atime
        # 修改文件时间戳
        if modify_mode == 1:
            os.utime(file_path, (new_mtime, new_mtime))
        else:
            logger.debug('file_path:{}, new_ctime:{}, new_mtime:{}, new_atime:{}'.format(file_path, new_ctime, new_mtime, new_atime))
            my_api.modifyFileTimeByTimestamp(file_path, new_ctime, new_mtime, new_atime)
        res = {'ctime': (old_ctime, new_ctime), 'mtime': (old_mtime, new_mtime), 'atime': (old_atime, new_atime)}
        return res

    @deal_running_task_arg('修改文件时间戳')
    def change_file_timestamp(self):
        """修改文件时间戳"""
        self.scr.delete(1.0, 'end')
        self.offset_curr = 0  # 清空之前的记录值
        # 判断输入时间戳是否正常，不正确则置为当前时间
        try:
            float(self.input_timestamp.get())
        except Exception:
            mBox.showerror("错误", "输入的时间戳/时间偏移,非小数格式,请检查!")
            return
        if self.use_ori_time.get():  # True 使用文件自己的时间戳 False 使用输入的时间戳
            self.change_timestamp(self.calc_new_file_timestamp_use_ori_time, '修改文件时间戳')
        else:
            self.change_timestamp(self.calc_new_file_timestamp, '修改文件时间戳')

    @deal_running_task_arg('修改媒体文件时间戳为拍摄时间')
    def change_media_timestamp(self):
        """修改媒体时间为拍摄时间"""
        self.change_timestamp(self.calc_new_media_timestamp, '修改照片、视频时间为拍摄时间')

    def change_timestamp(self, func_calc_new_stamp, log_opeate_str):
        """修改时间戳"""
        self.scr.delete(1.0, 'end')
        # 获取文件路径
        file_paths = self.chg_files
        msg = ''
        # 递归操作时，会操作文件夹下所有文件
        total_count = len(file_paths)
        num = 0
        for file_path in file_paths:
            num += 1
            res = self.do_change_file_timestamp(file_path, func_calc_new_stamp)
            time_str_c_old = common_utils.get_local_time(res['ctime'][0])
            time_str_a_old = common_utils.get_local_time(res['atime'][0])
            time_str_m_old = common_utils.get_local_time(res['mtime'][0])
            time_str_c_new = common_utils.get_local_time(res['ctime'][1])
            time_str_a_new = common_utils.get_local_time(res['atime'][1])
            time_str_m_new = common_utils.get_local_time(res['mtime'][1])
            # 显示文件时间戳信息
            msg += "【{}/{}】path: {} 的时间戳修改为\n\n".format(num, total_count, file_path)
            msg += "\t创建时间戳: \t %s    >>>    %s\n" % (res['ctime'][0], res['ctime'][1])
            msg += "\t修改时间戳: \t %s    >>>    %s\n" % (res['mtime'][0], res['mtime'][1])
            msg += "\t访问时间戳: \t %s    >>>    %s\n" % (res['atime'][0], res['atime'][1])
            msg += "\t创建 时间：\t %s    >>>    %s\n" % (time_str_c_old, time_str_c_new)
            msg += "\t修改 时间：\t %s    >>>    %s\n" % (time_str_m_old, time_str_m_new)
            msg += "\t访问 时间：\t %s    >>>    %s\n" % (time_str_a_old, time_str_a_new)
        if msg:
            self.scr.insert("end", msg)
            # 写出记录
            time_now_str = time.strftime(r"%Y%m%d%H%M%S", time.localtime())
            self.record_path = os.path.join(settings.RECORD_DIR, 'change_timestamp_record_%s.txt' % time_now_str)
            with open(self.record_path, 'a', encoding='utf-8') as f:
                f.write(msg+'\n')
            logger.info('【%s】  文件时间修改信息,记录到 %s' % (log_opeate_str, self.record_path))

    def calc_new_media_timestamp(self, file_path):
        """计算照片/视频的拍摄时间新时间戳"""
        new_ctime = os.path.getctime(file_path)
        new_mtime = os.path.getmtime(file_path)
        new_atime = os.path.getatime(file_path)
        date_information = common_utils.get_media_encoded_date(file_path)
        if date_information:
            date_information = time.mktime(time.strptime(date_information, r'%Y-%m-%d %H:%M:%S'))  # 转换为时间戳
            new_ctime, new_mtime, new_atime = (date_information, date_information, date_information)
        return {'new_ctime': new_ctime, 'new_mtime': new_mtime, 'new_atime': new_atime}

    def calc_new_file_timestamp(self, file_path):
        """计算新时间戳"""
        input_timestamp = float(self.input_timestamp.get())
        if self.offset_flag.get():  # 时间偏移
            # 计算偏移量, 计算偏移后的时间戳
            offset = common_utils.get_float(self.offset.get(), 0)
            if self.offset_mode.get() == '1':  # 等差
                _offset_curr = self.offset_curr + offset
            else:  # 随机
                _offset_curr = self.offset_curr + random.uniform(0, offset)
            # 计算偏移后的时间戳
            if self.offset_curr == 0:  # 第一个文件时间不偏移
                m_timestamp = input_timestamp
            else:
                m_timestamp = input_timestamp + self.offset_curr
            self.offset_curr = _offset_curr  # 记录当前已偏移量，注意：这个值是下次的时间戳偏移量！
        else:  # 不偏移
            m_timestamp = input_timestamp
        new_ctime, new_mtime, new_atime = (m_timestamp, m_timestamp, m_timestamp)
        return {'new_ctime': new_ctime, 'new_mtime': new_mtime, 'new_atime': new_atime}

    def calc_new_file_timestamp_use_ori_time(self, file_path):
        """计算新时间戳, 使用原文件自己的时间戳"""
        c_timestamp = os.path.getctime(file_path)
        m_timestamp = os.path.getmtime(file_path)
        a_timestamp = os.path.getatime(file_path)
        if self.offset_flag.get():  # 时间偏移
            # 计算偏移量, 计算偏移后的时间戳
            offset = common_utils.get_float(self.offset.get(), 0)
            if self.offset_mode.get() == '2':  # 随机
                offset =  random.uniform(0, offset) 
            c_timestamp += offset
            m_timestamp += offset
            a_timestamp += offset

        new_ctime, new_mtime, new_atime = (m_timestamp, m_timestamp, m_timestamp)
        return {'new_ctime': new_ctime, 'new_mtime': new_mtime, 'new_atime': new_atime}

    def time_to_timestamp(self):
        """时间转换为时间戳"""
        self.scr.delete(1.0, 'end')
        input_time = self.input_time.get()
        input_time = common_utils.changeStrToTime(input_time)
        # logger.debug('input_time: %s' % input_time)
        if input_time:
            try:
                timestamp = time.mktime(time.strptime(input_time, r'%Y-%m-%d %H:%M:%S'))
                msg = "时间：'%s' \n-->时间戳为: '%s'\n" % (input_time, timestamp)
                self.scr.insert("end", msg)
                self.input_timestamp.set(timestamp)
                return True
            except ValueError:
                mBox.showerror("错误", "时间格式输入错误! 请使用标准格式(yyyy-mm-dd HH:MM:SS)输入!")
                return False
        else:
            mBox.showerror("错误", "时间格式输入错误! 请使用标准格式(yyyy-mm-dd HH:MM:SS)输入!")
            return False

    def timestamp_to_time(self):
        """时间戳转换为时间"""
        self.scr.delete(1.0, 'end')
        input_timestamp = self.input_timestamp.get()
        if input_timestamp:
            try:
                input_timestamp = float(self.input_timestamp.get())
                get_time = time.strftime(r'%Y-%m-%d %H:%M:%S', time.localtime(input_timestamp))
                msg = "时间戳：'%s' \n-->时间为: '%s'\n" % (input_timestamp, get_time)
                self.scr.insert("end", msg)
                self.input_time.set(get_time)
                return True
            except Exception:
                mBox.showerror("错误", "输入时间戳格式有误! 须为纯数字或小数")
                return False
        else:
            mBox.showerror("错误", "输入时间戳格式有误! 须为纯数字或小数")
            return False

    def deal_export_media_info(self):
        """按钮绑定的方法用于创建函数子线程,防止tk阻塞导致页面无响应"""
        # 校验输入路径
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.export_media_info)
        t.daemon = True
        t.start()

    def deal_change_file_timestamp(self):
        """按钮绑定的方法用于创建函数子线程,防止tk阻塞导致页面无响应"""
        t = threading.Thread(target=self.change_file_timestamp)
        t.daemon = True
        t.start()
        
    def deal_change_media_timestamp(self):
        """按钮绑定的方法用于创建函数子线程,防止tk阻塞导致页面无响应"""
        t = threading.Thread(target=self.change_media_timestamp)
        t.daemon = True
        t.start()

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        self.all_children(self.f_option, self.lock_elements)
        for element in self.lock_elements:
            element.config(state=tk.DISABLED)


class ImageProcessingFrame(BaseFrame):
    """图像处理"""
    def __init__(self, master=None):
        super().__init__(master)
        self.option_mode = tk.StringVar()  # '1' 导出xx类型图片 '2' heic转为jpg '3' webp转为jpg
        self.continue_flag = tk.BooleanVar()  # 是否继续上次进度
        self.dst_encode = tk.StringVar()  # 要转换到的图片格式
        self.rate_value = 0  # 进度条数值
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.continue_flag.set(False)  # 设置默认选中否
        self.original_mtime_flag.set(True)
        self.is_chg_quality = tk.BooleanVar()  # 是否设置JPEG保存时图片质量 True 设置
        self.is_chg_quality.set(False)  # 设置默认选中否
        self.is_chg_subsampling = tk.BooleanVar()  # 是否设置JPEG保存时编码器子采样 True 设置
        self.is_chg_subsampling.set(False)  # 设置默认选中否
        self.is_save_exif = tk.BooleanVar()  # 是否保留JPEG 图片exif信息 True 保留
        self.is_save_exif.set(False)  # 设置默认选中否
        self.is_chg_icon_size = tk.BooleanVar()  # 是否设置ICO保存尺寸 True 设置
        self.is_chg_icon_size.set(False)  # 设置默认选中否
        self.quality = tk.IntVar()  # JPEG图片质量 1-100
        self.quality.set(95)
        self.subsampling = tk.IntVar()  # 子采样 0 1 2
        self.subsampling.set(0)
        # sizes 包括在这个ICO文件中的大小列表；这是一个2元组， (width, height) 
        # 默认为 [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        # 任何大于原始大小或256的大小都将被忽略。
        self.ico_size = tk.StringVar()
        self.ico_size.set("16,20,24,32,48,64,128,256")
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "图片处理"
        ttk.Label(self.f_input, text='图片路径: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='导出路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input1 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input1.grid(row=3, columnspan=5, sticky=tk.EW)
        self.f_input2 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input2.grid(row=4, columnspan=5, sticky=tk.EW)
        ttk.Label(self.f_input1, text='选择操作: ').grid(row=0, column=0, pady=5)
        ttk.Radiobutton(self.f_input1, text="HEIC转JPG", variable=self.option_mode, value='2', command=self.invoke_image_type_input).grid(
            row=0, column=4, padx=5)
        ttk.Radiobutton(self.f_input1, text="WEBP转JPG", variable=self.option_mode, value='3', command=self.invoke_image_type_input).grid(
            row=0, column=5, padx=5)
        ttk.Radiobutton(self.f_input1, text="转换为", variable=self.option_mode, value='4', command=self.invoke_image_type_input).grid(
            row=0, column=6, padx=5)
        self.e_trans_type = ttk.Entry(self.f_input1, textvariable=self.dst_encode, width=12, justify=tk.CENTER)
        self.e_trans_type.grid(row=0, column=7)
        self.option_mode.set('4')
        ttk.Checkbutton(self.f_input1, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(
            row=0, column=8, padx=5)
        ttk.Checkbutton(self.f_input1, text="继承原修改时间", variable=self.original_mtime_flag, onvalue=True, offvalue=False).grid(
            row=0, column=9, padx=5)
        
        ttk.Label(self.f_input2, text='高级操作: ').grid(row=0, column=0, pady=5)
        ttk.Checkbutton(self.f_input2, text="设置图像质量:", variable=self.is_chg_quality, onvalue=True, offvalue=False, command=self.chg_option_enable).grid(row=0, column=1, padx=5)
        self.e_quality = ttk.Entry(self.f_input2, textvariable=self.quality, width=5, state=tk.DISABLED, justify=tk.CENTER)
        self.e_quality.grid(row=0, column=2)
        ttk.Checkbutton(self.f_input2, text="设置子采样:", variable=self.is_chg_subsampling, onvalue=True, offvalue=False, command=self.chg_option_enable).grid(row=0, column=3, padx=5)
        self.e_subsampling = ttk.Entry(self.f_input2, textvariable=self.subsampling, width=5, state=tk.DISABLED, justify=tk.CENTER)
        self.e_subsampling.grid(row=0, column=4)
        ttk.Checkbutton(self.f_input2, text="保留EXIF信息", variable=self.is_save_exif, onvalue=True, offvalue=False, command=self.chg_option_enable).grid(row=0, column=5, padx=5)
        ttk.Checkbutton(self.f_input2, text="设置icon大小:", variable=self.is_chg_icon_size, onvalue=True, offvalue=False, command=self.chg_option_enable).grid(row=0, column=6, padx=5)
        self.e_ico_size = ttk.Entry(self.f_input2, textvariable=self.ico_size, width=25, state=tk.DISABLED, justify=tk.CENTER)
        self.e_ico_size.grid(row=0, column=7)

        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        # 展示结果
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 36
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.invoke_image_type_input()
        self.btn_show = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
        src_dir = self.src_dir.get().strip()
        if os.path.isfile(src_dir):
            self.dst_dir.set(os.path.join(os.path.dirname(src_dir), '转码'))
        else:
            self.dst_dir.set(os.path.abspath(src_dir) + '_[转码]')

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.btn_show.config(state=tk.DISABLED)

    def chg_option_enable(self):
        """设置高级选项使能状态"""
        if self.is_chg_quality.get():
            self.e_quality.config(state=tk.NORMAL)
        else:
            self.e_quality.config(state=tk.DISABLED)
        if self.is_chg_subsampling.get():
            self.e_subsampling.config(state=tk.NORMAL)
        else:
            self.e_subsampling.config(state=tk.DISABLED)
        if self.is_chg_icon_size.get():
            self.e_ico_size.config(state=tk.NORMAL)
        else:
            self.e_ico_size.config(state=tk.DISABLED)

    def invoke_image_type_input(self):
        """用于激活图像类型输入框"""
        if self.option_mode.get() == '4':
            self.e_trans_type.config(state=tk.NORMAL)
        else:
            self.e_trans_type.config(state=tk.DISABLED)

    @deal_running_task_arg('图片格式转换')
    def transcode(self, src_encode=''):
        """通用转码"""
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        is_continue = self.continue_flag.get()
        dst_encode = self.dst_encode.get().lower()
        dst_dir = os.path.join(dst_dir, dst_encode.upper())
        quality = int(self.quality.get()) if self.is_chg_quality.get() else None
        subsampling = int(self.subsampling.get()) if self.is_chg_subsampling.get() else None
        ico_size_str = self.ico_size.get() if self.is_chg_icon_size.get() else None
        is_save_exif = self.is_save_exif.get()
        original_mtime_flag = self.original_mtime_flag.get()
        kwargs = {'quality':quality, 'subsampling': subsampling, 'ico_size_str': ico_size_str, 
                  'is_save_exif': is_save_exif, 'original_mtime_flag': original_mtime_flag}
        self.scr.insert(tk.END, '{}\t开始遍历文件目录...\n'.format(common_utils.get_times_now().get('time_str')))
        src_encode = src_encode.lower()
        path_list = common_utils.get_files_by_filetype(src_dir, src_encode) if src_encode else common_utils.get_files_by_filetype(src_dir, 'image')
        self.rate_value = 0
        total_count = len(path_list)
        self.pb1["maximum"] = total_count
        local_time = common_utils.get_times_now().get('time_str')
        if total_count == 0:
            self.scr.insert(tk.END, '{}\t遍历文件目录完成,未找到图片!\n'.format(local_time))
            mBox.showinfo('任务完成', "图片格式转换完成!")
            return
        self.scr.insert(tk.END, '{}\t遍历文件目录完成,找到图片共 {} 张,开始转码...\n'.format(local_time, total_count))
        t = threading.Thread(target=self.show_rate, args=(total_count,))  # 创建显示进度条子线程
        t.daemon = True
        t.start()
        failed_list = []  # 记录操作失败的文件
        succ_count = 0  # 记录转码成功的文件数
        for file_path in path_list:
            logger.debug('进度[{}/{}] file_path: {}\n'.format(self.rate_value, total_count, file_path))
            # 将要存储的路径及名称
            _path, filename = os.path.split(file_path)
            name, ext = os.path.splitext(filename)
            if file_path == src_dir:  # 单个文件转码
                dst_path = os.path.join(dst_dir, '{}.{}'.format(name, dst_encode))
            else:  # 目录转码
                dst_path = os.path.join(_path.replace(src_dir, dst_dir), '{}.{}'.format(name, dst_encode))
            if is_continue is True:
                if os.path.exists(dst_path):
                    continue
            try:
                # 判断是否目标路径下是否有重名文件，若有则重新规划目标文件名
                dst_path = common_utils.get_new_path(dst_path)
                print(kwargs)
                image_utils.transcode(file_path, dst_path, dst_encode, **kwargs)
                succ_count += 1
            except Exception as e:
                failed_list.append((file_path, e))
                logger.error('{} 转换为 {} 失败! error: {}'.format(file_path, dst_encode, e))
            finally:
                self.rate_value += 1
        local_time = common_utils.get_times_now().get('time_str')
        msg = '【图片格式转换】  将 {} 下图片共 {} 张，转码成功 {} 张，转码为 {} 类型，转码至 {}'.format(src_dir, total_count, succ_count, dst_encode.upper(), dst_dir)
        # 输入路径是目录
        logger.info(msg)
        self.scr.insert('end', '{}\t{}\n'.format(local_time, msg))
        # 输出操作失败文件信息
        if len(failed_list):
            failed_msg = '\n\n以下文件操作失败:\n'
            for item in failed_list:
                failed_msg += '\n%s  --  error: %s' % item
            self.scr.insert('end', failed_msg)
        mBox.showinfo('任务完成', "图片格式转换完成!")

    def show_rate(self, total_count):
        """显示进度"""
        while True:
            self.pb1["value"] = self.rate_value
            time.sleep(0.2)  # 节省cpu资源
            logger.debug("rate:{}".format(self.rate_value))
            if self.rate_value >= total_count:
                self.pb1["value"] = total_count
                break

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        src_dir = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        if not dst_dir:  # 目标路径输入框未输入
            if os.path.isfile(src_dir):
                self.dst_dir.set(os.path.join(os.path.dirname(src_dir), '转码'))
            else:
                self.dst_dir.set(os.path.abspath(src_dir) + '_[转码]')
        src_encode = ''
        option_mode =  self.option_mode.get()
        if option_mode == '2':
            src_encode = 'heic'
        if option_mode == '3':
            src_encode = 'webp'
        t = threading.Thread(target=self.transcode, args=(src_encode,))
        t.daemon = True
        t.start()
        self.btn_show.config(state=tk.NORMAL)


class TxtEncodeFrame(BaseFrame):
    """文本文件编码转换"""
    def __init__(self, master=None):
        super().__init__(master)
        self.option_mode = tk.StringVar()  # '1' 导出xx编码的文本文件 '2' 文本编码转换
        self.encode_type = tk.StringVar()  # 编码格式
        self.continue_flag = tk.BooleanVar()  # 是否继续上次进度
        self.rename_flag = tk.BooleanVar()  # 是否重命名文件，在原文件名后添加_[UTF-8] 的编码描述
        self.rename_flag.set(False)
        self.rate_value = 0  # 进度条数值
        self.src_encode = tk.StringVar()  # 源文本编码格式
        self.dst_encode = tk.StringVar()  # 目标编码
        self.end_line_mode = tk.StringVar()  # 换行格式 '1' Windows(CRLF) '2' Unix（LF） '0' 系统默认
        self.move_flag = tk.BooleanVar()  # 移动文件 True  拷贝文件 False
        self.move_flag.set(True)
        self.original_mtime_flag = tk.BooleanVar()  # 是否继承原文件修改时间
        self.original_mtime_flag.set(True)
        self.fast_flag = tk.BooleanVar()  # 快速匹配 True 直接尝试用指定编码对文本进行解码，不报错则表示编码为指定编码  False chardet求编码
        self.fast_flag.set(True)
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "文本编码处理"
        ttk.Label(self.f_input, text='源路径: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=2)
        ttk.Label(self.f_input, text='目标路径: ').grid(row=1, pady=10)
        ttk.Entry(self.f_input, textvariable=self.dst_dir).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath2).grid(row=1, column=2)
        self.f_input_option = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option.grid(row=3, columnspan=5, sticky=tk.EW)
        self.f_input_option1 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option1.grid(row=0, column=1, sticky=tk.W)
        self.f_input_option2 = ttk.Frame(self.f_input_option)  # 选项容器
        self.f_input_option2.grid(row=1, column=1, sticky=tk.W)
        ttk.Label(self.f_input_option, text='选择操作: ').grid(row=0, column=0, pady=10)
        ttk.Radiobutton(self.f_input_option1, text="导出：", variable=self.option_mode, value='1', command=self.invoke_encode_type_input).grid(
            row=0, column=1)
        self.e_encode_type = ttk.Entry(self.f_input_option1, textvariable=self.encode_type, width=10)
        self.e_encode_type.grid(row=0, column=2)
        ttk.Label(self.f_input_option1, text='编码文件').grid(row=0, column=3, pady=10, padx=5)
        ttk.Checkbutton(self.f_input_option1, text="快速匹配", variable=self.fast_flag, onvalue=True, offvalue=False).grid(
            row=0, column=4, padx=5)
        ttk.Label(self.f_input_option1, text='  导出方式: ').grid(row=0, column=5, padx=5)
        ttk.Radiobutton(self.f_input_option1, text="剪切", variable=self.move_flag, value=True).grid(row=0, column=6)
        ttk.Radiobutton(self.f_input_option1, text="拷贝", variable=self.move_flag, value=False).grid(row=0, column=7)
        ttk.Checkbutton(self.f_input_option1, text="继续上次进度", variable=self.continue_flag, onvalue=True, offvalue=False).grid(
            row=0, column=9, padx=5)
        self.continue_flag.set(False)  # 设置默认选中否
        ttk.Checkbutton(self.f_input_option1, text="继承原修改时间", variable=self.original_mtime_flag, onvalue=True, offvalue=False).grid(
            row=0, column=10, padx=5)
        ttk.Radiobutton(self.f_input_option2, text="转码：", variable=self.option_mode, value='2', command=self.invoke_encode_type_input).grid(
            row=1, column=1)
        self.e_encode_type1 = ttk.Entry(self.f_input_option2, textvariable=self.src_encode, width=10)
        self.e_encode_type1.grid(row=1, column=2)
        ttk.Label(self.f_input_option2, text='->').grid(row=1, column=3, sticky=tk.EW)
        self.e_encode_type2 = ttk.Entry(self.f_input_option2, textvariable=self.dst_encode, width=10)
        self.e_encode_type2.grid(row=1, column=4)
        self.option_mode.set('2')
        ttk.Label(self.f_input_option2, text='  换行格式：').grid(row=1, column=5, padx=5)
        ttk.Radiobutton(self.f_input_option2, text="Windows(CRLF) ", variable=self.end_line_mode, value='1').grid(row=1, column=6)
        ttk.Radiobutton(self.f_input_option2, text="Unix(LF)", variable=self.end_line_mode, value='2').grid(row=1, column=7)
        ttk.Radiobutton(self.f_input_option2, text="系统默认", variable=self.end_line_mode, value='0').grid(row=1, column=8)
        self.end_line_mode.set('0')
        ttk.Checkbutton(self.f_input_option2, text="文件名添加编码格式", variable=self.rename_flag, onvalue=True, offvalue=False).grid(
            row=1, column=9, padx=5)
        ttk.Button(self.f_input, text="执行", command=self.run).grid(row=3, column=2)
        # 展示结果
        self.pb1 = ttk.Progressbar(self.f_state, orient="horizontal", length=850, value=0, mode="determinate")
        self.pb1.grid(row=0, sticky=tk.EW, pady=10)
        scrolW = 120
        scrolH = 35
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, sticky=tk.NSEW)
        self.invoke_encode_type_input()
        self.btn_show = ttk.Button(self.f_bottom, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=10)
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    @dragged_locked
    def dragged_files(self, files):
        """拖拽文件捕获"""
        self.clear()
        self.dst_dir.set("")
        for item in files:
            dir_path = item.decode(settings.SYSTEM_CODE_TYPE)
            self.src_dir.set(dir_path)
        src_dir = self.src_dir.get().strip()
        if os.path.isfile(src_dir):
            self.dst_dir.set(os.path.join(os.path.dirname(src_dir), '转码'))
        else:
            self.dst_dir.set(os.path.abspath(src_dir) + '_[转码]')

    def clear(self):
        """用于清除数据"""
        self.scr.delete(1.0, tk.END)
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        self.btn_show.config(state=tk.DISABLED)

    def invoke_encode_type_input(self):
        """用于编码类型输入框"""
        if self.option_mode.get() == '1':
            self.e_encode_type.config(state=tk.NORMAL)
            self.e_encode_type1.config(state=tk.DISABLED)
            self.e_encode_type2.config(state=tk.DISABLED)
        else:
            self.e_encode_type.config(state=tk.DISABLED)
            self.e_encode_type1.config(state=tk.NORMAL)
            self.e_encode_type2.config(state=tk.NORMAL)

    @deal_running_task_arg('文本文件编码转换')
    def transcode(self, src_path, dst_dir, src_encode, dst_encode, is_continue=False):
        """转码"""
        end_line_mode = self.end_line_mode.get()  # 换行格式
        original_mtime_flag = self.original_mtime_flag.get()  # 是否继承原修改时间
        rename_flag = self.rename_flag.get()
        self.scr.insert(tk.END, '{}\t开始遍历文件目录...\n'.format(common_utils.get_times_now().get('time_str')))
        path_list = common_utils.get_files_by_filetype(src_path, 'text')  # 找出所有文本类型文件
        self.rate_value = 0
        total_count = len(path_list)
        self.pb1["maximum"] = total_count
        local_time = common_utils.get_times_now().get('time_str')
        if total_count == 0:
            self.scr.insert(tk.END, '{}\t遍历文件目录完成,目录下无文件!\n'.format(local_time))
            mBox.showinfo('任务完成', "文本编码转换完成!")
            return
        self.scr.insert(tk.END, '{}\t遍历文件目录完成,找到文件共 {} 个，开始转码...\n'.format(local_time, total_count))
        t = threading.Thread(target=self.show_rate, args=(total_count,))  # 创建显示进度条子线程
        t.daemon = True
        t.start()
        failed_list = []  # 记录操作失败的文件
        succ_count = 0  # 记录转码成功的文件数
        for file_path in path_list:
            logger.debug('进度[{}/{}] file_path: {}\n'.format(self.rate_value, total_count, file_path))
            _path, filename = os.path.split(file_path)
            if rename_flag:
                name, ext = os.path.splitext(filename)
                new_name = name + "_[{}]".format(dst_encode.upper()) + ext
            else:
                new_name = filename
            if file_path == src_path:  # 单个文件转码
                dst_path = os.path.join(dst_dir, new_name)
            else:  # 目录转码
                dst_path = os.path.join(_path.replace(src_path, dst_dir), new_name)
            if is_continue is True:
                if os.path.exists(dst_path):
                    continue
            dst_tmp_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_tmp_dir):
                os.makedirs(dst_tmp_dir)
            try:
                _encode = src_encode if src_encode else common_utils.get_txt_encode(file_path)  # 若无输入则自动适配
                with open(file_path, 'r', encoding=_encode) as f:
                    text = f.read()
                    # logger.debug(text)
                # 判断是否目标路径下是否有重名文件，若有则重新规划目标文件名
                dst_path = common_utils.get_new_path(dst_path)
                # 转码并更改换行格式
                if end_line_mode in ['1', '2']:
                    if end_line_mode == '1':  # 转为CRLF
                        text = text.replace('\r\n', '\n').replace('\n', '\r\n')  # 转为CRLF
                # 转码
                with open(dst_path, 'wb') as f:
                    f.write(text.encode(dst_encode, errors='ignore'))
                succ_count += 1
                if original_mtime_flag:
                    _mtime = os.path.getmtime(file_path)
                    os.utime(dst_path, (_mtime, _mtime))
            except Exception as e:
                failed_list.append((file_path, e))
                logger.debug('error! {}'.format(e))
            finally:
                self.rate_value += 1
        msg = '【文本编码转换】  将 {} 下共 {} 个文件，转码成功 {} 个，转码为 {} 至 {}'.format(src_path, total_count, succ_count, dst_encode, dst_dir)
        logger.info(msg)
        self.scr.insert('end', '{}\t{}\n'.format(common_utils.get_times_now().get('time_str'), msg))
        # 输出操作失败文件信息
        if len(failed_list):
            failed_msg = '\n\n以下文件操作失败:\n'
            failed_count = len(failed_list)
            num = 0
            for _path, error_msg in failed_list:
                num += 1
                failed_msg += '\n[{}/{}] 【path】:{}, 【error】:{}'.format(num, failed_count, _path, error_msg)
            self.scr.insert('end', failed_msg)
        mBox.showinfo('任务完成', "文本编码转换完成!")
    
    @deal_running_task_arg('检索指定编码文本')
    def find_files(self, file_dir, dst_dir, encode):
        """找到符合文件类型的文件，并导出"""
        move_flag = self.move_flag.get()  # 文件导出模式
        local_time = common_utils.get_times_now().get('time_str')
        self.scr.insert(tk.END, '{}\t开始遍历文件目录并进行编码匹配...\n'.format(local_time))
        if encode:
            if self.fast_flag.get():  # 直接用指定编码去尝试解码，不报错则代表编码为指定编码格式
                path_list = common_utils.get_files_by_encode2(file_dir, encode.upper())
            else:  # chardet 求解码
                path_list = common_utils.get_files_by_encode(file_dir, encode.upper())
        else:
            path_list = []
        self.rate_value = 0
        total_count = len(path_list)
        self.pb1["maximum"] = total_count
        local_time = common_utils.get_times_now().get('time_str')
        if total_count == 0:
            self.scr.insert(tk.END, '{}\t遍历文件目录完成,未找到 {} 编码的文本！\n'.format(local_time, encode))
            mBox.showinfo('任务完成', "检索指定编码文件完成!")
            return
        self.scr.insert(tk.END, '{}\t遍历文件目录完成,找到 {} 编码的文件共 {} 个，开始导出...\n'.format(local_time, encode, total_count))
        t = threading.Thread(target=self.show_rate, args=(total_count,))  # 创建显示进度条子线程
        t.daemon = True
        t.start()
        failed_list = []  # 记录操作失败的文件
        new_old_record = {}
        for file_path in path_list:
            self.rate_value += 1
            # 将要存储的路径及名称
            path, filename = os.path.split(file_path)
            dst_path = os.path.join(path.replace(file_dir, dst_dir), filename)
            if os.path.exists(dst_path):  # 目标目录已存在同名文件，则跳出该文件导出操作
                failed_list.append(file_path)
                logger.debug('{} 已存在！'.format(dst_path))
                continue
            try:
                dst_tmp_dir = os.path.dirname(dst_path)
                if not os.path.exists(dst_tmp_dir):
                    os.makedirs(dst_tmp_dir)
                if move_flag is True:
                    shutil.move(file_path, dst_path)
                else:
                    shutil.copy2(file_path, dst_path)
                new_old_record[dst_path] = file_path
            except Exception as e:
                failed_list.append(file_path)
                logger.debug('error!')
        # 记录到日志
        time_res = common_utils.get_times_now()
        local_time = time_res.get('time_str')
        # 写出新旧文件名记录
        time_str = time_res.get('time_num_str') # 用来生成文件名
        record_path = os.path.join(settings.RECORD_DIR, 'new_old_record_{}.txt'.format(time_str))
        common_utils.export_new_old_record(new_old_record, record_path)
        msg = '【检索指定编码文件】  检索到 {} 下 {} 编码的文件共 {} 个'.format(file_dir, encode, total_count)
        msg += '，导出至 {}，新旧文件名记录到 {}\n'.format(dst_dir, record_path)
        logger.info(msg)
        self.scr.insert('end', '{}\t{}\n'.format(local_time, msg))
        # 输出操作失败文件信息
        if len(failed_list):
            failed_msg = '\n\n以下文件操作失败:\n'
            failed_msg += '\n'.join(failed_list)
            self.scr.insert('end', failed_msg)
        mBox.showinfo('任务完成', "检索指定编码文件完成!")

    def show_rate(self, total_count):
        """显示进度"""
        while True:
            self.pb1["value"] = self.rate_value
            time.sleep(0.3)  # 节省cpu资源
            logger.debug("rate:{}".format(self.rate_value))
            if self.rate_value >= total_count:
                self.pb1["value"] = total_count
                break

    def run(self):
        self.clear()
        # 校验输入路径
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        src_path = self.src_dir.get()
        dst_dir = self.dst_dir.get()
        if not dst_dir:  # 目标路径输入框未输入
            if os.path.isfile(src_path):
                self.dst_dir.set(os.path.join(os.path.dirname(src_path), '转码'))
            else:
                self.dst_dir.set(os.path.abspath(src_path) + '_[转码]')
            dst_dir = self.dst_dir.get()
        src_encode = self.src_encode.get()
        dst_encode = self.dst_encode.get()
        option_mode = self.option_mode.get()
        encode_type = self.encode_type.get()
        continue_flag = self.continue_flag.get()
        if option_mode == '1':  # 导出指定编码文本
            dst_path = os.path.join(dst_dir, '导出{}'.format(encode_type.upper()))
            t = threading.Thread(target=self.find_files, args=(src_path, dst_path, encode_type.lower()))
            t.daemon = True
            t.start()
        else:
            dst_path = os.path.join(dst_dir, '{}'.format(dst_encode.upper()))
            t = threading.Thread(target=self.transcode, args=(src_path, dst_path, src_encode, dst_encode, continue_flag))
            t.daemon = True
            t.start()
        self.btn_show.config(state=tk.NORMAL)


class FileArrangeFrame(BaseFrame):
    """整理文件"""
    def __init__(self, master=None):
        super().__init__(master)
        self.search_mode = tk.StringVar()  # 搜索模式 '1' 文件类别 '2'文件时间  '3' 媒体文件时长 '4' 媒体文件分辨率 '5' 拍摄设备 '6' 自定义数据
        self.search_str = tk.StringVar()  # 搜索语句
        self.export_mode = tk.IntVar()  # 导出模式 1.导出到单级目录并附带目录结构描述 2.导出到单级目录 3.保持源目录结构
        self.same_file_option = tk.StringVar()  # 遇到已存在同名文件处理方式  'ask'询问，'overwrite' 覆盖，'skip' 跳过
        self.rec_flag = tk.BooleanVar()  # 是否递归操作子目录和子文件  True 递归
        self.ext_extend_flag = tk.BooleanVar()  # 对不能字节码识别的文件，是否使用后缀名识别 比如私有格式，文本文件等  True 使用后缀名匹配
        self.mime_desc_flag = tk.BooleanVar()  # 按MIME描述  True 使用MIME类型描述，False 使用后缀名描述 例如 jpg 格式 True image/jpeg  False jpeg 例如png True就分类到 image下的png目录下 Flase就 image或者png 
        self.resolution_postion_flag = tk.BooleanVar()  # 分辨率位置是否严格一致，True 要求比对视频分辨率宽高必须和输入宽高位置一致，例输入1920*1080 则视频为1080*1920则不符合
        self.mode_option = tk.StringVar()  # 下拉框参数 文件类别、数据类型， 创建时间、修改时间、拍摄时间
        self.search_mode.set('1')
        self.export_mode.set(1)
        self.same_file_option.set('skip')
        self.rec_flag.set(True)
        self.ext_extend_flag.set(False)
        self.mime_desc_flag.set(False) 
        self.resolution_postion_flag.set(False)
        self.OPTION_DICT = {'1': ['文件类别', '数据类型'],
                            '2': ['修改时间', '创建时间', '拍摄时间'],
                            '3': ['媒体时长',],
                            '4': ['分辨率'],
                            '5': ['设备品牌', '设备型号'],
                            '6': ['自定义字段'],
                            '7': ['文件大小']
                            }  # 选项内容
        self.result = {'files': [], 'dirs': []}  # 用于储存文件操作的搜索结果  过滤之后进行文件复制移动的文件信息
        self.createPage()

    def createPage(self):
        self.l_title["text"] = "文件分类"
        ttk.Label(self.f_input, text='文件目录: ').grid(row=0, pady=10)
        ttk.Entry(self.f_input, textvariable=self.src_dir).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(self.f_input, text="浏览", command=self.selectPath1).grid(row=0, column=4)
        self.f_input_option1 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option1.grid(row=2, columnspan=5, sticky=tk.EW)
        self.f_input_option2 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option2.grid(row=3, columnspan=5, sticky=tk.EW)
        self.f_input_option3 = ttk.Frame(self.f_input)  # 选项容器
        self.f_input_option3.grid(row=4, columnspan=5, sticky=tk.EW)
        ttk.Label(self.f_input_option1, text='模式选择: ').grid(row=0, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option1, text="文件类型", variable=self.search_mode, command=self.chg_search_mode,
                        value='1').grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option1, text="文件时间", variable=self.search_mode, command=self.chg_search_mode,
                        value='2').grid(row=0, column=2, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option1, text="媒体时长", variable=self.search_mode, command=self.chg_search_mode,
                        value='3').grid(row=0, column=3, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option1, text="媒体分辨率", variable=self.search_mode, command=self.chg_search_mode,
                        value='4').grid(row=0, column=4, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option1, text="设备信息", variable=self.search_mode, command=self.chg_search_mode,
                        value='5').grid(row=0, column=5, sticky=tk.EW)
        ttk.Radiobutton(self.f_input_option1, text="自定义数据段", variable=self.search_mode, command=self.chg_search_mode,
                        value='6').grid(row=0, column=6, sticky=tk.W)
        ttk.Radiobutton(self.f_input_option1, text="文件大小", variable=self.search_mode, command=self.chg_search_mode,
                        value='7').grid(row=0, column=7, sticky=tk.W)
        ttk.Label(self.f_input_option2, text='参数选择: ').grid(row=1, pady=5)
        self.optionChosen = ttk.Combobox(self.f_input_option2, width=15, textvariable=self.mode_option)
        self.optionChosen.grid(row=1, column=1, sticky=tk.W)
        self.optionChosen.config(state='readonly')  # 设为只读模式
        self.c_ext_extend_flag = ttk.Checkbutton(self.f_input_option2, text="后缀名识别", variable=self.ext_extend_flag, onvalue=True, offvalue=False)
        self.c_ext_extend_flag.grid(row=1, column=6, padx=5)
        self.c_mime_desc_flag = ttk.Checkbutton(self.f_input_option2, text="MIME归类", variable=self.mime_desc_flag, onvalue=True, offvalue=False)
        self.c_mime_desc_flag.grid(row=1, column=7, padx=5)
        self.c_resolution_postion = ttk.Checkbutton(self.f_input_option2, text="分辨率位置严格一致", variable=self.resolution_postion_flag, onvalue=True, offvalue=False)
        self.c_resolution_postion.grid(row=1, column=8, padx=5)
        ttk.Label(self.f_input_option3, text='参数设置: ').grid(row=3, sticky=tk.W)
        self.e_search_str = ttk.Entry(self.f_input_option3, textvariable=self.search_str, width=100)
        self.e_search_str.grid(row=3, column=1)
        ttk.Button(self.f_input, text="归类", command=self.deal_search).grid(row=4, column=4, pady=5)
        # 展示结果
        scrolW = 120
        scrolH = 38
        self.scr = scrolledtext.ScrolledText(self.f_content, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(row=0, column=0, sticky=tk.NSEW)
        self.f_filter = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_filter.grid(row=1, columnspan=3, sticky=tk.EW)
        self.f_bottom_option1 = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_bottom_option1.grid(row=2, columnspan=3, sticky=tk.EW)
        self.f_bottom_option2 = ttk.Frame(self.f_bottom)  # 选项容器
        self.f_bottom_option2.grid(row=3, columnspan=3, sticky=tk.EW)
        ttk.Label(self.f_bottom_option1, text='文件操作模式: ').grid(row=1, sticky=tk.EW)
        ttk.Radiobutton(self.f_bottom_option1, text="导出到单级目录并附带目录描述", variable=self.export_mode, value=1).grid(row=1, column=1)
        ttk.Radiobutton(self.f_bottom_option1, text="导出到单级目录", variable=self.export_mode, value=2).grid(row=1, column=2)
        ttk.Radiobutton(self.f_bottom_option1, text="保持原目录层次", variable=self.export_mode, value=3).grid(row=1, column=3)
        ttk.Label(self.f_bottom_option1, text='遇重名: ').grid(row=1, column=4, padx=5)
        ttk.Radiobutton(self.f_bottom_option1, text="覆盖", variable=self.same_file_option, value='overwrite').grid(row=1, column=5)
        ttk.Radiobutton(self.f_bottom_option1, text="跳过", variable=self.same_file_option, value='skip').grid(row=1, column=6)
        self.btn_show = ttk.Button(self.f_bottom_option2, text="查看结果", command=self.showFiles, state=tk.DISABLED)
        self.btn_show.grid(row=0, column=0, pady=5)
        self.btn_restore = ttk.Button(self.f_bottom_option2, text="还原文件", command=self.restoreFiles, state=tk.DISABLED)
        self.btn_restore.grid(row=0, column=1)
        self.btn_undo_restore = ttk.Button(self.f_bottom_option2, text="撤销还原", command=self.undoRestoreFiles, state=tk.DISABLED)
        self.btn_undo_restore.grid(row=0, column=2)
        self.chg_search_mode()  # 设置选项下拉框值
        windnd.hook_dropfiles(self, func=self.dragged_files)  # 监听文件拖拽操作

    def chg_search_mode(self):
        """用于修改不同模式的输入组件"""
        search_mode = self.search_mode.get()  # 搜索模式
        # self.search_str.set('')
        if search_mode in ('1', '5'):
            self.search_str.set('')
            self.e_search_str.config(state=tk.DISABLED)
        else:
            self.e_search_str.config(state=tk.NORMAL)
        if search_mode == '2':
            self.search_str.set(r'%Y-%m-%d')  # 设置默认参数
        if search_mode == '3':
            self.search_str.set(r'%H%M')  # 设置默认参数
        if search_mode == '4':
            self.c_resolution_postion.config(state=tk.NORMAL)
            self.search_str.set(r'%wx%h')  # 设置默认参数
        else:
            self.c_resolution_postion.config(state=tk.DISABLED)
        if search_mode == '7':
            self.search_str.set(r'%MB')  # 设置默认参数
        # 设置单选框按钮内容和搜索语句标签
        value_list = self.OPTION_DICT.get(search_mode)
        self.optionChosen['values'] = value_list if value_list else ['',]
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标

    def disable_all_elements(self):
        """用来锁定所有的输入组件，防止程序执行过程中出错"""
        # 递归方式获取
        self.lock_elements = []
        self.all_children(self.f_input, self.lock_elements)
        self.all_children(self.f_bottom_option1, self.lock_elements)
        for element in self.lock_elements:
            element.config(state=tk.DISABLED)

    def selectPath1(self):
        self.clear()
        path_ = askdirectory()
        self.src_dir.set(path_)

    @deal_running_task_arg('文件分类-整理文件')
    def do_search(self):
        """实际搜索操作"""
        search_path = self.src_dir.get()
        search_mode = self.search_mode.get()
        FUNC_DICT = {
                '1': self.search_by_type,
                '2': self.search_by_time,
                '3': self.search_by_duration,
                '4': self.search_by_resolution,
                '5': self.search_by_dev,
                '6': self.search_by_data,
                '7': self.search_by_size
                }
        self.scr.insert('end', '%s  正在分析 %s 目录下的文件信息...\n' % (common_utils.get_times_now().get('time_str'), search_path))
        FUNC_DICT[search_mode]()  # 执行搜索分析
        self.scr.insert('end', '%s  分析完成！开始操作文件...\n' % common_utils.get_times_now().get('time_str'))
        self.deal_files()  # 操作文件

    def clear(self):
        self.record_path = None
        self.dst_dir.set('')
        self.scr.delete(1.0, tk.END)
        self.result = {}
        self.btn_restore.config(state=tk.DISABLED)
        self.btn_show.config(state=tk.DISABLED)
        self.btn_undo_restore.config(state=tk.DISABLED)

    def search_by_type(self):
        """按文件类型搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        option = self.mode_option.get()
        ext_extend_flag = self.ext_extend_flag.get()  # 对不能字节码识别的文件，是否使用后缀名识别
        mime_desc_flag = self.mime_desc_flag.get()  # 按MIME描述分类
        if ext_extend_flag:
            res = common_utils.get_files_with_filetype_extended(src_path)
        else:
            res = common_utils.get_files_with_filetype(src_path)
        # 整理
        # logger.debug(res)
        for _path, type_dict in res.items():
            _cate = None
            if type_dict:
                _mime = type_dict.get('mime')
                _extension = type_dict.get('extension')
                if option == '文件类别':
                    _cate = _mime.split('/')[0]  # video image等
                else:
                    _cate = _mime if mime_desc_flag else _extension  # 'text/javascript' 和 'js' 的区别
            if not _cate:
                _cate = '未知类型'
            if _cate in self.result:
                self.result[_cate].append(_path)
            else:
                self.result[_cate] = [_path,]

    def search_by_time(self):
        """按文件时间搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        # 遍历获取文件路径
        file_list = []
        for root, dirs, files in os.walk(src_path):
            for item in files:
                file_list.append(os.path.join(root, item))
        # 获取时间信息
        option = self.mode_option.get()
        time_str = self.search_str.get().strip().replace(' ', '_').replace(':', '-')  # 时间字符串%Y-%M
        # 整理
        for _path in file_list:
            timestamp = self.get_file_timestamp(_path, option)  # 获取时间戳
            time_info = time.strftime(time_str, time.localtime(timestamp))  # 获取想要的时间信息
            if time_info:
                if time_info in self.result:
                    self.result[time_info].append(_path)
                else:
                    self.result[time_info] = [_path,]

    def search_by_duration(self):
        """按视频/音频时长搜索
        media_type 文件类型 'video', 'audio'
        """
        src_path = common_utils.check_path(self.src_dir.get())
        func = common_utils.get_files_with_fileCategory_extended if self.ext_extend_flag.get() else common_utils.get_files_with_fileCategory
        res = func(src_path)
        _format = self.search_str.get()
        FUNC_DICT = {
                'video': common_utils.get_video_info,
                'audio': common_utils.get_audio_info
        }
        for _path, _cate in res.items():
            if _cate not in ('video', 'audio'):
                continue
            # 获取媒体时长
            duration_sec = FUNC_DICT[_cate](_path).get('duration_sec')
            duration_str = common_utils.make_duration_str(duration_sec, _format)
            # 整理
            if duration_str:
                if duration_str in self.result:
                    self.result[duration_str].append(_path)
                else:
                    self.result[duration_str] = [_path,]

    def search_by_resolution(self):
        """按分辨率搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        func = common_utils.get_files_with_fileCategory_extended if self.ext_extend_flag.get() else common_utils.get_files_with_fileCategory
        res = func(src_path)
        resolution_postion_flag = self.resolution_postion_flag.get()  # 强制分辨率位置一致
        FUNC_DICT = {
                'video': common_utils.get_video_resolution,
                'image': common_utils.get_image_resolution
        }
        for _path, _cate in res.items():
            if _cate not in ('video', 'image'):
                continue
            # 获取分辨率
            res = FUNC_DICT[_cate](_path)
            width = int(res.get('width'))
            height = int(res.get('height'))
            if resolution_postion_flag:
                resolution_str = '%sx%s' % (width, height)
            else:  # 无强制位置信息，则默认取大的分辨率在前
                resolution_str = ('%sx%s' % (width, height)) if (width > height) else ('%sx%s' % (height, width))
            # 整理
            if resolution_str:
                if resolution_str in self.result:
                    self.result[resolution_str].append(_path)
                else:
                    self.result[resolution_str] = [_path,]

    def search_by_dev(self):
        """按拍摄设备搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        func = common_utils.get_files_with_fileCategory_extended if self.ext_extend_flag.get() else common_utils.get_files_with_fileCategory
        res = func(src_path)
        option = self.mode_option.get()
        FUNC_DICT = {
                'video': common_utils.get_video_info,
                'image': common_utils.get_image_info
        }
        for _path, _cate in res.items():
            if _cate not in ('video', 'image'):
                continue
            res = FUNC_DICT[_cate](_path)
            if option == '设备品牌':
                _str = res.get('hardware_make')
            else:
                _str = res.get('hardware_model')
            if _str:  # 整理
                if _str in self.result:
                    self.result[_str].append(_path)
                else:
                    self.result[_str] = [_path,]

    def search_by_data(self):
        """按自定义字段搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        func = common_utils.get_files_with_fileCategory_extended if self.ext_extend_flag.get() else common_utils.get_files_with_fileCategory
        res = func(src_path)
        search_str = self.search_str.get()
        FUNC_DICT = {
                'video': common_utils.get_media_meta_sample,
                'image': common_utils.get_image_meta,
                'audio': common_utils.get_media_meta_sample
        }
        for _path, _cate in res.items():
            if _cate not in ('video', 'image', 'audio'):
                continue
            res = FUNC_DICT[_cate](_path)
            _str = ''
            for item in res:
                if re.search(search_str, item, re.I):
                    _str = item.replace(':', '_').replace('.','_') + '__' + res[item]
                    _str = _str[:30]  # 避免字符过多导致路径名太长出错
                    break
            # 整理
            if not _str:
                continue
            if _str in self.result:
                self.result[_str].append(_path)
            else:
                self.result[_str] = [_path,]

    def search_by_size(self):
        """按文件大小搜索"""
        src_path = common_utils.check_path(self.src_dir.get())
        # 遍历获取文件路径
        file_dict = {}
        for root, dirs, files in os.walk(src_path):
            for item in files:
                file_path = os.path.join(root, item)
                file_dict[file_path] = os.path.getsize(file_path)
        _str = self.search_str.get().strip()  # 时间字符串%Y-%M
        # 整理
        for _path, _size in file_dict.items():
            size_info = common_utils.make_size_str(_size, _str)
            if size_info:
                if size_info in self.result:
                    self.result[size_info].append(_path)
                else:
                    self.result[size_info] = [_path,]

    def deal_search(self):
        """为搜索操作新开一个线程,避免高耗时操作阻塞GUI主线程"""
        self.clear()
        # 校验输入路径
        flag = self.check_path_exists(self.src_dir)
        if not flag:
            return
        t = threading.Thread(target=self.do_search)
        t.daemon = True
        t.start()

    @staticmethod
    def get_file_timestamp(file_path, time_option):
        """获取文件的修改时间、创建时间、或者拍摄时间
        time_option  # 修改时间   创建时间  照片拍摄时间
        """
        timestamp = None
        if time_option == '修改时间':
            timestamp = os.path.getmtime(file_path)
        elif time_option == '创建时间':
            timestamp = os.path.getctime(file_path)
        else:  # 获取拍摄时间
            date_information = common_utils.get_media_encoded_date(file_path)
            if date_information:  # 转换为时间戳
                timestamp = time.mktime(time.strptime(date_information, r'%Y-%m-%d %H:%M:%S'))
        return timestamp

    def deal_files(self):
        """处理文件操作"""
        src_dir = common_utils.check_path(self.src_dir.get())
        option = self.mode_option.get()
        search_str = self.search_str.get()
        dst_dir = src_dir + '_[文件分类-%s]' % option
        self.dst_dir.set(dst_dir)
        export_mode = self.export_mode.get()  # 导出模式 1.导出到单级目录并附带目录结构描述 2.导出到单级目录 3.保持源目录结构
        same_file_option = self.same_file_option.get()  # 同名文件处理'overwrite' 'skip'
        new_old_record = {}
        failed_list = []  # 用于记录拷贝或剪切失败的文件信息
        skip_list = []  # 用来记录跳过的文件信息
        # 移动文件的函数
        FUNC_DICT = {
            'overwrite': common_utils.move_file_force,
            'skip': common_utils.move_file_skip
        }
        # 新文件名命名函数
        if export_mode == 1:  # 单级目录并附带目录描述
            get_new_path_func = common_utils.make_new_path
        elif export_mode == 2:  # 单级目录
            get_new_path_func = lambda file_path, old_dir, new_dir, none_para: os.path.join(new_dir, os.path.basename(file_path))
        else:  # 源目录层级
            get_new_path_func = lambda file_path, old_dir, new_dir, none_para: file_path.replace(old_dir, new_dir)
        # 操作文件
        for item in self.result:
            tmp_dir = os.path.join(dst_dir, item)
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            for old_path in self.result[item]:
                new_path = get_new_path_func(old_path, src_dir, tmp_dir, True)
                res_flag = FUNC_DICT[same_file_option](old_path, new_path)
                if res_flag == 0:
                    failed_list.append(old_path)
                elif res_flag == 2:
                    skip_list.append(old_path)
                else:
                    new_old_record[new_path] = old_path  # 保存原文件信息，格式为"{new_file: old_file, }"
        # 写出到记录文件和日志
        msg = ''
        time_res = common_utils.get_times_now()
        time_str = time_res.get('time_str')
        time_num_str = time_res.get('time_num_str')
        self.scr.insert('end', '%s  操作文件结束！\n' % time_str)
        if len(new_old_record):
            self.record_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("new_old_record", time_num_str))
            common_utils.export_new_old_record(new_old_record, self.record_path)  # 将文件剪切前后文件信息导出到new_old_record
            msg = "【文件分类】  从 %s 按 %s 归类文件(参数设置: %s)到 %s,新旧文件名导出到 %s" % (src_dir, option, search_str, dst_dir, self.record_path)
            if len(skip_list):
                skip_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("skip", time_num_str))
                msg += "\n\t\t 共有 %s 个文件遇重名跳过,文件信息导出到 %s" % (len(skip_list), skip_path)
                common_utils.export_path_record(skip_list, skip_path)
            if len(failed_list):
                failed_path = os.path.join(settings.RECORD_DIR, '%s_%s.txt' % ("failed", time_num_str))
                msg += "\n\t\t 共有 %s 个文件操作失败,文件信息导出到 %s" % (len(failed_list), failed_path)
                common_utils.export_path_record(failed_list, failed_path)
            logger.info(msg)
        mBox.showinfo("任务完成", '文件整理分类操作完成！')
        self.scr.insert('end', "\n%s\n" % msg)
        self.scr.see('end')
        self.btn_show.config(state=tk.NORMAL)
        self.btn_restore.config(state=tk.NORMAL)


class SettingFrame(tk.Frame):
    """计算视频相似度"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.frame = ttk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.BASE_DIR = tk.StringVar()
        self.RECORD_DIR = tk.StringVar()  # 保存记录的目录
        self.SAFE_DEL_DIR = tk.StringVar()  # 保存删除文件备份的目录
        self.DB_DIR = tk.StringVar()  # 保存数据相关的目录
        self.LOG_DIR = tk.StringVar()  # 保存日志的目录
        self.FFMPEG_PATH = tk.StringVar()  # ffmpeg路径
        self.SAFE_DEL_LOCAL = tk.BooleanVar()  # 标记是否在文件所在分区创建safe_del文件夹，False 在程序目录下创建safe_del文件夹
        self.SAFE_FLAG = tk.BooleanVar()  # 标记执行文件删除操作时是否使用安全删除选项(安全删除选项会将被删除的文件剪切到safe_del目录下)
        self.SKIP_FLAG = tk.BooleanVar()  # 标记执行文件复制或者粘贴操作时是否遇见同名同路径文件是否跳过选项(True跳过 False覆盖)
        self.SYSTEM_CODE_TYPE = tk.StringVar()  # 系统的编码格式，用于跟windnd配合解码拖拽的文件名
        self.IO_THREAD_NUM = tk.StringVar()  # IO线程数，即提取视频帧图像时开启的线程数
        self.CALC_THREAD_NUM = tk.StringVar()  # 计算线程数，即计算图片视频相似度时开启的线程数
        self.auth_flag = False  # 开放修改权限
        self.init_setting()
        self.createPage()

    def init_setting(self):
        """用于导入或者更新设置界面的设置信息"""
        self.BASE_DIR.set(settings.BASE_DIR)
        self.RECORD_DIR.set(settings.RECORD_DIR)
        self.DB_DIR.set(settings.DB_DIR)
        self.LOG_DIR.set(settings.LOG_DIR)
        self.SAFE_DEL_DIR.set(settings.SAFE_DEL_DIR)
        self.SYSTEM_CODE_TYPE.set(settings.SYSTEM_CODE_TYPE)
        self.SAFE_DEL_LOCAL.set(settings.SAFE_DEL_LOCAL)
        self.SAFE_FLAG.set(settings.SAFE_FLAG)
        self.SKIP_FLAG.set(settings.SKIP_FLAG)
        self.FFMPEG_PATH.set(settings.FFMPEG_PATH)
        self.IO_THREAD_NUM.set(settings.IO_THREAD_NUM)
        self.CALC_THREAD_NUM.set(settings.CALC_THREAD_NUM)

    def open_path(self, pathObj):
        temp_path = pathObj.get()
        if os.path.exists(temp_path):
            webbrowser.open(temp_path)

    def open_path2(self, pathObj):
        temp_path = pathObj.get()
        temp_path = os.path.dirname(temp_path)
        if os.path.exists(temp_path):
            webbrowser.open(temp_path)

    def createPage(self):
        self.f_title = ttk.Frame(self)  # 页面标题
        self.f_input = ttk.Frame(self)  # 输入部分
        self.f_input2 = ttk.Frame(self)  # 输入部分
        self.f_option = ttk.Frame(self)
        self.f_bottom = ttk.Frame(self)  # 页面底部
        self.f_title.pack()
        self.f_input.pack(fill=tk.X, expand=True)
        self.f_input2.pack(fill=tk.X, expand=True)
        self.f_option.pack(fill=tk.X, expand=True)
        self.f_bottom.pack(fill=tk.X, expand=True)
        self.f_input.grid_columnconfigure(1, weight=1)
        self.f_bottom.grid_columnconfigure(1, weight=1)
        self.l_title = tk.Label(self.f_title, text='设置界面', font=('Arial', 12))
        self.l_title.pack(fill=tk.X, expand=True, side=tk.TOP, anchor=tk.NW)
        ttk.Label(self.f_input, text='保存记录的目录: ').grid(row=1, pady=10)
        self.e1 = ttk.Entry(self.f_input, textvariable=self.RECORD_DIR)
        self.e1.grid(row=1, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="查看", command=lambda: self.open_path(self.RECORD_DIR)).grid(row=1, column=4)
        ttk.Label(self.f_input, text='保存数据库的目录: ').grid(row=2, pady=10)
        self.e2 = ttk.Entry(self.f_input, textvariable=self.DB_DIR)
        self.e2.grid(row=2, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="查看", command=lambda: self.open_path(self.DB_DIR)).grid(row=2, column=4)
        ttk.Label(self.f_input, text='保存日志的目录: ').grid(row=3, pady=10)
        self.e3 = ttk.Entry(self.f_input, textvariable=self.LOG_DIR)
        self.e3.grid(row=3, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="查看", command=lambda: self.open_path(self.LOG_DIR)).grid(row=3, column=4)
        ttk.Label(self.f_input, text='FFMPEG路径: ').grid(row=6, pady=10)
        self.e8 = ttk.Entry(self.f_input, textvariable=self.FFMPEG_PATH)
        self.e8.grid(row=6, column=1, columnspan=3, sticky=tk.EW)
        ttk.Button(self.f_input, text="查看", command=lambda: self.open_path2(self.FFMPEG_PATH)).grid(row=6, column=4)

        ttk.Label(self.f_input2, text='SAFE_DIR目录名: ').grid(row=7, pady=10)
        self.e6 = ttk.Entry(self.f_input2, textvariable=self.SAFE_DEL_DIR, width=15)
        self.e6.grid(row=7, column=1, sticky=tk.W)
        ttk.Label(self.f_input2, text='系统的编码格式: ').grid(row=8, column=0, pady=10)
        self.e7 = ttk.Entry(self.f_input2, textvariable=self.SYSTEM_CODE_TYPE, width=15)
        self.e7.grid(row=8, column=1, sticky=tk.W)
        ttk.Label(self.f_input2, text='IO线程数: ').grid(row=9, column=0, pady=10)
        self.e9 = ttk.Entry(self.f_input2, textvariable=self.IO_THREAD_NUM, width=15)
        self.e9.grid(row=9, column=1, sticky=tk.W)
        ttk.Label(self.f_input2, text='计算线程数: ').grid(row=10, column=0, pady=10)
        self.e10 = ttk.Entry(self.f_input2, textvariable=self.CALC_THREAD_NUM, width=15)
        self.e10.grid(row=10, column=1, sticky=tk.W)

        self.r1 = ttk.Checkbutton(self.f_option, text="在文件所在分区创建SAFE_DEL文件夹", variable=self.SAFE_DEL_LOCAL, onvalue=True,offvalue=False)
        self.r1.grid(row=0, column=0, padx=10)
        self.r2 = ttk.Checkbutton(self.f_option, text="使用安全删除", variable=self.SAFE_FLAG, onvalue=True,offvalue=False)
        self.r2.grid(row=0, column=1, padx=10)
        ttk.Label(self.f_option, text='遇到路径重复的文件: ').grid(row=0, column=2, pady=10, padx=5)
        self.r3 = ttk.Radiobutton(self.f_option, text="跳过", variable=self.SKIP_FLAG, value=True)
        self.r3.grid(row=0, column=3, padx=5)
        self.r4 = ttk.Radiobutton(self.f_option, text="覆盖", variable=self.SKIP_FLAG, value=False)
        self.r4.grid(row=0, column=4, padx=5)

        ttk.Button(self.f_bottom, text="权限验证", command=self.mod_auth_flag).grid(row=0, column=2)
        self.btn1 = ttk.Button(self.f_bottom, text="保存设置", command=self.export_config)
        self.btn1.grid(row=0, column=3)
        self.btn2 = ttk.Button(self.f_bottom, text="恢复默认设置", command=self.reset_config)
        self.btn2.grid(row=0, column=4)
        self.invoke_entry()  # 设置状态

    def export_config(self):
        """用于保存设置信息到配置文件"""
        settings.config["SAFE_DEL_DIR"] = self.SAFE_DEL_DIR.get()
        settings.config["SAFE_DEL_LOCAL"] = self.SAFE_DEL_LOCAL.get()
        settings.config["SAFE_FLAG"] = self.SAFE_FLAG.get()
        settings.config["SKIP_FLAG"] = self.SKIP_FLAG.get()
        settings.config["SYSTEM_CODE_TYPE"] = self.SYSTEM_CODE_TYPE.get()
        settings.config["FFMPEG_PATH"] = self.FFMPEG_PATH.get()
        settings.config["IO_THREAD_NUM"] = self.IO_THREAD_NUM.get()
        settings.config["CALC_THREAD_NUM"] = self.CALC_THREAD_NUM.get()
        settings.export_config()
        mBox.showinfo("任务完成", "保存配置信息成功！\n为确保数据安全程序将退出!请重启程序!")
        self.root.destroy()

    def reset_config(self):
        """用于恢复默认配置"""
        settings.reset_config()
        mBox.showinfo("任务完成", "恢复默认设置成功！\n为确保数据安全程序将退出!请重启程序!")
        self.root.destroy()

    def mod_auth_flag(self):
        """开放修改权限"""
        if len(running_task) != 0:
            msg = '现有 %s 个任务正在进行！' % len(running_task)
            msg += '\n程序当前有正在执行的任务,不能修改配置!'
            mBox.showwarning('权限拒绝', msg)
            return
        self.auth_flag= True
        self.invoke_entry()

    def invoke_entry(self):
        """用于设置Entry和Radiobutton只读和可读写状态"""
        elements = [self.e6, self.e7, self.e8, self.e9, self.e10, self.r1, self.r2, self.r3, self.r4, self.btn1, self.btn2]
        for item in [self.e1, self.e2, self.e3]:
            item["state"] = 'disabled'
        for item in elements:
            item["state"] = "normal" if self.auth_flag else 'disabled'


class AboutFrame(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.createPage()

    def createPage(self):
        tk.Label(self, text='关于界面', font=("微软雅黑", 12)).pack()
        tk.Label(self, text='FileManager', font=("微软雅黑", 20), fg="green").pack()
        ttk.Label(self, text='VERSION:  3.38.0.0').pack()
        link = tk.Label(self, text="GitHub:  https://github.com/codecyou/FileManager", fg="blue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/codecyou/FileManager"))
        ttk.Label(self, text='这是一个多功能的小程序，').pack()
        tk.Label(self, text='功能：', font=("微软雅黑", 18)).pack()
        ttk.Label(self, text='查找重复文件、文件同步备份、搜索文件、计算文件hash值、比对文本内容').pack()
        ttk.Label(self, text='清除空文件夹、拷贝目录层次结构、批量重命名、时间戳转换、修改文件时间戳').pack()
        ttk.Label(self, text='提取视频帧图像、计算图片相似度、查找相似视频、以图搜图、以视频搜索相似视频').pack()
        ttk.Label(self, text='获取图片文件EXIF信息(GPS信息、拍摄信息、设备信息)').pack()
        ttk.Label(self, text='获取视频元数据(时长、拍摄时间、设备、位置信息)、导出媒体文件信息').pack()
        ttk.Label(self, text='识别文件真实数据类型、图片格式转换、WEBP转JPG、HEIC转JPG').pack()
        ttk.Label(self, text='视频裁剪、提取音频、音频格式转换、文本编码转换、文本CRLF和LF转换').pack()
