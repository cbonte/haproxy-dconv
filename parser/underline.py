import parser

class Parser(parser.Parser):
    # Detect underlines
    def parse(self, line):
        pctxt = self.pctxt
        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
            if (len(line) > 0) and (len(nextline) > 0) and (nextline[0] == '-') and ("-" * len(line) == nextline):
                template = pctxt.templates.get_template("parser/underline.tpl")
                line = template.render(pctxt=pctxt, data=line).strip()
                pctxt.next(2)
                pctxt.eat_empty_lines()
                pctxt.stop = True

        return line
