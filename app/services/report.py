import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_
from app.models.models import AttendanceSession, AttendanceRecord, Student, Class, Course

def get_filtered_attendance_data(
    db: Session,
    from_date: str = None,
    to_date: str = None,
    session_id: str = None,
    course_id: str = None,
    class_id: str = None,
    student_id: str = None,
    status: str = None,
    recognition_method: str = None,
    liveness_result: str = None
):
    session_id = int(session_id) if session_id else None
    course_id = int(course_id) if course_id else None
    class_id = int(class_id) if class_id else None
    student_id = int(student_id) if student_id else None

    # 1. Filter Sessions
    session_query = select(AttendanceSession).join(Class).join(Course)
    
    if session_id:
        session_query = session_query.where(AttendanceSession.session_id == session_id)
    if from_date:
        session_query = session_query.where(AttendanceSession.session_date >= from_date)
    if to_date:
        session_query = session_query.where(AttendanceSession.session_date <= to_date)
    if course_id:
        session_query = session_query.where(Class.course_id == course_id)
    if class_id:
        session_query = session_query.where(AttendanceSession.class_id == class_id)
        
    session_query = session_query.order_by(AttendanceSession.session_date.desc(), AttendanceSession.session_id.desc())
    sessions = db.scalars(session_query).all()
    
    report_data = []
    
    for s in sessions:
        # 2. Get students for this session's class
        student_query = select(Student).where(Student.class_id == s.class_id, Student.status == 'Active')
        if student_id:
            student_query = student_query.where(Student.student_id == student_id)
        student_query = student_query.order_by(Student.roll_no)
        students_in_class = db.scalars(student_query).all()
        
        if not students_in_class:
            continue
            
        # 3. Get all records for this session
        records = db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.session_id == s.session_id)
        ).all()
        
        # Deduplicate
        record_map = {}
        for r in records:
            if r.attendance_status == 'Present':
                if r.student_id not in record_map:
                    record_map[r.student_id] = r
                else:
                    if r.attendance_id > record_map[r.student_id].attendance_id:
                        record_map[r.student_id] = r
                        
        # 4. Calculate Stats (before row filtering)
        total_enrolled = len(students_in_class)
        present_count = sum(1 for st in students_in_class if st.student_id in record_map)
        absent_count = total_enrolled - present_count
        attendance_pct = (present_count / total_enrolled * 100) if total_enrolled > 0 else 0
        
        # 5. Apply row-level filters and build table data
        table_rows = []
        for st in students_in_class:
            rec = record_map.get(st.student_id)
            
            row_status = "Present" if rec else "Absent"
            row_time = rec.recorded_time if rec else "—"
            row_conf = f"{(rec.recognition_confidence * 100):.1f}%" if rec and rec.recognition_confidence else "—"
            row_live = rec.liveness_result if rec and rec.liveness_result else "—"
            row_method = rec.recognition_method if rec and rec.recognition_method else "—"
            
            # Filters
            if status and status != "All":
                if row_status != status:
                    continue
                    
            if recognition_method and recognition_method != "All":
                if row_method != recognition_method:
                    continue
                    
            if liveness_result and liveness_result != "All":
                if row_live != liveness_result:
                    continue
                    
            table_rows.append({
                "student_id": st.student_id,
                "roll_no": st.roll_no,
                "student_name": f"{st.first_name} {st.last_name}",
                "status": row_status,
                "recorded_time": row_time,
                "confidence": row_conf,
                "liveness": row_live,
                "method": row_method
            })
            
        # Only include session if it has matching rows
        if table_rows:
            report_data.append({
                "session": s,
                "course_name": s.class_.course.course_name,
                "class_name": s.class_.class_name,
                "stats": {
                    "total": total_enrolled,
                    "present": present_count,
                    "absent": absent_count,
                    "pct": round(attendance_pct, 2)
                },
                "rows": table_rows
            })
            
    return report_data

def generate_excel_report(db: Session, filters: dict = None):
    if filters is None:
        filters = {}
        
    report_data = get_filtered_attendance_data(db, **filters)
    
    wb = Workbook()
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="0F2747")
    title_font = Font(bold=True, size=16, color="0F2747")
    subtitle_font = Font(bold=True, size=12)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )

    if not report_data:
        ws = wb.active
        ws.title = "Summary"
        ws.append(["SMART ATTENDANCE"])
        ws.append(["ATTENDANCE REPORT"])
        ws.append([])
        ws.append(["No attendance records found for the selected filters."])
        
        ws['A1'].font = title_font
        ws['A2'].font = subtitle_font
        
        bio = io.BytesIO()
        wb.save(bio)
        return bio.getvalue()

    # --- SHEET 1: SUMMARY ---
    ws_summary = wb.active
    ws_summary.title = "Summary"
    
    ws_summary.append(["SMART ATTENDANCE"])
    ws_summary.append(["ATTENDANCE REPORT SUMMARY"])
    ws_summary.append(["Report Generated On:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    ws_summary.append([])
    
    ws_summary['A1'].font = title_font
    ws_summary['A2'].font = subtitle_font
    
    # Filter info
    ws_summary.append(["Applied Filters:"])
    ws_summary.cell(row=ws_summary.max_row, column=1).font = Font(bold=True)
    for k, v in filters.items():
        if v and v != "All":
            ws_summary.append([k.replace('_', ' ').title() + ":", str(v)])
    ws_summary.append([])
    
    # Overall Stats
    total_sessions = len(report_data)
    total_students_across = sum(d["stats"]["total"] for d in report_data)
    total_present_across = sum(d["stats"]["present"] for d in report_data)
    total_absent_across = sum(d["stats"]["absent"] for d in report_data)
    avg_pct = (total_present_across / total_students_across * 100) if total_students_across > 0 else 0
    
    ws_summary.append(["Overall Statistics:"])
    ws_summary.cell(row=ws_summary.max_row, column=1).font = Font(bold=True)
    ws_summary.append(["Total Sessions:", total_sessions])
    ws_summary.append(["Total Students (Enrolled across sessions):", total_students_across])
    ws_summary.append(["Total Present:", total_present_across])
    ws_summary.append(["Total Absent:", total_absent_across])
    ws_summary.append(["Average Attendance %:", f"{avg_pct:.2f}%"])
    ws_summary.append([])
    
    # Session-wise summary
    summary_headers = ["Session ID", "Date", "Course", "Class", "Total Students", "Present", "Absent", "Attendance %"]
    ws_summary.append(summary_headers)
    
    summary_header_row = ws_summary.max_row
    for col, h in enumerate(summary_headers, 1):
        cell = ws_summary.cell(row=summary_header_row, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border
        
    for d in report_data:
        s = d["session"]
        stats = d["stats"]
        row = [
            s.session_id, 
            s.session_date, 
            d["course_name"], 
            d["class_name"], 
            stats["total"], 
            stats["present"], 
            stats["absent"], 
            f"{stats['pct']}%"
        ]
        ws_summary.append(row)
        current_row = ws_summary.max_row
        for col in range(1, len(row) + 1):
            cell = ws_summary.cell(row=current_row, column=col)
            cell.border = border
            cell.alignment = center_align if col not in [3, 4] else left_align
            
    for col, width in zip("ABCDEFGH", [12, 15, 25, 15, 15, 12, 12, 15]):
        ws_summary.column_dimensions[col].width = width

    # --- SHEET 2 ONWARD: INDIVIDUAL SESSIONS ---
    for d in report_data:
        s = d["session"]
        safe_title = f"Session_{s.session_id}"
        # Max sheet name length is 31
        ws = wb.create_sheet(title=safe_title[:31])
        
        ws.append(["SESSION DETAILS"])
        ws['A1'].font = title_font
        ws.append([])
        
        ws.append(["Session ID:", s.session_id])
        ws.append(["Date:", s.session_date])
        ws.append(["Course:", d["course_name"]])
        ws.append(["Class:", d["class_name"]])
        ws.append(["Total Enrolled:", d["stats"]["total"]])
        ws.append(["Present:", d["stats"]["present"]])
        ws.append(["Absent:", d["stats"]["absent"]])
        ws.append(["Attendance %:", f"{d['stats']['pct']}%"])
        ws.append([])
        
        for r in range(3, 11):
            ws.cell(row=r, column=1).font = Font(bold=True)
            
        headers = ["Roll No", "Student Name", "Status", "Recorded Time", "Confidence", "Liveness", "Method"]
        ws.append(headers)
        
        header_row = 12
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
            
        ws.freeze_panes = ws['A13']
        ws.auto_filter.ref = f"A12:G12"
        
        for r_data in d["rows"]:
            row = [
                r_data["roll_no"],
                r_data["student_name"],
                r_data["status"],
                r_data["recorded_time"],
                r_data["confidence"],
                r_data["liveness"],
                r_data["method"]
            ]
            ws.append(row)
            current_row = ws.max_row
            for col in range(1, len(row) + 1):
                cell = ws.cell(row=current_row, column=col)
                cell.border = border
                cell.alignment = center_align if col not in [2] else left_align
                
        for col, width in zip("ABCDEFG", [15, 25, 15, 15, 15, 15, 20]):
            ws.column_dimensions[col].width = width

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
