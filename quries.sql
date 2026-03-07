CREATE DATABASE IF NOT EXISTS university;
USE university;

CREATE TABLE Individuals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unique_id VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    place_of_birth VARCHAR(100),
    nationality VARCHAR(50),
    gender ENUM('M','F'),
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    status ENUM('Pending','Active','Suspended','Inactive','Archived') DEFAULT 'Pending',
    type ENUM('Student','Faculty','Staff','External','Alumni','Temporary') NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE Students (
    student_id INT PRIMARY KEY,
    academic_info TEXT,
    national_id VARCHAR(20),
    high_school_diploma VARCHAR(100),
    major_program VARCHAR(100),
    entry_year YEAR,
    group_name VARCHAR(50),
    scholarship_status BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (student_id) REFERENCES Individuals(id) ON DELETE CASCADE
);

CREATE TABLE Faculty (
    faculty_id INT PRIMARY KEY,
    rank VARCHAR(50),
    employment_category VARCHAR(50),
    start_date DATE,
    primary_department VARCHAR(100),
    secondary_departments VARCHAR(255),
    office VARCHAR(50),
    phd_institution VARCHAR(100),
    research_areas TEXT,
    habilitation BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (faculty_id) REFERENCES Individuals(id) ON DELETE CASCADE
);

CREATE TABLE Staff (
    staff_id INT PRIMARY KEY,
    department VARCHAR(100),
    job_title VARCHAR(50),
    grade VARCHAR(50),
    entry_date DATE,
    FOREIGN KEY (staff_id) REFERENCES Individuals(id) ON DELETE CASCADE
);

CREATE TABLE IdentityHistory (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    individual_id INT NOT NULL,
    old_status ENUM('Pending','Active','Suspended','Inactive','Archived'),
    new_status ENUM('Pending','Active','Suspended','Inactive','Archived'),
    change_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100),
    FOREIGN KEY (individual_id) REFERENCES Individuals(id) ON DELETE CASCADE
);

INSERT INTO Individuals (unique_id, first_name, last_name, date_of_birth, gender, email, type, status)
VALUES 
('STU202400001','Ahmed','Ali','2005-06-15','M','ahmed.ali@example.com','Student','Active'),
('FAC202400001','Dr. Sarah','Hassan','1980-03-20','F','sarah.hassan@example.com','Faculty','Active'),
('STF202400001','Mourad','Khaled','1975-09-10','M','mourad.khaled@example.com','Staff','Active');

INSERT INTO Students (student_id, academic_info, national_id, high_school_diploma, major_program, entry_year, group_name, scholarship_status)
VALUES (1, 'Undergraduate', '123456789', 'Science 2023, Excellent', 'Computer Science', 2024, 'CS-1', TRUE);

INSERT INTO Faculty (faculty_id, rank, employment_category, start_date, primary_department, secondary_departments, office, phd_institution, research_areas, habilitation)
VALUES (2, 'Professor', 'Tenured', '2010-09-01', 'Computer Science', 'Math', 'Bldg A-3-201', 'MIT', 'AI, Security', TRUE);

INSERT INTO Staff (staff_id, department, job_title, grade, entry_date)
VALUES (3, 'IT Department', 'System Admin', 'Senior', '2000-01-15');