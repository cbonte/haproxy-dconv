import re
import parser

class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        template = pctxt.templates.get_template("parser/arguments.tpl")
        self.replace = template.render().strip()

    def parse(self, line):
        return re.sub(r'(Arguments :)', self.replace, line)
