import re
import parser

class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        template = pctxt.templates.get_template("parser/seealso.tpl")
        self.replace = template.render().strip()

    def parse(self, line):
        return re.sub(r'(See also *:)', self.replace, line)
