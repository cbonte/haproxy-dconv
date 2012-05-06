<div class="separator">
    % if label:
        <span class="label label-success">${label}</span>
    % endif
<pre class="prettyprint">\
% if desc:
<div class="example-desc">${desc}</div>\
% endif
<code>${"\n".join(content)}</code></pre>
</div>