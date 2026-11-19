#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# verificar_entorno.sh
# Verifica que el entorno local esté listo para trabajar con el Learner Lab:
#   1. AWS CLI v2 instalada.
#   2. Credenciales válidas (aws sts get-caller-identity).
#   3. Región configurada en us-east-1.
#   4. Existencia de LabRole, LabInstanceProfile, EMR_DefaultRole y
#      EMR_EC2_DefaultRole (reporta OK/FALTA sin abortar).
# Uso: bash infra/verificar_entorno.sh
# -----------------------------------------------------------------------------
set -euo pipefail

REGION_ESPERADA="us-east-1"
DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVO_ENV="${DIR_RAIZ}/.env"

# Contadores para el resumen final
total_ok=0
total_falta=0

reportar_ok() {
    echo "  [OK]    $1"
    total_ok=$((total_ok + 1))
}

reportar_falta() {
    echo "  [FALTA] $1"
    total_falta=$((total_falta + 1))
}

# Lee una variable del archivo .env (si existe) sin ejecutarlo
leer_variable_env() {
    local nombre_variable="$1"
    local valor=""
    if [[ -f "${ARCHIVO_ENV}" ]]; then
        valor="$(grep -E "^${nombre_variable}=" "${ARCHIVO_ENV}" | tail -n 1 | cut -d '=' -f 2- | tr -d '\r"' || true)"
    fi
    echo "${valor}"
}

echo "=============================================="
echo " Verificación del entorno - Proyecto 2 Big Data"
echo "=============================================="

# --- 1. AWS CLI v2 -----------------------------------------------------------
echo ""
echo "1) AWS CLI"
if ! command -v aws >/dev/null 2>&1; then
    echo "  [ERROR] No se encontró el comando 'aws'. Instale AWS CLI v2:"
    echo "          https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

version_aws="$(aws --version 2>&1)"
echo "  Versión detectada: ${version_aws}"
if [[ "${version_aws}" == aws-cli/2.* ]]; then
    reportar_ok "AWS CLI v2 instalada"
else
    echo "  [ERROR] Se requiere AWS CLI v2."
    exit 1
fi

# --- 2. Identidad ------------------------------------------------------------
echo ""
echo "2) Identidad (aws sts get-caller-identity)"
if ! aws sts get-caller-identity --output table; then
    echo "  [ERROR] Las credenciales no son válidas o expiraron."
    echo "          Copie de nuevo las credenciales de 'AWS Details' del Learner Lab"
    echo "          en ~/.aws/credentials e intente otra vez."
    exit 1
fi
reportar_ok "Credenciales válidas"

# --- 3. Región ---------------------------------------------------------------
echo ""
echo "3) Región"
region_cli="$(aws configure get region || true)"
region_entorno="${AWS_REGION:-}"
region_env_archivo="$(leer_variable_env AWS_REGION)"
echo "  Región en ~/.aws/config : ${region_cli:-<sin definir>}"
echo "  Variable AWS_REGION     : ${region_entorno:-<sin definir>}"
echo "  AWS_REGION en .env      : ${region_env_archivo:-<sin definir o sin .env>}"

region_efectiva="${region_entorno:-${region_cli}}"
if [[ "${region_efectiva}" == "${REGION_ESPERADA}" ]]; then
    reportar_ok "Región efectiva es ${REGION_ESPERADA}"
else
    reportar_falta "La región efectiva es '${region_efectiva:-<vacía>}' y debe ser ${REGION_ESPERADA} (ejecute: aws configure set region ${REGION_ESPERADA})"
fi

# --- 4. Roles e instance profiles --------------------------------------------
echo ""
echo "4) Roles e instance profiles del Learner Lab"

for nombre_rol in LabRole EMR_DefaultRole EMR_EC2_DefaultRole; do
    if aws iam get-role --role-name "${nombre_rol}" >/dev/null 2>&1; then
        reportar_ok "Rol ${nombre_rol}"
    else
        reportar_falta "Rol ${nombre_rol} (no existe o no hay permiso para consultarlo)"
    fi
done

if aws iam get-instance-profile --instance-profile-name LabInstanceProfile >/dev/null 2>&1; then
    reportar_ok "Instance profile LabInstanceProfile"
else
    reportar_falta "Instance profile LabInstanceProfile (no existe o no hay permiso para consultarlo)"
fi

# --- Resumen -----------------------------------------------------------------
echo ""
echo "=============================================="
echo " Resumen: ${total_ok} OK, ${total_falta} FALTA"
echo "=============================================="
if [[ "${total_falta}" -gt 0 ]]; then
    echo " Revise los elementos marcados como FALTA antes de continuar."
    echo " Nota: EMR_DefaultRole y EMR_EC2_DefaultRole suelen existir en el Learner Lab;"
    echo " si faltan, al crear el cluster EMR use LabRole y LabInstanceProfile."
fi
