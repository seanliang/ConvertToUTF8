说明
------------------
通过本插件，您可以编辑并保存目前编码不被 Sublime Text 支持的文件，特别是中日韩用户使用的 GB2312，GBK，BIG5，EUC-KR，EUC-JP 等。

![ConvertToUTF8](http://dl.dropbox.com/u/31937639/ConvertToUTF8/ConvertToUTF8.gif)

安装
------------------
推荐使用 [Package Control](http://wbond.net/sublime_packages/package_control) 查找 *ConvertToUTF8* 进行自动下载安装与更新。

如需手工安装，请将本项目打包下载并解压，将解压后的文件夹名修改为 *ConvertToUTF8* ，然后将此文件夹移动到 Sublime Text 的 *Packages* 文件夹下（可通过 Sublime Text 菜单中的 Preferences > Browse Packages 找到 *Packages* 文件夹）。

您的文件夹应该看起来是这样的：

![Folder Hierarchy](http://dl.dropbox.com/u/31937639/ConvertToUTF8/hierarchy.png)

设置
------------------
请查看 ConvertToUTF8.sublime-settings 文件获取详细信息。为防止更新插件时被覆盖，请将个人设置保存到 User 目录中名为 ConvertToUTF8.sublime-settings 文件中。

* encoding_list：检测失败时显示的编码列表
* max_cache_size：最大编码缓存数量，0 表示不缓存（默认为 100）
* max_detect_lines：最大检测行数，0 表示不限制（默认为 600）
* preview_action：指定预览模式下的动作，可选项：no_action 不作任何动作，convert_and_open 转换编码并打开（默认为 no_action）
* default_encoding_on_create：指定新建文件的默认编码（如 GBK），空值表示使用 Sublime Text 的 default_encoding 设置（默认为空值）
* convert_on_load：启用/禁用文件装载时将窗口内容转换成UTF-8编码，可选项：always 自动转换，never 不转换（默认为 always）
* convert_on_save：启用/禁用文件保存时将其从UTF-8转换成指定转码，可选项：always 自动转换，never 不转换（默认为 always）

使用说明
------------------
多数情况下，本插件将自动对处理编码相关的事项。

您也可以通过 File > Set File Encoding to 菜单对文件编码进行手工转换。例如，您可以打开一个 UTF-8 编码的文件，指定保存为 GBK，反之亦然。

注意：
* 如果 convert_on_save 被设置为 never，文件不会被保存成指定编码
* 在文件编码检测过程完成前请勿编辑文件
* 若检测结果不准确，请尝试增大 max_detect_lines 的值或手工指定编码


常见问题
------------------
* 问：安装后无法工作，要如何修复？

  答：请尝试以下步骤：
  1. 重启 Sublime Text
  2. 请确认插件目录名为 ConvertToUTF8（如果是通过 Package Control 安装的可略过此步骤）
  3. 如果您的系统是64位 Ubuntu，请手工安装 Python 2.6
<code>  
sudo add-apt-repository ppa:fkrull/deadsnakes  
sudo apt-get update  
sudo apt-get install python2.6  
sudo ln -s /usr/lib/python2.6 /PATH_TO_ST2/lib  
</code>
  4. 禁用其他编码相关的插件
  5. 联系我

* 问：这个插件支持哪些编码？

  答：只要您的系统支持的编码应该都可使用。

* 问：为何有时重新激活窗口，里面的内容会变乱码？

  答：此问题是由重新载入引起的，且已修复，请更新 *ConvertToUTF8* 插件到最新版本。

* 问：为什么重新激活窗口时，ST2 问我文件“已经被修改。是否要重新载入？”

  答：原因与上一条相同。如果您有未保存的修改，请选择“取消”。

* 问：在保存文件时，Sublime Text 为什么提示将文件保存为 UTF-8？

  答：没有关系，本插件会自动将文件内容保存为原始编码。

联系我
------------------
请发送您的问题或建议给我：sunlxy (at) yahoo.com 或 http://weibo.com/seanliang
