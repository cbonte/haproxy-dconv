<% from urllib.parse import quote %>
<% base = pctxt.context['base'] %>
<tr>\
% for col in columns:
<% data = col['data'] %>\
<%
    if data in ['yes']:
        style = "class=\"alert-success pagination-centered\""
        data = 'yes<br /><img src="%scss/check.png" alt="yes" title="yes" />' % base
    elif data in ['yes(!)']:
        style = "class=\"alert-info pagination-centered\""
        data = 'yes(!)<br /><img src="%scss/checkmark.png" alt="yes(!)" title="yes(!)" />' % base
    elif data in ['no']:
        style = "class=\"alert-error pagination-centered\""
        data = 'no<br /><img src="%scss/cross.png" alt="no" title="no" />' % base
    elif data in ['X']:
        style = "class=\"pagination-centered\""
        data = '<img src="%scss/check.png" alt="X" title="yes" />' % base
    elif data in ['X (!)']:
        style = "class=\"pagination-centered\""
        data = '<img src="%scss/checkmark.png" alt="X (!)" title="yes (!)" />' % base
    elif data in ['-']:
        style = "class=\"pagination-centered\""
        data = '&nbsp;'
    elif data in ['*']:
        style = "class=\"pagination-centered\""
    else:
        style = ""
%>\
<td ${style}>\
% if "keyword" in col:
<a href="#${quote("%s-%s" % (col['toplevel'], col['keyword'].split('(')[0]))}">\
% for extra in col['extra']:
<span class="pull-right">${extra}</span>\
% endfor
${data}</a>\
% else:
${data}\
% endif
</td>\
% endfor
</tr>
