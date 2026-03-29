# SQL Server Connection Details for Temple Feedback System

## Database Information
- **Server**: DESKTOP-FUQL29E\SQLEXPRESS (or your server name)
- **Database**: ts_feedbackdb
- **Username**: ts_feedback_user
- **Password**: TsFeedback@2026!

## Connection Strings

### Python (pyodbc)
```python
import pyodbc

connection_string = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-FUQL29E\\SQLEXPRESS;"
    "Database=ts_feedbackdb;"
    "UID=ts_feedback_user;"
    "PWD=TsFeedback@2026!;"
    "TrustServerCertificate=yes;"
)

conn = pyodbc.connect(connection_string)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

# URL encode the password if it has special characters
connection_url = "mssql+pyodbc://ts_feedback_user:TsFeedback%402026%21@DESKTOP-FUQL29E\\SQLEXPRESS/ts_feedbackdb?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"

engine = create_engine(connection_url)
```

### .NET / C#
```csharp
string connectionString = "Server=DESKTOP-FUQL29E\\SQLEXPRESS;Database=ts_feedbackdb;User Id=ts_feedback_user;Password=TsFeedback@2026!;TrustServerCertificate=True;";
```

### Node.js (mssql)
```javascript
const sql = require('mssql');

const config = {
    user: 'ts_feedback_user',
    password: 'TsFeedback@2026!',
    server: 'DESKTOP-FUQL29E\\SQLEXPRESS',
    database: 'ts_feedbackdb',
    options: {
        encrypt: true,
        trustServerCertificate: true
    }
};

sql.connect(config);
```

### Java (JDBC)
```java
String url = "jdbc:sqlserver://DESKTOP-FUQL29E\\SQLEXPRESS;databaseName=ts_feedbackdb;user=ts_feedback_user;password=TsFeedback@2026!;encrypt=true;trustServerCertificate=true;";
```

## Tables Overview

| Table | Description |
|-------|-------------|
| users | Admin users for the system |
| temples | Temple information and settings |
| services | Feedback service categories |
| officers | Temple officers who handle feedback |
| feedback | Main feedback/complaints table |
| whatsapp_logs | WhatsApp notification logs |
| file_uploads | Uploaded files (logos, videos) |

## Stored Procedures

| Procedure | Description |
|-----------|-------------|
| sp_GetDashboardStats | Get dashboard statistics |
| sp_GetTempleWiseFeedback | Get feedback count by temple |
| sp_GenerateComplaintId | Generate unique complaint ID (TF00001) |
| sp_CreateFeedback | Create new feedback entry |
| sp_UpdateFeedbackStatus | Update feedback status |
| sp_AssignOfficer | Assign officer to feedback |

## Views

| View | Description |
|------|-------------|
| vw_FeedbackSummary | Feedback with all details |
| vw_OfficerPerformance | Officer statistics |

## Default Credentials

### Admin
- Email: admin@temple.com
- Password: admin123

### Officer
- Email: officer@temple.com
- Password: officer123

## Setup Instructions

1. Open SQL Server Management Studio (SSMS)
2. Connect to your SQL Server instance
3. Open the `SQL_SERVER_SETUP.sql` file
4. Execute the entire script
5. Verify tables are created in `ts_feedbackdb` database

## Notes

- The password hash in the script is a bcrypt hash
- Change the default passwords after setup
- Ensure SQL Server Authentication is enabled
- Enable TCP/IP protocol if connecting remotely
