#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
## user_problem_statement: "Implementar reporte tipo Power BI (Item-Estados) con filtros y exportación; luego completar exportación Kardex"
## backend:
##   - task: "Reporte estados por Item (API + export CSV)"
##     implemented: true
##     working: true
##     file: "backend/server.py"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: false
##     status_history:
##       - working: true
##         agent: "main"
##         comment: "Implementado GET /api/reportes/estados-item y /api/reportes/estados-item/export (CSV). Probado con curl (200, devuelve rows y CSV descargable). Incluye toggle include_tienda para que no cuente en Total cuando está apagado."
##       - working: true
##         agent: "testing"
##         comment: "✅ COMPREHENSIVE E2E TESTING COMPLETED: 1) Login admin (eduard/eduard123) ✅ 2) GET /api/reportes/estados-item - status 200, JSON structure validated (updated_at, include_tienda, rows) ✅ 3) include_tienda=true/false toggle working correctly, tienda key present/absent as expected ✅ 4) Filters working (prioridad=urgente, search parameter) ✅ 5) CSV export working - proper content-type (text/csv), Content-Disposition header with filename, correct column structure including conditional Tienda column ✅ All 20/20 specific tests passed. API fully functional."
## frontend:
##   - task: "UI Reporte estados por Item (filtros + tabla + export PDF/Excel + toggle Tienda)"
##     implemented: true
##     working: true
##     file: "frontend/src/pages/ReporteEstadosItem.jsx"
##     stuck_count: 0
##     priority: "high"
##     needs_retesting: false
##     status_history:
##       - working: true
##         agent: "main"
##         comment: "Nueva página /reportes/estados-item. Capturas OK: carga tabla, toggle Tienda y re-filtra."
##       - working: true
##         agent: "testing"
##         comment: "✅ COMPREHENSIVE E2E TESTING COMPLETED: 1) Login eduard/eduard123 ✅ 2) Navigation to /reportes/estados-item ✅ 3) Table loads with 3 rows of data ✅ 4) Row selection working ✅ 5) Ver detalles modal opens successfully ✅ 6) State dropdown in modal functional (limited options available) ✅ 7) Modal close working ✅ 8) Toggle 'Mostrar Tienda' + Filtrar working ✅ 9) Excel export working (CSV download successful) ✅ 10) PDF export FIXED and working (jsPDF autoTable import issue resolved) ✅ All core functionalities tested and working. Minor: State dropdown had limited options but this is expected based on data. Fixed PDF export compatibility issue with jsPDF autoTable plugin."
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 1
##   run_ui: true
## test_plan:
##   current_focus:
##     - "Validar e2e Reporte estados por Item: filtros, toggle tienda, export excel, export PDF"
##   stuck_tasks: []
##   test_all: false
##   test_priority: "high_first"
## agent_communication:
##   - agent: "main"
##     message: "Se agregó reporte tipo Power BI (Item-Estados) y endpoints. Pendiente: testing subagent e2e completo (incluye descarga de archivos)."
##   - agent: "testing"
##     message: "✅ BACKEND TESTING COMPLETED SUCCESSFULLY: Reporte estados-item API fully tested and working. All endpoints (GET /api/reportes/estados-item, CSV export, filters, include_tienda toggle) are functioning correctly. Created comprehensive test suite at /app/backend/tests/test_reporte_estados_item.py. Ready for main agent to summarize and finish."
##   - agent: "testing"
##     message: "✅ FRONTEND E2E TESTING COMPLETED SUCCESSFULLY: All 10 test steps passed including login, navigation, table loading, row selection, modal interactions, filters, and both Excel/PDF exports. Fixed critical PDF export issue (jsPDF autoTable compatibility). Module is fully functional and ready for production use."