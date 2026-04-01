-- =====================================================
-- TEMPLE FEEDBACK MANAGEMENT SYSTEM
-- SQL Server Database Setup Script
-- Database: ts_feedbackdb
-- User: ts_feedback_user
-- =====================================================

-- Step 1: Create Database
USE master;
GO

IF EXISTS (SELECT name FROM sys.databases WHERE name = 'ts_feedbackdb')
BEGIN
    ALTER DATABASE ts_feedbackdb SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE ts_feedbackdb;
END
GO

CREATE DATABASE ts_feedbackdb;
GO

USE ts_feedbackdb;
GO

-- Step 2: Create Login and User
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'ts_feedback_user')
BEGIN
    CREATE LOGIN ts_feedback_user WITH PASSWORD = 'TsFeedback@2026!';
END
GO

CREATE USER ts_feedback_user FOR LOGIN ts_feedback_user;
GO

-- Grant permissions
ALTER ROLE db_owner ADD MEMBER ts_feedback_user;
GO

-- =====================================================
-- TABLES
-- =====================================================

-- 1. Users Table (Admins)
CREATE TABLE users (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    username NVARCHAR(100) NOT NULL UNIQUE,
    email NVARCHAR(255) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL,
    role NVARCHAR(50) DEFAULT 'admin',
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- 2. Temples Table
CREATE TABLE temples (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255) NOT NULL,
    location NVARCHAR(500) NOT NULL,
    email NVARCHAR(255),
    logo_path NVARCHAR(500),
    officer_id UNIQUEIDENTIFIER,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- 3. Services Table
CREATE TABLE services (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(100) NOT NULL,
    display_order INT DEFAULT 1,
    is_active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- 4. Officers Table
CREATE TABLE officers (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(255) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL,
    temple_id UNIQUEIDENTIFIER,
    temple_name NVARCHAR(255),
    role NVARCHAR(50) DEFAULT 'officer',
    permissions NVARCHAR(MAX), -- JSON array of permissions
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (temple_id) REFERENCES temples(id) ON DELETE SET NULL
);
GO

-- 5. Feedback Table
CREATE TABLE feedback (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    complaint_id NVARCHAR(50) NOT NULL UNIQUE,
    temple_id UNIQUEIDENTIFIER NOT NULL,
    temple_name NVARCHAR(255),
    user_name NVARCHAR(255) NOT NULL,
    user_mobile NVARCHAR(15) NOT NULL,
    service NVARCHAR(100) NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    message NVARCHAR(MAX),
    video_url NVARCHAR(500),
    status NVARCHAR(50) DEFAULT 'Pending',
    officer_id UNIQUEIDENTIFIER,
    officer_name NVARCHAR(255),
    resolution_notes NVARCHAR(MAX),
    officer_notes NVARCHAR(MAX),
    resolved_at DATETIME2,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (temple_id) REFERENCES temples(id) ON DELETE CASCADE,
    FOREIGN KEY (officer_id) REFERENCES officers(id) ON DELETE SET NULL
);
GO

-- 6. WhatsApp Logs Table
CREATE TABLE whatsapp_logs (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    feedback_id UNIQUEIDENTIFIER,
    phone_number NVARCHAR(15) NOT NULL,
    message NVARCHAR(MAX) NOT NULL,
    status NVARCHAR(50) DEFAULT 'Sent',
    message_type NVARCHAR(50) DEFAULT 'notification',
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE SET NULL
);
GO

-- 7. File Uploads Table
CREATE TABLE file_uploads (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    filename NVARCHAR(255) NOT NULL,
    original_filename NVARCHAR(255),
    file_path NVARCHAR(500) NOT NULL,
    file_type NVARCHAR(100),
    file_size BIGINT,
    uploaded_by NVARCHAR(255),
    file_blob VARBINARY(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- =====================================================
-- INDEXES for better performance
-- =====================================================

CREATE INDEX idx_feedback_temple_id ON feedback(temple_id);
CREATE INDEX idx_feedback_status ON feedback(status);
CREATE INDEX idx_feedback_created_at ON feedback(created_at DESC);
CREATE INDEX idx_feedback_complaint_id ON feedback(complaint_id);
CREATE INDEX idx_officers_temple_id ON officers(temple_id);
CREATE INDEX idx_officers_email ON officers(email);
CREATE INDEX idx_temples_email ON temples(email);
CREATE INDEX idx_whatsapp_logs_feedback_id ON whatsapp_logs(feedback_id);
GO

-- =====================================================
-- DEFAULT DATA
-- =====================================================

-- Insert Default Admin User (password: admin123)
INSERT INTO users (username, email, password, role)
VALUES ('admin', 'admin@temple.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HxMaQJ8WQKW6mK', 'admin');
GO

-- Insert Default Services
INSERT INTO services (name, display_order) VALUES 
('Darshan', 1),
('Annadhanam', 2),
('Prasadam', 3),
('Pooja', 4),
('Donation', 5),
('Accommodation', 6),
('Ticket', 7),
('Laddu', 8),
('Annaprasana', 9),
('General', 10);
GO

-- Insert Sample Temples
INSERT INTO temples (name, location, email) VALUES 
('Bhadrachalam Devasthanam', 'Bhadrachalam, Telangana', 'bhadrachalam@temple.com'),
('Vemulawada Devasthanam', 'Vemulawada, Telangana', 'vemulawada@temple.com'),
('Yadagirigutta', 'Yadagirigutta, Telangana', 'yadagirigutta@temple.com');
GO

-- Insert Sample Officer (password: officer123)
INSERT INTO officers (name, email, password, temple_id, temple_name, role, permissions)
SELECT 
    'Test Officer',
    'officer@temple.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.HxMaQJ8WQKW6mK',
    id,
    name,
    'officer',
    '["view_feedback", "update_status"]'
FROM temples WHERE name = 'Bhadrachalam Devasthanam';
GO

-- =====================================================
-- STORED PROCEDURES
-- =====================================================

-- Get Dashboard Statistics
CREATE PROCEDURE sp_GetDashboardStats
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        (SELECT COUNT(*) FROM temples) AS total_temples,
        (SELECT COUNT(*) FROM officers) AS total_officers,
        (SELECT COUNT(*) FROM feedback) AS total_feedback,
        (SELECT COUNT(*) FROM feedback WHERE status = 'Pending') AS pending,
        (SELECT COUNT(*) FROM feedback WHERE status = 'In Progress') AS in_progress,
        (SELECT COUNT(*) FROM feedback WHERE status = 'Resolved') AS resolved,
        (SELECT COUNT(*) FROM feedback WHERE status = 'Rejected') AS rejected;
END
GO

-- Get Temple-wise Feedback Count
CREATE PROCEDURE sp_GetTempleWiseFeedback
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        t.name AS temple_name,
        COUNT(f.id) AS feedback_count
    FROM temples t
    LEFT JOIN feedback f ON t.id = f.temple_id
    GROUP BY t.id, t.name
    ORDER BY feedback_count DESC;
END
GO

-- Generate Complaint ID
CREATE PROCEDURE sp_GenerateComplaintId
    @NewComplaintId NVARCHAR(50) OUTPUT
AS
BEGIN
    DECLARE @Count INT;
    SELECT @Count = COUNT(*) + 1 FROM feedback;
    SET @NewComplaintId = 'TF' + RIGHT('00000' + CAST(@Count AS NVARCHAR), 5);
END
GO

-- Create Feedback
CREATE PROCEDURE sp_CreateFeedback
    @temple_id UNIQUEIDENTIFIER,
    @user_name NVARCHAR(255),
    @user_mobile NVARCHAR(15),
    @service NVARCHAR(100),
    @rating INT,
    @message NVARCHAR(MAX) = NULL,
    @video_url NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @complaint_id NVARCHAR(50);
    DECLARE @temple_name NVARCHAR(255);
    
    EXEC sp_GenerateComplaintId @NewComplaintId = @complaint_id OUTPUT;
    
    SELECT @temple_name = name FROM temples WHERE id = @temple_id;
    
    INSERT INTO feedback (complaint_id, temple_id, temple_name, user_name, user_mobile, service, rating, message, video_url)
    VALUES (@complaint_id, @temple_id, @temple_name, @user_name, @user_mobile, @service, @rating, @message, @video_url);
    
    SELECT @complaint_id AS complaint_id;
END
GO

-- Update Feedback Status
CREATE PROCEDURE sp_UpdateFeedbackStatus
    @feedback_id UNIQUEIDENTIFIER,
    @status NVARCHAR(50),
    @resolution_notes NVARCHAR(MAX) = NULL,
    @officer_notes NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE feedback 
    SET 
        status = @status,
        resolution_notes = @resolution_notes,
        officer_notes = @officer_notes,
        resolved_at = CASE WHEN @status = 'Resolved' THEN GETUTCDATE() ELSE resolved_at END,
        updated_at = GETUTCDATE()
    WHERE id = @feedback_id;
END
GO

-- Assign Officer to Feedback
CREATE PROCEDURE sp_AssignOfficer
    @feedback_id UNIQUEIDENTIFIER,
    @officer_id UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @officer_name NVARCHAR(255);
    SELECT @officer_name = name FROM officers WHERE id = @officer_id;
    
    UPDATE feedback 
    SET 
        officer_id = @officer_id,
        officer_name = @officer_name,
        status = 'In Progress',
        updated_at = GETUTCDATE()
    WHERE id = @feedback_id;
END
GO

-- =====================================================
-- VIEWS
-- =====================================================

-- Feedback Summary View
CREATE VIEW vw_FeedbackSummary
AS
SELECT 
    f.id,
    f.complaint_id,
    f.temple_name,
    f.user_name,
    f.user_mobile,
    f.service,
    f.rating,
    f.message,
    f.status,
    f.officer_name,
    f.created_at,
    f.resolved_at,
    DATEDIFF(HOUR, f.created_at, ISNULL(f.resolved_at, GETUTCDATE())) AS hours_since_created
FROM feedback f;
GO

-- Officer Performance View
CREATE VIEW vw_OfficerPerformance
AS
SELECT 
    o.id,
    o.name,
    o.email,
    o.temple_name,
    COUNT(f.id) AS total_assigned,
    SUM(CASE WHEN f.status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_count,
    SUM(CASE WHEN f.status = 'Pending' THEN 1 ELSE 0 END) AS pending_count
FROM officers o
LEFT JOIN feedback f ON o.id = f.officer_id
GROUP BY o.id, o.name, o.email, o.temple_name;
GO

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

GRANT EXECUTE ON sp_GetDashboardStats TO ts_feedback_user;
GRANT EXECUTE ON sp_GetTempleWiseFeedback TO ts_feedback_user;
GRANT EXECUTE ON sp_GenerateComplaintId TO ts_feedback_user;
GRANT EXECUTE ON sp_CreateFeedback TO ts_feedback_user;
GRANT EXECUTE ON sp_UpdateFeedbackStatus TO ts_feedback_user;
GRANT EXECUTE ON sp_AssignOfficer TO ts_feedback_user;
GRANT SELECT ON vw_FeedbackSummary TO ts_feedback_user;
GRANT SELECT ON vw_OfficerPerformance TO ts_feedback_user;
GO

PRINT '=====================================================';
PRINT 'Temple Feedback Database Setup Complete!';
PRINT '=====================================================';
PRINT 'Database: ts_feedbackdb';
PRINT 'User: ts_feedback_user';
PRINT 'Password: TsFeedback@2026!';
PRINT '';
PRINT 'Default Admin Login:';
PRINT '  Email: admin@temple.com';
PRINT '  Password: admin123';
PRINT '';
PRINT 'Default Officer Login:';
PRINT '  Email: officer@temple.com';
PRINT '  Password: officer123';
PRINT '=====================================================';
GO
