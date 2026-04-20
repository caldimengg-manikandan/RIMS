const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

// 1. Define the Modules (Models) and their "Containers" (Pages/Forms/Modals)
const projectStructure = [
  {
    module: "Authentication",
    containers: ["Login Form", "Password Reset", "User Registration", "Auth Middleware"]
  },
  {
    module: "Dashboard",
    containers: ["Analytics Overview", "Recent Activity Feed", "Sidebar Navigation", "Quick Stats Card"]
  },
  {
    module: "Interviews",
    containers: ["Interview Scheduler", "Candidate Photo Capture", "Batch Upload Modal", "Hire/Reject Dialogs"]
  },
  {
    module: "Jobs",
    containers: ["Job Creation Form", "Pipeline Board", "Job Listing View", "Application Tracking"]
  },
  {
    module: "Employee/Company",
    containers: ["Company Profile", "Employee Directory", "Role Management"]
  }
];

// 2. Prepare Test Cases Data
const testCases = [];
projectStructure.forEach(m => {
  m.containers.forEach(container => {
    testCases.push({
      "Module": m.module,
      "Container/Function": container,
      "Test ID": `TC-${m.module.substring(0,3).toUpperCase()}-${Math.floor(Math.random()*1000)}`,
      "Requirement": `Verify ${container} functionality`,
      "Steps": "1. Navigate to page\n2. Interact with element\n3. Verify response",
      "Expected Result": "Success/Correct Data Display",
      "Status": "Pending",
      "Priority": "High"
    });
  });
});

// 3. Prepare Bug Tracker Template
const bugTracker = [
  {
    "Bug ID": "BUG-001",
    "Module": "Interview",
    "Description": "Photo capture failing on low bandwidth",
    "Severity": "Critical",
    "Status": "Open",
    "Reporter": "Automated Test",
    "Date Found": new Date().toLocaleDateString()
  }
];

// 4. Create Workbook
const wb = XLSX.utils.book_new();

// Add Sheets
const ws_cases = XLSX.utils.json_to_sheet(testCases);
const ws_bugs = XLSX.utils.json_to_sheet(bugTracker);

XLSX.utils.book_append_sheet(wb, ws_cases, "Test Cases");
XLSX.utils.book_append_sheet(wb, ws_bugs, "Bug Tracker");

// Write File
// We use an absolute path to ensure clarity on where it's saved
const fileName = "RIMS_Testing_Report.xlsx";
const filePath = path.join(__dirname, '..', fileName);
XLSX.writeFile(wb, filePath);

console.log(`✅ Success! Testing report generated at: ${filePath}`);
