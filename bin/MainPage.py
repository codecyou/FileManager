from bin.view import *   # 菜单栏对应的各个子页面


class MainPage(object):
    def __init__(self, master=None):
        self.fuc_dict = {
            '1.导出文件信息': self.exportData,
            '2.查找重复文件': self.querySameData,
            '3.文件备份与同步': self.countData,
            '4.还原文件': self.restoreFile,
            '5.删除文件': self.delFile,
            '6.删除空文件夹': self.clearEmptyDir,
            "7.搜索文件或目录": self.queryData,
            "8.拷贝目录结构": self.copyDir,
            "9.比对文本文件内容": self.compareTxt,
            "10.计算文件的hash值": self.calHash,
            "A.提取视频帧图像": self.getImg,
            "B.计算图片相似度,找出相似图片": self.calImgSim,
            "C.找出相似视频": self.calVideoSim,
            "D.以图搜图": self.searchImage,
            "D.以视频搜相似视频": self.searchVideo,
        }
        self.root = master  # 定义内部变量root
        # 设置窗口大小
        winWidth = 900
        winHeight = 750
        # 获取屏幕分辨率
        screenWidth = self.root.winfo_screenwidth()
        screenHeight = self.root.winfo_screenheight()

        x = int((screenWidth - winWidth) / 2)
        y = int((screenHeight - winHeight) / 2)

        # 设置窗口初始位置在屏幕居中
        self.root.geometry("%sx%s+%s+%s" % (winWidth, winHeight, x, y))
        self.page = None  # 用于标记功能界面
        self.createPage()

    def createPage(self):
        self.exportPage = ExportFrame(self.root)  # 创建不同Frame
        self.querySamePage = QuerySameFrame(self.root)
        self.countPage = SynFrame(self.root)
        self.restorePage = RestoreFrame(self.root)
        self.clearEmptyDirPage = ClearEmptyDirFrame(self.root)
        self.copyDirPage = CopyDirTreeFrame(self.root)
        self.getImgPage = GetImgFrame(self.root)
        self.calImgSimPage = CalImgSimFrame(self.root)
        self.calVideoSimPage = CalVideoSimFrame(self.root)
        self.delFilePage = DelFileFrame(self.root)
        self.queryPage = QueryFrame(self.root)
        self.compareTxtPage = CompareTxtFrame(self.root)
        self.calHashPage = CalHashFrame(self.root)
        self.searchImagePage = SearchImgFrame(self.root)
        self.searchVideoPage = SearchVideoFrame(self.root)
        self.aboutPage = AboutFrame(self.root)
        self.settingPage = SettingFrame(self.root)

        self.pages = [self.exportPage, self.querySamePage, self.countPage, self.restorePage, self.clearEmptyDirPage,
                      self.copyDirPage, self.getImgPage, self.calImgSimPage, self.calVideoSimPage, self.delFilePage,
                      self.queryPage, self.compareTxtPage, self.calHashPage, self.aboutPage, self.settingPage,
                      self.searchImagePage, self.searchVideoPage]

        self.exportPage.pack()  # 默认显示数据录入界面
        menubar = tk.Menu(self.root)
        optionmenu = tk.Menu(menubar, tearoff=0)
        # 将上面定义的空菜单命名为File，放在菜单栏中，就是装入那个容器中
        menubar.add_cascade(label='操作', menu=optionmenu)

        # 在File中加入New、Open、Save等小菜单，即我们平时看到的下拉菜单，每一个小菜单对应命令操作。
        for item in self.fuc_dict:
            optionmenu.add_command(label=item, variable=self.page, command=self.fuc_dict[item])

        # 第7步，创建一个Edit菜单项（默认不下拉，下拉内容包括Cut，Copy，Paste功能项）
        settingmenu = tk.Menu(menubar, tearoff=0)
        # 将上面定义的空菜单命名为 Edit，放在菜单栏中，就是装入那个容器中
        menubar.add_cascade(label='设置', menu=settingmenu)
        settingmenu.add_command(label="设置", command=self.setting)
        settingmenu.add_command(label="关于", command=self.aboutDisp)
        self.root['menu'] = menubar  # 设置菜单栏

    def display(self, page):
        """用于展示当前页面"""
        for item in self.pages:
            if item == page:
                page.pack()
                continue
            item.pack_forget()

    def exportData(self):
        self.display(self.exportPage)

    def querySameData(self):
        self.display(self.querySamePage)

    def countData(self):
        self.display(self.countPage)

    def restoreFile(self):
        self.display(self.restorePage)

    def clearEmptyDir(self):
        self.display(self.clearEmptyDirPage)

    def queryData(self):
        self.display(self.queryPage)

    def copyDir(self):
        self.display(self.copyDirPage)

    def getImg(self):
        self.display(self.getImgPage)

    def calImgSim(self):
        self.display(self.calImgSimPage)

    def calVideoSim(self):
        self.display(self.calVideoSimPage)

    def searchImage(self):
        self.display(self.searchImagePage)

    def searchVideo(self):
        self.display(self.searchVideoPage)

    def delFile(self):
        self.display(self.delFilePage)

    def compareTxt(self):
        self.display(self.compareTxtPage)

    def calHash(self):
        self.display(self.calHashPage)

    def aboutDisp(self):
        self.display(self.aboutPage)

    def setting(self):
        self.display(self.settingPage)


