__all__ = [
    'arguments',
    'example',
    'keyword',
    'seealso',
    'table',
    'underline'
]


class Parser:
    def __init__(self, pctxt):
        self.pctxt = pctxt

    def parse(self, line):
        return line

class PContext:
    def __init__(self, templates = None):
        self.set_content_list([])
        self.templates = templates

    def set_content(self, content):
        self.set_content_list(content.split("\n"))

    def set_content_list(self, content):
        self.lines = content
        self.nblines = len(self.lines)
        self.i = 0
        self.stop = False

    def get_lines(self):
        return self.lines

    def eat_lines(self):
        count = 0
        while self.has_more_lines() and self.lines[self.i].strip():
            count += 1
            self.next()
        return count

    def eat_empty_lines(self):
        count = 0
        while self.has_more_lines() and not self.lines[self.i].strip():
            count += 1
            self.next()
        return count

    def next(self, count=1):
        self.i += count

    def has_more_lines(self, offset=0):
        return self.i + offset < self.nblines

    def get_line(self, offset=0):
        return self.lines[self.i + offset].rstrip()


# Get the indentation of a line
def get_indent(line):
        indent = 0
        length = len(line)
        while indent < length and line[indent] == ' ':
            indent += 1
        return indent


# Remove unneeded indentation
def remove_indent(list):
    # Detect the minimum indentation in the list
    min_indent = -1
    for line in list:
        if not line.strip():
            continue
        indent = get_indent(line)
        if min_indent < 0 or indent < min_indent:
            min_indent = indent
    # Realign the list content to remove the minimum indentation
    if min_indent > 0:
        for index, line in enumerate(list):
            list[index] = line[min_indent:]
