class Parser:
    def parse(self, pctxt, line):
        if pctxt.has_more_lines(1):
            nextline = pctxt.get_line(1)
            if (len(line) > 0) and (len(nextline) > 0) and (nextline[0] == '-') and ("-" * len(line) == nextline):
                # Detect underlines
                line = '<h5>%s</h5>' % line
                pctxt.next(2)
                pctxt.eat_empty_lines()
                pctxt.stop = True

        return line
