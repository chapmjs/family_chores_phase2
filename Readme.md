# Family Chores Tracker App Phase 2

A comprehensive family chores management system built with Streamlit and MySQL.

## Features

### Phase 1
- ✅ Assign chores to family members
- ✅ Track chore completion with photos
- ✅ Record actual time taken for each task
- ✅ View daily assignments
- ✅ Copy previous day's assignments
- ✅ Complete master list of all household chores

### Phase 2 (Enhanced)
- 🔁 Recurring chores (daily, weekly, monthly, weekdays, specific days)
- 📅 Due dates for assignments
- 👀 Parental review system with approval workflow
- 📊 Family-wide reporting (daily, weekly, monthly)
- 📈 Individual performance reports
- 📸 Photo uploads for completed chores
- ⏱️ Time tracking and comparison
- 🎯 Progress tracking and completion rates

## Database Setup

### Step 1: Install MySQL

Make sure you have MySQL installed on your system. Download from: https://dev.mysql.com/downloads/

### Step 2: Create the Database

**For Phase 1:**
```bash
mysql -u your_username -p < phase1_database_schema.sql
```

**For Phase 2 (after Phase 1):**
```bash
mysql -u your_username -p < phase2_database_schema.sql
```

Or run the SQL files directly in your MySQL client.

### Step 3: Update Database Credentials

In both `phase1_chores_app.py` and `phase2_chores_app.py`, update the database configuration:

```python
DB_CONFIG = {
    'host': 'localhost',  # Your MySQL host
    'database': 'family_chores',
    'user': 'your_username',  # Your MySQL username
    'password': 'your_password'  # Your MySQL password
}
```

**Security Best Practice:** Use environment variables instead:

```python
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'family_chores'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}
```

Then create a `.env` file (don't commit this to GitHub):
```
DB_HOST=localhost
DB_NAME=family_chores
DB_USER=your_username
DB_PASSWORD=your_password
```

## Local Installation

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Run Phase 1 App

```bash
streamlit run phase1_chores_app.py
```

### Step 3: Run Phase 2 App (when ready)

```bash
streamlit run phase2_chores_app.py
```

## Deployment to Streamlit Cloud

### Step 1: Prepare Your Repository

1. Create a new GitHub repository
2. Add these files to your repository:
   - `phase1_chores_app.py` or `phase2_chores_app.py` (rename to `app.py`)
   - `requirements.txt`
   - `README.md`

**Important:** Do NOT commit your database credentials to GitHub!

### Step 2: Database Hosting

For production deployment, you'll need a cloud-hosted MySQL database. Options:

1. **Amazon RDS (Recommended)**
   - Create a MySQL instance in AWS RDS
   - Note the endpoint, username, and password

2. **Google Cloud SQL**
   - Create a Cloud SQL MySQL instance
   - Configure connection settings

3. **PlanetScale** (Free tier available)
   - Create a serverless MySQL database
   - Great for hobby projects

4. **ClearDB** (Heroku add-on)
   - Easy to set up
   - Free tier available

### Step 3: Configure Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Choose `app.py` as the main file

### Step 4: Add Secrets

In Streamlit Cloud, add your database credentials as secrets:

1. Go to your app settings
2. Click "Secrets"
3. Add your database configuration:

```toml
[database]
host = "your-database-host.com"
database = "family_chores"
user = "your_username"
password = "your_password"
```

Then update your app code to use secrets:

```python
import streamlit as st

DB_CONFIG = {
    'host': st.secrets["database"]["host"],
    'database': st.secrets["database"]["database"],
    'user': st.secrets["database"]["user"],
    'password': st.secrets["database"]["password"]
}
```

### Step 5: Initialize Database

After deploying, you'll need to run the SQL schema on your cloud database:

```bash
mysql -h your-database-host.com -u your_username -p family_chores < phase1_database_schema.sql
```

Or use a MySQL client tool like MySQL Workbench.

## File Structure

```
family-chores-app/
├── phase1_database_schema.sql      # Phase 1 database setup
├── phase2_database_schema.sql      # Phase 2 database enhancements
├── phase1_chores_app.py            # Phase 1 Streamlit app
├── phase2_chores_app.py            # Phase 2 Streamlit app (full-featured)
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── chore_photos/                   # Directory for uploaded photos (auto-created)
```

## Usage Guide

### For Parents:

1. **Assign Chores**
   - Select a date
   - Assign chores to family members
   - Set due dates
   - Use "Generate Recurring" to auto-create recurring chores
   - Copy from previous day if needed

2. **Review Completions**
   - View completed chores with photos
   - Approve or reject submissions
   - Add review notes

3. **View Reports**
   - Check family-wide completion rates
   - View individual performance
   - Track trends over time
   - Export data as CSV

### For Children:

1. **View Assigned Chores**
   - See your chores for today
   - Check due dates
   - View estimated time

2. **Complete Chores**
   - Mark chores as complete
   - Enter actual time taken
   - Upload a photo (optional)
   - Add notes

3. **Track Progress**
   - View your completion rates
   - See your performance over time
   - Compare estimated vs actual time

## Troubleshooting

### Connection Issues

If you get a connection error:
1. Verify MySQL is running
2. Check database credentials
3. Ensure database exists
4. Check firewall settings

### Photo Upload Issues

If photos aren't saving:
1. Ensure the app has write permissions
2. The `chore_photos` directory is created automatically
3. Check available disk space

### Recurring Chores Not Generating

If recurring chores aren't being created:
1. Verify the stored procedure exists (Phase 2)
2. Check chore recurring settings
3. Make sure you click "Generate Recurring" button

## Advanced Configuration

### Custom Family Members

Add or modify family members in the database:

```sql
INSERT INTO people (name) VALUES ('NewMember');
```

### Custom Chore Categories

Chores are organized by room. To add new rooms, simply add chores with the new room name:

```sql
INSERT INTO chores (room, task, frequency, estimated_time) 
VALUES ('Basement', 'Organize storage', 'Monthly', 60);
```

### Backup Your Data

Regular backups are essential:

```bash
mysqldump -u your_username -p family_chores > backup_$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
mysql -u your_username -p family_chores < backup_20240101.sql
```

## Contributing

This is a family project! Feel free to:
- Add new features
- Improve the UI
- Fix bugs
- Add more reporting options

## Support

For issues or questions:
1. Check this README
2. Review the database schema
3. Check Streamlit documentation: https://docs.streamlit.io/
4. MySQL documentation: https://dev.mysql.com/doc/

## License

This is a personal family project. Use and modify as needed for your own family!

## Roadmap

Future enhancements could include:
- [ ] Mobile app version
- [ ] Push notifications for due chores
- [ ] Reward/points system
- [ ] Chore trading between siblings
- [ ] Integration with calendar apps
- [ ] Automated recurring assignment generation
- [ ] More detailed analytics
- [ ] Family leaderboards
- [ ] Allowance tracking tied to chore completion

---

**Happy Choring! 🏠✨**
