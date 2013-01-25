<% from urllib import quote %>
<tr>\
% for col in columns:
<% data = col['data'] %>\
<%
    if data in ['yes']:
        style = "class=\"alert-success pagination-centered\""
        data = 'yes<br /><img src="css/check.png" alt="yes" title="yes" />'
    elif data in ['no']:
        style = "class=\"alert-error pagination-centered\""
        data = 'no<br /><img src="css/cross.png" alt="no" title="no" />'
    elif data in ['X']:
        style = "class=\"pagination-centered\""
        data = '<img src="css/check.png" alt="X" title="yes" />'
    elif data in ['-']:
        style = "class=\"pagination-centered\""
        data = '&nbsp;'
    elif data in ['*']:
        style = "class=\"pagination-centered\""
    else:
        style = None
%>\
<td ${style}>\
% if "keyword" in col:
<a href="#${quote("%s-%s" % (col['toplevel'], col['keyword']))}">\
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
