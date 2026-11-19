#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# destruir_fuentes.sh
# Borra TODAS las fuentes del Punto 2, previa confirmación:
#   1. Instancia RDS (sin snapshot final, se pierden los datos cargados).
#   2. EC2 de fuentes (si está registrada en .env como ID_INSTANCIA_EC2_FUENTES).
#   3. Security groups de RDS y de la EC2.
# Al final limpia de .env los valores que ya no son válidos.
# El bucket del data lake NO se toca (para eso está destruir_datalake.sh).
#
# Uso (desde la raíz del repositorio): bash infra/destruir_fuentes.sh
# -----------------------------------------------------------------------------
set -euo pipefail

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=funciones_comunes.sh
source "${DIR_RAIZ}/infra/funciones_comunes.sh"

PALABRA_CONFIRMACION="DESTRUIR"

NOMBRE_INSTANCIA_RDS="$(leer_variable_env_o_defecto NOMBRE_INSTANCIA_RDS rds-movilidad)"
NOMBRE_SG_RDS="$(leer_variable_env_o_defecto NOMBRE_SG_RDS sg-rds-movilidad)"
NOMBRE_SG_EC2="$(leer_variable_env_o_defecto NOMBRE_SG_EC2 sg-ec2-fuentes)"
ID_INSTANCIA_EC2="$(leer_variable_env ID_INSTANCIA_EC2_FUENTES)"

verificar_aws_cli
ID_VPC="$(obtener_vpc_por_defecto)"

# Borra un security group, reintentando mientras siga en uso por recursos que se están eliminando.
borrar_security_group() {
    local nombre_grupo="$1"
    local id_grupo
    local intento
    id_grupo="$(buscar_security_group "${nombre_grupo}" "${ID_VPC}")"
    if [[ -z "${id_grupo}" ]]; then
        mensaje_info "Security group ${nombre_grupo}: no existe."
        return 0
    fi
    for intento in 1 2 3 4 5 6 7 8 9 10; do
        if aws ec2 delete-security-group --region "${REGION}" --group-id "${id_grupo}" >/dev/null 2>&1; then
            mensaje_ok "Security group ${nombre_grupo} (${id_grupo}) borrado."
            return 0
        fi
        mensaje_info "Security group ${nombre_grupo} aún en uso; reintento ${intento} de 10 en 30 s..."
        sleep 30
    done
    mensaje_error "No se pudo borrar ${nombre_grupo} (${id_grupo}). Revise dependencias en la consola de EC2."
    return 1
}

# --- 1. Confirmación ---------------------------------------------------------
echo "Se borrarán de forma PERMANENTE:"
echo "  - RDS:  ${NOMBRE_INSTANCIA_RDS} (sin snapshot final)"
if [[ -n "${ID_INSTANCIA_EC2}" ]]; then
    echo "  - EC2:  ${ID_INSTANCIA_EC2}"
fi
echo "  - Security groups: ${NOMBRE_SG_RDS}, ${NOMBRE_SG_EC2}"
echo ""
read -r -p "Escriba ${PALABRA_CONFIRMACION} para continuar: " respuesta_usuario
if [[ "${respuesta_usuario}" != "${PALABRA_CONFIRMACION}" ]]; then
    mensaje_info "Operación cancelada. No se borró nada."
    exit 0
fi

# --- 2. Borrar RDS y terminar EC2 (en paralelo; luego se espera) -------------
ESTADO_RDS="$(obtener_estado_rds "${NOMBRE_INSTANCIA_RDS}")"
if [[ "${ESTADO_RDS}" == "no-existe" ]]; then
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: no existe."
elif [[ "${ESTADO_RDS}" == "deleting" ]]; then
    mensaje_info "RDS ${NOMBRE_INSTANCIA_RDS}: ya se está borrando."
else
    aws rds delete-db-instance \
        --region "${REGION}" \
        --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" \
        --skip-final-snapshot \
        --delete-automated-backups >/dev/null
    mensaje_ok "RDS ${NOMBRE_INSTANCIA_RDS}: borrado solicitado."
fi

if [[ -n "${ID_INSTANCIA_EC2}" ]]; then
    ESTADO_EC2="$(obtener_estado_ec2 "${ID_INSTANCIA_EC2}")"
    if [[ "${ESTADO_EC2}" == "no-existe" || "${ESTADO_EC2}" == "terminated" ]]; then
        mensaje_info "EC2 ${ID_INSTANCIA_EC2}: no existe o ya está terminada."
    else
        aws ec2 terminate-instances --region "${REGION}" --instance-ids "${ID_INSTANCIA_EC2}" >/dev/null
        mensaje_ok "EC2 ${ID_INSTANCIA_EC2}: terminación solicitada."
        aws ec2 wait instance-terminated --region "${REGION}" --instance-ids "${ID_INSTANCIA_EC2}"
        mensaje_ok "EC2 ${ID_INSTANCIA_EC2}: terminada."
    fi
fi

if [[ "$(obtener_estado_rds "${NOMBRE_INSTANCIA_RDS}")" != "no-existe" ]]; then
    mensaje_info "Esperando a que termine el borrado de la RDS (~5-10 min)..."
    aws rds wait db-instance-deleted --region "${REGION}" --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}"
    mensaje_ok "RDS ${NOMBRE_INSTANCIA_RDS}: borrada."
fi

# --- 3. Security groups ------------------------------------------------------
# Primero el de RDS, porque tiene una regla que referencia al de la EC2
borrar_security_group "${NOMBRE_SG_RDS}"
borrar_security_group "${NOMBRE_SG_EC2}"

# --- 4. Limpiar .env ---------------------------------------------------------
if [[ -f "${ARCHIVO_ENV}" ]]; then
    escribir_variable_env RDS_HOST ""
    escribir_variable_env RDS_CLAVE ""
    escribir_variable_env ID_SG_RDS ""
    escribir_variable_env ID_SG_EC2 ""
    escribir_variable_env ID_INSTANCIA_EC2_FUENTES ""
    mensaje_ok "Valores de RDS, EC2 y security groups limpiados en .env."
fi

mensaje_ok "Fuentes destruidas."
