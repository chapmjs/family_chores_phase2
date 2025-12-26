"""
Family Chores App - Phase 2
Full-featured application with recurring chores, reporting, and parental review
"""

import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, date, timedelta
import os
from PIL import Image
import io
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Family Chores Tracker - Pro",
    page_icon="🏠",
    layout="wide"
)

# Session state initialization
if 'user_role' not in st.session_state:
    st.session_state.user_role = 'child'  # 'parent' or 'child'

def get_db_connection():
    """Create and return a database connection using Streamlit secrets"""
    try:
        connection = mysql.connector.connect(
            host=st.secrets["database"]["host"],
            database=st.secrets["database"]["database"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            port=st.secrets["database"].get("port", 3306)
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        st.info("💡 Make sure you've created .streamlit/secrets.toml with your database credentials")
        return None

def get_all_people():
    """Get all family members"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM people ORDER BY name")
            people = cursor.fetchall()
            return people
        finally:
            conn.close()
    return []

def get_all_chores():
    """Get all chores including recurring information"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT *, 
                       CASE WHEN is_recurring THEN 'Yes' ELSE 'No' END as recurring_status
                FROM chores 
                ORDER BY room, task
            """)
            chores = cursor.fetchall()
            return chores
        finally:
            conn.close()
    return []

def get_assignments_for_date(target_date):
    """Get all assignments for a specific date with completion and review status"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    a.id as assignment_id,
                    a.due_date,
                    c.id as chore_id,
                    c.room,
                    c.task,
                    c.estimated_time,
                    p.name as assigned_to,
                    p.id as person_id,
                    comp.id as completion_id,
                    CASE WHEN comp.id IS NOT NULL THEN 1 ELSE 0 END as is_completed,
                    comp.completed_datetime,
                    comp.actual_minutes,
                    comp.photo_filename,
                    comp.notes as completion_notes,
                    pr.id as review_id,
                    pr.approved,
                    pr.review_notes,
                    p2.name as reviewed_by
                FROM assignments a
                JOIN chores c ON a.chore_id = c.id
                JOIN people p ON a.person_id = p.id
                LEFT JOIN completions comp ON a.id = comp.assignment_id
                LEFT JOIN parental_reviews pr ON comp.id = pr.completion_id
                LEFT JOIN people p2 ON pr.reviewed_by_person_id = p2.id
                WHERE a.assigned_date = %s
                ORDER BY a.due_date, c.room, c.task
            """
            cursor.execute(query, (target_date,))
            assignments = cursor.fetchall()
            return assignments
        finally:
            conn.close()
    return []

def generate_recurring_assignments(target_date):
    """Generate assignments for recurring chores"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.callproc('generate_recurring_assignments', [target_date])
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error generating recurring assignments: {e}")
            return False
        finally:
            conn.close()
    return False

def assign_chore(chore_id, person_id, assigned_date, due_date=None):
    """Assign a chore to a person"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            if due_date is None:
                due_date = assigned_date
            
            cursor.execute(
                "SELECT id FROM assignments WHERE chore_id = %s AND assigned_date = %s",
                (chore_id, assigned_date)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute(
                    "UPDATE assignments SET person_id = %s, due_date = %s WHERE chore_id = %s AND assigned_date = %s",
                    (person_id, due_date, chore_id, assigned_date)
                )
            else:
                cursor.execute(
                    "INSERT INTO assignments (chore_id, person_id, assigned_date, due_date) VALUES (%s, %s, %s, %s)",
                    (chore_id, person_id, assigned_date, due_date)
                )
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error assigning chore: {e}")
            return False
        finally:
            conn.close()
    return False

def mark_chore_complete(assignment_id, actual_minutes, notes=None, photo_data=None, photo_filename=None):
    """Mark a chore as complete"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            saved_filename = None
            if photo_data and photo_filename:
                os.makedirs("chore_photos", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                saved_filename = f"{timestamp}_{photo_filename}"
                filepath = os.path.join("chore_photos", saved_filename)
                
                with open(filepath, "wb") as f:
                    f.write(photo_data)
            
            cursor.execute(
                """INSERT INTO completions (assignment_id, actual_minutes, notes, photo_filename)
                   VALUES (%s, %s, %s, %s)""",
                (assignment_id, actual_minutes, notes, saved_filename)
            )
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error marking chore complete: {e}")
            return False
        finally:
            conn.close()
    return False

def add_parental_review(completion_id, reviewer_person_id, approved=True, review_notes=None):
    """Add a parental review for a completed chore"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO parental_reviews (completion_id, reviewed_by_person_id, approved, review_notes)
                   VALUES (%s, %s, %s, %s)""",
                (completion_id, reviewer_person_id, approved, review_notes)
            )
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error adding review: {e}")
            return False
        finally:
            conn.close()
    return False

def update_chore_recurring(chore_id, is_recurring, recurrence_type=None, recurrence_days=None):
    """Update recurring settings for a chore"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE chores 
                   SET is_recurring = %s, recurrence_type = %s, recurrence_days = %s
                   WHERE id = %s""",
                (is_recurring, recurrence_type, recurrence_days, chore_id)
            )
            conn.commit()
            return True
        except Error as e:
            st.error(f"Error updating chore: {e}")
            return False
        finally:
            conn.close()
    return False

def get_individual_report(person_id, start_date, end_date):
    """Get individual performance report"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    DATE(a.assigned_date) as date,
                    COUNT(DISTINCT a.id) as assigned,
                    COUNT(DISTINCT comp.id) as completed,
                    ROUND(COUNT(DISTINCT comp.id) * 100.0 / COUNT(DISTINCT a.id), 1) as completion_rate,
                    SUM(c.estimated_time) as estimated_minutes,
                    SUM(COALESCE(comp.actual_minutes, 0)) as actual_minutes
                FROM assignments a
                JOIN chores c ON a.chore_id = c.id
                LEFT JOIN completions comp ON a.id = comp.assignment_id
                WHERE a.person_id = %s
                AND a.assigned_date BETWEEN %s AND %s
                GROUP BY DATE(a.assigned_date)
                ORDER BY date
            """
            cursor.execute(query, (person_id, start_date, end_date))
            results = cursor.fetchall()
            return results
        finally:
            conn.close()
    return []

def get_family_report(start_date, end_date):
    """Get family-wide performance report"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT 
                    DATE(a.assigned_date) as date,
                    COUNT(DISTINCT a.id) as total_assigned,
                    COUNT(DISTINCT comp.id) as total_completed,
                    ROUND(COUNT(DISTINCT comp.id) * 100.0 / COUNT(DISTINCT a.id), 1) as completion_rate
                FROM assignments a
                LEFT JOIN completions comp ON a.id = comp.assignment_id
                WHERE a.assigned_date BETWEEN %s AND %s
                GROUP BY DATE(a.assigned_date)
                ORDER BY date
            """
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
        finally:
            conn.close()
    return []

# Main App
def main():
    st.title("🏠 Family Chores Tracker - Phase 2")
    
    # Role selector in sidebar
    with st.sidebar:
        st.session_state.user_role = st.radio("User Role", ["Parent", "Child"], 
                                               index=0 if st.session_state.user_role == 'parent' else 1)
        st.session_state.user_role = st.session_state.user_role.lower()
    
    # Navigation based on role
    if st.session_state.user_role == 'parent':
        pages = ["📋 Assign Chores", "✅ Complete Chores", "👀 Parental Review", 
                 "📊 Family Reports", "📈 Individual Reports", "⚙️ Manage Chores", "🔁 Recurring Setup"]
    else:
        pages = ["✅ My Chores", "📈 My Progress"]
    
    page = st.sidebar.radio("Navigation", pages)
    
    # Route to pages
    if page == "📋 Assign Chores":
        assign_chores_page()
    elif page == "✅ Complete Chores" or page == "✅ My Chores":
        complete_chores_page()
    elif page == "👀 Parental Review":
        parental_review_page()
    elif page == "📊 Family Reports":
        family_reports_page()
    elif page == "📈 Individual Reports" or page == "📈 My Progress":
        individual_reports_page()
    elif page == "⚙️ Manage Chores":
        manage_chores_page()
    elif page == "🔁 Recurring Setup":
        recurring_setup_page()

def assign_chores_page():
    """Page for assigning chores"""
    st.header("📋 Assign Chores")
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        selected_date = st.date_input("Select Date", value=date.today())
    
    with col2:
        if st.button("Generate Recurring"):
            if generate_recurring_assignments(selected_date):
                st.success("Recurring assignments generated!")
                st.rerun()
    
    with col3:
        if st.button("Copy from Yesterday"):
            previous_date = selected_date - timedelta(days=1)
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM assignments WHERE assigned_date = %s", (selected_date,))
                    query = """
                        INSERT INTO assignments (chore_id, person_id, assigned_date, due_date)
                        SELECT chore_id, person_id, %s, %s
                        FROM assignments
                        WHERE assigned_date = %s
                    """
                    cursor.execute(query, (selected_date, selected_date, previous_date))
                    conn.commit()
                    st.success(f"Copied {cursor.rowcount} assignments!")
                    st.rerun()
                finally:
                    conn.close()
    
    with col4:
        if st.button("Clear All"):
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM assignments WHERE assigned_date = %s", (selected_date,))
                    conn.commit()
                    st.success("Cleared!")
                    st.rerun()
                finally:
                    conn.close()
    
    chores = get_all_chores()
    people = get_all_people()
    assignments = get_assignments_for_date(selected_date)
    
    if not chores or not people:
        st.warning("Please ensure chores and family members are in the database.")
        return
    
    assignment_dict = {a['chore_id']: {'person_id': a['person_id'], 'due_date': a['due_date']} 
                      for a in assignments}
    
    st.subheader(f"Assignments for {selected_date}")
    
    chores_by_room = {}
    for chore in chores:
        room = chore['room']
        if room not in chores_by_room:
            chores_by_room[room] = []
        chores_by_room[room].append(chore)
    
    people_names = [p['name'] for p in people]
    people_dict = {p['name']: p['id'] for p in people}
    
    for room, room_chores in sorted(chores_by_room.items()):
        with st.expander(f"🏠 {room} ({len(room_chores)} tasks)", expanded=False):
            for chore in room_chores:
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
                
                with col1:
                    recurring_badge = "🔁" if chore['is_recurring'] else ""
                    st.write(f"**{chore['task']}** {recurring_badge}")
                
                with col2:
                    current_person = None
                    if chore['id'] in assignment_dict:
                        person_id = assignment_dict[chore['id']]['person_id']
                        for p in people:
                            if p['id'] == person_id:
                                current_person = p['name']
                                break
                    
                    assigned_to = st.selectbox(
                        "Assign to",
                        ["Unassigned"] + people_names,
                        index=people_names.index(current_person) + 1 if current_person else 0,
                        key=f"assign_{chore['id']}_{selected_date}"
                    )
                
                with col3:
                    current_due = assignment_dict.get(chore['id'], {}).get('due_date', selected_date)
                    due_date = st.date_input(
                        "Due",
                        value=current_due if current_due else selected_date,
                        key=f"due_{chore['id']}_{selected_date}"
                    )
                
                with col4:
                    st.write(f"{chore['estimated_time']} min")
                
                with col5:
                    if assigned_to != "Unassigned":
                        if st.button("💾", key=f"save_{chore['id']}_{selected_date}"):
                            person_id = people_dict[assigned_to]
                            if assign_chore(chore['id'], person_id, selected_date, due_date):
                                st.success("✓")
                                st.rerun()

def complete_chores_page():
    """Page for completing chores"""
    st.header("✅ Complete Chores")
    
    col1, col2 = st.columns([2, 3])
    with col1:
        selected_date = st.date_input("Select Date", value=date.today())
    
    # Get assignments
    assignments = get_assignments_for_date(selected_date)
    
    if not assignments:
        st.info(f"No chores assigned for {selected_date}")
        return
    
    # Filters
    with col2:
        people = sorted(list(set([a['assigned_to'] for a in assignments])))
        if st.session_state.user_role == 'child':
            filter_person = st.selectbox("Your name", people)
        else:
            filter_person = st.selectbox("Filter by Person", ["All"] + people)
    
    show_completed = st.checkbox("Show Completed", value=True)
    
    # Filter assignments
    filtered = assignments
    if filter_person != "All":
        filtered = [a for a in filtered if a['assigned_to'] == filter_person]
    if not show_completed:
        filtered = [a for a in filtered if not a['is_completed']]
    
    # Stats
    total = len([a for a in assignments if filter_person == "All" or a['assigned_to'] == filter_person])
    complete = len([a for a in assignments if a['is_completed'] and (filter_person == "All" or a['assigned_to'] == filter_person)])
    st.progress(complete / total if total > 0 else 0)
    st.write(f"**Progress:** {complete}/{total} completed ({100*complete/total if total > 0 else 0:.0f}%)")
    
    # Display assignments by room
    by_room = {}
    for assignment in filtered:
        room = assignment['room']
        if room not in by_room:
            by_room[room] = []
        by_room[room].append(assignment)
    
    for room, room_assignments in sorted(by_room.items()):
        with st.expander(f"🏠 {room}", expanded=True):
            for assignment in room_assignments:
                if assignment['is_completed']:
                    # Show completed chore
                    status = "✅ REVIEWED" if assignment['review_id'] else "⏳ Pending Review"
                    st.success(f"{status}: **{assignment['task']}** - {assignment['assigned_to']} - "
                             f"{assignment['actual_minutes']} min")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if assignment['photo_filename']:
                            photo_path = os.path.join("chore_photos", assignment['photo_filename'])
                            if os.path.exists(photo_path):
                                st.image(photo_path, width=200)
                    with col_b:
                        if assignment['completion_notes']:
                            st.write(f"**Notes:** {assignment['completion_notes']}")
                        if assignment['review_notes']:
                            st.write(f"**Review:** {assignment['review_notes']}")
                else:
                    # Completion form
                    overdue = assignment['due_date'] and assignment['due_date'] < date.today()
                    due_text = f"⚠️ OVERDUE (Due: {assignment['due_date']})" if overdue else f"Due: {assignment['due_date']}"
                    
                    st.write(f"**{assignment['task']}** - {assignment['assigned_to']} - {due_text}")
                    
                    with st.form(f"complete_{assignment['assignment_id']}"):
                        col_a, col_b, col_c = st.columns([2, 2, 1])
                        
                        with col_a:
                            actual_minutes = st.number_input(
                                "Actual minutes",
                                min_value=1,
                                value=assignment['estimated_time'],
                                key=f"min_{assignment['assignment_id']}"
                            )
                        
                        with col_b:
                            photo = st.file_uploader(
                                "Upload photo",
                                type=['png', 'jpg', 'jpeg'],
                                key=f"photo_{assignment['assignment_id']}"
                            )
                        
                        notes = st.text_area("Notes (optional)", key=f"notes_{assignment['assignment_id']}")
                        
                        with col_c:
                            st.write("")
                            st.write("")
                            submitted = st.form_submit_button("✅ Complete")
                        
                        if submitted:
                            photo_data = photo.read() if photo else None
                            photo_filename = photo.name if photo else None
                            
                            if mark_chore_complete(assignment['assignment_id'], 
                                                  actual_minutes, 
                                                  notes,
                                                  photo_data, 
                                                  photo_filename):
                                st.success("Chore completed!")
                                st.rerun()

def parental_review_page():
    """Page for parents to review completed chores"""
    st.header("👀 Parental Review")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=date.today())
    
    # Get completions needing review
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                comp.id as completion_id,
                a.assigned_date,
                c.room,
                c.task,
                p.name as completed_by,
                comp.completed_datetime,
                comp.actual_minutes,
                comp.photo_filename,
                comp.notes,
                pr.id as review_id,
                pr.approved,
                pr.review_notes,
                p2.name as reviewed_by
            FROM completions comp
            JOIN assignments a ON comp.assignment_id = a.id
            JOIN chores c ON a.chore_id = c.id
            JOIN people p ON a.person_id = p.id
            LEFT JOIN parental_reviews pr ON comp.id = pr.completion_id
            LEFT JOIN people p2 ON pr.reviewed_by_person_id = p2.id
            WHERE a.assigned_date BETWEEN %s AND %s
            ORDER BY comp.completed_datetime DESC
        """
        cursor.execute(query, (start_date, end_date))
        completions = cursor.fetchall()
        
        # Filter options
        show_reviewed = st.checkbox("Show already reviewed", value=False)
        
        if not show_reviewed:
            completions = [c for c in completions if not c['review_id']]
        
        st.write(f"**{len(completions)} items to review**")
        
        # Get reviewer (parent)
        people = get_all_people()
        parents = [p for p in people if p['name'] in ['Dad', 'Mom']]
        reviewer = st.selectbox("Reviewing as", [p['name'] for p in parents])
        reviewer_id = next((p['id'] for p in parents if p['name'] == reviewer), None)
        
        for completion in completions:
            with st.expander(f"{completion['completed_by']} - {completion['task']} ({completion['assigned_date']})",
                           expanded=not completion['review_id']):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Room:** {completion['room']}")
                    st.write(f"**Completed:** {completion['completed_datetime']}")
                    st.write(f"**Time Taken:** {completion['actual_minutes']} minutes")
                    if completion['notes']:
                        st.write(f"**Notes:** {completion['notes']}")
                    
                    if completion['review_id']:
                        status = "✅ Approved" if completion['approved'] else "❌ Not Approved"
                        st.success(f"{status} by {completion['reviewed_by']}")
                        if completion['review_notes']:
                            st.write(f"**Review Notes:** {completion['review_notes']}")
                
                with col2:
                    if completion['photo_filename']:
                        photo_path = os.path.join("chore_photos", completion['photo_filename'])
                        if os.path.exists(photo_path):
                            st.image(photo_path, width=300)
                
                if not completion['review_id']:
                    with st.form(f"review_{completion['completion_id']}"):
                        approved = st.radio("Status", ["✅ Approve", "❌ Reject"], 
                                          key=f"approve_{completion['completion_id']}")
                        review_notes = st.text_area("Review Notes", 
                                                   key=f"rev_notes_{completion['completion_id']}")
                        
                        if st.form_submit_button("Submit Review"):
                            if reviewer_id:
                                if add_parental_review(
                                    completion['completion_id'],
                                    reviewer_id,
                                    approved == "✅ Approve",
                                    review_notes
                                ):
                                    st.success("Review submitted!")
                                    st.rerun()
    
    finally:
        conn.close()

def family_reports_page():
    """Family-wide reports"""
    st.header("📊 Family Reports")
    
    # Time period selector
    period = st.radio("Period", ["This Week", "This Month", "Custom"], horizontal=True)
    
    if period == "This Week":
        start_date = date.today() - timedelta(days=date.today().weekday())
        end_date = date.today()
    elif period == "This Month":
        start_date = date.today().replace(day=1)
        end_date = date.today()
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=date.today())
    
    # Get family report data
    data = get_family_report(start_date, end_date)
    
    if not data:
        st.info("No data for selected period")
        return
    
    df = pd.DataFrame(data)
    
    # Overall stats
    st.subheader("Overall Statistics")
    col1, col2, col3 = st.columns(3)
    
    total_assigned = df['total_assigned'].sum()
    total_completed = df['total_completed'].sum()
    avg_completion = df['completion_rate'].mean()
    
    col1.metric("Total Assigned", total_assigned)
    col2.metric("Total Completed", total_completed)
    col3.metric("Avg Completion Rate", f"{avg_completion:.1f}%")
    
    # Daily completion chart
    st.subheader("Daily Completion Trends")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['total_assigned'],
        name='Assigned',
        marker_color='lightblue'
    ))
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['total_completed'],
        name='Completed',
        marker_color='green'
    ))
    fig.update_layout(barmode='group', xaxis_title='Date', yaxis_title='Number of Chores')
    st.plotly_chart(fig, use_container_width=True)
    
    # Completion rate over time
    fig2 = px.line(df, x='date', y='completion_rate', 
                   title='Completion Rate Over Time',
                   labels={'completion_rate': 'Completion Rate (%)', 'date': 'Date'})
    fig2.update_traces(line_color='green', line_width=3)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Detailed table
    st.subheader("Detailed Data")
    st.dataframe(df, use_container_width=True)

def individual_reports_page():
    """Individual performance reports"""
    st.header("📈 Individual Reports")
    
    # Person selector
    people = get_all_people()
    if st.session_state.user_role == 'child':
        selected_person = st.selectbox("Your Progress", [p['name'] for p in people])
    else:
        selected_person = st.selectbox("Select Person", [p['name'] for p in people])
    
    person_id = next((p['id'] for p in people if p['name'] == selected_person), None)
    
    if not person_id:
        return
    
    # Time period
    period = st.radio("Period", ["This Week", "This Month", "This Year", "Custom"], horizontal=True)
    
    if period == "This Week":
        start_date = date.today() - timedelta(days=date.today().weekday())
        end_date = date.today()
    elif period == "This Month":
        start_date = date.today().replace(day=1)
        end_date = date.today()
    elif period == "This Year":
        start_date = date.today().replace(month=1, day=1)
        end_date = date.today()
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=date.today())
    
    # Get report data
    data = get_individual_report(person_id, start_date, end_date)
    
    if not data:
        st.info("No data for selected period")
        return
    
    df = pd.DataFrame(data)
    
    # Stats
    st.subheader(f"Statistics for {selected_person}")
    col1, col2, col3, col4 = st.columns(4)
    
    total_assigned = df['assigned'].sum()
    total_completed = df['completed'].sum()
    avg_completion = df['completion_rate'].mean()
    total_time = df['actual_minutes'].sum()
    
    col1.metric("Assigned", total_assigned)
    col2.metric("Completed", total_completed)
    col3.metric("Avg Rate", f"{avg_completion:.1f}%")
    col4.metric("Total Time", f"{total_time:.0f} min")
    
    # Charts
    st.subheader("Performance Trends")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['completion_rate'],
        mode='lines+markers',
        name='Completion Rate',
        line=dict(color='green', width=3)
    ))
    fig.update_layout(xaxis_title='Date', yaxis_title='Completion Rate (%)')
    st.plotly_chart(fig, use_container_width=True)
    
    # Time efficiency
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df['date'],
        y=df['estimated_minutes'],
        name='Estimated',
        marker_color='lightblue'
    ))
    fig2.add_trace(go.Bar(
        x=df['date'],
        y=df['actual_minutes'],
        name='Actual',
        marker_color='orange'
    ))
    fig2.update_layout(barmode='group', xaxis_title='Date', yaxis_title='Minutes')
    st.plotly_chart(fig2, use_container_width=True)
    
    # Detailed table
    st.subheader("Detailed Data")
    st.dataframe(df, use_container_width=True)

def manage_chores_page():
    """Manage chores master list"""
    st.header("⚙️ Manage Chores")
    
    tab1, tab2 = st.tabs(["View All Chores", "Add New Chore"])
    
    with tab1:
        chores = get_all_chores()
        if chores:
            df = pd.DataFrame(chores)
            st.dataframe(df[['room', 'task', 'frequency', 'estimated_time', 'recurring_status']], 
                        use_container_width=True)
    
    with tab2:
        with st.form("add_chore"):
            room = st.text_input("Room")
            task = st.text_input("Task")
            frequency = st.selectbox("Frequency", 
                                    ["Daily", "Weekly", "Monthly", "Semi-annually", "Annual"])
            estimated_time = st.number_input("Estimated Time (minutes)", min_value=1, value=10)
            
            if st.form_submit_button("Add Chore"):
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO chores (room, task, frequency, estimated_time) VALUES (%s, %s, %s, %s)",
                            (room, task, frequency, estimated_time)
                        )
                        conn.commit()
                        st.success("Chore added!")
                    finally:
                        conn.close()

def recurring_setup_page():
    """Setup recurring chores"""
    st.header("🔁 Recurring Chores Setup")
    
    chores = get_all_chores()
    
    st.write("Configure which chores should automatically repeat")
    
    for chore in chores:
        with st.expander(f"{chore['room']} - {chore['task']}"):
            with st.form(f"recurring_{chore['id']}"):
                is_recurring = st.checkbox("Enable Recurring", 
                                          value=chore['is_recurring'] if chore['is_recurring'] else False)
                
                if is_recurring:
                    recurrence_type = st.selectbox(
                        "Recurrence Type",
                        ["daily", "weekly", "monthly", "weekdays", "specific_days"],
                        index=["daily", "weekly", "monthly", "weekdays", "specific_days"].index(chore['recurrence_type']) 
                              if chore['recurrence_type'] else 0
                    )
                    
                    recurrence_days = None
                    if recurrence_type == "specific_days":
                        days = st.multiselect(
                            "Select Days",
                            ["M", "T", "W", "TH", "F", "SA", "SU"],
                            default=chore['recurrence_days'].split(',') if chore['recurrence_days'] else []
                        )
                        recurrence_days = ','.join(days)
                else:
                    recurrence_type = None
                    recurrence_days = None
                
                if st.form_submit_button("Save Settings"):
                    if update_chore_recurring(chore['id'], is_recurring, recurrence_type, recurrence_days):
                        st.success("Updated!")
                        st.rerun()

if __name__ == "__main__":
    main()
