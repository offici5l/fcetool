const form = document.getElementById('extractForm');
const submitBtn = document.getElementById('submitBtn');
const statusMessage = document.getElementById('statusMessage');
const downloadSection = document.getElementById('downloadSection');
const downloadBtn = document.getElementById('downloadBtn');
const newExtractionBtn = document.getElementById('newExtractionBtn');
const durationText = document.getElementById('durationText');
const filenameText = document.getElementById('filenameText');
const statusText = document.getElementById('statusText');
const urlInput = document.getElementById('firmwareUrl');
const partitionSelect = document.getElementById('partitionSelect');

document.addEventListener('DOMContentLoaded', () => {
    populatePartitionSelect();
    setupEventListeners();
    setLoading(false);
});

function populatePartitionSelect() {
    if (!partitionSelect) return;

    SUPPORTED_FILES.forEach(key => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = key;
        partitionSelect.appendChild(option);
    });
}

function setupEventListeners() {
    form.addEventListener('submit', handleSubmit);
    newExtractionBtn.addEventListener('click', resetForm);
}

async function handleSubmit(e) {
    e.preventDefault();

    hideMessage();
    hideDownloadSection();

    const selectedPartition = partitionSelect.value;

    if (!selectedPartition) {
        showMessage('<i class="fas fa-exclamation-circle"></i> Please select a partition image to extract', 'error');
        return;
    }

    const payload = {
        url: urlInput.value,
        images: selectedPartition
    };

    setLoading(true);

    try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.extract}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            handleSuccess(data);
        } else {
            handleError(data, response.status);
        }
    } catch (error) {
        showMessage('<i class="fas fa-exclamation-triangle"></i> Network error: Unable to connect to the server', 'error');
    } finally {
        setLoading(false);
    }
}

function handleSuccess(data) {
    if (data.status === 'cached') {
        statusText.innerHTML = '<i class="fas fa-rocket" style="color: var(--info); margin-right: 0.25rem;"></i> Retrieved from cache';
        showMessage(`<i class="fas fa-bolt"></i> ${data.message}`, 'info');
    } else if (data.status === 'completed') {
        statusText.innerHTML = '<i class="fas fa-check" style="color: var(--success); margin-right: 0.25rem;"></i> Extraction completed';
        showMessage(`<i class="fas fa-check-circle"></i> ${data.message}`, 'success');
    }

    downloadBtn.href = data.download_url;
    downloadBtn.download = data.filename;
    durationText.textContent = `${data.duration_seconds}s`;
    filenameText.textContent = data.filename;

    hideForm();
    showDownloadSection();
}

function handleError(data, statusCode) {
    let errorIcon = '<i class="fas fa-exclamation-circle"></i>';
    let errorType = 'error';
    
    // The backend now always returns a 'message' field in the JSON body
    let errorText = data.message || data.detail || 'An unexpected error occurred';

    // Handle specific status codes based on the new backend logic
    if (statusCode === 429) {
        errorIcon = '<i class="fas fa-clock"></i>';
        errorType = 'warning';
    } else if (errorText.toLowerCase().includes('capacity')) {
        errorIcon = '<i class="fas fa-hourglass-half"></i>';
        errorType = 'warning';
    }

    showMessage(`${errorIcon} ${errorText}`, errorType);
}

function showMessage(message, type) {
    statusMessage.innerHTML = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
}

function hideMessage() {
    statusMessage.classList.add('hidden');
}

function showDownloadSection() {
    downloadSection.classList.remove('hidden');
}

function hideDownloadSection() {
    downloadSection.classList.add('hidden');
}

function hideForm() {
    form.classList.add('hidden');
}

function showForm() {
    form.classList.remove('hidden');
}

function resetForm() {
    hideDownloadSection();
    hideMessage();
    showForm();
    urlInput.value = '';
    partitionSelect.value = '';
}

function setLoading(loading) {
    submitBtn.disabled = loading;
    urlInput.disabled = loading;
    partitionSelect.disabled = loading;

    if (loading) {
        submitBtn.innerHTML = `
            <div class="spinner"></div>
            <span>Processing...</span>
        `;
    } else {
        submitBtn.innerHTML = `
            <i class="fas fa-bolt"></i>
            <span>Extract Now</span>
        `;
    }
}
