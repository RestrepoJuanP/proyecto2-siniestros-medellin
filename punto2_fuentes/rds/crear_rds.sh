#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# crear_rds.sh
# Crea la fuente relacional del proyecto en el VPC por defecto:
#   1. Security group de la EC2 de fuentes (vacío; se usa en el Módulo 2B).
#   2. Security group de RDS con entrada 3306 desde la IP pública actual (/32)
#      y desde el security group de la EC2.
#   3. Instancia RDS MariaDB (db.t3.micro, 20 GB gp2, single-AZ, pública,
#      sin backups, sin Enhanced Monitoring, sin Performance Insights) con la
#      base inicial y un usuario maestro con clave aleatoria.
#   4. Espera a que esté disponible y escribe la conexión e IDs en .env.
#
# Es idempotente: si los recursos ya existen, no los vuelve a crear.
# Nombres configurables en .env (con valores por defecto):
#   NOMBRE_INSTANCIA_RDS (rds-movilidad), NOMBRE_SG_RDS (sg-rds-movilidad),
#   NOMBRE_SG_EC2 (sg-ec2-fuentes), RDS_USUARIO (admin_movilidad), RDS_BASE (movilidad)
#
# Uso (desde la raíz del repositorio): bash punto2_fuentes/rds/crear_rds.sh
# -----------------------------------------------------------------------------
set -euo pipefail

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../../infra/funciones_comunes.sh
source "${DIR_RAIZ}/infra/funciones_comunes.sh"

CLASE_INSTANCIA="db.t3.micro"
ALMACENAMIENTO_GB="20"
TIPO_ALMACENAMIENTO="gp2"
PUERTO_MARIADB="3306"
# Descripción con la que se marca la regla de la IP del desarrollador.
# actualizar_mi_ip.sh la usa para encontrar y reemplazar la regla anterior.
DESCRIPCION_REGLA_IP="ip-desarrollador"

NOMBRE_INSTANCIA_RDS="$(leer_variable_env_o_defecto NOMBRE_INSTANCIA_RDS rds-movilidad)"
NOMBRE_SG_RDS="$(leer_variable_env_o_defecto NOMBRE_SG_RDS sg-rds-movilidad)"
NOMBRE_SG_EC2="$(leer_variable_env_o_defecto NOMBRE_SG_EC2 sg-ec2-fuentes)"
USUARIO_MAESTRO="$(leer_variable_env_o_defecto RDS_USUARIO admin_movilidad)"
NOMBRE_BASE="$(leer_variable_env_o_defecto RDS_BASE movilidad)"

# Genera una clave aleatoria alfanumérica de 24 caracteres.
# Solo letras y números: RDS no acepta / @ " ni espacios en la clave maestra.
generar_clave_aleatoria() {
    local texto_aleatorio
    if ! command -v openssl >/dev/null 2>&1; then
        mensaje_error "Se requiere openssl para generar la clave (viene con Git Bash, Linux y macOS)."
        exit 1
    fi
    texto_aleatorio="$(openssl rand -base64 96 | tr -dc 'A-Za-z0-9')"
    echo "${texto_aleatorio:0:24}"
}

# Retorna el ID del security group; lo crea si no existe.
obtener_o_crear_security_group() {
    local nombre_grupo="$1"
    local descripcion_grupo="$2"
    local id_vpc="$3"
    local id_grupo
    id_grupo="$(buscar_security_group "${nombre_grupo}" "${id_vpc}")"
    if [[ -n "${id_grupo}" ]]; then
        mensaje_info "El security group ${nombre_grupo} ya existe (${id_grupo})."
    else
        id_grupo="$(aws ec2 create-security-group \
            --region "${REGION}" \
            --group-name "${nombre_grupo}" \
            --description "${descripcion_grupo}" \
            --vpc-id "${id_vpc}" \
            --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${nombre_grupo}},{Key=proyecto,Value=proyecto2-siniestros}]" \
            --query 'GroupId' \
            --output text | limpiar_salida)"
        mensaje_ok "Security group ${nombre_grupo} creado (${id_grupo})."
    fi
    echo "${id_grupo}"
}

# Agrega la regla TCP <puerto> desde <ip>/32 si aún no existe.
agregar_regla_ip() {
    local id_grupo="$1"
    local puerto="$2"
    local ip_publica="$3"
    local cidr="${ip_publica}/32"
    local cidrs_existentes
    cidrs_existentes="$(aws ec2 describe-security-groups \
        --region "${REGION}" \
        --group-ids "${id_grupo}" \
        --query "SecurityGroups[0].IpPermissions[?FromPort==\`${puerto}\`].IpRanges[].CidrIp" \
        --output text | limpiar_salida)"
    if [[ " ${cidrs_existentes} " == *" ${cidr} "* ]]; then
        mensaje_info "La regla ${puerto} desde ${cidr} ya existe en ${id_grupo}."
        return 0
    fi
    aws ec2 authorize-security-group-ingress \
        --region "${REGION}" \
        --group-id "${id_grupo}" \
        --ip-permissions "IpProtocol=tcp,FromPort=${puerto},ToPort=${puerto},IpRanges=[{CidrIp=${cidr},Description=${DESCRIPCION_REGLA_IP}}]" \
        >/dev/null
    mensaje_ok "Regla ${puerto} desde ${cidr} agregada a ${id_grupo}."
}

# Agrega la regla TCP <puerto> desde otro security group si aún no existe.
agregar_regla_desde_grupo() {
    local id_grupo="$1"
    local puerto="$2"
    local id_grupo_origen="$3"
    local grupos_existentes
    grupos_existentes="$(aws ec2 describe-security-groups \
        --region "${REGION}" \
        --group-ids "${id_grupo}" \
        --query "SecurityGroups[0].IpPermissions[?FromPort==\`${puerto}\`].UserIdGroupPairs[].GroupId" \
        --output text | limpiar_salida)"
    if [[ "${grupos_existentes}" == *"${id_grupo_origen}"* ]]; then
        mensaje_info "La regla ${puerto} desde ${id_grupo_origen} ya existe en ${id_grupo}."
        return 0
    fi
    aws ec2 authorize-security-group-ingress \
        --region "${REGION}" \
        --group-id "${id_grupo}" \
        --ip-permissions "IpProtocol=tcp,FromPort=${puerto},ToPort=${puerto},UserIdGroupPairs=[{GroupId=${id_grupo_origen},Description=desde-ec2-fuentes}]" \
        >/dev/null
    mensaje_ok "Regla ${puerto} desde ${id_grupo_origen} agregada a ${id_grupo}."
}

# Crea la instancia RDS. Si AWS la rechaza, muestra el error de forma clara.
crear_instancia_rds() {
    local id_sg_rds="$1"
    local clave_maestra="$2"
    local salida_creacion
    mensaje_info "Creando la instancia ${NOMBRE_INSTANCIA_RDS} (${CLASE_INSTANCIA}, MariaDB versión por defecto)..."
    if ! salida_creacion="$(aws rds create-db-instance \
        --region "${REGION}" \
        --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" \
        --engine mariadb \
        --db-instance-class "${CLASE_INSTANCIA}" \
        --allocated-storage "${ALMACENAMIENTO_GB}" \
        --storage-type "${TIPO_ALMACENAMIENTO}" \
        --no-multi-az \
        --publicly-accessible \
        --backup-retention-period 0 \
        --monitoring-interval 0 \
        --no-enable-performance-insights \
        --no-deletion-protection \
        --db-name "${NOMBRE_BASE}" \
        --master-username "${USUARIO_MAESTRO}" \
        --master-user-password "${clave_maestra}" \
        --vpc-security-group-ids "${id_sg_rds}" \
        --port "${PUERTO_MARIADB}" \
        --tags Key=proyecto,Value=proyecto2-siniestros \
        --output text 2>&1)"; then
        mensaje_error "AWS rechazó la creación de la instancia RDS:"
        echo "${salida_creacion}" >&2
        if [[ "${salida_creacion}" == *"${CLASE_INSTANCIA}"* \
            || "${salida_creacion}" == *"InstanceClass"* \
            || "${salida_creacion}" == *"InvalidParameterCombination"* \
            || "${salida_creacion}" == *"not authorized"* \
            || "${salida_creacion}" == *"AccessDenied"* ]]; then
            mensaje_error "Posible causa: el Learner Lab no permite la clase ${CLASE_INSTANCIA} o esa combinación de motor/versión."
            mensaje_error "Revise las clases permitidas en la guía del Learner Lab y ajuste CLASE_INSTANCIA en este script."
        fi
        exit 1
    fi
    mensaje_ok "Solicitud de creación aceptada."
}

# Espera hasta que la instancia esté 'available' (la creación tarda ~10-15 min).
esperar_rds_disponible() {
    local intento
    for intento in 1 2 3; do
        mensaje_info "Esperando a que ${NOMBRE_INSTANCIA_RDS} esté disponible (intento ${intento} de 3, puede tardar 15 min)..."
        if aws rds wait db-instance-available --region "${REGION}" --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}"; then
            mensaje_ok "La instancia está disponible."
            return 0
        fi
    done
    mensaje_error "La instancia no quedó disponible. Revise la consola de RDS."
    exit 1
}

# --- 1. Validaciones ---------------------------------------------------------
verificar_aws_cli
if [[ ! -f "${ARCHIVO_ENV}" ]]; then
    mensaje_info "No existe .env; se crea a partir de .env.example."
    cp "${DIR_RAIZ}/.env.example" "${ARCHIVO_ENV}"
fi

IP_PUBLICA="$(obtener_ip_publica)"
ID_VPC="$(obtener_vpc_por_defecto)"
mensaje_info "IP pública actual: ${IP_PUBLICA} | VPC por defecto: ${ID_VPC}"

# --- 2. Security groups ------------------------------------------------------
ID_SG_EC2="$(obtener_o_crear_security_group "${NOMBRE_SG_EC2}" "EC2 de fuentes del proyecto 2 (archivos en /datos)" "${ID_VPC}")"
ID_SG_RDS="$(obtener_o_crear_security_group "${NOMBRE_SG_RDS}" "RDS MariaDB movilidad del proyecto 2" "${ID_VPC}")"
agregar_regla_ip "${ID_SG_RDS}" "${PUERTO_MARIADB}" "${IP_PUBLICA}"
agregar_regla_desde_grupo "${ID_SG_RDS}" "${PUERTO_MARIADB}" "${ID_SG_EC2}"
escribir_variable_env ID_SG_EC2 "${ID_SG_EC2}"
escribir_variable_env ID_SG_RDS "${ID_SG_RDS}"

# --- 3. Instancia RDS --------------------------------------------------------
ESTADO_RDS="$(obtener_estado_rds "${NOMBRE_INSTANCIA_RDS}")"
mensaje_info "Estado actual de ${NOMBRE_INSTANCIA_RDS}: ${ESTADO_RDS}"

if [[ "${ESTADO_RDS}" == "no-existe" ]]; then
    CLAVE_MAESTRA="$(generar_clave_aleatoria)"
    crear_instancia_rds "${ID_SG_RDS}" "${CLAVE_MAESTRA}"
    # Se guarda la clave de inmediato para no perderla si la espera se interrumpe
    escribir_variable_env RDS_USUARIO "${USUARIO_MAESTRO}"
    escribir_variable_env RDS_CLAVE "${CLAVE_MAESTRA}"
elif [[ "${ESTADO_RDS}" == "stopped" ]]; then
    mensaje_info "La instancia está detenida; se inicia."
    aws rds start-db-instance --region "${REGION}" --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" >/dev/null
elif [[ "${ESTADO_RDS}" == "deleting" ]]; then
    mensaje_error "La instancia se está borrando. Espere a que termine y vuelva a ejecutar el script."
    exit 1
fi

esperar_rds_disponible

# Si la instancia ya existía pero .env no tiene la clave, se asigna una nueva
CLAVE_EN_ENV="$(leer_variable_env RDS_CLAVE)"
if [[ -z "${CLAVE_EN_ENV}" ]]; then
    mensaje_aviso "La instancia existe pero .env no tiene RDS_CLAVE. Se asigna una clave nueva."
    CLAVE_MAESTRA="$(generar_clave_aleatoria)"
    aws rds modify-db-instance \
        --region "${REGION}" \
        --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" \
        --master-user-password "${CLAVE_MAESTRA}" \
        --apply-immediately >/dev/null
    escribir_variable_env RDS_CLAVE "${CLAVE_MAESTRA}"
    esperar_rds_disponible
fi

# --- 4. Escribir conexión en .env -------------------------------------------
HOST_RDS="$(aws rds describe-db-instances \
    --region "${REGION}" \
    --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text | limpiar_salida)"
VERSION_MOTOR="$(aws rds describe-db-instances \
    --region "${REGION}" \
    --db-instance-identifier "${NOMBRE_INSTANCIA_RDS}" \
    --query 'DBInstances[0].EngineVersion' \
    --output text | limpiar_salida)"

escribir_variable_env RDS_HOST "${HOST_RDS}"
escribir_variable_env RDS_PUERTO "${PUERTO_MARIADB}"
escribir_variable_env RDS_USUARIO "${USUARIO_MAESTRO}"
escribir_variable_env RDS_BASE "${NOMBRE_BASE}"

# --- 5. Resumen (sin mostrar la clave) --------------------------------------
echo ""
echo "=============================================="
echo " Fuente RDS lista"
echo "=============================================="
echo "  Instancia:        ${NOMBRE_INSTANCIA_RDS} (MariaDB ${VERSION_MOTOR}, ${CLASE_INSTANCIA})"
echo "  Host:             ${HOST_RDS}:${PUERTO_MARIADB}"
echo "  Base de datos:    ${NOMBRE_BASE}"
echo "  Usuario:          ${USUARIO_MAESTRO} (clave guardada en .env como RDS_CLAVE)"
echo "  SG de RDS:        ${NOMBRE_SG_RDS} (${ID_SG_RDS})"
echo "  SG de EC2:        ${NOMBRE_SG_EC2} (${ID_SG_EC2})"
echo "  IP autorizada:    ${IP_PUBLICA}/32"
echo ""
echo "Siguiente paso: python punto2_fuentes/rds/cargar_rds.py"
