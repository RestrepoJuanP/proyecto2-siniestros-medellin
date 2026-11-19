#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# actualizar_mi_ip.sh
# Reemplaza la regla de la IP anterior del desarrollador por la IP pública
# actual, para usar cuando se cambia de red (casa, universidad, datos móviles):
#   - sg-rds-movilidad: puerto 3306 (la regla se crea si no existe).
#   - sg-ec2-fuentes:   puerto 22 (solo si el grupo existe y ya tiene una
#                       regla de IP del desarrollador; la crea el Módulo 2B).
#
# Las reglas del desarrollador se reconocen por la descripción "ip-desarrollador".
# Las reglas que permiten tráfico desde otro security group no se tocan.
#
# Uso (desde la raíz del repositorio): bash punto2_fuentes/rds/actualizar_mi_ip.sh
# -----------------------------------------------------------------------------
set -euo pipefail

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../infra/funciones_comunes.sh
source "${DIR_RAIZ}/infra/funciones_comunes.sh"

DESCRIPCION_REGLA_IP="ip-desarrollador"
PUERTO_MARIADB="3306"
PUERTO_SSH="22"

NOMBRE_SG_RDS="$(leer_variable_env_o_defecto NOMBRE_SG_RDS sg-rds-movilidad)"
NOMBRE_SG_EC2="$(leer_variable_env_o_defecto NOMBRE_SG_EC2 sg-ec2-fuentes)"

# Lista los CIDR marcados como IP del desarrollador para un puerto.
listar_cidrs_desarrollador() {
    local id_grupo="$1"
    local puerto="$2"
    aws ec2 describe-security-groups \
        --region "${REGION}" \
        --group-ids "${id_grupo}" \
        --query "SecurityGroups[0].IpPermissions[?FromPort==\`${puerto}\`].IpRanges[] | [?Description=='${DESCRIPCION_REGLA_IP}'].CidrIp" \
        --output text | limpiar_salida
}

# Reemplaza en un grupo y puerto las reglas de IPs anteriores por la IP actual.
# crear_si_no_hay: "si" agrega la regla aunque no hubiera una anterior.
reemplazar_regla_ip() {
    local id_grupo="$1"
    local puerto="$2"
    local cidr_actual="$3"
    local crear_si_no_hay="$4"
    local cidrs_anteriores
    local cidr
    local ya_tiene_actual="no"
    local habia_reglas="no"

    cidrs_anteriores="$(listar_cidrs_desarrollador "${id_grupo}" "${puerto}")"
    if [[ "${cidrs_anteriores}" == "None" ]]; then
        cidrs_anteriores=""
    fi

    for cidr in ${cidrs_anteriores}; do
        habia_reglas="si"
        if [[ "${cidr}" == "${cidr_actual}" ]]; then
            ya_tiene_actual="si"
            mensaje_info "${id_grupo}: la regla ${puerto} desde ${cidr} ya es la IP actual."
            continue
        fi
        aws ec2 revoke-security-group-ingress \
            --region "${REGION}" \
            --group-id "${id_grupo}" \
            --ip-permissions "IpProtocol=tcp,FromPort=${puerto},ToPort=${puerto},IpRanges=[{CidrIp=${cidr}}]" \
            >/dev/null
        mensaje_ok "${id_grupo}: regla anterior ${puerto} desde ${cidr} eliminada."
    done

    if [[ "${ya_tiene_actual}" == "si" ]]; then
        return 0
    fi
    if [[ "${habia_reglas}" == "no" && "${crear_si_no_hay}" != "si" ]]; then
        mensaje_info "${id_grupo}: no hay regla ${puerto} del desarrollador; no se crea (la crea el módulo correspondiente)."
        return 0
    fi
    aws ec2 authorize-security-group-ingress \
        --region "${REGION}" \
        --group-id "${id_grupo}" \
        --ip-permissions "IpProtocol=tcp,FromPort=${puerto},ToPort=${puerto},IpRanges=[{CidrIp=${cidr_actual},Description=${DESCRIPCION_REGLA_IP}}]" \
        >/dev/null
    mensaje_ok "${id_grupo}: regla ${puerto} desde ${cidr_actual} agregada."
}

# --- Programa principal ------------------------------------------------------
verificar_aws_cli
IP_PUBLICA="$(obtener_ip_publica)"
CIDR_ACTUAL="${IP_PUBLICA}/32"
ID_VPC="$(obtener_vpc_por_defecto)"
mensaje_info "IP pública actual: ${CIDR_ACTUAL}"

ID_SG_RDS="$(buscar_security_group "${NOMBRE_SG_RDS}" "${ID_VPC}")"
if [[ -z "${ID_SG_RDS}" ]]; then
    mensaje_error "No existe el security group ${NOMBRE_SG_RDS}. Ejecute primero punto2_fuentes/rds/crear_rds.sh"
    exit 1
fi
reemplazar_regla_ip "${ID_SG_RDS}" "${PUERTO_MARIADB}" "${CIDR_ACTUAL}" "si"

ID_SG_EC2="$(buscar_security_group "${NOMBRE_SG_EC2}" "${ID_VPC}")"
if [[ -n "${ID_SG_EC2}" ]]; then
    reemplazar_regla_ip "${ID_SG_EC2}" "${PUERTO_SSH}" "${CIDR_ACTUAL}" "no"
else
    mensaje_info "No existe ${NOMBRE_SG_EC2}; se omite el puerto ${PUERTO_SSH}."
fi

mensaje_ok "Reglas actualizadas para ${CIDR_ACTUAL}."
