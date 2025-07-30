import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz
import os
import io
import base64
import xlsxwriter
from behavior_tracker import BehaviorTracker
from data_manager import DataManager

# Initialize session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'selected_student' not in st.session_state:
    st.session_state.selected_student = None
if 'students_df' not in st.session_state: # This will now be derived from data_manager
    st.session_state.students_df = None
if 'behavior_tracker' not in st.session_state:
    st.session_state.behavior_tracker = BehaviorTracker()
if 'speed_mode_active' not in st.session_state:
    st.session_state.speed_mode_active = False
if 'record_previous_date_active' not in st.session_state:
    st.session_state.record_previous_date_active = False
if 'persistent_date' not in st.session_state:
    st.session_state.persistent_date = None
if 'show_export_dialog' not in st.session_state:
    st.session_state.show_export_dialog = False
if 'show_print_dialog' not in st.session_state:
    st.session_state.show_print_dialog = False


def generate_excel_report(start_date, end_date):
    """Generates an Excel report for all students within a date range."""
    all_data = st.session_state.data_manager.get_all_behavior_data()
    students_df = st.session_state.students_df
    if all_data is None or students_df is None or all_data.empty:
        return None

    try:
        all_data['date'] = pd.to_datetime(all_data['date']).dt.date
        mask = (all_data['date'] >= start_date) & (all_data['date'] <= end_date)
        filtered_data = all_data.loc[mask]
    except Exception as e:
        st.error(f"Error filtering data: {e}")
        return None

    if filtered_data.empty:
        return None

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Behavior Report")

    # --- Formatting ---
    title_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
    cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})

    # --- Write Titles and Headers ---
    worksheet.merge_range('A1:E1', 'Behavior Report', title_format)
    date_range_str = f"Date Range: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}"
    worksheet.merge_range('A2:E2', date_range_str, workbook.add_format({'align': 'center'}))

    headers = ["Student Name", "Good Points", "Bad Points", "Good Behavior %", "Days Recorded"]
    worksheet.write_row('A4', headers, header_format)
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:E', 15)

    # --- Write Data for Each Student ---
    row_num = 4
    for student_name in students_df['name']:
        student_data = filtered_data[filtered_data['student'] == student_name]

        worksheet.write(row_num, 0, student_name, cell_format)

        if student_data.empty:
            worksheet.merge_range(row_num, 1, row_num, 4, "No data for this period", cell_format)
            row_num += 1
            continue

        points_summary = st.session_state.behavior_tracker.calculate_points_summary(student_data)
        
        worksheet.write(row_num, 1, points_summary['total_good_points'], cell_format)
        worksheet.write(row_num, 2, points_summary['total_bad_points'], cell_format)
        worksheet.write(row_num, 3, f"{points_summary['good_percentage']}%", cell_format)
        worksheet.write(row_num, 4, points_summary['days_recorded'], cell_format)

        row_num += 1

    workbook.close()
    return output.getvalue()


def generate_printable_html(student_list):
    """Generates a rich, interactive HTML report that opens in a new tab."""
    
    all_student_html = ""
    for student_name in student_list:
        student_data = st.session_state.data_manager.get_student_behavior_data(student_name)
        
        pie_chart_html = "<h4>Behavior Distribution</h4><p>No data to display.</p>"
        bar_chart_html = "<h4>Behavior Percentages</h4><p>No data to display.</p>"
        timeline_html = "<h4>Recent Behavior</h4><p>No data to display.</p>"

        if not student_data.empty:
            colors = st.session_state.behavior_tracker.get_color_options()
            color_names = list(colors.keys())
            color_counts = student_data['color'].value_counts()
            total_entries = len(student_data)
            percentages = {color: (color_counts.get(color, 0) / total_entries) * 100 for color in color_names}

            # --- Generate Pie Chart ---
            fig_pie = px.pie(values=list(percentages.values()), names=color_names, color=color_names, color_discrete_map=colors)
            fig_pie.update_layout(showlegend=False, width=300, height=300, margin=dict(l=10, r=10, t=10, b=10))
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            pie_chart_html = f"<h4>Behavior Distribution</h4>{fig_pie.to_html(full_html=False, include_plotlyjs='cdn')}"

            # --- Generate Bar Chart ---
            fig_bar = px.bar(x=color_names, y=[percentages[c] for c in color_names], color=color_names, color_discrete_map=colors)
            fig_bar.update_layout(showlegend=False, width=300, height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Percentage (%)")
            bar_chart_html = f"<h4>Behavior Percentages</h4>{fig_bar.to_html(full_html=False, include_plotlyjs='cdn')}"

            # --- Generate Timeline Chart ---
            recent_data = student_data.sort_values('date', ascending=False).head(10)
            fig_timeline = go.Figure()
            if not recent_data.empty:
                min_date = recent_data['date'].min()
                for color in color_names:
                    fig_timeline.add_trace(go.Scatter(x=[min_date], y=[color], mode='markers', marker=dict(size=0, opacity=0), showlegend=False))
                for _, row in recent_data.iterrows():
                    fig_timeline.add_trace(go.Scatter(x=[row['date']], y=[row['color']], mode='markers', marker=dict(size=15, color=colors[row['color']], line=dict(width=2, color='black')), name=row['color'], showlegend=False))
            fig_timeline.update_layout(width=650, height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(categoryorder='array', categoryarray=color_names), xaxis_title="Date")
            timeline_html = f"<h4>Recent Behavior Timeline</h4>{fig_timeline.to_html(full_html=False, include_plotlyjs='cdn')}"

        points_summary = st.session_state.behavior_tracker.calculate_points_summary(student_data)
        
        all_student_html += f"""
        <div class="student-report">
            <h2>{student_name}</h2>
            <div class="top-row">
                <div class="summary-table">
                    <h4>Point System Summary</h4>
                    <table>
                        <tr><th>Category</th><th>Value</th></tr>
                        <tr><td>Good Points</td><td>{points_summary['total_good_points']}</td></tr>
                        <tr><td>Bad Points</td><td>{points_summary['total_bad_points']}</td></tr>
                        <tr><td>Good Behavior %</td><td>{points_summary['good_percentage']}%</td></tr>
                        <tr><td>Days Recorded</td><td>{points_summary['days_recorded']}</td></tr>
                    </table>
                </div>
                <div class="chart-cell">{pie_chart_html}</div>
            </div>
            <div class="bottom-row">
                <div class="chart-cell">{bar_chart_html}</div>
                <div class="chart-cell timeline">{timeline_html}</div>
            </div>
        </div>
        """

    full_html = f"""
    <html><head><title>Behavior Report</title><style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
        body {{ font-family: 'Poppins', sans-serif; padding: 20px; }}
        .student-report {{ page-break-inside: avoid; border: 1px solid #ccc; border-radius: 10px; padding: 15px; margin-bottom: 20px; }}
        h1 {{ text-align: center; }} h2 {{ border-bottom: 2px solid #eee; padding-bottom: 5px; }} h4 {{ text-align: center; margin-top: 0; }}
        .top-row, .bottom-row {{ display: flex; align-items: center; justify-content: space-around; margin-bottom: 15px; }}
        .summary-table, .chart-cell {{ flex: 1; padding: 10px; text-align: center; }}
        .chart-cell.timeline {{ flex: 2; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style></head><body>
        <h1>Behavior Report</h1>
        {all_student_html}
    </body></html>
    """
    return full_html


def main():
    st.set_page_config(page_title="Mrs. Joyner's Class",
                       page_icon="📚",
                       layout="wide",
                       initial_sidebar_state="expanded")

    # --- STYLING BLOCK FOR HEADER AND BUTTONS ---
    colors = st.session_state.behavior_tracker.get_color_options()
    style_css = """
    <style>
        /* Light Mode Banner Styles */
        .stripe-banner {
            background-color: #FFFFFF;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            border: 1px solid #E0E0E0;
        }
        .stripe-title {
            font-size: 2.8em;
            font-weight: bold;
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }

        /* Dark Mode Banner Styles */
        body[data-theme="dark"] .stripe-banner {
            background-color: #262730; /* Streamlit's dark background */
            border: 1px solid #444;
        }
        body[data-theme="dark"] .stripe-title {
            color: #FAFAFA; /* Light text for dark mode */
        }

        /* Common Banner Elements */
        .color-stripe {
            display: flex;
            height: 15px;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
        }
        .color-box {
            flex-grow: 1;
        }
    </style>
    """
    st.markdown(style_css, unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.header("Class Data")
    uploaded_file = st.sidebar.file_uploader(
        "Upload Roster or Data File",
        type=['csv', 'xlsx', 'xls'])

    if uploaded_file is not None:
        # Load data only once when a new file is uploaded
        if 'loaded_file_id' not in st.session_state or st.session_state.loaded_file_id != uploaded_file.id:
            success, message = st.session_state.data_manager.load_data_from_file(uploaded_file)
            if success:
                st.session_state.students_df = pd.DataFrame({'name': st.session_state.data_manager.get_student_list()})
                st.session_state.selected_student = st.session_state.students_df['name'].iloc[0]
                st.session_state.loaded_file_id = uploaded_file.id
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)
                st.stop()
    
    # --- SAVE & DOWNLOAD BUTTON ---
    if st.session_state.data_manager.behavior_data is not None:
        st.sidebar.markdown("---")
        st.sidebar.header("Save Session Data")
        
        download_data = st.session_state.data_manager.get_data_for_download()
        
        if download_data:
            # Generate a dynamic filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.sidebar.download_button(
                label="Save & Download Data",
                data=download_data,
                file_name=f"behavior_data_{timestamp}.csv",
                mime="text/csv",
                help="Download all current data to a new CSV file. Upload this file next time to continue."
            )

    # --- MAIN APP ---
    # Show header only if data is loaded
    if st.session_state.data_manager.behavior_data is not None:
        color_boxes_html = "".join([
            f'<div class="color-box" style="background-color: {hex_code};"></div>'
            for hex_code in colors.values()
        ])
        st.markdown(f"""
            <div class="stripe-banner">
                <div class="stripe-title">Mrs. Joyner's Class</div>
                <div class="color-stripe">
                    {color_boxes_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Speed Entry Button
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        _, col_btn = st.columns([0.8, 0.2])
        with col_btn:
            if st.session_state.speed_mode_active:
                if st.button("Back to Home Page", use_container_width=True, type="primary"):
                    st.session_state.speed_mode_active = False
                    st.rerun()
            else:
                if st.button("Enter Today's Data", use_container_width=True, type="primary"):
                    st.session_state.speed_entry_index = 0
                    st.session_state.speed_mode_active = True
                    st.rerun()
    
    # --- RENDER MAIN CONTENT ---
    if st.session_state.data_manager.behavior_data is None:
        st.info("Welcome! Please upload a class roster or a previously saved data file to begin.")
        st.stop()
    
    if st.session_state.get('speed_mode_active', False):
        # --- SPEED MODE VIEW ---
        from zoneinfo import ZoneInfo
        students = st.session_state.students_df['name'].tolist()
        
        if "speed_entry_index" not in st.session_state:
            st.session_state.speed_entry_index = 0

        if st.session_state.speed_entry_index >= len(students):
            st.success("All students logged for today!")
            if st.button("Start Over"):
                st.session_state.speed_entry_index = 0
                st.rerun()
            st.stop()

        current_student = students[st.session_state.speed_entry_index]
        st.subheader(f"Log behavior for: {current_student}")

        current_date = datetime.now(ZoneInfo("America/Chicago")).date()
        date_str = current_date.strftime("%Y-%m-%d")
        date_display = current_date.strftime("%m/%d/%Y")
        st.markdown(f"**Recording for:** {date_display}")

        cols = st.columns(len(colors))
        for i, color in enumerate(colors.keys()):
            with cols[i]:
                if st.button(color, key=f"speed_color_{color}_{current_student}", use_container_width=True):
                    st.session_state.data_manager.add_behavior_entry(current_student, color, date_str)
                    st.session_state.speed_entry_index += 1
                    st.rerun()

        st.markdown("###")
        if st.button("Skip Student"):
            st.session_state.speed_entry_index += 1
            st.rerun()
    else:
        # --- DASHBOARD VIEW ---
        col1, spacer, col2 = st.columns([1, 0.2, 3])
        with col1:
            st.header("Student Roster")
            for student in st.session_state.students_df['name']:
                if st.button(student, key=f"btn_{student}", use_container_width=True):
                    st.session_state.selected_student = student
                    st.rerun()
        with col2:
            if st.session_state.selected_student:
                display_student_details(st.session_state.selected_student)
            else:
                st.info("👈 Select a student to view their data.")


def display_student_details(student_name):
    st.header(f"{student_name}")

    # Behavior entry section
    st.subheader("Record Behavior")

    colors = st.session_state.behavior_tracker.get_color_options()
    color_names = list(colors.keys())

    chicago_tz = pytz.timezone('America/Chicago')
    current_date_chicago = datetime.now(chicago_tz).date()

    if st.session_state.persistent_date is None:
        st.session_state.persistent_date = current_date_chicago

    st.session_state.record_previous_date_active = st.checkbox(
        "Record behavior for previous date?",
        value=st.session_state.record_previous_date_active
    )

    if st.session_state.record_previous_date_active:
        selected_date = st.date_input("Select date:", value=st.session_state.persistent_date, max_value=current_date_chicago, format="MM/DD/YYYY")
        st.session_state.persistent_date = selected_date
    else:
        selected_date = current_date_chicago
        st.session_state.persistent_date = current_date_chicago

    date_display = selected_date.strftime("%m/%d/%Y")
    st.write(f"**Recording for:** {date_display}")

    cols = st.columns(7)
    for i, color in enumerate(color_names):
        with cols[i]:
            if st.button(color, key=f"color_{color}_{student_name}", use_container_width=True):
                st.session_state.data_manager.add_behavior_entry(student_name, color, selected_date.strftime("%Y-%m-%d"))
                st.rerun()

    student_data = st.session_state.data_manager.get_student_behavior_data(student_name)

    if not student_data.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Behavior Distribution")
            fig_pie = px.pie(student_data, values=student_data['color'].value_counts().values, names=student_data['color'].value_counts().index, color=student_data['color'].value_counts().index, color_discrete_map=colors)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            st.subheader("Behavior Percentages")
            percentages = student_data['color'].value_counts(normalize=True) * 100
            fig_bar = px.bar(percentages, x=percentages.index, y=percentages.values, color=percentages.index, color_discrete_map=colors, labels={'x': 'Behavior Color', 'y': 'Percentage (%)'})
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Point System Distribution")
        points_summary = st.session_state.behavior_tracker.calculate_points_summary(student_data)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Good Points", points_summary['total_good_points'])
        c2.metric("Bad Points", points_summary['total_bad_points'])
        c3.metric("Good Behavior %", f"{points_summary['good_percentage']}%")
        c4.metric("Days Recorded", points_summary['days_recorded'])

        st.write("")
        st.subheader("Recent Behavior Timeline")
        recent_data = student_data.sort_values('date', ascending=False).head(10)
        if not recent_data.empty:
            fig_timeline = go.Figure()
            for color in color_names:
                fig_timeline.add_trace(go.Scatter(x=recent_data['date'], y=[color]*len(recent_data), mode='markers', marker=dict(size=0, opacity=0), showlegend=False))
            for _, row in recent_data.iterrows():
                fig_timeline.add_trace(go.Scatter(x=[row['date']], y=[row['color']], mode='markers', marker=dict(size=15, color=colors[row['color']], line=dict(width=2, color='black')), name=row['color'], showlegend=False))
            fig_timeline.update_layout(xaxis_title="Date", yaxis_title="Behavior Color", xaxis=dict(tickformat='%m/%d'), yaxis=dict(categoryorder='array', categoryarray=color_names))
            st.plotly_chart(fig_timeline, use_container_width=True)

        # --- ACTION BUTTONS ---
        st.write("")
        st.write("")
        export_col, print_col, clear_col = st.columns([0.4, 0.4, 0.2])
        with export_col:
            if st.button("Export Behavior Data"):
                st.session_state.show_export_dialog = True
                st.rerun()
        with print_col:
            if st.button("Print Behavior Data"):
                st.session_state.show_print_dialog = True
                st.rerun()
        with clear_col:
            if st.button("Clear Behavior Data", key=f"clear_link_{student_name}"):
                st.session_state[f'show_clear_dialog_{student_name}'] = True

        # --- DIALOGS ---
        handle_dialogs(student_name)
    else:
        st.info("No behavior data recorded for this student yet.")


def handle_dialogs(student_name):
    chicago_tz = pytz.timezone('America/Chicago')
    # --- PRINT DIALOG ---
    if st.session_state.show_print_dialog:
        with st.form("print_form"):
            st.markdown("---")
            st.markdown("#### Print Behavior Report")
            print_option = st.radio("Select which students to print:", (f"Only {student_name}", "All Students"), key="print_radio")
            submitted = st.form_submit_button("Generate & Open Report")
            if submitted:
                student_list = [student_name] if print_option == f"Only {student_name}" else st.session_state.students_df['name'].tolist()
                with st.spinner("Generating report..."):
                    report_html = generate_printable_html(student_list)
                    b64_html = base64.b64encode(report_html.encode()).decode()
                    link = f'<a href="data:text/html;base64,{b64_html}" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Click Here to Open Printable Report in New Tab</a>'
                    st.markdown(link, unsafe_allow_html=True)
                    st.success("Your report is ready!")
        if st.button("Close Print View"):
            st.session_state.show_print_dialog = False
            st.rerun()

    # --- EXPORT DIALOG ---
    if st.session_state.show_export_dialog:
        with st.form("export_form"):
            st.markdown("---")
            st.markdown("#### Export Class Report")
            today = datetime.now(chicago_tz).date()
            default_start = today - pd.Timedelta(days=30)
            date_range = st.date_input("Select date range for report:", value=(default_start, today), max_value=today, format="MM/DD/YYYY")
            submitted = st.form_submit_button("Generate Report File")
            if submitted:
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    if start_date > end_date:
                        st.error("Error: Start date cannot be after end date.")
                    else:
                        with st.spinner("Generating report..."):
                            report_bytes = generate_excel_report(start_date, end_date)
                            if report_bytes:
                                st.session_state.report_to_download = {"data": report_bytes, "name": f"behavior_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.xlsx"}
                            else:
                                st.warning("No data found in the selected date range.")
                else:
                    st.warning("Please select a valid date range.")
        if 'report_to_download' in st.session_state:
            st.download_button(label="Click to Download Report", data=st.session_state.report_to_download['data'], file_name=st.session_state.report_to_download['name'], mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        if st.button("Close Export View"):
            st.session_state.show_export_dialog = False
            if 'report_to_download' in st.session_state:
                del st.session_state.report_to_download
            st.rerun()

    # --- CLEAR DATA DIALOG ---
    if st.session_state.get(f'show_clear_dialog_{student_name}', False):
        with st.container():
            st.markdown("---")
            st.markdown("**Clear Behavior Data**")
            clear_option = st.radio("Choose what to clear:", (f"Only {student_name}", "All students"), key=f"clear_radio_{student_name}")
            password = st.text_input("Enter password to confirm:", type="password", key=f"clear_password_{student_name}")
            c1, c2 = st.columns(2)
            if c1.button("Clear Data", type="primary", key=f"confirm_clear_{student_name}"):
                if password == "MRSJOYNER":
                    if clear_option == f"Only {student_name}":
                        if st.session_state.data_manager.clear_student_data(student_name):
                            st.success(f"All behavior data cleared for {student_name}")
                            st.session_state[f'show_clear_dialog_{student_name}'] = False
                            st.rerun()
                    else:
                        if st.session_state.data_manager.clear_all_data():
                            st.success("All behavior data cleared for all students")
                            st.session_state[f'show_clear_dialog_{student_name}'] = False
                            st.rerun()
                else:
                    st.error("Incorrect password")
            if c2.button("Cancel", key=f"cancel_clear_{student_name}"):
                st.session_state[f'show_clear_dialog_{student_name}'] = False
                st.rerun()

if __name__ == "__main__":
    main()
