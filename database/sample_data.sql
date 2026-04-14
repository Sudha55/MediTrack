INSERT INTO patients (first_name, last_name, date_of_birth, gender) VALUES
('John', 'Smith', '1980-03-15', 'M'),
('Sarah', 'Johnson', '1975-07-22', 'F'),
('Michael', 'Brown', '1992-11-05', 'M');

INSERT INTO encounters (patient_id, admission_date, discharge_date, hospital_department) VALUES
(1, '2024-05-15', '2024-05-20', 'ICU'),
(2, '2024-05-16', '2024-05-18', 'General Medicine'),
(1, '2024-06-01', '2024-06-03', 'Emergency Room'),
(3, '2024-06-10', '2024-06-15', 'Surgery');

INSERT INTO diagnoses (encounter_id, icd10_code, diagnosis_description, is_primary) VALUES
(1, 'E11.40', 'Type 2 Diabetes with neuropathy', 1),
(1, 'I10', 'Essential hypertension', 0),
(2, 'J45.9', 'Unspecified asthma', 1),
(3, 'R07.9', 'Chest pain, unspecified', 1),
(4, 'K80.0', 'Calculus of gallbladder', 1);

INSERT INTO procedures (encounter_id, cpt_code, procedure_description, procedure_date, estimated_cost) VALUES
(1, '99214', 'Office visit - moderate complexity', '2024-05-15', 150.00),
(1, '80053', 'Comprehensive metabolic panel', '2024-05-15', 75.00),
(2, '94060', 'Spirometry test', '2024-05-16', 120.00),
(3, '93000', 'Electrocardiogram', '2024-06-01', 50.00),
(4, '47600', 'Cholecystectomy', '2024-06-10', 2500.00);

INSERT INTO supplies (encounter_id, hcpcs_code, supply_name, quantity, unit_cost) VALUES
(1, 'A4253', 'Blood glucose test strips', 2, 25.00),
(1, 'A4255', 'Lancets', 1, 10.00),
(2, 'J3301', 'Albuterol inhaler', 3, 15.00),
(4, 'Y9006', 'Surgical gloves', 10, 2.00);
