import re
import parser

class Parser(parser.Parser):
    def __init__(self, pctxt):
        parser.Parser.__init__(self, pctxt)
        #template = pctxt.templates.get_template("parser/arguments.tpl")
        #self.replace = template.render().strip()

    def parse(self, line):
        #return re.sub(r'(Arguments *:)', self.replace, line)
        pctxt = self.pctxt

        result = re.search(r'(Arguments? *:)', line)
        if result:
            label = result.group(0)

            desc_indent = False
            desc = re.sub(r'.*Arguments? *:', '', line).strip()

            indent = self.get_indent(line)

            pctxt.next()
            pctxt.eat_empty_lines()

            content = []
            add_empty_lines = 0
            while pctxt.has_more_lines() and (self.get_indent(pctxt.get_line()) > indent):
                for i in xrange(0, add_empty_lines):
                    content.append("")
                content.append(pctxt.get_line())
                pctxt.next()
                add_empty_lines = pctxt.eat_empty_lines()

            pctxt.stop = True

            template = pctxt.templates.get_template("parser/arguments.tpl")
            return template.render(
                label=label,
                desc=desc,
                content=content
            )
        return line

