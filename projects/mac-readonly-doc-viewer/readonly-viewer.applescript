property supportedExtensions : {"doc", "docx", "rtf", "rtfd", "odt", "wps", "pdf", "txt"}

on run
	set chosenItems to choose file with prompt "选择要只读查看的文档" with multiple selections allowed
	my previewItems(chosenItems)
end run

on open droppedItems
	my previewItems(droppedItems)
end open

on previewItems(theItems)
	repeat with anItem in theItems
		set itemPath to POSIX path of anItem
		set shellCommand to "/usr/bin/nohup /usr/bin/qlmanage -p " & quoted form of itemPath & " >/dev/null 2>&1 &"
		do shell script shellCommand
	end repeat
end previewItems
