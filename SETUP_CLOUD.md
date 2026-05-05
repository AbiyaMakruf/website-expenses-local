# Setup Google Cloud Run

Jalankan semua perintah ini **sekali saja** dari terminal. Setelah selesai, CI/CD otomatis berjalan setiap push ke `main`.

## Prasyarat
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) sudah terinstall
- Sudah login: `gcloud auth login`

---

## LANGKAH 1 — Set project aktif

```bash
gcloud config set project tracker-expenses-478512
```

---

## LANGKAH 2 — Enable semua API yang dibutuhkan

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com
```

---

## LANGKAH 3 — Buat GCS bucket

```bash
gcloud storage buckets create gs://new-tracker-expenses \
  --location=asia-southeast1 \
  --uniform-bucket-level-access
```

Buat folder `data/` di dalam bucket (GCS butuh placeholder):

```bash
echo "" | gcloud storage cp - gs://new-tracker-expenses/data/.keep
```

---

## LANGKAH 4 — Upload database lama Anda

Jalankan dari folder project lokal Anda:

```bash
gcloud storage cp data/expenses.db gs://new-tracker-expenses/data/expenses.db
```

Upload gambar-gambar jika ada:

```bash
gcloud storage cp -r data/uploads gs://new-tracker-expenses/data/uploads 2>/dev/null || true
gcloud storage cp -r data/wallet_icons gs://new-tracker-expenses/data/wallet_icons 2>/dev/null || true
gcloud storage cp -r data/subscription_icons gs://new-tracker-expenses/data/subscription_icons 2>/dev/null || true
```

---

## LANGKAH 5 — Buat Artifact Registry repository

```bash
gcloud artifacts repositories create expenses-repo \
  --repository-format=docker \
  --location=asia-southeast1 \
  --description="Docker images untuk expenses app"
```

---

## LANGKAH 6 — Beri izin Cloud Build untuk deploy ke Cloud Run dan akses GCS

Ambil nomor project dulu:

```bash
PROJECT_NUMBER=$(gcloud projects describe tracker-expenses-478512 --format='value(projectNumber)')
echo "Project number: $PROJECT_NUMBER"
```

Beri izin:

```bash
# Cloud Build bisa deploy ke Cloud Run
gcloud projects add-iam-policy-binding tracker-expenses-478512 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# Cloud Build bisa pakai service account
gcloud projects add-iam-policy-binding tracker-expenses-478512 \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Cloud Run bisa akses GCS bucket (baca + tulis)
gcloud projects add-iam-policy-binding tracker-expenses-478512 \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## LANGKAH 7 — Hubungkan GitHub repo ke Cloud Build

1. Buka: https://console.cloud.google.com/cloud-build/triggers?project=tracker-expenses-478512
2. Klik **"Connect Repository"**
3. Pilih **GitHub** → authorize → pilih repo `AbiyaMakruf/website-expenses-local`
4. Klik **"Create Trigger"** dengan konfigurasi:
   - Name: `deploy-on-push-main`
   - Event: **Push to a branch**
   - Branch: `^main$`
   - Configuration: **Cloud Build configuration file (yaml)**
   - File location: `/cloudbuild.yaml`
5. Klik **Save**

---

## LANGKAH 8 — Build & deploy pertama kali (manual trigger)

```bash
gcloud builds submit --config cloudbuild.yaml .
```

Tunggu ~5-10 menit. Setelah selesai, URL app muncul di output atau cek:

```bash
gcloud run services describe new-tracker-expenses-web \
  --region=asia-southeast1 \
  --format='value(status.url)'
```

---

## Setelah setup selesai

- Setiap `git push origin main` → Cloud Build otomatis build + deploy
- DB dan gambar tersimpan permanen di GCS
- App scale to 0 saat tidak dipakai (tidak ada biaya idle)
- Untuk lihat logs: `gcloud run services logs read new-tracker-expenses-web --region=asia-southeast1`
