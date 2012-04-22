% if title:
<div><p>${title} :</p>\
% endif
<table class="table table-bordered" border="0" cellspacing="0" cellpadding="0">
% for row in rows:
${row}
% endfor
</table>\
% if title:
</div>
% endif