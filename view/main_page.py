from view.views import *   # 菜单栏对应的各个子页面


class MainPage(object):
    def __init__(self, master=None):
        self.fuc_dict = {
            '查找重复文件': self.findSameData,
            "查找重复文件-Hash": self.findSameFilesByHash,
            '文件备份同步': self.synData,
            '还原文件': self.restoreFile,
            '清除空目录': self.cleanEmptyDir,
            "拷贝目录结构": self.copyDir,
            "搜索": self.searchData,
            "比对文本": self.compareTxt,
            "计算Hash值": self.calHash,
            "提取视频帧图像": self.getImg,
            "查找相似图片": self.calImgSim,
            "查找相似视频": self.calVideoSim,
            "以图搜图": self.searchImage,
            "以视频搜视频": self.searchVideo,
            "重命名": self.rename,
            "视频截取": self.videoCut,
            "音频处理": self.getAudio,
            "图片处理": self.imageProcessing,
            "文本处理": self.txtEncode,
            "文件分类": self.fileArrange,
            "时间戳操作": self.getTimestamp,
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
        # self.root.resizable(width=0, height=0)  # 设置窗口大小固定
        self.page = None  # 用于标记功能界面
        self.createPage()

    def createPage(self):
        self.findSamePage = FindSameFrame(self.root)
        self.synPage = SynFrame(self.root)
        self.restorePage = RestoreFrame(self.root)
        self.cleanEmptyDirPage = CleanEmptyDirFrame(self.root)
        self.copyDirPage = CopyDirTreeFrame(self.root)
        self.getImgPage = GetImgFrame(self.root)
        self.calImgSimPage = CalImgSimFrame(self.root)
        self.calVideoSimPage = CalVideoSimFrame(self.root)
        self.searchPage = SearchFrame(self.root)
        self.compareTxtPage = CompareTxtFrame(self.root)
        self.calHashPage = CalHashFrame(self.root)
        self.searchImagePage = SearchImgFrame(self.root)
        self.searchVideoPage = SearchVideoFrame(self.root)
        self.findSameFilesByHashPage = FindSameByHashFrame(self.root)
        self.renamePage = RenameFrame(self.root)
        self.getAudioPage = GetAudioFrame(self.root)
        self.videoCutPage = VideoCutFrame(self.root)
        self.getTimestampPage = TimestampFrame(self.root)
        self.imageProcessingPage = ImageProcessingFrame(self.root)
        self.txtEncodePage = TxtEncodeFrame(self.root)
        self.fileArrangePage = FileArrangeFrame(self.root)
        self.aboutPage = AboutFrame(self.root)
        self.settingPage = SettingFrame(self.root)

        self.pages = [self.findSamePage, self.findSameFilesByHashPage,self.synPage, self.restorePage, self.cleanEmptyDirPage,
                      self.copyDirPage, self.getImgPage, self.calImgSimPage, self.calVideoSimPage,
                      self.searchPage, self.compareTxtPage, self.calHashPage, self.aboutPage, self.settingPage,
                      self.searchImagePage, self.searchVideoPage, 
                      self.renamePage, self.getAudioPage,self.videoCutPage, self.getTimestampPage,
                      self.imageProcessingPage, self.txtEncodePage,self.fileArrangePage]

        self.pages[0].pack(fill=tk.BOTH, expand=True, padx=10, pady=10)  # 默认显示界面
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
                page.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                continue
            item.pack_forget()


    def findSameData(self):
        self.display(self.findSamePage)

    def synData(self):
        self.display(self.synPage)

    def restoreFile(self):
        self.display(self.restorePage)

    def cleanEmptyDir(self):
        self.display(self.cleanEmptyDirPage)

    def searchData(self):
        self.display(self.searchPage)

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

    def compareTxt(self):
        self.display(self.compareTxtPage)

    def calHash(self):
        self.display(self.calHashPage)

    def findSameFilesByHash(self):
        self.display(self.findSameFilesByHashPage)

    def rename(self):
        self.display(self.renamePage)

    def getAudio(self):
        self.display(self.getAudioPage)

    def videoCut(self):
        self.display(self.videoCutPage)

    def getTimestamp(self):
        self.display(self.getTimestampPage)

    def imageProcessing(self):
        self.display(self.imageProcessingPage)

    def txtEncode(self):
        self.display(self.txtEncodePage)
    
    def fileArrange(self):
        self.display(self.fileArrangePage)

    def aboutDisp(self):
        self.display(self.aboutPage)

    def setting(self):
        self.display(self.settingPage)


