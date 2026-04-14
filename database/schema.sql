CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS encounters (
    encounter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    admission_date DATE NOT NULL,
    discharge_date DATE,
    hospital_department VARCHAR(100),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER NOT NULL,
    icd10_code VARCHAR(10) NOT NULL,
    diagnosis_description VARCHAR(255) NOT NULL,
    is_primary BOOLEAN DEFAULT 0,
    FOREIGN KEY (encounter_id) REFERENCES encounters(encounter_id)
);

CREATE TABLE IF NOT EXISTS procedures (
    procedure_id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER NOT NULL,
    cpt_code VARCHAR(10) NOT NULL,
    procedure_description VARCHAR(255) NOT NULL,
    procedure_date DATE NOT NULL,
    estimated_cost DECIMAL(10, 2),
    FOREIGN KEY (encounter_id) REFERENCES encounters(encounter_id)
);

CREATE TABLE IF NOT EXISTS supplies (
    supply_id INTEGER PRIMARY KEY AUTOINCREMENT,
    encounter_id INTEGER NOT NULL,
    hcpcs_code VARCHAR(10) NOT NULL,
    supply_name VARCHAR(255) NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_cost DECIMAL(10, 2),
    FOREIGN KEY (encounter_id) REFERENCES encounters(encounter_id)
);
