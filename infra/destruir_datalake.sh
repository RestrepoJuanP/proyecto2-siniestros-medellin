#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# destruir_datalake.sh
# Vacía y elimina el bucket del data lake. ACCIÓN IRREVERSIBLE.
# Pide confirmación escribiendo el nombre exacto del bucket.
# Lee NOMBRE_BUCKET del archivo .env en la raíz del repositorio.
# Uso: bash infra/destruir_datalake.sh
# -----------------------------------------------------------------------------
set -euo pipefail

REGION="us-east-1"
DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVO_ENV="${DIR_RAIZ}/.env"

# Lee una variable del archivo .env sin ejecutarlo
leer_variable_env() {
    local nombre_variable="$1"
    local valor=""
    if [[ -f "${ARCHIVO_ENV}" ]]; then
        valor="$(grep -E "^${nombre_variable}=" "${ARCHIVO_ENV}" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r"' || true)"
    fi
    echo "${valor}"
}

# --- 1. Leer configuración ---------------------------------------------------
if [[ ! -f "${ARCHIVO_ENV}" ]]; then
    echo "[ERROR] No existe ${ARCHIVO_ENV}."
    exit 1
fi

NOMBRE_BUCKET="$(leer_variable_env NOMBRE_BUCKET)"
if [[ -z "${NOMBRE_BUCKET}" ]]; then
    echo "[ERROR] NOMBRE_BUCKET está vacío en ${ARCHIVO_ENV}."
    exit 1
fi

# --- 2. Verificar que el bucket exista ---------------------------------------
if ! aws s3api head-bucket --bucket "${NOMBRE_BUCKET}" --region "${REGION}" >/dev/null 2>&1; then
    echo "[INFO] El bucket ${NOMBRE_BUCKET} no existe o no es accesible. Nada que borrar."
    exit 0
fi

# --- 3. Confirmación ---------------------------------------------------------
echo "=============================================================="
echo " ATENCIÓN: se borrarán TODOS los objetos y el bucket:"
echo "   s3://${NOMBRE_BUCKET}"
echo " Esta acción NO se puede deshacer."
echo "=============================================================="
read -r -p "Escriba el nombre del bucket para confirmar: " confirmacion

if [[ "${confirmacion}" != "${NOMBRE_BUCKET}" ]]; then
    echo "[CANCELADO] El nombre no coincide. No se borró nada."
    exit 1
fi

# --- 4. Vaciar el bucket -----------------------------------------------------
echo "[INFO] Vaciando el bucket..."
aws s3 rm "s3://${NOMBRE_BUCKET}" --recursive --region "${REGION}"

# Si el bucket tuviera versionamiento, borrar también versiones y marcadores
estado_versionamiento="$(aws s3api get-bucket-versioning --bucket "${NOMBRE_BUCKET}" --region "${REGION}" --query 'Status' --output text || true)"
if [[ "${estado_versionamiento}" == "Enabled" || "${estado_versionamiento}" == "Suspended" ]]; then
    echo "[INFO] El bucket tiene versionamiento; borrando versiones..."
    while true; do
        versiones_json="$(aws s3api list-object-versions \
            --bucket "${NOMBRE_BUCKET}" \
            --region "${REGION}" \
            --no-paginate \
            --max-keys 1000 \
            --query '{Objects: [Versions, DeleteMarkers][][].{Key: Key, VersionId: VersionId}}' \
            --output json)"
        if [[ "${versiones_json}" == *'"Objects": []'* || "${versiones_json}" == *'"Objects": null'* ]]; then
            break
        fi
        aws s3api delete-objects \
            --bucket "${NOMBRE_BUCKET}" \
            --region "${REGION}" \
            --delete "${versiones_json}" >/dev/null
    done
fi

# --- 5. Borrar el bucket -----------------------------------------------------
echo "[INFO] Eliminando el bucket..."
aws s3api delete-bucket --bucket "${NOMBRE_BUCKET}" --region "${REGION}"
echo "[OK] Bucket s3://${NOMBRE_BUCKET} eliminado."
