import sys
import re
import parser

'''
TODO: Allow inner data parsing (this will allow to parse the examples provided in an arguments block)
'''
class ArgumentParser(parser.Parser):
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
            content = []

            desc_indent = False
            desc = re.sub(r'.*Arguments? *:', '', line).strip()

            indent = parser.get_indent(line)

            pctxt.next()
            pctxt.eat_empty_lines()

            arglines = []
            if desc != "none":
                add_empty_lines = 0
                while pctxt.has_more_lines() and (parser.get_indent(pctxt.get_line()) > indent):
                    for j in range(0, add_empty_lines):
                        arglines.append("")
                    arglines.append(pctxt.get_line())
                    pctxt.next()
                    add_empty_lines = pctxt.eat_empty_lines()
                    '''
                    print line

                    if parser.get_indent(line) == arg_indent:
                        argument = re.sub(r' *([^ ]+).*', r'\1', line)
                        if argument:
                            #content.append("<b>%s</b>" % argument)
                            arg_desc = [line.replace(argument, " " * len(self.unescape(argument)), 1)]
                            #arg_desc = re.sub(r'( *)([^ ]+)(.*)', r'\1<b>\2</b>\3', line)
                            arg_desc_indent = parser.get_indent(arg_desc[0])
                            arg_desc[0] = arg_desc[0][arg_indent:]
                            pctxt.next()
                            add_empty_lines = 0
                            while pctxt.has_more_lines and parser.get_indent(pctxt.get_line()) >= arg_indent:
                                for i in xrange(0, add_empty_lines):
                                    arg_desc.append("")
                                arg_desc.append(pctxt.get_line()[arg_indent:])
                                pctxt.next()
                                add_empty_lines = pctxt.eat_empty_lines()
                            # TODO : reduce space at the beginnning
                            content.append({
                                'name': argument,
                                'desc': arg_desc
                            })
                    '''

                if arglines:
                    new_arglines = []
                    #content = self.parse_args(arglines)
                    parser.remove_indent(arglines)
                    '''
                    pctxt2 = parser.PContext(pctxt.templates)
                    pctxt2.set_content_list(arglines)
                    while pctxt2.has_more_lines():
                        new_arglines.append(parser.example.Parser(pctxt2).parse(pctxt2.get_line()))
                        pctxt2.next()
                    arglines = new_arglines
                    '''

            pctxt.stop = True

            template = pctxt.templates.get_template("parser/arguments.tpl")
            return template.render(
                pctxt=pctxt,
                label=label,
                desc=desc,
                content=arglines
                #content=content
            )
            return line

        return line

'''
    def parse_args(self, data):
        args = []

        pctxt = parser.PContext()
        pctxt.set_content_list(data)

        while pctxt.has_more_lines():
            line = pctxt.get_line()
            arg_indent = parser.get_indent(line)
            argument = re.sub(r' *([^ ]+).*', r'\1', line)
            if True or argument:
                arg_desc = []
                trailing_desc = line.replace(argument, " " * len(self.unescape(argument)), 1)[arg_indent:]
                if trailing_desc.strip():
                    arg_desc.append(trailing_desc)
                pctxt.next()
                add_empty_lines = 0
                while pctxt.has_more_lines() and parser.get_indent(pctxt.get_line()) > arg_indent:
                    for i in xrange(0, add_empty_lines):
                        arg_desc.append("")
                    arg_desc.append(pctxt.get_line()[arg_indent:])
                    pctxt.next()
                    add_empty_lines = pctxt.eat_empty_lines()

                parser.remove_indent(arg_desc)

                args.append({
                    'name': argument,
                    'desc': arg_desc
                })
        return args

    def unescape(self, s):
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        # this has to be last:
        s = s.replace("&amp;", "&")
        return s
'''
