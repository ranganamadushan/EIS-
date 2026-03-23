// Global State
let globalSamples = [];
let plotlyData = [];
let chartLayout = {};
let fileNameDisplay = "";
// Extended palette roughly matching matplotlib tab20 + tab20b + tab20c
let customColors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
    '#393b79', '#5254a3', '#6b6ecf', '#9c9ede', '#637939', '#8ca252', '#b5cf6b', '#cedb9c', '#8c6d31', '#bd9e39'
];

document.addEventListener('DOMContentLoaded', () => {
    initChart();
    attachEventListeners();
});

function initChart() {
    chartLayout = {
        title: {
            text: 'Nyquist Plot: <b style="color:#57606a; font-size:14px;">No Data</b>',
            font: { color: '#24292f', size: 20, family: 'Inter, sans-serif' }
        },
        paper_bgcolor: '#ffffff',
        plot_bgcolor: '#ffffff',
        xaxis: {
            title: { text: "Z' (kΩ)", font: { color: '#24292f', size: 14, weight: 'bold' } },
            tickfont: { color: '#57606a' },
            gridcolor: '#e1e4e8',
            zerolinecolor: '#57606a',
            zerolinewidth: 1,
            showgrid: true
        },
        yaxis: {
            title: { text: "-Z'' (kΩ)", font: { color: '#24292f', size: 14, weight: 'bold' } },
            tickfont: { color: '#57606a' },
            gridcolor: '#e1e4e8',
            zerolinecolor: '#57606a',
            zerolinewidth: 1,
            showgrid: true
        },
        showlegend: false, // Custom sidebar handles legends
        margin: { l: 90, r: 90, t: 80, b: 120 }, // Increased margins for labels
        hovermode: 'closest',
        dragmode: 'pan'
    };
    
    let config = { 
        responsive: true, 
        displayModeBar: true,
        scrollZoom: true,
        editable: false // Reverted to false as per user preference
    };
    
    Plotly.newPlot('plot-container', [], chartLayout, config);
}

function attachEventListeners() {
    document.getElementById('csv-upload').addEventListener('change', handleFileUpload);
    document.getElementById('apply-limits-btn').addEventListener('click', applyLimits);
    document.getElementById('auto-scale-btn').addEventListener('click', forceAutoscale);
    document.getElementById('show-lines-toggle').addEventListener('change', updatePlot);
    document.getElementById('export-btn').addEventListener('click', exportSelectedCSV);
    document.getElementById('select-all-btn').addEventListener('click', () => setAllTraces(true));
    document.getElementById('clear-all-btn').addEventListener('click', () => setAllTraces(false));
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    fileNameDisplay = file.name;
    document.getElementById('file-name').textContent = fileNameDisplay;

    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target.result;
        parseCSVData(text);
    };
    reader.onerror = () => {
        alert("Failed to read the file.");
    };
    reader.readAsText(file);
}

function parseCSVData(rawText) {
    globalSamples = []; // Clear existing
    let lowerText = rawText.toLowerCase();
    
    // Fallback detection (similar to python script logic)
    if (!lowerText.includes('freq') && !lowerText.includes('hz')) {
        alert(`Could not detect a valid format in:\n${fileNameDisplay}`);
        return;
    }

    let normalizedText = rawText.replace(/;/g, ',').replace(/\t/g, ',');
    let lines = normalizedText.split(/\r?\n/);
    
    let samples = [];
    let counts = {};
    let i = 0;

    while (i < lines.length) {
        let line = lines[i];
        let lowerLine = line.toLowerCase();

        if (lowerLine.includes('freq') && lowerLine.includes('hz')) {
            let cells = line.split(',').map(c => c.trim().replace(/^['"](.*)['"]$/, '$1').toLowerCase());
            
            let zRealIdx = 7, zImagIdx = 8;
            let foundRealIdx = cells.findIndex(h => h.includes("z'") && h.includes("ohm") && !h.includes("-"));
            if (foundRealIdx !== -1) zRealIdx = foundRealIdx;
            
            let foundImagIdx = cells.findIndex(h => h.includes("-z''") && h.includes("ohm"));
            if (foundImagIdx !== -1) zImagIdx = foundImagIdx;

            let rawName = "Sample";
            if (i > 0 && lines[i-1].trim() !== '') {
                rawName = lines[i-1].trim().replace(/^['",]{1,}/, '').replace(/['",]{1,}$/, '');
            }

            // Extract legend name from the last comma-separated part (Concentration)
            let cleanName = rawName;
            let parts = rawName.split(',').map(p => p.trim()).filter(p => p !== '');
            if (parts.length > 0) {
                cleanName = parts[parts.length - 1]; // Use the last non-empty field
            }

            counts[cleanName] = (counts[cleanName] || 0) + 1;
            let uniqueName = `${cleanName} (Run ${counts[cleanName]})`;

            let zReal = [], zImag = [];
            i++;

            while (i < lines.length) {
                let dataLine = lines[i].trim();
                if (!dataLine) break;

                let dataCells = dataLine.split(',').map(c => c.trim().replace(/^['"](.*)['"]$/, '$1'));
                if (dataCells.length <= Math.max(zRealIdx, zImagIdx)) break;

                let firstVal = parseFloat(dataCells[0]);
                if (isNaN(firstVal)) break;

                let zr = parseFloat(dataCells[zRealIdx]);
                let zi = parseFloat(dataCells[zImagIdx]);
                
                if (!isNaN(zr) && !isNaN(zi)) {
                    zReal.push(zr / 1000.0);
                    zImag.push(zi / 1000.0);
                }
                i++;
            }

            if (zReal.length > 0 && zImag.length > 0) {
                samples.push({
                    base_name: cleanName,
                    name: uniqueName,
                    z_real: zReal,
                    z_imag: zImag,
                    visible: true
                });
            }
            continue;
        }
        i++;
    }

    if (samples.length === 0) {
        alert("No valid numerical data pairs found in the CSV file.");
        return;
    }

    globalSamples = samples;
    forceAutoscale(); // Also updates UI components
}

function renderSidebar() {
    const traceList = document.getElementById('trace-list');
    traceList.innerHTML = '';

    if (globalSamples.length === 0) {
        traceList.innerHTML = `<div class="empty-state">Upload a CSV to view traces</div>`;
        return;
    }

    let groups = {};
    globalSamples.forEach((s, idx) => {
        if (!groups[s.base_name]) groups[s.base_name] = [];
        groups[s.base_name].push(idx);
    });

    for (let baseName in groups) {
        let indices = groups[baseName];
        
        let groupDiv = document.createElement('div');
        groupDiv.className = 'trace-group';

        let groupTitle = document.createElement('div');
        groupTitle.className = 'trace-group-title';
        groupTitle.innerHTML = `<span title="${baseName}" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">${baseName}</span> <span style="font-size: 0.8rem; color: #8b949e;">Toggle</span>`;
        groupTitle.onclick = () => {
            let allVisible = indices.every(i => globalSamples[i].visible);
            let newState = !allVisible;
            indices.forEach(i => globalSamples[i].visible = newState);
            updateCheckboxes();
            updatePlot();
        };
        groupDiv.appendChild(groupTitle);

        indices.forEach(idx => {
            let s = globalSamples[idx];
            let color = customColors[idx % customColors.length];
            
            let itemDiv = document.createElement('div');
            itemDiv.className = 'trace-item';

            let colorInd = document.createElement('div');
            colorInd.className = 'color-indicator';
            colorInd.style.backgroundColor = color;
            
            let lbl = document.createElement('label');
            lbl.className = 'checkbox-label';
            
            let cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.checked = s.visible;
            cb.dataset.idx = idx;
            cb.onchange = (e) => {
                globalSamples[idx].visible = e.target.checked;
                updatePlot();
            };
            
            lbl.appendChild(cb);
            lbl.appendChild(document.createTextNode(s.name));
            
            itemDiv.appendChild(colorInd);
            itemDiv.appendChild(lbl);
            groupDiv.appendChild(itemDiv);
        });

        traceList.appendChild(groupDiv);
    }
}

function updateCheckboxes() {
    const cbs = document.querySelectorAll('.trace-item input[type="checkbox"]');
    cbs.forEach(cb => {
        let idx = parseInt(cb.dataset.idx);
        cb.checked = globalSamples[idx].visible;
    });
}

function updatePlot() {
    plotlyData = [];
    let annotations = [];
    let seenBaseNames = new Set();
    
    const showLines = document.getElementById('show-lines-toggle').checked;
    const drawMode = showLines ? 'lines+markers' : 'markers';
    const symbols = ['circle', 'square', 'diamond', 'triangle-up', 'triangle-down', 'cross', 'x', 'pentagon', 'hexagram', 'star'];

    globalSamples.forEach((s, idx) => {
        if (!s.visible) return;

        let color = customColors[idx % customColors.length];
        let symbol = symbols[idx % symbols.length];
        
        plotlyData.push({
            x: s.z_real,
            y: s.z_imag,
            mode: drawMode,
            name: s.name,
            line: { width: 1.5, color: color },
            marker: { size: 6, symbol: symbol },
            type: 'scatter'
        });

        if (!seenBaseNames.has(s.base_name)) {
            seenBaseNames.add(s.base_name);
            if (s.z_real.length > 0) {
                // Point the arrow to the PEAK of the Nyquist arc (Maximum Y/-Z'' value)
                let peakIdx = 0;
                let maxY = -Infinity;
                for (let j = 0; j < s.z_imag.length; j++) {
                    if (s.z_imag[j] > maxY) {
                        maxY = s.z_imag[j];
                        peakIdx = j;
                    }
                }
                
                // Double column stacking (all upwards) to avoid bottom cutoff
                let colIdx = idx % 2;
                let rowIdx = Math.floor(idx / 2);
                let axOffset = 40 + (colIdx * 110);
                let ayOffset = -20 - (rowIdx * 22); 

                annotations.push({
                    x: s.z_real[peakIdx],
                    y: s.z_imag[peakIdx],
                    xref: 'x', yref: 'y',
                    text: `<b>${s.base_name}</b>`,
                    showarrow: true,
                    arrowhead: 1,
                    arrowsize: 0.8,
                    arrowwidth: 1,
                    arrowcolor: color,
                    ax: axOffset,
                    ay: ayOffset, 
                    font: { color: color, size: 12, family: 'Inter, sans-serif' },
                    bgcolor: 'rgba(255, 255, 255, 0.9)',
                    bordercolor: color,
                    borderwidth: 1,
                    borderpad: 2
                });
            }
        }
    });

    let finalLayout = JSON.parse(JSON.stringify(chartLayout));
    if (fileNameDisplay) {
        finalLayout.title.text = `Nyquist Plot: <span style="color:#0969da;">${fileNameDisplay}</span>`;
    }
    finalLayout.annotations = annotations;
    
    const autoScaleToggle = document.getElementById('auto-scale-toggle');
    if (autoScaleToggle.checked) {
        finalLayout.xaxis.autorange = true;
        finalLayout.yaxis.autorange = true;
        
        document.getElementById('x-min').value = '';
        document.getElementById('x-max').value = '';
        document.getElementById('y-min').value = '';
        document.getElementById('y-max').value = '';
    } else {
        const xmin = document.getElementById('x-min').value;
        const xmax = document.getElementById('x-max').value;
        const ymin = document.getElementById('y-min').value;
        const ymax = document.getElementById('y-max').value;
        
        if (xmin !== '' && xmax !== '') {
            finalLayout.xaxis.range = [parseFloat(xmin), parseFloat(xmax)];
            finalLayout.xaxis.autorange = false;
        } else {
            finalLayout.xaxis.autorange = true;
        }
        
        if (ymin !== '' && ymax !== '') {
            finalLayout.yaxis.range = [parseFloat(ymin), parseFloat(ymax)];
            finalLayout.yaxis.autorange = false;
        } else {
            finalLayout.yaxis.autorange = true;
        }
    }

    Plotly.react('plot-container', plotlyData, finalLayout);
}

function applyLimits() {
    document.getElementById('auto-scale-toggle').checked = false;
    
    // We update the plot to reflect the customized layout ranges
    updatePlot();
}

function forceAutoscale() {
    document.getElementById('auto-scale-toggle').checked = true;
    renderSidebar();
    updatePlot();
}

function setAllTraces(state) {
    globalSamples.forEach(s => s.visible = state);
    updateCheckboxes();
    updatePlot();
}

function exportSelectedCSV() {
    let selected = globalSamples.filter(s => s.visible);
    if (selected.length === 0) {
        alert("Please explicitly check at least one box to export.");
        return;
    }

    let headers = [];
    selected.forEach(s => {
        headers.push(`"${s.name} Z' (kOhm)"`);
        headers.push(`"${s.name} -Z'' (kOhm)"`);
    });

    let maxLen = Math.max(...selected.map(s => s.z_real.length));
    let rows = [headers.join(',')];

    for (let i = 0; i < maxLen; i++) {
        let row = [];
        selected.forEach(s => {
            if (i < s.z_real.length) {
                row.push(s.z_real[i]);
                row.push(s.z_imag[i]);
            } else {
                row.push('');
                row.push('');
            }
        });
        rows.push(row.join(','));
    }

    let csvContent = rows.join('\r\n');
    let blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    let link = document.createElement("a");
    let url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "Cleaned_EIS_Data.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
