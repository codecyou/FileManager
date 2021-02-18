FileManager程序说明

程序目录结构
│  readme.txt  # 程序说明
│  
├─bin
│      filemanager.py  # 程序入口
│      MainPage.py  # 程序视图
│      view.py  # 程序视图
│      __init__.py
│      
├─conf
│      settings.py  # 程序配置文件
│      __init__.py
│      
├─core
│      backup.py  # 文件同步备份模块1
│      compare_file.py  # 比对文本文件内容模块
│      file_dir_syn.py  # 文件同步，比对备份端目录变更模块
│      get_img_thread.py  # 提取视频帧图像模块
│      hash_core.py  # 计算文件hash值模块
│      image_similarity_thread.py  # 计算文件相似度模块
│      logger.py  # 日志模块
│      Mybackup.py  # 文件同步模块，优化备份端备份操作
│      Mytools.py  # 通用工具模块
│      search.py  # 搜索文件功能模块
│      search_image.py  # 以图搜图模块
│      search_video.py  # 以视频搜视频模块
│      video_similarity.py  # 搜索相似视频模块
│      __init__.py
│      
├─db  # 用于存放记录相关
├─dir # 用于存放程序运行产生文件
└─log  # 日志
        error.log
        operate.log
        process.log
        
		

使用说明:
1.程序所需第三方包opencv,pillow,windnd
安装 pip install 

2.运行方式 python filemanager.py

注意事项:
	1.除非必要否则不要轻易修改设置内容
	2.数据无价，谨慎操作！



程序模块说明：
view.py 类说明
ExportFrame 导出文件信息
QuerySameFrame  文件查重
SynFrame  文件备份同步
RestoreFrame  还原文件
ClearEmptyDirFrame  清空空文件夹
QueryFrame  搜索文件
CopyDirTreeFrame  拷贝目录结构
DelFileFrame  更新删除文件的样本记录
CompareTxtFrame  比对文本文件内容
CalHashFrame  计算文件hash值
GetImgFrame  提取视频帧图像
CalImgSimFrame  计算图片相似度
CalVideoSimFrame  查找相似视频
SearchImgFrame  以图搜图
SearchVideoFrame  以视频搜相似视频
SettingFrame  设置界面
AboutFrame  关于界面


