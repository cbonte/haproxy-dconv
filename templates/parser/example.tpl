<div class="separator">
<span class="badge bg-success">${label}</span>
<pre class="prettyprint">
% if desc:
<div class="example-desc">${desc}</div>\
% endif
<code>\
% for line in content:
${line}
% endfor
</code></pre>
</div>