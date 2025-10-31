document.addEventListener('DOMContentLoaded', () => {

    // --- ELEMENT REFERENCES ---
    const palette = document.getElementById('palette');
    const canvas = document.getElementById('canvas');
    const saveBtn = document.getElementById('save-btn');
    const deleteBtn = document.getElementById('delete-btn');

    // --- STATE VARIABLES ---
    let selectedElement = null;
    let isDragging = false;
    let dragOffsetX, dragOffsetY;
    let zIndexCounter = 10; // To manage element layering

    // --- 1. DYNAMICALLY LOAD FEATURES ---
    for (const [name, data] of Object.entries(categories)) {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'category';
        const capitalizedName = name.charAt(0).toUpperCase() + name.slice(1);
        categoryDiv.innerHTML = `<h2><button>${capitalizedName}</button></h2>`;

        const gridDiv = document.createElement('div');
        gridDiv.className = 'features-grid';

        for (const fileName of data.files) {
            const img = document.createElement('img');
            img.src = data.path + '/' + fileName;
            img.className = 'feature-img';
            img.alt = `${capitalizedName} feature: ${fileName.split('.')[0]}`;
            img.draggable = true;
            gridDiv.appendChild(img);
        }

        categoryDiv.appendChild(gridDiv);
        palette.appendChild(categoryDiv);
    }

    // --- 2. ACCORDION LOGIC ---
    palette.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' && e.target.closest('.category')) {
            e.target.closest('h2').nextElementSibling.classList.toggle('active');
        }
    });

    // --- 3. DRAG & DROP FROM PALETTE ---
    palette.addEventListener('dragstart', (e) => {
        if (e.target.classList.contains('feature-img')) {
            e.dataTransfer.setData('text/plain', e.target.src);
            e.dataTransfer.setData('alt', e.target.alt);
        }
    });

    canvas.addEventListener('dragover', (e) => e.preventDefault());

    canvas.addEventListener('drop', (e) => {
        e.preventDefault();
        const src = e.dataTransfer.getData('text/plain');
        const alt = e.dataTransfer.getData('alt');
        if (!src) return;

        const newFeature = document.createElement('img');
        newFeature.src = src;
        newFeature.alt = alt;
        newFeature.className = 'placed-feature';
        
        newFeature.onload = () => {
             newFeature.dataset.aspectRatio = newFeature.naturalWidth / newFeature.naturalHeight;
        }

        const canvasRect = canvas.getBoundingClientRect();
        newFeature.style.left = `${e.clientX - canvasRect.left - 50}px`;
        newFeature.style.top = `${e.clientY - canvasRect.top - 50}px`;
        newFeature.style.width = '100px';

        canvas.appendChild(newFeature);
    });

    // --- 4. SELECT, MOVE, RESIZE, AND LAYER ---
    function selectElement(element) {
        if (selectedElement) {
            selectedElement.classList.remove('selected');
        }
        selectedElement = element;
        if (selectedElement) {
            selectedElement.classList.add('selected');
            deleteBtn.style.display = 'block';
            zIndexCounter++;
            selectedElement.style.zIndex = zIndexCounter;
        } else {
            deleteBtn.style.display = 'none';
        }
    }

    canvas.addEventListener('mousedown', (e) => {
        if (e.target.classList.contains('placed-feature')) {
            e.preventDefault();
            selectElement(e.target);
            isDragging = true;
            selectedElement.classList.add('is-dragging');
            dragOffsetX = e.clientX - selectedElement.offsetLeft;
            dragOffsetY = e.clientY - selectedElement.offsetTop;
        } else {
            selectElement(null);
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (isDragging && selectedElement) {
            const canvasRect = canvas.getBoundingClientRect();
            let newLeft = e.clientX - dragOffsetX;
            let newTop = e.clientY - dragOffsetY;

            const elemWidth = selectedElement.offsetWidth;
            const elemHeight = selectedElement.offsetHeight;
            
            if (newLeft < 0) newLeft = 0;
            if (newTop < 0) newTop = 0;
            if (newLeft + elemWidth > canvasRect.width) newLeft = canvasRect.width - elemWidth;
            if (newTop + elemHeight > canvasRect.height) newTop = canvasRect.height - elemHeight;

            selectedElement.style.left = `${newLeft}px`;
            selectedElement.style.top = `${newTop}px`;
        }
    });

    document.addEventListener('mouseup', () => {
        if (isDragging && selectedElement) {
            selectedElement.classList.remove('is-dragging');
        }
        isDragging = false;
    });

    canvas.addEventListener('wheel', (e) => {
        if (selectedElement) {
            e.preventDefault();
            const scaleFactor = 0.1;
            
            const rect = selectedElement.getBoundingClientRect();
            const currentWidth = rect.width;
            const currentHeight = rect.height; 

            const newWidth = e.deltaY < 0 
                ? currentWidth * (1 + scaleFactor) 
                : currentWidth * (1 - scaleFactor);

            const centerX = selectedElement.offsetLeft + currentWidth / 2;
            const centerY = selectedElement.offsetTop + currentHeight / 2;

            selectedElement.style.width = `${newWidth}px`;
            const aspectRatio = parseFloat(selectedElement.dataset.aspectRatio) || 1;
            const newHeight = newWidth / aspectRatio;
            selectedElement.style.height = `${newHeight}px`;

            selectedElement.style.left = `${centerX - newWidth / 2}px`;
            selectedElement.style.top = `${centerY - newHeight / 2}px`;
        }
    });
    
    // --- 5. DELETE A PLACED FEATURE ---
    function deleteSelected() {
        if (selectedElement) {
            selectedElement.remove();
            selectElement(null);
        }
    }

    deleteBtn.addEventListener('click', deleteSelected);
    document.addEventListener('keydown', (e) => {
        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedElement) {
            deleteSelected();
        }
    });

    // --- 6. SAVE THE FINAL IMAGE ---
    saveBtn.addEventListener('click', () => {
        selectElement(null);
        setTimeout(() => {
            html2canvas(canvas, { backgroundColor: null }).then(canvasElement => {
                const link = document.createElement('a');
                link.download = 'face-sketch.png';
                link.href = canvasElement.toDataURL('image/png');
                link.click();
            });
        }, 100);
    });
});