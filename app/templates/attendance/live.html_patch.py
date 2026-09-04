import re

with open('app/templates/attendance/live.html', 'r') as f:
    content = f.read()

# Find the modals at the end
modals_start = content.find('<!-- UNKNOWN PERSON MODAL -->')
if modals_start != -1:
    modals = content[modals_start:]
    content = content[:modals_start]
    
    # Insert before {% endblock %} of content
    content_endblock = content.find('{% endblock %}')
    content = content[:content_endblock] + modals + '\n' + content[content_endblock:]
    
    with open('app/templates/attendance/live.html', 'w') as f:
        f.write(content)
