// Bulk Generation JavaScript Logic

function toggleManualNewOrg(val) {
    const container = document.getElementById('manualNewOrgContainer');
    const input = document.getElementById('manualNewOrgName');
    if (val === 'NEW') {
        container.style.display = 'block';
        input.required = true;
    } else {
        container.style.display = 'none';
        input.required = false;
    }
}

function toggleCsvNewOrg(val) {
    const container = document.getElementById('csvNewOrgContainer');
    const input = container.querySelector('input');
    if (val === 'NEW') {
        container.style.display = 'block';
        input.required = true;
    } else {
        container.style.display = 'none';
        input.required = false;
    }
}

function updateRowNumbers() {
    const rows = document.querySelectorAll('#recipientsBody tr');
    rows.forEach((row, idx) => {
        row.querySelector('.row-num').textContent = idx + 1;
    });
    const countText = document.getElementById('recipientCountText');
    if (countText) {
        countText.textContent = `${rows.length} recipient rows configured`;
    }
}

function addRecipientRow() {
    const tbody = document.getElementById('recipientsBody');
    const rowCount = tbody.querySelectorAll('tr').length + 1;
    const tr = document.createElement('tr');
    tr.className = 'recipient-row';
    tr.innerHTML = `
        <td class="text-center text-muted fw-semibold row-num">${rowCount}</td>
        <td>
            <input type="text" class="form-control form-control-sm rec-name" placeholder="Full Name" required>
        </td>
        <td>
            <input type="email" class="form-control form-control-sm rec-email" placeholder="Email" required>
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-outline-danger btn-sm p-1" onclick="removeRecipientRow(this)" title="Remove row">
                <i class="bi bi-trash"></i>
            </button>
        </td>
    `;
    tbody.appendChild(tr);
    updateRowNumbers();
}

function removeRecipientRow(btn) {
    const tbody = document.getElementById('recipientsBody');
    if (tbody.querySelectorAll('tr').length <= 1) {
        alert("At least one recipient row must be present.");
        return;
    }
    const row = btn.closest('tr');
    row.remove();
    updateRowNumbers();
}

function validateAndSubmitManual(e) {
    const orgSelect = document.getElementById('manualOrgSelect');
    const newOrgName = document.getElementById('manualNewOrgName');
    if (!orgSelect.value) {
        alert("Please select an organization or choose '+ Register New Organization'.");
        e.preventDefault();
        return false;
    }
    if (orgSelect.value === 'NEW' && !newOrgName.value.trim()) {
        alert("Please specify the new organization name.");
        e.preventDefault();
        return false;
    }

    const rows = document.querySelectorAll('#recipientsBody tr');
    const recipients = [];
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    let hasError = false;

    rows.forEach((row, idx) => {
        const nameInput = row.querySelector('.rec-name');
        const emailInput = row.querySelector('.rec-email');
        const name = nameInput.value.trim();
        const email = emailInput.value.trim();

        if (!name || !email) {
            alert(`Row #${idx + 1} has empty name or email.`);
            hasError = true;
            return;
        }

        if (!emailRegex.test(email)) {
            alert(`Row #${idx + 1} has an invalid email format: "${email}".`);
            hasError = true;
            return;
        }

        recipients.push({ name: name, email: email });
    });

    if (hasError) {
        e.preventDefault();
        return false;
    }

    if (recipients.length === 0) {
        alert("Please add at least one recipient.");
        e.preventDefault();
        return false;
    }

    document.getElementById('recipientsJson').value = JSON.stringify(recipients);
    return true;
}

function openCertificatePreview() {
    const modalEl = document.getElementById('certPreviewModal');
    const modal = new bootstrap.Modal(modalEl);
    const container = document.getElementById('previewModalContent');
    container.innerHTML = '<div class="spinner-border text-primary my-5" role="status"></div>';
    modal.show();

    // Collect field values
    const orgSelect = document.getElementById('manualOrgSelect');
    let orgName = orgSelect.options[orgSelect.selectedIndex] ? orgSelect.options[orgSelect.selectedIndex].text : "CertiFlow Academy";
    if (orgSelect.value === 'NEW') {
        orgName = document.getElementById('manualNewOrgName').value || "New Organization";
    }
    const courseName = document.getElementById('manualCourseName').value || "Full-Stack Software Architecture";
    const certTitle = document.getElementById('manualCertTitle').value || "Certificate of Completion";
    const sigName = document.getElementById('manualSignatoryName').value || "Dr. Rajesh Kumar";
    const sigDesig = document.getElementById('manualSignatoryDesig').value || "Director of Academic Affairs";

    const firstRow = document.querySelector('#recipientsBody tr');
    let recName = "Johnathan Doe";
    let recEmail = "johnathan.doe@example.com";
    if (firstRow) {
        const n = firstRow.querySelector('.rec-name').value.trim();
        const e = firstRow.querySelector('.rec-email').value.trim();
        if (n) recName = n;
        if (e) recEmail = e;
    }

    // Call server to render template
    fetch('/bulk-generation/preview-html', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({
            organization_name: orgName,
            course_name: courseName,
            certificate_title: certTitle,
            recipient_name: recName,
            recipient_email: recEmail,
            signatory_name: sigName,
            signatory_designation: sigDesig
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success && data.html) {
            // Render iframe for isolated preview
            container.innerHTML = `<iframe srcdoc="${escapeHtml(data.html)}" style="width: 100%; height: 560px; border: none; background: #ffffff;"></iframe>`;
        } else {
            container.innerHTML = `<div class="p-4 text-danger">Failed to generate preview: ${data.error || 'Server error'}</div>`;
        }
    })
    .catch(err => {
        container.innerHTML = `<div class="p-4 text-danger">Error loading preview: ${err}</div>`;
    });
}

function escapeHtml(text) {
    return text.replace(/"/g, '&quot;');
}
