import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import AttendanceSession, AttendanceRecord, Student

def generate_excel_report(db: Session, session_id: int = None):
    # Retrieve sessions to export
    if session_id:
        sessions = db.scalars(select(AttendanceSession).where(AttendanceSession.session_id == session_id)).all()
    else:
        sessions = db.scalars(select(AttendanceSession).order_by(AttendanceSession.session_date.desc(), AttendanceSession.session_id.desc())).all()

    wb = Workbook()
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="0F2747")  # Navy color matching UI
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

    if not sessions:
        ws = wb.active
        ws.title = "Attendance Report"
        ws.append(["SMART ATTENDANCE"])
        ws.append(["ATTENDANCE REPORT"])
        ws.append([])
        ws.append(["No attendance data available."])
        
        ws['A1'].font = title_font
        ws['A2'].font = subtitle_font
        
        bio = io.BytesIO()
        wb.save(bio)
        return bio.getvalue()

    if len(sessions) == 1:
        s = sessions[0]
        ws = wb.active
        ws.title = "Attendance Report"
        
        # Title section
        ws.append(["SMART ATTENDANCE"])
        ws.append(["ATTENDANCE REPORT"])
        ws.append([])
        
        ws['A1'].font = title_font
        ws['A2'].font = subtitle_font
        
        # Class info
        ws.append(["Class:", s.class_.class_name])
        ws.append(["Course:", s.class_.course.course_name])
        ws.append(["Academic Year:", s.class_.academic_year or "—"])
        ws.append(["Semester:", s.class_.semester or "—"])
        ws.append(["Date:", s.session_date])
        ws.append([])
        
        for r in range(4, 9):
            ws.cell(row=r, column=1).font = Font(bold=True)
            
        # Calculate attendance
        students_in_class = db.scalars(
            select(Student).where(Student.class_id == s.class_id, Student.status == 'Active').order_by(Student.roll_no)
        ).all()
        
        records = db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.session_id == s.session_id)
        ).all()
        
        # Deduplicate records by student_id, preferring the latest recorded_time or ID (highest ID)
        record_map = {}
        for r in records:
            if r.attendance_status == 'Present':
                if r.student_id not in record_map:
                    record_map[r.student_id] = r
                else:
                    if r.attendance_id > record_map[r.student_id].attendance_id:
                        record_map[r.student_id] = r
        
        total_students = len(students_in_class)
        # Ensure we only count students that are registered and active
        present_count = 0
        for st in students_in_class:
            if st.student_id in record_map:
                present_count += 1
                
        present_students = min(present_count, total_students)
        absent_students = max(total_students - present_students, 0)
        pct = (present_students / total_students * 100) if total_students > 0 else 0
        
        # Summary
        ws.append(["Total Students:", total_students])
        ws.append(["Present:", present_students])
        ws.append(["Absent:", absent_students])
        ws.append(["Attendance %:", f"{pct:.2f}%"])
        ws.append([])
        
        for r in range(10, 14):
            ws.cell(row=r, column=1).font = Font(bold=True)
            
        # Table Header
        headers = ["S.No.", "Roll No.", "Student Name", "Date", "Status", "Time", "Confidence", "Liveness"]
        ws.append(headers)
        
        header_row = 15
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
            
        ws.freeze_panes = ws['A16']
        ws.auto_filter.ref = "A15:H15"

        data_row = 16
        for i, st in enumerate(students_in_class, 1):
            rec = record_map.get(st.student_id)
            
            sno = i
            roll = st.roll_no
            name = f"{st.first_name} {st.last_name}"
            date_val = s.session_date
            
            if rec:
                status = "Present"
                time_val = rec.recorded_time
                conf = f"{(rec.recognition_confidence * 100):.1f}%" if rec.recognition_confidence else "—"
                live = rec.liveness_result or "—"
            else:
                status = "Absent"
                time_val = "—"
                conf = "—"
                live = "—"
                
            row_data = [sno, roll, name, date_val, status, time_val, conf, live]
            ws.append(row_data)
            
            for col, val in enumerate(row_data, 1):
                cell = ws.cell(row=data_row, column=col)
                cell.border = border
                if col in [1, 4, 5, 6, 7, 8]:
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align
            data_row += 1

        # Auto-adjust column widths
        column_widths = {'A': 8, 'B': 18, 'C': 25, 'D': 15, 'E': 12, 'F': 12, 'G': 15, 'H': 15}
        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

    else:
        # Multiple Sessions logic
        ws_summary = wb.active
        ws_summary.title = "Daily Summary"
        ws_details = wb.create_sheet(title="Attendance Details")
        
        # Summary Header
        ws_summary.append(["SMART ATTENDANCE"])
        ws_summary.append(["DAILY SUMMARY"])
        ws_summary.append([])
        
        ws_summary['A1'].font = title_font
        ws_summary['A2'].font = subtitle_font
        
        summary_headers = ["Date", "Class", "Course", "Total Students", "Present", "Absent", "Attendance %"]
        ws_summary.append(summary_headers)
        
        summary_header_row = 4
        for col, h in enumerate(summary_headers, 1):
            cell = ws_summary.cell(row=summary_header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        ws_summary.freeze_panes = ws_summary['A5']
        ws_summary.auto_filter.ref = "A4:G4"
        
        # Details Header
        details_headers = ["S.No.", "Class", "Roll No.", "Student Name", "Date", "Status", "Time", "Confidence", "Liveness"]
        ws_details.append(["SMART ATTENDANCE"])
        ws_details.append(["ATTENDANCE DETAILS"])
        ws_details.append([])
        ws_details['A1'].font = title_font
        ws_details['A2'].font = subtitle_font
        
        ws_details.append(details_headers)
        details_header_row = 4
        for col, h in enumerate(details_headers, 1):
            cell = ws_details.cell(row=details_header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        ws_details.freeze_panes = ws_details['A5']
        ws_details.auto_filter.ref = "A4:I4"
        
        summary_data_row = 5
        details_data_row = 5
        
        s_no = 1
        for s in sessions:
            students_in_class = db.scalars(
                select(Student).where(Student.class_id == s.class_id, Student.status == 'Active').order_by(Student.roll_no)
            ).all()
            
            records = db.scalars(
                select(AttendanceRecord).where(AttendanceRecord.session_id == s.session_id)
            ).all()
            
            record_map = {}
            for r in records:
                if r.attendance_status == 'Present':
                    if r.student_id not in record_map:
                        record_map[r.student_id] = r
                    else:
                        if r.attendance_id > record_map[r.student_id].attendance_id:
                            record_map[r.student_id] = r
            
            total_students = len(students_in_class)
            present_count = 0
            for st in students_in_class:
                if st.student_id in record_map:
                    present_count += 1
            
            present_students = min(present_count, total_students)
            absent_students = max(total_students - present_students, 0)
            pct = (present_students / total_students * 100) if total_students > 0 else 0
            
            # Write Summary Row
            s_row = [s.session_date, s.class_.class_name, s.class_.course.course_name, total_students, present_students, absent_students, f"{pct:.2f}%"]
            ws_summary.append(s_row)
            for col, val in enumerate(s_row, 1):
                cell = ws_summary.cell(row=summary_data_row, column=col)
                cell.border = border
                if col in [1, 4, 5, 6, 7]:
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align
            summary_data_row += 1
            
            # Write Details Rows
            for st in students_in_class:
                rec = record_map.get(st.student_id)
                roll = st.roll_no
                name = f"{st.first_name} {st.last_name}"
                date_val = s.session_date
                class_name = s.class_.class_name
                
                if rec:
                    status = "Present"
                    time_val = rec.recorded_time
                    conf = f"{(rec.recognition_confidence * 100):.1f}%" if rec.recognition_confidence else "—"
                    live = rec.liveness_result or "—"
                else:
                    status = "Absent"
                    time_val = "—"
                    conf = "—"
                    live = "—"
                    
                d_row = [s_no, class_name, roll, name, date_val, status, time_val, conf, live]
                ws_details.append(d_row)
                for col, val in enumerate(d_row, 1):
                    cell = ws_details.cell(row=details_data_row, column=col)
                    cell.border = border
                    if col in [1, 5, 6, 7, 8, 9]:
                        cell.alignment = center_align
                    else:
                        cell.alignment = left_align
                details_data_row += 1
                s_no += 1
                
        # Auto-adjust column widths
        summary_widths = {'A': 15, 'B': 20, 'C': 30, 'D': 15, 'E': 10, 'F': 10, 'G': 15}
        for col, width in summary_widths.items():
            ws_summary.column_dimensions[col].width = width
            
        details_widths = {'A': 8, 'B': 20, 'C': 18, 'D': 25, 'E': 15, 'F': 12, 'G': 12, 'H': 15, 'I': 15}
        for col, width in details_widths.items():
            ws_details.column_dimensions[col].width = width

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
