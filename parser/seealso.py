import re

class Parser:
    def parse(self, pctxt, line):
        line = re.sub(r'(See also *:)', r'<span class="label label-see-also">\1</span>', line)
        return line
