import re
import parser

class Parser(parser.Parser):
    def parse(self, line):
        pctxt = self.pctxt

        result = re.search(r'(See also *:)', line)
        if result:
            label = result.group(0)

            desc = re.sub(r'.*See also *:', '', line).strip()

            indent = parser.get_indent(line)

            # Some descriptions are on multiple lines
            while pctxt.has_more_lines(1) and parser.get_indent(pctxt.get_line(1)) >= indent:
                desc += " " + pctxt.get_line(1).strip()
                pctxt.next()

            pctxt.eat_empty_lines()
            pctxt.next()
            pctxt.stop = True

            template = pctxt.templates.get_template("parser/seealso.tpl")
            return template.render(
                pctxt=pctxt,
                label=label,
                desc=desc,
            )

        return line
