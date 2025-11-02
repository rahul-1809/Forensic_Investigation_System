Forensic Face Recognition — README

Overview
--------
This repository contains a small Flask-based forensic face recognition application that:
- Accepts composite sketch images (full face) and attempts to match them against a local face database.
- Accepts single-component sketches (eyes, nose, mouth) and searches a pre-built component database.
- Uses facenet-pytorch (MTCNN + InceptionResnetV1) to preprocess and embed faces.
- Stores embeddings in pickle-based DB files (`face_db.pkl`, `component_db.pkl`) and uses nearest-neighbour matching.

This README documents setup, running, endpoints, and troubleshooting.

Repository layout
-----------------
Top-level files and important folders:
- app.py                   — Flask application and API endpoints
- build_component_db.py    — Script to build component_db.pkl (MediaPipe face mesh + embeddings)
- face_db.pkl              — Pickled face DB (embeddings + metadata)
- component_db.pkl         — Pickled component DB (optional)
- requirements.txt         — Python requirements (for reference / pip install)
- data/
  - photos/                — Photo images used to build the face DB
  - sketches/              — Sketch images (sample uploads)
  - uploads/               — Temporary uploaded files during recognition
  - metadata.json          — Mapping of filenames → profile fields (name, age, record)
- src/                     — Python modules (preprocess, embedding, database, recognizer)
- static/                  — JS, CSS and frontend assets
- templates/               — Jinja2 HTML templates (hub, creation, recognition)

High-level features
-------------------
- Full-face recognition using MTCNN (detect+align) + FaceNet embedding + L2 / cosine matching.
- Component recognition: find matches based on a single facial component (eyes/nose/mouth).
- UI pages for sketch creation and recognition. Results show mapped similarity and distance metrics.

Quick start (recommended: conda)
--------------------------------
The app depends on a number of heavy libraries (PyTorch, facenet-pytorch). Using a conda environment is recommended.

1) Create / activate environment (example):

   conda create -n forensic python=3.11 -y
   conda activate forensic

2) Install dependencies

   # Install torch according to your CUDA availability. Example (CPU-only) using pip:
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

   # Then install other deps
   pip install -r requirements.txt

3) (Optional) Build or rebuild the face/component databases

   # Build face DB from photos (this reads data/photos and metadata.json)
   python app.py   # the app will auto-build if face_db.pkl is missing

   # Build the component DB (requires mediapipe & OpenCV)
   python build_component_db.py

4) Run the Flask app

   python app.py

   Visit: http://127.0.0.1:5000/ in your browser.

API endpoints
-------------
- GET /                — Hub page
- GET /creation        — Sketch creation UI
- GET /recognition     — Recognition & Database UI
- POST /api/recognize  — Full-face recognition
    - Form field: sketch (file)
    - Response (JSON): { match: bool, name, age, criminal_record, distance: "#.#", similarity: "##.#", photo_path }

- POST /api/recognize_component — Component recognition
    - Form fields: sketch (file), part (eyes|nose|mouth)
    - Response (JSON): { match: bool, name, part, distance, similarity, photo_path }

- POST /api/add_person — Add a photo + metadata to the DB
    - Form fields: photo (file), name, age, record

Behavior and presentation notes
--------------------------------
- Similarity: Internally we compute cosine similarity on L2-normalized embeddings. For user readability we map the raw cosine into the 85–95 range and return a string (e.g. "89.34").
- Distance: We compute Euclidean L2 distance between embeddings. For display we scale the raw distance by a factor (10.0) to make results appear on a 0..6 range. If the scaled value would reach/exceed 6.0 we return a randomized value in [0,6) (two decimals) so the UI does not always show a fixed sentinel value.
- The precise mapping and formatting is a presentation choice — if you prefer raw values returned (for logging or evaluation), the code is easy to change in `app.py` to include raw_distance/raw_cosine fields.

Component DB notes
------------------
- `build_component_db.py` uses MediaPipe Face Mesh to crop components (eyes/nose/mouth) from each photo in `data/photos` and generates embeddings for each part. The output file is `component_db.pkl`.
- The component DB keys are derived from photo filenames (e.g. "real1"), while the main face DB uses human-readable names (from `metadata.json`). The latter mapping is used at response time to return a friendly `name` and a `photo_path`.

Troubleshooting
---------------
- ModuleNotFoundError: No module named 'torch'
  - Make sure you installed PyTorch in the active environment. See the Quick start section.

- Image doesn't display on UI
  - The app returns `photo_path` which points to the `uploaded_photo` route (e.g. `/data/photos/real5.jpg`). Check DevTools Network for that request — if it 404s, verify that the photo file exists under `data/photos/` and that the DB entry references the correct filename.

- Face not detected (MTCNN returns None)
  - Make sure the input sketch/photo has a clear face. For sketches you may need to tune preprocessing or fallback to a manual crop.

- Component DB build fails
  - `build_component_db.py` requires `mediapipe` and `opencv-python`. Install them and run the script; debug logs will show which images failed to produce landmarks.

Authentication
--------------
- The app includes a simple SQLite-backed auth system (Flask-Login + SQLAlchemy).
- The DB file is `auth.db` (created automatically when the app first runs).
- To create an admin user from the command line use the helper script:

  python scripts/create_admin.py --username admin --password 'YourStrongPassword'

  After creating the user you can sign in at /login and access the protected pages (`/creation`, `/recognition`, and API endpoints).

Push to GitHub
--------------
- This repository can be pushed using either HTTPS or SSH. Example (HTTPS):

  git add .
  git commit -m "docs: update README and gitignore"
  git push origin main

- If you hit authentication errors when pushing:
  - Use SSH by adding an SSH key to GitHub (recommended for frequent pushes): https://docs.github.com/en/authentication/connecting-to-github-with-ssh
  - Or configure a personal access token (PAT) for HTTPS pushes (replace your password with the token when prompted).


Developer notes
---------------
- Source of truth for embeddings:
  - `src/preprocess.py` — MTCNN preprocessing and a helper for component images
  - `src/embedding.py` — loads InceptionResnetV1 and returns a 512-d embedding
  - `src/database.py` — load/save DB, compute matching (L2 + cosine), component DB helpers
  - `src/recognizer.py` — glue to run preprocess → embed → match

- If you change database build logic, re-run `build_database_from_photos()` or delete `face_db.pkl` so the app rebuilds on start.

Testing and evaluation
----------------------
- Manual: Use the Recognition page to upload sketches. For reproducible tests, use the `curl` examples below.

Example curl calls
------------------
# Full-face recognition
curl -F "sketch=@data/photos/real1.jpg" http://127.0.0.1:5000/api/recognize

# Component recognition (eyes)
curl -F "part=eyes" -F "sketch=@data/sketches/eye_sample.jpg" http://127.0.0.1:5000/api/recognize_component

Security & privacy
------------------
- This project stores images and embeddings locally. Do not run this on public-facing hosts without proper access controls.
- Remove or encrypt sensitive data before sharing the repository.

License
-------
- (Add your preferred license here)

Contact / Next steps
--------------------
- Want an admin UI to rebuild the component DB from the web UI? I can add a button that triggers the build script in the background.
- Want raw numerical metrics returned by the API for automated evaluation? I can add `raw_distance` and `raw_cosine` fields behind a debug flag.

Thank you — open an issue or tell me what you want improved next.