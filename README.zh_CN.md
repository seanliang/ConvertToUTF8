说明
------------------
通过本插件，您可以编辑并保存目前编码不被 Sublime Text 支持的文件，特别是中日韩用户使用的 GB2312，GBK，BIG5，EUC-KR，EUC-JP 等。ConvertToUTF8 同时支持 Sublime Text 2 和 3。

![ConvertToUTF8](https://seanliang.github.io/donate/ConvertToUTF8.gif)

如果您觉得本插件有用并想给予支持，可通过支付宝或微信捐助。感谢！:)

![支付宝钱包扫一下](https://seanliang.github.io/donate/ap.png) ![微信扫一下](https://seanliang.github.io/donate/wx.png)


注意
------------------
** Windows 7（Sublime Text 3）：当设置Windows自定义文本大小（DPI）超过100%时，文件名可能无法正确显示，请尝试在Sublime Text 3的用户设置中添加`"dpi_scale": 1`。

** Linux（Sublime Text 2 & 3）及OSX（Sublime Text 3）：你需要安装一个额外插件以便ConvertToUTF8能正常工作：[Codecs26](https://github.com/seanliang/Codecs26)（针对 Sublime Text 2）或 [Codecs33](https://github.com/seanliang/Codecs33)（针对 Sublime Text 3）。

安装
------------------
推荐使用 [Package Control](https://packagecontrol.io/installation) 查找 *ConvertToUTF8* 进行自动下载安装与更新。

如需手工安装，请将本项目打包下载并解压，将解压后的文件夹名修改为 *ConvertToUTF8* ，然后将此文件夹移动到 Sublime Text 的 *Packages* 文件夹下（可通过 Sublime Text 菜单中的 Preferences > Browse Packages 找到 *Packages* 文件夹）。

您的文件夹应该看起来是这样的：

![Folder Hierarchy](https://seanliang.github.io/donate/hierarchy.png)

设置
------------------
请查看 ConvertToUTF8.sublime-settings 文件获取详细信息。为防止更新插件时被覆盖，请将个人设置保存到 User 目录中名为 ConvertToUTF8.sublime-settings 文件中。您可以在 .sublime-project 文件（可通过 Project > Edit Project 打开）中指定项目专属设置（除 encoding_list 和 max_cache_size 外）。

* encoding_list：检测失败时显示的编码列表
* reset_diff_markers：在转换后重置差异标记（默认为 true）
* max_cache_size：最大编码缓存数量，0 表示不缓存（默认为 100）
* max_detect_lines：最大检测行数，0 表示不限制（默认为 600）
* preview_action：预览文件时是否将其内容转换为 UTF-8（默认为 false）
* default_encoding_on_create：指定新建文件的默认编码（如 GBK），空值表示使用 Sublime Text 的 default_encoding 设置（默认为 ""）
* convert_on_load：文件装载时是否将其内容转换成 UTF-8（默认为 true）
* convert_on_save：文件保存时是否将其内容转换成原有（或指定）编码（默认为 true）
* convert_on_find：将 Find Results 窗口里的内容转换成 UTF-8（默认为 false）
* lazy_reload：将文件保存到临时位置，并在切换窗口或标签时在后台自动重载（默认为 false）
* confidence：最低可信率，检测时超过这个值将触发自动转换（默认为0.95）

使用说明
------------------
多数情况下，本插件将自动对处理编码相关的事项。

您也可以通过 File > Set File Encoding to 菜单对文件编码进行手工转换。例如，您可以打开一个 UTF-8 编码的文件，指定保存为 GBK，反之亦然。

注意：
* 如果 convert_on_save 被设置为 `false`，文件*不会*被保存成指定编码
* 在文件编码检测过程完成前请勿编辑文件
* 若检测结果不准确，请尝试增大 max_detect_lines 的值或手工指定编码
* 由于 API 限制，在 lazy_reload 设置为 `true` 时，保存文件后立即退出 Sublime Text 将造成文件被保存为 UTF-8，正确的内容将在下次 Sublime Text 打开时重载

常见问题
------------------
* 问：安装后无法工作，要如何修复？

  答：请尝试以下步骤：
  1. 重启 Sublime Text
  2. 请确认插件目录名为 ConvertToUTF8（如果是通过 Package Control 安装的可略过此步骤）
  3. 参见[上述“注意”条目](#注意)
  4. 禁用其他编码相关的插件
  5. 联系我

* 问：这个插件支持哪些编码？

  答：所有 [Python 支持的编码](http://docs.python.org/library/codecs.html#standard-encodings) 都可以，其他编码如 EUC-TW 将不被支持。

* 问：为何有时重新激活窗口，里面的内容会变乱码？

  答：此问题是由重新载入引起的，且已修复，请更新 *ConvertToUTF8* 插件到最新版本。

* 问：为什么重新激活窗口时，ST2 问我文件“已经被修改。是否要重新载入？”

  答：原因与上一条相同。如果您有未保存的修改，请选择“取消”。

* 问：在保存文件时，Sublime Text 为什么提示将文件保存为 UTF-8？

  答：没有关系，本插件会自动将文件内容保存为原始编码。

* 问：我的文件被保存为UTF-8，而且变成了乱码，要如何恢复？

  答：请打开这个文件，并确认它的编码是UTF-8，然后选择菜单项目 File > Save with Encoding > Western (Windows 1252)，关闭再重新打开该文件即可。

联系我
------------------
请发送您的问题或建议给我：sunlxy (at) yahoo.com 或 http://weibo.com/seanliang
