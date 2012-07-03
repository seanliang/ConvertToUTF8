说明
------------------
Sublime Text 2 目前不支持双字节编码，包括 CJK 用户经常使用的 GB2312、GBK、BIG5、EUC-KR、EUC-JP 等，这将导致读取使用此类编码的文件出现乱码，本插件就是为解决此问题而产生。安装本插件后，将可以正常查看、修改和保存这些文件。

本插件的主要功能：
* 在打开文件时对其进行解码
* 如发现此编码不被 Sublime Text 支持，将对文件内容进行转换，以便用户正常读取和编辑
* 在保存文件时，将文件内容转换回原文档编码

安装
------------------
推荐使用 [Package Control](http://wbond.net/sublime_packages/package_control) 查找 *ConvertToUTF8* 进行自动下载安装与更新。

如需手工安装，请将本项目打包下载并解压，将解压后的文件夹名修改为 *ConvertToUTF8* ，然后将此文件夹移动到 Sublime Text 的 *Packages* 文件夹下（可通过 Sublime Text 菜单中的 Preferences > Browse Packages 找到 *Packages* 文件夹）。

设置
------------------
请查看[设置文件](ConvertToUTF8.sublime-settings)获取详细信息。
* max_cache_size：最大编码缓存数量，0 表示不缓存（默认为 100）
* max_detect_lines：最大检测行数，0 表示不限制（默认为 600）
* convert_on_load：如设置为 never，打开文件时将不进行解码（默认为 always）
* convert_on_save：如设置为 never，文件保存时将转换成 UTF-8 编码（默认为 always）

使用说明
------------------
本插件将自动对文件编码进行检测，并将其内容转换成 UTF-8，以供用户查看与编辑。同时，在保存时将文件转换回原编码。

ConvertToUTF8 在 File（文件）菜单下建立了一个子菜单 Set File Encoding to。用户可通过该菜单对文件编码进行手工转换。例如，你可以打开一个 UTF-8 编码的文件，指定保存为 GBK，反之亦然。

注意：
* 如果 convert_on_load 被设置为 never，ConvertToUTF8 将使用指定的编码对文件进行解码
* 如果 convert_on_save 被设置为 never，文件不会被保存成指定编码
* 在文件编码检测过程完成前请勿编辑文件
* 若检测结果不准确，请尝试增大 max_detect_lines 的值或手工指定编码


常见问题
------------------
* 问：这个插件支持哪些编码？

  答：只要你的系统支持的编码应该都可使用。

* 问：为何有时重新激活窗口，里面的内容会变乱码？

  答：此问题是由重新载入引起的，且已修复，请更新 *ConvertToUTF8* 插件到最新版本。

* 问：为什么重新激活窗口时，ST2 问我文件“已经被修改。是否要重新载入？”

  答：原因与上一条相同。如果你有未保存的修改，请选择“取消”。

* 问：在保存文件时，Sublime Text 为什么提示将文件保存为 UTF-8？

  答：没有关系，本插件会自动将文件内容保存为原始编码。

联系我
------------------
有什么问题或建议，欢迎给我留言：http://weibo.com/seanliang
