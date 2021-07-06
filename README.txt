FileManager程序说明

程序目录结构
│  README.txt  # 程序说明
│  
├─bin
│      __init__.py
│      filemanager.py  # 程序入口
│      MainPage.py  # 程序视图
│      view.py  # 程序视图
│      
├─conf
│      __init__.py
│      settings.py  # 程序配置文件
│      
├─core
│      __init__.py
│      Check.py  # 用于实现校验功能的函数
│      CompareTxt.py  # 比对文本文件内容模块
│      hash_core.py  # 计算文件hash值模块
│      ImageTools.py  # 计算文件相似度模块
│      logger.py  # 日志模块
│      ModifyTimestamp.py  # 文件同步模块，优化备份端备份操作
│      Mytools.py  # 通用工具模块
│      SearchFiles.py  # 搜索文件功能模块
│      SynTools.py  # 以图搜图模块
│      VideoTools.py  # 以视频搜视频模块
│      
├─db  # 用于存放记录相关
├─dir # 用于存放程序运行产生文件
└─log  # 日志
        error.log
        operate.log
        process.log
        
		

使用说明:
1.程序所需依赖包

pip install opencv-python
pip install pillow
pip install windnd
pip install moviepy
pip install natsort
pip install exifread
pip install pywin32

安装 pip install 

2.运行方式 python filemanager.py

注意事项:
	1.除非必要否则不要轻易修改设置内容
	2.数据无价，谨慎操作！



程序模块说明：
view.py 所有操作视图类
	BaseFrame  所有视图类的基类
	ExportFrame 导出文件信息
	FindSameFrame  文件查重
	FindSameFilesByHashFrame  文件去重（hash值方式）
	SynFrame  文件备份同步
	RestoreFrame  还原文件
	DelfileFrame  文件删除
	CleanEmptyDirFrame  清空空文件夹
	SearchFrame  搜索文件
	CopyDirTreeFrame  拷贝目录结构
	DelFileFrame  更新删除文件的样本记录
	CompareTxtFrame  比对文本文件内容
	CalHashFrame  计算文件hash值
	CompStrFrame  校对字符串
	RenameFrame  批量重命名
	GetImgFrame  提取视频帧图像
	CalImgSimFrame  计算图片相似度
	CalVideoSimFrame  查找相似视频
	SearchImgFrame  以图搜图
	SearchVideoFrame  以视频搜相似视频
	GetAudioFrame  音频处理
	VideoMergeFrame  视频合并
	VideoCutFrame  视频截取
	TimestampFrame  时间戳相关功能
	FindBadVideoFrame  查找损坏或不完整的视频文件
	SettingFrame  设置界面
	AboutFrame  关于界面


