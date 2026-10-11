// Dashboard Charts Initialization via Chart.js

document.addEventListener('DOMContentLoaded', function () {
    fetch('/api/v1/dashboard/charts?days=7')
        .then(response => response.json())
        .then(res => {
            if (!res.success) return;
            const data = res.data;

            // 1. Certificates Per Day Line Chart
            const ctxPerDay = document.getElementById('certsPerDayChart');
            if (ctxPerDay) {
                new Chart(ctxPerDay, {
                    type: 'line',
                    data: {
                        labels: data.certs_per_day.labels,
                        datasets: [{
                            label: 'Certificates Generated',
                            data: data.certs_per_day.data,
                            borderColor: '#2563eb',
                            backgroundColor: 'rgba(37, 99, 235, 0.1)',
                            borderWidth: 2.5,
                            fill: true,
                            tension: 0.35,
                            pointBackgroundColor: '#2563eb',
                            pointRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { precision: 0 }
                            }
                        }
                    }
                });
            }

            // 2. Status Doughnut Chart
            const ctxDonut = document.getElementById('statusDonutChart');
            if (ctxDonut) {
                new Chart(ctxDonut, {
                    type: 'doughnut',
                    data: {
                        labels: data.success_vs_fail.labels,
                        datasets: [{
                            data: data.success_vs_fail.data,
                            backgroundColor: ['#10b981', '#ef4444', '#94a3b8'],
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { boxWidth: 12, padding: 15 }
                            }
                        },
                        cutout: '68%'
                    }
                });
            }

            // 3. Volume by Organization Bar Chart
            const ctxOrg = document.getElementById('orgVolumeChart');
            if (ctxOrg) {
                new Chart(ctxOrg, {
                    type: 'bar',
                    data: {
                        labels: data.volume_by_org.labels.length > 0 ? data.volume_by_org.labels : ['No Data'],
                        datasets: [{
                            label: 'Certificates',
                            data: data.volume_by_org.data.length > 0 ? data.volume_by_org.data : [0],
                            backgroundColor: '#38bdf8',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true, ticks: { precision: 0 } }
                        }
                    }
                });
            }

            // 4. Jobs by Status Chart
            const ctxJobs = document.getElementById('jobsStatusChart');
            if (ctxJobs) {
                new Chart(ctxJobs, {
                    type: 'bar',
                    data: {
                        labels: data.jobs_by_status.labels,
                        datasets: [{
                            label: 'Job Count',
                            data: data.jobs_by_status.data,
                            backgroundColor: [
                                '#0ea5e9', // Queued
                                '#f59e0b', // Processing
                                '#10b981', // Completed
                                '#f97316', // Completed with failures
                                '#ef4444', // Failed
                                '#64748b'  // Cancelled
                            ],
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            y: { beginAtZero: true, ticks: { precision: 0 } }
                        }
                    }
                });
            }
        })
        .catch(err => console.error("Error loading dashboard chart data:", err));
});
