#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# reanudar_fuentes.sh
# Inicia la instancia RDS de fuentes y, si está registrada en .env
# (ID_INSTANCIA_EC2_FUENTES), la EC2 de fuentes del Módulo 2B.
# Espera a que queden disponibles. Si cambió de red, ejecute después
# punto2_fuentes/rds/actualizar_mi_ip.sh
#
# Uso (desde la raíz del repositorio): bash infra/reanudar_fuentes.sh
# -----------------------------------------------------------------------------
set -euo pipefail

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=funciones_comunes.sh
source "${DIR_RAIZ}/infra/funciones_comunes.sh"

NOMBRE_INSTANCIA_RDS="$(leer_variable_env_o_defecto NOMBRE_INSTANCIA_RDS rds-movilidad)"
ID_INSTANCIA_EC2="$(leer_variable_env ID_INSTANCIA_EC2_FUENTES)"

verificar_aws_cli

# --- RDS ---------------------------------------------------------------------
ESTADO_RDS="$(obtener_estado_rds "${NOMBRE_INSTANCIA_RDS}")"
if [[ "${ESTADO_RDS}" == "stopped" ]]; then
    aws rds start-db-instance --region "${REGION}" --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" >/dev/null
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: inicio solicitado; esperando disponibilidad (~5-10 min)..."
    aws rds wait db-instance-available --region "${REGION}" --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}"
    mensaje_ok "RDS ${NOMBRE_INSTANCIA_RDS}: disponible."
elif [[ "${ESTADO_RDS}" == "no-existe" ]]; then
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: no existe. Créela con punto2_fuentes/rds/crear_rds.sh"
else
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: estado '${ESTADO_RDS}'."
fi

# --- EC2 (Módulo 2B) ---------------------------------------------------------
if [[ -z "${ID_INSTANCIA_EC2}" ]]; then
    mensaje_info "EC2 de fuentes: no registrada en .env (ID_INSTANCIA_EC2_FUENTES)."
else
    ESTADO_EC2="$(obtener_estado_ec2 "${ID_INSTANCIA_EC2}")"
    if [[ "${ESTADO_EC2}" == "stopped" ]]; then
        aws ec2 start-instances --region "${REGION}" --instance-ids "${ID_INSTANCIA_EC2}" >/dev/null
        aws ec2 wait instance-running --region "${REGION}" --instance-ids "${ID_INSTANCIA_EC2}"
        mensaje_ok "EC2 ${ID_INSTANCIA_EC2}: en ejecución (su IP pública pudo cambiar)."
    else
        mensaje_info "EC2 ${ID_INSTANCIA_EC2}: estado '${ESTADO_EC2}'."
    fi
fi
