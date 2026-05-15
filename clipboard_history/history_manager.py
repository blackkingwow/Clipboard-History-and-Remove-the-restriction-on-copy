class HistoryManager:
    """剪贴板历史记录管理器，负责存储、去重、裁剪和排序。"""

    def __init__(self, max_entries=30):
        self._entries = []
        self.max_entries = max_entries

    def add(self, text: str) -> bool:
        """添加一条记录。如内容重复则删除旧条目并将新条目置顶。返回 True 表示列表有变化。"""
        if not text:
            return False
        for i, entry in enumerate(self._entries):
            if entry == text:
                self._entries.pop(i)
                self._entries.insert(0, text)
                return True
        self._entries.insert(0, text)
        if len(self._entries) > self.max_entries:
            self._entries.pop()
        return True

    def remove(self, index: int):
        """删除指定索引的条目。"""
        if 0 <= index < len(self._entries):
            del self._entries[index]

    def clear(self):
        """清空所有条目。"""
        self._entries.clear()

    def move_to_top(self, index: int):
        """将指定索引的条目移动到顶部。"""
        if 0 <= index < len(self._entries):
            entry = self._entries.pop(index)
            self._entries.insert(0, entry)

    def get_all(self) -> list:
        """返回所有条目的副本，索引 0 为最新。"""
        return list(self._entries)

    def __len__(self):
        return len(self._entries)
