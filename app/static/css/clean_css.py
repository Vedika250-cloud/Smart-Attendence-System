import io

with io.open('app/static/css/app.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the first occurrence of the Polish block
idx = content.find('/* =========================================================\n   UI/CSS POLISH OVERRIDES (Modernization)')
if idx == -1:
    idx = content.find('/* =========================================================\n   UI/CSS POLISH')

if idx != -1:
    clean_content = content[:idx]
    
    with io.open('app/static/css/polish.css', 'r', encoding='utf-8') as f2:
        polish = f2.read()
        
    with io.open('app/static/css/app.css', 'w', encoding='utf-8') as f:
        f.write(clean_content + polish)
