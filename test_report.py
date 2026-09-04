from app.database import SessionLocal
from app.services.report import get_filtered_attendance_data, generate_excel_report

db = SessionLocal()

print("Testing get_filtered_attendance_data without filters...")
data = get_filtered_attendance_data(db)
print(f"Total sessions returned: {len(data)}")

if data:
    s0 = data[0]
    print(f"Session 1: {s0['session'].session_id}, Total: {s0['stats']['total']}, Present: {s0['stats']['present']}")

print("\nTesting generate_excel_report without filters...")
excel_bytes = generate_excel_report(db)
print(f"Excel generated, size: {len(excel_bytes)} bytes")

with open('test_export.xlsx', 'wb') as f:
    f.write(excel_bytes)
    
print("\nTesting generate_excel_report with Present filter...")
filters = {'status': 'Present'}
excel_bytes_filtered = generate_excel_report(db, filters)
print(f"Excel generated with filter, size: {len(excel_bytes_filtered)} bytes")

print("Tests completed successfully!")
