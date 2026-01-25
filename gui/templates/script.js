

function switchTab(toTabElement) {
    // Hide all
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show target
    toTabElement.classList.add('active');
}

