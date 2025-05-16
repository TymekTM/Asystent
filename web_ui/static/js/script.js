// Theme Switching Logic
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const lightIcon = document.getElementById('theme-icon-light');
const darkIcon = document.getElementById('theme-icon-dark');
const currentTheme = localStorage.getItem('theme');
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

function applyTheme(theme) {
    if (theme === 'dark') {
        document.body.setAttribute('data-bs-theme', 'dark');
        if (lightIcon) lightIcon.classList.add('d-none');
        if (darkIcon) darkIcon.classList.remove('d-none');
    } else {
        document.body.setAttribute('data-bs-theme', 'light');
        if (lightIcon) lightIcon.classList.remove('d-none');
        if (darkIcon) darkIcon.classList.add('d-none');
    }
}

// Apply initial theme based on preference or system setting
if (currentTheme) {
    applyTheme(currentTheme);
} else if (prefersDarkScheme.matches) {
    applyTheme('dark');
} else {
     applyTheme('light'); // Default to light
}


// Listener for theme toggle button
if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        let newTheme = document.body.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    });
}

// Listener for system theme changes
prefersDarkScheme.addEventListener('change', (e) => {
    // Only change if no explicit theme is set in local storage
    if (!localStorage.getItem('theme')) {
        applyTheme(e.matches ? 'dark' : 'light');
    }
});

// --- Other Global JS (if any) ---
console.log("Assistant CP UI script loaded.");


// Audio device selection: cache and refresh
let cachedAudioDevices = null;
function populateAudioDevices(devices) {
    const select = document.getElementById('mic-device-id-select');
    if (!select) return;
    const current = select.getAttribute('data-current-value');
    select.innerHTML = '';
    devices.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id;
        opt.textContent = d.name + (d.is_default ? ' (Domyślny)' : '');
        if (current != null && d.id.toString() === current.toString()) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });
}
async function loadAudioDevices(useCache = true) {
    // Show loading state on refresh button when not using cache
    const refreshBtn = document.getElementById('refresh-mic-devices-btn');
    let originalBtnHTML;
    if (!useCache && refreshBtn) {
        refreshBtn.disabled = true;
        originalBtnHTML = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm text-secondary" role="status" aria-hidden="true"></span>';
    }
    if (useCache && cachedAudioDevices) {
        populateAudioDevices(cachedAudioDevices);
        return;
    }
    try {
        const res = await fetch('/api/audio/devices');
        if (res.ok) {
            const devices = await res.json();
            cachedAudioDevices = devices;
            populateAudioDevices(devices);
        } else {
            console.error('Failed to load audio devices');
        }
    } catch (e) {
        console.error('Error fetching audio devices:', e);
    }
}

// Load devices on page load and set up refresh button
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
    // Audio device selection
    if (document.getElementById('mic-device-id-select')) {
        // Load cached devices first; will fetch on first call
        loadAudioDevices();
        const btn = document.getElementById('refresh-mic-devices-btn');
        if (btn) {
            btn.addEventListener('click', function() {
                loadAudioDevices(false);
            });
        }
    }

    // Close flash messages
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Close after 5 seconds
    });
    
    // --- LTM Page Listeners ---
    const addMemoryForm = document.getElementById('add-memory-form');
    const addMemoryStatus = document.getElementById('add-memory-status');
    const searchMemoryInput = document.getElementById('search-memory-input');
    const searchMemoryButton = document.getElementById('search-memory-button');
    const clearSearchButton = document.getElementById('clear-search-button'); // Added clear button

    if (addMemoryForm) {
        addMemoryForm.addEventListener('submit', function(event) {
            event.preventDefault();
            addMemoryStatus.textContent = '';
            addMemoryStatus.className = '';
            // Disable button to prevent double submit
            const submitBtn = addMemoryForm.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.disabled = true;
            const formData = new FormData(addMemoryForm);
            const content = formData.get('content');
            const user = formData.get('user') || null;
            fetch('/api/ltm/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: content, user: user }),
            })
            .then(response => response.json().then(data => ({ status: response.status, body: data })))
            .then(({ status, body }) => {
                if (status === 201) {
                    addMemoryStatus.textContent = `Dodano wspomnienie (ID: ${body.id}).`;
                    addMemoryStatus.className = 'mt-2 text-success';
                    addMemoryForm.reset();
                    fetchAndDisplayMemories(searchMemoryInput ? searchMemoryInput.value : '');
                } else {
                    addMemoryStatus.textContent = `Błąd: ${body.error || 'Nie udało się dodać wspomnienia.'}`;
                    addMemoryStatus.className = 'mt-2 text-danger';
                }
            })
            .catch(error => {
                console.error('Error adding memory:', error);
                addMemoryStatus.textContent = 'Wystąpił błąd sieciowy podczas dodawania.';
                addMemoryStatus.className = 'mt-2 text-danger';
            })
            .finally(() => {
                if (submitBtn) submitBtn.disabled = false;
            });
        });
    }

    if (searchMemoryButton && searchMemoryInput) {
        searchMemoryButton.addEventListener('click', function() {
            fetchAndDisplayMemories(searchMemoryInput.value);
        });

        // Allow searching on pressing Enter in the input field
        searchMemoryInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent potential form submission if it were in a form
                fetchAndDisplayMemories(searchMemoryInput.value);
            }
        });
    }

     if (clearSearchButton && searchMemoryInput) { // Added listener for clear button
        clearSearchButton.addEventListener('click', function() {
            searchMemoryInput.value = ''; // Clear the input
            fetchAndDisplayMemories(); // Fetch all memories
        });
    }

    // Initial load of memories and attachment of delete listeners
    if (document.getElementById('memory-list')) {
       fetchAndDisplayMemories(); // Load all memories initially, this will also attach listeners
    }
});

// Helper function to escape HTML (prevent XSS)
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) {
        return '';
    }
    return unsafe
         .toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// --- LTM Page Specific Functions ---

function fetchAndDisplayMemories(query = '') {
    const memoryList = document.getElementById('memory-list');
    const url = `/api/ltm/get${query ? '?query=' + encodeURIComponent(query) : ''}`;

    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(memories => {
            memoryList.innerHTML = ''; // Clear current list
            if (memories.length > 0) {
                const ul = document.createElement('ul');
                ul.className = 'list-group';
                memories.forEach(memory => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-start';
                    li.dataset.id = memory.id;

                    const timestamp = memory.timestamp ? memory.timestamp.split('.')[0] : 'N/A'; // Format timestamp

                    li.innerHTML = `
                        <div class="ms-2 me-auto">
                            <div class="fw-bold">ID: ${memory.id} | User: ${memory.user || 'N/A'}</div>
                            <small class="text-muted">${timestamp}</small>
                            <p class="mb-1">${escapeHtml(memory.content)}</p>
                        </div>
                        <button class="btn btn-danger btn-sm delete-memory-button" data-id="${memory.id}">Usuń</button>
                    `;
                    ul.appendChild(li);
                });
                memoryList.appendChild(ul);
                // Re-attach delete listeners after updating list
                attachDeleteMemoryListeners();
            } else {
                memoryList.innerHTML = '<p>Brak zapisanych wspomnień' + (query ? ' pasujących do wyszukiwania.' : '.') + '</p>';
            }
        })
        .catch(error => {
            console.error('Error fetching memories:', error);
            memoryList.innerHTML = '<p class="text-danger">Wystąpił błąd podczas pobierania wspomnień.</p>';
        });
}

function attachDeleteMemoryListeners() {
    document.querySelectorAll('.delete-memory-button').forEach(button => {
        // Remove existing listener to prevent duplicates if re-attaching
        button.replaceWith(button.cloneNode(true));
    });
    // Add new listeners
    document.querySelectorAll('.delete-memory-button').forEach(button => {
        button.addEventListener('click', function() {
            const memoryId = this.dataset.id;
            const statusDiv = document.getElementById('delete-memory-status');
            statusDiv.textContent = ''; // Clear previous status

            if (confirm(`Czy na pewno chcesz usunąć wspomnienie o ID ${memoryId}?`)) {
                fetch(`/api/ltm/delete/${memoryId}`, {
                    method: 'DELETE',
                })
                .then(response => response.json().then(data => ({ status: response.status, body: data })))
                .then(({ status, body }) => {
                    if (status === 200) {
                        statusDiv.textContent = `Usunięto wspomnienie ID ${memoryId}.`;
                        statusDiv.className = 'mt-2 text-success';
                        // Remove the item from the list visually
                        const listItem = document.querySelector(`li[data-id="${memoryId}"]`);
                        if (listItem) {
                            listItem.remove();
                        }
                        // Optional: Refresh the whole list if needed, though removing is often sufficient
                        // fetchAndDisplayMemories(document.getElementById('search-memory-input').value);
                    } else {
                        statusDiv.textContent = `Błąd: ${body.error || 'Nie udało się usunąć wspomnienia.'}`;
                        statusDiv.className = 'mt-2 text-danger';
                    }
                })
                .catch(error => {
                    console.error('Error deleting memory:', error);
                    statusDiv.textContent = 'Wystąpił błąd sieciowy podczas usuwania.';
                     statusDiv.className = 'mt-2 text-danger';
                });
            }
        });
    });
}

// --- Testy jednostkowe Dev tab ---
// (Logika dynamiczna jest w dev.html, ale można tu dodać obsługę WebSocket/pollingu globalnie w przyszłości)
