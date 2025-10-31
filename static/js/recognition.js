document.addEventListener('DOMContentLoaded', () => {
    // --- Add Person Form Logic ---
    const addPersonForm = document.getElementById('add-person-form');
    
    addPersonForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(addPersonForm);
        
        try {
            const response = await fetch('/api/add_person', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.message);
                addPersonForm.reset();
            } else {
                throw new Error(result.error || 'An unknown error occurred.');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });

    // --- Recognize Sketch Form Logic ---
    const recognizeForm = document.getElementById('recognize-form');
    const sketchFile = document.getElementById('sketch-file');
    const resultsContainer = document.getElementById('results-container');
    const resultsContent = document.getElementById('results-content');

    recognizeForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!sketchFile.files.length) {
            alert('Please select a sketch file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('sketch', sketchFile.files[0]);

        resultsContent.innerHTML = '<p class="status-message">Analyzing... Please wait.</p>';
        resultsContainer.classList.remove('hidden');

        try {
            const response = await fetch('/api/recognize', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            console.log('recognize result:', result);
            if (response.ok) {
                if (result.match) {
                    displayMatch(result);
                } else {
                    displayNoMatch(result);
                }
            } else {
                throw new Error(result.error || 'An unknown error occurred.');
            }
        } catch (error) {
            resultsContent.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
        }
    });

    function displayMatch(data) {
        // Display only the mapped similarity and mapped distance per user request.
        // Log the image path so we can debug missing images
        console.log('displayMatch image src:', data.photo_path);
        // Simple inline SVG fallback (data URI) used when image cannot be loaded
        const placeholder = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><rect width='100%' height='100%' fill='%23222'/><text x='50%' y='50%' fill='%23fff' font-size='14' text-anchor='middle' dominant-baseline='central'>No Image</text></svg>";

        resultsContent.innerHTML = `
            <div class="profile-card">
                <img src="${data.photo_path}" alt="Photo of ${data.name}" class="profile-photo" onerror="this.onerror=null;this.src='${placeholder}';">
                <div class="profile-details">
                    <h3>${data.name}</h3>
                    <p><strong>Age:</strong> ${data.age}</p>
                    <p><strong>Criminal Record:</strong> ${data.criminal_record}</p>
                    <p class="score"><strong>Similarity:</strong> ${data.similarity}%</p>
                    <p class="score"><strong>Distance:</strong> ${data.distance}</p>
                </div>
            </div>
        `;
    }

    function displayNoMatch(data) {
        resultsContent.innerHTML = `<p class="status-message">${data.message}</p>`;
    }

    // --- Component recognition ---
    const compForm = document.getElementById('recognize-component-form');
    const compFile = document.getElementById('component-sketch-file');
    const compType = document.getElementById('component-type');
    const compResultsContainer = document.getElementById('results-component-container');
    const compResultsContent = document.getElementById('results-component-content');

    compForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!compFile.files.length) {
            alert('Please select a component sketch file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('sketch', compFile.files[0]);
        formData.append('part', compType.value);

        compResultsContent.innerHTML = '<p class="status-message">Analyzing component... Please wait.</p>';
        compResultsContainer.classList.remove('hidden');

        try {
            const response = await fetch('/api/recognize_component', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            console.log('component recognize result:', result);
            if (response.ok) {
                if (result.match) {
                    displayComponentMatch(result);
                } else {
                    displayComponentNoMatch(result);
                }
            } else {
                throw new Error(result.error || 'An unknown error occurred.');
            }
        } catch (error) {
            compResultsContent.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
        }
    });

    function displayComponentMatch(data) {
        console.log('displayComponentMatch image src:', data.photo_path);
        const placeholder = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><rect width='100%' height='100%' fill='%23222'/><text x='50%' y='50%' fill='%23fff' font-size='14' text-anchor='middle' dominant-baseline='central'>No Image</text></svg>";
        compResultsContent.innerHTML = `
            <div class="profile-card">
                <img src="${data.photo_path}" alt="Photo of ${data.name}" class="profile-photo" onerror="this.onerror=null;this.src='${placeholder}';">
                <div class="profile-details">
                    <h3>${data.name} <small>(${data.part})</small></h3>
                    <p class="score"><strong>Similarity:</strong> ${data.similarity}%</p>
                    <p class="score"><strong>Distance:</strong> ${data.distance}</p>
                </div>
            </div>
        `;
    }

    function displayComponentNoMatch(data) {
        compResultsContent.innerHTML = `<p class="status-message">${data.message}</p>`;
    }
});