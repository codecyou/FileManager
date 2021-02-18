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
import traceback
import time

from conf import settings

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
from core import backup, Mybackup, file_dir_syn, hash_core, search, Mytools, compare_file, get_img_thread, \
    image_similarity_thread, video_similarity, logger, search_image, search_video

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


def check_path_arg(*pargs, **pkwargs):  # 这是一个装饰器   失败了！！ 变成装饰器的时候传的参数就要定下来而不是后面在确定
    """
    装饰器，用于检测输入的路径是否存在
    :param pargs: 给装饰器传的参数
    :param pkwargs: 给装饰器传的参数
    :return:
    """

    def check_path(func):
        def wrapped_func(self, *args, **kwargs):
            create_flag = False
            if len(pkwargs):  # 检查是否存在"create_flag"， True 当目录路径不存在时，创建目录 False 不创建
                if "create_flag" in kwargs:
                    create_flag = kwargs["create_flag"]
            if len(pargs):
                for item in args:
                    path_ = Mytools.check_path(item, create_flag)
                    if path_ is None:
                        mBox.showerror("路径不存在！", "%s  不存在！请检查！" % item)
                        return
            return func(self, *args, **kwargs)

        return wrapped_func

    return check_path


def check_path_flag(flag=False):  # 这是一个装饰器   失败了！！ 变成装饰器的时候传的参数就要定下来而不是后面在确定
    """
    装饰器，用于检测输入的路径是否存在
    :return:
    """

    def check_path(func):
        def wrapped_func(self, *args, **kwargs):
            if flag is False:
                mBox.showerror("您输入的路径有误！", "您输入的路径有误！请检查")
                return
            return func(self, *args, **kwargs)

        return wrapped_func

    return check_path


def check_path(pathObj, create_flag=False):
    """检查输入的路径是否合法"""
    flag = False
    if pathObj.get():  # 有输入内容
        dir_path = pathObj.get().strip()  # 防止出现输入' '
        if os.path.exists(dir_path):  # 检查路径是否存在
            # 当输入'/home/'时获取文件名就是''，所以加处理
            dir_path = os.path.abspath(dir_path)
            pathObj.set(dir_path)
            flag = True
        elif create_flag is True:
            # print("输入目录不存在！已为您新建该目录！")
            os.makedirs(dir_path)
            dir_path = os.path.abspath(dir_path)
            pathObj.set(dir_path)
            flag = True
    return flag


def show_path_error():
    mBox.showwarning("输入路径有误！", "输入路径不存在，请检查！")


def check_frameNum(numObj):
    """检查输入的帧数是否合法"""
    flag = False
    if numObj.get():  # 有输入内容
        num = str(numObj.get()).strip()  # 防止出现输入' '
        try:
            num = int(num)
        except Exception:
            return False
        if num >= 0:
            numObj.set(num)
            flag = True
    return flag


def show_frameNum_error():
    mBox.showwarning("输入的帧数有误！", "输入的帧数数据格式有误！\n帧数应为正整数！")


def check_threNum(numObj):
    """检查输入的相似度阈值是否合法"""
    flag = False
    if numObj.get():  # 有输入内容
        num = str(numObj.get()).strip()  # 防止出现输入' '
        try:
            num = float(num)
        except Exception:
            return False
        if 0 <= num <= 1:
            numObj.set(num)
            flag = True
    return flag


def show_threNum_error():
    mBox.showwarning("输入的相似度阈值有误！", "输入的相似度阈值格式有误！\n相似度阈值应为0~1之间的小数！")


def log_error(func):
    """装饰器用于装饰各个模块页面的run方法来捕获异常"""

    def wrapped_func(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error_logger(traceback.format_exc())
            mBox.showerror("错误！", "程序运行出错！详情请查看日志")

    return wrapped_func


class ExportFrame(tk.Frame):  # 继承Frame类
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.dir_path = tk.StringVar()
        self.record_path = None  # 导出的记录文件路径
        self.createPage()

    def createPage(self):
        tk.Label(self, text='导出文件信息', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, stick=tk.W, pady=10)
        ttk.Label(self, text='要导出文件信息的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dir_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dir_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath).grid(row=1, column=3)
        ttk.Label(self, text='结果进度: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Button(self, text='导出', command=self.run).grid(row=2, column=3, stick=tk.E, pady=10)

        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)
        self.button_show = ttk.Button(self, text='查看导出文件', command=self.showResult, state=tk.DISABLED)
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

    # @check_path_arg(self)   失败了！！！
    @log_error
    def deal_export_file(self, dir_path):
        # print(self.dir_path.get())
        # self.t.insert('end', '\n正在导出%s目录下的文件信息...\n' % self.dir_path.get())
        # msg = handler.deal_export_file_info(self.dir_path.get())
        # self.t.insert('end', msg + '\n')
        # self.scr.delete(1.0, 'end')
        self.scr.insert('end', '\n正在导出%s目录下的文件信息...\n' % self.dir_path.get())
        self.record_path, count = Mytools.export_file_info(self.dir_path.get())
        msg = "导出%s个文件信息到%s完成！" % (count, self.record_path)
        logger.operate_logger("从%s 下导出%s个文件信息到%s" % (dir_path, count, self.record_path))
        self.scr.insert('end', msg + '\n')
        mBox.showinfo('导出文件信息完成！', msg)
        self.button_show.config(state=tk.NORMAL)

    def run(self):
        # print(self.dir_path.get())
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.dir_path.get())
        # print(dir_path)
        if dir_path:
            t = threading.Thread(target=self.deal_export_file, args=(dir_path,))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dir_path.get())
        # t = threading.Thread(target=self.deal_export_file, args=(self.dir_path.get(),))
        # t.start()


class QuerySameFrame(tk.Frame):  # 继承Frame类
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.mode_dict = {
            "同名文件": "name",
            "相同大小文件": "size",
            "同名且大小相同文件": "name_size",
            "大小相同且修改时间相同文件": "size_mtime",
            "同名且大小相同且修改时间相同文件": "name_size_mtime"
        }
        self.optionDict = {"拷贝": "copy", "剪切": "move"}
        self.mode = tk.StringVar()
        self.option = tk.StringVar()
        self.search_path = tk.StringVar()
        self.save_path = tk.StringVar()  # 重复文件导出目录路径
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.search_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.save_path.set(path_)

    def createPage(self):
        tk.Label(self, text='查询相同文件界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='要查重的路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.search_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                             column=1,
                                                                                                             columnspan=3,
                                                                                                             stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='要导出的路径: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.save_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.save_path, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                 column=1,
                                                                                                                 columnspan=3,
                                                                                                                 stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        modeChosen = ttk.Combobox(self, width=40, textvariable=self.mode)
        modeChosen['values'] = list(self.mode_dict.keys())
        modeChosen.grid(row=4, column=1, sticky=tk.W)
        modeChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        modeChosen.config(state='readonly')  # 设为只读模式

        col = 2
        for item in self.optionDict:
            ttk.Radiobutton(self, text=item, variable=self.option, value=item).grid(column=col, row=4, sticky=tk.W)
            col += 1
        self.option.set("拷贝")  # 设置默认值

        ttk.Button(self, text="执行", command=self.run).grid(row=5, column=4)
        ttk.Label(self, text='结果进度: ').grid(row=6, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=6, column=1, columnspan=5, stick=tk.EW)
        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)

        ttk.Button(self, text="查看结果", command=self.showFiles).grid(row=8, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.save_path.get():
            webbrowser.open(self.save_path.get())

    @log_error
    def deal_query_same(self, search_dir, save_dir):
        # search_dir = self.search_path.get()
        # save_dir = self.save_path.get()
        search_mode = self.mode_dict[self.mode.get()]
        deal_mode = self.optionDict[self.option.get()]
        self.scr.insert("end", "正在遍历文件目录，请稍候！\n")
        self.pb1["value"] = 1  # 模拟遍历完成
        file_dict, count = search.find_same(search_dir, search_mode)
        if len(file_dict):  # 如果有相同文件再进行后续动作
            self.scr.insert("end", "检索%s\n  共发现%s %s个！\n" % (search_dir, search_mode, len(file_dict)))
            self.pb1["value"] = 2  # 比对完成
            self.scr.insert("end", "正在将%s 由%s %s到%s！\n" % (search_mode, search_dir, deal_mode, save_dir))
            record_path = Mytools.move_or_copy_file(file_dict, search_dir, save_dir, deal_mode, name_simple=True)
            msg = "%s  中发现%s个%s的文件\t已%s到%s\n新旧文件名记录到%s" % (
            search_dir, count, self.mode.get(), self.option.get(), save_dir, record_path)
        else:
            msg = "%s  中未发现%s的文件！" % (search_dir, self.mode.get())
        self.scr.insert("end", "%s\n" % msg)
        self.pb1["value"] = 3  # 操作文件完成
        mBox.showinfo('查找相同文件完成！', msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 3  # 总项目数 1/3为遍历文件完成， 2/3 为比对完成， 3/3为操作文件完成
        search_dir = Mytools.check_path(self.search_path.get())
        save_dir = Mytools.check_path(self.save_path.get(), True)
        if search_dir and save_dir:
            t = threading.Thread(target=self.deal_query_same, args=(search_dir, save_dir))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.search_path.get())
            return


class SynFrame(tk.Frame):  # 继承Frame类
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.mode = tk.StringVar()
        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
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
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.src_path.get())
            return

    def createPage(self):
        # print(self.mode.get())
        tk.Label(self, text='文件同步界面', font=('Arial', 12), width=30, height=2).grid(row=0, column=1, pady=10,
                                                                                   columnspan=3)
        ttk.Label(self, text='源目录路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.src_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.src_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          columnspan=3,
                                                                                                          stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='备份端路径: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dst_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dst_path, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        col = 1
        for item in self.modeDict:
            ttk.Radiobutton(self, text=item, variable=self.mode, value=item, command=self.selectOption).grid(column=col,
                                                                                                             row=4)
            col += 1
        self.mode.set("基于filecmp模块")

        ttk.Button(self, text="比对差异", command=self.findDiffRun).grid(row=4, column=4)

        # 展示结果
        ttk.Label(self, text='比对结果: ').grid(row=6, stick=tk.W, pady=10)
        # self.pbrun = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="indeterminate")  # 用于展示程序运行中的状态
        # self.pbrun.grid(row=6, column=1, columnspan=5, stick=tk.EW)
        scrolW = 40
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)

        # 布局操作选项控件
        # Creating all three Radiobutton widgets within one loop
        ttk.Label(self, text='请选择操作: ').grid(row=8, column=0, pady=10)
        self.optionChosen = ttk.Combobox(self, width=20, textvariable=self.option)
        if self.mode.get():
            self.optionChosen['values'] = self.optionDict[self.mode.get()]
        else:
            self.optionChosen['values'] = self.optionDict["基于filecmp模块"]
        self.optionChosen.grid(column=2, row=8, pady=10)
        self.optionChosen.current(0)  # 设置初始显示值，值为元组['values']的下标
        self.optionChosen.config(state='readonly')  # 设为只读模式

        ttk.Button(self, text="执行", command=self.run).grid(row=8, column=4)
        # ttk.Label(self, text='完成进度: ').grid(row=9, stick=tk.W, pady=10)
        # self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        # self.pb1.grid(row=9, column=1, columnspan=5, stick=tk.EW)
        ttk.Label(self, text='程序运行状态: ').grid(row=10, stick=tk.W, pady=10)
        self.exeStateLabel = ttk.Label(self, text='')  # 用于显示程序执行任务状态
        self.exeStateLabel.grid(row=10, column=1, columnspan=2, stick=tk.W, pady=10)
        self.proStateLabel = ttk.Label(self, text='')  # 用于显示程序总运行状态
        self.proStateLabel.grid(row=10, column=4, stick=tk.W, pady=10)


class RestoreFrame(tk.Frame):  # 继承Frame类
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.dir_path = tk.StringVar()
        self.createPage()

    def createPage(self):
        tk.Label(self, text='还原文件界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, stick=tk.W, pady=10)
        ttk.Label(self, text='new_old_record文件路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dir_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dir_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath).grid(row=1, column=3)
        ttk.Label(self, text='结果进度: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Button(self, text='还原', command=self.run).grid(row=2, column=3, stick=tk.E, pady=10)

        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)

    def selectPath(self):
        path_ = askopenfilename()
        self.dir_path.set(path_)

    @log_error
    def deal_restore(self, dir_path):
        print(self.dir_path.get())
        # self.scr.delete(1.0, 'end')
        self.scr.insert('end', '\n正在还原%s记录中的文件...\n' % dir_path)
        restore_path, count = Mytools.restore_file_by_record(dir_path)
        msg = "还原了%s个文件，还原文件信息记录到%s" % (count, restore_path)
        self.scr.insert('end', msg + '\n')
        mBox.showinfo('还原文件完成！', msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        dir_path = Mytools.check_path(self.dir_path.get())
        if dir_path:
            t = threading.Thread(target=self.deal_restore, args=(dir_path,))
            t.start()
        else:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dir_path.get())
            return


class ClearEmptyDirFrame(tk.Frame):  # 继承Frame类
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.dir_path = tk.StringVar()
        self.createPage()

    def createPage(self):
        tk.Label(self, text='清空空文件夹界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, stick=tk.W,
                                                                                     pady=10)
        ttk.Label(self, text='要清空空文件夹的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dir_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dir_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath).grid(row=1, column=3)
        ttk.Label(self, text='结果进度: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Button(self, text='清空', command=self.run).grid(row=2, column=3, stick=tk.E, pady=10)

        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=7, sticky='WE', columnspan=5)

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


class QueryFrame(tk.Frame):  # 继承Frame类
    """搜索文件"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
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
        print(self.search_mode.get())
        tk.Label(self, text='搜索文件界面', font=('Arial', 12), width=30, height=2).grid(row=0, column=1, pady=10,
                                                                                   columnspan=3)
        ttk.Label(self, text='要搜索的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.src_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.src_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          columnspan=3,
                                                                                                          stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="文件名", variable=self.search_mode, value="filename").grid(column=1, row=4, stick=tk.W)
        ttk.Radiobutton(self, text="文件大小", variable=self.search_mode, value="filesize").grid(column=2, row=4,
                                                                                             stick=tk.W)
        self.search_mode.set("filename")
        ttk.Radiobutton(self, text="精确搜索", variable=self.search_option, value=False).grid(column=1, row=5, stick=tk.W)
        ttk.Radiobutton(self, text="正则搜索/条件搜索", variable=self.search_option, value=True).grid(column=2, row=5,
                                                                                              stick=tk.W)
        self.search_option.set(False)
        ttk.Button(self, text="使用说明", command=self.showTip).grid(column=3, row=5, stick=tk.W)

        ttk.Label(self, text='搜索语句: ').grid(row=6, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_str, width=30).grid(row=6, column=1, stick=tk.W)

        ttk.Button(self, text="搜索", command=self.do_search).grid(row=6, column=4)

        # 展示结果
        ttk.Label(self, text='搜索结果: ').grid(row=7, stick=tk.W, pady=10)
        scrolW = 30
        scrolH = 20
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=8, sticky='WE', columnspan=5)

        ttk.Label(self, text='导出方式: ').grid(row=10, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="复制", variable=self.deal_mode, value="copy").grid(column=1, row=10, stick=tk.W)
        ttk.Radiobutton(self, text="剪切", variable=self.deal_mode, value="move").grid(column=2, row=10, stick=tk.W)
        self.deal_mode.set("copy")

        ttk.Label(self, text='是否原样导出？: ').grid(row=11, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="导出到单级目录并附带目录描述", variable=self.rename_flag, value=True).grid(column=1, row=11,
                                                                                                 stick=tk.W)
        ttk.Radiobutton(self, text="原样导出", variable=self.rename_flag, value=False).grid(column=2, row=11, stick=tk.W)
        self.rename_flag.set(True)
        ttk.Label(self, text='要导出的路径: ').grid(row=12, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dst_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dst_path, True), invalidcommand=show_path_error).grid(row=12,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=12, column=4)

        ttk.Button(self, text="导出", command=self.run).grid(row=13, column=4)

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
        if save_path is None:
            mBox.showerror("路径不存在！", "%s  不存在！请检查！" % self.dst_path.get())
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


class CopyDirTreeFrame(tk.Frame):
    """拷贝或导出目录结构"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.mode = tk.StringVar()
        self.option = tk.StringVar()
        self.search_path = tk.StringVar()
        self.save_path = tk.StringVar()
        self.path_ok_flag = True  # 用于标记用户输入的路径是否经过安全验证 True 路径存在 False 路径不存在
        self.createPage()

    def selectPath1(self):
        if self.option.get() == 'fromfile':
            path_ = askopenfilename()
        else:
            path_ = askdirectory()
        self.search_path.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.save_path.set(path_)

    def selectOption(self):
        # 从文件信息拷贝目录结构还是 从目录拷贝目录结构
        self.scr.delete(1.0, "end")  # 每次切换选项时都进行结果显示区域清屏

    def createPage(self):
        tk.Label(self, text='拷贝目录结构界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='要拷贝目录结构的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.search_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                             column=1,
                                                                                                             columnspan=2,
                                                                                                             stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=3)
        ttk.Label(self, text='要创建目录结构的目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.save_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.save_path, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                 column=1,
                                                                                                                 columnspan=2,
                                                                                                                 stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=3)

        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="从目录拷贝", variable=self.option, value="fromdir", command=self.selectOption).grid(
            column=1, row=4, sticky=tk.W)
        ttk.Radiobutton(self, text="从文件拷贝", variable=self.option, value="fromfile", command=self.selectOption).grid(
            column=2, row=4, sticky=tk.W)
        self.option.set("fromdir")  # 设置单选默认值
        ttk.Button(self, text="拷贝目录结构", command=self.copyDirTree).grid(row=5, column=2)
        ttk.Button(self, text="导出目录结构", command=self.exportDirTree).grid(row=5, column=3)
        # ttk.Label(self, text='完成进度: ').grid(row=6, stick=tk.W, pady=10)
        # self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        # self.pb1.grid(row=6, column=1, columnspan=5, stick=tk.EW)
        # 展示结果
        ttk.Label(self, text='目录结构信息: ').grid(row=7, stick=tk.W, pady=10)
        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=8, sticky='WE', columnspan=5)

    @log_error
    def copyDirTree(self):
        self.scr.delete(1.0, "end")
        self.scr.insert("end", '正在拷贝目录结构，请稍候...\n')
        msg, dir_str_list = Mytools.make_dirs(self.search_path.get(), self.save_path.get())
        self.scr.insert("end", '拷贝目录结构完成，目录结构如下:\n')
        self.scr.insert("end", '\n'.join(dir_str_list))
        mBox.showinfo('完成！', msg)

    @log_error
    def exportDirTree(self):
        self.scr.delete(1.0, "end")
        self.scr.insert("end", '正在导出目录结构信息，请稍候...\n')
        search_path = self.search_path.get()
        record_path, dir_list = Mytools.export_dirs(search_path)
        if len(dir_list):
            self.scr.insert("end", '导出目录结构信息完成，目录结构如下:\n')
            for item in dir_list:
                self.scr.insert("end", "%s\n" % item)
            mBox.showinfo('完成！', "导出%s 的目录结构信息到%s 完成！" % (search_path, record_path))
        else:
            if record_path is None:
                self.scr.insert("end", "您输入的是文件，暂不支持从文件导出目录结构到文件！\n若需备份该文件，您可直接复制该文件！\n")
                mBox.showwarning("warning！", "您输入的是文件，暂不支持从文件导出目录结构到文件！\n若需备份该文件，您可直接复制该文件！")
                return
            self.scr.insert("end", "%s  下并无子目录结构！" % search_path)
            showinfo("完成", "%s  下并无子目录结构！" % search_path)


class DelFileFrame(tk.Frame):
    """删除文件"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.mode = tk.StringVar()
        self.dir_path = tk.StringVar()  # 源文件路径，即要执行删除操作的目录路径
        self.eg_path = tk.StringVar()  # 样本路径
        self.record_path = tk.StringVar()  # 记录文件的路径
        self.newdir_path = tk.StringVar()  # 之前导出的，并且已经审核后的文件的目录路径
        self.save_flag = tk.StringVar()  # 标记文件夹中的文件是要保留还是要删除，True保留
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
        tk.Label(self, text='删除文件界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=0, columnspan=5,
                                                                                   pady=10)
        ttk.Label(self, text='要进行文件删除的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dir_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dir_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          columnspan=3,
                                                                                                          stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='样本路径: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.eg_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.eg_path), invalidcommand=show_path_error).grid(row=2,
                                                                                                         column=1,
                                                                                                         columnspan=3,
                                                                                                         stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="根据样本目录", variable=self.mode, value="fromdir").grid(column=1, row=4, sticky=tk.EW)
        ttk.Radiobutton(self, text="根据导出的文件信息", variable=self.mode, value="frominfo").grid(column=2, row=4,
                                                                                           sticky=tk.EW)
        ttk.Radiobutton(self, text="根据new_old_record", variable=self.mode, value="fromrecord").grid(column=3, row=4,
                                                                                                    sticky=tk.EW)
        self.mode.set("fromdir")  # 设置默认值

        ttk.Button(self, text="执行删除", command=self.delFile).grid(row=5, column=4)

        tk.Label(self, text='获取要删除的文件new_old_record界面', font=('Arial', 12), width=50, height=2).grid(row=7, column=0,
                                                                                                     columnspan=5,
                                                                                                     pady=10)
        ttk.Label(self, text="获取要删除的文件记录(过滤new_old_record,获取要删除的文件的new_old_record): ").grid(row=8, columnspan=3,
                                                                                            stick=tk.W, pady=10)
        ttk.Label(self, text="已审核后的目录路径").grid(row=9, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.newdir_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.newdir_path), invalidcommand=show_path_error).grid(row=9,
                                                                                                             column=1,
                                                                                                             columnspan=3,
                                                                                                             stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath3).grid(row=9, column=4)
        ttk.Label(self, text='new_old_record路径：').grid(row=10, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.record_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.record_path), invalidcommand=show_path_error).grid(row=10,
                                                                                                             column=1,
                                                                                                             columnspan=3,
                                                                                                             stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath4).grid(row=10, column=4)

        ttk.Label(self, text='目录中的文件是否要保留: ').grid(row=11, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="保留", variable=self.save_flag, value=True).grid(column=1, row=11, sticky=tk.E)
        ttk.Radiobutton(self, text="删除", variable=self.save_flag, value=False).grid(column=2, row=11, sticky=tk.E)
        self.save_flag.set(True)  # 设置默认值True 保留
        ttk.Button(self, text="获取记录", command=self.getDelRecord).grid(row=12, column=4)
        ttk.Label(self, text='del_record: ').grid(row=13, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.del_record, width=80).grid(row=13, column=1, columnspan=3, stick=tk.EW)

    @log_error
    def delFile(self):
        """用于执行删除文件操作"""
        mode = self.mode.get()  # 获取删除模式
        dir_path = self.dir_path.get()
        eg_path = self.eg_path.get()
        if mode == "fromrecord":
            del_record_path, del_count = Mytools.remove_file_by_record(eg_path, safe_flag=True)
        else:
            del_record_path, del_count = Mytools.remove_file_by_info(dir_path, eg_path, safe_flag=True)
        mBox.showinfo("删除文件完成！", "删除了%s个文件！被删除文件信息记录到%s" % (del_count, del_record_path))

    @log_error
    def getDelRecord(self):
        """用于获取要删除的文件的new_old_record"""
        dir_path = self.dir_path.get()
        record_path = self.record_path.get()
        save_flag = self.save_flag
        del_record_path = Mytools.get_del_record(record_path, dir_path, save_flag)
        mBox.showinfo("获取要del_record记录完成！", "del_record路径为： %s" % del_record_path)


class CompareTxtFrame(tk.Frame):  # 继承Frame类
    """比较文本文件内容差异"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
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
        tk.Label(self, text='对比文本文件内容差异界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='源目录的路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.src_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.src_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          columnspan=3,
                                                                                                          stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='目标目录路径: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dst_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dst_path, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.E)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="对比目录", variable=self.mode, value=True).grid(column=1, row=4, sticky=tk.E)
        ttk.Radiobutton(self, text="对比文件", variable=self.mode, value=False).grid(column=2, row=4, sticky=tk.E)
        self.mode.set(True)  # 设置单选默认值
        ttk.Button(self, text="执行", command=self.run).grid(row=5, column=4)

        # 展示结果
        ttk.Label(self, text='比对结果: ').grid(row=7, stick=tk.W, pady=10)
        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=8, sticky='WE', columnspan=5)
        ttk.Button(self, text="查看详情", command=self.showDiff).grid(row=10, column=4, pady=10)

    @log_error
    def showDiff(self):
        """用于查看文件差异"""
        if self.record_dir_path:
            webbrowser.open(self.record_dir_path)

    def do_compare(self):
        src_path = self.src_path.get()
        dst_path = self.dst_path.get()
        file_list1 = Mytools.get_pathlist(src_path)
        file_list2 = Mytools.get_pathlist(dst_path)
        # print(file_list1, file_list2)
        compare_list = []  # 要比对的文件路径
        # 获取要比对的文件列表
        for item in file_list1:
            if item.replace(src_path, dst_path) in file_list2:
                compare_list.append(item)
        self.record_dir_path, diff_files = compare_file.compare_file_list(src_path, dst_path, compare_list)
        if len(diff_files):
            self.scr.insert("end", "总共有%s个文件文本内容发生变化！\n详情如下：\n" % len(diff_files))
        else:
            self.scr.insert("end", "未发现文本内容有变化的同名文件！\n")
        for item in diff_files:
            self.scr.insert("end", "%s\n" % item)
        mBox.showinfo("完成！", "比对完成！总共有%s个文件文本内容发生变化！" % len(diff_files))

    def run(self):
        self.scr.delete(1.0, "end")
        self.scr.insert("end", "正在比对%s 与%s 下的文本文件内容...\n" % (self.src_path.get(), self.dst_path.get()))
        t = threading.Thread(target=self.do_compare)
        t.start()


class CalHashFrame(tk.Frame):  # 继承Frame类
    """计算文件hash值"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.dir_path = tk.StringVar()
        self.mode = tk.BooleanVar()  # True 对比目录 False 对比文件
        self.upper = tk.BooleanVar()  # True 大写 False 小写
        self.CODE_TYPE = settings.SYSTEM_CODE_TYPE  # 系统的编码格式，用于处理后面拖拽文件，文件名解码
        self.vars = []
        self.result = {}
        self.algors = ['sha1', 'sha256', 'md5', "sha224", "sha512", "sha384"]  # 算法
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
            dir_path = item.decode(self.CODE_TYPE)
            path_list.append(dir_path)
        t = threading.Thread(target=self.cal_hash, args=(path_list,))
        t.start()

    def selectPath(self):
        if self.mode.get():
            path_ = askdirectory()
        else:
            path_ = askopenfilename()
        self.dir_path.set(path_)

    def run(self):
        t = threading.Thread(target=self.cal_hash, args=([self.dir_path.get(), ],))
        t.start()

    def toupper(self):
        # content = self.scr.get(1.0, "end")
        # self.scr.delete(1.0, "end")
        # self.scr.insert("end", content.upper())
        self.scr.delete(1.0, "end")
        for file in self.result:
            self.scr.insert("end", '%s:\t%s\n' % ("File", file))
            for item in self.result[file]:
                info_str = "%s:\t%s" % (item, self.result[file][item])
                self.scr.insert("end", '%s\n' % info_str.upper())
            self.scr.insert("end", "\n")

    def tolower(self):
        self.scr.delete(1.0, "end")
        for file in self.result:
            self.scr.insert("end", '%s:\t%s\n' % ("File", file))
            for item in self.result[file]:
                info_str = "%s:\t%s" % (item, self.result[file][item])
                self.scr.insert("end", '%s\n' % info_str.lower())
            self.scr.insert("end", "\n")

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

    def createPage(self):
        tk.Label(self, text='计算hash界面', font=('Arial', 12), width=50, height=2).grid(row=0, columnspan=8, stick=tk.EW,
                                                                                     pady=10)
        ttk.Label(self, text='文件路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dir_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dir_path), invalidcommand=show_path_error).grid(row=1,
                                                                                                          column=1,
                                                                                                          columnspan=6,
                                                                                                          stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath).grid(row=1, column=7)

        ttk.Label(self, text='浏览模式: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="目录", variable=self.mode, value=True).grid(column=1, row=2, sticky=tk.W)
        ttk.Radiobutton(self, text="文件", variable=self.mode, value=False).grid(column=2, row=2, sticky=tk.W)
        self.mode.set(True)

        ttk.Label(self, text='算法: ').grid(row=3, stick=tk.W)
        col = 1
        row = 3
        for index, item in enumerate(self.vars):
            value = self.algors[index]
            if index < 3:
                item.set(value)
            else:
                item.set('')
            cb = ttk.Checkbutton(self, text=value, variable=item, onvalue=value, offvalue='')
            cb.grid(column=col, row=row, stick=tk.W, ipadx=5)
            col += 1

        ttk.Radiobutton(self, text="大写", variable=self.upper, value=True, command=self.toupper).grid(row=2, column=5,
                                                                                                     sticky=tk.EW)
        ttk.Radiobutton(self, text="小写", variable=self.upper, value=False, command=self.tolower).grid(row=2, column=6,
                                                                                                      sticky=tk.W)
        self.upper.set(False)
        ttk.Button(self, text='清除', command=self.clear).grid(row=9, column=5, stick=tk.E, pady=10)
        ttk.Button(self, text='保存', command=self.writehash).grid(row=9, column=6, stick=tk.EW, pady=10)
        ttk.Button(self, text='计算', command=self.run).grid(row=9, column=7, stick=tk.E, pady=10)
        ttk.Label(self, text='进度: ').grid(row=10, stick=tk.W)
        ttk.Label(self, text='完成: ').grid(row=11, stick=tk.W, pady=5)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=10, column=1, columnspan=7, stick=tk.EW)
        self.pb2 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb2.grid(row=11, column=1, columnspan=7, stick=tk.EW, pady=5)

        scrolW = 80
        scrolH = 30
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=12, sticky='WE', columnspan=8)

        windnd.hook_dropfiles(self.root, func=self.dragged_files)


class GetImgFrame(tk.Frame):
    """提取视频帧图像"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.frameNum = tk.IntVar()
        self.continue_flag = tk.BooleanVar()
        self.video_dir = tk.StringVar()
        self.img_dir = tk.StringVar()
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.video_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.img_dir.set(path_)

    def createPage(self):
        tk.Label(self, text='提取视频帧图像界面', font=('Arial', 12), width=50, height=2).grid(row=0, columnspan=5, sticky=tk.EW,
                                                                                      pady=10)
        ttk.Label(self, text='源视频目录路径: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.video_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.video_dir), invalidcommand=show_path_error).grid(row=1,
                                                                                                           column=1,
                                                                                                           columnspan=4,
                                                                                                           stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=5)
        ttk.Label(self, text='图片保存路径: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.img_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.img_dir, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                               column=1,
                                                                                                               columnspan=4,
                                                                                                               stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=5)

        ttk.Label(self, text='模式选择: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Label(self, text='提取第几帧图像: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.frameNum, width=10, validate="focusout",
                  validatecommand=lambda: check_frameNum(self.frameNum), invalidcommand=show_frameNum_error).grid(row=4,
                                                                                                                  column=1,
                                                                                                                  stick=tk.W)
        self.frameNum.set(90)  # 设置默认值为90
        ttk.Label(self, text='是否继续上次进度: ').grid(row=4, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="是", variable=self.continue_flag, value=True).grid(column=3, row=4, sticky=tk.W)
        ttk.Radiobutton(self, text="否", variable=self.continue_flag, value=False).grid(column=4, row=4, sticky=tk.W)
        self.continue_flag.set(False)  # 设置默认选中否

        ttk.Button(self, text="执行", command=self.run).grid(row=5, column=5)
        ttk.Label(self, text='完成进度: ').grid(row=6, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=6, column=1, columnspan=5, stick=tk.EW)
        scrolW = 80
        scrolH = 28
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=8, sticky='WE', columnspan=6)
        ttk.Button(self, text="查看提取完成帧图像", command=self.showFiles).grid(row=10, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.img_dir.get():
            webbrowser.open(self.img_dir.get())

    @log_error
    def deal_get_img(self):
        msg = get_img_thread.run(self, self.video_dir.get(), self.img_dir.get(), self.frameNum.get(),
                                 self.continue_flag.get())
        mBox.showinfo('完成！', msg)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        print(self.video_dir.get(), self.img_dir.get(), self.frameNum.get(), self.continue_flag.get())
        # msg = handler.deal_get_img(self.video_dir.get(), self.img_dir.get(), self.frameNum.get(), self.continue_flag.get())
        # msg = get_img_multiprocess.run(self.video_dir.get(), self.img_dir.get(), self.frameNum.get(), self.continue_flag.get())
        t = threading.Thread(target=self.deal_get_img)
        t.start()


class CalImgSimFrame(tk.Frame):
    """计算图片相似度"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.search_dir = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.search_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.save_dir.set(path_)

    def createPage(self):
        tk.Label(self, text='计算图片相似度界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='源图片目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.search_dir), invalidcommand=show_path_error).grid(row=1,
                                                                                                            column=1,
                                                                                                            columnspan=3,
                                                                                                            stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='相似图片导出目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.save_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.save_dir, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Label(self, text='相似度阈值(默认0.98): ').grid(row=4, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.threshold, width=10, validate="focusout",
                  validatecommand=lambda: check_threNum(self.threshold), invalidcommand=show_threNum_error).grid(row=4,
                                                                                                                 column=1,
                                                                                                                 stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self, text='导出方式: ').grid(row=4, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="复制", variable=self.option, value="copy").grid(column=3, row=4, sticky=tk.W)
        ttk.Radiobutton(self, text="剪切", variable=self.option, value="move").grid(column=4, row=4, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否

        ttk.Button(self, text="执行", command=self.run).grid(row=5, column=4)
        ttk.Label(self, text='完成进度: ').grid(row=6, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=6, column=1, columnspan=5, stick=tk.EW)
        scrolW = 80
        scrolH = 28
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=8, sticky='WE', columnspan=6)
        ttk.Button(self, text="查看相似图片", command=self.showFiles).grid(row=10, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.save_dir.get():
            webbrowser.open(self.save_dir.get())

    @log_error
    def deal_image_similarity(self):
        print(self.search_dir.get(), self.save_dir.get(), self.threshold.get(), self.option.get())
        # msg = handler.deal_image_similarity(self.search_dir.get(), self.save_dir.get(), self.threshold.get(), self.option.get())
        record, msg = image_similarity_thread.run(self, self.search_dir.get(), self.save_dir.get(),
                                                  self.threshold.get(), self.option.get())
        mBox.showinfo('完成！', msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        t = threading.Thread(target=self.deal_image_similarity)
        t.start()


class CalVideoSimFrame(tk.Frame):
    """计算视频相似度"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.frameNum = tk.IntVar()
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.search_dir = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.createPage()

    def selectPath1(self):
        path_ = askdirectory()
        self.search_dir.set(path_)

    def selectPath2(self):
        path_ = askdirectory()
        self.save_dir.set(path_)

    def createPage(self):
        tk.Label(self, text='查找相似视频界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='要查找视频相似的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.search_dir), invalidcommand=show_path_error).grid(row=1,
                                                                                                            column=1,
                                                                                                            columnspan=3,
                                                                                                            stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='相似视频导出目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.save_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.save_dir, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)

        ttk.Label(self, text='模式选择: ').grid(row=3, column=0, stick=tk.W, pady=10)
        ttk.Label(self, text='比对第几帧图像: ').grid(row=4, column=0, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.frameNum, width=10, validate="focusout",
                  validatecommand=lambda: check_frameNum(self.frameNum), invalidcommand=show_frameNum_error).grid(row=4,
                                                                                                                  column=1,
                                                                                                                  stick=tk.W)
        self.frameNum.set(90)  # 设置默认值为90
        ttk.Label(self, text='是否继续上次进度: ').grid(row=4, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="是", variable=self.continue_flag, value=True).grid(column=3, row=4, sticky=tk.W)
        ttk.Radiobutton(self, text="否", variable=self.continue_flag, value=False).grid(column=4, row=4, sticky=tk.W)
        self.continue_flag.set(False)  # 设置默认选中否

        ttk.Label(self, text='相似度阈值(默认0.98): ').grid(row=5, column=0, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.threshold, width=10, validate="focusout",
                  validatecommand=lambda: check_threNum(self.threshold), invalidcommand=show_threNum_error).grid(row=5,
                                                                                                                 column=1,
                                                                                                                 stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self, text='导出方式: ').grid(row=5, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="复制", variable=self.option, value="copy").grid(column=3, row=5, sticky=tk.W)
        ttk.Radiobutton(self, text="剪切", variable=self.option, value="move").grid(column=4, row=5, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否
        ttk.Button(self, text="执行", command=self.run).grid(row=6, column=4)
        ttk.Label(self, text='完成进度: ').grid(row=7, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=7, column=1, columnspan=5, stick=tk.EW)
        scrolW = 80
        scrolH = 25
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=8, sticky='WE', columnspan=6)
        ttk.Button(self, text="查看相似视频", command=self.showFiles).grid(row=10, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.save_dir.get():
            webbrowser.open(self.save_dir.get())

    @log_error
    def deal_video_similarity(self, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold, deal_video_mode):
        msg = video_similarity.run(self, src_dir_path, dst_dir_path, frame_num, continue_flag, threshold,
                                   deal_video_mode)
        mBox.showinfo("查找相似视频完成!", msg)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        print(self.search_dir.get(), self.save_dir.get(), self.frameNum.get(), self.continue_flag.get(),
              self.threshold.get(), self.option.get())
        args = (
        self.search_dir.get(), self.save_dir.get(), self.frameNum.get(), self.continue_flag.get(), self.threshold.get(),
        self.option.get())
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.start()


class SearchImgFrame(tk.Frame):
    """以图搜图"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.search_dir = tk.StringVar()
        self.save_dir = tk.StringVar()
        self.dst_path = tk.StringVar()  # 原有图片路径或者phash json
        self.mode = tk.BooleanVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
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
        self.dst_path.set(path_)

    def createPage(self):
        tk.Label(self, text='以图搜图界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='要搜索的图片的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.search_dir), invalidcommand=show_path_error).grid(row=1,
                                                                                                            column=1,
                                                                                                            columnspan=3,
                                                                                                            stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='相似图片导出目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.save_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.save_dir, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)
        ttk.Label(self, text='原有图片目录或phash: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dst_path, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dst_path, True), invalidcommand=show_path_error).grid(row=3,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath3).grid(row=3, column=4)
        ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="根据原有图片目录", variable=self.mode, value=True).grid(column=1, row=4, sticky=tk.EW)
        ttk.Radiobutton(self, text="根据原有图片phash信息", variable=self.mode, value=False).grid(column=2, row=4, sticky=tk.EW)
        self.mode.set(True)  # 设置默认值

        ttk.Label(self, text='相似度阈值(默认0.98): ').grid(row=5, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.threshold, width=10, validate="focusout",
                  validatecommand=lambda: check_threNum(self.threshold), invalidcommand=show_threNum_error).grid(row=5,
                                                                                                                 column=1,
                                                                                                                 stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self, text='导出方式: ').grid(row=5, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="复制", variable=self.option, value="copy").grid(column=3, row=5, sticky=tk.W)
        ttk.Radiobutton(self, text="剪切", variable=self.option, value="move").grid(column=4, row=5, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中否

        ttk.Button(self, text="执行", command=self.run).grid(row=6, column=4)
        ttk.Label(self, text='完成进度: ').grid(row=8, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=8, column=1, columnspan=5, stick=tk.EW)
        scrolW = 80
        scrolH = 25
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=9, sticky='WE', columnspan=6)
        ttk.Button(self, text="查看相似图片", command=self.showFiles).grid(row=10, column=0, pady=10, sticky=tk.W)

    def showFiles(self):
        """查看结果目录"""
        if self.save_dir.get():
            webbrowser.open(self.save_dir.get())

    @log_error
    def deal_image_similarity(self):
        print(self.search_dir.get(), self.save_dir.get(), self.threshold.get(), self.option.get())
        # msg = handler.deal_image_similarity(self.search_dir.get(), self.save_dir.get(), self.threshold.get(), self.option.get())
        record, msg = search_image.run(self, self.search_dir.get(), self.dst_path.get(), self.save_dir.get(),
                                       self.threshold.get(), self.option.get())
        mBox.showinfo('完成！', msg)

    def run(self):
        self.scr.delete(1.0, 'end')
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        t = threading.Thread(target=self.deal_image_similarity)
        t.start()


class SearchVideoFrame(tk.Frame):
    """以视频搜索相似视频"""

    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.root = master  # 定义内部变量root
        self.frameNum = tk.IntVar()
        self.continue_flag = tk.BooleanVar()
        self.threshold = tk.DoubleVar()
        self.option = tk.StringVar()
        self.search_dir = tk.StringVar()
        self.dst_dir = tk.StringVar()  # 原有视频路径或者phash json
        self.mode = tk.StringVar()  # 是否根据图片目录 True 图片目录 False 图片phash json
        self.save_dir = tk.StringVar()
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
        tk.Label(self, text='以视频搜索视频界面', font=('Arial', 12), width=50, height=2).grid(row=0, column=1, pady=10)
        ttk.Label(self, text='要搜索的视频的目录: ').grid(row=1, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.search_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.search_dir), invalidcommand=show_path_error).grid(row=1,
                                                                                                            column=1,
                                                                                                            columnspan=3,
                                                                                                            stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath1).grid(row=1, column=4)
        ttk.Label(self, text='相似视频导出目录: ').grid(row=2, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.save_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.save_dir, True), invalidcommand=show_path_error).grid(row=2,
                                                                                                                column=1,
                                                                                                                columnspan=3,
                                                                                                                stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath2).grid(row=2, column=4)
        self.mode_ttk = ttk.Label(self, text='原有视频目录: ').grid(row=3, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.dst_dir, width=80, validate="focusout",
                  validatecommand=lambda: check_path(self.dst_dir, True), invalidcommand=show_path_error).grid(row=3,
                                                                                                               column=1,
                                                                                                               columnspan=3,
                                                                                                               stick=tk.EW)
        ttk.Button(self, text="浏览", command=self.selectPath3).grid(row=3, column=4)
        # ttk.Label(self, text='模式选择: ').grid(row=4, stick=tk.W, pady=10)
        # ttk.Radiobutton(self, text="根据原有视频目录", variable=self.mode, value="原有视频目录", command=self.changeMode).grid(column=1, row=4, sticky=tk.EW)
        # ttk.Radiobutton(self, text="根据原有视频导出帧图片目录", variable=self.mode, value="原有视频导出帧图片目录", command=self.changeMode).grid(column=2, row=4, sticky=tk.EW)
        # ttk.Radiobutton(self, text="根据原有视频导出帧图片phash信息", variable=self.mode, value="原有视频导出帧图片目录", command=self.changeMode).grid(column=3, row=4, sticky=tk.EW)
        self.mode.set("原有视频目录")  # 设置默认值ttk.Label(self, text='比对第几帧图像: ').grid(row=4, column=0, stick=tk.W, pady=10)
        ttk.Label(self, text='比对第几帧图像: ').grid(row=5, column=0, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.frameNum, width=10, validate="focusout",
                  validatecommand=lambda: check_frameNum(self.frameNum), invalidcommand=show_frameNum_error).grid(row=5,
                                                                                                                  column=1,
                                                                                                                  stick=tk.W)
        self.frameNum.set(90)  # 设置默认值为90
        ttk.Label(self, text='是否继续上次进度: ').grid(row=5, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="是", variable=self.continue_flag, value=True).grid(column=3, row=5, sticky=tk.W)
        ttk.Radiobutton(self, text="否", variable=self.continue_flag, value=False).grid(column=4, row=5, sticky=tk.W)
        self.continue_flag.set(False)  # 设置默认选中否

        ttk.Label(self, text='相似度阈值(默认0.98): ').grid(row=6, column=0, stick=tk.W, pady=10)
        ttk.Entry(self, textvariable=self.threshold, width=10, validate="focusout",
                  validatecommand=lambda: check_threNum(self.threshold), invalidcommand=show_threNum_error).grid(row=6,
                                                                                                                 column=1,
                                                                                                                 stick=tk.W)
        self.threshold.set(0.98)  # 设置默认值为0.98
        ttk.Label(self, text='导出方式: ').grid(row=6, column=2, stick=tk.W, pady=10)
        ttk.Radiobutton(self, text="复制", variable=self.option, value="copy").grid(column=3, row=6, sticky=tk.W)
        ttk.Radiobutton(self, text="剪切", variable=self.option, value="move").grid(column=4, row=6, sticky=tk.W)
        self.option.set("copy")  # 设置默认选中
        ttk.Button(self, text="执行", command=self.run).grid(row=7, column=4)
        ttk.Label(self, text='完成进度: ').grid(row=8, stick=tk.W, pady=10)
        self.pb1 = ttk.Progressbar(self, orient="horizontal", length=400, value=0, mode="determinate")
        self.pb1.grid(row=8, column=1, columnspan=5, stick=tk.EW)
        scrolW = 80
        scrolH = 25
        self.scr = scrolledtext.ScrolledText(self, width=scrolW, height=scrolH, wrap=tk.WORD)
        self.scr.grid(column=0, row=9, sticky='WE', columnspan=6)
        ttk.Button(self, text="查看相似视频", command=self.showFiles).grid(row=10, column=0, pady=10, sticky=tk.W)

    def changeMode(self):
        """用于修改模式，是根据原有视频目录比对还是根据原有视频导出帧图像比对还是根据原视频帧图像phash信息比对"""
        self.mode_ttk["text"] = self.mode.get()

    def showFiles(self):
        """查看结果目录"""
        if self.save_dir.get():
            webbrowser.open(self.save_dir.get())

    @log_error
    def deal_video_similarity(self, src_dir_path, dst_dir_path, save_dir_path, frame_num, continue_flag, threshold,
                              deal_video_mode):
        msg = search_video.run(self, src_dir_path, dst_dir_path, save_dir_path, frame_num, continue_flag, threshold,
                               deal_video_mode)
        mBox.showinfo("查找相似视频完成!", msg)

    def run(self):
        self.scr.delete(1.0, "end")
        self.pb1["value"] = 0
        self.pb1["maximum"] = 0  # 总项目数
        print(self.search_dir.get(), self.dst_dir.get(), self.save_dir.get(), self.frameNum.get(),
              self.continue_flag.get(), self.threshold.get(), self.option.get())
        args = (
        self.search_dir.get(), self.dst_dir.get(), self.save_dir.get(), self.frameNum.get(), self.continue_flag.get(),
        self.threshold.get(), self.option.get())
        t = threading.Thread(target=self.deal_video_similarity, args=args)
        t.start()


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
        ttk.Label(self, text='by yl').pack()
        ttk.Label(self, text='这是一个多功能的小程序，').pack()
        ttk.Label(self, text=' 包含导出文件信息 、查找重复文件、文件同步备份、还原文件、删除文件、清除空文件夹、搜索文件、拷贝目录层次结构、').pack()
        ttk.Label(self, text='计算文件hash值、比对文本文件内容、提取视频帧图像、计算图片相似度、查找相似视频等功能').pack()
