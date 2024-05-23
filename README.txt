FileManager程序说明（本程序暂时仅支持windows平台）
version 3.37.0+


程序目录结构
│      README.md  # 程序说明
│  
├─bin
│      __init__.py
│      filemanager.py  # 程序入口
│
├─view
│      __init__.py
│      MainPage.py  # 程序视图
│      views.py  # 程序视图
│
├─conf
│      __init__.py
│      my_api.py  # 程序功能函数路由|接口
│      settings.py  # 程序配置文件
│      
├─core
│      __init__.py
│      common_utils.py  # 通用工具模块
│      expire_func.py  # 扩展工具模块，存放已经不再使用的功能函数，作为储备代码备用，打包exe的时候不打包，减小程序体积
│      extension_utils.py  # 涉及第三方库引用的功能函数
│      image_utils.py  # 图像处理相关模块，图像转码、计算相似度
│      logger.py  # 日志模块
│      search_utils.py  # 搜索相似文件模块
│      syn_utils.py  # 文件同步备份相关模块
│      video_utils.py  # 视频处理相关模块，视频帧图像提取、计算视频相似度
│      
├─db  # 用于存放记录相关
├─Record  # 用于存放程序运行产生文件
└─log  # 日志
        operate.log  # 操作日志

		

使用说明:
1.程序所需依赖包
pip install windnd
pip install filetype
pip install natsort
pip install openpyxl
pip install exifread
pip install chardet
pip install pymediainfo
pip install pillow
pip install pillow_heif
pip install pywin32

# 以下第三方库可选
pip install opencv-python


2.运行方式 python filemanager.py


注意事项:
	1.除非必要否则不要轻易修改设置内容
	2.数据无价，谨慎操作！


关于代码：
	1.threading.Thread.setDaemon 于 python 3.10 被弃用，使用threading.Thread.daemon设置线程守护
	2.pillow(10.0.0之后) Image.ANTIALIAS 被移除了,取而代之的是Image.LANCZOS or Image.Resampling.LANCZOS
	3.pyinstaller>=6.0.0 版本后，在打包 one dir（-D 目录模式）时，除可执行文件外，其余文件都将被转移到 _internal 文件夹下


程序模块说明：
view.py 所有操作视图类
	BaseFrame  所有视图类的基类
	FindSameFrame  查找重复文件
	FindSameFilesByHashFrame  查找重复文件（hash值方式）
	SynFrame  文件备份同步
	RestoreFrame  还原文件
	CleanEmptyDirFrame  清除空文件夹
	SearchFrame  搜索文件
	CopyDirTreeFrame  拷贝目录结构
	CompareTxtFrame  比对文本文件内容
	CalHashFrame  计算文件hash值
	RenameFrame  批量重命名
	GetImgFrame  提取视频帧图像
	CalImgSimFrame  计算图片相似度
	CalVideoSimFrame  查找相似视频
	SearchImgFrame  以图搜图
	SearchVideoFrame  以视频搜相似视频
	GetAudioFrame  音频处理
	VideoCutFrame  视频截取
	TimestampFrame  时间戳相关功能
	ImageProcessingFrame  图片格式转换
	TxtEncodeFrame  处理文本文件编码转换
	FileArrangeFrame  文件分类
	SettingFrame  设置界面
	AboutFrame  关于界面


