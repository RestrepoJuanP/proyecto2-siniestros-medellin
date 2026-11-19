#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# pausar_fuentes.sh
# Detiene la instancia RDS de fuentes y, si está registrada en .env
# (ID_INSTANCIA_EC2_FUENTES), la EC2 de fuentes del Módulo 2B.
# Sirve para ahorrar crédito del Learner Lab entre sesiones de trabajo.
# Nota: AWS vuelve a iniciar automáticamente una RDS detenida tras 7 días.
#
# Uso (desde la raíz del repositorio): bash infra/pausar_fuentes.sh
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
if [[ "${ESTADO_RDS}" == "available" ]]; then
    aws rds stop-db-instance --region "${REGION}" --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" >/dev/null
    mensaje_ok "RDS ${NOMBRE_INSTANCIA_RDS}: detención solicitada (tarda unos minutos)."
elif [[ "${ESTADO_RDS}" == "no-existe" ]]; then
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: no existe."
else
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: estado '${ESTADO_RDS}', no se puede detener ahora."
fi

# --- EC2 (Módulo 2B) ---------------------------------------------------------
if [[ -z "${ID_INSTANCIA_EC2}" ]]; then
    mensaje_info "EC2 de fuentes: no registrada en .env (ID_INSTANCIA_EC2_FUENTES)."
else
    ESTADO_EC2="$(obtener_estado_ec2 "${ID_INSTANCIA_EC2}")"
    if [[ "${ESTADO_EC2}" == "running" ]]; then
        aws ec2 stop-instances --region "${REGION}" --instance-ids "${ID_INSTANCIA_EC2}" >/dev/null
        mensaje_ok "EC2 ${ID_INSTANCIA_EC2}: detención solicitada."
    else
        mensaje_info "EC2 ${ID_INSTANCIA_EC2}: estado '${ESTADO_EC2}', no se detiene."
    fi
fi
