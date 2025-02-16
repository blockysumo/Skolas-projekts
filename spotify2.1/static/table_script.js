document.addEventListener('DOMContentLoaded', function() {
    updateVisibleRows();
});

function updateVisibleRows() {
    const rows = document.querySelectorAll('.table-hover tbody tr');
    rows.forEach((row, index) => {
        row.style.display = index < 10 ? '' : 'none';
    });
}

function sortTable(columnIndex, isNumeric = false) {
    const table = document.querySelector('.table-hover');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    
    // Toggle sorting direction
    const isAsc = !header.classList.contains('asc');
    header.classList.remove('asc', 'desc');
    header.classList.add(isAsc ? 'asc' : 'desc');

    rows.sort((a, b) => {
        const aVal = getSortValue(a, columnIndex);
        const bVal = getSortValue(b, columnIndex);
        
        if (columnIndex <= 1) { // Track and Artist columns
            return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
        return isAsc ? aVal - bVal : bVal - aVal;
    });

    // Rebuild table
    rows.forEach(row => tbody.appendChild(row));
    updateVisibleRows();
}

function getSortValue(row, columnIndex) {
    const cell = row.children[columnIndex];
    switch(columnIndex) {
        case 0: // Track
        case 1: // Artist
            return cell.textContent.trim().toLowerCase();
        
        case 3: // Total Time
            return parseInt(cell.dataset.ms); // Use raw ms value
            
        case 2: // Plays
            return parseInt(cell.textContent);
            
        default:
            return 0;
    }
}

function sortSkipRate(columnIndex) {
    const table = document.querySelector('.table-hover');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    
    const isAsc = !header.classList.contains('asc');
    header.classList.remove('asc', 'desc');
    header.classList.add(isAsc ? 'asc' : 'desc');

    rows.sort((a, b) => {
        const aRate = parseFloat(a.children[columnIndex].querySelector('.badge').textContent);
        const bRate = parseFloat(b.children[columnIndex].querySelector('.badge').textContent);
        return isAsc ? aRate - bRate : bRate - aRate;
    });

    rows.forEach(row => tbody.appendChild(row));
    updateVisibleRows();
}