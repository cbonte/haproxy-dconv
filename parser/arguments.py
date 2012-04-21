import re

class Parser:
    def parse(self, pctxt, line):
        line = re.sub(r'(Arguments :)', r'<span class="label label-info">\1</span>', line)
        return line
