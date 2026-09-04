import io

with io.open('app/templates/attendance/live.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The file now has modals inside {% endblock %} and also at the very end of the file.
# The very end starts with '<!-- UNKNOWN PERSON MODAL -->'
parts = content.split('{% endblock %}')
if len(parts) >= 3:
    # There are two {% endblock %} strings? No, {% block content %} and {% block scripts %}
    # The last block is {% endblock %} followed by the duplicate modals.
    
    # Actually, we can just split by '{% endblock %}\n<!-- UNKNOWN PERSON MODAL -->' or similar
    pass

# safer: truncate everything after the last {% endblock %}
idx = content.rfind('{% endblock %}')
if idx != -1:
    clean_content = content[:idx + len('{% endblock %}')] + '\n'
    with io.open('app/templates/attendance/live.html', 'w', encoding='utf-8') as f:
        f.write(clean_content)
