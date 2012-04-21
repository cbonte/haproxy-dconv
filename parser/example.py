import re
import parser

class Parser(parser.Parser):
    def parse(self, line):
        pctxt = self.pctxt
        res = ""
        if re.search(r'Examples? *:', line):
            # Detect examples blocks
            desc_indent = False
            desc = re.sub(r'.*Examples? *:', '', line).strip()

            # Some examples have a description
            if desc:
                desc_indent = len(line) - len(desc)

            line = re.sub(r'(Examples? *:)', r'<span class="label label-success">\1</span>', line)
            indent = self.get_indent(line)

            if desc:
                res += line[:len(line) - len(desc)]
                # And some description are on multiple lines
                while pctxt.get_line(1) and self.get_indent(pctxt.get_line(1)) == desc_indent:
                    desc += " " + pctxt.get_line(1).strip()
                    pctxt.next()
            else:
                res += line

            pctxt.next()
            add_empty_line = pctxt.eat_empty_lines()

            if self.get_indent(pctxt.get_line()) > indent:
                res += '<pre class="prettyprint">'
                if desc:
                    desc = desc[0].upper() + desc[1:]
                    res += '<div class="example-desc">%s</div>' % desc
                add_empty_line = 0
                while pctxt.has_more_lines() and ((not pctxt.get_line()) or (self.get_indent(pctxt.get_line()) > indent)):
                    if pctxt.get_line():
                        for j in xrange(0, add_empty_line):
                            res += "\n"
                        line = re.sub(r'(#.*)$', r'<span class="comment">\1</span>', pctxt.get_line())
                        res += line + '\n'
                        add_empty_line = 0
                    else:
                        add_empty_line += 1
                    pctxt.next()
                res += "</pre>"
            elif self.get_indent(pctxt.get_line()) == indent:
                # Simple example that can't have empty lines
                res += '<pre class="prettyprint">'
                if add_empty_line:
                        # This means that the example was on the same line as the 'Example' tag
                    res += " " * indent + desc
                else:
                    while pctxt.has_more_lines() and (self.get_indent(pctxt.get_line()) == indent):
                        res += pctxt.get_line()
                        pctxt.next()
                    pctxt.eat_empty_lines() # Skip empty remaining lines
                res += "</pre>"
            pctxt.stop = True
        else:
            res = line
        return res

    def get_indent(self, line):
        indent = 0
        length = len(line)
        while indent < length and line[indent] == ' ':
            indent += 1
        return indent

