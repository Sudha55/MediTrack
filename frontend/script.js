const API_BASE = '/api';
let allEncounters = [];
let allPatients = [];
let currentUser = null;
let authToken = null;
let isInitialized = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking auth...');
    checkAuthentication();
});

function checkAuthentication() {
    authToken = localStorage.getItem('authToken');
    console.log('Auth token from storage:', authToken ? 'Found' : 'Not found');
    
    if (!authToken) {
        console.log('No token, redirecting to login');
        window.location.href = 'login.html';
        return;
    }
    
    console.log('Token found, fetching user...');
    fetch(`${API_BASE}/auth/me`, {
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    })
        .then(r => {
            console.log('Auth me response:', r.status);
            return r.json();
        })
        .then(data => {
            console.log('User data:', data);
            if (data.user_id) {
                currentUser = data;
                initializeApp();
            } else {
                console.log('No user_id in response');
                localStorage.removeItem('authToken');
                window.location.href = 'login.html';
            }
        })
        .catch(err => {
            console.error('Auth error:', err);
            localStorage.removeItem('authToken');
            window.location.href = 'login.html';
        });
}

function initializeApp() {
    if (isInitialized) return;
    isInitialized = true;
    
    console.log('Initializing app...');
    loadPatients();
    loadEncounters();
    populatePatientSelects();
    setupSearchableSelect('patientSearch', 'patientDropdown', 'patientId');
    setupSearchableSelect('billingPatientSearch', 'billingPatientDropdown', 'billingPatientId');
    
    const forms = [
        { el: document.getElementById('addPatientForm'), fn: addPatient },
        { el: document.getElementById('addEncounterForm'), fn: addEncounter },
        { el: document.getElementById('addDiagnosisForm'), fn: addDiagnosis },
        { el: document.getElementById('addProcedureForm'), fn: addProcedure },
        { el: document.getElementById('addSupplyForm'), fn: addSupply }
    ];
    
    forms.forEach(form => {
        if (form.el) form.el.addEventListener('submit', form.fn);
    });
    
    console.log('App initialized');
}

function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
    };
}

function handleApiError(response, context = '') {
    return response.json().then(data => {
        const errorMsg = data.errors 
            ? `${data.error}: ${JSON.stringify(data.errors)}`
            : data.error || 'An error occurred';
        
        console.error(`API Error (${context}):`, errorMsg);
        return { error: errorMsg, code: data.code };
    });
}

function setupSearchableSelect(inputId, dropdownId, hiddenId) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    
    if (!input || !dropdown) return;
    
    input.addEventListener('focus', () => {
        dropdown.classList.add('active');
        displayPatientOptions(allPatients, dropdownId, inputId, hiddenId);
    });
    
    input.addEventListener('blur', () => {
        setTimeout(() => {
            dropdown.classList.remove('active');
        }, 200);
    });
    
    input.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        if (searchTerm) {
            const filtered = allPatients.filter(p => 
                `${p.first_name} ${p.last_name}`.toLowerCase().includes(searchTerm)
            );
            displayPatientOptions(filtered, dropdownId, inputId, hiddenId);
        } else {
            displayPatientOptions(allPatients, dropdownId, inputId, hiddenId);
        }
    });
}

function displayPatientOptions(patients, dropdownId, inputId, hiddenId) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    
    dropdown.innerHTML = '';
    
    if (patients.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item">No patients found</div>';
        return;
    }
    
    patients.forEach(patient => {
        const item = document.createElement('div');
        item.className = 'dropdown-item';
        item.textContent = `${patient.first_name} ${patient.last_name}`;
        item.onclick = () => selectPatientFromDropdown(patient, inputId, hiddenId);
        dropdown.appendChild(item);
    });
}

function selectPatientFromDropdown(patient, inputId, hiddenId) {
    document.getElementById(inputId).value = `${patient.first_name} ${patient.last_name}`;
    document.getElementById(hiddenId).value = patient.patient_id;
    document.getElementById(inputId).parentElement.querySelector('.dropdown-list').classList.remove('active');
    
    if (hiddenId === 'billingPatientId') {
        loadPatientBill();
    }
}

function showSection(sectionId) {
    const sections = document.querySelectorAll('.section');
    sections.forEach(s => s.classList.remove('active'));
    const section = document.getElementById(sectionId);
    if (section) section.classList.add('active');
    
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => btn.classList.remove('active'));
    if (event && event.target) event.target.classList.add('active');
}

async function loadPatients() {
    try {
        const response = await fetch(`${API_BASE}/patients`, {
            headers: getHeaders()
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'loadPatients');
            alert(`Error loading patients: ${error.error}`);
            return;
        }
        
        const patients = await response.json();
        allPatients = patients;
        
        const tbody = document.getElementById('patients-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        patients.forEach(patient => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${patient.patient_id}</td>
                <td>${patient.first_name} ${patient.last_name}</td>
                <td>${patient.date_of_birth || 'N/A'}</td>
                <td>${patient.gender || 'N/A'}</td>
                <td>${patient.encounter_count}</td>
                <td><button class="btn-danger" onclick="deletePatient(${patient.patient_id})">Delete</button></td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading patients:', error);
        alert('Failed to load patients');
    }
}

async function addPatient(e) {
    e.preventDefault();
    
    const data = {
        first_name: document.getElementById('firstName').value,
        last_name: document.getElementById('lastName').value,
        date_of_birth: document.getElementById('dateOfBirth').value,
        gender: document.getElementById('gender').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/patients`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'addPatient');
            alert(`Error: ${error.error}`);
            return;
        }
        
        alert('Patient added successfully!');
        document.getElementById('addPatientForm').reset();
        loadPatients();
        populatePatientSelects();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function deletePatient(patientId) {
    if (!confirm('Delete this patient and all their data?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/patients/${patientId}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'deletePatient');
            alert(`Error: ${error.error}`);
            return;
        }
        
        alert('Patient deleted successfully!');
        loadPatients();
        populatePatientSelects();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function loadEncounters() {
    try {
        const response = await fetch(`${API_BASE}/encounters`, {
            headers: getHeaders()
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'loadEncounters');
            return;
        }
        
        allEncounters = await response.json();
        displayEncounters(allEncounters);
    } catch (error) {
        console.error('Error loading encounters:', error);
    }
}

function displayEncounters(encounters) {
    const tbody = document.getElementById('encounters-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    encounters.forEach(enc => {
        const admission = new Date(enc.admission_date);
        const discharge = new Date(enc.discharge_date);
        const days = Math.floor((discharge - admission) / (1000 * 60 * 60 * 24));
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${enc.encounter_id}</td>
            <td>${enc.first_name} ${enc.last_name}</td>
            <td>${enc.admission_date}</td>
            <td>${enc.discharge_date}</td>
            <td>${enc.hospital_department}</td>
            <td>${days}</td>
            <td><button class="btn-info" onclick="editEncounter(${enc.encounter_id})">Edit</button></td>
        `;
        tbody.appendChild(row);
    });
}

async function addEncounter(e) {
    e.preventDefault();
    
    const patientId = document.getElementById('patientId').value;
    if (!patientId) {
        alert('Please select a patient');
        return;
    }
    
    const data = {
        patient_id: parseInt(patientId),
        admission_date: document.getElementById('admissionDate').value,
        discharge_date: document.getElementById('dischargeDate').value,
        hospital_department: document.getElementById('department').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/encounters`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'addEncounter');
            alert(`Error: ${error.error}`);
            return;
        }
        
        const result = await response.json();
        alert('Encounter created successfully!');
        document.getElementById('addEncounterForm').reset();
        document.getElementById('patientSearch').value = '';
        loadEncounters();
        editEncounter(result.encounter_id);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function editEncounter(encounterId) {
    const details = document.getElementById('encounter-details');
    if (details) details.style.display = 'block';
    
    const title = document.getElementById('encounter-title');
    if (title) title.textContent = `Encounter #${encounterId}`;
    
    document.getElementById('diagnosisEncounterId').value = encounterId;
    document.getElementById('procedureEncounterId').value = encounterId;
    document.getElementById('supplyEncounterId').value = encounterId;
    loadEncounterDetails(encounterId);
}

async function loadEncounterDetails(encounterId) {
    try {
        const response = await fetch(`${API_BASE}/encounters/${encounterId}`, {
            headers: getHeaders()
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'loadEncounterDetails');
            return;
        }
        
        const data = await response.json();
        
        const diagList = document.getElementById('diagnoses-list');
        if (diagList) {
            diagList.innerHTML = '<h5>💊 Diagnoses</h5>';
            if (data.diagnoses.length === 0) {
                diagList.innerHTML += '<p>No diagnoses added</p>';
            } else {
                data.diagnoses.forEach(d => {
                    diagList.innerHTML += `<div class="summary-item"><div class="summary-item-code">${d.icd10_code}</div><div class="summary-item-desc">${d.diagnosis_description}</div></div>`;
                });
            }
        }
        
        const procList = document.getElementById('procedures-list');
        if (procList) {
            procList.innerHTML = '<h5 style="margin-top:15px;">🔬 Procedures</h5>';
            if (data.procedures.length === 0) {
                procList.innerHTML += '<p>No procedures added</p>';
            } else {
                data.procedures.forEach(p => {
                    procList.innerHTML += `<div class="summary-item"><div class="summary-item-code">${p.cpt_code}</div><div class="summary-item-desc">${p.procedure_description}</div><div class="summary-item-cost">$${parseFloat(p.estimated_cost || 0).toFixed(2)}</div></div>`;
                });
            }
        }
        
        const supList = document.getElementById('supplies-list');
        if (supList) {
            supList.innerHTML = '<h5 style="margin-top:15px;">📦 Supplies</h5>';
            if (data.supplies.length === 0) {
                supList.innerHTML += '<p>No supplies added</p>';
            } else {
                data.supplies.forEach(s => {
                    const cost = parseFloat(s.unit_cost || 0) * parseInt(s.quantity || 1);
                    supList.innerHTML += `<div class="summary-item"><div class="summary-item-code">${s.hcpcs_code} x${s.quantity}</div><div class="summary-item-desc">${s.supply_name}</div><div class="summary-item-cost">$${cost.toFixed(2)}</div></div>`;
                });
            }
        }
    } catch (error) {
        console.error('Error loading encounter details:', error);
    }
}

async function addDiagnosis(e) {
    e.preventDefault();
    
    const data = {
        encounter_id: parseInt(document.getElementById('diagnosisEncounterId').value),
        icd10_code: document.getElementById('icd10Code').value,
        diagnosis_description: document.getElementById('diagnosisDesc').value,
        is_primary: document.getElementById('isPrimary').checked ? 1 : 0
    };
    
    try {
        const response = await fetch(`${API_BASE}/diagnoses`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'addDiagnosis');
            alert(`Error: ${error.error}`);
            return;
        }
        
        alert('Diagnosis added successfully!');
        document.getElementById('addDiagnosisForm').reset();
        loadEncounterDetails(data.encounter_id);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function addProcedure(e) {
    e.preventDefault();
    
    const data = {
        encounter_id: parseInt(document.getElementById('procedureEncounterId').value),
        cpt_code: document.getElementById('cptCode').value,
        procedure_description: document.getElementById('procedureDesc').value,
        estimated_cost: parseFloat(document.getElementById('procedureCost').value),
        procedure_date: new Date().toISOString().split('T')[0]
    };
    
    try {
        const response = await fetch(`${API_BASE}/procedures`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'addProcedure');
            alert(`Error: ${error.error}`);
            return;
        }
        
        alert('Procedure added successfully!');
        document.getElementById('addProcedureForm').reset();
        loadEncounterDetails(data.encounter_id);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function addSupply(e) {
    e.preventDefault();
    
    const data = {
        encounter_id: parseInt(document.getElementById('supplyEncounterId').value),
        hcpcs_code: document.getElementById('hcpcsCode').value,
        supply_name: document.getElementById('supplyName').value,
        quantity: parseInt(document.getElementById('supplyQty').value),
        unit_cost: parseFloat(document.getElementById('supplyCost').value)
    };
    
    try {
        const response = await fetch(`${API_BASE}/supplies`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'addSupply');
            alert(`Error: ${error.error}`);
            return;
        }
        
        alert('Supply added successfully!');
        document.getElementById('addSupplyForm').reset();
        loadEncounterDetails(data.encounter_id);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function loadPatientBill() {
    const patientId = document.getElementById('billingPatientId').value;
    if (!patientId) {
        document.getElementById('patient-bill').style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/patients/${patientId}/bill`, {
            headers: getHeaders()
        });
        
        if (!response.ok) {
            const error = await handleApiError(response, 'loadPatientBill');
            alert(`Error: ${error.error}`);
            return;
        }
        
        const data = await response.json();
        
        document.getElementById('bill-patient-name').textContent = `${data.patient.first_name} ${data.patient.last_name}`;
        document.getElementById('bill-patient-info').textContent = `DOB: ${data.patient.date_of_birth} | ID: ${data.patient.patient_id}`;
        
        let billHTML = '';
        let totalAmount = 0;
        
        data.encounters.forEach((enc, i) => {
            billHTML += `
                <div class="bill-encounter">
                    <h4>Encounter ${i+1}: ${enc.encounter.admission_date} to ${enc.encounter.discharge_date}</h4>
                    <p style="font-size:13px; color:#6b7280; margin-bottom:10px;">${enc.encounter.hospital_department}</p>
                    
                    <div style="margin-bottom:10px;">
                        <strong>Diagnoses (ICD-10):</strong>
                        ${enc.diagnoses.map(d => `<div class="bill-item"><div><span class="bill-item-code">${d.icd10_code}</span> ${d.diagnosis_description}</div></div>`).join('')}
                    </div>
                    
                    <div style="margin-bottom:10px;">
                        <strong>Procedures (CPT):</strong>
                        ${enc.procedures.map(p => {
                            totalAmount += parseFloat(p.estimated_cost || 0);
                            return `<div class="bill-item"><div><span class="bill-item-code">${p.cpt_code}</span> ${p.procedure_description}</div><div class="bill-item-cost">$${parseFloat(p.estimated_cost || 0).toFixed(2)}</div></div>`;
                        }).join('')}
                    </div>
                    
                    <div>
                        <strong>Supplies (HCPCS):</strong>
                        ${enc.supplies.map(s => {
                            const cost = parseFloat(s.unit_cost || 0) * parseInt(s.quantity || 1);
                            totalAmount += cost;
                            return `<div class="bill-item"><div><span class="bill-item-code">${s.hcpcs_code}</span> ${s.supply_name} x${s.quantity}</div><div class="bill-item-cost">$${cost.toFixed(2)}</div></div>`;
                        }).join('')}
                    </div>
                </div>
            `;
        });
        
        document.getElementById('bill-encounters').innerHTML = billHTML;
        document.getElementById('total-amount').textContent = `$${totalAmount.toFixed(2)}`;
        document.getElementById('patient-bill').style.display = 'block';
    } catch (error) {
        console.error('Error loading bill:', error);
    }
}

function populatePatientSelects() {
    fetch(`${API_BASE}/patients`, {
        headers: getHeaders()
    })
        .then(r => r.json())
        .then(patients => {
            allPatients = patients;
        })
        .catch(err => console.error('Error populating patients:', err));
}
