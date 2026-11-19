#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# crear_datalake.sh
# Crea (si no existe) el bucket único del data lake en us-east-1, bloquea el
# acceso público y crea los prefijos de las zonas con un archivo .keep.
# Es idempotente: se puede ejecutar varias veces sin efectos secundarios.
# Lee NOMBRE_BUCKET del archivo .env en la raíz del repositorio.
# Uso: bash infra/crear_datalake.sh
# -----------------------------------------------------------------------------
set -euo pipefail

REGION="us-east-1"
DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVO_ENV="${DIR_RAIZ}/.env"
PREFIJOS_ZONAS=("raw/" "trusted/" "refined/" "scripts/" "athena-resultados/")

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
    echo "[ERROR] No existe ${ARCHIVO_ENV}. Copie .env.example como .env y complete NOMBRE_BUCKET."
    exit 1
fi

NOMBRE_BUCKET="$(leer_variable_env NOMBRE_BUCKET)"
if [[ -z "${NOMBRE_BUCKET}" ]]; then
    echo "[ERROR] NOMBRE_BUCKET está vacío en ${ARCHIVO_ENV}."
    exit 1
fi

echo "Bucket del data lake: ${NOMBRE_BUCKET} (región ${REGION})"

# --- 2. Crear el bucket si no existe -----------------------------------------
# head-bucket devuelve error si no existe (404) o si pertenece a otra cuenta (403)
if salida_head="$(aws s3api head-bucket --bucket "${NOMBRE_BUCKET}" --region "${REGION}" 2>&1)"; then
    echo "[INFO] El bucket ya existe y es accesible. No se vuelve a crear."
else
    if [[ "${salida_head}" == *"403"* || "${salida_head}" == *"Forbidden"* ]]; then
        echo "[ERROR] El bucket ${NOMBRE_BUCKET} existe pero pertenece a otra cuenta. Elija otro nombre."
        exit 1
    fi
    echo "[INFO] Creando el bucket ${NOMBRE_BUCKET}..."
    # En us-east-1 NO se envía LocationConstraint
    aws s3api create-bucket --bucket "${NOMBRE_BUCKET}" --region "${REGION}" >/dev/null
    aws s3api wait bucket-exists --bucket "${NOMBRE_BUCKET}" --region "${REGION}"
    echo "[OK] Bucket creado."
fi

# --- 3. Bloquear acceso público ----------------------------------------------
echo "[INFO] Aplicando bloqueo de acceso público..."
aws s3api put-public-access-block \
    --bucket "${NOMBRE_BUCKET}" \
    --region "${REGION}" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
echo "[OK] Acceso público bloqueado."

# --- 4. Crear prefijos de las zonas ------------------------------------------
for prefijo in "${PREFIJOS_ZONAS[@]}"; do
    clave_keep="${prefijo}.keep"
    aws s3api put-object \
        --bucket "${NOMBRE_BUCKET}" \
        --key "${clave_keep}" \
        --region "${REGION}" >/dev/null
    echo "[OK] Prefijo s3://${NOMBRE_BUCKET}/${prefijo}"
done

# --- 5. Resumen --------------------------------------------------------------
echo ""
echo "Contenido actual del bucket:"
aws s3 ls "s3://${NOMBRE_BUCKET}/" --region "${REGION}"
echo ""
echo "[OK] Data lake listo en s3://${NOMBRE_BUCKET}"
